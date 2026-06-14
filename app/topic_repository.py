from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


JUDGE_METRICS = ("faithfulness", "specificity", "interpretability", "linguistic_utility")


@dataclass(frozen=True)
class ModelExplanation:
    model: str
    status: str
    label: str
    explanation: str
    themes: list[str]
    reasoning: str
    cohesion: float | None
    cohesion_reasoning: str
    raw_error: str
    faithfulness: float | None = None
    specificity: float | None = None
    interpretability: float | None = None
    linguistic_utility: float | None = None
    judge_total: float | None = None
    judge_justification: str = ""

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "status": self.status,
            "label": self.label,
            "explanation": self.explanation,
            "themes": self.themes,
            "reasoning": self.reasoning,
            "cohesion": self.cohesion,
            "cohesion_reasoning": self.cohesion_reasoning,
            "raw_error": self.raw_error,
            "judge": {
                "faithfulness": self.faithfulness,
                "specificity": self.specificity,
                "interpretability": self.interpretability,
                "linguistic_utility": self.linguistic_utility,
                "total": self.judge_total,
                "justification": self.judge_justification,
            },
        }


@dataclass(frozen=True)
class Topic:
    topic_id: int
    doc_count: int
    original_name: str
    top_keywords: list[str]
    models: list[ModelExplanation]
    winner_model: str
    judgment_reasoning: str

    @property
    def winner(self) -> ModelExplanation | None:
        return next((model for model in self.models if model.model == self.winner_model), None)

    @property
    def display_model(self) -> ModelExplanation | None:
        return self.winner or max(
            self.models,
            key=lambda model: model.judge_total if model.judge_total is not None else -1,
            default=None,
        )

    @property
    def display_label(self) -> str:
        model = self.display_model
        return model.label if model and model.label else self.original_name

    @property
    def display_score(self) -> float | None:
        model = self.display_model
        return model.judge_total if model else None

    def searchable_text(self) -> str:
        parts = [self.original_name, " ".join(self.top_keywords), self.winner_model, self.judgment_reasoning]
        for model in self.models:
            parts.extend([
                model.model,
                model.label,
                model.explanation,
                " ".join(model.themes),
                model.reasoning,
                model.cohesion_reasoning,
                model.judge_justification,
            ])
        return " ".join(parts).lower()

    def score_for_model(self, model_name: str) -> float | None:
        target = self.display_model if model_name == "winner" else self.get_model(model_name)
        return target.judge_total if target else None

    def get_model(self, model_name: str) -> ModelExplanation | None:
        return next((model for model in self.models if model.model == model_name), None)

    def to_summary(self) -> dict:
        winner = self.display_model
        return {
            "topic_id": self.topic_id,
            "doc_count": self.doc_count,
            "original_name": self.original_name,
            "top_keywords": self.top_keywords,
            "label": self.display_label,
            "winner_model": self.winner_model,
            "judge_total": self.display_score,
            "cohesion": winner.cohesion if winner else None,
            "model_count": len(self.models),
        }

    def to_detail(self) -> dict:
        return {
            **self.to_summary(),
            "judgment_reasoning": self.judgment_reasoning,
            "models": [model.to_dict() for model in self.models],
        }


