from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "PubMed Topic XAI"
    app_root: Path = Path(__file__).resolve().parents[1]
    project_root: Path = Path(__file__).resolve().parents[2]
    xai_csv_path: Path


@lru_cache
def get_settings() -> Settings:
    app_root = Path(__file__).resolve().parents[1]
    project_root = Path(__file__).resolve().parents[2]
    default_csv = app_root / "artifacts" / "s3_xai_detailed_comparison_hdbscan_25.csv"
    configured_csv = os.getenv("XAI_CSV_PATH")

    return Settings(
        app_root=app_root,
        project_root=project_root,
        xai_csv_path=Path(configured_csv) if configured_csv else default_csv,
    )
