import json
import os
import urllib.parse
import urllib.request

from backend.config import GEMINI_KEYS_LOCAL_PATH
from backend.services.model_performance_service import build_model_performance_summary
from backend.services.system_summary_service import build_system_summary


SAFETY_NOTE = (
    "This is a machine-learning screening prediction, not biological proof or clinical advice."
)

DEFAULT_SUGGESTED_QUESTIONS = [
    "What is ComboScore?",
    "How does prediction work?",
    "Can I trust the prediction?",
    "What should be validated experimentally?",
    "Is this clinical advice?",
    "What is Explain AI?",
    "What CSV format is required?",
]

PROJECT_TOPIC_SUGGESTIONS = {
    "basics": [
        "What is SynergyLens?",
        "What is ComboScore?",
        "What is NSC?",
        "What dataset is used?",
        "What are the main project limitations?",
    ],
    "prediction": [
        "How does prediction work?",
        "Why predict both directions?",
        "What thresholds are used for labels?",
        "Can I trust the prediction?",
        "What should be validated experimentally?",
    ],
    "xai": [
        "What is Explain AI?",
        "What is XAI?",
        "What is SHAP?",
        "How do I read XAI results?",
        "Can XAI prove the biological mechanism?",
    ],
    "batch": [
        "What is batch prediction?",
        "What CSV format is required?",
        "Why did a batch row fail?",
        "How do I download batch results?",
    ],
    "molecules": [
        "What is Molecule Lookup?",
        "What molecule information is shown?",
        "Why might molecule structure be unavailable?",
    ],
    "backend": [
        "What files does the backend use?",
        "What is the model registry?",
        "What are 263 and 526 features?",
        "Are models cell-line specific?",
    ],
    "safety": [
        "Is this clinical advice?",
        "Can this be used for treatment decisions?",
        "Can I trust the prediction?",
        "What should be validated experimentally?",
        "What does screening confidence mean?",
    ],
}

PREDICTION_SUGGESTED_QUESTIONS = [
    "Explain this result",
    "What does this score mean?",
    "What model was used?",
    "Why predict both directions?",
    "Is this clinical advice?",
    "What should I check next?",
]

NEUTRAL_THRESHOLD = 20
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_PROVIDER_LABEL = "AI Enhanced"
FALLBACK_PROVIDER_LABEL = "Built-in Guide"
PLACEHOLDER_GEMINI_KEYS = {
    "your_gemini_api_key_here",
    "your_first_gemini_api_key_here",
    "your_second_gemini_api_key_here",
    "key1",
    "key2",
    "key3",
}


class ChatServiceError(Exception):
    pass


def answer_chat_question(payload):
    if not isinstance(payload, dict):
        raise ChatServiceError("Request body must be a JSON object.")

    mode = str(payload.get("mode") or "project").strip().lower()
    if mode == "project":
        payload["mode"] = mode
        return answer_project_question(payload)
    if mode == "prediction":
        payload["mode"] = mode
        return answer_prediction_question(payload)

    raise ChatServiceError("Only project and prediction chat modes are available in this version.")


def answer_project_question(payload):
    if not isinstance(payload, dict):
        raise ChatServiceError("Request body must be a JSON object.")

    mode = str(payload.get("mode") or "project").strip().lower()
    if mode != "project":
        raise ChatServiceError("Only project chat mode is available in this version.")

    question = str(payload.get("question") or "").strip()
    if not question:
        raise ChatServiceError("Question is required.")

    context = _load_project_context()
    matched_topic, answer = _match_project_answer(question, context)

    return {
        "status": "success",
        "mode": "project",
        "answer": answer,
        "matched_topic": matched_topic,
        "suggested_questions": _suggestions_for_topic(matched_topic),
        "safety_note": SAFETY_NOTE,
    }


def answer_prediction_question(payload):
    if not isinstance(payload, dict):
        raise ChatServiceError("Request body must be a JSON object.")

    question = str(payload.get("question") or "").strip()
    if not question:
        raise ChatServiceError("Question is required.")

    prediction = payload.get("prediction")
    if not isinstance(prediction, dict):
        raise ChatServiceError("Prediction context is required for prediction chat mode.")

    context = _normalize_prediction_context(prediction)
    explanation = payload.get("explanation") if isinstance(payload.get("explanation"), dict) else None
    matched_topic, fallback_answer = _match_prediction_answer(question, context, explanation)

    llm_result = _try_gemini_answer(question, context, explanation, matched_topic)
    if llm_result["answer"]:
        answer = llm_result["answer"]
        llm_used = True
        provider = "gemini"
        provider_label = GEMINI_PROVIDER_LABEL
    else:
        answer = fallback_answer
        llm_used = False
        provider = "fallback"
        provider_label = FALLBACK_PROVIDER_LABEL

    return {
        "status": "success",
        "mode": "prediction",
        "answer": answer,
        "matched_topic": matched_topic,
        "llm_used": llm_used,
        "provider": provider,
        "provider_label": provider_label,
        "attempted_key_count": llm_result["attempted_key_count"],
        "successful_key_index": llm_result["successful_key_index"],
        "suggested_questions": _prediction_suggestions_for_topic(matched_topic),
        "safety_note": SAFETY_NOTE,
    }


