from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.topic_repository import TopicRepository


app = FastAPI(
    title="PubMed Topic XAI",
    description="Read-only dashboard for scenario 3 topic explainability outputs.",
    version="0.1.0",
)

settings = get_settings()
app.mount("/static", StaticFiles(directory=settings.app_root / "app" / "static"), name="static")


@lru_cache
def get_repository() -> TopicRepository:
    return TopicRepository(get_settings().xai_csv_path)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PubMed Topic XAI</title>
    <link rel="stylesheet" href="/static/styles.css" />
  </head>
  <body>
    <header class="topbar">
      <div>
        <p class="eyebrow">Scenario 3 Output</p>
        <h1>PubMed Topic XAI</h1>
      </div>
      <div class="source-status" id="sourceStatus">Loading source...</div>
    </header>

    <main class="layout">
      <section class="summary-band" aria-label="Summary metrics">
        <div class="metric">
          <span class="metric-label">Topics</span>
          <strong id="topicCount">-</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Documents</span>
          <strong id="docCount">-</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Gemini Cohesion</span>
          <strong id="geminiAvg">-</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Qwen Cohesion</span>
          <strong id="qwenAvg">-</strong>
        </div>
      </section>

      <section class="workspace">
        <aside class="filters" aria-label="Filters">
          <label for="searchInput">Search</label>
          <input id="searchInput" type="search" placeholder="topic, keyword, label" />

          <label for="cohesionInput">Minimum cohesion</label>
          <input id="cohesionInput" type="number" min="0" max="10" step="0.5" placeholder="0-10" />

          <label for="modelSelect">Cohesion model</label>
          <select id="modelSelect">
            <option value="gemini">Gemini</option>
            <option value="qwen">Qwen</option>
            <option value="best">Best available</option>
          </select>

          <button id="resetButton" type="button">Reset</button>
        </aside>

        <section class="topic-list" aria-label="Topic list">
          <div class="section-header">
            <h2>Topics</h2>
            <span id="resultCount">0 results</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Label</th>
                  <th>Keywords</th>
                  <th>Docs</th>
                  <th>Cohesion</th>
                </tr>
              </thead>
              <tbody id="topicRows"></tbody>
            </table>
          </div>
        </section>

        <section class="detail-panel" aria-label="Topic detail">
          <div class="section-header">
            <h2 id="detailTitle">Select a topic</h2>
            <span id="detailMeta">-</span>
          </div>
          <div id="detailContent" class="empty-state">
            Choose a row from the topic table to inspect label reasoning, themes, and cohesion notes.
          </div>
        </section>
      </section>
    </main>

    <script src="/static/app.js"></script>
  </body>
</html>
"""


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "ok": settings.xai_csv_path.exists(),
        "source_file": str(settings.xai_csv_path),
    }


@app.get("/api/summary")
def summary(repository: TopicRepository = Depends(get_repository)) -> dict:
    return repository.summary()


@app.get("/api/topics")
def topics(
    q: str | None = Query(default=None),
    min_cohesion: float | None = Query(default=None, ge=0, le=10),
    model: str = Query(default="gemini", pattern="^(gemini|qwen|best)$"),
    repository: TopicRepository = Depends(get_repository),
) -> list[dict]:
    return [
        topic.to_summary()
        for topic in repository.search(q=q, min_cohesion=min_cohesion, model=model)
    ]


@app.get("/api/topics/{topic_id}")
def topic_detail(
    topic_id: int,
    repository: TopicRepository = Depends(get_repository),
) -> dict:
    topic = repository.get(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic.to_detail()
