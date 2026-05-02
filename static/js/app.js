const API = {
  health: "/api/health",
  drugs: "/api/drugs",
  cellLines: "/api/cell-lines",
  predict: "/api/predict",
  explain: "/api/explain",
  moleculePair: "/api/molecule-pair",
  batch: "/api/batch-predict",
  demoCases: "/api/demo-cases",
  download: "/api/download/"
};

const state = {
  shapChart: null,
  batchBlob: null,
  batchDownloadUrl: "",
  drugs: [],
  drugIds: new Set(),
  cellLines: [],
  drugsLoaded: false,
  cellLinesLoaded: false,
  drugLoadError: "",
  cellLineLoadError: "",
  demos: [],
  lastPrediction: null,
  lastExplanation: null,
  selectedBatchFile: null,
  lastBatchRendered: false,
  inlineLoaders: {}
};

const autocompleteTimers = {};
const THEME_STORAGE_KEY = "synergylens-theme";
const SAFETY_NOTE_TEXT = "This is a machine-learning screening prediction. It is not biological proof and not clinical advice. Promising synergy predictions should be validated experimentally.";
const PREDICTION_FLOW_MESSAGES = [
  "Validating inputs",
  "Building 526-feature vector",
  "Selecting best cell-line model",
  "Running NSC1 \u2192 NSC2 prediction",
  "Running NSC2 \u2192 NSC1 prediction",
  "Averaging ComboScore",
  "Preparing result"
];
const EXPLAIN_FLOW_MESSAGES = [
  "Validating prediction input",
  "Loading selected cell-line model",
  "Building 526-feature vector",
  "Computing SHAP explanation",
  "Ranking top molecular contributors",
  "Preparing explainable AI story"
];
const BATCH_FLOW_MESSAGES = [
  "Reading uploaded CSV",
  "Validating required columns",
  "Checking drug and cell-line availability",
  "Running predictions row by row",
  "Saving batch output CSV",
  "Preparing download link"
];
const DRUG_INFO_FLOW_MESSAGES = [
  "Validating drug NSC values",
  "Resolving molecule aliases",
  "Loading molecule structures",
  "Generating RDKit SVG structures",
  "Preparing compound profile cards"
];
const DEMO_ORDER = ["strong_synergy", "neutral", "antagonism"];
const DEMO_TITLES = {
  strong_synergy: "Strong Synergy",
  neutral: "Neutral",
  antagonism: "Antagonism"
};
const VALIDATION_GROUPS = {
  predict: {
    buttonId: "predict-btn",
    drugFields: [
      { inputId: "drug1-input", hiddenId: "drug1-id", messageId: "drug1-validation" },
      { inputId: "drug2-input", hiddenId: "drug2-id", messageId: "drug2-validation" }
    ],
    cellField: { selectId: "cell-line", messageId: "cell-line-validation" }
  },
  explain: {
    buttonId: "explain-btn",
    drugFields: [
      { inputId: "edrug1-input", hiddenId: "edrug1-id", messageId: "edrug1-validation" },
      { inputId: "edrug2-input", hiddenId: "edrug2-id", messageId: "edrug2-validation" }
    ],
    cellField: { selectId: "ecell-line", messageId: "ecell-line-validation" }
  },
  drugs: {
    buttonId: "drug-info-btn",
    drugFields: [
      { inputId: "ddrug1-input", hiddenId: "ddrug1-id", messageId: "ddrug1-validation" },
      { inputId: "ddrug2-input", hiddenId: "ddrug2-id", messageId: "ddrug2-validation" }
    ]
  }
};
const NEUTRAL_THRESHOLD = 20;
const SCORE_DISPLAY_MIN = -500;
const SCORE_DISPLAY_MAX = 500;

document.addEventListener("DOMContentLoaded", () => {
  bindThemeToggle();
  document.body.classList.add("is-ready");
  bindViewNavigation();
  bindAutocomplete();
  bindLiveValidation();
  bindActions();
  bindBatchUpload();
  refreshAllValidation();
  bootstrapBackendData();
});

function bindViewNavigation() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });

  document.querySelectorAll("[data-view-trigger]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.viewTrigger));
  });
}

function bindThemeToggle() {
  const toggle = document.getElementById("switch");
  if (!toggle) {
    return;
  }

  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);
  toggle.checked = initialTheme === "dark";

  toggle.addEventListener("change", () => {
    applyTheme(toggle.checked ? "dark" : "light");
  });
}

function getPreferredTheme() {
  try {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "dark" || storedTheme === "light") {
      return storedTheme;
    }
  } catch (error) {
    // Local storage can be unavailable in private or restricted browser modes.
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch (error) {
    // Keep the current session theme even if persistence fails.
  }

  refreshChartTheme();
}

