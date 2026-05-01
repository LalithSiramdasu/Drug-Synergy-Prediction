from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

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
