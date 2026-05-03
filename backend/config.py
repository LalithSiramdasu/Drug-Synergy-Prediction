import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
GEMINI_KEYS_LOCAL_PATH = ROOT_DIR / ".gemini_keys.local"


def _strip_env_quotes(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_local_env(env_path=ENV_PATH):
    # .env is a private local file. It may contain API keys and must stay ignored by Git.
    if not env_path.is_file():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        os.environ[key] = _strip_env_quotes(value)


load_local_env()

DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
RESULTS_DIR = ROOT_DIR / "results"
MOLECULES_DIR = ROOT_DIR / "molecules"
PREDICTIONS_DIR = ROOT_DIR / "predictions"
OUTPUTS_DIR = ROOT_DIR / "outputs"
UPLOADS_DIR = ROOT_DIR / "uploads"

DRUG_FEATURES_PATH = DATA_DIR / "drug_features.csv"
FEATURE_COLUMNS_PATH = DATA_DIR / "step6_final_model_feature_columns.json"
MODEL_REGISTRY_PATH = RESULTS_DIR / "step6_final_model_registry.csv"
DRUG_MOLS_PATH = MOLECULES_DIR / "drug_mols.pkl"
SDF_PATH = MOLECULES_DIR / "ComboCompoundSet.sdf"
MOLECULE_ALIASES_PATH = ROOT_DIR / "backend" / "molecule_aliases.json"

EXPECTED_MODEL_COUNT = 60
EXPECTED_DRUG_COUNT = 100
EXPECTED_CELL_LINE_COUNT = 60
