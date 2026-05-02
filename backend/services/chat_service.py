from backend.services.model_performance_service import build_model_performance_summary
from backend.services.system_summary_service import build_system_summary


SAFETY_NOTE = (
    "This is a machine-learning screening prediction, not biological proof or clinical advice."
)

DEFAULT_SUGGESTED_QUESTIONS = [
    "What is ComboScore?",
    "How does prediction work?",
    "What does synergistic mean?",
    "Is this clinical advice?",
    "What is Explain AI?",
    "What CSV format is required?",
]


class ChatServiceError(Exception):
    pass


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
            "prediction_aware_not_available",
            "The Project Assistant can explain general ComboScore and synergy meaning. Run a prediction first; the prediction-aware assistant will be added in the next step.",
        )

    if _has_any(text, ["clinical", "medical", "advice", "doctor", "patient", "treatment", "therapy"]):
        return (
            "safety",
            "No. SynergyLens is an ML screening and education demo. It is not biological proof, not clinical advice, and not a treatment recommendation. Promising synergy predictions should be validated experimentally.",
        )

    if _has_any(text, ["csv", "batch format", "upload format", "batch input", "sample csv"]):
        return (
            "batch_csv_format",
            "Batch prediction needs a CSV with exactly these columns: NSC1, NSC2, CELLNAME. Example rows are: 740,750,786-0; 740,752,A498; and 750,755,A549/ATCC. Each row is validated and predicted independently.",
        )

    if _has_any(text, ["batch", "bulk", "many rows", "multiple predictions"]):
        return (
            "batch_prediction",
            "Batch prediction lets you upload a CSV of drug pairs and cell lines. The backend runs the same single-prediction flow row by row, records row-level success or error, and returns a preview plus a downloadable output CSV.",
        )

    if _has_any(text, ["shap", "explain ai", "explainable", "feature contribution", "contributors"]):
        return (
            "explain_ai",
            "Explain AI uses SHAP-style feature contributions to describe which input features pushed the ComboScore upward or downward. Positive SHAP values push the ComboScore upward toward synergy, while negative SHAP values pull it downward toward antagonism.",
        )

    if _has_any(text, ["model", "algorithm", "randomforest", "xgboost", "catboost", "lightgbm"]):
        return ("models", _model_answer(context))

    if _has_any(text, ["why", "reverse", "both orders", "nsc1 to nsc2", "nsc2 to nsc1", "order"]):
        return (
            "directional_average",
            "The feature vector is order-sensitive because Drug 1 features and Drug 2 features occupy different columns. The combination itself should be interpreted symmetrically, so SynergyLens predicts NSC1 -> NSC2 and NSC2 -> NSC1, then averages both values into the final ComboScore.",
        )

    if _has_any(text, ["how does prediction", "prediction work", "flow", "pipeline", "predict"]):
        return (
            "prediction_flow",
            f"Prediction starts by validating NSC1, NSC2, and CELLNAME. The backend loads 263 features for each drug, builds a {context['feature_column_count']}-feature pair vector, selects the best saved model for the chosen cell line, predicts both drug orders, averages the two ComboScores, and labels the result.",
        )

    if _has_any(text, ["asset", "file", "backend use", "backend uses", "registry", "feature columns"]):
        return (
            "backend_assets",
            "The backend uses data/drug_features.csv for drug features, data/step6_final_model_feature_columns.json for the exact 526-feature order, results/step6_final_model_registry.csv for automatic model selection, models/final_step6_*.pkl for saved models, and molecule assets for structure rendering.",
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
            f"SynergyLens is a Flask app for NCI ALMANAC ComboScore prediction. It lets users select two valid NSC drugs and one cell line, then uses saved ML models to predict drug-combination interaction. The deployed project includes {context['available_drugs']} drugs, {context['available_cell_lines']} cell lines, and {context['final_model_count']} final models.",
        )

    if _has_any(text, ["synergistic", "synergy", "positive"]):
        return (
            "synergy",
            "Synergistic means the predicted ComboScore is positive enough to suggest stronger-than-expected inhibition for the selected drug pair and cell line. In this project, positive ComboScore points toward synergy.",
        )

    if _has_any(text, ["antagonistic", "antagonism", "negative"]):
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
            "ComboScore = Expected growth - Observed percent growth. Positive ComboScore suggests synergy, near-zero ComboScore suggests neutral or additive behavior, and negative ComboScore suggests antagonism.",
        )

    return (
        "fallback",
        "I can answer general SynergyLens project questions about ComboScore, NSC IDs, available drugs and cell lines, prediction flow, model types, SHAP Explain AI, batch CSV format, backend assets, and safety limitations.",
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


def _suggestions_for_topic(topic):
    topic_suggestions = {
        "comboscore": ["What does synergistic mean?", "What does antagonistic mean?", "Is this clinical advice?"],
        "prediction_flow": ["Why predict both drug orders?", "What models are used?", "What files does the backend use?"],
        "models": ["How does prediction work?", "What is Explain AI?", "How many cell lines are available?"],
        "batch_csv_format": ["What is batch prediction?", "How does prediction work?", "What is NSC?"],
        "safety": ["What is ComboScore?", "What does synergistic mean?", "What is Explain AI?"],
    }
    return topic_suggestions.get(topic, DEFAULT_SUGGESTED_QUESTIONS)


def _normalize(value):
    return " ".join(str(value or "").lower().strip().split())


def _has_any(text, keywords):
    return any(keyword in text for keyword in keywords)
