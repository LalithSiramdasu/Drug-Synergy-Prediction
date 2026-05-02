# BACKEND_FLOW.md

This file explains the exact backend data flow for the NCI ALMANAC Flask app.

The main goal is backend correctness.

The backend should clearly show how data moves from user input to final ComboScore prediction.

---

# 1. Backend Main Responsibility

The backend receives:

- NSC1
- NSC2
- CELLNAME

Then backend returns:

- selected model
- forward prediction
- reverse prediction
- final averaged ComboScore
- synergy / neutral / antagonism label
- explanation
- molecule structures
- optional SHAP explanation
- batch prediction output when CSV is uploaded

---

# 2. Very Important Rule

The backend must not train models.

The backend must only load already trained final Step 6 models from:

models/

Model selection must come from:

results/step6_final_model_registry.csv

Feature order must come from:

data/step6_final_model_feature_columns.json

Drug features must come from:

data/drug_features.csv

---

# 3. Backend File Responsibilities

Create these backend files.

---

## app.py

Main Flask entry point.

Responsibilities:

- create Flask app
- register API routes
- serve frontend page
- configure upload/output folders
- start app

Should import routes from:

backend/routes/api_routes.py

---

## backend/config.py

Central location for all project paths.

Responsibilities:

- define ROOT_DIR
- define DATA_DIR
- define MODELS_DIR
- define RESULTS_DIR
- define MOLECULES_DIR
- define PREDICTIONS_DIR
- define OUTPUTS_DIR
- define UPLOADS_DIR

Important file paths:

- DRUG_FEATURES_PATH = data/drug_features.csv
- FEATURE_COLUMNS_PATH = data/step6_final_model_feature_columns.json
- MODEL_REGISTRY_PATH = results/step6_final_model_registry.csv
- MODEL_MATRIX_PATH = data/model_matrix.csv
- DRUG_MOLS_PATH = molecules/drug_mols.pkl
- SDF_PATH = molecules/ComboCompoundSet.sdf
- MOLECULE_ALIASES_PATH = backend/molecule_aliases.json
- TEST_PREDICTIONS_PATH = predictions/step5_best_model_test_predictions.csv

Config should check if important files exist.

---

## backend/routes/api_routes.py

Contains Flask API endpoints.

Required endpoints:

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

This file should not contain heavy ML logic.

It should call service files.

---

## backend/services/model_loader.py

Handles model registry and model loading.

Responsibilities:

- load step6_final_model_registry.csv
- return available cell lines
- return model info for a cell line
- load the correct model file
- cache loaded models so same model is not loaded again repeatedly

Important rule:

The model must be selected automatically using CELLNAME.

User must never manually select the model.

---

## backend/services/feature_builder.py

Builds model input features.

Responsibilities:

- load drug_features.csv
- load step6_final_model_feature_columns.json
- validate NSC exists
- get 263 features for a drug
- create D1_feat_0 to D1_feat_262
- create D2_feat_0 to D2_feat_262
- combine into 526 features
- order features exactly using saved JSON file
- return a 1-row dataframe ready for model prediction

Important rule:

Final feature dataframe must be exactly:

1 row x 526 columns

---

## backend/services/prediction_service.py

Main prediction logic.

Responsibilities:

- accept NSC1, NSC2, CELLNAME
- validate inputs
- get correct model for cell line
- build forward feature vector
- build reverse feature vector
- predict forward score
- predict reverse score
- average both predictions
- call interpretation service
- return complete prediction dictionary

Important rule:

Always predict both orders.

Forward:

NSC1 -> NSC2

Reverse:

NSC2 -> NSC1

Final:

average of forward and reverse

---

## backend/services/interpretation_service.py

Converts numeric ComboScore into understandable output.

ComboScore = Expected growth - Observed percent growth. Positive ComboScore indicates
stronger-than-expected inhibition and suggests synergy. Negative ComboScore indicates
weaker-than-expected inhibition and suggests antagonism. Scores near zero suggest
additive or neutral behavior.

Responsibilities:

- assign prediction label
- assign prediction category
- create short explanation
- create suggestion
- create gauge values

Label thresholds:

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

Gauge:

- left = Strong Antagonism
- middle = Neutral
- right = Strong Synergy

Use historical min/max from model_matrix.csv if available.

Fallback:

- gauge_min = -1200
- gauge_max = 700

---

## backend/services/batch_service.py

Handles CSV batch predictions.

Responsibilities:

- accept uploaded CSV
- validate required columns
- run prediction_service for every row
- keep processing even if one row fails
- save batch output CSV to outputs/
- return summary and output file path

Required input columns:

- NSC1
- NSC2
- CELLNAME

Required output columns:

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

## backend/services/molecule_service.py

Handles molecule structure viewing.

Responsibilities:

- accept NSC
- apply molecule alias if needed
- load molecule from drug_mols.pkl
- fallback to ComboCompoundSet.sdf if needed
- convert molecule to SVG or image
- return molecule info

Important alias:

753082 -> 761431

If alias is used, return:

- requested_nsc = 753082
- used_nsc = 761431
- alias_used = true

If no molecule is found, return clear error.

---

## backend/services/shap_service.py

Handles Explainable AI.

Responsibilities:

- run only when requested
- use same feature vector as prediction
- use same model as prediction
- compute SHAP values
- convert feature names into readable names
- return top positive and negative feature impacts
- explain in simple language

Important:

Do not run SHAP during normal prediction.

SHAP can be slower.

SHAP should run only when user clicks Explainable AI button.

Readable feature names:

D1_feat_256 = Drug 1 Molecular Weight

D1_feat_257 = Drug 1 LogP

D1_feat_258 = Drug 1 TPSA

D1_feat_259 = Drug 1 Hydrogen Bond Donors

D1_feat_260 = Drug 1 Hydrogen Bond Acceptors

D1_feat_261 = Drug 1 Rotatable Bonds

D1_feat_262 = Drug 1 Ring Count

D2_feat_256 = Drug 2 Molecular Weight

D2_feat_257 = Drug 2 LogP

D2_feat_258 = Drug 2 TPSA

D2_feat_259 = Drug 2 Hydrogen Bond Donors

D2_feat_260 = Drug 2 Hydrogen Bond Acceptors

D2_feat_261 = Drug 2 Rotatable Bonds

D2_feat_262 = Drug 2 Ring Count

For fingerprint features:

D1_feat_45 = Drug 1 fingerprint pattern 45

D2_feat_90 = Drug 2 fingerprint pattern 90

---

## backend/services/demo_service.py

Handles demo/load test cases.

Responsibilities:

- read predictions/step5_best_model_test_predictions.csv
- find strong synergy example
- find neutral example
- find antagonism example
- return those 3 examples to frontend

Selection logic:

Strong synergy:

Most positive predicted ComboScore

Neutral:

Predicted ComboScore closest to zero

Antagonism:

Most negative predicted ComboScore

---

# 4. Single Prediction Full Flow

This is the most important backend flow.

---

## Step 1: User Input

Frontend sends POST request to:

/api/predict

Request body:

    {
      "NSC1": 740,
      "NSC2": 750,
      "CELLNAME": "786-0"
    }

---

## Step 2: Validate Input Format

Backend checks:

- NSC1 exists
- NSC2 exists
- CELLNAME exists
- NSC1 can be converted to integer
- NSC2 can be converted to integer
- CELLNAME is not empty

If invalid, return error.

---

## Step 3: Validate Drugs

Backend checks both drugs in:

data/drug_features.csv

Example:

NSC1 = 740 must exist in drug_features.csv

NSC2 = 750 must exist in drug_features.csv

If missing, return:

    {
      "status": "error",
      "error": "NSC 999999 not found in available drug features."
    }

---

## Step 4: Validate Cell Line

Backend checks CELLNAME in:

results/step6_final_model_registry.csv

Example:

CELLNAME = 786-0 must exist in registry.

If missing, return:

    {
      "status": "error",
      "error": "Cell line INVALID_CELL not found. Please choose one of the available 60 cell lines."
    }

---

## Step 5: Select Correct Model

Backend uses registry to find model for cell line.

Example:

CELLNAME = 786-0

Registry says best final model is CatBoost.

Backend loads:

models/final_step6_catboost_786_0.pkl

The frontend must not choose this.

The backend must decide.

---

## Step 6: Build Forward Feature Vector

Forward means:

Drug 1 = NSC1

Drug 2 = NSC2

Backend gets:

- 263 features for NSC1
- 263 features for NSC2

Then creates:

- D1_feat_0 to D1_feat_262 from NSC1
- D2_feat_0 to D2_feat_262 from NSC2

Total:

526 features

Then reorder columns using:

data/step6_final_model_feature_columns.json

---

## Step 7: Build Reverse Feature Vector

Reverse means:

Drug 1 = NSC2

Drug 2 = NSC1

