# PROJECT_CONTEXT.md

This document gives full project context for the NCI ALMANAC Flask deployment app.

The machine learning pipeline is already completed.

This Flask app should only use the final prepared data files, result files, prediction files, molecule files, and trained Step 6 models.

The goal is to build a backend-first deployment application that predicts ComboScore for a given drug pair and cell line.

---

# 1. Project Name

NCI ALMANAC ComboScore Prediction Flask App

Project root folder:

nci_almanac_flask_app/

---

# 2. Main Purpose

The app predicts drug-combination ComboScore.

User input:

- Drug 1 NSC
- Drug 2 NSC
- Cell line

Backend output:

- Predicted ComboScore
- Model used
- Synergy / neutral / antagonism label
- Forward prediction
- Reverse prediction
- Final averaged prediction
- Molecule structures
- Optional SHAP explanation
- Optional batch prediction output

---

# 3. Important Correction From Previous Work

Earlier wrong work confused PercentGrowth with ComboScore.

Final corrected project uses:

Target column = COMBOSCORE

Do not use PercentGrowth.

Do not use raw PercentGrowth values as model target.

The Flask app must use only final corrected files.

---

# 4. Reference Paper Logic Used

The project follows the NCI ALMANAC paper-style logic:

- Use ComboScore as the drug-combination response target.
- Use FG-only ComboScore data.
- Use molecular features for Drug 1 and Drug 2.
- Train separate models per cell line.
- For every cell line, select the best model based on Step 5 evaluation.
- Train final Step 6 deployment models on 100 percent of the cell-line data.
- Use the final Step 6 models only for deployment.

Important:

Step 5 = official evaluation metrics.

Step 6 = final deployment models trained on full data.

---

# 5. Final Data Source Used For Flask

The Flask app uses copied assets from the completed project:

Original ML project:

nci_almanac_v3/

Deployment project:

nci_almanac_flask_app/

The Flask app should not go back to nci_almanac_v3 during runtime.

All needed files are already copied into nci_almanac_flask_app/.

---

# 6. Existing Flask App Folder Structure

Current structure:

nci_almanac_flask_app/

- backend/
- backend/routes/
- backend/services/
- data/
- models/
- molecules/
- outputs/
- predictions/
- results/
- static/
- static/css/
- static/js/
- templates/
- uploads/
- final_project_summary/

---

# 7. Main Data Files

The backend must use these files:

data/drug_features.csv

Purpose:

Contains final cleaned drug features for all available NSC drugs.

Expected shape:

100 rows
264 columns

Columns:

- NSC
- feat_0 to feat_262

---

data/model_matrix.csv

Purpose:

Final full model matrix created during training.

Contains:

- NSC1
- NSC2
- CELLNAME
- D1_feat_0 to D1_feat_262
- D2_feat_0 to D2_feat_262
- COMBOSCORE

Expected shape from training:

145212 rows
530 columns

This file can be used for:

- checking historical min and max ComboScore
- creating gauge range
- debugging
- reference only

Do not retrain models from this file inside Flask.

---

data/step6_final_model_feature_columns.json

Purpose:

Stores exact model input feature order.

Expected feature count:

526

This file is critical.

Before prediction, backend must order the prediction feature vector exactly according to this JSON file.

---

# 8. Drug Feature Details

Each drug has 263 features.

Columns:

feat_0 to feat_262

Meaning:

feat_0 to feat_255:

Morgan fingerprint count features

feat_256 to feat_262:

Physicochemical features

Readable names:

feat_256 = Molecular Weight
feat_257 = LogP
feat_258 = TPSA
feat_259 = Hydrogen Bond Donors
feat_260 = Hydrogen Bond Acceptors
feat_261 = Rotatable Bonds
feat_262 = Ring Count

For model prediction, features become:

Drug 1:

D1_feat_0 to D1_feat_262

Drug 2:

D2_feat_0 to D2_feat_262

Total:

