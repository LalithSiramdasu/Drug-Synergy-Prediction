import re

import numpy as np
import shap

from backend.services.prediction_service import (
    PredictionError,
    build_prediction_context,
    predict_from_context,
)


class ShapExplanationError(Exception):
    pass


_EXPLAINER_CACHE = {}
_FEATURE_PATTERN = re.compile(r"^(D[12])_feat_(\d+)$")


def _get_explainer(model, model_path):
    if model_path not in _EXPLAINER_CACHE:
        try:
            _EXPLAINER_CACHE[model_path] = shap.TreeExplainer(model)
        except Exception as exc:
            raise ShapExplanationError(f"Failed to create SHAP TreeExplainer: {exc}")
    return _EXPLAINER_CACHE[model_path]


def _extract_shap_values(raw_values, feature_count):
    if isinstance(raw_values, list):
        if not raw_values:
            raise ShapExplanationError("SHAP returned no values.")
        raw_values = raw_values[0]

    if hasattr(raw_values, "values"):
        raw_values = raw_values.values

    values = np.asarray(raw_values, dtype=float)
    if values.ndim == 3:
        values = values[0, :, 0]
    elif values.ndim == 2:
        values = values[0]
    elif values.ndim != 1:
        raise ShapExplanationError(f"Unexpected SHAP value shape: {values.shape}.")

    if values.shape[0] != feature_count:
        raise ShapExplanationError(
            f"SHAP returned {values.shape[0]} feature values, expected {feature_count}."
        )
    return values


def _get_base_value(explainer):
    expected_value = explainer.expected_value
    if isinstance(expected_value, list):
        expected_value = expected_value[0]
    values = np.asarray(expected_value, dtype=float).reshape(-1)
    if values.size == 0:
        raise ShapExplanationError("SHAP expected value was empty.")
    return float(values[0])


def _run_shap(explainer, feature_frame, feature_count):
    try:
        raw_values = explainer.shap_values(feature_frame)
    except Exception as exc:
        raise ShapExplanationError(f"SHAP calculation failed: {exc}")
    return _extract_shap_values(raw_values, feature_count)


def _feature_metadata(feature_name):
    match = _FEATURE_PATTERN.match(feature_name)
    if not match:
        return {
            "drug_side": "Unknown",
            "feature_type": "unknown",
            "readable_feature": feature_name,
        }

    prefix, feature_index_text = match.groups()
    feature_index = int(feature_index_text)
    drug_side = "Drug 1" if prefix == "D1" else "Drug 2"
    if 0 <= feature_index <= 255:
        feature_type = "Morgan fingerprint"
        readable_feature = f"{drug_side} fingerprint feature {feature_index}"
    elif 256 <= feature_index <= 262:
        feature_type = "physicochemical"
        readable_feature = f"{drug_side} physicochemical feature {feature_index}"
    else:
        feature_type = "unknown"
        readable_feature = f"{drug_side} feature {feature_index}"

    return {
        "drug_side": drug_side,
        "feature_type": feature_type,
        "readable_feature": readable_feature,
    }


def _counterpart_feature(feature_name):
    if feature_name.startswith("D1_"):
        return "D2_" + feature_name[3:]
    if feature_name.startswith("D2_"):
        return "D1_" + feature_name[3:]
    return feature_name


def _feature_record(feature_name, feature_value, shap_value):
    metadata = _feature_metadata(feature_name)
    effect = (
        "pushes prediction upward / more antagonistic"
        if shap_value > 0
        else "pushes prediction downward / more synergistic"
    )
    return {
        "feature": feature_name,
        "readable_feature": metadata["readable_feature"],
        "feature_value": float(feature_value),
        "shap_value": float(shap_value),
        "effect": effect,
    }


