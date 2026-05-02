# AGENTS.md

You are building a Flask backend and simple Bootstrap frontend for an NCI ALMANAC ComboScore prediction project.

The machine learning training is already completed.

Your job is only to build the deployment application using the already prepared files and already trained models.

---

# 1. Main Project Goal

Build a Flask web application where the user can enter:

- Drug 1 NSC
- Drug 2 NSC
- Cell line

Then the backend should:

1. Validate the input.
2. Load the correct drug features.
3. Build the exact model input feature vector.
4. Select the correct best model for that cell line.
5. Predict ComboScore.
6. Predict again with reversed drug order.
7. Average both predictions.
8. Label the result as synergy, neutral, or antagonism.
9. Return the prediction to the frontend.
10. Optionally show molecule structures.
11. Optionally generate SHAP explanation when requested.

---

# 2. Important Rules

1. Do not retrain models.
2. Do not modify the trained model files.
3. Do not modify the prepared data files unless the user explicitly asks.
4. Do not use PercentGrowth as the prediction target.
5. The prediction target is COMBOSCORE.
6. Use the final Step 6 models from the `models/` folder.
7. Use `results/step6_final_model_registry.csv` to select the correct model for each cell line.
8. The user must never manually choose the model.
9. Backend correctness is more important than frontend beauty.
10. Frontend should be simple Bootstrap only.
11. Build backend first, then frontend.
12. Keep code modular, readable, and well commented.
13. Explain the data flow clearly in comments.
14. If something is missing, return a clear error message.
15. Do not silently guess missing files, models, cell lines, or drugs.
16. Do not return raw Python tracebacks to the frontend.

---

# 3. Existing Project Folder

The Flask app root folder is:

nci_almanac_flask_app/

Important folders already exist:

- backend/
- backend/routes/
- backend/services/
- data/
- models/
- molecules/
- predictions/
- results/
- outputs/
- uploads/
- static/
- templates/
- final_project_summary/

---

# 4. Important Files Already Available

Use these files as source assets.

Data files:

- data/drug_features.csv
- data/model_matrix.csv
- data/step6_final_model_feature_columns.json

Model files:

- models/final*step6*\*.pkl

Result files:

- results/step6_final_model_registry.csv
- results/step6_final_model_summary.csv
- results/step5_best_model_per_cellline.csv
- results/step5_average_model_performance.csv
- results/step5_all_cellline_model_comparison.csv

Prediction/test files:

- predictions/step5_official_test_dataset.csv
- predictions/step5_best_model_test_predictions.csv
- predictions/final_model_single_prediction.csv
- predictions/batch_prediction_input.csv
- predictions/batch_prediction_output.csv

Molecule files:

- molecules/drug_mols.pkl
- molecules/ComboCompoundSet.sdf
- backend/molecule_aliases.json

Summary files:

- final_project_summary/available_cell_lines.txt
- final_project_summary/available_drug_nscs.txt
- final_project_summary/final_available_inputs.csv
- final_project_summary/final_best_models_per_cellline.csv
- final_project_summary/final_model_performance_summary.csv
- final_project_summary/final_project_readme.txt

---

# 5. Feature Information

Each drug has 263 features.

The drug feature file is:

data/drug_features.csv

It contains:

- NSC
- feat_0
- feat_1
- feat_2
- ...
- feat_262

Feature meaning:

- feat_0 to feat_255 are Morgan fingerprint count features.
- feat_256 to feat_262 are physicochemical features.

Readable names for the last 7 features:

- feat_256 = Molecular Weight
- feat_257 = LogP
- feat_258 = TPSA
- feat_259 = Hydrogen Bond Donors
- feat_260 = Hydrogen Bond Acceptors
- feat_261 = Rotatable Bonds
- feat_262 = Ring Count

---

# 6. Model Input Feature Rule

For one prediction, the backend must build 526 input features.

Drug 1 features must become:

- D1_feat_0
- D1_feat_1
- ...
- D1_feat_262

Drug 2 features must become:

- D2_feat_0
- D2_feat_1
- ...
- D2_feat_262