def _load_project_context():
    context = {
        "available_drugs": "100",
        "available_cell_lines": "60",
        "feature_column_count": "526",
        "final_model_count": "60",
        "model_counts": {
            "CatBoost": 17,
            "LightGBM": 17,
            "RandomForest": 15,
            "XGBoost": 11,
        },
    }

    try:
        system_summary = build_system_summary()
        assets = system_summary.get("assets", {})
        model_summary = system_summary.get("model_summary", {})
        context.update(
            {
                "available_drugs": _display_count(assets.get("available_drugs"), context["available_drugs"]),
                "available_cell_lines": _display_count(assets.get("available_cell_lines"), context["available_cell_lines"]),
                "feature_column_count": _display_count(assets.get("feature_column_count"), context["feature_column_count"]),
                "final_model_count": _display_count(assets.get("final_model_count"), context["final_model_count"]),
            }
        )
        if isinstance(model_summary.get("count_per_model_type"), dict):
            context["model_counts"] = {
                str(model): int(count)
                for model, count in model_summary["count_per_model_type"].items()
            }
    except Exception:
        pass

    try:
        performance = build_model_performance_summary()
        model_summary = performance.get("model_summary", {})
        if isinstance(model_summary.get("count_per_model_type"), dict):
            context["model_counts"] = {
                str(model): int(count)
                for model, count in model_summary["count_per_model_type"].items()
            }
    except Exception:
        pass

    return context


def _display_count(value, fallback):
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return str(fallback)


