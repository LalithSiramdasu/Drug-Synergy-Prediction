const API = {
  health: "/api/health",
  drugs: "/api/drugs",
  cellLines: "/api/cell-lines",
  predict: "/api/predict",
  moleculePair: "/api/molecule-pair",
  explain: "/api/explain",
  batch: "/api/batch-predict",
  demoCases: "/api/demo-cases",
  download: "/api/download/"
};

const STORAGE = {
  theme: "synergylens-theme",
  recent: "synergylens-recent-predictions"
};

const DEMO_ORDER = ["strong_synergy", "neutral", "antagonism"];
const DEMO_TITLES = {
  strong_synergy: "Strong Synergy",
  neutral: "Neutral",
  antagonism: "Antagonism"
};
const GAUGE_MIN = -500;
const GAUGE_MAX = 500;
const NEUTRAL_THRESHOLD = 20;

const state = {
  drugs: new Set(),
  cellLines: new Set(),
  demos: [],
  currentPayload: null,
  currentPrediction: null,
  flowTimer: null,
  scoreAnimationFrame: null
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  initTheme();
  bindEvents();
  renderRecentPredictions();
  bootstrapPage();
});

function cacheElements() {
  [
    "backendStatus",
    "themeToggle",
    "metricDrugs",
    "metricCells",
    "metricModels",
    "predictionForm",
    "nsc1Input",
    "nsc2Input",
    "cellLineInput",
    "drugList",
    "nsc1Message",
    "nsc2Message",
    "cellLineMessage",
    "resetButton",
    "demoButtons",
    "flowSteps",
    "toastArea",
    "resultLabel",
    "finalScore",
    "gaugeNeedle",
    "resultFacts",
    "resultStory",
    "recentPredictions",
    "clearRecentButton",
    "explainButton",
    "explainContent",
    "moleculeStatus",
    "moleculeGrid",
    "batchFile",
    "batchUploadButton",
    "sampleCsvButton",
    "batchResult"
  ].forEach((id) => {
    els[id] = document.getElementById(id);
  });
}

function bindEvents() {
  els.themeToggle?.addEventListener("click", toggleTheme);
  els.predictionForm?.addEventListener("submit", handlePredictionSubmit);
  els.resetButton?.addEventListener("click", resetPredictionWorkspace);
  els.nsc1Input?.addEventListener("input", validatePredictionForm);
  els.nsc2Input?.addEventListener("input", validatePredictionForm);
  els.cellLineInput?.addEventListener("change", validatePredictionForm);
  els.explainButton?.addEventListener("click", handleExplain);
  els.batchUploadButton?.addEventListener("click", handleBatchUpload);
  els.sampleCsvButton?.addEventListener("click", downloadSampleCsv);
  els.clearRecentButton?.addEventListener("click", clearRecentPredictions);

  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tabTarget, true));
  });
}

async function bootstrapPage() {
  // Page bootstrap data flow:
  // health populates status/metrics, drugs and cell lines power live validation,
  // and demo cases become quick-load cards inside the prediction workspace.
  await Promise.allSettled([
    loadHealth(),
    loadDrugs(),
    loadCellLines(),
    loadDemoCases()
  ]);
  validatePredictionForm();
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json().catch(() => ({}))
    : { error: await response.text().catch(() => "") };

  if (!response.ok || data.status === "error") {
    throw new Error(cleanApiError(data.error || data.message || `Request failed with HTTP ${response.status}.`));
  }
  return data;
}

function cleanApiError(message) {
  const text = String(message || "The backend request failed.");
  if (/traceback|stack trace/i.test(text)) {
    return "Backend returned an internal error. Check the Flask console logs for the exact traceback.";
  }
  return text.length > 260 ? `${text.slice(0, 257)}...` : text;
}

function initTheme() {
  const saved = localStorage.getItem(STORAGE.theme) || localStorage.getItem("nci-theme") || "light";
  document.documentElement.dataset.theme = saved === "dark" ? "dark" : "light";
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem(STORAGE.theme, next);
}

