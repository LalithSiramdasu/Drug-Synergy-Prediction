# SynergyLens: NCI ALMANAC Drug Synergy Prediction

SynergyLens is a Flask web application for predicting drug-combination ComboScore values from the NCI ALMANAC dataset. The app uses already trained machine-learning models, automatically selects the best saved model for the chosen cell line, predicts both drug orders, averages the result, and presents the output with a clear label, explanation story, molecule structures, SHAP explanation, and batch-prediction support.

This project is designed as a final-year machine-learning deployment project. It is a screening and explainability tool, not a clinical decision system.

## Problem Statement

Drug-combination screening can help identify pairs of compounds that may behave differently together than expected from their individual effects. Manually inspecting large combination screens is difficult, and deploying trained models in a usable interface requires careful input validation, consistent feature construction, model selection, and clear result interpretation.

SynergyLens addresses this by providing a lightweight Flask app where users enter two valid NSC drug IDs and a valid cancer cell line. The backend then predicts the NCI ALMANAC ComboScore using saved final models and returns a readable interpretation for project demonstration and screening exploration.

## Dataset And Assets

- Dataset source: NCI ALMANAC drug-combination screening data.
- Prediction target: `COMBOSCORE`.
- Available drugs in the deployed app: 100 NSC IDs.
- Available cell lines in the deployed app: 60.
- Drug feature source: `data/drug_features.csv`.
- Model feature order source: `data/step6_final_model_feature_columns.json`.
- Model registry source: `results/step6_final_model_registry.csv`.
- Final saved deployment models: 60, one model per cell line.

The app uses prepared deployment assets and saved trained models. It does not retrain models during normal use.

## ComboScore Interpretation

SynergyLens uses the NCI ALMANAC ComboScore convention:

`ComboScore = Expected growth - Observed percent growth`

Correct interpretation:

- Positive ComboScore indicates stronger-than-expected inhibition and suggests synergy.
- Near zero ComboScore suggests additive, neutral, or weak interaction behavior.
- Negative ComboScore indicates weaker-than-expected inhibition and suggests antagonism.

The backend label convention is:

| Score range | Label | Meaning |
| --- | --- | --- |
| `score >= 80` | Strong Synergy | Strong positive predicted interaction |
| `20 <= score < 80` | Moderate Synergy | Positive predicted interaction |
| `-20 < score < 20` | Neutral / Weak effect | Roughly additive or weak interaction |
| `-80 < score <= -20` | Moderate Antagonism | Negative predicted interaction |
| `score <= -80` | Strong Antagonism | Strong negative predicted interaction |

Frontend summaries may also show the simpler categories `synergistic`, `neutral`, and `antagonistic`.

## Machine Learning Pipeline Summary

The training pipeline was completed before this Flask deployment app was built.

1. Prepared an FG-only ComboScore dataset from NCI ALMANAC data.
2. Prepared drug-level features for the final available NSC set.
3. Used 263 features per drug:
   - Morgan fingerprint count features.
   - Physicochemical descriptors.
4. Built each model input as a 526-feature drug-pair vector:
   - `D1_feat_0` to `D1_feat_262`.
   - `D2_feat_0` to `D2_feat_262`.
5. Compared multiple model families per cell line during Step 5 test-set evaluation.
6. Selected one best model per cell line.
7. Trained 60 final Step 6 deployment models on the full available training data.

The final app always uses the saved Step 6 models and the saved feature-column order. It does not create a different feature order at runtime.

## Models Used

The project compared and deployed models from these families:

- RandomForest
- XGBoost
- CatBoost
- LightGBM

Final deployment model counts from the registry:

| Model type | Final model count |
| --- | ---: |
| CatBoost | 17 |
| LightGBM | 17 |
| RandomForest | 15 |
| XGBoost | 11 |
| Total | 60 |

Step 5 average test-set performance summary:

| Model | Mean R2 | Mean Pearson Rp | Mean RMSE | Mean MAE |
| --- | ---: | ---: | ---: | ---: |
| CatBoost | 0.375 | 0.618 | 44.222 | 31.616 |
| RandomForest | 0.371 | 0.613 | 44.318 | 31.315 |
| LightGBM | 0.371 | 0.613 | 44.291 | 31.475 |
| XGBoost | 0.370 | 0.612 | 44.423 | 31.646 |

These metrics come from Step 5 official evaluation files. Step 6 final models are deployment models trained on the full available data and are not used as a separate held-out metric source.

## Backend Prediction Flow

For a single prediction, the backend follows this flow:

1. User provides `NSC1`, `NSC2`, and `CELLNAME`.
2. Backend validates that both NSC IDs and the cell line are available.
3. Backend loads the 263 drug features for each NSC.
4. Backend builds the exact 526-feature model input row using the saved feature-column list.
5. Backend selects the best saved model automatically from the final model registry for the chosen cell line.
6. Backend predicts `NSC1 -> NSC2`.
7. Backend predicts `NSC2 -> NSC1`.
8. Backend averages both directional predictions into `final_predicted_COMBOSCORE`.
9. Backend assigns the corrected ComboScore label.
10. Backend returns prediction values, label, result story, model information, gauge metadata, and links for molecule or explanation features.
11. The app can then show the prediction label, readable story, molecule structures, and SHAP explanation for the same input.

