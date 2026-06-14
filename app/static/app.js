const state = {
  topics: [],
  selectedTopicId: null,
};

const els = {
  sourceStatus: document.getElementById("sourceStatus"),
  topicCount: document.getElementById("topicCount"),
  docCount: document.getElementById("docCount"),
  topWinner: document.getElementById("topWinner"),
  bestJudgeAvg: document.getElementById("bestJudgeAvg"),
  modelInfoStatus: document.getElementById("modelInfoStatus"),
  modelInfoGrid: document.getElementById("modelInfoGrid"),
  searchInput: document.getElementById("searchInput"),
  scoreInput: document.getElementById("scoreInput"),
  modelSelect: document.getElementById("modelSelect"),
  resetButton: document.getElementById("resetButton"),
  resultCount: document.getElementById("resultCount"),
  topicRows: document.getElementById("topicRows"),
  detailTitle: document.getElementById("detailTitle"),
  detailMeta: document.getElementById("detailMeta"),
  detailContent: document.getElementById("detailContent"),
};

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function formatScore(value) {
  return value === null || value === undefined ? "-" : Number(value).toFixed(1);
}

function formatCompactModel(value) {
  return String(value ?? "-")
    .replace("-4-31B", "")
    .replace("-3-32B", "")
    .replace("-3.3-70B", "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadSummary() {
  const [health, summary] = await Promise.all([
    getJson("/health"),
    getJson("/api/summary"),
  ]);

  els.sourceStatus.textContent = health.ok ? "Source connected" : "Source missing";
  els.sourceStatus.classList.toggle("error", !health.ok);
  els.topicCount.textContent = summary.topic_count;
  els.docCount.textContent = formatNumber(summary.total_documents);

  const winnerEntries = Object.entries(summary.winner_distribution ?? {})
    .sort((a, b) => b[1] - a[1]);
  const bestModel = Object.entries(summary.model_stats ?? {})
    .sort((a, b) => (b[1].avg_judge_total ?? -1) - (a[1].avg_judge_total ?? -1))[0];

  els.topWinner.textContent = winnerEntries.length
    ? `${formatCompactModel(winnerEntries[0][0])} (${winnerEntries[0][1]})`
    : "-";
  els.bestJudgeAvg.textContent = bestModel
    ? `${formatCompactModel(bestModel[0])} ${formatScore(bestModel[1].avg_judge_total)}`
    : "-";

  renderScenario2Winner(summary.scenario2_winner);
}

function renderScenario2Winner(winner) {
  if (!winner) {
    els.modelInfoStatus.textContent = "Not provided";
    els.modelInfoGrid.innerHTML = `
      <div class="model-info-empty">Place scenario2_winner_for_scenario3.csv in artifacts/ to show experiment metadata.</div>
    `;
    return;
  }

  els.modelInfoStatus.textContent = winner.arm || "Loaded";
  const items = [
    ["Arm", winner.arm],
    ["Topics", winner.n_topics],
    ["Outlier", formatScore(winner.outlier_rate)],
    ["c_v", formatScore(winner.cv)],
    ["Uniqueness", formatScore(winner.topic_uniqueness)],
    ["Hungarian F1", formatScore(winner.hungarian_f1)],
    ["Harmonic", formatScore(winner.harmonic_mean)],
    ["Silhouette", formatScore(winner.silhouette)],
  ];

  els.modelInfoGrid.innerHTML = items.map(([label, value]) => `
    <div class="model-info-item">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value ?? "-")}</strong>
    </div>
  `).join("");
}

function currentQueryUrl() {
  const params = new URLSearchParams();
  const q = els.searchInput.value.trim();
  const minScore = els.scoreInput.value.trim();

  if (q) params.set("q", q);
  if (minScore) params.set("min_score", minScore);
  params.set("model", els.modelSelect.value);

  return `/api/topics?${params.toString()}`;
}

async function loadTopics() {
  state.topics = await getJson(currentQueryUrl());
  renderTopics();

  if (state.topics.length > 0) {
    const stillVisible = state.topics.some((topic) => topic.topic_id === state.selectedTopicId);
    await selectTopic(stillVisible ? state.selectedTopicId : state.topics[0].topic_id);
  } else {
    clearDetail();
  }
}

function renderTopics() {
  els.resultCount.textContent = `${state.topics.length} results`;
  els.topicRows.innerHTML = state.topics.map((topic) => {
    const keywords = topic.top_keywords.slice(0, 5).join(", ");
    const selectedClass = topic.topic_id === state.selectedTopicId ? "selected" : "";
    return `
      <tr class="${selectedClass}" data-topic-id="${topic.topic_id}" tabindex="0">
        <td>${topic.topic_id}</td>
        <td><strong>${escapeHtml(topic.label)}</strong><br><small>${formatNumber(topic.doc_count)} docs</small></td>
        <td>${escapeHtml(keywords)}</td>
        <td>${escapeHtml(formatCompactModel(topic.winner_model))}</td>
        <td>${formatScore(topic.judge_total)}</td>
      </tr>
    `;
  }).join("");

  for (const row of els.topicRows.querySelectorAll("tr")) {
    row.addEventListener("click", () => selectTopic(Number(row.dataset.topicId)));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        selectTopic(Number(row.dataset.topicId));
      }
    });
  }
}