def _match_project_answer(question, context):
    text = _normalize(question)

    if _has_any(text, ["my prediction", "my result", "why is my", "explain result", "this prediction", "my score"]):
        return (
            "prediction_assistant",
            (
                "The Project Assistant explains general SynergyLens concepts. For a specific result, run a prediction and use "
                "Ask Prediction Assistant so the chat can use the latest NSC pair, cell line, ComboScore, model, and direction-averaged score."
            ),
        )

    if _has_any(text, ["clinical", "medical", "advice", "doctor", "patient", "treatment", "therapy", "treatment decision", "treatment decisions"]):
        return (
            "safety",
            (
                "No. SynergyLens is a machine-learning screening and education tool. It is not biological proof, not clinical advice, "
                "and not a treatment recommendation. Promising predictions should be treated as research leads and validated experimentally."
            ),
        )

    if _has_any(text, ["trust", "reliable", "confidence", "can i trust", "screening confidence"]):
        return (
            "trust_and_limitations",
            (
                "Use a SynergyLens prediction as a machine-learning screening estimate, not as proof. The result comes from learned "
                "patterns in the NCI ALMANAC-derived data and the saved model selected for the chosen cell line. It can help prioritize "
                "pairs for review, but it should be checked with the result story, XAI contributors, molecule information, model context, "
                "and experimental validation. It is not clinical advice or a treatment recommendation."
            ),
        )

    if _has_any(text, ["validated experimentally", "validate experimentally", "experimental validation", "what should be validated", "validated in lab", "experimentally"]):
        return (
            "experimental_validation",
            (
                "Validate the predicted drug pair experimentally in the selected cell line. Check dose-response behavior, the combination "
                "effect versus each individual drug, reproducibility across assay repeats, toxicity or viability assay consistency, and whether "
                "the observed response supports the predicted synergy, neutrality, or antagonism. XAI can suggest model drivers, but it does not "
                "prove a biological mechanism."
            ),
        )

    if _has_any(text, ["check next", "what should i check", "after prediction", "next after prediction"]):
        return (
            "next_checks",
            (
                "After a prediction, review the ComboScore sign and label, compare the forward and reverse directional predictions, check the "
                "auto-selected model, run Explain AI/XAI for feature contributors, inspect molecule structures if useful, and treat promising "
                "or surprising results as candidates for experimental validation."
            ),
        )

    if _has_any(text, ["limitation", "limitations", "weakness", "caveat", "overpromise"]):
        return (
            "limitations",
            (
                "Main limitations: SynergyLens uses saved ML models trained from available NCI ALMANAC-derived data, so predictions depend on "
                "that dataset, feature preparation, and cell-line-specific model quality. It does not prove biology, does not model dosing or "
                "clinical outcomes, and should not be used for treatment decisions. Results need experimental validation."
            ),
        )

    if _has_any(text, ["purpose", "goal", "why was", "why build"]):
        return (
            "project_purpose",
            (
                "The purpose of SynergyLens is to deploy the completed drug-synergy ML pipeline as a clear Flask demo. It lets evaluators enter "
                "valid NSC drug IDs and a cell line, then see a ComboScore prediction, model context, readable interpretation, molecule lookup, "
                "XAI explanation, and batch prediction support."
            ),
        )

    if _has_any(text, ["dataset", "nci almanac", "almanac"]):
        return (
            "dataset",
            (
                "The project uses the NCI ALMANAC drug-combination screening dataset prepared for ComboScore prediction. In this deployed app, "
                f"the available input set contains {context['available_drugs']} drugs and {context['available_cell_lines']} cell lines, with saved "
                "features and final models already prepared before deployment."
            ),
        )

    if _has_any(text, ["csv", "batch format", "upload format", "batch input", "sample csv"]):
        return (
            "batch_csv_format",
            (
                "Batch prediction needs a CSV with these columns: NSC1, NSC2, CELLNAME. Example rows are 740,750,786-0; "
                "740,752,A498; and 750,755,A549/ATCC. Each row is validated independently, and one failed row should not stop the full batch."
            ),
        )

    if _has_any(text, ["batch row fail", "row fail", "failed row", "why did a batch row fail", "successful failed", "successful/failed"]):
        return (
            "batch_row_status",
            (
                "A batch row can fail if an NSC ID is unavailable, the cell line is not in the deployed model registry, required columns are "
                "missing, or a row has empty/invalid values. Successful rows receive model, directional predictions, final ComboScore, label, "
                "and status. Failed rows keep an error message so the rest of the CSV can still be processed."
            ),
        )

    if _has_any(text, ["download batch", "download results", "output csv"]):
        return (
            "batch_download",
            "After batch prediction succeeds, use the Download CSV button in the Batch Preview area to download the processed output file.",
        )

    if _has_any(text, ["batch", "bulk", "many rows", "multiple predictions"]):
        return (
            "batch_prediction",
            (
                "Batch prediction lets you upload a CSV of drug pairs and cell lines. The backend runs the same single-prediction flow row by row, "
                "records row-level success or error, shows a preview table, and provides a downloadable output CSV."
            ),
        )

    if _has_any(text, ["prove", "mechanism", "biological mechanism"]) and _has_any(text, ["xai", "shap", "explain"]):
        return (
            "xai_limits",
            (
                "No. XAI explains model behavior, not biological mechanism. It can show which input features pushed the predicted ComboScore "
                "upward or downward, but mechanism claims still require experimental and biological validation."
            ),
        )

    if _has_any(text, ["positive xai", "positive shap", "xai values", "shap values", "negative xai", "negative shap", "how do i read xai", "read xai", "read explain"]):
        return (
            "xai_direction",
            (
                "Read XAI values by direction. Positive contributors push the ComboScore upward toward synergy. Negative contributors pull the "
                "ComboScore downward toward antagonism. Larger absolute values usually indicate stronger influence on that model output, but they "
                "explain the model calculation rather than proving biology."
            ),
        )

    if _has_any(text, ["shap", "xai", "explain ai", "explainable", "feature contribution", "contributors", "feature impact"]):
        return (
            "explain_ai",
            (
                "Explain AI is the app's XAI section. It uses SHAP-style feature contributions to show which drug-pair features pushed the "
                "ComboScore upward toward synergy or downward toward antagonism. It helps interpret model behavior, but it is not biological proof."
            ),
        )

    if _has_any(text, ["fingerprint", "physicochemical", "feature named", "feature names"]):
        return (
            "feature_names",
            (
                "Most input features are molecular fingerprint counts, so they are displayed as fingerprint pattern features. The final seven "
                "features per drug are readable physicochemical descriptors such as Molecular Weight, LogP, TPSA, hydrogen-bond counts, rotatable "
                "bonds, and ring count."
            ),
        )

    if _has_any(text, ["molecule lookup", "molecules", "molecule information", "compound profile", "structure", "direct molecule match", "structure unavailable"]):
        return (
            "molecule_lookup",
            (
                "Molecule Lookup shows compound profile cards for the selected NSC values, including the input NSC, structure NSC, molecular formula, "
                "structure source, and rendered molecule SVG when available. A direct molecule match means the requested NSC had a structure in the "
                "molecule assets. A structure can be unavailable if that NSC is missing from the stored molecule files or aliases."
            ),
        )

    if _has_any(text, ["263", "526", "features per drug", "feature vector", "drug features"]):
        return (
            "feature_vector",
            (
                "Each drug has 263 prepared features. For a pair, SynergyLens builds Drug 1 features plus Drug 2 features, giving 526 total model "
                "input columns. The backend uses the saved feature-column JSON file so the deployed feature order matches the trained models."
            ),
        )

    if _has_any(text, ["model registry", "registry"]):
        return (
            "model_registry",
            (
                "The model registry maps each valid cell line to its selected final Step 6 model and model file. SynergyLens uses it automatically, "
                "so users enter NSC1, NSC2, and CELLNAME but do not manually choose RandomForest, XGBoost, CatBoost, or LightGBM."
            ),
        )

    if _has_any(text, ["step 6", "step6", "final model"]):
        return (
            "step6_models",
            (
                "Step 6 models are the final saved deployment models for this project. The app loads these saved model files from the models folder "
                "and selects one model per cell line using the final registry. It does not retrain models during prediction."
            ),
        )

    if _has_any(text, ["what model was used", "model selected", "model selection", "how is the model selected", "cell-line specific", "cell line specific", "cell-line-specific"]):
        return (
            "model_selection",
            (
                "Models are cell-line specific. For each prediction, the backend looks up the selected final model for the input CELLNAME in the "
                "model registry, loads that saved model, and returns the model name in the prediction result. The Project Assistant cannot name a "
                "specific model until a prediction context is available."
            ),
        )

    if _has_any(text, ["model", "algorithm", "randomforest", "xgboost", "catboost", "lightgbm"]):
        return ("models", _model_answer(context))

    if _has_any(text, ["threshold", "thresholds", "label rule", "label rules", "label"]):
        return (
            "label_thresholds",
            (
                "SynergyLens labels the final averaged ComboScore using a neutral band of -20 to +20. Scores >= 20 are synergistic, scores <= -20 "
                "are antagonistic, and scores between -20 and +20 are neutral or weak effect. Stronger display categories use the same sign direction: "
                "higher positive means stronger synergy, and more negative means stronger antagonism."
            ),
        )

    if _has_any(text, ["why predict both", "why are two", "two drug orders", "two predictions", "reverse", "both orders", "nsc1 to nsc2", "nsc2 to nsc1", "order"]):
        return (
            "directional_average",
            (
                "The model input has separate Drug 1 and Drug 2 columns, so NSC1 -> NSC2 and NSC2 -> NSC1 are not identical feature vectors. "
                "Because a drug combination should be interpreted symmetrically, SynergyLens predicts both orders and averages them into the final ComboScore."
            ),
        )

    if _has_any(text, ["inputs", "input required", "required input", "nsc1", "nsc2", "cellname", "cell name"]):
        return (
            "prediction_inputs",
            "A single prediction requires NSC1, NSC2, and CELLNAME. NSC1 and NSC2 must be valid project drug IDs, and CELLNAME must be one of the deployed cell lines.",
        )

    if _has_any(text, ["how does prediction", "prediction work", "what happens after", "flow", "pipeline", "predict"]):
        return (
            "prediction_flow",
            (
                "Prediction starts by validating NSC1, NSC2, and CELLNAME. The backend loads 263 features for each drug, builds the D1+D2 and "
                "D2+D1 feature vectors in the saved 526-column order, selects the saved model for the cell line, predicts both directions, averages "
                "the two ComboScores, assigns the label, and returns model/result/safety context."
            ),
        )

    if _has_any(text, ["asset", "file", "backend use", "backend uses", "feature file", "feature columns", "data flow", "frontend to backend"]):
        return (
            "backend_assets",
            (
                "The backend uses data/drug_features.csv for drug features, data/step6_final_model_feature_columns.json for the exact 526-feature "
                "order, results/step6_final_model_registry.csv for automatic model selection, models/final_step6_*.pkl for saved models, and molecule "
                "assets for structure rendering. The frontend sends NSC1, NSC2, and CELLNAME to the Flask API, and the backend returns JSON for the UI."
            ),
        )

    if _has_any(text, ["how many", "count", "drugs", "cell lines", "features", "available"]):
        return (
            "project_counts",
            f"SynergyLens currently exposes {context['available_drugs']} valid drugs, {context['available_cell_lines']} valid cell lines, a {context['feature_column_count']}-feature model input vector, and {context['final_model_count']} final saved models.",
        )

    if _has_any(text, ["nsc", "drug id", "compound id"]):
        return (
            "nsc",
            "NSC is the identifier used by the National Cancer Institute for compounds in this project. In SynergyLens, users enter valid NSC IDs for Drug 1 and Drug 2, and the backend looks up the prepared features for those IDs.",
        )

    if _has_any(text, ["what is synergylens", "synergylens", "project", "app"]):
        return (
            "project_overview",
            (
                "SynergyLens is a Flask app for NCI ALMANAC ComboScore prediction. It lets users select two valid NSC drugs and one cell line, "
                "then uses saved ML models to estimate the drug-combination interaction. "
                f"The deployed project includes {context['available_drugs']} drugs, {context['available_cell_lines']} cell lines, and {context['final_model_count']} final models."
            ),
        )

    if _has_any(text, ["positive comboscore", "positive score", "synergistic", "synergy", "positive"]):
        return (
            "synergy",
            "Synergistic means the predicted ComboScore is positive enough to suggest stronger-than-expected inhibition for the selected drug pair and cell line. In this project, positive ComboScore points toward synergy.",
        )

    if _has_any(text, ["negative comboscore", "negative score", "antagonistic", "antagonism", "negative"]):
        return (
            "antagonism",
            "Antagonistic means the predicted ComboScore is negative enough to suggest weaker-than-expected inhibition for the selected drug pair and cell line. In this project, negative ComboScore points toward antagonism.",
        )

    if _has_any(text, ["neutral", "additive", "near zero", "weak effect"]):
        return (
            "neutral",
            "Neutral means the predicted ComboScore is close to zero, so the drug pair behaves roughly as expected from the individual drugs. It suggests additive or weak interaction behavior rather than strong synergy or antagonism.",
        )

    if _has_any(text, ["comboscore", "combo score", "score"]):
        return (
            "comboscore",
            (
                "ComboScore compares expected growth with observed percent growth: ComboScore = Expected growth - Observed percent growth. "
                "Positive means observed growth is lower than expected and suggests stronger-than-expected inhibition or synergy. Near zero suggests "
                "neutral/additive behavior. Negative suggests weaker-than-expected effect or antagonism. It is a screening score, not proof."
            ),
        )

    return (
        "fallback",
        (
            "I can answer SynergyLens project questions about ComboScore, NSC IDs, prediction flow, XAI/Explain AI, batch CSV format, molecule lookup, "
            "model assets, and safety limits. Try asking: 'How does prediction work?', 'Can I trust the prediction?', or 'What should be validated experimentally?'"
        ),
    )