Backend gets:

- 263 features for NSC2
- 263 features for NSC1

Then creates:

- D1_feat_0 to D1_feat_262 from NSC2
- D2_feat_0 to D2_feat_262 from NSC1

Total:

526 features

Then reorder columns using:

data/step6_final_model_feature_columns.json

---

## Step 8: Predict Both Orders

Backend uses selected model.

Forward prediction:

prediction_NSC1_to_NSC2 = model.predict(forward_vector)

Reverse prediction:

prediction_NSC2_to_NSC1 = model.predict(reverse_vector)

---

## Step 9: Average Final Score

Final ComboScore:

final_predicted_COMBOSCORE =
(prediction_NSC1_to_NSC2 + prediction_NSC2_to_NSC1) / 2

This averaged value is the final score returned to frontend.

---

## Step 10: Interpret Score

Backend calls interpretation_service.

Example:

final_predicted_COMBOSCORE = -16.87

This is between -30 and +30.

Label:

Neutral / Weak effect

Category:

neutral

Explanation:

The predicted ComboScore is close to zero, so this drug pair is predicted to have weak or neutral interaction for this cell line.

Suggestion:

This pair is not predicted to show strong synergy. Consider checking stronger positive ComboScore pairs.

---

## Step 11: Return JSON Response

Example response:

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
      "explanation": "The predicted ComboScore is close to zero, so this drug pair is predicted to have weak or neutral interaction for this cell line.",
      "suggestion": "This pair is not predicted to show strong synergy. Consider checking stronger positive ComboScore pairs.",
      "gauge_min": -1200,
      "gauge_max": 700,
      "gauge_value": -16.87,
      "left_label": "Strong Antagonism",
      "middle_label": "Neutral",
      "right_label": "Strong Synergy"
    }

---

# 5. Batch Prediction Flow

Endpoint:

POST /api/batch-predict

Input:

CSV file upload

Required CSV columns:

- NSC1
- NSC2
- CELLNAME

Flow:

1. Save uploaded file to uploads/
2. Read CSV using pandas
3. Validate required columns
4. Loop over every row
5. For each row, call prediction_service
6. If row succeeds, save prediction result
7. If row fails, save error for that row
8. Continue until all rows are processed
9. Save final batch output CSV to outputs/
10. Return output file path and summary

Important:

One bad row should not stop full batch prediction.

Batch response example:

    {
      "status": "success",
      "total_rows": 100,
      "successful_rows": 97,
      "failed_rows": 3,
      "output_file": "outputs/batch_prediction_2026_04_30_191500.csv"
    }

---

# 6. Molecule Structure Flow

Endpoint:

GET /api/molecule/<nsc>

Example:

GET /api/molecule/740

Flow:

1. Convert NSC to integer
2. Check molecule_aliases.json
3. If alias exists, replace requested NSC with used NSC
4. Search molecule in drug_mols.pkl
5. If not found, search ComboCompoundSet.sdf
6. Convert molecule to SVG/image
7. Return molecule result

Response example:

    {
      "status": "success",
      "requested_nsc": 753082,
      "used_nsc": 761431,
      "alias_used": true,
      "structure_svg": "<svg>...</svg>"
    }

---

# 7. SHAP Explanation Flow

Endpoint:

POST /api/explain

Input:

    {
      "NSC1": 740,
      "NSC2": 750,
      "CELLNAME": "786-0"
    }

Flow:

1. Validate input
2. Select correct model using registry
3. Build forward and reverse feature vectors
4. Use same final feature order
5. Compute SHAP explanation
6. Convert raw feature names into readable names
7. Return top features pushing the ComboScore upward toward synergy
8. Return top features pulling the ComboScore downward toward antagonism
9. Return simple explanation

Important:

SHAP should not run automatically during /api/predict.

It should run only through /api/explain.

Response example:

    {
      "status": "success",
      "CELLNAME": "786-0",
      "model_used": "CatBoost",
      "top_synergy_drivers": [
        {
          "feature": "Drug 1 LogP",
          "value": 2.31,
          "impact": 5.44,
          "meaning": "This feature pushed the ComboScore upward toward synergy."
        }
      ],
      "top_antagonism_drivers": [
        {
          "feature": "Drug 2 Molecular Weight",
          "value": 489.93,
          "impact": -3.18,
          "meaning": "This feature pulled the ComboScore downward toward antagonism."
        }
      ],
      "plain_english_explanation": "The model prediction was mainly influenced by molecular descriptors and fingerprint patterns from both drugs.",
      "suggestion": "Use this explanation as model reasoning support, not as biological proof."
    }