def _combine_forward_reverse_effects(context, forward_shap, reverse_shap):
    feature_columns = context["feature_columns"]
    forward_features = context["forward_features"]
    forward_by_feature = dict(zip(feature_columns, forward_shap))
    reverse_by_feature = dict(zip(feature_columns, reverse_shap))

    combined_records = []
    for feature_name in feature_columns:
        counterpart = _counterpart_feature(feature_name)
        if counterpart not in reverse_by_feature:
            raise ShapExplanationError(f"Missing reverse SHAP counterpart for {feature_name}.")

        # SHAP data flow:
        # user NSC input -> shared prediction context builds forward and reverse
        # 526-feature matrices -> SHAP explains each matrix -> reverse effects are
        # mapped back to the original drug side -> averaged feature effects become
        # JSON contributors for frontend display.
        #
        # Forward keeps the user's NSC1/NSC2 order. Reverse swaps drug positions,
        # so the counterpart column maps the reverse effect back to the same input drug.
        combined_shap = (forward_by_feature[feature_name] + reverse_by_feature[counterpart]) / 2.0
        feature_value = forward_features.at[0, feature_name]
        combined_records.append(_feature_record(feature_name, feature_value, combined_shap))

    return combined_records


def _top_features(records):
    positive = [record for record in records if record["shap_value"] > 0]
    negative = [record for record in records if record["shap_value"] < 0]
    positive = sorted(positive, key=lambda record: abs(record["shap_value"]), reverse=True)[:10]
    negative = sorted(negative, key=lambda record: abs(record["shap_value"]), reverse=True)[:10]
    return positive, negative


def _summary(label, final_prediction):
    if label == "synergistic":
        interpretation = "the model predicts this pair may work better together for this cell line"
    elif label == "antagonistic":
        interpretation = "the model predicts this pair may interfere with each other for this cell line"
    else:
        interpretation = "the model predicts mostly additive or neutral behavior for this cell line"

    return (
        f"The final predicted ComboScore is {final_prediction:.3f}, so {interpretation}. "
        "Positive SHAP values pushed the prediction upward toward antagonism. "
        "Negative SHAP values pushed the prediction downward toward synergy. "
        "The listed contributors average the forward and reverse drug-order explanations."
    )


def _suggestion(label):
    if label == "synergistic":
        return (
            "This is a model prediction, not biological proof. Strong synergy cases may be "
            "worth further experimental checking."
        )
    if label == "antagonistic":
        return (
            "This is a model prediction, not biological proof. Predicted antagonistic cases "
            "may need caution before prioritization."
        )
    return (
        "This is a model prediction, not biological proof. Neutral cases may not show a "
        "strong interaction and should be interpreted cautiously."
    )


def explain_prediction(payload):
    try:
        context = build_prediction_context(payload)
        prediction = predict_from_context(context)
    except PredictionError:
        raise
    except Exception as exc:
        raise ShapExplanationError(str(exc))

    model = context["model"]
    model_path = prediction["model_path"]
    model_name = prediction["model_used"]
    cell_line = prediction["input"]["CELLNAME"]
    feature_count = len(context["feature_columns"])
    try:
        explainer = _get_explainer(model, model_path)
        forward_shap = _run_shap(explainer, context["forward_features"], feature_count)
        reverse_shap = _run_shap(explainer, context["reverse_features"], feature_count)
        combined_records = _combine_forward_reverse_effects(context, forward_shap, reverse_shap)
        top_positive, top_negative = _top_features(combined_records)
    except ShapExplanationError as exc:
        raise ShapExplanationError(
            f"SHAP explanation failed for {model_name} model on cell line {cell_line}: {exc}"
        )

    return {
        "status": "success",
        "input": prediction["input"],
        "model_used": prediction["model_used"],
        "model_path": prediction["model_path"],
        "prediction_NSC1_to_NSC2": prediction["prediction_NSC1_to_NSC2"],
        "prediction_NSC2_to_NSC1": prediction["prediction_NSC2_to_NSC1"],
        "final_predicted_COMBOSCORE": prediction["final_predicted_COMBOSCORE"],
        "label": prediction["label"],
        "explanation_summary": _summary(
            prediction["label"],
            prediction["final_predicted_COMBOSCORE"],
        ),
        "suggestion": _suggestion(prediction["label"]),
        "top_positive_contributors": top_positive,
        "top_negative_contributors": top_negative,
    }
