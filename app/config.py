from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "PubMed Topic XAI"
    app_root: Path = Path(__file__).resolve().parents[1]
    project_root: Path = Path(__file__).resolve().parents[2]
    detailed_csv_path: Path
    judged_csv_path: Path


@lru_cache
def get_settings() -> Settings:
    app_root = Path(__file__).resolve().parents[1]
    project_root = Path(__file__).resolve().parents[2]
    default_detailed_csv = app_root / "artifacts" / "s3_xai_detailed_comparison_hdbscan_25_llm_as_judge.csv"
    default_judged_csv = app_root / "artifacts" / "s3_xai_judged_results_hdbscan_25.csv"
    configured_detailed_csv = os.getenv("XAI_DETAILED_CSV_PATH") or os.getenv("XAI_CSV_PATH")
    configured_judged_csv = os.getenv("XAI_JUDGED_CSV_PATH")

    return Settings(
        app_root=app_root,
        project_root=project_root,
        detailed_csv_path=Path(configured_detailed_csv) if configured_detailed_csv else default_detailed_csv,
        judged_csv_path=Path(configured_judged_csv) if configured_judged_csv else default_judged_csv,
    )
