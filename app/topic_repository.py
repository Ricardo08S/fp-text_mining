from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


QWEN = "Qwen-3-32B"
GEMINI = "Gemini-3.1-Flash-Lite"


@dataclass(frozen=True)
class Topic:
    topic_id: int
    doc_count: int
    original_name: str
    top_keywords: list[str]
    qwen_label: str
    qwen_explanation: str
    qwen_themes: list[str]
    qwen_reasoning: str
    qwen_cohesion: float | None
    qwen_cohesion_reasoning: str
    gemini_status: str
    gemini_label: str
    gemini_explanation: str
    gemini_themes: list[str]
    gemini_reasoning: str
    gemini_cohesion: float | None
    gemini_cohesion_reasoning: str

    @property
    def best_label(self) -> str:
        return self.gemini_label or self.qwen_label or self.original_name

    @property
    def best_cohesion(self) -> float | None:
        return self.gemini_cohesion if self.gemini_cohesion is not None else self.qwen_cohesion

    def to_summary(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "doc_count": self.doc_count,
            "original_name": self.original_name,
            "top_keywords": self.top_keywords,
            "label": self.best_label,
            "qwen_label": self.qwen_label,
            "gemini_label": self.gemini_label,
            "qwen_cohesion": self.qwen_cohesion,
            "gemini_cohesion": self.gemini_cohesion,
            "best_cohesion": self.best_cohesion,
        }

    def to_detail(self) -> dict:
        return {
            **self.to_summary(),
            "qwen": {
                "model": QWEN,
                "label": self.qwen_label,
                "explanation": self.qwen_explanation,
                "themes": self.qwen_themes,
                "reasoning": self.qwen_reasoning,
                "cohesion": self.qwen_cohesion,
                "cohesion_reasoning": self.qwen_cohesion_reasoning,
            },
            "gemini": {
                "model": GEMINI,
                "status": self.gemini_status,
                "label": self.gemini_label,
                "explanation": self.gemini_explanation,
                "themes": self.gemini_themes,
                "reasoning": self.gemini_reasoning,
                "cohesion": self.gemini_cohesion,
                "cohesion_reasoning": self.gemini_cohesion_reasoning,
            },
        }


class TopicRepository:
    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self._topics: list[Topic] | None = None

    def all(self) -> list[Topic]:
        if self._topics is None:
            self._topics = self._load_topics()
        return self._topics

    def get(self, topic_id: int) -> Topic | None:
        return next((topic for topic in self.all() if topic.topic_id == topic_id), None)

    def search(
        self,
        q: str | None = None,
        min_cohesion: float | None = None,
        model: str = "gemini",
    ) -> list[Topic]:
        topics = self.all()
        query = (q or "").strip().lower()

        if query:
            topics = [
                topic for topic in topics
                if query in " ".join([
                    topic.original_name,
                    " ".join(topic.top_keywords),
                    topic.qwen_label,
                    topic.gemini_label,
                    topic.qwen_explanation,
                    topic.gemini_explanation,
                ]).lower()
            ]

        if min_cohesion is not None:
            topics = [
                topic for topic in topics
                if _cohesion_for_model(topic, model) is not None
                and _cohesion_for_model(topic, model) >= min_cohesion
            ]

        return sorted(topics, key=lambda item: item.topic_id)

    def summary(self) -> dict:
        topics = self.all()
        qwen_scores = [topic.qwen_cohesion for topic in topics if topic.qwen_cohesion is not None]
        gemini_scores = [topic.gemini_cohesion for topic in topics if topic.gemini_cohesion is not None]
        total_docs = sum(topic.doc_count for topic in topics)
        exact_label_agreement = sum(
            1 for topic in topics
            if topic.qwen_label and topic.gemini_label
            and topic.qwen_label.strip().lower() == topic.gemini_label.strip().lower()
        )

        return {
            "topic_count": len(topics),
            "total_documents": total_docs,
            "qwen_avg_cohesion": _average(qwen_scores),
            "gemini_avg_cohesion": _average(gemini_scores),
            "exact_label_agreement": exact_label_agreement,
            "source_file": str(self.csv_path),
        }

    def _load_topics(self) -> list[Topic]:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"XAI CSV not found: {self.csv_path}")

        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        topics = [_row_to_topic(row) for row in rows]
        return sorted(topics, key=lambda item: item.topic_id)


def _row_to_topic(row: dict[str, str]) -> Topic:
    return Topic(
        topic_id=_to_int(row.get("topic_id")),
        doc_count=_to_int(row.get("doc_count")),
        original_name=row.get("original_name", ""),
        top_keywords=_split_list(row.get("top_keywords", "")),
        qwen_label=row.get(f"{QWEN}_label", ""),
        qwen_explanation=row.get(f"{QWEN}_explanation", ""),
        qwen_themes=_split_list(row.get(f"{QWEN}_themes", "")),
        qwen_reasoning=row.get(f"{QWEN}_reasoning", ""),
        qwen_cohesion=_to_float(row.get(f"{QWEN}_cohesion")),
        qwen_cohesion_reasoning=row.get(f"{QWEN}_cohesion_reasoning", ""),
        gemini_status=row.get(f"{GEMINI}_status", ""),
        gemini_label=row.get(f"{GEMINI}_label", ""),
        gemini_explanation=row.get(f"{GEMINI}_explanation", ""),
        gemini_themes=_split_list(row.get(f"{GEMINI}_themes", "")),
        gemini_reasoning=row.get(f"{GEMINI}_reasoning", ""),
        gemini_cohesion=_to_float(row.get(f"{GEMINI}_cohesion")),
        gemini_cohesion_reasoning=row.get(f"{GEMINI}_cohesion_reasoning", ""),
    )


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _cohesion_for_model(topic: Topic, model: str) -> float | None:
    if model.lower() == "qwen":
        return topic.qwen_cohesion
    if model.lower() == "best":
        return topic.best_cohesion
    return topic.gemini_cohesion