def _model_answer(context):
    model_counts = context.get("model_counts", {})
    if model_counts:
        counts_text = ", ".join(
            f"{model}: {count}"
            for model, count in sorted(model_counts.items())
        )
    else:
        counts_text = "CatBoost, LightGBM, RandomForest, and XGBoost."

    return (
        "SynergyLens compares and deploys RandomForest, XGBoost, CatBoost, and LightGBM model families. "
        "The final registry stores one selected model per cell line, so users do not manually choose the model. "
        f"Current final model counts are {counts_text}."
    )


def _normalize_prediction_context(prediction):
    input_context = prediction.get("input") if isinstance(prediction.get("input"), dict) else {}
    score = _required_number(
        prediction.get("final_predicted_COMBOSCORE")
        if "final_predicted_COMBOSCORE" in prediction
        else prediction.get("score"),
        "final_predicted_COMBOSCORE",
    )
    forward = _optional_number(prediction.get("prediction_NSC1_to_NSC2"))
    reverse = _optional_number(prediction.get("prediction_NSC2_to_NSC1"))
    label = _normalize_prediction_label(prediction.get("label") or prediction.get("prediction_label"), score)

    return {
        "nsc1": input_context.get("NSC1") or prediction.get("NSC1") or prediction.get("nsc1") or "Drug 1",
        "nsc2": input_context.get("NSC2") or prediction.get("NSC2") or prediction.get("nsc2") or "Drug 2",
        "cell_line": input_context.get("CELLNAME") or prediction.get("CELLNAME") or prediction.get("cellLine") or "selected cell line",
        "score": score,
        "forward": forward,
        "reverse": reverse,
        "label": label,
        "model_used": prediction.get("model_used") or prediction.get("model") or prediction.get("model_name") or "auto-selected model",
    }


