const state = {
  topics: [],
  selectedTopicId: null,
};

const els = {
  sourceStatus: document.getElementById("sourceStatus"),
  topicCount: document.getElementById("topicCount"),
  docCount: document.getElementById("docCount"),
  geminiAvg: document.getElementById("geminiAvg"),
  qwenAvg: document.getElementById("qwenAvg"),
  searchInput: document.getElementById("searchInput"),
  cohesionInput: document.getElementById("cohesionInput"),
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
  els.geminiAvg.textContent = formatScore(summary.gemini_avg_cohesion);
  els.qwenAvg.textContent = formatScore(summary.qwen_avg_cohesion);
}

function currentQueryUrl() {
  const params = new URLSearchParams();
  const q = els.searchInput.value.trim();
  const minCohesion = els.cohesionInput.value.trim();

  if (q) params.set("q", q);
  if (minCohesion) params.set("min_cohesion", minCohesion);
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
        <td><strong>${escapeHtml(topic.label)}</strong></td>
        <td>${escapeHtml(keywords)}</td>
        <td>${formatNumber(topic.doc_count)}</td>
        <td>${formatScore(topic.best_cohesion)}</td>
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
  els.detailMeta.textContent = `Topic ${detail.topic_id} · ${formatNumber(detail.doc_count)} docs`;

  els.detailContent.className = "detail-content";
  els.detailContent.innerHTML = `
    <div class="keyword-line">
      ${detail.top_keywords.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
    </div>

    <div class="comparison">
      ${renderModelBlock("Gemini", detail.gemini)}
      ${renderModelBlock("Qwen", detail.qwen)}
    </div>
  `;
}

function renderModelBlock(title, model) {
  return `
    <article class="model-block">
      <div class="model-heading">
        <h3>${escapeHtml(title)}</h3>
        <span>Cohesion ${formatScore(model.cohesion)}</span>
      </div>
      <h4>${escapeHtml(model.label)}</h4>
      <p>${escapeHtml(model.explanation)}</p>
      <h5>Themes</h5>
      <ul>
        ${model.themes.map((theme) => `<li>${escapeHtml(theme)}</li>`).join("")}
      </ul>
      <h5>Label reasoning</h5>
      <p>${escapeHtml(model.reasoning)}</p>
      <h5>Cohesion reasoning</h5>
      <p>${escapeHtml(model.cohesion_reasoning)}</p>
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
els.cohesionInput.addEventListener("input", debouncedLoadTopics);
els.modelSelect.addEventListener("change", loadTopics);
els.resetButton.addEventListener("click", () => {
  els.searchInput.value = "";
  els.cohesionInput.value = "";
  els.modelSelect.value = "gemini";
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
