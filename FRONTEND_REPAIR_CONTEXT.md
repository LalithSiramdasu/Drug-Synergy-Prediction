# FRONTEND_REPAIR_CONTEXT.md

## Purpose

This file is the handoff context for continuing the frontend repair work in VS Code / Codex. It summarizes the current verified backend state, the current frontend files, the screenshots that show the present UI, the likely integration mismatches, and the exact repair/testing goals.

Use this file as the first thing to read before editing the project.

---

## Project

Project folder on Windows:

```text
C:\Users\HP\Desktop\SDP 27 april\nci_almanac_flask_app
```

App name shown in the UI: **SynergyLens**

App goal: A Flask web app for drug-combination synergy prediction, SHAP explanation, compound information lookup, and batch CSV prediction.

Main frontend files currently reviewed:

```text
static/templates or templates: index.html
static/css/app.css
static/js/app.js
```

The uploaded files reviewed for this context were:

```text
index.html
app.css
app.js
```

The uploaded screenshots reviewed show four frontend tabs:

```text
Predict
Explain
Drug Info
Batch
```

---

## Backend status already verified by user

The backend is running locally and the health endpoint is working.

User ran:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

Returned summary:

```text
status: success
message: Backend is ready
available_cell_lines: 60
available_drugs: 100
expected_available_cell_lines: 60
expected_available_drugs: 100
model_count: 60
expected_model_count: 60
feature_column_count: 526
models_dir_exists: True
model_registry_exists: True
model_registry_loaded: True
drug_features_exists: True
drug_features_loaded: True
feature_columns_exists: True
feature_columns_loaded: True
errors: {}
```

User also ran:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/demo-cases
```

Returned:

```text
count: 3
demo_cases: 3 rows
```

The first shown demo case includes fields like:

```text
CELLNAME = HL-60(TB)
NSC1 = 92859
NSC2 = 141540
actual_comboscore = -727.0...
```

Important conclusion: **backend is ready**. Do not assume the model is broken just because the UI is empty or not wired.

---

## Screenshot observations

### 1. Predict tab screenshot

Visible UI state:

- Hero title: `SynergyLens`
- Subtitle: `Predict drug-combination synergy, inspect SHAP feature impact, review compound metadata, and process batch CSV files from one polished interface.`
- Hero cards show:
  - Drugs: `86 indexed compounds`
  - Cell Lines: `38 prediction contexts`
  - Cancer Types: `9 optional labels`
  - Pipeline: `ML + SHAP`
- Predict tab is active.
- Input panel contains:
  - Drug 1 autocomplete input
  - Drug 2 autocomplete input
  - Cell Line select
  - Cancer Type select
  - `Predict Synergy` button
- Output area starts in empty state:
  - `No prediction yet`
  - Gauge shows `0.00 Awaiting input`
  - Drug pair placeholders: `Drug 1 + Drug 2`
  - Response / Cell Line / Cancer all show pending

Issue visible from screenshot:

- Frontend hero stats are stale: screenshot says **86 drugs / 38 cell lines**, but backend health says **100 drugs / 60 cell lines**.
- This must be repaired. Do not hard-code 86 or 38.

### 2. Explain tab screenshot

Visible UI state:

- Explain tab is active.
- Left panel: `SHAP Feature Impact`
- Inputs:
  - Drug 1 autocomplete
  - Drug 2 autocomplete
  - Cell Line select
  - Cancer Type select
  - `Generate Explanation` button
- Right panel: `Contribution Map`
- Empty state says:
  - `Explanation panel ready`
  - `Run an explanation request to render the top SHAP features.`
- Bottom meta placeholders:
  - Prediction: `--`
  - Base Value: `--`

Repair goal:

- The Explain tab should call the actual backend SHAP/explain endpoint and render a Chart.js horizontal bar chart.
- It must use a valid demo case as a smoke test.

### 3. Drug Info tab screenshot

Visible UI state:

- Drug Info tab is active.
- Left panel: `Compound Lookup`
- Inputs:
  - Drug 1 autocomplete
  - Drug 2 autocomplete
  - `Load Drug Details` button
- Right panel: `Compound Profiles`
- Empty state says:
  - `No drug cards yet`
  - `Load two compounds to compare molecular details.`

Repair goal:

- Drug Info must call the real backend compound/molecule/drug metadata route.
- If the backend route name differs from the current JS route, update the JS or add a small compatibility route.
- It should render two cards with structure image and metadata when possible.

### 4. Batch tab screenshot

Visible UI state:

- Batch tab is active.
- Main panel: `CSV Upload`
- Upload area says:
  - `DROP YOUR FILE HERE`
  - `OR CLICK TO BROWSE. MAXIMUM UPLOAD SIZE: 10 MB.`
  - expected columns displayed as `DRUG1_ID, DRUG2_ID, CELL_LINE, CANCER_TYPE(OPTIONAL)`
- Checklist says:
  1. Include `drug1_id`, `drug2_id`, and `cell_line` in every CSV row.
  2. Use `cancer_type` only when you want to provide supported disease context.
  3. The preview table below mirrors the downloadable CSV returned by the backend.
- Results section starts empty:
  - `Batch results will appear here`
  - `Process a CSV to unlock the preview and download action.`

Repair goal:

- Batch upload must call the actual backend batch endpoint and display a preview table.
- Download CSV should save the backend-returned CSV blob.
- Expected CSV headers must match the backend exactly.

---

## Current frontend structure observed from index.html

The current `index.html` is a Flask/Jinja-rendered single-page interface.

Important details:

- It loads fonts from Google Fonts.
- It loads Chart.js from CDN:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js" defer></script>
```

