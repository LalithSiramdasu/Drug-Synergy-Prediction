import pandas as pd

from backend import config
from backend.services.data_loader import build_health_report, load_model_registry


AVERAGE_PERFORMANCE_PATH = config.RESULTS_DIR / "step5_average_model_performance.csv"
FINAL_MODEL_SUMMARY_PATH = config.RESULTS_DIR / "step6_final_model_summary.csv"


def _round_float(value, digits=4):
    if pd.isna(value):
        return None
    return round(float(value), digits)


def _model_counts(errors):
    try:
        registry = load_model_registry()
    except Exception as exc:
        errors.append(f"Failed to load final model registry: {exc}")
        return {
            "model_types": [],
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
        "model_types": list(count_per_model_type.keys()),
        "count_per_model_type": count_per_model_type,
        "total_models": int(counts.sum()),
    }


def _average_performance_by_model(warnings):
    if not AVERAGE_PERFORMANCE_PATH.is_file():
        warnings.append("results/step5_average_model_performance.csv was not found.")
        return []

    try:
        frame = pd.read_csv(AVERAGE_PERFORMANCE_PATH)
    except Exception as exc:
        warnings.append(f"Failed to read step5_average_model_performance.csv: {exc}")
        return []

    required_columns = {
        "model",
        "mean_r2_score",
        "mean_pearson_rp",
        "mean_rmse",
        "mean_mae",
    }
    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        warnings.append(
            "step5_average_model_performance.csv is missing columns: "
            + ", ".join(missing_columns)
        )
        return []

    rows = []
    for _index, row in frame.iterrows():
        rows.append(
            {
                "model": str(row["model"]),
                "mean_r2_score": _round_float(row["mean_r2_score"]),
                "mean_pearson_rp": _round_float(row["mean_pearson_rp"]),
                "mean_rmse": _round_float(row["mean_rmse"], 3),
                "mean_mae": _round_float(row["mean_mae"], 3),
            }
        )
    return rows


def _deployed_final_average(warnings):
    if not FINAL_MODEL_SUMMARY_PATH.is_file():
        warnings.append("results/step6_final_model_summary.csv was not found.")
        return {}

    try:
        frame = pd.read_csv(FINAL_MODEL_SUMMARY_PATH)
    except Exception as exc:
        warnings.append(f"Failed to read step6_final_model_summary.csv: {exc}")
        return {}

    required_columns = {
        "step5_r2_score",
        "step5_pearson_rp",
        "step5_rmse",
        "step5_mae",
    }
    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        warnings.append(
            "step6_final_model_summary.csv is missing columns: "
            + ", ".join(missing_columns)
        )
        return {}

    return {
        "source": "results/step6_final_model_summary.csv",
        "cell_line_count": int(len(frame)),
        "mean_r2_score": _round_float(frame["step5_r2_score"].mean()),
        "mean_pearson_rp": _round_float(frame["step5_pearson_rp"].mean()),
        "mean_rmse": _round_float(frame["step5_rmse"].mean(), 3),
        "mean_mae": _round_float(frame["step5_mae"].mean(), 3),
    }


def build_model_performance_summary():
    health = build_health_report()
    errors = list(health.get("errors", []))
    warnings = []
    model_summary = _model_counts(errors)

    status = "success" if health.get("status") == "success" and not errors else "error"

    return {
        "status": status,
        "assets": {
            "total_cell_lines": health.get("available_cell_lines"),
            "total_drugs": health.get("available_drugs"),
            "feature_vector": 526,
            "final_model_count": health.get("model_count"),
            "model_registry_available": bool(health.get("model_registry_exists")),
            "drug_features_available": bool(health.get("drug_features_exists")),
        },
        "model_summary": model_summary,
        "performance": {
            "source": "results/step5_average_model_performance.csv",
            "by_model_type": _average_performance_by_model(warnings),
            "deployed_final_average": _deployed_final_average(warnings),
        },
        "explanation": (
            "For each cell line, multiple models were compared. The best model per "
            "cell line was selected using test-set evaluation, and final Step 6 "
            "models were trained for deployment."
        ),
        "comboscore_convention": {
            "positive": "synergistic",
            "near_zero": "neutral/additive",
            "negative": "antagonistic",
        },
        "errors": errors,
        "warnings": warnings,
    }