def _required_number(value, field_name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ChatServiceError(f"{field_name} is required and must be numeric.")
    if number != number or number in (float("inf"), float("-inf")):
        raise ChatServiceError(f"{field_name} is required and must be numeric.")
    return number


def _optional_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _normalize_prediction_label(value, score):
    normalized = str(value or "").strip().lower()
    if "synerg" in normalized:
        return "synergistic"
    if "antag" in normalized:
        return "antagonistic"
    if "neutral" in normalized or "weak" in normalized or "additive" in normalized:
        return "neutral"
    return _label_from_score(score)


def _label_from_score(score):
    if score >= NEUTRAL_THRESHOLD:
        return "synergistic"
    if score <= -NEUTRAL_THRESHOLD:
        return "antagonistic"
    return "neutral"


def _match_prediction_answer(question, context, explanation):
    text = _normalize(question)
    if _has_any(text, ["clinical", "medical", "advice", "doctor", "patient", "treatment", "therapy", "trust"]):
        return (
            "safety",
            (
                "This prediction should be treated as an ML screening estimate, not biological proof and not clinical advice. "
                f"For NSC {context['nsc1']} + NSC {context['nsc2']} in {context['cell_line']}, the model output is "
                f"{_format_score(context['score'])} ({context['label']}). Use it to prioritize review, then validate experimentally."
            ),
        )

    if _has_any(text, ["feature", "features", "caused", "driver", "drivers", "contributor", "contributors", "shap", "why exactly"]):
        feature_answer = _feature_context_answer(explanation)
        return (
            "feature_contributors" if feature_answer else "feature_contributors_missing",
            feature_answer
            or (
                "For feature-level reasons, run Explain AI first. This Prediction Assistant currently has the score, model, "
                "cell-line, and direction-averaging context, but no XAI contributor context for this chat. After Explain AI runs, "
                "ask again to summarize the top contributors."
            ),
        )

    if _has_any(text, ["model", "algorithm", "lightgbm", "catboost", "xgboost", "randomforest"]):
        return (
            "model_used",
            (
                f"This prediction used the auto-selected {context['model_used']} model for the {context['cell_line']} cell line. "
                "SynergyLens selects the saved Step 6 model from the final registry, so the user does not manually choose the model family."
            ),
        )

    if _has_any(text, ["two predictions", "both directions", "both drug", "reverse", "forward", "nsc1", "nsc2", "direction"]):
        return (
            "directional_predictions",
            (
                "The app predicts both directions because the feature matrix has separate Drug 1 and Drug 2 columns. "
                f"Here, NSC {context['nsc1']} -> NSC {context['nsc2']} predicted {_format_score(context['forward'])}, "
                f"and NSC {context['nsc2']} -> NSC {context['nsc1']} predicted {_format_score(context['reverse'])}. "
                f"The final ComboScore is their average: {_format_score(context['score'])}."
            ),
        )

    if _has_any(text, ["next", "check next", "what should", "recommend", "prioritize"]):
        return (
            "next_steps",
            (
                "Next, review the score direction and magnitude, compare the two directional predictions, run Explain AI for XAI contributors, "
                "inspect molecule structures if useful, and treat the result as a screening lead that needs experimental validation."
            ),
        )

    if _has_any(text, ["score", "comboscore", "mean", "interpret"]):
        return ("score_meaning", _prediction_result_summary(context))

    if _has_any(text, ["synergistic", "synergy", "antagonistic", "antagonism", "neutral", "why", "explain", "result"]):
        return ("result_explanation", _prediction_result_summary(context))

    return ("prediction_overview", _prediction_result_summary(context))


def _prediction_result_summary(context):
    meaning = {
        "synergistic": "positive ComboScore suggests stronger-than-expected inhibition and possible synergy",
        "antagonistic": "negative ComboScore suggests weaker-than-expected inhibition and possible antagonism",
        "neutral": "near-zero ComboScore suggests roughly additive or weak interaction behavior",
    }[context["label"]]

    return (
        f"Result meaning: For NSC {context['nsc1']} + NSC {context['nsc2']} in {context['cell_line']}, "
        f"SynergyLens predicted a final averaged ComboScore of {_format_score(context['score'])}. "
        f"Why this label: The result is {context['label']} because {meaning}. "
        f"Model context: The auto-selected model was {context['model_used']}. The forward prediction was "
        f"{_format_score(context['forward'])}, the reverse prediction was {_format_score(context['reverse'])}, "
        "and SynergyLens averaged those two values because the feature matrix has separate Drug 1 and Drug 2 columns. "
        "What to check next: Run Explain AI for XAI feature contributors, inspect molecule structures if useful, and use the result only as a screening lead. "
        f"Safety: {SAFETY_NOTE}"
    )


def _feature_context_answer(explanation):
    positive, negative = _extract_contributors(explanation)
    if not positive and not negative:
        return ""

    positive_text = _contributors_text(positive, "upward toward synergy")
    negative_text = _contributors_text(negative, "downward toward antagonism")
    parts = []
    if positive_text:
        parts.append(f"Top positive contributors pushed the ComboScore {positive_text}.")
    if negative_text:
        parts.append(f"Top negative contributors pulled the ComboScore {negative_text}.")
    parts.append("These XAI contributors explain model behavior, not biological proof.")
    return " ".join(parts)


def _extract_contributors(explanation):
    if not isinstance(explanation, dict):
        return [], []

    positive = explanation.get("top_positive_contributors")
    negative = explanation.get("top_negative_contributors")
    if isinstance(positive, list) or isinstance(negative, list):
        return _clean_contributors(positive or []), _clean_contributors(negative or [])

    features = explanation.get("features")
    if isinstance(features, list):
        positive = [feature for feature in features if _contributor_value(feature) > 0]
        negative = [feature for feature in features if _contributor_value(feature) < 0]
        positive = sorted(positive, key=lambda item: abs(_contributor_value(item)), reverse=True)[:5]
        negative = sorted(negative, key=lambda item: abs(_contributor_value(item)), reverse=True)[:5]
        return _clean_contributors(positive), _clean_contributors(negative)

    return [], []


def _clean_contributors(records):
    cleaned = []
    for record in records[:5]:
        if not isinstance(record, dict):
            continue
        name = (
            record.get("readable_feature")
            or record.get("feature_name")
            or record.get("feature")
            or "Feature"
        )
        cleaned.append({"name": str(name), "value": _contributor_value(record)})
    return cleaned


def _contributor_value(record):
    if not isinstance(record, dict):
        return 0.0
    return _optional_number(record.get("shap_value") or record.get("shap") or record.get("impact")) or 0.0


def _contributors_text(records, direction):
    if not records:
        return ""
    names = ", ".join(
        f"{record['name']} ({_format_score(record['value'])})"
        for record in records[:3]
    )
    return f"{direction}: {names}"


def _try_gemini_answer(question, context, explanation, matched_topic):
    # Gemini keys are private. They can come from OS env, .env, or .gemini_keys.local.
    # The local key file is ignored by Git; .gemini_keys.example is the safe template.
    # Fallback is used only after every configured key fails or no real key exists.
    api_keys = _collect_gemini_api_keys()
    model = os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    if not api_keys:
        return _empty_gemini_result(0)

    prompt = _build_gemini_prompt(question, context, explanation, matched_topic)
    model_path = model if model.startswith("models/") else f"models/{model}"
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 360},
        }
    ).encode("utf-8")

    for index, api_key in enumerate(api_keys, start=1):
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"{urllib.parse.quote(model_path, safe='/')}:generateContent?"
            + urllib.parse.urlencode({"key": api_key})
        )

        try:
            request = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue

        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            continue

        answer = str(text).strip()[:1800]
        if _is_high_quality_gemini_answer(answer, question, matched_topic):
            return {
                "answer": answer,
                "attempted_key_count": index,
                "successful_key_index": index,
            }

    return _empty_gemini_result(len(api_keys))