- It loads the app assets through Flask static URLs:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">
<script src="{{ url_for('static', filename='js/app.js') }}" defer></script>
```

- The hero metric cards are currently rendered by Jinja variables:

```html
{{ drugs|length }}
{{ cell_lines|length }}
{{ cancers|length }}
```

Because the screenshot shows `86` drugs and `38` cell lines while `/api/health` shows `100` drugs and `60` cell lines, inspect the Flask route that renders `index.html`. The template context is probably using old/partial data, or the template is being rendered with frontend-only lists that do not match backend-ready data.

The page has four view sections:

```text
#view-predict
#view-explain
#view-drugs
#view-batch
```

The tab buttons use:

```text
data-view="predict"
data-view="explain"
data-view="drugs"
data-view="batch"
```

The hero buttons use:

```text
data-view-trigger="predict"
data-view-trigger="batch"
```

Prediction inputs:

```text
drug1-input / drug1-id / drug1-list
drug2-input / drug2-id / drug2-list
cell-line
cancer-type
predict-btn
```

Explanation inputs:

```text
edrug1-input / edrug1-id / edrug1-list
edrug2-input / edrug2-id / edrug2-list
ecell-line
ecancer-type
explain-btn
```

Drug info inputs:

```text
ddrug1-input / ddrug1-id / ddrug1-list
ddrug2-input / ddrug2-id / ddrug2-list
drug-info-btn
drug-cards-area
```

Batch inputs/results:

```text
drop-zone
csv-file
batch-alert
batch-empty
batch-result
batch-table
batch-rows
batch-average
batch-download-name
download-btn
```

---

## Current frontend behavior observed from app.js

The current `app.js` is intended to handle:

- Theme toggle with localStorage key `synergylens-theme`
- View tab switching
- Drug autocomplete
- Prediction request
- Prediction result rendering
- SHAP explanation request and Chart.js rendering
- Drug info lookup
- Batch upload, preview, and CSV download

Current endpoint assumptions in `app.js`:

```text
GET  /api/drugs?q=<query>
POST /api/predict
POST /api/explain
GET  /api/drug_info/<drug_id>
POST /api/batch
```

These endpoint names must be cross-checked against the real Flask routes in `app.py` or route files.

Already verified backend routes from user commands:

```text
GET /api/health
GET /api/demo-cases
```

Do not assume `/api/drugs`, `/api/drug_info/<id>`, or `/api/batch` exist until you inspect the backend.

---

## Most likely frontend/backend mismatch points

### 1. Hero metrics are stale

Observed mismatch:

```text
Frontend screenshot: Drugs = 86, Cell Lines = 38
Backend health:      Drugs = 100, Cell Lines = 60
```

Fix options:

1. Best: render `index.html` using the same backend source as `/api/health` and the actual prediction data.
2. Alternative: add IDs to metric values and update them on page load from `/api/health`.
3. Do not hard-code 100/60 either. The UI should read live backend values.

Recommended metric IDs:

```html
<strong id="metric-drugs" class="metric-value">...</strong>
<strong id="metric-cell-lines" class="metric-value">...</strong>
<strong id="metric-cancer-types" class="metric-value">...</strong>
```

Then in JS:

```js
fetch('/api/health')
```

and update `available_drugs`, `available_cell_lines`.

Cancer type count may still come from template or a metadata endpoint; inspect backend.

### 2. Autocomplete may be calling a route that does not exist

Current JS calls:

```js
fetch(`/api/drugs?q=${encodeURIComponent(query)}`)
```

Expected return shape in current JS:

```json
[
  { "id": "92859", "name": "Drug Name" }
]
```

If backend uses `NSC` identifiers or a different shape, normalize it in one place.

Recommended robust frontend normalizer:

```js
function normalizeDrugOption(raw) {
  return {
    id: String(raw.id ?? raw.NSC ?? raw.nsc ?? raw.drug_id ?? raw.DRUG_ID ?? ''),
    name: String(raw.name ?? raw.drug_name ?? raw.NAME ?? raw.label ?? raw.NSC ?? raw.id ?? '')
  };
}
```

### 3. Prediction response shape must be verified

Current JS expects prediction response like:

```json
{
  "success": true,
  "score": 12.34,
  "label": "Synergy",
  "level": "positive",
  "color": "#...",
  "drug1_name": "...",
  "drug2_name": "...",
  "cell_line": "...",
  "cancer_type": "..."
}
```

But backend may return fields such as:

```text
prediction
predicted_comboscore
synergy_score
comboscore
interpretation
response
```

Repair requirement:

- Inspect actual `/api/predict` response using `/api/demo-cases`.
- Update `renderPrediction()` to use the real shape or create a small `normalizePredictionResponse(data)` function.
- Do not break the backend if backend is already correct.

### 4. Score interpretation must follow ComboScore direction

Current JS uses frontend thresholds in `buildInterpretationSummary()`:

```text
score > 10  => strong positive interaction
score > 5   => meaningful synergy
score > 0   => mild synergy
score > -5  => close to additive
else        => antagonistic
```

ComboScore is `Expected growth - Observed percent growth`. Positive ComboScore suggests synergy, negative ComboScore suggests antagonism, and values near zero suggest neutral or additive behavior. Score ranges can be much wider than `-20 to +20`, so the UI should show the raw score and use a clear neutral band.

Repair requirement:

- Prefer backend-provided `label`, `interpretation`, `level`, and `color` if available.
- If the backend does not provide them, use the project ComboScore rule: positive means synergy, negative means antagonism, near zero means neutral.
- Make the frontend display the model score and backend label faithfully.

### 5. Gauge scale is probably too narrow

Current JS gauge clamps to:

```js
const min = -20;
const max = 20;
```

But demo data includes a ComboScore around `-727`. This means the gauge can saturate and become misleading.

Repair options:

- Use backend-provided normalized score if available.
- Or create a display transform for large ComboScore values.
- Or set gauge min/max from observed/backend metadata.
- At minimum, do not hide the actual raw score.

### 6. Drug Info endpoint may be mismatched

Current JS calls:

```js
fetch(`/api/drug_info/${drug1}`)
fetch(`/api/drug_info/${drug2}`)
```

Expected current JS response shape:

```json
{
  "success": true,
  "id": "92859",
  "name": "...",
  "img_url": "...",
  "formula": "...",
  "weight": "...",
  "iupac": "..."
}
```

Inspect backend routes. If backend route is named differently, fix JS or add compatibility route.

### 7. Batch endpoint may be mismatched

Current JS calls:

```js
POST /api/batch
```

and expects a CSV blob back.

The UI says expected headers are:

```text
drug1_id, drug2_id, cell_line, cancer_type
```

But the dataset/demo case fields use:

```text
NSC1, NSC2, CELLNAME
```

Repair requirement:

- Inspect the actual backend batch endpoint and accepted headers.
- Make the UI checklist and parser match the backend exactly.
- It is okay to support aliases, for example:

```text
drug1_id or NSC1
drug2_id or NSC2
cell_line or CELLNAME
cancer_type optional
```

### 8. Batch preview parsing is simple and may break quoted CSV

Current JS has a custom `parseCSV()` implementation. If backend returns simple CSV, this may be okay. If CSV can contain commas inside quoted values, test carefully.

Repair requirement:

- Use returned CSV from backend and verify preview rows render.
- If parsing fails, improve parser or return JSON preview separately.

---

## Preserve current UI design

The screenshots show a polished dark/light glassmorphism UI. Preserve it unless a functional fix requires small changes.

Do not redesign the page.

Preserve:

- Large SynergyLens hero
- Rounded cards/panels
- Gradient active tabs/buttons
- Dark/light theme toggle
- Four-tab single-page layout
- Gauge card
- Chart.js SHAP chart
- Drag/drop batch area

Allowed UI edits:

- Add missing IDs to metric values
- Add small loading/error states
- Add backend-readiness indicators if useful
- Fix labels so they match backend data
- Fix expected CSV text if backend headers differ
- Make autocomplete visible/usable
- Improve responsive behavior only if currently broken

---

## Recommended Codex task prompt

Use this prompt in Codex VS Code extension:

```text
Read FRONTEND_REPAIR_CONTEXT.md first. Then inspect app.py/routes and the current frontend files index.html, static/css/app.css, and static/js/app.js.

