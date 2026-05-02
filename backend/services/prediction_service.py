import numpy as np
import pandas as pd

from backend.services.data_loader import load_drug_features, load_feature_columns
from backend.services.model_loader import ModelLoaderError, load_model_for_cell_line


class PredictionError(Exception):
    pass


FIELD_ALIASES = {
    "NSC1": ("NSC1", "drug1_id", "Drug1", "drug1", "nsc1"),
    "NSC2": ("NSC2", "drug2_id", "Drug2", "drug2", "nsc2"),
    "CELLNAME": ("CELLNAME", "cell_line", "cellLine", "cell", "cellname"),
}
NEUTRAL_THRESHOLD = 20


def _require_field(payload, field_name):
    value = None
    for candidate in FIELD_ALIASES.get(field_name, (field_name,)):
        value = payload.get(candidate)
        if value is not None and str(value).strip() != "":
            break
    if value is None or str(value).strip() == "":
        raise PredictionError(f"{field_name} is required.")
    return value


def _parse_nsc(payload, field_name):
    value = _require_field(payload, field_name)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise PredictionError(f"{field_name} must be a valid integer NSC.")


def _get_drug_row(drug_features, nsc):
    matches = drug_features[drug_features["NSC"] == nsc]
    if matches.empty:
        raise PredictionError(f"NSC {nsc} not found in data/drug_features.csv.")
    return matches.iloc[0]


def _build_feature_vector(drug1_row, drug2_row, feature_columns):
    base_feature_columns = [column for column in drug1_row.index if column != "NSC"]
    if len(base_feature_columns) != 263:
        raise PredictionError(
            f"Drug feature table has {len(base_feature_columns)} feature columns, expected 263."
        )

    values = {}
    for column in base_feature_columns:
        values[f"D1_{column}"] = drug1_row[column]
        values[f"D2_{column}"] = drug2_row[column]

    missing_columns = [column for column in feature_columns if column not in values]
    if missing_columns:
        raise PredictionError(
            "Feature vector is missing required columns from step6_final_model_feature_columns.json."
        )

    feature_frame = pd.DataFrame([{column: values[column] for column in feature_columns}], columns=feature_columns)
    feature_frame = feature_frame.apply(pd.to_numeric, errors="raise")

    expected_shape = (1, 526)
    if feature_frame.shape != expected_shape:
        raise PredictionError(
            f"Feature vector has incorrect shape {feature_frame.shape}, expected {expected_shape}."
        )
    return feature_frame


def _predict_one(model, feature_frame):
    prediction = model.predict(feature_frame)
    return float(np.asarray(prediction).reshape(-1)[0])


def _label_prediction(score):
    if score >= NEUTRAL_THRESHOLD:
        return (
            "synergistic",
            "The predicted ComboScore is positive, which suggests synergy for this drug pair and cell line.",
        )
    if score <= -NEUTRAL_THRESHOLD:
        return (
            "antagonistic",
            "The predicted ComboScore is negative, which suggests antagonism for this drug pair and cell line.",
        )
    return (
        "neutral",
        "The predicted ComboScore is near zero, which suggests neutral or additive behavior.",
    )


def build_prediction_context(payload):
    if not isinstance(payload, dict):
        raise PredictionError("Request body must be a JSON object.")

    nsc1 = _parse_nsc(payload, "NSC1")
    nsc2 = _parse_nsc(payload, "NSC2")
    cell_line = str(_require_field(payload, "CELLNAME")).strip()

    drug_features = load_drug_features()
    feature_columns = load_feature_columns()
    if len(feature_columns) != 526:
        raise PredictionError(
            f"Feature column list has {len(feature_columns)} columns, expected 526."
        )

    drug1_row = _get_drug_row(drug_features, nsc1)
    drug2_row = _get_drug_row(drug_features, nsc2)

    try:
        model, model_info = load_model_for_cell_line(cell_line)
    except ModelLoaderError as exc:
        raise PredictionError(str(exc))

    forward_features = _build_feature_vector(drug1_row, drug2_row, feature_columns)
    reverse_features = _build_feature_vector(drug2_row, drug1_row, feature_columns)

    return {
        "nsc1": nsc1,
        "nsc2": nsc2,
        "cell_line": cell_line,
        "model": model,
        "model_info": model_info,
        "feature_columns": feature_columns,
        "forward_features": forward_features,
        "reverse_features": reverse_features,
    }


def predict_from_context(context):
    model = context["model"]
    forward_features = context["forward_features"]
    reverse_features = context["reverse_features"]

    forward_prediction = _predict_one(model, forward_features)
    reverse_prediction = _predict_one(model, reverse_features)
    final_prediction = (forward_prediction + reverse_prediction) / 2.0
    label, explanation = _label_prediction(final_prediction)

    return {
        "status": "success",
        "input": {
            "NSC1": context["nsc1"],
            "NSC2": context["nsc2"],
            "CELLNAME": context["cell_line"],
        },
        "model_used": context["model_info"]["model_name"],
        "model_path": context["model_info"]["model_path"],
        "prediction_NSC1_to_NSC2": forward_prediction,
        "prediction_NSC2_to_NSC1": reverse_prediction,
        "final_predicted_COMBOSCORE": final_prediction,
        "label": label,
        "explanation": explanation,
        "feature_count": len(context["feature_columns"]),
    }


def predict_single(payload):
    context = build_prediction_context(payload)
    return predict_from_context(context)