def _empty_gemini_result(attempted_key_count):
    return {
        "answer": "",
        "attempted_key_count": attempted_key_count,
        "successful_key_index": None,
    }


def _collect_gemini_api_keys():
    keys = []
    seen = set()

    def add_key(value):
        cleaned = _clean_gemini_key(value)
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        keys.append(cleaned)

    add_key(os.environ.get("GEMINI_API_KEY"))
    add_key(os.environ.get("GOOGLE_API_KEY"))
    for key in _split_gemini_keys(os.environ.get("GEMINI_API_KEYS")):
        add_key(key)
    for key in _read_gemini_keys_local():
        add_key(key)

    return keys


def _split_gemini_keys(value):
    if not value:
        return []
    return [part.strip() for part in str(value).split(",")]


def _read_gemini_keys_local():
    if not GEMINI_KEYS_LOCAL_PATH.is_file():
        return []

    try:
        lines = GEMINI_KEYS_LOCAL_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    keys = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            keys.append(stripped)
    return keys


def _clean_gemini_key(value):
    if value is None:
        return ""

    key = str(value).strip().strip("'\"")
    if not key:
        return ""

    if key.lower() in PLACEHOLDER_GEMINI_KEYS:
        return ""

    return key


def _is_high_quality_gemini_answer(answer, question, matched_topic):
    text = " ".join(str(answer or "").split())
    if not text:
        return False

    lowered = text.lower()
    is_explanation = matched_topic in {
        "result_explanation",
        "prediction_overview",
        "score_meaning",
        "directional_predictions",
        "model_used",
    } or _has_any(_normalize(question), ["explain", "why", "score", "mean", "result", "model", "direction"])

    if is_explanation and len(text) < 80:
        return False

    if text.count("|") >= 4 or "---" in text:
        return False

    if text[-1] in {",", ":", ";"}:
        return False

    suspicious_endings = (" and", " or", " because", " with", " for", " to", "the")
    if lowered.endswith(suspicious_endings):
        return False

    sentence_markers = sum(text.count(marker) for marker in (".", "?", "!"))
    if is_explanation and sentence_markers < 2:
        return False

    first_alpha = next((char for char in text if char.isalpha()), "")
    if first_alpha and first_alpha.islower() and is_explanation:
        return False

    if is_explanation and not any(term in lowered for term in ("clinical", "advice", "screening", "biological proof")):
        return False

    return True