function switchView(viewName) {
  document.querySelectorAll(".view").forEach((view) => {
    const isActive = view.id === `view-${viewName}`;
    view.classList.toggle("is-active", isActive);
    view.setAttribute("aria-hidden", String(!isActive));
  });

  document.querySelectorAll("[data-view]").forEach((button) => {
    const isActive = button.dataset.view === viewName;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
}

async function bootstrapBackendData() {
  await Promise.allSettled([
    loadHealth(),
    loadDrugs(),
    loadCellLines(),
    loadDemoCases()
  ]);
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json().catch(() => ({}))
    : { error: await response.text().catch(() => "") };

  if (!response.ok || data.status === "error" || data.success === false) {
    throw new Error(cleanError(data.error || data.message || `Request failed with HTTP ${response.status}.`));
  }

  return data;
}

function cleanError(message) {
  const text = String(message || "Backend request failed.");
  if (/traceback|stack trace/i.test(text)) {
    return "Backend returned an internal error. Check the Flask console for details.";
  }
  return text.length > 260 ? `${text.slice(0, 257)}...` : text;
}

async function loadHealth() {
  try {
    const health = await apiJson(API.health);
    renderBackendHealth(health);
  } catch (error) {
    renderBackendHealthError(error.message);
  }
}

function renderBackendHealth(health) {
  const availableDrugs = health.available_drugs ?? "--";
  const availableCellLines = health.available_cell_lines ?? "--";
  const availableModels = health.model_count ?? "--";
  const featureColumns = health.feature_column_count ?? "--";
  const isReady = health.status === "success";
  const errors = Array.isArray(health.errors) ? health.errors.filter(Boolean) : [];

  setText("metric-drugs", availableDrugs);
  setText("metric-cell-lines", availableCellLines);
  setText("metric-features", featureColumns);
  setText("metric-models", availableModels);
  setText("health-drugs", availableDrugs);
  setText("health-features", featureColumns);
  setText("backend-status-title", isReady ? "" : "Backend error");
  setText("backend-status", isReady ? "" : errors[0] || health.message || "Backend health check failed.");
  updateBackendHealthTone(isReady ? "success" : "danger", isReady ? "Ready" : "Error");
}

function renderBackendHealthError(message) {
  setText("backend-status-title", "Backend error");
  setText("backend-status", message || "Could not reach /api/health.");
  setText("metric-models", "--");
  setText("health-drugs", "--");
  setText("health-features", "--");
  updateBackendHealthTone("danger", "Error");
}

function updateBackendHealthTone(level, badgeText) {
  const card = document.getElementById("backend-health-card");
  const badge = document.getElementById("backend-status-badge");

  if (card) {
    card.classList.remove("is-ready", "is-error");
    card.classList.add(level === "success" ? "is-ready" : "is-error");
  }

  if (badge) {
    setToneClass(badge, level === "success" ? "success" : "danger");
    badge.textContent = badgeText;
  }
}

async function loadDrugs() {
  try {
    const data = await apiJson(API.drugs);
    state.drugs = normalizeDrugList(data);
    state.drugIds = new Set(state.drugs.map((drug) => drug.id));
    state.drugsLoaded = true;
    state.drugLoadError = "";
    refreshOpenAutocompleteLists();
    if (state.drugs.length && document.getElementById("metric-drugs")?.textContent === "--") {
      setText("metric-drugs", state.drugs.length);
    }
  } catch (error) {
    state.drugsLoaded = false;
    state.drugLoadError = error.message;
    showAlert("predict-alert", `Drug list failed to load: ${error.message}`);
  } finally {
    refreshAllValidation();
  }
}

function normalizeDrugList(data) {
  const values = Array.isArray(data) ? data : data.drugs || data.items || [];
  return values
    .map((raw) => {
      if (typeof raw === "number" || typeof raw === "string") {
        const id = String(raw).trim();
        return { id, name: `NSC ${id}` };
      }

      const id = String(raw.id ?? raw.NSC ?? raw.nsc ?? raw.drug_id ?? raw.DRUG_ID ?? "").trim();
      const rawName = raw.name ?? raw.drug_name ?? raw.NAME ?? raw.label ?? raw.NSC ?? raw.id ?? "";
      const name = String(rawName || `NSC ${id}`).trim();
      return { id, name: /^\d+$/.test(name) ? `NSC ${name}` : name };
    })
    .filter((drug) => drug.id);
}

async function loadCellLines() {
  try {
    const data = await apiJson(API.cellLines);
    state.cellLines = normalizeCellLineList(data);
    state.cellLinesLoaded = true;
    state.cellLineLoadError = "";
    fillCellLineSelect("cell-line", state.cellLines);
    fillCellLineSelect("ecell-line", state.cellLines);
    if (state.cellLines.length && document.getElementById("metric-cell-lines")?.textContent === "--") {
      setText("metric-cell-lines", state.cellLines.length);
    }
  } catch (error) {
    state.cellLinesLoaded = false;
    state.cellLineLoadError = error.message;
    fillCellLineSelect("cell-line", [], "Cell lines unavailable");
    fillCellLineSelect("ecell-line", [], "Cell lines unavailable");
    showAlert("predict-alert", `Cell-line list failed to load: ${error.message}`);
  } finally {
    refreshAllValidation();
  }
}

function normalizeCellLineList(data) {
  const values = Array.isArray(data) ? data : data.cell_lines || data.items || [];
  return values
    .map((value) => String(value ?? "").trim())
    .filter(Boolean);
}

function fillCellLineSelect(id, values, placeholder = "Select a cell line") {
  const select = document.getElementById(id);
  if (!select) {
    return;
  }

  const previousValue = select.value;
  select.innerHTML = [`<option value="">${escapeHtml(placeholder)}</option>`]
    .concat(values.map((value) => `<option value="${escapeAttribute(value)}">${escapeHtml(value)}</option>`))
    .join("");
  if (previousValue && values.includes(previousValue)) {
    select.value = previousValue;
  }
}

async function loadDemoCases() {
  try {
    const data = await apiJson(API.demoCases);
    const cases = normalizeDemoCases(data.demo_cases);
    state.demos = sortDemoCases(cases);
    renderDemoCases(state.demos);
    if (cases.length) {
      fillDemoCase(state.demos[0], { preserveExisting: true });
    }
  } catch (error) {
    renderDemoError(error.message);
  }
}

function normalizeDemoCases(rawCases) {
  if (Array.isArray(rawCases)) {
    return rawCases;
  }
  if (rawCases && typeof rawCases === "object") {
    return Object.values(rawCases);
  }
  return [];
}

function sortDemoCases(cases) {
  return [...cases].sort((a, b) => {
    const aIndex = DEMO_ORDER.indexOf(a.case_type);
    const bIndex = DEMO_ORDER.indexOf(b.case_type);
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
  });
}

function renderDemoCases(cases) {
  const container = document.getElementById("demo-cases");
  if (!container) {
    return;
  }

  if (!cases.length) {
    container.innerHTML = `<div class="demo-loading">No demo cases returned by the backend.</div>`;
    return;
  }

  container.innerHTML = cases.map((demo, index) => {
    const score = demo.predicted_score ?? demo.predicted_comboscore ?? demo.final_predicted_COMBOSCORE;
    const title = DEMO_TITLES[demo.case_type] || demo.case_type || `Demo ${index + 1}`;
    const label = demo.label || labelForScore(Number(score));
    return `
      <button class="demo-case-card" type="button" data-demo-index="${index}">
        <strong>${escapeHtml(title)}</strong>
        <span>NSC ${escapeHtml(String(demo.NSC1))} + NSC ${escapeHtml(String(demo.NSC2))}</span>
        <span>${escapeHtml(String(demo.CELLNAME))}</span>
        <span class="demo-score">${escapeHtml(formatMaybeNumber(score))} | ${escapeHtml(label)}</span>
      </button>
    `;
  }).join("");

  container.querySelectorAll("[data-demo-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const demo = state.demos[Number(button.dataset.demoIndex)];
      if (!demo) {
        return;
      }
      fillDemoCase(demo);
      container.querySelectorAll(".demo-case-card").forEach((card) => card.classList.remove("is-selected"));
      button.classList.add("is-selected");
    });
  });
}

function renderDemoError(message) {
  const container = document.getElementById("demo-cases");
  if (container) {
    container.innerHTML = `<div class="demo-loading">Demo cases unavailable: ${escapeHtml(message)}</div>`;
  }
}

function fillDemoCase(demo, options = {}) {
  const preserveExisting = Boolean(options.preserveExisting);
  const nsc1 = resolveKnownDrugId(demo.NSC1) || String(demo.NSC1 ?? "").trim();
  const nsc2 = resolveKnownDrugId(demo.NSC2) || String(demo.NSC2 ?? "").trim();
  const fields = [
    ["drug1-input", "drug1-id", nsc1],
    ["drug2-input", "drug2-id", nsc2],
    ["edrug1-input", "edrug1-id", nsc1],
    ["edrug2-input", "edrug2-id", nsc2],
    ["ddrug1-input", "ddrug1-id", nsc1],
    ["ddrug2-input", "ddrug2-id", nsc2]
  ];

  fields.forEach(([inputId, hiddenId, value]) => {
    const input = document.getElementById(inputId);
    const hidden = document.getElementById(hiddenId);
    if (input && (!preserveExisting || !input.value) && value !== undefined && value !== null) {
      input.value = `NSC ${value}`;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (hidden && (!preserveExisting || !hidden.value) && value !== undefined && value !== null) {
      hidden.value = String(value);
    }
  });

  setSelectValueWhenAvailable("cell-line", demo.CELLNAME, preserveExisting);
  setSelectValueWhenAvailable("ecell-line", demo.CELLNAME, preserveExisting);
  clearAlert("predict-alert");
  refreshAllValidation();
  window.setTimeout(refreshAllValidation, 300);
  if (!preserveExisting) {
    switchView("predict");
    document.getElementById("predict-btn")?.focus();
  }
}

function setSelectValueWhenAvailable(id, value, preserveExisting = false) {
  if (!value) {
    return;
  }

  const select = document.getElementById(id);
  if (!select) {
    return;
  }

  const apply = () => {
    if (preserveExisting && select.value) {
      return;
    }
    if (Array.from(select.options).some((option) => option.value === value)) {
      select.value = value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };

  apply();
  window.setTimeout(apply, 250);
}

function bindAutocomplete() {
  document.querySelectorAll("[data-drug-search]").forEach((input) => {
    input.addEventListener("input", () => handleDrugSearch(input));
    input.addEventListener("focus", () => handleDrugSearch(input));
    input.addEventListener("blur", () => syncDrugInputWithKnownValue(input));
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".autocomplete-wrap")) {
      closeAllAutocomplete();
    }
  });
}

function handleDrugSearch(input) {
  const query = input.value.trim();
  const listId = input.dataset.listId;
  const hiddenId = input.dataset.hiddenId;
  const list = document.getElementById(listId);
  const hidden = document.getElementById(hiddenId);

  if (!list || !hidden) {
    return;
  }

  hidden.value = "";
  clearTimeout(autocompleteTimers[listId]);

  autocompleteTimers[listId] = window.setTimeout(() => {
    if (!state.drugs.length) {
      renderAutocompleteMessage(list, "Loading valid NSC IDs...");
      return;
    }
    const matches = query.length ? searchDrugs(query) : state.drugs;
    renderDrugAutocomplete(list, input, hidden, matches);
  }, 160);
}

