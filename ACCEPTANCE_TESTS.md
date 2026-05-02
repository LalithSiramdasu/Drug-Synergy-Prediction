# ACCEPTANCE_TESTS.md

This file contains acceptance tests for the NCI ALMANAC Flask backend.

Codex must use this file to verify that the backend works correctly.

The backend is not complete until these tests pass.

---

# 1. Main Testing Rule

Do not assume the app is working just because Flask starts.

The backend must be tested endpoint by endpoint.

Every important endpoint should return clear JSON.

Errors should also return clear JSON.

Raw Python tracebacks should not be shown to the frontend.

---

# 2. Start The Flask App

From the project root:

```text
nci_almanac_flask_app/
```

Run:

```bash
python app.py
```

Expected:

```text
Flask app starts without crashing.
```

The app should run at something like:

```text
http://127.0.0.1:5000
```

---

# 3. Test 1: Health Check

Endpoint:

```http
GET /api/health
```

Browser test:

```text
http://127.0.0.1:5000/api/health
```

Expected result:

```json
{
  "status": "success",
  "message": "Backend is ready"
}
```

The response should also confirm:

- drug_features.csv found
- feature columns JSON found
- model registry found
- model count is 60
- available drugs count is 100
- available cell lines count is 60

Pass condition:

```text
/api/health returns status success and confirms required files are available.
```

Fail condition:

```text
Any required file is missing, model count is not 60, or app crashes.
```

---

# 4. Test 2: Available Cell Lines

Endpoint:

```http
GET /api/cell-lines
```

Browser test:

```text
http://127.0.0.1:5000/api/cell-lines
```

Expected:

```json
{
  "status": "success",
  "count": 60,
  "cell_lines": [...]
}
```

The returned list must include:

```text
786-0
A498
A549/ATCC
MCF7
U251
```

Pass condition:

```text
Returns exactly 60 available cell lines.
```

---

# 5. Test 3: Available Drugs

Endpoint:

```http
GET /api/drugs
```

Browser test:

```text
http://127.0.0.1:5000/api/drugs
```

Expected:

```json
{
  "status": "success",
  "count": 100,
  "drugs": [...]
}
```

The returned list must include:

```text
740
750
752
755
753082
119875
```

Pass condition:

```text
Returns exactly 100 available drug NSCs.
```

---

# 6. Test 4: Model Info For One Cell Line

Endpoint:

```http
GET /api/model-info/<cell_line>
```

Browser test:

```text
http://127.0.0.1:5000/api/model-info/786-0
```

Expected:

```json
{
  "status": "success",
  "cell_line": "786-0",
  "model_name": "CatBoost",
  "model_path": "models/final_step6_catboost_786_0.pkl"
}
```

The exact key names can differ slightly, but the response must clearly show:

- cell line
- selected final model
- model file path
- model file exists

Pass condition:

```text
The backend finds the model for 786-0 automatically from step6_final_model_registry.csv.
```

Fail condition:

```text
The user is asked to choose model manually.
```

---

# 7. Test 5: Single Prediction Success

Endpoint:

```http
POST /api/predict
```

Test input:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Expected response must include:

```json
{
  "status": "success",
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0",
  "model_used": "CatBoost",
  "prediction_NSC1_to_NSC2": "...",
  "prediction_NSC2_to_NSC1": "...",
  "final_predicted_COMBOSCORE": "...",
  "prediction_label": "...",
  "prediction_category": "..."
}
```

Required fields:

```text
status
NSC1
NSC2
CELLNAME
model_used
model_path
prediction_NSC1_to_NSC2
prediction_NSC2_to_NSC1
final_predicted_COMBOSCORE
prediction_label
prediction_category
explanation
suggestion
gauge_min
gauge_max
gauge_value
left_label
middle_label
right_label
```

Pass condition:

```text
Prediction succeeds and uses the automatically selected model.
```

Important validation:

```text
final_predicted_COMBOSCORE must equal the average of prediction_NSC1_to_NSC2 and prediction_NSC2_to_NSC1.
```

---

# 8. Test 6: Forward And Reverse Average Check

Use same input:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Response must include:

```text
prediction_NSC1_to_NSC2
prediction_NSC2_to_NSC1
final_predicted_COMBOSCORE
```

Manual check:

```text
final_predicted_COMBOSCORE =
(prediction_NSC1_to_NSC2 + prediction_NSC2_to_NSC1) / 2
```

Pass condition:

```text
Final score is the average of forward and reverse predictions.
```

Fail condition:

```text
Only one direction is predicted.
```

---

# 9. Test 7: Prediction Label Check

Use this input:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

ComboScore = Expected growth - Observed percent growth. Positive ComboScore indicates
stronger-than-expected inhibition and suggests synergy. Negative ComboScore indicates
weaker-than-expected inhibition and suggests antagonism. Scores near zero suggest
additive or neutral behavior.

The returned prediction label must follow these thresholds:

```text
score >= +80       -> Strong Synergy
+20 to +80         -> Moderate Synergy
-20 to +20         -> Neutral / Weak effect
-80 to -20         -> Moderate Antagonism
score <= -80       -> Strong Antagonism
```

