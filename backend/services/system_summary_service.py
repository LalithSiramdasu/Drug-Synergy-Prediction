from backend import config
from backend.services.data_loader import build_health_report, load_model_registry
from backend.services.prediction_service import NEUTRAL_THRESHOLD


SAFETY_NOTE = (
    "This is a machine-learning screening prediction, not biological proof or clinical advice."
)


def _model_type_summary(errors):
    try:
        registry = load_model_registry()
    except Exception as exc:
        errors.append(f"Failed to summarize model registry: {exc}")
        return {
            "model_types_present": [],
            "count_per_model_type": {},
            "total_models": 0,
        }

    counts = (
        registry["selected_model"]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
        .sort_index()
    )
    count_per_model_type = {
        model_type: int(count)
        for model_type, count in counts.items()
    }

    return {
        "model_types_present": list(count_per_model_type.keys()),
        "count_per_model_type": count_per_model_type,
        "total_models": int(counts.sum()),
    }


def build_system_summary():
    health = build_health_report()
    errors = list(health.get("errors", []))
    model_summary = _model_type_summary(errors)

    status = "success" if health.get("status") == "success" and not errors else "error"

    return {
        "status": status,
        "project": {
            "name": "SynergyLens",
            "purpose": "NCI ALMANAC ComboScore prediction",
            "mode": "Flask backend with saved ML models",
        },
        "assets": {
            "available_drugs": health.get("available_drugs"),
            "available_cell_lines": health.get("available_cell_lines"),
            "feature_column_count": health.get("feature_column_count"),
            "final_model_count": health.get("model_count"),
            "model_registry_available": bool(health.get("model_registry_exists")),
            "drug_features_available": bool(health.get("drug_features_exists")),
        },
        "model_summary": model_summary,
        "comboscore_convention": {
            "formula": "ComboScore = Expected growth - Observed percent growth",
            "positive": "synergistic",
            "near_zero": "neutral/additive",
            "negative": "antagonistic",
            "thresholds": {
                "synergistic": f"score >= {NEUTRAL_THRESHOLD}",
                "neutral": f"-{NEUTRAL_THRESHOLD} < score < {NEUTRAL_THRESHOLD}",
                "antagonistic": f"score <= -{NEUTRAL_THRESHOLD}",
                "neutral_threshold": NEUTRAL_THRESHOLD,
            },
        },
        "prediction_flow": [
            "validate NSC1, NSC2, CELLNAME",
            "load drug features",
            "build 526 feature vector",
            "select best model for cell line",
            "predict NSC1 -> NSC2",
            "predict NSC2 -> NSC1",
            "average final ComboScore",
            "assign label",
        ],
        "safety_note": SAFETY_NOTE,
        "errors": errors,
        "expected_assets": {
            "available_drugs": config.EXPECTED_DRUG_COUNT,
            "available_cell_lines": config.EXPECTED_CELL_LINE_COUNT,
            "feature_column_count": 526,
            "final_model_count": config.EXPECTED_MODEL_COUNT,
        },
    }