function searchDrugs(query) {
  const normalized = query.toLowerCase().replace(/^nsc\s*/, "").trim();
  return state.drugs.filter((drug) => (
    drug.id.includes(normalized) || drug.name.toLowerCase().includes(query.toLowerCase())
  ));
}

function refreshOpenAutocompleteLists() {
  document.querySelectorAll("[data-drug-search]").forEach((input) => {
    const list = document.getElementById(input.dataset.listId);
    if (list?.classList.contains("is-open")) {
      handleDrugSearch(input);
    }
  });
}

function renderAutocompleteMessage(list, message) {
  list.innerHTML = `<div class="autocomplete-message">${escapeHtml(message)}</div>`;
  setAutocompleteOpen(list, true);
}

function renderDrugAutocomplete(list, input, hidden, matches) {
  list.innerHTML = "";

  if (!matches.length) {
    setAutocompleteOpen(list, false);
    return;
  }

  matches.slice(0, 12).forEach((drug) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "autocomplete-item";
    item.setAttribute("role", "option");
    item.innerHTML = `
      <span>${escapeHtml(drug.name)}</span>
      <span class="autocomplete-id">${escapeHtml(drug.id)}</span>
    `;
    item.addEventListener("click", () => {
      input.value = drug.name;
      hidden.value = drug.id;
      setAutocompleteOpen(list, false);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    list.appendChild(item);
  });

  setAutocompleteOpen(list, true);
}

function setAutocompleteOpen(list, isOpen) {
  list.classList.toggle("is-open", isOpen);
  const input = document.querySelector(`[data-list-id="${list.id}"]`);
  if (input) {
    input.setAttribute("aria-expanded", String(isOpen));
  }
}

function syncDrugInputWithKnownValue(input) {
  window.setTimeout(() => {
    const hidden = document.getElementById(input.dataset.hiddenId);
    if (!hidden || hidden.value) {
      return;
    }
    const resolvedId = resolveKnownDrugId(input.value);
    if (resolvedId) {
      hidden.value = resolvedId;
      input.value = `NSC ${resolvedId}`;
      refreshAllValidation();
    }
  }, 120);
}

function closeAllAutocomplete() {
  document.querySelectorAll(".autocomplete-list").forEach((list) => {
    setAutocompleteOpen(list, false);
  });
}

function bindLiveValidation() {
  document.querySelectorAll("[data-drug-search]").forEach((input) => {
    input.addEventListener("input", refreshAllValidation);
    input.addEventListener("change", refreshAllValidation);
    input.addEventListener("blur", () => window.setTimeout(refreshAllValidation, 140));
  });

  ["cell-line", "ecell-line"].forEach((id) => {
    const select = document.getElementById(id);
    if (select) {
      select.addEventListener("change", refreshAllValidation);
      select.addEventListener("input", refreshAllValidation);
    }
  });
}

function refreshAllValidation() {
  const results = {};
  Object.entries(VALIDATION_GROUPS).forEach(([name, config]) => {
    const groupResult = validateGroup(config);
    results[name] = groupResult.valid;
    setActionAvailability(config.buttonId, groupResult.valid);
  });
  return results;
}

function validateGroup(config) {
  const drugResults = config.drugFields.map((field) => validateDrugField(field));
  const cellResult = config.cellField ? validateCellLineField(config.cellField) : { valid: true };
  return {
    valid: drugResults.every((result) => result.valid) && cellResult.valid,
    drugResults,
    cellResult
  };
}

function validateDrugField({ inputId, hiddenId, messageId }) {
  const input = document.getElementById(inputId);
  const hidden = document.getElementById(hiddenId);
  const rawValue = input?.value?.trim() || "";

  if (!state.drugsLoaded) {
    return setValidationState(input, messageId, false, "neutral", state.drugLoadError ? "Drug list unavailable" : "Loading valid drugs...");
  }

  if (!rawValue) {
    if (hidden) {
      hidden.value = "";
    }
    return setValidationState(input, messageId, false, "neutral", "Required field");
  }

  const resolvedId = resolveKnownDrugId(rawValue);
  if (!resolvedId) {
    if (hidden) {
      hidden.value = "";
    }
    return setValidationState(input, messageId, false, "invalid", "Unknown drug");
  }

  if (hidden) {
    hidden.value = resolvedId;
  }
  if (input && input.value !== `NSC ${resolvedId}` && /^\d+$/.test(rawValue)) {
    input.value = `NSC ${resolvedId}`;
  }
  return setValidationState(input, messageId, true, "valid", "Available drug");
}

function validateCellLineField({ selectId, messageId }) {
  const select = document.getElementById(selectId);
  const value = select?.value?.trim() || "";

  if (!state.cellLinesLoaded) {
    return setValidationState(select, messageId, false, "neutral", state.cellLineLoadError ? "Cell-line list unavailable" : "Loading valid cell lines...");
  }

  if (!value) {
    return setValidationState(select, messageId, false, "neutral", "Required field");
  }

  if (!state.cellLines.includes(value)) {
    return setValidationState(select, messageId, false, "invalid", "Unknown cell line");
  }

  return setValidationState(select, messageId, true, "valid", "Available cell line");
}

function setValidationState(input, messageId, isValid, tone, message) {
  const fieldGroup = input?.closest(".field-group");
  if (fieldGroup) {
    fieldGroup.classList.remove("is-valid", "is-invalid", "is-neutral");
    fieldGroup.classList.add(isValid ? "is-valid" : tone === "invalid" ? "is-invalid" : "is-neutral");
  }

  const messageElement = document.getElementById(messageId);
  if (messageElement) {
    messageElement.textContent = message;
    messageElement.classList.remove("is-valid", "is-invalid", "is-neutral");
    messageElement.classList.add(`is-${tone}`);
  }

  return { valid: isValid, message, tone };
}

function setActionAvailability(buttonId, isEnabled) {
  const button = document.getElementById(buttonId);
  if (!button || button.classList.contains("is-loading")) {
    return;
  }
  button.disabled = !isEnabled;
}

function bindActions() {
  document.getElementById("predict-btn")?.addEventListener("click", runPredict);
  document.getElementById("explain-btn")?.addEventListener("click", runExplain);
  document.getElementById("drug-info-btn")?.addEventListener("click", loadDrugInfo);
  document.getElementById("batch-run-btn")?.addEventListener("click", runSelectedBatchFile);
  document.getElementById("download-btn")?.addEventListener("click", downloadBatchResults);
}

function bindBatchUpload() {
  const zone = document.getElementById("drop-zone");
  const input = document.getElementById("csv-file");
  if (!zone || !input) {
    return;
  }

  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("is-dragging");
  });

  zone.addEventListener("dragleave", () => {
    zone.classList.remove("is-dragging");
  });

  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("is-dragging");
    const file = event.dataTransfer.files[0];
    if (file) {
      stageBatchFile(file);
    }
  });

  input.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file) {
      stageBatchFile(file);
    }
  });
}