The backend health endpoint is already verified working: /api/health returns success with 60 cell lines, 100 drugs, 60 models, and 526 feature columns. /api/demo-cases returns 3 demo cases. The frontend screenshots currently show stale hero metrics 86 drugs and 38 cell lines, empty tabs, and likely endpoint/data-shape mismatches.

Repair the frontend-backend integration without redesigning the UI.

Goals:
1. Make hero stats reflect live backend values, not stale hard-coded/template values.
2. Make drug autocomplete work with the actual backend drug search/list endpoint. If no endpoint exists, add a minimal Flask API route using the existing loaded drug data.
3. Make Predict work using a demo case from /api/demo-cases and the actual /api/predict response shape.
4. Make Explain work and render the SHAP chart using the actual /api/explain response shape.
5. Make Drug Info work against the actual backend compound/molecule metadata route. If the route name differs from app.js, fix the frontend or add a compatibility route.
6. Make Batch upload work against the actual backend batch endpoint. Ensure the expected CSV headers in the UI match what backend accepts.
7. Use the corrected ComboScore sign convention: positive means synergy, negative means antagonism, near zero means neutral. Use backend-provided label/interpretation where possible.
8. Keep the current visual design in app.css.

After implementing, cross-verify your own work:
- Run Python/Flask startup check.
- Run PowerShell/curl endpoint tests for /api/health, /api/demo-cases, autocomplete/list endpoint, /api/predict, /api/explain, drug info, and batch if possible.
- Run a JS syntax check if Node is available: node --check static/js/app.js
- Manually test the four UI tabs in the browser.
- Debug and fix any errors you find.