function activateTab(panelId, shouldScroll = false) {
  if (!panelId) return;
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === panelId);
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.tabTarget === panelId);
  });
  if (shouldScroll) {
    document.querySelector(".app-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function loadHealth() {
  try {
    const health = await apiJson(API.health);
    els.backendStatus.textContent = "Backend ready";
    els.backendStatus.className = "status-pill is-ok";
    els.metricDrugs.textContent = health.available_drugs ?? "100";
    els.metricCells.textContent = health.available_cell_lines ?? "60";
    els.metricModels.textContent = health.model_count ?? "60";
  } catch (error) {
    els.backendStatus.textContent = "Backend issue";
    els.backendStatus.className = "status-pill is-error";
    showToast(error.message, "error");
  }
}

async function loadDrugs() {
  try {
    const data = await apiJson(API.drugs);
    state.drugs = new Set((data.drugs || []).map((drug) => String(drug)));
    els.drugList.innerHTML = (data.drugs || [])
      .map((drug) => `<option value="${escapeHtml(String(drug))}"></option>`)
      .join("");
  } catch (error) {
    showToast(`Drug list failed to load: ${error.message}`, "error");
  }
}

async function loadCellLines() {
  try {
    const data = await apiJson(API.cellLines);
    const values = data.cell_lines || [];
    state.cellLines = new Set(values);
    els.cellLineInput.innerHTML = `<option value="">Select cell line</option>` + values
      .map((cellLine) => `<option value="${escapeAttribute(cellLine)}">${escapeHtml(cellLine)}</option>`)
      .join("");
  } catch (error) {
    els.cellLineInput.innerHTML = `<option value="">Cell lines unavailable</option>`;
    showToast(`Cell-line list failed to load: ${error.message}`, "error");
  }
}

async function loadDemoCases() {
  try {
    const data = await apiJson(API.demoCases);
    state.demos = sortDemoCases(data.demo_cases || []);
    renderDemoButtons();
  } catch (error) {
    els.demoButtons.innerHTML = `<div class="inline-message">Demo cases unavailable: ${escapeHtml(error.message)}</div>`;
  }
}

function sortDemoCases(cases) {
  return [...cases].sort((a, b) => {
    const aIndex = DEMO_ORDER.indexOf(a.case_type);
    const bIndex = DEMO_ORDER.indexOf(b.case_type);
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
  });
}

function renderDemoButtons() {
  if (!state.demos.length) {
    els.demoButtons.innerHTML = `<div class="inline-message">No demo cases returned by the backend.</div>`;
    return;
  }

  els.demoButtons.innerHTML = state.demos.map((demo) => {
    const title = DEMO_TITLES[demo.case_type] || demo.case_type;
    return `
      <button class="demo-card" type="button" data-demo-type="${escapeAttribute(demo.case_type)}">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(demo.NSC1)} + ${escapeHtml(demo.NSC2)} on ${escapeHtml(demo.CELLNAME)}</span>
        <span class="score-preview">${formatScore(demo.predicted_comboscore)} | ${escapeHtml(demo.label)}</span>
      </button>
    `;
  }).join("");

  els.demoButtons.querySelectorAll("[data-demo-type]").forEach((button) => {
    button.addEventListener("click", async () => {
      const demo = state.demos.find((item) => item.case_type === button.dataset.demoType);
      if (!demo) return;
      fillPredictionInputs(demo.NSC1, demo.NSC2, demo.CELLNAME);
      activateTab("predictPanel", true);
      showToast(`${DEMO_TITLES[demo.case_type] || "Demo"} loaded. Running prediction...`, "success");
      await runPrediction(buildPayloadFromInputs());
    });
  });
}

function fillPredictionInputs(nsc1, nsc2, cellLine) {
  els.nsc1Input.value = nsc1;
  els.nsc2Input.value = nsc2;
  els.cellLineInput.value = cellLine;
  validatePredictionForm();
}

function validatePredictionForm() {
  const nsc1Ok = validateDrugInput(els.nsc1Input, els.nsc1Message, "NSC1");
  const nsc2Ok = validateDrugInput(els.nsc2Input, els.nsc2Message, "NSC2");
  const cellOk = validateCellLineInput();
  return nsc1Ok && nsc2Ok && cellOk;
}

function validateDrugInput(input, messageEl, label) {
  if (!input || !messageEl) return false;
  const value = input.value.trim();
  if (!value) {
    setFieldMessage(messageEl, `${label} is required.`, "error");
    return false;
  }
  if (!/^\d+$/.test(value)) {
    setFieldMessage(messageEl, `${label} must be numeric.`, "error");
    return false;
  }
  if (state.drugs.size && !state.drugs.has(String(Number(value)))) {
    setFieldMessage(messageEl, `NSC ${value} is not in the supported drug list.`, "error");
    return false;
  }
  setFieldMessage(messageEl, "Available drug.", "ok");
  return true;
}

function validateCellLineInput() {
  const value = els.cellLineInput?.value.trim() || "";
  if (!value) {
    setFieldMessage(els.cellLineMessage, "CELLNAME is required.", "error");
    return false;
  }
  if (state.cellLines.size && !state.cellLines.has(value)) {
    setFieldMessage(els.cellLineMessage, "Cell line is not in the final model registry.", "error");
    return false;
  }
  setFieldMessage(els.cellLineMessage, "Available cell line.", "ok");
  return true;
}

function setFieldMessage(element, text, kind) {
  if (!element) return;
  element.textContent = text;
  element.className = kind;
}

function buildPayloadFromInputs() {
  return {
    NSC1: Number(els.nsc1Input.value.trim()),
    NSC2: Number(els.nsc2Input.value.trim()),
    CELLNAME: els.cellLineInput.value.trim()
  };
}

async function handlePredictionSubmit(event) {
  event.preventDefault();
  if (!validatePredictionForm()) {
    showToast("Fix the highlighted inputs before running prediction.", "error");
    return;
  }
  await runPrediction(buildPayloadFromInputs());
}

async function runPrediction(payload) {
  // Single prediction flow:
  // form values -> /api/predict -> render backend-owned label/result -> fetch
  // molecule SVGs -> enable optional SHAP explanation for the same payload.
  state.currentPayload = payload;
  state.currentPrediction = null;
  els.explainButton.disabled = true;
  els.explainContent.classList.add("empty-state");
  els.explainContent.textContent = "Prediction is running. SHAP explanation will be available after it succeeds.";
  startFlowAnimation();

  try {
    const prediction = await apiJson(API.predict, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    state.currentPrediction = prediction;
    finishFlowAnimation();
    renderPrediction(prediction);
    saveRecentPrediction(prediction);
    renderRecentPredictions();
    els.explainButton.disabled = false;
    await loadMoleculePair(payload);
    showToast("Prediction complete.", "success");
  } catch (error) {
    stopFlowAnimation();
    els.explainContent.textContent = "Run a successful prediction first, then request SHAP explanation.";
    showToast(error.message, "error");
  }
}

function startFlowAnimation() {
  stopFlowAnimation();
  const steps = Array.from(els.flowSteps.querySelectorAll("li"));
  steps.forEach((step) => step.classList.remove("active", "done"));
  let index = 0;
  steps[index]?.classList.add("active");
  state.flowTimer = window.setInterval(() => {
    steps[index]?.classList.remove("active");
    steps[index]?.classList.add("done");
    index = Math.min(index + 1, steps.length - 1);
    steps[index]?.classList.add("active");
  }, 520);
}

function finishFlowAnimation() {
  const steps = Array.from(els.flowSteps.querySelectorAll("li"));
  stopFlowAnimation();
  steps.forEach((step) => {
    step.classList.remove("active");
    step.classList.add("done");
  });
}

function stopFlowAnimation() {
  if (state.flowTimer) {
    window.clearInterval(state.flowTimer);
    state.flowTimer = null;
  }
  els.flowSteps?.querySelectorAll("li").forEach((step) => step.classList.remove("active"));
}

function renderPrediction(prediction) {
  const score = Number(prediction.final_predicted_COMBOSCORE);
  animateScore(score);
  updateGauge(score);
  setResultLabel(prediction.label);

  const input = prediction.input || {};
  els.resultFacts.innerHTML = [
    factTile("Model", prediction.model_used),
    factTile("Model path", prediction.model_path),
    factTile("NSC1 -> NSC2", formatScore(prediction.prediction_NSC1_to_NSC2)),
    factTile("NSC2 -> NSC1", formatScore(prediction.prediction_NSC2_to_NSC1)),
    factTile("Feature count", prediction.feature_count || 526),
    factTile("Input", `${input.NSC1} + ${input.NSC2} / ${input.CELLNAME}`)
  ].join("");

  const directionText = score > NEUTRAL_THRESHOLD
    ? "the result suggests synergistic behavior."
    : score < -NEUTRAL_THRESHOLD
      ? "the result suggests antagonistic behavior."
      : "the result suggests neutral or mostly additive behavior.";

  els.resultStory.textContent =
    `For cell line ${input.CELLNAME}, the backend selected ${prediction.model_used} because it is the final best model for this cell line. ` +
    `It predicted Drug 1 to Drug 2 as ${formatScore(prediction.prediction_NSC1_to_NSC2)} and Drug 2 to Drug 1 as ` +
    `${formatScore(prediction.prediction_NSC2_to_NSC1)}, then averaged both values to produce final ComboScore ` +
    `${formatScore(score)}. Because the score is ${score < -NEUTRAL_THRESHOLD ? "negative" : score > NEUTRAL_THRESHOLD ? "positive" : "near zero"}, ${directionText} ` +
    `${prediction.explanation || ""}`;
}

function setResultLabel(label) {
  const normalized = String(label || "waiting").toLowerCase().replaceAll(/\s+/g, "_");
  els.resultLabel.textContent = label || "Waiting";
  els.resultLabel.className = `result-label ${normalized}`;
}

function factTile(label, value) {
  return `
    <div class="fact">
      <small>${escapeHtml(label)}</small>
      <strong>${escapeHtml(String(value ?? ""))}</strong>
    </div>
  `;
}

function animateScore(targetScore) {
  if (state.scoreAnimationFrame) {
    cancelAnimationFrame(state.scoreAnimationFrame);
  }

  const startText = els.finalScore.textContent;
  const start = Number.isFinite(Number(startText)) ? Number(startText) : 0;
  const end = Number.isFinite(targetScore) ? targetScore : 0;
  const startedAt = performance.now();
  const duration = 720;

  const tick = (now) => {
    const progress = Math.min(1, (now - startedAt) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = start + (end - start) * eased;
    els.finalScore.textContent = formatScore(value);
    if (progress < 1) {
      state.scoreAnimationFrame = requestAnimationFrame(tick);
    } else {
      els.finalScore.textContent = formatScore(end);
      state.scoreAnimationFrame = null;
    }
  };

  state.scoreAnimationFrame = requestAnimationFrame(tick);
}

function updateGauge(score) {
  const clamped = Math.max(GAUGE_MIN, Math.min(GAUGE_MAX, Number(score)));
  const percent = ((clamped - GAUGE_MIN) / (GAUGE_MAX - GAUGE_MIN)) * 100;
  els.gaugeNeedle.style.left = `${percent}%`;
}

async function loadMoleculePair(payload) {
  // Molecule data flow stays read-only: current NSCs -> /api/molecule-pair
  // -> sanitize returned SVG text in-browser -> render without saving files.
  els.moleculeStatus.textContent = "Loading RDKit molecule structures...";
  els.moleculeGrid.innerHTML = moleculeLoadingCards();
  try {
    const data = await apiJson(API.moleculePair, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ NSC1: payload.NSC1, NSC2: payload.NSC2 })
    });
    els.moleculeStatus.textContent = "";
    renderMolecules(data);
  } catch (error) {
    els.moleculeStatus.textContent = error.message;
    els.moleculeGrid.innerHTML = `
      <article class="molecule-card empty-state">Drug 1 molecule could not be loaded.</article>
      <article class="molecule-card empty-state">Drug 2 molecule could not be loaded.</article>
    `;
  }
}