class TopicRepository:
    def __init__(
        self,
        detailed_csv_path: Path,
        judged_csv_path: Path,
        scenario2_winner_csv_path: Path | None = None,
    ):
        self.detailed_csv_path = detailed_csv_path
        self.judged_csv_path = judged_csv_path
        self.scenario2_winner_csv_path = scenario2_winner_csv_path
        self._topics: list[Topic] | None = None
        self._model_names: list[str] | None = None
        self._scenario2_winner: dict | None = None

    def all(self) -> list[Topic]:
        if self._topics is None:
            self._topics = self._load_topics()
        return self._topics

    def model_names(self) -> list[str]:
        if self._model_names is None:
            self.all()
        return self._model_names or []

    def get(self, topic_id: int) -> Topic | None:
        return next((topic for topic in self.all() if topic.topic_id == topic_id), None)

    def search(
        self,
        q: str | None = None,
        min_score: float | None = None,
        model: str = "winner",
    ) -> list[Topic]:
        topics = self.all()
        query = (q or "").strip().lower()

        if query:
            topics = [topic for topic in topics if query in topic.searchable_text()]

        if min_score is not None:
            topics = [
                topic for topic in topics
                if topic.score_for_model(model) is not None
                and topic.score_for_model(model) >= min_score
            ]

        return sorted(topics, key=lambda item: item.topic_id)

    def summary(self) -> dict:
        topics = self.all()
        total_docs = sum(topic.doc_count for topic in topics)
        winner_distribution: dict[str, int] = {}

        for topic in topics:
            if topic.winner_model:
                winner_distribution[topic.winner_model] = winner_distribution.get(topic.winner_model, 0) + 1

        model_stats = {}
        for model_name in self.model_names():
            model_explanations = [
                topic.get_model(model_name)
                for topic in topics
                if topic.get_model(model_name) is not None
            ]
            model_stats[model_name] = {
                "avg_cohesion": _average([
                    model.cohesion for model in model_explanations
                    if model and model.cohesion is not None
                ]),
                "avg_judge_total": _average([
                    model.judge_total for model in model_explanations
                    if model and model.judge_total is not None
                ]),
            }

        return {
            "topic_count": len(topics),
            "total_documents": total_docs,
            "model_names": self.model_names(),
            "winner_distribution": winner_distribution,
            "model_stats": model_stats,
            "scenario2_winner": self.scenario2_winner(),
            "detailed_source_file": str(self.detailed_csv_path),
            "judged_source_file": str(self.judged_csv_path),
            "scenario2_winner_source_file": (
                str(self.scenario2_winner_csv_path)
                if self.scenario2_winner_csv_path
                else None
            ),
        }

    def scenario2_winner(self) -> dict | None:
        if self._scenario2_winner is not None:
            return self._scenario2_winner

        if not self.scenario2_winner_csv_path or not self.scenario2_winner_csv_path.exists():
            self._scenario2_winner = None
            return None

        try:
            rows = _read_csv(self.scenario2_winner_csv_path)
        except OSError:
            self._scenario2_winner = None
            return None

        if not rows:
            self._scenario2_winner = None
            return None

        row = rows[0]
        self._scenario2_winner = {
            "arm": row.get("arm", ""),
            "n_topics": _to_int(row.get("n_topics")),
            "outlier_rate": _to_float(row.get("outlier_rate")),
            "cv": _to_float(row.get("cv")),
            "topic_uniqueness": _to_float(row.get("topic_uniqueness")),
            "hungarian_f1": _to_float(row.get("hungarian_f1")),
            "harmonic_mean": _to_float(row.get("harmonic_mean")),
            "silhouette": _to_float(row.get("silhouette")),
            "dbcv": _to_float(row.get("dbcv")),
            "fit_seconds": _to_float(row.get("fit_seconds")),
        }
        return self._scenario2_winner

    def _load_topics(self) -> list[Topic]:
        if not self.detailed_csv_path.exists():
            raise FileNotFoundError(f"Detailed XAI CSV not found: {self.detailed_csv_path}")
        if not self.judged_csv_path.exists():
            raise FileNotFoundError(f"Judged XAI CSV not found: {self.judged_csv_path}")

        detailed_rows = _read_csv(self.detailed_csv_path)
        judged_by_topic = {
            _to_int(row.get("topic_id")): row
            for row in _read_csv(self.judged_csv_path)
        }

        model_names = _extract_model_names(detailed_rows[0] if detailed_rows else {})
        self._model_names = model_names

        topics = [
            _row_to_topic(row, judged_by_topic.get(_to_int(row.get("topic_id")), {}), model_names)
            for row in detailed_rows
        ]
        return sorted(topics, key=lambda item: item.topic_id)


def _row_to_topic(
    detailed_row: dict[str, str],
    judged_row: dict[str, str],
    model_names: list[str],
) -> Topic:
    models = [
        _model_from_rows(model_name, detailed_row, judged_row)
        for model_name in model_names
    ]

    return Topic(
        topic_id=_to_int(detailed_row.get("topic_id")),
        doc_count=_to_int(detailed_row.get("doc_count")),
        original_name=detailed_row.get("original_name", ""),
        top_keywords=_split_list(detailed_row.get("top_keywords", "")),
        models=models,
        winner_model=judged_row.get("winner_model", ""),
        judgment_reasoning=judged_row.get("judgment_reasoning", ""),
    )


def _model_from_rows(
    model_name: str,
    detailed_row: dict[str, str],
    judged_row: dict[str, str],
) -> ModelExplanation:
    return ModelExplanation(
        model=model_name,
        status=detailed_row.get(f"{model_name}_status", ""),
        label=detailed_row.get(f"{model_name}_label", ""),
        explanation=detailed_row.get(f"{model_name}_explanation", ""),
        themes=_split_list(detailed_row.get(f"{model_name}_themes", "")),
        reasoning=detailed_row.get(f"{model_name}_reasoning", ""),
        cohesion=_to_float(detailed_row.get(f"{model_name}_cohesion")),
        cohesion_reasoning=detailed_row.get(f"{model_name}_cohesion_reasoning", ""),
        raw_error=detailed_row.get(f"{model_name}_raw_error", ""),
        faithfulness=_to_float(judged_row.get(f"{model_name}_faithfulness")),
        specificity=_to_float(judged_row.get(f"{model_name}_specificity")),
        interpretability=_to_float(judged_row.get(f"{model_name}_interpretability")),
        linguistic_utility=_to_float(judged_row.get(f"{model_name}_linguistic_utility")),
        judge_total=_to_float(judged_row.get(f"{model_name}_total")),
        judge_justification=judged_row.get(f"{model_name}_justification_detail", ""),
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _extract_model_names(row: dict[str, str]) -> list[str]:
    names = []
    for column in row:
        if column.endswith("_label"):
            names.append(column.removesuffix("_label"))
    return names


def _split_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


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
