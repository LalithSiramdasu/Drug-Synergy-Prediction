# NCI ALMANAC Drug Synergy Prediction Flask App

This project is a Flask deployment application for predicting drug-combination
ComboScore values from the NCI ALMANAC workflow. The machine learning training
pipeline has already been completed. This repository only loads prepared data,
loads final trained Step 6 models, validates user input, builds the required
model feature vectors, and returns predictions through a web UI and JSON API.

The app is currently implemented as **SynergyLens**, a Flask backend with a
browser frontend for:

- single drug-pair ComboScore prediction
- automatic cell-line model selection
- forward and reverse drug-order prediction averaging
- batch CSV prediction
- molecule structure rendering with RDKit
- optional SHAP explainability
- demo cases from saved Step 5 test predictions

Verified current project state: **May 1, 2026**.

---

## Table of Contents

1. [Project Goal](#project-goal)
2. [Important Scientific Rules](#important-scientific-rules)
3. [Project Structure](#project-structure)
4. [Required Runtime Assets](#required-runtime-assets)
5. [Data Summary](#data-summary)
6. [Model Summary](#model-summary)
7. [Prediction Data Flow](#prediction-data-flow)
8. [ComboScore Interpretation](#comboscore-interpretation)
9. [Setup](#setup)
10. [Run The App](#run-the-app)
11. [Frontend](#frontend)
12. [API Reference](#api-reference)
13. [Single Prediction Example](#single-prediction-example)
14. [Batch Prediction](#batch-prediction)
15. [Molecule Structures](#molecule-structures)
16. [SHAP Explainability](#shap-explainability)
17. [Demo Cases](#demo-cases)
18. [Results And Evaluation Files](#results-and-evaluation-files)
19. [Validation And Health Checks](#validation-and-health-checks)
20. [Known Implementation Notes](#known-implementation-notes)
21. [Troubleshooting](#troubleshooting)

---

## Project Goal

The app accepts three user inputs:

- `NSC1`: Drug 1 NSC identifier
- `NSC2`: Drug 2 NSC identifier
- `CELLNAME`: NCI cell line name

For valid inputs, the backend:

1. Validates the NSC values and cell line.
2. Loads the 263 prepared features for each drug.
3. Builds a 526-column model input vector.
4. Selects the correct final Step 6 model for the requested cell line.
5. Predicts ComboScore with `NSC1` as Drug 1 and `NSC2` as Drug 2.
6. Predicts ComboScore again with the drug order reversed.
7. Averages both predictions.
8. Returns the final predicted ComboScore with model metadata and explanation.

The app does **not** train or tune models at runtime.

---

## Important Scientific Rules

- The prediction target is `COMBOSCORE`.
- `PercentGrowth` is not used as the deployment target.
- Final deployment models are loaded from `models/`.
- Runtime model selection comes from `results/step6_final_model_registry.csv`.
- Users never manually select RandomForest, XGBoost, CatBoost, or LightGBM.
- Drug-combination prediction is made in both feature orders and averaged.
- Feature order must come from `data/step6_final_model_feature_columns.json`.
- The trained model files and prepared data files should be treated as read-only.
- SHAP is optional and runs only when `/api/explain` is called.

---

## Project Structure

```text
Drug Synergy Prediction/
|-- app.py
|-- requirements.txt
|-- README.md
|-- ACCEPTANCE_TESTS.md
|-- AGENTS.md
|-- BACKEND_FLOW.md
|-- PROJECT_CONTEXT.md
|-- FRONTEND_REPAIR_CONTEXT.md
|-- backend/
|   |-- __init__.py
|   |-- config.py
|   |-- molecule_aliases.json
|   |-- routes/
|   |   |-- __init__.py
|   |   `-- api_routes.py
|   `-- services/
|       |-- __init__.py
|       |-- batch_service.py
|       |-- data_loader.py
|       |-- demo_service.py
|       |-- model_loader.py
|       |-- molecule_service.py
|       |-- prediction_service.py
|       `-- shap_service.py
|-- data/
|   |-- drug_features.csv
|   |-- model_matrix.csv
|   `-- step6_final_model_feature_columns.json
|-- final_project_summary/
|-- models/
|   `-- final_step6_*.pkl
|-- molecules/
|   |-- ComboCompoundSet.sdf
|   `-- drug_mols.pkl
|-- outputs/
|-- predictions/
|-- results/
|-- static/
|   |-- css/
|   |   |-- app.css
|   |   `-- style.css
|   `-- js/
|       |-- app.js
|       `-- main.js
|-- templates/
|   `-- index.html
`-- uploads/
```

Runtime writes are expected only in:

- `uploads/`
- `outputs/`

All model, data, result, molecule, prediction, and summary assets are read-only
during normal application use.

---

## Required Runtime Assets

These files are required for normal prediction:

| Asset | Purpose |
| --- | --- |
| `data/drug_features.csv` | 263 prepared features for each available drug NSC |
| `data/step6_final_model_feature_columns.json` | Exact 526-column model input order |
| `results/step6_final_model_registry.csv` | Maps each cell line to its selected final Step 6 model |
| `models/final_step6_*.pkl` | Final trained deployment models |

Additional assets used by optional features:

| Asset | Purpose |
| --- | --- |
| `molecules/drug_mols.pkl` | Primary molecule source for RDKit rendering |
| `molecules/ComboCompoundSet.sdf` | Fallback molecule source |
| `backend/molecule_aliases.json` | Molecule alias map, including `753082 -> 761431` |
| `predictions/step5_best_model_test_predictions.csv` | Demo case source |
| `data/model_matrix.csv` | Full model matrix reference, not used for retraining |

---

## Data Summary

Current checked data counts:

| Item | Count |
| --- | ---: |
| Available drug NSCs | 100 |
| Available cell lines | 60 |
| Drug feature columns per drug | 263 |
| Final model input columns | 526 |
| Final Step 6 model files | 60 |
| Rows in `data/model_matrix.csv` | 145,212 |
| Columns in `data/model_matrix.csv` | 530 |
| Rows in Step 5 official test predictions | 14,545 |

`data/drug_features.csv` has:

- `NSC`
- `feat_0` through `feat_262`

Feature meaning:

| Feature range | Meaning |
| --- | --- |
| `feat_0` to `feat_255` | Morgan fingerprint count features |
| `feat_256` | Molecular Weight |
| `feat_257` | LogP |
| `feat_258` | TPSA |
| `feat_259` | Hydrogen Bond Donors |
| `feat_260` | Hydrogen Bond Acceptors |
| `feat_261` | Rotatable Bonds |
| `feat_262` | Ring Count |

---

## Model Summary

There is one selected final model for each of the 60 supported cell lines.

Final Step 6 model counts:

| Model | Count | Percentage |
| --- | ---: | ---: |
| CatBoost | 17 | 28.33 |
| LightGBM | 17 | 28.33 |
| RandomForest | 15 | 25.00 |
| XGBoost | 11 | 18.33 |

Important distinction:

- **Step 5** contains the official train/test evaluation metrics.
- **Step 6** contains final deployment models trained on 100 percent of
  available data for each cell line.

Runtime prediction uses Step 6 models. Evaluation reporting should use Step 5
metrics.

Best average Step 5 model by mean R2:

| Metric | Value |
| --- | --- |
| Model | CatBoost |
| Mean R2 | 0.3748176022281819 |
| Mean Pearson Rp | 0.6179048740464373 |

Average Step 5 model performance:

| Model | Mean R2 | Mean RMSE | Mean MAE | Successful Cell Lines |
| --- | ---: | ---: | ---: | ---: |
| CatBoost | 0.3748176022281819 | 44.22195787354115 | 31.61550233880713 | 60 |
| RandomForest | 0.37123412165837766 | 44.31799441783017 | 31.315135227822257 | 60 |
| LightGBM | 0.37056954787885665 | 44.29068997675277 | 31.475353632851508 | 60 |

See `results/step5_average_model_performance.csv` for the full table.

---

## Prediction Data Flow

For one prediction request:

```text
User JSON
  NSC1, NSC2, CELLNAME
        |
        v
Validate request body
        |
        v
Validate NSC1 and NSC2 in data/drug_features.csv
        |
        v
Validate CELLNAME in results/step6_final_model_registry.csv
        |
        v
Load 263 features for NSC1 and 263 features for NSC2
        |
        v
Build forward row:
  D1_feat_0 ... D1_feat_262 from NSC1
  D2_feat_0 ... D2_feat_262 from NSC2
        |
        v
Build reverse row:
  D1_feat_0 ... D1_feat_262 from NSC2
  D2_feat_0 ... D2_feat_262 from NSC1
        |
        v
Order both rows using data/step6_final_model_feature_columns.json
        |
        v
Verify each row shape is 1 x 526
        |
        v
Load selected final Step 6 model from models/
        |
        v
Predict forward and reverse ComboScore
        |
        v
Average both values
        |
        v
Return JSON response
```

Feature vector rule:

```text
263 Drug 1 features + 263 Drug 2 features = 526 model input features
```

The app does not manually invent feature order. It uses:

```text
data/step6_final_model_feature_columns.json
```

---

## ComboScore Interpretation

ComboScore meaning:

- `ComboScore = Expected growth - Observed percent growth`.
- Positive ComboScore indicates stronger-than-expected inhibition and suggests synergy.
- Negative ComboScore indicates weaker-than-expected inhibition and suggests antagonism.
- Scores near zero suggest additive or neutral behavior.

Project-level five-band interpretation:

| Score range | Label | Category |
| --- | --- | --- |
| `score >= 80` | Strong Synergy | `strong_synergy` |
| `20 <= score < 80` | Moderate Synergy | `moderate_synergy` |
| `-20 < score < 20` | Neutral / Weak effect | `neutral` |
| `-80 < score <= -20` | Moderate Antagonism | `moderate_antagonism` |
| `score <= -80` | Strong Antagonism | `strong_antagonism` |

Current backend implementation note:

- `backend/services/prediction_service.py` currently returns a broad `label`
  field with values such as `synergistic`, `neutral`, and `antagonistic`.
- The current broad thresholds are `>= 20`, `<= -20`, and near-zero otherwise.
- The frontend has normalization helpers for the five-band labels when those
  fields are present.

---

## Setup

### 1. Open PowerShell in the project root

```powershell
cd "C:\Users\HP\Desktop\SDP 27 april\Drug Synergy Prediction"
```

### 2. Use the existing virtual environment

This repository already contains a `.venv` directory. Use it because the default
system `python` may not have CatBoost, LightGBM, XGBoost, SHAP, or RDKit.

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell script execution is blocked, run commands directly through the
virtual environment Python:

```powershell
.\.venv\Scripts\python.exe app.py
```

### 3. Install dependencies if needed

Only do this if the virtual environment is missing packages or you are creating
a fresh environment:

```powershell
python -m pip install -r requirements.txt
```

Dependencies listed in `requirements.txt`:

```text
Flask==3.1.3
pandas==2.3.3
numpy==2.2.6
scipy==1.15.3
scikit-learn==1.7.2
joblib==1.5.3
threadpoolctl==3.6.0
xgboost==3.2.0
catboost==1.2.10
lightgbm==4.6.0
shap==0.49.1
rdkit==2026.3.1
matplotlib==3.10.8
```

### 4. Confirm key dependencies

```powershell
.\.venv\Scripts\python.exe -c "import catboost, rdkit, shap; print('ML dependencies OK')"
```

---

## Run The App

Start Flask:

```powershell
.\.venv\Scripts\python.exe app.py
```

Expected server:

```text
http://127.0.0.1:5000
```

Open the frontend:

```text
http://127.0.0.1:5000/
```

Health check:

```text
http://127.0.0.1:5000/api/health
```

The app is configured in `app.py` to run on:

```text
host = 127.0.0.1
port = 5000
```

---

## Frontend

The active frontend is:

| File | Purpose |
| --- | --- |
| `templates/index.html` | Main Flask-rendered page |
| `static/css/app.css` | Active page styling |
| `static/js/app.js` | Active frontend logic |

Older or alternate frontend files also exist:

| File | Note |
| --- | --- |
| `static/css/style.css` | Alternate or earlier stylesheet |
| `static/js/main.js` | Alternate or earlier script |

The frontend includes:

- drug autocomplete
- cell-line dropdown
- single prediction form
- result card and gauge
- SHAP explanation tab
- molecule lookup tab
- batch CSV upload
- demo case buttons
- light and dark theme toggle

The frontend uses Chart.js from CDN for SHAP chart rendering:

```html
https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
```

If the browser has no internet access, the SHAP chart may not render, but the
backend `/api/explain` response still works.

---

## API Reference

### `GET /`

Renders the frontend.

### `GET /api/health`

Checks required runtime files and counts.

Expected success highlights:

```json
{
  "status": "success",
  "message": "Backend is ready",
  "model_count": 60,
  "available_drugs": 100,
  "available_cell_lines": 60,
  "feature_column_count": 526
}
```

### `GET /api/cell-lines`

Returns all available cell lines.

```json
{
  "status": "success",
  "count": 60,
  "cell_lines": ["786-0", "A498", "A549/ATCC"]
}
```

### `GET /api/drugs`

Returns all available drug NSCs.

Optional query search:

```text
/api/drugs?q=740
```

### `GET /api/model-info/<cell_line>`

Returns the selected final model for one cell line.

Example:

```text
/api/model-info/786-0
```

Verified response summary:

```json
{
  "status": "success",
  "cell_line": "786-0",
  "safe_cell_line": "786_0",
  "model_name": "CatBoost",
  "model_path": "models/final_step6_catboost_786_0.pkl",
  "model_file_exists": true
}
```

### `POST /api/predict`

Runs a single prediction.

Request:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Response includes:

- input values
- selected model name
- selected local model path
- forward prediction
- reverse prediction
- final averaged ComboScore
- broad label
- explanation
- feature count
- molecule endpoint URLs

### `POST /api/batch-predict`

Uploads a CSV file and processes each row independently.

Required CSV columns:

```text
NSC1,NSC2,CELLNAME
```

### `GET /api/molecule/<nsc>`

Returns molecule SVG and metadata for one NSC.

Example:

```text
/api/molecule/753082
```

### `POST /api/molecules`

Returns molecule results for two NSCs.

Request:

```json
{
  "NSC1": 740,
  "NSC2": 750
}
```

### `POST /api/molecule-pair`

Frontend-oriented pair molecule endpoint. Returns `NSC1` and `NSC2` molecule
objects.

### `POST /api/explain`

Runs SHAP explanation for the same input used by prediction.

Request:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

### `GET /api/demo-cases`

Returns three demo cases:

- strong synergy
- neutral
- antagonism

### `GET /api/download/<filename>`

Downloads a generated file from `outputs/`.

This endpoint sanitizes the requested filename and only serves files inside the
configured output directory.

---

## Single Prediction Example

Verified with the project virtual environment:

Request:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Response summary:

```json
{
  "status": "success",
  "input": {
    "NSC1": 740,
    "NSC2": 750,
    "CELLNAME": "786-0"
  },
  "model_used": "CatBoost",
  "model_path": "models/final_step6_catboost_786_0.pkl",
  "prediction_NSC1_to_NSC2": -15.484548102496127,
  "prediction_NSC2_to_NSC1": -18.266707736502354,
  "final_predicted_COMBOSCORE": -16.87562791949924,
  "label": "neutral",
  "feature_count": 526
}
```

Average check:

```text
(-15.484548102496127 + -18.266707736502354) / 2
= -16.87562791949924
```

Example invalid drug request:

```json
{
  "NSC1": 999999,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Expected error:

```json
{
  "status": "error",
  "error": "NSC 999999 not found in data/drug_features.csv."
}
```

---

## Batch Prediction

Batch input CSV must contain exactly:

```csv
NSC1,NSC2,CELLNAME
740,750,786-0
740,752,A498
750,755,A549/ATCC
```

The backend:

1. Saves the uploaded file in `uploads/`.
2. Reads the CSV with pandas.
3. Validates columns.
4. Runs the same single-prediction flow for every row.
5. Records success or row-level error.
6. Saves output CSV in `outputs/`.
7. Returns a JSON summary and preview.

One bad row does not stop the full batch.

Verified mixed-validity batch summary:

```json
{
  "status": "success",
  "total_rows": 3,
  "successful_rows": 2,
  "failed_rows": 1,
  "preview_statuses": ["success", "error", "success"]
}
```

Current batch output columns:

```text
row_index
NSC1
NSC2
CELLNAME
status
error
model_used
model_path
prediction_NSC1_to_NSC2
prediction_NSC2_to_NSC1
final_predicted_COMBOSCORE
label
explanation
```

---

## Molecule Structures

The molecule service uses:

1. `molecules/drug_mols.pkl`
2. `molecules/ComboCompoundSet.sdf` as fallback
3. `backend/molecule_aliases.json` for aliases

Important alias:

```json
{
  "753082": "761431"
}
```

Verified alias response summary:

```json
{
  "status": "success",
  "requested_nsc": 753082,
  "resolved_nsc": 761431,
  "alias_used": true,
  "source": "drug_mols.pkl",
  "molecule_found": true
}
```

The molecule response includes SVG text generated by RDKit. The frontend
sanitizes this SVG before rendering.

---

## SHAP Explainability

SHAP runs only through:

```text
POST /api/explain
```

It does not run automatically during `/api/predict`.

The SHAP service:

1. Reuses the normal prediction context.
2. Builds forward and reverse feature matrices.
3. Creates or reuses a cached `shap.TreeExplainer`.
4. Computes SHAP values for both drug orders.
5. Maps reverse features back to the original drug side.
6. Averages feature effects across both orders.
7. Returns top positive and negative contributors.

Positive SHAP values push the ComboScore upward, toward synergy.

Negative SHAP values pull the ComboScore downward, toward antagonism.

Verified SHAP response summary for `740 + 750 / 786-0`:

```json
{
  "status": "success",
  "model_used": "CatBoost",
  "final_predicted_COMBOSCORE": -16.87562791949924,
  "label": "neutral",
  "top_positive_count": 10,
  "top_negative_count": 10
}
```

Current readable SHAP feature naming examples:

```text
Drug 1 fingerprint feature 192
Drug 2 fingerprint feature 94
Drug 1 physicochemical feature 256
Drug 2 physicochemical feature 257
```

---

## Demo Cases

Demo cases come from:

```text
predictions/step5_best_model_test_predictions.csv
```

Selection logic:

| Demo | Selection |
| --- | --- |
| Strong synergy | Most positive `predicted_comboscore` |
| Neutral | `predicted_comboscore` closest to zero |
| Antagonism | Most negative `predicted_comboscore` |

Verified demo extremes:

| Demo | NSC1 | NSC2 | CELLNAME | Predicted ComboScore | Model |
| --- | ---: | ---: | --- | ---: | --- |
| Strong synergy | 761431 | 761432 | SK-MEL-5 | 230.61074799671496 | LightGBM |
| Neutral | 66847 | 749226 | SNB-19 | 0.0 | RandomForest |
| Antagonism | 92859 | 141540 | HL-60(TB) | -315.0966491087212 | LightGBM |

---

## Results And Evaluation Files

Key result files:

| File | Purpose |
| --- | --- |
| `results/step5_all_cellline_model_comparison.csv` | All Step 5 model comparisons across cell lines |
| `results/step5_best_model_per_cellline.csv` | Best Step 5 evaluated model per cell line |
| `results/step5_average_model_performance.csv` | Average Step 5 model performance by algorithm |
| `results/step6_final_model_registry.csv` | Runtime model registry for final deployment |
| `results/step6_final_model_summary.csv` | Final Step 6 training summary |

Prediction and example files:

| File | Purpose |
| --- | --- |
| `predictions/step5_official_test_dataset.csv` | Saved official Step 5 test dataset |
| `predictions/step5_best_model_test_predictions.csv` | Best-model test predictions, used for demos |
| `predictions/final_model_single_prediction.csv` | Single final-model prediction example |
| `predictions/batch_prediction_input.csv` | Batch input example |
| `predictions/batch_prediction_output.csv` | Batch output example |

Summary files:

| File | Purpose |
| --- | --- |
| `final_project_summary/available_cell_lines.txt` | Human-readable supported cell lines |
| `final_project_summary/available_drug_nscs.txt` | Human-readable supported drug NSCs |
| `final_project_summary/final_available_inputs.csv` | Counts for available inputs |
| `final_project_summary/final_best_models_per_cellline.csv` | Final selected models |
| `final_project_summary/final_model_counts.csv` | Final model type counts |
| `final_project_summary/final_model_performance_summary.csv` | Performance summary copy |
| `final_project_summary/final_flask_assets_manifest.csv` | Runtime asset manifest |
| `final_project_summary/final_pipeline_files_summary.csv` | Pipeline file summary |
| `final_project_summary/final_project_readme.txt` | Original generated project summary |

---

## Validation And Health Checks

Run the backend:

```powershell
.\.venv\Scripts\python.exe app.py
```

Then open:

```text
http://127.0.0.1:5000/api/health
```

Expected health facts:

```text
status: success
model_count: 60
available_drugs: 100
available_cell_lines: 60
feature_column_count: 526
```

Manual endpoint checklist:

```text
GET  /api/health
GET  /api/cell-lines
GET  /api/drugs
GET  /api/model-info/786-0
POST /api/predict
POST /api/batch-predict
GET  /api/molecule/740
GET  /api/molecule/753082
POST /api/explain
GET  /api/demo-cases
GET  /
```

No retraining should occur during any of these checks.

---

## Known Implementation Notes

These notes describe the current repository as inspected, not the idealized
original spec.

1. `feature_builder.py` and `interpretation_service.py` are not separate files.
   Their current responsibilities are implemented mainly inside
   `backend/services/prediction_service.py`.

2. The current `/api/predict` response nests input values under `input` and
   returns a broad `label` field. Older planning docs expect top-level `NSC1`,
   `NSC2`, `CELLNAME`, `prediction_label`, `prediction_category`, and gauge
   fields.

3. `results/step6_final_model_registry.csv` contains old absolute paths from
   the training project. The backend intentionally extracts only the filename
   and loads the model from the local `models/` folder.

4. The frontend currently uses custom polished CSS and JavaScript rather than a
   minimal Bootstrap-only implementation.

5. The active frontend files are `templates/index.html`, `static/css/app.css`,
   and `static/js/app.js`. The `style.css` and `main.js` files appear to be
   older or alternate assets.

6. If the app is run with the system Python instead of the project virtual
   environment, prediction may fail with missing dependencies such as
   `catboost`, and molecule rendering may fail if `rdkit` is unavailable.

---

## Troubleshooting

### Prediction fails with missing CatBoost

Error example:

```text
Model dependency catboost is not installed.
```

Use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe app.py
```

Or install dependencies:

```powershell
python -m pip install -r requirements.txt
```

### Molecule rendering fails

Molecule rendering requires RDKit.

Check:

```powershell
.\.venv\Scripts\python.exe -c "import rdkit; print('RDKit OK')"
```

### `/api/health` reports wrong counts

Expected:

```text
60 final models
100 available drugs
60 available cell lines
526 feature columns
```

If any count is wrong, check that these files and folders exist:

```text
data/drug_features.csv
data/step6_final_model_feature_columns.json
results/step6_final_model_registry.csv
models/
```

### Batch prediction fails

Make sure the uploaded CSV has exactly these columns:

```csv
NSC1,NSC2,CELLNAME
```

The backend is strict about column names and order.

### Cell line not found

Use `/api/cell-lines` to list supported values. Cell-line names must match the
registry, including punctuation, spaces, slashes, and parentheses.

Examples:

```text
786-0
A549/ATCC
HL-60(TB)
MDA-MB-231/ATCC
RXF 393
```

### Drug not found

Use `/api/drugs` to list the 100 supported NSC identifiers. The app does not
guess missing drugs.

---

## Safety And Scope

This application is for model deployment, demonstration, and research workflow
support. Predicted ComboScore values and SHAP explanations are not biological
proof and are not clinical advice. Experimental validation is required before
making scientific or medical decisions from these predictions.