function moleculeLoadingCards() {
  return `
    <article class="molecule-card empty-state">Loading Drug 1 molecule...</article>
    <article class="molecule-card empty-state">Loading Drug 2 molecule...</article>
  `;
}

function renderMolecules(data) {
  els.moleculeGrid.innerHTML = [
    moleculeCard("Drug 1", data.NSC1),
    moleculeCard("Drug 2", data.NSC2)
  ].join("");

  els.moleculeGrid.querySelectorAll("[data-svg-id]").forEach((container) => {
    const side = container.dataset.svgId;
    const molecule = side === "NSC1" ? data.NSC1 : data.NSC2;
    insertSanitizedSvg(container, molecule?.svg || "");
  });
}

function moleculeCard(title, molecule) {
  if (!molecule || !molecule.molecule_found) {
    return `
      <article class="molecule-card empty-state">
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(molecule?.error || "Molecule structure was not found.")}</p>
      </article>
    `;
  }

  return `
    <article class="molecule-card">
      <h3>${escapeHtml(title)}</h3>
      <div class="molecule-meta">
        <span>Requested ${escapeHtml(String(molecule.requested_nsc))}</span>
        <span>Resolved ${escapeHtml(String(molecule.resolved_nsc))}</span>
        <span>${molecule.used_alias ? "Alias used" : "Direct match"}</span>
      </div>
      <div class="svg-box" data-svg-id="${title === "Drug 1" ? "NSC1" : "NSC2"}"></div>
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

async function handleExplain() {
  // SHAP runs only on demand for the latest successful prediction payload.
  if (!state.currentPayload) {
    showToast("Run a prediction before requesting SHAP explanation.", "error");
    return;
  }

  activateTab("explainPanel", true);
  els.explainButton.disabled = true;
  els.explainContent.classList.remove("empty-state");
  els.explainContent.innerHTML = `<div class="inline-message">Computing SHAP explanation for the current prediction...</div>`;

  try {
    const explanation = await apiJson(API.explain, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.currentPayload)
    });
    renderExplanation(explanation);
  } catch (error) {
    els.explainContent.innerHTML = `<div class="toast is-error">${escapeHtml(error.message)}</div>`;
  } finally {
    els.explainButton.disabled = false;
  }
}

function renderExplanation(data) {
  els.explainContent.classList.remove("empty-state");
  els.explainContent.innerHTML = `
    <div class="story-card">
      <h3>Explanation summary</h3>
      <p>${escapeHtml(data.explanation_summary || "Explanation completed.")}</p>
      <p>${escapeHtml(data.suggestion || "")}</p>
    </div>
    <div class="contributor-grid">
      <section>
        <h3>Pushes upward / more synergistic</h3>
        <div class="contributor-column">${renderContributors(data.top_positive_contributors || [])}</div>
      </section>
      <section>
        <h3>Pushes downward / more antagonistic</h3>
        <div class="contributor-column">${renderContributors(data.top_negative_contributors || [])}</div>
      </section>
    </div>
  `;
}

function renderContributors(contributors) {
  if (!contributors.length) {
    return `<div class="contributor-card"><small>No contributors returned.</small></div>`;
  }

  return contributors.map((item) => `
    <article class="contributor-card">
      <strong>${escapeHtml(item.readable_feature || item.readable_name || item.feature)}</strong>
      <small>
        Raw feature: ${escapeHtml(item.feature)}<br>
        Feature value: ${formatScore(item.feature_value)}<br>
        SHAP value: ${formatScore(item.shap_value)}<br>
        ${escapeHtml(item.effect)}
      </small>
    </article>
  `).join("");
}

async function handleBatchUpload() {
  // Batch flow sends multipart FormData to the backend and displays only the
  // saved output filename/download link returned by /api/batch-predict.
  const file = els.batchFile.files[0];
  if (!file) {
    renderBatchError("Choose a CSV file first.");
    return;
  }
  if (!file.name.toLowerCase().endsWith(".csv")) {
    renderBatchError("Uploaded file must be a CSV.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  els.batchResult.classList.remove("empty-state");
  els.batchResult.innerHTML = `<div class="inline-message">Uploading CSV and running row-level predictions...</div>`;

  try {
    const response = await fetch(API.batch, { method: "POST", body: formData });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.status === "error") {
      throw new Error(cleanApiError(data.error || "Batch prediction failed."));
    }
    renderBatchResult(data);
  } catch (error) {
    renderBatchError(error.message);
  }
}

function renderBatchError(message) {
  els.batchResult.classList.remove("empty-state");
  els.batchResult.innerHTML = `<div class="toast is-error">${escapeHtml(message)}</div>`;
}

function renderBatchResult(data) {
  const outputName = String(data.output_file || "").split(/[\\/]/).pop();
  const downloadUrl = outputName ? `${API.download}${encodeURIComponent(outputName)}` : "#";

  els.batchResult.innerHTML = `
    <div class="batch-summary">
      <div><span>Total rows</span><strong>${escapeHtml(String(data.total_rows ?? 0))}</strong></div>
      <div><span>Successful</span><strong>${escapeHtml(String(data.successful_rows ?? 0))}</strong></div>
      <div><span>Failed</span><strong>${escapeHtml(String(data.failed_rows ?? 0))}</strong></div>
    </div>
    <a class="btn btn-primary" href="${escapeAttribute(downloadUrl)}">Download output CSV</a>
    <div class="table-wrap">${previewTable(data.preview || [])}</div>
  `;
}

function previewTable(rows) {
  if (!rows.length) return `<div class="inline-message">No preview rows returned.</div>`;
  const columns = Object.keys(rows[0]);
  return `
    <table class="preview-table">
      <thead>
        <tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows.map((row) => `
          <tr>${columns.map((column) => `<td>${escapeHtml(String(row[column] ?? ""))}</td>`).join("")}</tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function downloadSampleCsv() {
  const content = "NSC1,NSC2,CELLNAME\n740,750,786-0\n740,752,A498\n750,755,A549/ATCC";
  const blob = new Blob([content], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "batch_prediction_sample.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function resetPredictionWorkspace() {
  els.predictionForm.reset();
  state.currentPayload = null;
  state.currentPrediction = null;
  els.explainButton.disabled = true;
  els.explainContent.classList.add("empty-state");
  els.explainContent.textContent = "Run a successful prediction first, then request SHAP explanation.";
  els.finalScore.textContent = "--";
  els.gaugeNeedle.style.left = "50%";
  els.resultFacts.innerHTML = "";
  setResultLabel("Waiting");
  els.resultLabel.classList.add("is-idle");
  els.resultStory.textContent = "Run a prediction to see model selection, directional predictions, and the averaged ComboScore.";
  els.moleculeStatus.textContent = "";
  els.moleculeGrid.innerHTML = `
    <article class="molecule-card empty-state">Drug 1 molecule appears here after prediction.</article>
    <article class="molecule-card empty-state">Drug 2 molecule appears here after prediction.</article>
  `;
  stopFlowAnimation();
  validatePredictionForm();
}

function saveRecentPrediction(prediction) {
  const input = prediction.input || {};
  const item = {
    NSC1: input.NSC1,
    NSC2: input.NSC2,
    CELLNAME: input.CELLNAME,
    score: prediction.final_predicted_COMBOSCORE,
    label: labelForScore(prediction.final_predicted_COMBOSCORE),
    model: prediction.model_used
  };

  const history = getRecentPredictions()
    .filter((entry) => !(String(entry.NSC1) === String(item.NSC1)
      && String(entry.NSC2) === String(item.NSC2)
      && entry.CELLNAME === item.CELLNAME));
  history.unshift(item);
  localStorage.setItem(STORAGE.recent, JSON.stringify(history.slice(0, 6)));
}

function getRecentPredictions() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE.recent) || "[]");
  } catch {
    return [];
  }
}

function renderRecentPredictions() {
  const history = getRecentPredictions();
  if (!history.length) {
    els.recentPredictions.innerHTML = `<div class="empty-state">Successful predictions will appear here.</div>`;
    return;
  }

  els.recentPredictions.innerHTML = history.map((item, index) => {
    const label = labelForScore(item.score);
    return `
      <button class="recent-item" type="button" data-index="${index}">
        <strong>${escapeHtml(item.NSC1)} + ${escapeHtml(item.NSC2)}</strong>
        <span>${escapeHtml(item.CELLNAME)} | ${escapeHtml(item.model)}</span>
        <span>${formatScore(item.score)} | ${escapeHtml(label)}</span>
      </button>
    `;
  }).join("");

  els.recentPredictions.querySelectorAll("[data-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = history[Number(button.dataset.index)];
      fillPredictionInputs(item.NSC1, item.NSC2, item.CELLNAME);
      activateTab("predictPanel", true);
      showToast("Recent prediction loaded into the form.", "success");
    });
  });
}

function clearRecentPredictions() {
  localStorage.removeItem(STORAGE.recent);
  renderRecentPredictions();
}

function showToast(message, kind = "success") {
  if (!message || !els.toastArea) return;
  const toast = document.createElement("div");
  toast.className = `toast ${kind === "error" ? "is-error" : "is-success"}`;
  toast.textContent = message;
  els.toastArea.appendChild(toast);
  window.setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-4px)";
    window.setTimeout(() => toast.remove(), 180);
  }, 4800);
}

function formatScore(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "");
  return number.toFixed(3);
}

function labelForScore(score) {
  const value = Number(score);
  if (value >= NEUTRAL_THRESHOLD) return "synergistic";
  if (value <= -NEUTRAL_THRESHOLD) return "antagonistic";
  return "neutral";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
