from functools import lru_cache
from pathlib import Path

import joblib

from backend import config
from backend.services.data_loader import load_model_registry


class ModelLoaderError(Exception):
    pass


def _relative_model_path(model_filename):
    return (Path("models") / model_filename).as_posix()


def get_model_info(cell_line):
    requested_cell_line = str(cell_line).strip()
    if not requested_cell_line:
        raise ModelLoaderError("CELLNAME is required.")

    registry = load_model_registry()
    matches = registry[registry["cell_line"] == requested_cell_line]
    if matches.empty:
        raise ModelLoaderError(
            f"Cell line {requested_cell_line} not found in results/step6_final_model_registry.csv."
        )

    row = matches.iloc[0]
    registry_model_path = str(row["model_path"]).strip()
    model_filename = Path(registry_model_path).name
    if not model_filename:
        raise ModelLoaderError(f"Model path for cell line {requested_cell_line} is empty.")

    local_model_path = config.MODELS_DIR / model_filename
    return {
        "cell_line": requested_cell_line,
        "safe_cell_line": str(row["safe_cell_line"]),
        "model_name": str(row["selected_model"]),
        "model_path": _relative_model_path(model_filename),
        "local_model_path": local_model_path,
        "model_file_exists": local_model_path.is_file(),
    }


@lru_cache(maxsize=None)
def _load_model_from_path(local_model_path):
    try:
        model = joblib.load(local_model_path)
    except ModuleNotFoundError as exc:
        package_name = exc.name or "a required model package"
        raise ModelLoaderError(
            f"Model dependency {package_name} is not installed. Install the packages in requirements.txt before prediction."
        ) from exc
    except Exception as exc:
        raise ModelLoaderError(f"Failed to load model file {local_model_path}: {exc}") from exc
    return _normalize_loaded_model(model)


def _normalize_loaded_model(model):
    """Apply non-training compatibility fixes for older serialized estimators.

    Some final RandomForest models were saved with scikit-learn 1.3.x. In
    scikit-learn 1.7.x, DecisionTreeRegressor prediction checks expect a
    monotonic_cst attribute. The old pickles do not have it, so we attach the
    default value used for unconstrained trees. This does not retrain or modify
    the model file; it only makes the in-memory object compatible with runtime
    prediction.
    """
    for estimator in getattr(model, "estimators_", []):
        if not hasattr(estimator, "monotonic_cst"):
            estimator.monotonic_cst = None
    if hasattr(model, "estimators_") and hasattr(model, "n_jobs"):
        model.n_jobs = 1
    return model


def load_model_for_cell_line(cell_line):
    model_info = get_model_info(cell_line)
    local_model_path = model_info["local_model_path"]
    if not model_info["model_file_exists"]:
        raise ModelLoaderError(
            f"Model file for cell line {model_info['cell_line']} was not found: {model_info['model_path']}."
        )

    model = _load_model_from_path(str(local_model_path))
    return model, model_info