Total:

- 263 Drug 1 features
- 263 Drug 2 features
- 526 total input features

The final feature order must come from:

data/step6_final_model_feature_columns.json

Never create a different feature order manually.

Before prediction, verify the final input shape is:

1 row x 526 columns

---

# 7. Model Selection Rule

For every prediction, select the model automatically.

Use:

results/step6_final_model_registry.csv

This registry maps each cell line to its final best Step 6 model.

The backend should:

1. Read the input CELLNAME.
2. Find that cell line in the registry.
3. Get the correct model name and model path.
4. Load the correct model from models/.
5. Use that model for prediction.

The user should not select:

- RandomForest
- XGBoost
- CatBoost
- LightGBM

The backend should decide automatically from the registry.

---

# 8. Prediction Rule

Drug combinations are order-sensitive in the feature matrix, but biologically the combination should be treated symmetrically.

So for every prediction:

First prediction:

- NSC1 as Drug 1
- NSC2 as Drug 2

Second prediction:

- NSC2 as Drug 1
- NSC1 as Drug 2

Final prediction:

final_predicted_COMBOSCORE = average of both predictions

The response must include:

- prediction_NSC1_to_NSC2
- prediction_NSC2_to_NSC1
- final_predicted_COMBOSCORE

---

# 9. ComboScore Meaning

The model predicts COMBOSCORE.

Interpretation:

- ComboScore = Expected growth - Observed percent growth.
- Positive ComboScore means stronger-than-expected inhibition and suggests synergy.
- Near zero means neutral or weak effect.
- Negative ComboScore means weaker-than-expected inhibition and suggests antagonism.

Use these labels:

- score >= 80: Strong Synergy
- 20 <= score < 80: Moderate Synergy
- -20 < score < 20: Neutral / Weak effect
- -80 < score <= -20: Moderate Antagonism
- score <= -80: Strong Antagonism

Also return a simple category:

- strong_synergy
- moderate_synergy
- neutral
- moderate_antagonism
- strong_antagonism

---

# 10. Expected Single Prediction Response

POST /api/predict should return a JSON response similar to this:

{
"status": "success",
"NSC1": 740,
"NSC2": 750,
"CELLNAME": "786-0",
"model_used": "CatBoost",
"model_path": "models/final_step6_catboost_786_0.pkl",
"prediction_NSC1_to_NSC2": -15.48,
"prediction_NSC2_to_NSC1": -18.26,
"final_predicted_COMBOSCORE": -16.87,
"prediction_label": "Neutral / Weak effect",
"prediction_category": "neutral",
"explanation": "The predicted score is close to zero, so the interaction is likely neutral or weak.",
"suggestion": "This pair does not show strong predicted synergy.",
"gauge_min": -1200,
"gauge_max": 700,
"gauge_value": -16.87,
"left_label": "Strong Antagonism",
"middle_label": "Neutral",
"right_label": "Strong Synergy"
}

The numeric values can differ depending on the model output.

---

# 11. Batch Prediction Rule

The app should support batch prediction.

Input CSV must contain:

- NSC1
- NSC2
- CELLNAME

For each row:

1. Validate row.
2. Run the same prediction flow as single prediction.
3. Save success result if prediction works.
4. Save error message if that row fails.
5. Continue processing remaining rows.

One bad row should not stop the full batch.

Batch output should be saved inside:

outputs/

Batch output columns should include:

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

# 12. Molecule Structure Rule

The app should show molecule structures for Drug 1 and Drug 2.

Use:

- molecules/drug_mols.pkl
- molecules/ComboCompoundSet.sdf
- backend/molecule_aliases.json

Use drug_mols.pkl first.

Use ComboCompoundSet.sdf as fallback.

Important alias:

753082 maps to 761431

If the user asks for molecule NSC 753082, the backend should use NSC 761431 structure and clearly mention that alias was used.

Molecule response should include:

- requested_nsc
- used_nsc
- alias_used
- status
- molecule image or SVG data

---

# 13. SHAP Explainability Rule

SHAP should not run automatically during normal prediction.