263 + 263 = 526 model input features

---

# 9. Feature Recovery Note

During preprocessing, the corrected FG-only ComboScore file needed 100 unique drugs.

Initially, only 98 drugs had features.

Missing drugs were:

- 119875
- 753082

Recovery was done:

NSC 119875:

Recovered from local molecule information.

NSC 753082:

Recovered by copying features from NSC 761431 because 753082 and 761431 refer to the same molecule identity used in this project context.

Final result:

data/drug_features.csv has 100 percent coverage for the 100 needed drugs.

Important molecule alias:

753082 -> 761431

This alias is stored in:

backend/molecule_aliases.json

---

# 10. Model Training Summary

Models used:

- RandomForest
- XGBoost
- CatBoost
- LightGBM

Training was done per cell line.

There are 60 cell lines.

Each cell line has one selected final best model.

Final Step 6 models were trained on 100 percent of available data for each cell line.

The Flask backend must use only these final Step 6 models.

---

# 11. Official Evaluation Summary

Step 5 trained and evaluated models using:

- train/test split
- training augmentation only
- untouched test set
- per-cell-line model comparison

Step 5 is the official evaluation step.

Important Step 5 result files:

results/step5_all_cellline_model_comparison.csv

Contains all model metrics for all cell lines.

results/step5_best_model_per_cellline.csv

Contains the best evaluated model per cell line.

results/step5_average_model_performance.csv

Contains average performance across all cell lines.

These files are useful for displaying model performance.

Do not use them to select runtime model if Step 6 registry exists.

Runtime model selection should use:

results/step6_final_model_registry.csv

---

# 12. Final Deployment Model Summary

Step 6 selected final models and trained them on full available data.

Important Step 6 files:

results/step6_final_model_registry.csv

This is the most important file for backend model selection.

results/step6_final_model_summary.csv

Summary of final deployment models.

data/step6_final_model_feature_columns.json

Exact feature order for final deployment models.

models/final*step6*\*.pkl

The actual saved final models.

---

# 13. Final Model Count

Final model counts:

CatBoost:

17 cell lines

LightGBM:

17 cell lines

RandomForest:

15 cell lines

XGBoost:

11 cell lines

Total:

60 final models

There should be 60 model files in the models/ folder.

---

# 14. Model Registry Rule

The backend must use:

results/step6_final_model_registry.csv

This file maps each cell line to its final model.

The backend should not hardcode model names for cell lines unless absolutely required.

The user should never manually choose the model.

For example:

If cell line 786-0 uses CatBoost, backend should automatically load the CatBoost model for 786-0.

If another cell line uses LightGBM, backend should automatically load the LightGBM model for that cell line.

---

# 15. Prediction Data Flow

For a single prediction:

Input:

- NSC1
- NSC2
- CELLNAME

Flow:

1. Validate NSC1 exists in drug_features.csv.
2. Validate NSC2 exists in drug_features.csv.
3. Validate CELLNAME exists in model registry.
4. Get 263 features for NSC1.
5. Get 263 features for NSC2.
6. Build forward feature vector:
   - NSC1 as Drug 1
   - NSC2 as Drug 2
7. Build reverse feature vector:
   - NSC2 as Drug 1
   - NSC1 as Drug 2
8. Reorder both vectors using step6_final_model_feature_columns.json.
9. Load correct final Step 6 model for CELLNAME.
10. Predict forward ComboScore.
11. Predict reverse ComboScore.
12. Average both predictions.
13. Interpret final averaged score.
14. Return prediction response.

---

# 16. Why Forward And Reverse Prediction Is Needed

Drug-pair feature input is ordered:

Drug 1 features come first.

Drug 2 features come second.

But drug combinations are naturally symmetric.

Drug A + Drug B should be treated similar to Drug B + Drug A.

Therefore, for robust prediction:

Predict A to B.

Predict B to A.

Average both.

The final prediction returned to the user must be the averaged value.

---

# 17. ComboScore Meaning