def _build_gemini_prompt(question, context, explanation, matched_topic):
    contributors = _feature_context_answer(explanation) if explanation else ""
    return (
        "You are the SynergyLens Prediction Assistant. Only explain the supplied prediction context. "
        "Answer in clear, complete, project-specific language for a student/demo user. Do not start mid-sentence. "
        "Do not return incomplete fragments. Prefer 5 to 8 clear sentences unless the user asks for more detail. "
        "Do not use markdown tables, raw table pipes, or bold markers. Do not overuse markdown. "
        "Do not invent biology, do not claim biological proof, and do not give clinical or treatment advice. "
        "When relevant, use this plain-text structure: Result meaning; Why this label; Model context; What to check next; Safety. "
        "Mention Explain AI/XAI, molecule structures, and experimental validation when discussing next checks.\n\n"
        f"Question: {question}\n"
        f"Matched topic: {matched_topic}\n"
        f"NSC1: {context['nsc1']}\n"
        f"NSC2: {context['nsc2']}\n"
        f"Cell line: {context['cell_line']}\n"
        f"Forward prediction NSC1 -> NSC2: {_format_score(context['forward'])}\n"
        f"Reverse prediction NSC2 -> NSC1: {_format_score(context['reverse'])}\n"
        f"Final ComboScore: {_format_score(context['score'])}\n"
        f"Label: {context['label']}\n"
        f"Model used: {context['model_used']}\n"
        "ComboScore convention: positive = synergy, near zero = neutral/additive, negative = antagonism.\n"
        f"XAI context: {contributors or 'No XAI contributor context was supplied.'}\n"
        f"Safety note to include: {SAFETY_NOTE}"
    )


