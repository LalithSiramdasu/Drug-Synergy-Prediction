from pathlib import Path
import shutil
import json


# ============================================================
# COPY FINAL TRAINING ASSETS INTO FLASK APP
# ============================================================

# Change these only if your folder names are different
TRAINING_PROJECT_DIR = Path(r"C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v3")
OLD_SOURCE_DATA_DIR = Path(r"C:\Users\HP\Desktop\SDP 27 april\nci_almanac_v2\data")
FLASK_APP_DIR = Path(r"C:\Users\HP\Desktop\SDP 27 april\NCI_ALMANAC_FLASK_APP")


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def make_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dst: Path, required=True):
    make_dir(dst.parent)

    if src.exists():
        shutil.copy2(src, dst)
        print(f"✅ Copied: {src.name}")
        print(f"   From: {src}")
        print(f"   To  : {dst}\n")
        return True
    else:
        msg = "❌ MISSING REQUIRED" if required else "⚠️ Optional missing"
        print(f"{msg}: {src}\n")
        return False


def copy_folder_files(src_dir: Path, dst_dir: Path, pattern="*", required=True):
    make_dir(dst_dir)

    files = list(src_dir.glob(pattern))

    if not files:
        msg = "❌ NO REQUIRED FILES FOUND" if required else "⚠️ No optional files found"
        print(f"{msg}: {src_dir}\\{pattern}\n")
        return 0

    count = 0
    for src in files:
        if src.is_file():
            dst = dst_dir / src.name
            shutil.copy2(src, dst)
            count += 1

    print(f"✅ Copied {count} file(s)")
    print(f"   From: {src_dir}\\{pattern}")
    print(f"   To  : {dst_dir}\n")
    return count


# ------------------------------------------------------------
# 1. Create required folders
# ------------------------------------------------------------

folders = [
    "backend",
    "backend/routes",
    "backend/services",
    "data",
    "results",
    "models",
    "molecules",
    "final_project_summary",
    "predictions",
    "uploads",
    "outputs",
    "templates",
    "static",
    "static/css",
    "static/js",
]

for folder in folders:
    make_dir(FLASK_APP_DIR / folder)

print("✅ Flask folders checked/created\n")


# ------------------------------------------------------------
# 2. Copy data files
# ------------------------------------------------------------

print("=" * 70)
print("COPYING DATA FILES")
print("=" * 70)

copy_file(
    TRAINING_PROJECT_DIR / "data" / "drug_features.csv",
    FLASK_APP_DIR / "data" / "drug_features.csv",
    required=True
)

copy_file(
    TRAINING_PROJECT_DIR / "data" / "step6_final_model_feature_columns.json",
    FLASK_APP_DIR / "data" / "step6_final_model_feature_columns.json",
    required=True
)

# Optional, useful for gauge/odometer min and max
copy_file(
    TRAINING_PROJECT_DIR / "data" / "model_matrix.csv",
    FLASK_APP_DIR / "data" / "model_matrix.csv",
    required=False
)


# ------------------------------------------------------------
# 3. Copy result files
# ------------------------------------------------------------

print("=" * 70)
print("COPYING RESULTS FILES")
print("=" * 70)

result_files = [
    "step6_final_model_registry.csv",
    "step6_final_model_summary.csv",
    "step5_best_model_per_cellline.csv",
    "step5_average_model_performance.csv",
    "step5_all_cellline_model_comparison.csv",
]

for file_name in result_files:
    copy_file(
        TRAINING_PROJECT_DIR / "results" / file_name,
        FLASK_APP_DIR / "results" / file_name,
        required=(file_name == "step6_final_model_registry.csv")
    )


# ------------------------------------------------------------
# 4. Copy final Step 6 model files
# ------------------------------------------------------------

print("=" * 70)
print("COPYING FINAL MODEL FILES")
print("=" * 70)

model_count = copy_folder_files(
    TRAINING_PROJECT_DIR / "models",
    FLASK_APP_DIR / "models",
    pattern="final_step6_*.pkl",
    required=True
)

print(f"Final Step 6 model files copied: {model_count}")
if model_count != 60:
    print("⚠️ Warning: Expected 60 final model files.")
    print("   Check your nci_almanac_v3/models folder.\n")
else:
    print("✅ Correct: 60 final models copied\n")