Pass condition:

```text
The label matches the final averaged ComboScore.
```

---

# 10. Test 8: Invalid Drug Error

Endpoint:

```http
POST /api/predict
```

Input:

```json
{
  "NSC1": 999999,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Expected:

```json
{
  "status": "error",
  "error": "NSC 999999 not found..."
}
```

Pass condition:

```text
Backend returns clear error.
```

Fail condition:

```text
Backend crashes or silently guesses another drug.
```

---

# 11. Test 9: Invalid Cell Line Error

Endpoint:

```http
POST /api/predict
```

Input:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "INVALID_CELL"
}
```

Expected:

```json
{
  "status": "error",
  "error": "Cell line INVALID_CELL not found..."
}
```

Pass condition:

```text
Backend returns clear error.
```

Fail condition:

```text
Backend crashes or chooses a random/default cell line.
```

---

# 12. Test 10: Missing Input Error

Endpoint:

```http
POST /api/predict
```

Input:

```json
{
  "NSC1": 740,
  "CELLNAME": "786-0"
}
```

Expected:

```json
{
  "status": "error",
  "error": "NSC2 is required..."
}
```

Pass condition:

```text
Backend clearly reports missing NSC2.
```

---

# 13. Test 11: Different Cell Line Uses Different Model

Endpoint:

```http
POST /api/predict
```