async function runPredict() {
  clearAlert("predict-alert");

  const validation = refreshAllValidation();
  if (!validation.predict) {
    stopPredictionLoader({ restorePanel: true });
    showAlert("predict-alert", "Select valid drugs and a valid cell line before running prediction.");
    return;
  }

  const payload = buildModelPayload("drug1-id", "drug1-input", "drug2-id", "drug2-input", "cell-line");
  if (!payload) {
    stopPredictionLoader({ restorePanel: true });
    showAlert("predict-alert", getPredictionInputError("drug1-input", "drug2-input", "cell-line"));
    return;
  }

  setButtonLoading("predict-btn", "predict-btn-text", true, "Predict Synergy", "Running model");
  startPredictionLoader();

  try {
    const data = await apiJson(API.predict, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const prediction = normalizePredictionResponse(data, payload);
    state.lastPrediction = prediction;
    stopPredictionLoader();
    renderPrediction(prediction);
    syncSelectionsFromPredict();
  } catch (error) {
    stopPredictionLoader({ restorePanel: true });
    showAlert("predict-alert", error.message);
  } finally {
    setButtonLoading("predict-btn", "predict-btn-text", false, "Predict Synergy", "Running model");
    refreshAllValidation();
  }
}

function startPredictionLoader() {
  const empty = document.getElementById("results-empty");
  const content = document.getElementById("results-content");

  if (empty) {
    empty.hidden = true;
  }
  if (content) {
    content.hidden = true;
  }

  const pill = document.getElementById("score-pill");
  if (pill) {
    setToneClass(pill, "neutral");
    pill.textContent = "Running model";
  }

  startInlineLoader("prediction", PREDICTION_FLOW_MESSAGES);
}

function stopPredictionLoader(options = {}) {
  const restorePanel = Boolean(options.restorePanel);

  stopInlineLoader("prediction");
  if (restorePanel) {
    restorePredictionPanel();
  }
}

function startInlineLoader(name, messages) {
  const loader = document.getElementById(`${name}-loader`);
  if (!loader) {
    return;
  }

  clearInlineLoader(name);
  state.inlineLoaders[name] = {
    index: 0,
    messages: [...messages],
    timer: null
  };
  setInlineLoaderMessage(name);
  loader.hidden = false;

  state.inlineLoaders[name].timer = window.setInterval(() => {
    const loaderState = state.inlineLoaders[name];
    if (!loaderState) {
      return;
    }
    loaderState.index = (loaderState.index + 1) % loaderState.messages.length;
    setInlineLoaderMessage(name);
  }, 700);
}

function stopInlineLoader(name) {
  clearInlineLoader(name);
  const loader = document.getElementById(`${name}-loader`);
  if (loader) {
    loader.hidden = true;
  }
}

function clearInlineLoader(name) {
  const loaderState = state.inlineLoaders[name];
  if (loaderState?.timer) {
    window.clearInterval(loaderState.timer);
  }
  delete state.inlineLoaders[name];
}

function setInlineLoaderMessage(name) {
  const loaderState = state.inlineLoaders[name];
  const message = document.getElementById(`${name}-loader-message`);
  if (!loaderState || !message) {
    return;
  }

  message.classList.remove("is-active");
  // Restart the small text animation each time the flow advances.
  void message.offsetWidth;
  message.textContent = `${loaderState.messages[loaderState.index]}...`;
  message.classList.add("is-active");
}

function restorePredictionPanel() {
  const empty = document.getElementById("results-empty");
  const content = document.getElementById("results-content");

  if (state.lastPrediction) {
    if (empty) {
      empty.hidden = true;
    }
    if (content) {
      content.hidden = false;
    }
    const pill = document.getElementById("score-pill");
    if (pill) {
      setToneClass(pill, state.lastPrediction.level);
      pill.textContent = state.lastPrediction.label;
    }
    return;
  }

  if (empty) {
    empty.hidden = false;
  }
  if (content) {
    content.hidden = true;
  }

  const pill = document.getElementById("score-pill");
  if (pill) {
    setToneClass(pill, "neutral");
    pill.textContent = "Awaiting input";
  }
}

function buildModelPayload(drug1Hidden, drug1Input, drug2Hidden, drug2Input, cellSelect) {
  const nsc1 = resolveDrugId(drug1Hidden, drug1Input);
  const nsc2 = resolveDrugId(drug2Hidden, drug2Input);
  const cellLine = document.getElementById(cellSelect)?.value || "";

  if (!nsc1 || !nsc2 || !cellLine) {
    return null;
  }

  if (state.drugIds.size && (!state.drugIds.has(String(nsc1)) || !state.drugIds.has(String(nsc2)))) {
    return null;
  }

  if (state.cellLines.length && !state.cellLines.includes(cellLine)) {
    return null;
  }

  return {
    NSC1: Number(nsc1),
    NSC2: Number(nsc2),
    CELLNAME: cellLine,
    drug1_id: String(nsc1),
    drug2_id: String(nsc2),
    cell_line: cellLine
  };
}

function getPredictionInputError(drug1Input, drug2Input, cellSelect) {
  const drug1Text = document.getElementById(drug1Input)?.value?.trim() || "";
  const drug2Text = document.getElementById(drug2Input)?.value?.trim() || "";
  const cellLine = document.getElementById(cellSelect)?.value || "";

  if (!drug1Text || !drug2Text || !cellLine) {
    return "Select both valid NSC drugs and a cell line before running the prediction.";
  }

  const drug1Candidate = extractDrugCandidate(drug1Text);
  const drug2Candidate = extractDrugCandidate(drug2Text);
  if (state.drugIds.size && (!drug1Candidate || !state.drugIds.has(drug1Candidate))) {
    return `Drug 1 NSC ${drug1Candidate || drug1Text} is not in the loaded valid drug list.`;
  }
  if (state.drugIds.size && (!drug2Candidate || !state.drugIds.has(drug2Candidate))) {
    return `Drug 2 NSC ${drug2Candidate || drug2Text} is not in the loaded valid drug list.`;
  }
  if (state.cellLines.length && !state.cellLines.includes(cellLine)) {
    return `Cell line ${cellLine} is not in the loaded valid cell-line list.`;
  }

  return "Select both valid NSC drugs and a cell line before running the prediction.";
}

function getDrugInfoInputError(drug1Input, drug2Input) {
  const drug1Text = document.getElementById(drug1Input)?.value?.trim() || "";
  const drug2Text = document.getElementById(drug2Input)?.value?.trim() || "";

  if (!drug1Text || !drug2Text) {
    return "Select two valid NSC drugs before loading compound details.";
  }

  const drug1Candidate = extractDrugCandidate(drug1Text);
  const drug2Candidate = extractDrugCandidate(drug2Text);
  if (state.drugIds.size && (!drug1Candidate || !state.drugIds.has(drug1Candidate))) {
    return `Drug 1 NSC ${drug1Candidate || drug1Text} is not in the loaded valid drug list.`;
  }
  if (state.drugIds.size && (!drug2Candidate || !state.drugIds.has(drug2Candidate))) {
    return `Drug 2 NSC ${drug2Candidate || drug2Text} is not in the loaded valid drug list.`;
  }

  return "Select two valid NSC drugs before loading compound details.";
}

function extractDrugCandidate(value) {
  const text = String(value ?? "").trim();
  if (/^\d+$/.test(text)) {
    return text;
  }
  const match = text.match(/\b(\d{2,})\b/);
  return match ? match[1] : "";
}

function normalizePredictionResponse(data, payload) {
  const input = data.input || {};
  const score = Number(
    data.final_predicted_COMBOSCORE ??
    data.final_prediction ??
    data.predicted_comboscore ??
    data.synergy_score ??
    data.score ??
    0
  );
  const label = String(data.prediction_label ?? data.label ?? data.interpretation ?? labelForScore(score));
  const category = String(data.prediction_category ?? data.category ?? categoryForLabel(label, score));
  const color = data.color || colorForCategory(category, score);

  return {
    score,
    label,
    category,
    color,
    level: toneForCategory(category, score),
    nsc1: input.NSC1 ?? data.NSC1 ?? payload.NSC1,
    nsc2: input.NSC2 ?? data.NSC2 ?? payload.NSC2,
    cellLine: input.CELLNAME ?? data.CELLNAME ?? payload.CELLNAME,
    model: data.model_used || data.model_name || "",
    modelPath: data.model_path || "",
    forward: data.prediction_NSC1_to_NSC2,
    reverse: data.prediction_NSC2_to_NSC1,
    explanation: data.explanation || "",
    suggestion: data.suggestion || "",
    gaugeMin: SCORE_DISPLAY_MIN,
    gaugeMax: SCORE_DISPLAY_MAX
  };
}

function renderPrediction(data) {
  document.getElementById("results-empty").hidden = true;
  document.getElementById("results-content").hidden = false;

  setText("score-value", formatScore(data.score, 2));
  setText("score-label", data.label);
  document.getElementById("score-label").style.color = data.color;
  document.getElementById("score-value").style.color = data.color;
  setText("r-drug1", `NSC ${data.nsc1}`);
  setText("r-drug2", `NSC ${data.nsc2}`);
  setText("r-cell", data.cellLine);
  setText("r-cancer", "Step 6 cell-line model");
  setText("r-level", data.label);
  setText("r-cell-tile", data.cellLine);
  setText("r-cancer-tile", data.model || "Auto-selected model");
  renderPredictionStory(data);

  const pill = document.getElementById("score-pill");
  setToneClass(pill, data.level);
  pill.textContent = data.label;

  setGauge(data.score, data.color, data.gaugeMin, data.gaugeMax);
}

function renderPredictionStory(data) {
  const container = document.getElementById("score-summary");
  if (!container) {
    return;
  }

  container.innerHTML = buildPredictionStoryHtml(data);
}

function buildPredictionStoryHtml(data) {
  const storyLabel = storyLabelForPrediction(data.label, data.score);
  const forward = formatScore(data.forward, 3);
  const reverse = formatScore(data.reverse, 3);
  const finalScore = formatScore(data.score, 3);
  const scoreMeaning = scoreMeaningForScore(data.score);

  return `
    <p>
      SynergyLens evaluated the drug pair <strong>NSC ${escapeHtml(String(data.nsc1))}</strong> and
      <strong>NSC ${escapeHtml(String(data.nsc2))}</strong> for the
      <strong>${escapeHtml(data.cellLine)}</strong> cell line. The final readout below summarizes
      what the predicted ComboScore represents for this pair.
    </p>
    <div class="story-score-grid">
      <div><span>NSC ${escapeHtml(String(data.nsc1))} -&gt; NSC ${escapeHtml(String(data.nsc2))}</span><strong>${escapeHtml(forward)}</strong></div>
      <div><span>NSC ${escapeHtml(String(data.nsc2))} -&gt; NSC ${escapeHtml(String(data.nsc1))}</span><strong>${escapeHtml(reverse)}</strong></div>
      <div><span>Final averaged ComboScore</span><strong>${escapeHtml(finalScore)}</strong></div>
      <div><span>Final label</span><strong>${escapeHtml(storyLabel)}</strong></div>
    </div>
    <p>
      The same pair was scored in both drug orders because combination features are order-sensitive.
      Averaging those two directional scores gives the final ComboScore.
      This result is <strong>${escapeHtml(storyLabel)}</strong>: ${escapeHtml(scoreMeaning)}
      Positive ComboScore suggests synergy, near zero suggests neutral or additive behavior,
      and negative ComboScore suggests antagonism.
    </p>
    <p class="story-safety">${escapeHtml(SAFETY_NOTE_TEXT)}</p>
  `;
}

function storyLabelForPrediction(label, score) {
  const normalized = String(label || "").toLowerCase();
  if (normalized.includes("synerg")) {
    return "synergistic";
  }
  if (normalized.includes("antag")) {
    return "antagonistic";
  }
  if (normalized.includes("neutral") || normalized.includes("weak")) {
    return "neutral";
  }
  return semanticLabelForScore(score);
}

function semanticLabelForScore(score) {
  const value = Number(score);
  if (value >= NEUTRAL_THRESHOLD) {
    return "synergistic";
  }
  if (value <= -NEUTRAL_THRESHOLD) {
    return "antagonistic";
  }
  return "neutral";
}

function scoreMeaningForScore(score) {
  const value = Number(score);
  if (value >= NEUTRAL_THRESHOLD) {
    return "the model predicts a positive ComboScore, which means the drug pair may perform better together than expected in this cell line. This suggests a synergistic interaction.";
  }
  if (value > -NEUTRAL_THRESHOLD) {
    return "the predicted ComboScore is close to zero, which means the drug pair behaves roughly as expected from the individual drugs. This suggests neutral or additive behavior.";
  }
  return "the model predicts a negative ComboScore, which means the drug pair may perform worse together than expected in this cell line. This suggests antagonism.";
}

function setGauge(score, color, min, max) {
  const arc = document.getElementById("gauge-arc");
  if (!arc) {
    return;
  }

  const safeMin = Number.isFinite(min) ? min : SCORE_DISPLAY_MIN;
  const safeMax = Number.isFinite(max) && max > safeMin ? max : SCORE_DISPLAY_MAX;
  const clamped = Math.max(safeMin, Math.min(safeMax, Number(score)));
  const ratio = ((clamped - safeMin) / (safeMax - safeMin)) * 100;
  arc.style.strokeDashoffset = String(100 - ratio);
  arc.style.stroke = color;
}

function syncSelectionsFromPredict() {
  copyField("drug1-input", "edrug1-input");
  copyField("drug1-id", "edrug1-id");
  copyField("drug2-input", "edrug2-input");
  copyField("drug2-id", "edrug2-id");
  copyField("cell-line", "ecell-line");
  copyField("drug1-input", "ddrug1-input");
  copyField("drug1-id", "ddrug1-id");
  copyField("drug2-input", "ddrug2-input");
  copyField("drug2-id", "ddrug2-id");
}

function copyField(sourceId, targetId) {
  const source = document.getElementById(sourceId);
  const target = document.getElementById(targetId);
  if (source && target) {
    target.value = source.value;
  }
}

async function runExplain() {
  clearAlert("explain-alert");

  const validation = refreshAllValidation();
  if (!validation.explain) {
    showAlert("explain-alert", "Select valid drugs and a valid cell line before requesting the SHAP explanation.");
    return;
  }

  const payload = buildModelPayload("edrug1-id", "edrug1-input", "edrug2-id", "edrug2-input", "ecell-line");
  if (!payload) {
    showAlert("explain-alert", getPredictionInputError("edrug1-input", "edrug2-input", "ecell-line"));
    return;
  }

  setButtonLoading("explain-btn", "explain-btn-text", true, "Generate Explanation", "Computing SHAP");
  startExplainLoader();

  try {
    const data = await apiJson(API.explain, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const explanation = normalizeExplanationResponse(data);
    state.lastExplanation = explanation;
    stopExplainLoader();
    renderExplanation(explanation);
  } catch (error) {
    stopExplainLoader({ restorePanel: true });
    showAlert("explain-alert", error.message);
  } finally {
    setButtonLoading("explain-btn", "explain-btn-text", false, "Generate Explanation", "Computing SHAP");
    refreshAllValidation();
  }
}

function startExplainLoader() {
  document.getElementById("shap-empty").hidden = true;
  document.getElementById("shap-content").hidden = true;
  startInlineLoader("explain", EXPLAIN_FLOW_MESSAGES);
}

function stopExplainLoader(options = {}) {
  stopInlineLoader("explain");
  if (options.restorePanel) {
    restoreExplainPanel();
  }
}

function restoreExplainPanel() {
  const empty = document.getElementById("shap-empty");
  const content = document.getElementById("shap-content");

  if (state.lastExplanation) {
    empty.hidden = true;
    content.hidden = false;
    return;
  }

  empty.hidden = false;
  content.hidden = true;
}

function normalizeExplanationResponse(data) {
  const positive = normalizeShapRecords(
    data.top_positive_contributors || data.top_synergy_drivers || [],
    1
  );
  const negative = normalizeShapRecords(
    data.top_negative_contributors || data.top_antagonism_drivers || [],
    -1
  );
  const features = negative.concat(positive)
    .sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap))
    .slice(0, 14)
    .reverse();

  return {
    features,
    prediction: Number(data.final_predicted_COMBOSCORE ?? data.prediction ?? 0),
    baseValue: data.base_value ?? data.expected_value ?? null,
    summary: data.plain_english_explanation || data.explanation_summary || data.suggestion || ""
  };
}

