import pandas as pd

from backend import config
from backend.services.prediction_service import _label_prediction


class DemoCaseError(Exception):
    pass


DEMO_CASES_PATH = config.PREDICTIONS_DIR / "step5_best_model_test_predictions.csv"
REQUIRED_COLUMNS = {"NSC1", "NSC2", "CELLNAME", "predicted_comboscore"}


def _load_demo_predictions():
    if not DEMO_CASES_PATH.is_file():
        raise DemoCaseError("predictions/step5_best_model_test_predictions.csv was not found.")

    try:
        predictions = pd.read_csv(DEMO_CASES_PATH)
    except Exception as exc:
        raise DemoCaseError(f"Failed to load step5_best_model_test_predictions.csv: {exc}")

    missing_columns = sorted(REQUIRED_COLUMNS.difference(predictions.columns))
    if missing_columns:
        raise DemoCaseError(f"Demo prediction file is missing required columns: {', '.join(missing_columns)}.")

    predictions["predicted_comboscore"] = pd.to_numeric(
        predictions["predicted_comboscore"],
        errors="coerce",
    )
    predictions = predictions.dropna(subset=["predicted_comboscore"])
    if predictions.empty:
        raise DemoCaseError("Demo prediction file has no valid predicted_comboscore values.")

    return predictions


def _optional_value(row, column):
    if column not in row.index or pd.isna(row[column]):
        return None
    value = row[column]
    if hasattr(value, "item"):
        return value.item()
    return value


def _make_demo_record(case_type, description, row):
    predicted_score = float(row["predicted_comboscore"])
    label, _explanation = _label_prediction(predicted_score)
    return {
        "case_type": case_type,
        "description": description,
        "NSC1": int(row["NSC1"]),
        "NSC2": int(row["NSC2"]),
        "CELLNAME": str(row["CELLNAME"]),
        "predicted_comboscore": predicted_score,
        "actual_comboscore": _optional_value(row, "actual_comboscore"),
        "model": _optional_value(row, "model"),
        "label": label,
    }


def get_demo_cases():
    predictions = _load_demo_predictions()

    strong_synergy_row = predictions.loc[predictions["predicted_comboscore"].idxmax()]
    neutral_row = predictions.loc[predictions["predicted_comboscore"].abs().idxmin()]
    antagonism_row = predictions.loc[predictions["predicted_comboscore"].idxmin()]

    demo_cases = [
        _make_demo_record(
            "strong_synergy",
            "Most positive predicted ComboScore in the saved Step 5 test predictions.",
            strong_synergy_row,
        ),
        _make_demo_record(
            "neutral",
            "Predicted ComboScore closest to zero in the saved Step 5 test predictions.",
            neutral_row,
        ),
        _make_demo_record(
            "antagonism",
            "Most negative predicted ComboScore in the saved Step 5 test predictions.",
            antagonism_row,
        ),
    ]

    return {
        "status": "success",
        "count": len(demo_cases),
        "demo_cases": demo_cases,
    }