---

# 8. Demo Cases Flow

Endpoint:

GET /api/demo-cases

Source file:

predictions/step5_best_model_test_predictions.csv

Flow:

1. Load prediction file
2. Identify predicted score column
3. Pick most positive prediction as strong synergy demo
4. Pick prediction closest to zero as neutral demo
5. Pick most negative prediction as antagonism demo
6. Return three demo records

Response example:

    {
      "status": "success",
      "demo_cases": {
        "strong_synergy": {
          "NSC1": 123,
          "NSC2": 456,
          "CELLNAME": "A498",
          "predicted_score": 210.5,
          "label": "Strong Synergy"
        },
        "neutral": {
          "NSC1": 740,
          "NSC2": 750,
          "CELLNAME": "786-0",
          "predicted_score": -1.2,
          "label": "Neutral / Weak effect"
        },
        "antagonism": {
          "NSC1": 111,
          "NSC2": 222,
          "CELLNAME": "MCF7",
          "predicted_score": -150.8,
          "label": "Strong Antagonism"
        }
      }
    }

---

# 9. Health Check Flow

Endpoint:

GET /api/health

This should check:

- drug_features.csv exists
- feature columns JSON exists
- model registry exists
- models folder exists
- 60 final model files exist
- molecule files exist
- outputs folder exists
- uploads folder exists

Response example:

    {
      "status": "success",
      "message": "Backend is ready",
      "drug_features_found": true,
      "feature_columns_found": true,
      "model_registry_found": true,
      "model_count": 60,
      "available_drugs": 100,
      "available_cell_lines": 60
    }

---

# 10. Error Handling Rules

Return clear JSON errors.

Do not expose raw traceback.

Bad request example:

    {
      "status": "error",
      "error": "NSC1 is required."
    }

Invalid drug example:

    {
      "status": "error",
      "error": "NSC 999999 not found in drug_features.csv."
    }

Invalid cell line example:

    {
      "status": "error",
      "error": "Cell line INVALID_CELL not found in model registry."
    }

Missing model example:

    {
      "status": "error",
      "error": "Model file for cell line 786-0 was not found."
    }

Feature mismatch example:

    {
      "status": "error",
      "error": "Feature vector has 525 columns, expected 526."
    }

---

# 11. Frontend Flow

Frontend should be simple Bootstrap.

Page:

GET /

User sees:

- Drug 1 NSC input
- Drug 2 NSC input
- Cell line dropdown
- Predict button
- Result section
- Gauge / odometer
- Drug structure cards
- Explainable AI button
- Batch upload section
- Demo case buttons

Frontend calls:

- /api/cell-lines to fill dropdown
- /api/drugs optionally for validation/autocomplete
- /api/predict for prediction
- /api/molecule/<nsc> for molecule images
- /api/explain for SHAP
- /api/batch-predict for batch CSV
- /api/demo-cases for demo cases

---

# 12. Recommended Implementation Order For Codex

Do not implement frontend first.

Use this order:

1. Create backend/config.py
2. Create backend/services/model_loader.py
3. Create backend/services/feature_builder.py
4. Create backend/services/interpretation_service.py
5. Create backend/services/prediction_service.py
6. Create backend/routes/api_routes.py
7. Create app.py
8. Test /api/health
9. Test /api/cell-lines
10. Test /api/drugs
11. Test /api/predict
12. Create batch_service.py
13. Test /api/batch-predict
14. Create molecule_service.py
15. Test /api/molecule/<nsc>
16. Create shap_service.py
17. Test /api/explain
18. Create demo_service.py
19. Test /api/demo-cases
20. Build simple Bootstrap frontend

---

# 13. Backend Completion Checklist

Backend is complete only when:

- Flask starts successfully
- /api/health returns success
- /api/cell-lines returns 60 cell lines
- /api/drugs returns 100 NSC drugs
- /api/model-info/786-0 returns selected model info
- /api/predict works for valid input
- /api/predict rejects invalid drug
- /api/predict rejects invalid cell line
- prediction uses correct model automatically
- prediction uses 526 features
- forward and reverse predictions are both made
- final prediction is average
- prediction label is returned
- gauge values are returned
- /api/batch-predict works
- /api/molecule/740 works
- /api/molecule/753082 uses alias if needed
- /api/explain works only when requested
- /api/demo-cases returns 3 examples
- no retraining code exists