Normal prediction should be fast.

SHAP should run only when the user clicks the Explainable AI button or calls:

POST /api/explain

SHAP output should be readable.

Use readable feature names.

Examples:

- D1_feat_256 = Drug 1 Molecular Weight
- D1_feat_257 = Drug 1 LogP
- D1_feat_258 = Drug 1 TPSA
- D1_feat_259 = Drug 1 Hydrogen Bond Donors
- D1_feat_260 = Drug 1 Hydrogen Bond Acceptors
- D1_feat_261 = Drug 1 Rotatable Bonds
- D1_feat_262 = Drug 1 Ring Count

Same for Drug 2:

- D2_feat_256 = Drug 2 Molecular Weight
- D2_feat_257 = Drug 2 LogP
- D2_feat_258 = Drug 2 TPSA
- D2_feat_259 = Drug 2 Hydrogen Bond Donors
- D2_feat_260 = Drug 2 Hydrogen Bond Acceptors
- D2_feat_261 = Drug 2 Rotatable Bonds
- D2_feat_262 = Drug 2 Ring Count

For fingerprint features:

- D1_feat_45 = Drug 1 fingerprint pattern 45
- D2_feat_90 = Drug 2 fingerprint pattern 90

The SHAP response should explain:

- which features pushed the score upward toward synergy
- which features pulled the score downward toward antagonism
- simple explanation of why this prediction may have happened
- suggestion based on prediction label

---

# 14. Demo Cases Rule

The app should include 3 demo/load test cases:

1. Strong synergy case
2. Neutral case
3. Antagonism case

Use:

predictions/step5_best_model_test_predictions.csv

Selection logic:

- Strong synergy demo = most positive predicted ComboScore
- Neutral demo = predicted ComboScore closest to zero
- Antagonism demo = most negative predicted ComboScore

Demo response should include:

- NSC1
- NSC2
- CELLNAME
- predicted score
- label
- short description

---

# 15. Required Backend Files To Create

Create or modify these backend files:

- app.py
- backend/config.py
- backend/routes/api_routes.py
- backend/services/model_loader.py
- backend/services/feature_builder.py
- backend/services/interpretation_service.py
- backend/services/prediction_service.py
- backend/services/batch_service.py
- backend/services/molecule_service.py
- backend/services/shap_service.py
- backend/services/demo_service.py

---

# 16. Required Frontend Files To Create Later

Create frontend only after backend works.

Frontend files:

- templates/index.html
- static/css/style.css
- static/js/main.js

Frontend should be simple Bootstrap.

Frontend should include:

- Drug 1 NSC input
- Drug 2 NSC input
- Cell line dropdown
- Predict button
- Result card
- Gauge / odometer visualization
- Drug 1 molecule viewer
- Drug 2 molecule viewer
- Explainable AI button
- Batch CSV upload
- Demo case buttons

---

# 17. Required API Endpoints

Implement these endpoints:

- GET /api/health
- GET /api/cell-lines
- GET /api/drugs
- GET /api/model-info/<cell_line>
- POST /api/predict
- POST /api/batch-predict
- GET /api/molecule/<nsc>
- POST /api/explain
- GET /api/demo-cases
- GET /

---

# 18. Implementation Order

Do not build everything at once.

Follow this order:

Phase 1:

- Flask app setup
- Config paths
- Load model registry
- Load drug features
- Build feature vector
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

---

# 19. What Not To Do

Do not retrain models.

Do not create new ML training code.

Do not use PercentGrowth.

Do not use raw screening data for prediction.

Do not ignore the final model registry.

Do not let the user manually select the model.

Do not change feature order.

Do not predict only one drug order.

Do not run SHAP automatically.

Do not make frontend complex before backend works.

Do not hide errors.

Do not silently guess missing models or missing drugs.

---

# 20. First Codex Action

Before writing code, inspect the project folder.

Then explain:

1. What files you will create.
2. What files you will modify.
3. Backend implementation order.
4. Exact prediction data flow.
5. Missing assets or risks.

Do not start coding until the user approves the plan.