function normalizeShapRecords(records, fallbackSign) {
  return records.map((record) => {
    const rawImpact = record.impact ?? record.shap_value ?? record.shap ?? 0;
    let shap = Number(rawImpact);
    if (!Number.isFinite(shap)) {
      shap = 0;
    }
    if (shap === 0 && fallbackSign) {
      shap = fallbackSign * 0.0001;
    }
    return {
      feature: String(record.readable_feature || record.feature_name || record.feature || "Feature"),
      shap,
      value: record.feature_value ?? record.value ?? ""
    };
  });
}

function renderExplanation(data) {
  document.getElementById("shap-empty").hidden = true;
  document.getElementById("shap-content").hidden = false;

  const themeColors = getThemeChartColors();
  const labels = data.features.map((feature) => feature.feature);
  const values = data.features.map((feature) => Number(feature.shap));
  const colors = values.map((value) => value >= 0 ? "rgba(15, 118, 110, 0.82)" : "rgba(199, 71, 71, 0.82)");
  const borders = values.map((value) => value >= 0 ? "rgba(15, 118, 110, 1)" : "rgba(199, 71, 71, 1)");
  const prediction = Number(data.prediction).toFixed(3);
  const baseValue = data.baseValue === null || data.baseValue === undefined
    ? "n/a"
    : Number(data.baseValue).toFixed(3);

  setText("shap-prediction", prediction);
  setText("shap-base", baseValue);
  setText("shap-base-info", data.summary || (
    data.baseValue === null || data.baseValue === undefined
      ? `Final prediction: ${prediction}. Base value was not returned by the explainer.`
      : `Base value: ${baseValue}. Final prediction: ${prediction}.`
  ));

  const chartShell = document.querySelector(".chart-shell");
  if (!window.Chart) {
    if (state.shapChart) {
      state.shapChart.destroy();
      state.shapChart = null;
    }
    renderShapFallback(chartShell, data.features);
    showAlert("explain-alert", "Chart.js did not load, so a lightweight SHAP list is shown instead.");
    return;
  }

  if (chartShell && !document.getElementById("shap-chart")) {
    chartShell.innerHTML = `<canvas id="shap-chart"></canvas>`;
  }

  if (state.shapChart) {
    state.shapChart.destroy();
  }

  const context = document.getElementById("shap-chart").getContext("2d");
  state.shapChart = new Chart(context, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: borders,
        borderWidth: 1,
        borderRadius: 8
      }]
    },
    options: {
      animation: { duration: 500 },
      maintainAspectRatio: false,
      indexAxis: "y",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => ` SHAP: ${item.parsed.x.toFixed(4)}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: themeColors.grid },
          ticks: {
            color: themeColors.tick,
            font: { family: "IBM Plex Mono", size: 11 }
          }
        },
        y: {
          grid: { display: false },
          ticks: {
            color: themeColors.label,
            font: { family: "Space Grotesk", size: 12, weight: "600" }
          }
        }
      }
    }
  });

}

function renderShapFallback(container, features) {
  if (!container) {
    return;
  }

  const rows = features.slice(0, 12).map((feature) => {
    const value = Number(feature.shap);
    const safeValue = Number.isFinite(value) ? value : 0;
    const magnitude = Math.min(100, Math.abs(safeValue) * 100);
    const direction = safeValue >= 0 ? "synergy" : "antagonism";
    const directionText = safeValue >= 0 ? "toward synergy" : "toward antagonism";
    return `
      <div class="shap-fallback-row">
        <div>
          <strong>${escapeHtml(feature.feature)}</strong>
          <span>${escapeHtml(directionText)}</span>
        </div>
        <div class="shap-fallback-bar" data-direction="${direction}">
          <i style="width: ${magnitude}%"></i>
        </div>
        <code>${escapeHtml(formatScore(value, 4))}</code>
      </div>
    `;
  }).join("");

  container.innerHTML = `<div class="shap-fallback-list">${rows || "<p>No SHAP contributors returned.</p>"}</div>`;
}

async function loadDrugInfo() {
  clearAlert("drug-alert");

  const validation = refreshAllValidation();
  if (!validation.drugs) {
    showAlert("drug-alert", "Select two valid NSC drugs before loading compound details.");
    return;
  }

  const drug1 = resolveDrugId("ddrug1-id", "ddrug1-input");
  const drug2 = resolveDrugId("ddrug2-id", "ddrug2-input");

  if (!drug1 || !drug2) {
    showAlert("drug-alert", getDrugInfoInputError("ddrug1-input", "ddrug2-input"));
    return;
  }

  setButtonLoading("drug-info-btn", "dinfo-btn-text", true, "Load Drug Details", "Loading compounds");
  startDrugInfoLoader();

  try {
    const response = await fetch(API.moleculePair, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ NSC1: Number(drug1), NSC2: Number(drug2) })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok && !data.NSC1 && !data.NSC2) {
      throw new Error(cleanError(data.error || "Molecule lookup failed."));
    }
    stopDrugInfoLoader();
    renderMoleculeCards(data);
    if (data.status === "error") {
      showAlert("drug-alert", "One or more molecules could not be rendered. See the cards for details.");
    }
  } catch (error) {
    stopDrugInfoLoader({ restorePanel: true });
    showAlert("drug-alert", error.message);
  } finally {
    setButtonLoading("drug-info-btn", "dinfo-btn-text", false, "Load Drug Details", "Loading compounds");
    refreshAllValidation();
  }
}

function startDrugInfoLoader() {
  const area = document.getElementById("drug-cards-area");
  if (area) {
    area.hidden = true;
  }
  startInlineLoader("drug", DRUG_INFO_FLOW_MESSAGES);
}

function stopDrugInfoLoader(options = {}) {
  stopInlineLoader("drug");
  const area = document.getElementById("drug-cards-area");
  if (area) {
    area.hidden = false;
  }
}

function renderMoleculeCards(data) {
  const molecules = [
    normalizeMolecule(data.NSC1 || data.molecule_1, "Drug 1"),
    normalizeMolecule(data.NSC2 || data.molecule_2, "Drug 2")
  ];
  const area = document.getElementById("drug-cards-area");
  area.innerHTML = molecules.map((molecule, index) => moleculeCardShell(molecule, index)).join("");
  molecules.forEach((molecule, index) => {
    const container = document.querySelector(`[data-molecule-slot="${index}"]`);
    if (container && molecule.svg) {
      insertSanitizedSvg(container, molecule.svg);
    }
  });
}

function normalizeMolecule(raw, title) {
  const requested = raw?.requested_nsc ?? "";
  const used = raw?.used_nsc ?? raw?.resolved_nsc ?? requested;
  return {
    title,
    ok: Boolean(raw && (raw.status === "success" || raw.molecule_found || raw.found)),
    requested,
    used,
    aliasUsed: Boolean(raw?.alias_used ?? raw?.used_alias),
    molecularFormula: raw?.molecular_formula || "",
    source: raw?.source || "",
    svg: raw?.structure_svg || raw?.svg || "",
    error: raw?.error || "Molecule structure was not found."
  };
}

function moleculeCardShell(molecule, index) {
  if (!molecule.ok) {
    return `
      <article class="drug-card">
        <div class="drug-card-header">
          <h3>${escapeHtml(molecule.title)}</h3>
          <span>${escapeHtml(molecule.error)}</span>
        </div>
      </article>
    `;
  }

  return `
    <article class="drug-card">
      <div class="drug-card-header">
        <h3>${escapeHtml(molecule.title)}: NSC ${escapeHtml(String(molecule.requested))}</h3>
        <span>${molecule.aliasUsed ? `Alias used: NSC ${escapeHtml(String(molecule.used))}` : "Direct molecule match"}</span>
      </div>
      <div class="drug-card-body">
        <div class="drug-structure" data-molecule-slot="${index}"></div>
        <div class="drug-meta">
          <div class="drug-meta-row"><span>Input Drug NSC</span><span>${escapeHtml(String(molecule.requested))}</span></div>
          <div class="drug-meta-row"><span>Structure NSC</span><span>${escapeHtml(String(molecule.used))}<small class="drug-meta-badge">${molecule.aliasUsed ? "alias used" : "direct molecule match"}</small></span></div>
          <div class="drug-meta-row"><span>Molecular Formula</span><span>${escapeHtml(molecule.molecularFormula || "n/a")}</span></div>
          <div class="drug-meta-row"><span>Structure Source</span><span>${escapeHtml(molecule.source || "n/a")}</span></div>
        </div>
      </div>
    </article>
  `;
}

function insertSanitizedSvg(container, svgText) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgText, "image/svg+xml");
  const svg = doc.documentElement;
  if (!svg || svg.nodeName.toLowerCase() !== "svg") {
    container.textContent = "SVG could not be rendered.";
    return;
  }

  svg.querySelectorAll("script, foreignObject").forEach((node) => node.remove());
  svg.querySelectorAll("*").forEach((node) => {
    Array.from(node.attributes).forEach((attribute) => {
      if (/^on/i.test(attribute.name)) {
        node.removeAttribute(attribute.name);
      }
    });
  });
  container.replaceChildren(document.importNode(svg, true));
}

function stageBatchFile(file) {
  clearAlert("batch-alert");

  if (file.size > 10 * 1024 * 1024) {
    state.selectedBatchFile = null;
    showAlert("batch-alert", "Maximum upload size is 10 MB.");
    setText("drop-zone-title", "Drop your file here");
    const runButton = document.getElementById("batch-run-btn");
    if (runButton) {
      runButton.disabled = true;
    }
    return;
  }

  state.selectedBatchFile = file;
  setText("drop-zone-title", `Selected ${file.name}`);
  setButtonLoading("batch-run-btn", "batch-run-btn-text", false, "Run Batch Prediction", "Running Batch");
}

function runSelectedBatchFile() {
  if (!state.selectedBatchFile) {
    showAlert("batch-alert", "Select a CSV file before running batch prediction.");
    return;
  }

  processBatchFile(state.selectedBatchFile);
}

async function processBatchFile(file) {
  clearAlert("batch-alert");

  if (file.size > 10 * 1024 * 1024) {
    showAlert("batch-alert", "Maximum upload size is 10 MB.");
    return;
  }

  document.getElementById("drop-zone-title").textContent = `Processing ${file.name}`;
  setButtonLoading("batch-run-btn", "batch-run-btn-text", true, "Run Batch Prediction", "Running Batch");
  startBatchLoader();

  try {
    const uploadFile = await normalizeBatchFile(file);
    const formData = new FormData();
    formData.append("file", uploadFile, uploadFile.name || file.name);

    const response = await fetch(API.batch, { method: "POST", body: formData });
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.status === "error") {
        throw new Error(cleanError(data.error || "Batch prediction failed."));
      }
      state.batchBlob = null;
      state.batchDownloadUrl = makeDownloadUrl(data.output_file);
      stopBatchLoader();
      renderBatchJson(data);
    } else {
      if (!response.ok) {
        throw new Error("Batch prediction failed.");
      }
      state.batchBlob = await response.blob();
      state.batchDownloadUrl = "";
      const csvText = await state.batchBlob.text();
      stopBatchLoader();
      renderBatchCsv(csvText);
    }

    document.getElementById("batch-empty").hidden = true;
    document.getElementById("batch-result").classList.add("is-visible");
    state.lastBatchRendered = true;
    document.getElementById("download-btn").disabled = false;
    document.getElementById("drop-zone-title").textContent = `Processed ${file.name}`;
    setButtonLoading("batch-run-btn", "batch-run-btn-text", false, "Run Again", "Running Batch");
  } catch (error) {
    stopBatchLoader({ restorePanel: true });
    showAlert("batch-alert", error.message);
    document.getElementById("drop-zone-title").textContent = `Selected ${file.name}`;
    setButtonLoading("batch-run-btn", "batch-run-btn-text", false, "Run Batch Prediction", "Running Batch");
  }
}

function startBatchLoader() {
  const empty = document.getElementById("batch-empty");
  const result = document.getElementById("batch-result");
  const download = document.getElementById("download-btn");

  if (empty) {
    empty.hidden = true;
  }
  if (result) {
    result.classList.remove("is-visible");
  }
  if (download) {
    download.disabled = true;
  }

  startInlineLoader("batch", BATCH_FLOW_MESSAGES);
}

function stopBatchLoader(options = {}) {
  stopInlineLoader("batch");
  if (options.restorePanel) {
    restoreBatchPanel();
  }
}

function restoreBatchPanel() {
  const empty = document.getElementById("batch-empty");
  const result = document.getElementById("batch-result");
  const download = document.getElementById("download-btn");

  if (state.lastBatchRendered) {
    if (empty) {
      empty.hidden = true;
    }
    if (result) {
      result.classList.add("is-visible");
    }
    if (download) {
      download.disabled = !state.batchBlob && !state.batchDownloadUrl;
    }
    return;
  }

  if (empty) {
    empty.hidden = false;
  }
  if (result) {
    result.classList.remove("is-visible");
  }
  if (download) {
    download.disabled = true;
  }
}

async function normalizeBatchFile(file) {
  const text = await file.text();
  const rows = parseCSV(text);
  if (!rows.length) {
    throw new Error("Uploaded CSV is empty.");
  }

  const headers = rows[0].map((header) => header.trim());
  const canonical = headers.map((header) => {
    const lower = header.toLowerCase();
    if (lower === "drug1_id" || lower === "drug1" || lower === "nsc1") return "NSC1";
    if (lower === "drug2_id" || lower === "drug2" || lower === "nsc2") return "NSC2";
    if (lower === "cell_line" || lower === "cellname") return "CELLNAME";
    return header;
  });

  const required = ["NSC1", "NSC2", "CELLNAME"];
  const indexes = required.map((column) => canonical.indexOf(column));
  if (indexes.some((index) => index === -1)) {
    throw new Error("CSV must include NSC1, NSC2, and CELLNAME.");
  }

  const outputRows = [required].concat(rows.slice(1).map((row) => indexes.map((index) => row[index] ?? "")));
  const csv = outputRows.map((row) => row.map(csvEscape).join(",")).join("\n");
  return new File([csv], file.name.replace(/\.csv$/i, "") + "_normalized.csv", { type: "text/csv" });
}

function renderBatchJson(data) {
  const rows = data.preview || [];
  const scores = rows
    .map((row) => Number(row.final_predicted_COMBOSCORE))
    .filter((value) => Number.isFinite(value));
  const averageScore = scores.length
    ? (scores.reduce((sum, value) => sum + value, 0) / scores.length).toFixed(2)
    : "n/a";

  document.getElementById("batch-stats").innerHTML = `
    <article class="stat-card"><strong>${escapeHtml(String(data.total_rows ?? rows.length))}</strong><span>Total Rows</span></article>
    <article class="stat-card"><strong>${escapeHtml(String(data.successful_rows ?? 0))}</strong><span>Successful</span></article>
    <article class="stat-card"><strong>${escapeHtml(String(data.failed_rows ?? 0))}</strong><span>Failed</span></article>
    <article class="stat-card"><strong>${escapeHtml(String(averageScore))}</strong><span>Preview Avg</span></article>
  `;

  renderBatchTable(rows);
}

function renderBatchCsv(csvText) {
  const rows = parseCSV(csvText);
  if (!rows.length) {
    showAlert("batch-alert", "The returned CSV preview was empty.");
    return;
  }

  const headers = rows[0];
  const dataRows = rows.slice(1);
  const scoreIndex = headers.indexOf("final_predicted_COMBOSCORE");
  const scores = dataRows.map((row) => Number.parseFloat(row[scoreIndex])).filter((value) => Number.isFinite(value));
  const averageScore = scores.length ? (scores.reduce((sum, value) => sum + value, 0) / scores.length).toFixed(2) : "n/a";

  document.getElementById("batch-stats").innerHTML = `
    <article class="stat-card"><strong>${dataRows.length}</strong><span>Total Rows</span></article>
    <article class="stat-card"><strong>${scores.length}</strong><span>Scored Rows</span></article>
    <article class="stat-card"><strong>${averageScore}</strong><span>Average Score</span></article>
    <article class="stat-card"><strong>CSV</strong><span>Download Ready</span></article>
  `;

  const objects = dataRows.slice(0, 50).map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])));
  renderBatchTable(objects);
}

function renderBatchTable(rows) {
  const tableHead = document.getElementById("batch-thead");
  const tableBody = document.getElementById("batch-tbody");

  if (!rows.length) {
    tableHead.innerHTML = "";
    tableBody.innerHTML = `<tr><td>No preview rows returned.</td></tr>`;
    return;
  }

  const headers = Object.keys(rows[0]);
  tableHead.innerHTML = headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
  tableBody.innerHTML = rows.slice(0, 50).map((row) => `
    <tr>
      ${headers.map((header) => {
        const value = row[header] ?? "";
        if (header === "prediction_label" || header === "label") {
          return `<td>${renderBadge(batchLabelForRow(row, value))}</td>`;
        }
        if (header === "status") {
          return `<td>${renderBadge(value)}</td>`;
        }
        if (header === "final_predicted_COMBOSCORE") {
          return `<td class="mono">${escapeHtml(formatMaybeNumber(value))}</td>`;
        }
        return `<td>${escapeHtml(String(value))}</td>`;
      }).join("")}
    </tr>
  `).join("");
}

function batchLabelForRow(row, fallbackLabel) {
  const score = Number(row.final_predicted_COMBOSCORE);
  return Number.isFinite(score) ? semanticLabelForScore(score) : fallbackLabel;
}

function downloadBatchResults() {
  if (state.batchBlob) {
    const url = URL.createObjectURL(state.batchBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "synergy_predictions.csv";
    link.click();
    URL.revokeObjectURL(url);
    return;
  }

  if (state.batchDownloadUrl) {
    const link = document.createElement("a");
    link.href = state.batchDownloadUrl;
    link.download = "synergy_predictions.csv";
    link.click();
  }
}

function makeDownloadUrl(outputFile) {
  const filename = String(outputFile || "").split(/[\\/]/).pop();
  return filename ? `${API.download}${encodeURIComponent(filename)}` : "";
}

function renderBadge(label) {
  const normalized = String(label || "").toLowerCase();
  let className = "badge badge-neutral";

  if (normalized.includes("synergy") || normalized.includes("synerg") || normalized === "success") {
    className = "badge badge-synergy";
  } else if (normalized.includes("weak") || normalized.includes("neutral")) {
    className = "badge badge-mild";
  } else if (normalized.includes("antag") || normalized === "error" || normalized.includes("fail")) {
    className = "badge badge-antag";
  }

  return `<span class="${className}">${escapeHtml(String(label || ""))}</span>`;
}

function showAlert(id, message) {
  const alert = document.getElementById(id);
  if (!alert) {
    return;
  }
  alert.textContent = message;
  alert.hidden = false;
}

function clearAlert(id) {
  const alert = document.getElementById(id);
  if (!alert) {
    return;
  }
  alert.hidden = true;
  alert.textContent = "";
}

function resolveDrugId(hiddenId, inputId) {
  const hiddenValue = document.getElementById(hiddenId)?.value?.trim() || "";
  if (hiddenValue && (!state.drugIds.size || state.drugIds.has(hiddenValue))) {
    return hiddenValue;
  }

  const typedValue = document.getElementById(inputId)?.value?.trim() || "";
  return resolveKnownDrugId(typedValue);
}

function resolveKnownDrugId(value) {
  const typedValue = String(value ?? "").trim();
  if (/^\d+$/.test(typedValue)) {
    return state.drugIds.size && !state.drugIds.has(typedValue) ? "" : typedValue;
  }

  const match = typedValue.match(/\b(\d{2,})\b/);
  if (match) {
    const matchedId = match[1];
    return state.drugIds.size && !state.drugIds.has(matchedId) ? "" : matchedId;
  }

  const exactNameMatch = state.drugs.find((drug) => drug.name.toLowerCase() === typedValue.toLowerCase());
  return exactNameMatch?.id || "";
}

function setButtonLoading(buttonId, textId, isLoading, idleText, loadingText = idleText) {
  const button = document.getElementById(buttonId);
  const text = document.getElementById(textId);
  if (!button || !text) {
    return;
  }
  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
  text.textContent = isLoading ? loadingText : idleText;
}

function setToneClass(element, level) {
  if (!element) {
    return;
  }
  element.classList.remove("tone-success", "tone-good", "tone-mild", "tone-neutral", "tone-danger");
  element.classList.add(`tone-${level || "neutral"}`);
}

function categoryForLabel(label, score) {
  const normalized = String(label || "").toLowerCase();
  if (normalized.includes("strong") && normalized.includes("synergy")) return "strong_synergy";
  if (normalized.includes("moderate") && normalized.includes("synergy")) return "moderate_synergy";
  if (normalized.includes("strong") && normalized.includes("antag")) return "strong_antagonism";
  if (normalized.includes("moderate") && normalized.includes("antag")) return "moderate_antagonism";
  if (normalized.includes("synerg")) return "moderate_synergy";
  if (normalized.includes("antag")) return "moderate_antagonism";
  if (Number(score) >= 80) return "strong_synergy";
  if (Number(score) >= NEUTRAL_THRESHOLD) return "moderate_synergy";
  if (Number(score) <= -80) return "strong_antagonism";
  if (Number(score) <= -NEUTRAL_THRESHOLD) return "moderate_antagonism";
  return "neutral";
}

function labelForScore(score) {
  if (score >= 80) return "Strong Synergy";
  if (score >= NEUTRAL_THRESHOLD) return "Moderate Synergy";
  if (score > -NEUTRAL_THRESHOLD) return "Neutral / Weak effect";
  if (score > -80) return "Moderate Antagonism";
  return "Strong Antagonism";
}

function colorForCategory(category, score) {
  const normalized = String(category || categoryForLabel("", score)).toLowerCase();
  if (normalized.includes("synergy")) return "#0f766e";
  if (normalized.includes("antagonism")) return "#c74747";
  return "#b7791f";
}

function toneForCategory(category, score) {
  const normalized = String(category || categoryForLabel("", score)).toLowerCase();
  if (normalized.includes("strong_synergy")) return "success";
  if (normalized.includes("synergy")) return "good";
  if (normalized.includes("antagonism")) return "danger";
  return "neutral";
}

function parseCSV(text) {
  const rows = [];
  let row = [];
  let value = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === "\"") {
      if (inQuotes && nextChar === "\"") {
        value += "\"";
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      row.push(value);
      value = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && nextChar === "\n") {
        i += 1;
      }
      row.push(value);
      if (row.some((cell) => cell !== "")) {
        rows.push(row);
      }
      row = [];
      value = "";
    } else {
      value += char;
    }
  }

  if (value !== "" || row.length) {
    row.push(value);
    rows.push(row);
  }

  return rows;
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, "\"\"")}"`;
  }
  return text;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function formatScore(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : String(value ?? "");
}

function formatMaybeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : String(value ?? "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

function getThemeChartColors() {
  const styles = window.getComputedStyle(document.body);
  return {
    grid: styles.getPropertyValue("--chart-grid").trim() || "rgba(24, 49, 44, 0.07)",
    tick: styles.getPropertyValue("--chart-tick").trim() || "#60746e",
    label: styles.getPropertyValue("--chart-label").trim() || "#18312c"
  };
}

function refreshChartTheme() {
  if (!state.shapChart) {
    return;
  }

  const themeColors = getThemeChartColors();
  state.shapChart.options.scales.x.grid.color = themeColors.grid;
  state.shapChart.options.scales.x.ticks.color = themeColors.tick;
  state.shapChart.options.scales.y.ticks.color = themeColors.label;
  state.shapChart.update();
}