# ------------------------------------------------------------
# 5. Copy final_project_summary files
# ------------------------------------------------------------

print("=" * 70)
print("COPYING FINAL PROJECT SUMMARY FILES")
print("=" * 70)

summary_count = copy_folder_files(
    TRAINING_PROJECT_DIR / "final_project_summary",
    FLASK_APP_DIR / "final_project_summary",
    pattern="*",
    required=True
)

print(f"Final project summary files copied: {summary_count}\n")


# ------------------------------------------------------------
# 6. Copy molecule files
# ------------------------------------------------------------

print("=" * 70)
print("COPYING MOLECULE FILES")
print("=" * 70)

copy_file(
    OLD_SOURCE_DATA_DIR / "ComboCompoundSet.sdf",
    FLASK_APP_DIR / "molecules" / "ComboCompoundSet.sdf",
    required=True
)

copy_file(
    OLD_SOURCE_DATA_DIR / "drug_mols.pkl",
    FLASK_APP_DIR / "molecules" / "drug_mols.pkl",
    required=True
)


# ------------------------------------------------------------
# 7. Copy prediction/demo files
# ------------------------------------------------------------

print("=" * 70)
print("COPYING PREDICTION AND DEMO FILES")
print("=" * 70)

prediction_files = [
    "step5_official_test_dataset.csv",
    "step5_best_model_test_predictions.csv",
    "batch_prediction_input.csv",
    "batch_prediction_output.csv",
    "final_model_single_prediction.csv",
]

for file_name in prediction_files:
    copy_file(
        TRAINING_PROJECT_DIR / "predictions" / file_name,
        FLASK_APP_DIR / "predictions" / file_name,
        required=False
    )


# ------------------------------------------------------------
# 8. Create molecule_aliases.json
# ------------------------------------------------------------

print("=" * 70)
print("CREATING BACKEND HELPER FILES")
print("=" * 70)

molecule_aliases = {
    "753082": "761431"
}

alias_file = FLASK_APP_DIR / "backend" / "molecule_aliases.json"
with open(alias_file, "w", encoding="utf-8") as f:
    json.dump(molecule_aliases, f, indent=4)

print("✅ Created molecule_aliases.json")
print(f"   Path: {alias_file}\n")


# ------------------------------------------------------------
# 9. Create empty Python package files
# ------------------------------------------------------------

init_files = [
    FLASK_APP_DIR / "backend" / "__init__.py",
    FLASK_APP_DIR / "backend" / "routes" / "__init__.py",
    FLASK_APP_DIR / "backend" / "services" / "__init__.py",
]

for init_file in init_files:
    init_file.touch(exist_ok=True)
    print(f"✅ Created/checked: {init_file}")

print()


# ------------------------------------------------------------
# 10. Final verification
# ------------------------------------------------------------

print("=" * 70)
print("FINAL VERIFICATION")
print("=" * 70)

required_files = [
    FLASK_APP_DIR / "data" / "drug_features.csv",
    FLASK_APP_DIR / "data" / "step6_final_model_feature_columns.json",
    FLASK_APP_DIR / "results" / "step6_final_model_registry.csv",
    FLASK_APP_DIR / "final_project_summary" / "available_cell_lines.txt",
    FLASK_APP_DIR / "final_project_summary" / "available_drug_nscs.txt",
    FLASK_APP_DIR / "molecules" / "ComboCompoundSet.sdf",
    FLASK_APP_DIR / "molecules" / "drug_mols.pkl",
    FLASK_APP_DIR / "backend" / "molecule_aliases.json",
]

all_ok = True

for file_path in required_files:
    if file_path.exists():
        print(f"✅ FOUND: {file_path}")
    else:
        print(f"❌ MISSING: {file_path}")
        all_ok = False

final_models = list((FLASK_APP_DIR / "models").glob("final_step6_*.pkl"))
print(f"\nFinal model count found in Flask app: {len(final_models)}")

if len(final_models) != 60:
    print("⚠️ Expected 60 final_step6_*.pkl model files.")
    all_ok = False

print("\n" + "=" * 70)

if all_ok:
    print("✅ ALL IMPORTANT FILES ARE READY FOR FLASK BACKEND")
else:
    print("⚠️ SOME FILES ARE MISSING. CHECK THE MESSAGES ABOVE.")

print("=" * 70)

print("\nFlask app folder:")
print(FLASK_APP_DIR)