from datetime import datetime
from pathlib import Path

import pandas as pd
from werkzeug.utils import secure_filename

from backend import config
from backend.services.prediction_service import PredictionError, predict_single


class BatchPredictionError(Exception):
    pass


REQUIRED_COLUMNS = ["NSC1", "NSC2", "CELLNAME"]
OUTPUT_COLUMNS = [
    "row_index",
    "NSC1",
    "NSC2",
    "CELLNAME",
    "status",
    "error",
    "model_used",
    "model_path",
    "prediction_NSC1_to_NSC2",
    "prediction_NSC2_to_NSC1",
    "final_predicted_COMBOSCORE",
    "label",
    "explanation",
]


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _clean_uploaded_filename(filename):
    safe_name = secure_filename(filename or "")
    if not safe_name:
        raise BatchPredictionError("Uploaded file must have a valid filename.")
    if Path(safe_name).suffix.lower() != ".csv":
        raise BatchPredictionError("Uploaded file must be a CSV file.")
    return safe_name


def _ensure_runtime_dirs():
    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload(uploaded_file):
    safe_name = _clean_uploaded_filename(uploaded_file.filename)
    _ensure_runtime_dirs()
    upload_name = f"batch_upload_{_timestamp()}_{safe_name}"
    upload_path = config.UPLOADS_DIR / upload_name
    uploaded_file.save(upload_path)
    return upload_path


def _validate_input_columns(frame):
    actual_columns = list(frame.columns)
    if actual_columns != REQUIRED_COLUMNS:
        raise BatchPredictionError(
            "CSV columns must be exactly: NSC1, NSC2, CELLNAME."
        )


def _row_value(row, column):
    value = row[column]
    if pd.isna(value):
        return None
    return value


def _success_output(row_index, result):
    prediction_input = result["input"]
    return {
        "row_index": row_index,
        "NSC1": prediction_input["NSC1"],
        "NSC2": prediction_input["NSC2"],
        "CELLNAME": prediction_input["CELLNAME"],
        "status": "success",
        "error": "",
        "model_used": result["model_used"],
        "model_path": result["model_path"],
        "prediction_NSC1_to_NSC2": result["prediction_NSC1_to_NSC2"],
        "prediction_NSC2_to_NSC1": result["prediction_NSC2_to_NSC1"],
        "final_predicted_COMBOSCORE": result["final_predicted_COMBOSCORE"],
        "label": result["label"],
        "explanation": result["explanation"],
    }


def _error_output(row_index, row, error):
    return {
        "row_index": row_index,
        "NSC1": _row_value(row, "NSC1"),
        "NSC2": _row_value(row, "NSC2"),
        "CELLNAME": _row_value(row, "CELLNAME"),
        "status": "error",
        "error": error,
        "model_used": "",
        "model_path": "",
        "prediction_NSC1_to_NSC2": "",
        "prediction_NSC2_to_NSC1": "",
        "final_predicted_COMBOSCORE": "",
        "label": "",
        "explanation": "",
    }


def run_batch_prediction(uploaded_file):
    if uploaded_file is None:
        raise BatchPredictionError("No file uploaded.")

    upload_path = _save_upload(uploaded_file)

    try:
        input_frame = pd.read_csv(upload_path)
    except Exception as exc:
        raise BatchPredictionError(f"Failed to read uploaded CSV: {exc}")

    _validate_input_columns(input_frame)

    output_rows = []
    for row_index, row in input_frame.iterrows():
        payload = {
            "NSC1": _row_value(row, "NSC1"),
            "NSC2": _row_value(row, "NSC2"),
            "CELLNAME": _row_value(row, "CELLNAME"),
        }
        try:
            result = predict_single(payload)
            output_rows.append(_success_output(int(row_index), result))
        except PredictionError as exc:
            output_rows.append(_error_output(int(row_index), row, str(exc)))
        except Exception as exc:
            output_rows.append(_error_output(int(row_index), row, f"Unexpected row error: {exc}"))

    output_frame = pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS)
    output_name = f"batch_prediction_{_timestamp()}.csv"
    output_path = config.OUTPUTS_DIR / output_name
    output_frame.to_csv(output_path, index=False)

    successful_rows = int((output_frame["status"] == "success").sum())
    failed_rows = int((output_frame["status"] == "error").sum())

    return {
        "status": "success",
        "message": "Batch prediction complete",
        "total_rows": int(len(output_frame)),
        "successful_rows": successful_rows,
        "failed_rows": failed_rows,
        "uploaded_file": f"uploads/{upload_path.name}",
        "output_file": f"outputs/{output_path.name}",
        "preview": output_frame.head(5).to_dict(orient="records"),
    }