The user never manually chooses RandomForest, XGBoost, CatBoost, or LightGBM. Model selection is automatic.

## Frontend Features

The frontend is intentionally lightweight and Flask-compatible. It uses Flask templates, static CSS, vanilla JavaScript, and Bootstrap-compatible layout patterns.

Implemented user-facing features include:

- SPA-style section navigation.
- Drug NSC autocomplete suggestions.
- Cell-line dropdown/select.
- Backend health/status badge.
- Live input validation.
- Prediction loading animation with flow messages.
- Human-readable prediction story.
- Correct ComboScore gauge direction:
  - left = antagonism / negative.
  - center = neutral.
  - right = synergy / positive.
- Safety note for prediction and explanation outputs.
- Recent prediction history using browser `localStorage`.
- Downloadable prediction report generated in the browser.
- Sample CSV download for batch prediction.
- Batch prediction upload and output download.
- Molecule structure viewer.
- Explain AI / SHAP explanation panel.
- Model Performance / Project Transparency section.
- Dark and light theme support.

## API Endpoints

Main routes:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Render the Flask frontend |
| `GET` | `/api/health` | Health check and deployed asset counts |
| `GET` | `/api/system-summary` | Project asset, model, flow, and ComboScore summary |
| `GET` | `/api/model-performance-summary` | Model count and Step 5 performance transparency summary |
| `GET` | `/api/drugs` | List valid NSC drug IDs |
| `GET` | `/api/cell-lines` | List valid cell lines |
| `GET` | `/api/model-info/<cell_line>` | Return model metadata for a cell line |
| `POST` | `/api/predict` | Run one drug-pair ComboScore prediction |
| `POST` | `/api/explain` | Generate SHAP explanation for a selected input |
| `GET` | `/api/molecule/<nsc>` | Return one molecule structure |
| `POST` | `/api/molecule-pair` | Return molecule structures for two NSC IDs |
| `POST` | `/api/molecules` | Return molecule structures for two NSC IDs |
| `POST` | `/api/batch-predict` | Run batch prediction from uploaded CSV |
| `GET` | `/api/download/<filename>` | Download generated batch output CSV |
| `GET` | `/api/demo-cases` | Return corrected demo cases for synergy, neutral, and antagonism |

### Example Prediction Request

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

The prediction response includes both directional predictions, the averaged final ComboScore, corrected label/category, model metadata, explanatory text, and visualization metadata.

## Run Locally

Windows PowerShell example:

```powershell
cd "C:\Users\HP\Desktop\SDP 27 april\Drug Synergy Prediction"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

If PowerShell script execution policy prevents activation, run the app through the virtualenv interpreter directly:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Verification

Run the full backend verification script from the project root:

```powershell
python verify_app.py
```

The script uses Flask `test_client`, so a running Flask server is not required. It verifies:

- `/api/health`
- `/api/drugs`
- `/api/cell-lines`
- `/api/demo-cases`
- `/api/predict`
- `/api/explain`
- `/api/molecule-pair`
- `/api/batch-predict`

Expected final success message:

```text
ALL VERIFICATION TESTS PASSED
```

Optional syntax checks:

```powershell
python -m compileall backend app.py verify_app.py
node --check static/js/app.js
```

## Batch Prediction CSV Format

Batch input CSV files must contain exactly these required columns:

```csv
NSC1,NSC2,CELLNAME
740,750,786-0
740,752,A498
750,755,A549/ATCC
```

The frontend includes a browser-generated sample CSV download button using this format.

## Project Structure

Important folders and files:

| Path | Purpose |
| --- | --- |
| `app.py` | Flask application factory and entry point |
| `backend/routes/` | Flask API routes |
| `backend/services/` | Data loading, prediction, batch, molecule, SHAP, and summary services |
| `templates/index.html` | Main Flask-rendered frontend template |
| `static/css/app.css` | Frontend styling |
| `static/js/app.js` | Vanilla JavaScript frontend logic |
| `data/` | Prepared drug features and feature-column order |
| `models/` | Saved final Step 6 model files |
| `results/` | Model registry and performance summary files |
| `molecules/` | Molecule structure assets |
| `predictions/` | Saved prediction/test input examples |
| `final_project_summary/` | Final pipeline summary artifacts |
| `verify_app.py` | Full backend verification script |

## Repository Notes

- Large trained model files in `models/` are expected to be tracked with Git LFS.
- Runtime batch outputs are generated under `outputs/`.
- Uploaded batch files are handled through `uploads/`.
- Browser-only features such as recent history and prediction report downloads do not store user reports in the repository.

## Limitations

- SynergyLens is an ML screening tool only.
- A predicted synergistic result is not biological proof.
- A predicted antagonistic result is not a clinical warning.
- Results require experimental validation before any scientific or practical conclusion.
- The app does not provide medical advice, treatment advice, dosing advice, or clinical recommendations.
- Model predictions depend on the available NCI ALMANAC-derived training data, final selected features, and saved deployment models.

## Safety Disclaimer

This is a machine-learning screening prediction system. It is not biological proof and not clinical advice. Promising synergy predictions should be validated experimentally before being used for scientific claims or downstream decisions.