Input 1:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Input 2:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "A549/ATCC"
}
```

Expected:

For 786-0:

```text
Uses CatBoost
```

For A549/ATCC:

```text
Uses LightGBM
```

Pass condition:

```text
Backend automatically selects different correct models based on cell line.
```

Fail condition:

```text
Same hardcoded model is used for every cell line.
```

---

# 14. Test 12: Batch Prediction Success

Endpoint:

```http
POST /api/batch-predict
```

Input CSV must contain:

```csv
NSC1,NSC2,CELLNAME
740,750,786-0
740,752,A498
750,755,A549/ATCC
```

Expected response:

```json
{
  "status": "success",
  "total_rows": 3,
  "successful_rows": 3,
  "failed_rows": 0,
  "output_file": "outputs/..."
}
```

Output CSV must include:

```text
row_index
NSC1
NSC2
CELLNAME
model_used
prediction_NSC1_to_NSC2
prediction_NSC2_to_NSC1
final_predicted_COMBOSCORE
prediction_label
prediction_category
status
error
```

Pass condition:

```text
Batch output file is created inside outputs/.
```

---

# 15. Test 13: Batch Prediction With One Bad Row

Input CSV:

```csv
NSC1,NSC2,CELLNAME
740,750,786-0
999999,750,786-0
740,752,A498
```

Expected:

```json
{
  "status": "success",
  "total_rows": 3,
  "successful_rows": 2,
  "failed_rows": 1
}
```

Output CSV should show:

Row 1:

```text
success
```

Row 2:

```text
error
```

Row 3:

```text
success
```

Pass condition:

```text
One bad row does not stop the full batch.
```

---

# 16. Test 14: Molecule Structure Success

Endpoint:

```http
GET /api/molecule/740
```

Browser test:

```text
http://127.0.0.1:5000/api/molecule/740
```

Expected response:

```json
{
  "status": "success",
  "requested_nsc": 740,
  "used_nsc": 740,
  "alias_used": false,
  "structure_svg": "..."
}
```

Pass condition:

```text
Molecule structure is returned as SVG or image data.
```

---

# 17. Test 15: Molecule Alias Check

Endpoint:

```http
GET /api/molecule/753082
```

Expected response:

```json
{
  "status": "success",
  "requested_nsc": 753082,
  "used_nsc": 761431,
  "alias_used": true,
  "structure_svg": "..."
}
```

Pass condition:

```text
Backend uses alias 753082 -> 761431 and clearly reports alias_used true.
```

---

# 18. Test 16: SHAP Explainability

Endpoint:

```http
POST /api/explain
```

Input:

```json
{
  "NSC1": 740,
  "NSC2": 750,
  "CELLNAME": "786-0"
}
```

Expected response:

```json
{
  "status": "success",
  "CELLNAME": "786-0",
  "model_used": "CatBoost",
  "top_synergy_drivers": [],
  "top_antagonism_drivers": [],
  "plain_english_explanation": "...",
  "suggestion": "..."
}
```

Required:

```text
SHAP should run only when /api/explain is called.
```

Pass condition:

```text
SHAP output uses readable feature names.
Positive SHAP values push the ComboScore upward toward synergy, and negative SHAP values pull the ComboScore downward toward antagonism.
```

Readable examples:

```text
Drug 1 Molecular Weight
Drug 2 LogP
Drug 1 fingerprint pattern 45
Drug 2 fingerprint pattern 90
```

Fail condition:

```text
SHAP runs automatically during /api/predict.
```

---

# 19. Test 17: Demo Cases

Endpoint:

```http
GET /api/demo-cases
```

Browser test:

```text
http://127.0.0.1:5000/api/demo-cases
```

Expected response:

```json
{
  "status": "success",
  "demo_cases": {
    "strong_synergy": {},
    "neutral": {},
    "antagonism": {}
  }
}
```

Each demo case should include:

```text
NSC1
NSC2
CELLNAME
predicted_score
label
description
```

Pass condition:

```text
Returns exactly 3 demo cases: strong synergy, neutral, antagonism.
```

---

# 20. Test 18: Frontend Page Loads

Endpoint:

```http
GET /
```

Browser test:

```text
http://127.0.0.1:5000/
```

Expected:

```text
Simple Bootstrap frontend loads.
```

Page should show:

- Drug 1 NSC input
- Drug 2 NSC input
- Cell line dropdown
- Predict button
- Batch upload section
- Demo case buttons
- Result area
- Molecule structure area
- Explainable AI button

Pass condition:

```text
Frontend loads without error and can call backend APIs.
```

---

# 21. Test 19: Frontend Single Prediction

In frontend:

1. Enter Drug 1 NSC:

```text
740
```

2. Enter Drug 2 NSC:

```text
750
```

3. Select cell line:

```text
786-0
```

4. Click Predict.

Expected frontend result:

```text
Prediction card appears.
ComboScore is shown.
Model used is shown.
Synergy / neutral / antagonism label is shown.
Gauge / odometer moves to prediction value.
Drug molecule structures are shown.
```

Pass condition:

```text
Frontend displays result from /api/predict correctly.
```

---

# 22. Test 20: Gauge / Odometer

After prediction, frontend gauge should show:

Left label:

```text
Strong Antagonism
```

Middle label:

```text
Neutral
```

Right label:

```text
Strong Synergy
```

Gauge value:

```text
final_predicted_COMBOSCORE
```

Pass condition:

```text
Gauge visually represents final predicted ComboScore.
```

---

# 23. Test 21: No Retraining

Search project files for training code.

The Flask app should not contain:

```text
fit(
train_test_split
RandomizedSearchCV
GridSearchCV
model.fit
```

Exception:

```text
These may appear only in comments explaining that retraining should not happen.
```

Pass condition:

```text
Backend only loads trained models and predicts.
```

Fail condition:

```text
Flask app retrains models during startup or prediction.
```

---

# 24. Test 22: Feature Shape Validation

During prediction, backend should internally verify:

```text
Feature vector shape = 1 x 526
```

Expected behavior:

If shape is wrong, return:

```json
{
  "status": "error",
  "error": "Feature vector has incorrect shape..."
}
```

Pass condition:

```text
Feature vector is always exactly 526 columns before model.predict().
```

---

# 25. Test 23: Feature Order Validation

Backend must use:

```text
data/step6_final_model_feature_columns.json
```

Pass condition:

```text
Feature dataframe columns exactly match saved feature column list before prediction.
```

Fail condition:

```text
Backend manually creates feature order and ignores JSON file.
```

---

# 26. Test 24: Output Folder Usage

Batch outputs and generated downloadable files should be saved in:

```text
outputs/
```

Pass condition:

```text
New batch prediction CSV appears inside outputs/.
```

Fail condition:

```text
Output files are saved randomly in root folder or overwrite training files.
```

---

# 27. Test 25: Data Protection

The backend must not modify these folders during normal prediction:

```text
data/
models/
results/
molecules/
final_project_summary/
predictions/
```

Allowed write folders:

```text
outputs/
uploads/
```

Pass condition:

```text
Normal prediction only reads from data/models/results/molecules/predictions and writes only to outputs/uploads when needed.
```

---

# 28. Final Backend Acceptance Checklist

Backend is accepted only if all are true:

```text
[ ] Flask starts without crashing
[ ] /api/health works
[ ] /api/cell-lines returns 60 cell lines
[ ] /api/drugs returns 100 drugs
[ ] /api/model-info/786-0 works
[ ] /api/predict works for valid input
[ ] /api/predict rejects invalid drug
[ ] /api/predict rejects invalid cell line
[ ] /api/predict rejects missing fields
[ ] correct model is selected automatically
[ ] user never selects model manually
[ ] 526 features are created
[ ] feature order comes from JSON file
[ ] forward prediction is made
[ ] reverse prediction is made
[ ] final prediction is average
[ ] prediction label is returned
[ ] gauge values are returned
[ ] batch prediction works
[ ] bad batch row does not stop whole batch
[ ] molecule structure works
[ ] molecule alias 753082 -> 761431 works
[ ] SHAP works only when requested
[ ] SHAP names are readable
[ ] demo cases work
[ ] frontend loads
[ ] frontend can call prediction API
[ ] no retraining happens
[ ] no important source files are overwritten
```

---

# 29. Final Success Message

When all tests pass, Codex should say:

```text
Backend acceptance tests passed.

The Flask backend correctly loads final Step 6 models, validates inputs, builds 526 ordered features, selects the best model per cell line, predicts forward and reverse ComboScore, averages the result, labels the prediction, supports batch prediction, molecule viewing, SHAP explanation, and demo cases.

Frontend basic Bootstrap UI is connected to the backend.
```