Only report completion after tests pass. Include the exact files changed and exact commands/tests run.
```

---

## Step-by-step tests to run after repair

Run Flask first from project root:

```powershell
cd "C:\Users\HP\Desktop\SDP 27 april\nci_almanac_flask_app"
python app.py
```

In another PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
Invoke-RestMethod http://127.0.0.1:5000/api/demo-cases
```

Expected health values:

```text
status = success
available_cell_lines = 60
available_drugs = 100
model_count = 60
feature_column_count = 526
```

Use demo case for prediction:

```powershell
$demo = Invoke-RestMethod http://127.0.0.1:5000/api/demo-cases
$case = $demo.demo_cases[0]
$body = @{
  drug1_id = "$($case.NSC1)"
  drug2_id = "$($case.NSC2)"
  cell_line = "$($case.CELLNAME)"
  cancer_type = ""
} | ConvertTo-Json
Invoke-RestMethod -Method POST `
  -Uri http://127.0.0.1:5000/api/predict `
  -ContentType "application/json" `
  -Body $body
```

Use same demo case for explanation:

```powershell
Invoke-RestMethod -Method POST `
  -Uri http://127.0.0.1:5000/api/explain `
  -ContentType "application/json" `
  -Body $body
```

Test JS syntax if Node exists:

```powershell
node --check static\js\app.js
```