The model predicts COMBOSCORE.

Interpretation:

ComboScore = Expected growth - Observed percent growth.

Positive ComboScore:

Synergy, because observed inhibition is stronger than expected.

Near zero ComboScore:

Neutral or weak effect

Negative ComboScore:

Antagonism, because observed inhibition is weaker than expected.

Use these thresholds:

score >= 80:

Strong Synergy

20 <= score < 80:

Moderate Synergy

-20 < score < 20:

Neutral / Weak effect

-80 < score <= -20:

Moderate Antagonism

score <= -80:

Strong Antagonism

---

# 18. Gauge Or Odometer Requirement

Frontend should show a gauge / odometer for predicted ComboScore.

Gauge meaning:

Left side:

Strong Antagonism

Middle:

Neutral

Right side:

Strong Synergy

Gauge value:

final_predicted_COMBOSCORE

Preferred gauge range:

Use historical minimum and maximum COMBOSCORE from:

data/model_matrix.csv

Fallback range:

minimum = -1200

maximum = 700

The backend can return:

- gauge_min
- gauge_max
- gauge_value
- left_label
- middle_label
- right_label

---

# 19. Prediction Response Should Be Explainable

Each prediction should return:

- predicted score
- prediction label
- model used
- short explanation
- suggestion

Example explanation logic:

If score is strongly positive:

The model predicts strong synergy, meaning this drug pair may inhibit more strongly than expected for this cell line.

If score is near zero:

The model predicts a neutral or weak interaction.

If score is strongly negative:

The model predicts antagonism, meaning the drug pair may inhibit less strongly than expected for this cell line.

---

# 20. Batch Prediction Requirement

The app should support batch prediction using CSV upload.

Input CSV columns:

- NSC1
- NSC2
- CELLNAME

For each row, backend should run the same single-prediction logic.

Important:

One bad row should not stop the whole batch.

If one row has invalid NSC or invalid cell line, mark only that row as error and continue.

Batch output should be saved in:

outputs/

Batch output columns:

- row_index
- NSC1
- NSC2
- CELLNAME
- model_used
- prediction_NSC1_to_NSC2
- prediction_NSC2_to_NSC1
- final_predicted_COMBOSCORE
- prediction_label
- prediction_category
- status
- error

---

# 21. Prediction Files Available

The predictions/ folder contains previous prediction/test outputs.

Important files:

predictions/step5_official_test_dataset.csv

This is the official saved test dataset from Step 5.

It can be used to test prediction examples.

predictions/step5_best_model_test_predictions.csv

This contains best model predictions on official Step 5 test entries.

It can be used to create demo/load test cases.

predictions/final_model_single_prediction.csv

Single prediction example from final model flow.

predictions/batch_prediction_input.csv

Example batch input file.

predictions/batch_prediction_output.csv

Example batch output file.

---

# 22. Demo Case Requirement

The app should include 3 demo/load test cases:

1. Strong synergy demo
2. Neutral demo
3. Antagonism demo

Use:

predictions/step5_best_model_test_predictions.csv

Selection logic:

Strong synergy:

row with most positive predicted ComboScore

Neutral:

row with predicted ComboScore closest to zero

Antagonism:

row with most negative predicted ComboScore

Each demo case should return:

- NSC1
- NSC2
- CELLNAME
- predicted score
- label
- short description

---

# 23. Molecule Structure Requirement

The app should show molecule structures for Drug 1 and Drug 2.

Use molecule files:

molecules/drug_mols.pkl

Primary source for molecule objects.

molecules/ComboCompoundSet.sdf

Fallback source.

backend/molecule_aliases.json

Alias mapping file.

Important alias:

753082 -> 761431

If user enters 753082, backend should use molecule structure of 761431 and mention alias was used.

Molecule response should include:

- requested_nsc
- used_nsc
- alias_used
- status
- image or SVG data

---

# 24. SHAP Explainability Requirement

