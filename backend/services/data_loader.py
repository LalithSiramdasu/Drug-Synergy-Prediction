import json
from functools import lru_cache

import pandas as pd

from backend import config


def _add_error(errors, message):
    errors.append(message)


def _count_unique_values(frame, column_name):
    if column_name not in frame.columns:
        raise ValueError(f"Required column {column_name} was not found.")
    return int(frame[column_name].dropna().astype(str).str.strip().nunique())


@lru_cache(maxsize=1)
def load_drug_features():
    drug_features = pd.read_csv(config.DRUG_FEATURES_PATH)
    if "NSC" not in drug_features.columns:
        raise ValueError("Required column NSC was not found.")
    drug_features["NSC"] = pd.to_numeric(drug_features["NSC"], errors="raise").astype(int)
    return drug_features


@lru_cache(maxsize=1)
def load_feature_columns():
    with config.FEATURE_COLUMNS_PATH.open("r", encoding="utf-8") as handle:
        feature_columns = json.load(handle)
    if not isinstance(feature_columns, list):
        raise ValueError("Feature columns JSON must contain a list.")
    return feature_columns


@lru_cache(maxsize=1)
def load_model_registry():
    model_registry = pd.read_csv(config.MODEL_REGISTRY_PATH)
    required_columns = {"cell_line", "safe_cell_line", "selected_model", "model_path"}
    missing_columns = sorted(required_columns.difference(model_registry.columns))
    if missing_columns:
        raise ValueError(f"Model registry is missing required columns: {', '.join(missing_columns)}.")
    model_registry["cell_line"] = model_registry["cell_line"].astype(str).str.strip()
    model_registry["selected_model"] = model_registry["selected_model"].astype(str).str.strip()
    return model_registry


def get_available_drugs():
    drug_features = load_drug_features()
    return sorted(drug_features["NSC"].dropna().astype(int).unique().tolist())


def get_available_cell_lines():
    model_registry = load_model_registry()
    return sorted(model_registry["cell_line"].dropna().astype(str).unique().tolist())


def build_health_report():
    errors = []

    drug_features_exists = config.DRUG_FEATURES_PATH.is_file()
    feature_columns_exists = config.FEATURE_COLUMNS_PATH.is_file()
    model_registry_exists = config.MODEL_REGISTRY_PATH.is_file()
    models_dir_exists = config.MODELS_DIR.is_dir()

    model_files = []
    if models_dir_exists:
        model_files = sorted(config.MODELS_DIR.glob("final_step6_*.pkl"))
    model_count = len(model_files)

    drug_features_loaded = False
    feature_columns_loaded = False
    model_registry_loaded = False
    available_drugs = None
    available_cell_lines = None
    feature_column_count = None

    if drug_features_exists:
        try:
            drug_features = load_drug_features()
            available_drugs = _count_unique_values(drug_features, "NSC")
            drug_features_loaded = True
        except Exception as exc:
            _add_error(errors, f"Failed to load drug_features.csv: {exc}")
    else:
        _add_error(errors, "data/drug_features.csv was not found.")

    if feature_columns_exists:
        try:
            feature_columns = load_feature_columns()
            feature_column_count = len(feature_columns)
            feature_columns_loaded = True
        except Exception as exc:
            _add_error(errors, f"Failed to load step6_final_model_feature_columns.json: {exc}")
    else:
        _add_error(errors, "data/step6_final_model_feature_columns.json was not found.")

    if model_registry_exists:
        try:
            model_registry = load_model_registry()
            available_cell_lines = _count_unique_values(model_registry, "cell_line")
            model_registry_loaded = True
        except Exception as exc:
            _add_error(errors, f"Failed to load step6_final_model_registry.csv: {exc}")
    else:
        _add_error(errors, "results/step6_final_model_registry.csv was not found.")

    model_count_ok = model_count == config.EXPECTED_MODEL_COUNT
    available_drugs_ok = available_drugs == config.EXPECTED_DRUG_COUNT
    available_cell_lines_ok = available_cell_lines == config.EXPECTED_CELL_LINE_COUNT

    if not models_dir_exists:
        _add_error(errors, "models folder was not found.")
    elif not model_count_ok:
        _add_error(
            errors,
            f"Expected {config.EXPECTED_MODEL_COUNT} final_step6_*.pkl model files, found {model_count}.",
        )

    if drug_features_loaded and not available_drugs_ok:
        _add_error(
            errors,
            f"Expected {config.EXPECTED_DRUG_COUNT} available drugs, found {available_drugs}.",
        )

    if model_registry_loaded and not available_cell_lines_ok:
        _add_error(
            errors,
            f"Expected {config.EXPECTED_CELL_LINE_COUNT} available cell lines, found {available_cell_lines}.",
        )

    checks = {
        "drug_features_exists": drug_features_exists,
        "feature_columns_exists": feature_columns_exists,
        "model_registry_exists": model_registry_exists,
        "models_dir_exists": models_dir_exists,
        "model_count_ok": model_count_ok,
        "drug_features_loaded": drug_features_loaded,
        "feature_columns_loaded": feature_columns_loaded,
        "model_registry_loaded": model_registry_loaded,
        "available_drugs_ok": available_drugs_ok,
        "available_cell_lines_ok": available_cell_lines_ok,
    }

    status = "success" if all(checks.values()) else "error"

    return {
        "status": status,
        "message": "Backend is ready" if status == "success" else "Backend health check failed",
        "drug_features_exists": drug_features_exists,
        "feature_columns_exists": feature_columns_exists,
        "model_registry_exists": model_registry_exists,
        "models_dir_exists": models_dir_exists,
        "model_count": model_count,
        "expected_model_count": config.EXPECTED_MODEL_COUNT,
        "drug_features_loaded": drug_features_loaded,
        "feature_columns_loaded": feature_columns_loaded,
        "feature_column_count": feature_column_count,
        "model_registry_loaded": model_registry_loaded,
        "available_drugs": available_drugs,
        "expected_available_drugs": config.EXPECTED_DRUG_COUNT,
        "available_cell_lines": available_cell_lines,
        "expected_available_cell_lines": config.EXPECTED_CELL_LINE_COUNT,
        "checks": checks,
        "errors": errors,
    }
