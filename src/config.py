# src/config.py

from __future__ import annotations

from pathlib import Path
from pydantic import BaseSettings


class Settings(BaseSettings):
    RAPIDAPI_KEY: str
    CM_API_KEY: str | None = None
    # Project root directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    # Data directory derived from BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"

    class Config:
        env_file = ".env"


settings = Settings()