The app should support Explainable AI using SHAP.

SHAP should not run during normal prediction.

SHAP should run only when user clicks Explainable AI button or calls:

POST /api/explain

SHAP should explain:

- which features pushed prediction upward toward synergy
- which features pulled prediction downward toward antagonism
- simple English explanation
- prediction-based suggestion

Readable feature names must be used.

Do not show only raw feature names.

Good names:

Drug 1 Molecular Weight

Drug 2 LogP

Drug 1 fingerprint pattern 45

Drug 2 fingerprint pattern 90

Bad names:

D1_feat_256 without explanation

D2_feat_90 without explanation

---

# 25. Flask Backend Files To Create

Create these files:

app.py

backend/config.py

backend/routes/api_routes.py

backend/services/model_loader.py

backend/services/feature_builder.py

backend/services/interpretation_service.py

backend/services/prediction_service.py

backend/services/batch_service.py

backend/services/molecule_service.py

backend/services/shap_service.py

backend/services/demo_service.py

---

# 26. Frontend Files To Create Later

Create frontend only after backend works.

Frontend files:

templates/index.html

static/css/style.css

static/js/main.js

Frontend should be simple Bootstrap.

Frontend should contain:

- Drug 1 NSC input
- Drug 2 NSC input
- Cell line dropdown
- Predict button
- Result card
- Gauge / odometer
- Drug 1 molecule viewer
- Drug 2 molecule viewer
- Explainable AI button
- Batch upload section
- Demo case buttons

---

# 27. Required API Endpoints

GET /api/health

Purpose:

Check backend status and important file availability.

GET /api/cell-lines

Purpose:

Return available 60 cell lines.

GET /api/drugs

Purpose:

Return available 100 NSC drugs.

GET /api/model-info/<cell_line>

Purpose:

Return final model selected for a specific cell line.

POST /api/predict

Purpose:

Single prediction.

POST /api/batch-predict

Purpose:

Batch CSV prediction.

GET /api/molecule/<nsc>

Purpose:

Return molecule structure.

POST /api/explain

Purpose:

Return SHAP explanation.

GET /api/demo-cases

Purpose:

Return strong synergy, neutral, and antagonism examples.

GET /

Purpose:

Render simple Bootstrap frontend.

---

# 28. Backend First Development Plan

Development should happen in phases.

Phase 1:

- Flask app setup
- Config paths
- Model registry loading
- Drug feature loading
- Feature vector building
- Single prediction API

Phase 2:

- Batch prediction API

Phase 3:

- Molecule structure API

Phase 4:

- SHAP explanation API

Phase 5:

- Demo cases API

Phase 6:

- Simple Bootstrap frontend

Do not implement everything at once.

---

# 29. Important Testing Examples

Single prediction example:

NSC1 = 740

NSC2 = 750

CELLNAME = 786-0

Expected:

- status success
- selected model automatically
- forward prediction exists
- reverse prediction exists
- final prediction is average
- final prediction has label

Invalid drug test:

NSC1 = 999999

NSC2 = 750

CELLNAME = 786-0

Expected:

Clear error saying NSC 999999 not found.

Invalid cell line test:

NSC1 = 740

NSC2 = 750

CELLNAME = INVALID_CELL

Expected:

Clear error saying cell line not found.

---

# 30. Final Success Definition

The project is successful when:

1. Backend starts without errors.
2. /api/health works.
3. /api/cell-lines returns 60 cell lines.
4. /api/drugs returns 100 drugs.
5. /api/predict works for valid input.
6. Correct model is selected automatically from registry.
7. 526 features are built in exact saved order.
8. Forward and reverse predictions are both made.
9. Final prediction is averaged.
10. Prediction is labeled as synergy, neutral, or antagonism.
11. Batch prediction works.
12. Molecule structure viewing works.
13. SHAP explanation works only when requested.
14. Demo cases work.
15. Simple Bootstrap frontend works.
16. No model retraining happens inside Flask.