def _prediction_suggestions_for_topic(topic):
    topic_suggestions = {
        "model_used": ["Explain this result", "Why predict both directions?", "What should I check next?"],
        "directional_predictions": ["What does this score mean?", "What model was used?", "Is this clinical advice?"],
        "feature_contributors_missing": ["What is Explain AI?", "What should I check next?", "Can I trust this result?"],
        "feature_contributors": ["Explain this result", "What should I check next?", "Is this clinical advice?"],
        "safety": ["Explain this result", "What does this score mean?", "What should I check next?"],
    }
    return topic_suggestions.get(topic, PREDICTION_SUGGESTED_QUESTIONS)


def _format_score(value):
    if value is None:
        return "not available"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _suggestions_for_topic(topic):
    topic_suggestions = {
        "project_overview": PROJECT_TOPIC_SUGGESTIONS["basics"],
        "project_purpose": PROJECT_TOPIC_SUGGESTIONS["basics"],
        "dataset": ["What is ComboScore?", "How many drugs are available?", "How does prediction work?"],
        "comboscore": ["What does synergistic mean?", "What does antagonistic mean?", "What thresholds are used for labels?"],
        "synergy": ["What is ComboScore?", "What does neutral mean?", "Can I trust the prediction?"],
        "antagonism": ["What is ComboScore?", "What does neutral mean?", "Is this clinical advice?"],
        "neutral": ["What is ComboScore?", "What thresholds are used for labels?", "How does prediction work?"],
        "prediction_flow": PROJECT_TOPIC_SUGGESTIONS["prediction"],
        "prediction_inputs": ["What is NSC?", "How many cell lines are available?", "How does prediction work?"],
        "directional_average": ["How does prediction work?", "What are 263 and 526 features?", "Can I trust the prediction?"],
        "label_thresholds": ["What is ComboScore?", "What does synergistic mean?", "What does antagonistic mean?"],
        "models": PROJECT_TOPIC_SUGGESTIONS["backend"],
        "model_selection": ["What is the model registry?", "Are models cell-line specific?", "How does prediction work?"],
        "model_registry": ["What model was used?", "What is Step 6 model?", "What files does the backend use?"],
        "step6_models": ["What is the model registry?", "What models are used?", "Are models cell-line specific?"],
        "feature_vector": ["How does prediction work?", "What files does the backend use?", "What is XAI?"],
        "feature_names": ["What is XAI?", "How do I read XAI results?", "Can XAI prove the biological mechanism?"],
        "backend_assets": PROJECT_TOPIC_SUGGESTIONS["backend"],
        "project_counts": ["How many drugs are available?", "How many cell lines are available?", "What are 263 and 526 features?"],
        "nsc": ["What CSV format is required?", "How does prediction work?", "What is Molecule Lookup?"],
        "explain_ai": PROJECT_TOPIC_SUGGESTIONS["xai"],
        "xai_direction": PROJECT_TOPIC_SUGGESTIONS["xai"],
        "xai_limits": ["What is XAI?", "What should be validated experimentally?", "Can I trust the prediction?"],
        "batch_csv_format": PROJECT_TOPIC_SUGGESTIONS["batch"],
        "batch_prediction": PROJECT_TOPIC_SUGGESTIONS["batch"],
        "batch_row_status": ["What CSV format is required?", "What is batch prediction?", "How do I download batch results?"],
        "batch_download": ["What is batch prediction?", "What CSV format is required?", "Why did a batch row fail?"],
        "molecule_lookup": PROJECT_TOPIC_SUGGESTIONS["molecules"],
        "safety": PROJECT_TOPIC_SUGGESTIONS["safety"],
        "trust_and_limitations": ["What should be validated experimentally?", "What is XAI?", "Is this clinical advice?"],
        "experimental_validation": ["Can I trust the prediction?", "Can XAI prove the biological mechanism?", "What should I check next after prediction?"],
        "next_checks": ["Can I trust the prediction?", "What should be validated experimentally?", "What is Explain AI?"],
        "limitations": PROJECT_TOPIC_SUGGESTIONS["safety"],
    }
    return topic_suggestions.get(topic, DEFAULT_SUGGESTED_QUESTIONS)


def _normalize(value):
    return " ".join(str(value or "").lower().strip().split())


def _has_any(text, keywords):
    return any(keyword in text for keyword in keywords)