async function selectTopic(topicId) {
  if (topicId === null || topicId === undefined) return;
  state.selectedTopicId = topicId;
  renderTopics();

  const detail = await getJson(`/api/topics/${topicId}`);
  els.detailTitle.textContent = detail.label;
  els.detailMeta.textContent = `Topic ${detail.topic_id} | ${formatNumber(detail.doc_count)} docs | Winner ${formatCompactModel(detail.winner_model)}`;

  els.detailContent.className = "detail-content";
  els.detailContent.innerHTML = `
    <div class="keyword-line">
      ${detail.top_keywords.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
    </div>

    <section class="judge-summary">
      <h3>Judge reasoning</h3>
      <p>${escapeHtml(detail.judgment_reasoning || "-")}</p>
    </section>

    <div class="comparison">
      ${detail.models.map((model) => renderModelBlock(model, model.model === detail.winner_model)).join("")}
    </div>
  `;
}

function renderModelBlock(model, isWinner) {
  return `
    <article class="model-block ${isWinner ? "winner-block" : ""}">
      <div class="model-heading">
        <h3>${escapeHtml(model.model)}${isWinner ? " - Winner" : ""}</h3>
        <span>Judge ${formatScore(model.judge.total)}/16</span>
      </div>
      <h4>${escapeHtml(model.label)}</h4>
      <div class="score-grid">
        <span>Faith ${formatScore(model.judge.faithfulness)}</span>
        <span>Spec ${formatScore(model.judge.specificity)}</span>
        <span>Interp ${formatScore(model.judge.interpretability)}</span>
        <span>Utility ${formatScore(model.judge.linguistic_utility)}</span>
        <span>Cohesion ${formatScore(model.cohesion)}</span>
      </div>
      <p>${escapeHtml(model.explanation)}</p>
      <h5>Themes</h5>
      <ul>
        ${model.themes.map((theme) => `<li>${escapeHtml(theme)}</li>`).join("")}
      </ul>
      <h5>Label reasoning</h5>
      <p>${escapeHtml(model.reasoning)}</p>
      <h5>Cohesion reasoning</h5>
      <p>${escapeHtml(model.cohesion_reasoning)}</p>
      <h5>Judge justification</h5>
      <p>${escapeHtml(model.judge.justification)}</p>
    </article>
  `;
}

function clearDetail() {
  state.selectedTopicId = null;
  els.detailTitle.textContent = "No topics";
  els.detailMeta.textContent = "-";
  els.detailContent.className = "empty-state";
  els.detailContent.textContent = "No topics match the current filters.";
}

function debounce(fn, delay = 250) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), delay);
  };
}

const debouncedLoadTopics = debounce(loadTopics);

els.searchInput.addEventListener("input", debouncedLoadTopics);
els.scoreInput.addEventListener("input", debouncedLoadTopics);
els.modelSelect.addEventListener("change", loadTopics);
els.resetButton.addEventListener("click", () => {
  els.searchInput.value = "";
  els.scoreInput.value = "";
  els.modelSelect.value = "winner";
  loadTopics();
});

loadSummary()
  .then(loadTopics)
  .catch((error) => {
    els.sourceStatus.textContent = "Failed to load data";
    els.sourceStatus.classList.add("error");
    els.detailContent.className = "empty-state error-text";
    els.detailContent.textContent = error.message;
  });