Manual browser tests:

```text
http://127.0.0.1:5000/
```

Checklist:

- Hero stats show backend-ready counts, not old 86/38 values.
- Predict tab: select two drugs and a cell line, click Predict Synergy, result appears.
- Explain tab: same pair/context, click Generate Explanation, SHAP bars appear.
- Drug Info tab: select two drugs, click Load Drug Details, two compound cards appear or clear error message appears.
- Batch tab: upload CSV with accepted columns, preview table appears, Download CSV enables.
- Browser console has no JavaScript errors.
- Network tab has no 404 for frontend API calls.

---

## Minimal batch CSV for testing

Create a file like:

```csv
drug1_id,drug2_id,cell_line,cancer_type
92859,141540,HL-60(TB),
```

If backend expects dataset names instead of frontend names, support aliases or update this UI text after verifying backend.

Possible backend/dataset aliases:

```text
drug1_id -> NSC1
drug2_id -> NSC2
cell_line -> CELLNAME
```

---

## Important repair notes

### Do not rely on screenshot values

The screenshots are useful for visual state only. Backend `/api/health` is the source of truth for readiness counts.

### Do not re-train or touch model files

Backend health says model files and feature files are loaded. This is frontend integration repair, not model repair.

### Keep a compatibility approach

If frontend and backend endpoint names differ, either:

1. Update frontend to use existing backend routes, or
2. Add small compatibility routes in Flask that map to the existing backend logic.

Do not duplicate model prediction logic in frontend.

### Normalize API responses in one place

Recommended frontend pattern:

```js
function normalizePredictionResponse(data) { ... }
function normalizeDrugOption(raw) { ... }
function normalizeExplanationResponse(data) { ... }
function normalizeDrugInfoResponse(data) { ... }
```

This keeps the rendering code clean and makes frontend tolerant to backend field names.

### Always show clear errors

Current UI has alert containers:

```text
predict-alert
explain-alert
drug-alert
batch-alert
```

Use these instead of silent failures.

### Avoid silent autocomplete failure

Current autocomplete catches errors and closes the list silently. During repair/testing, show a console warning or visible alert if the drug endpoint fails. Silent failure makes debugging hard.

---

## Files to inspect first in project

Start with:

```text
app.py
flask.py if present
routes files if present
templates/index.html
static/js/app.js
static/css/app.css
```

Search commands:

```powershell
Select-String -Path .\*.py -Pattern "@app.route|Blueprint|api/health|api/demo|api/predict|api/explain|api/drug|api/batch" -CaseSensitive:$false
Select-String -Path .\static\js\app.js -Pattern "fetch\(|api/" -CaseSensitive:$false
```

If using bash/Git Bash:

```bash
grep -R "@app.route\|Blueprint\|api/health\|api/demo\|api/predict\|api/explain\|api/drug\|api/batch" -n . --include="*.py"
grep -n "fetch(\|api/" static/js/app.js
```

---

## Final acceptance criteria

The repair is complete only when all are true:

1. `/api/health` still returns `status: success`.
2. Frontend hero counts match backend values: 100 drugs and 60 cell lines, or whatever `/api/health` returns live.
3. Drug autocomplete returns real project drugs and fills hidden IDs.
4. Prediction succeeds from the UI using a demo case.
5. Explanation succeeds from the UI and renders the SHAP chart.
6. Drug Info either renders real compound profiles or shows a truthful backend metadata error without crashing.
7. Batch upload accepts the documented CSV format and returns preview/download.
8. No JavaScript console errors.
9. No 404 API calls from the frontend.
10. Codex reports files changed and exact test commands it ran.

---

## Current known good backend facts to keep in mind

```text
available_drugs = 100
available_cell_lines = 60
model_count = 60
feature_column_count = 526
health message = Backend is ready
```

If the UI says otherwise, fix the UI/template/API wiring first.
