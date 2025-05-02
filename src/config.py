# src/config.py

from __future__ import annotations

from pathlib import Path
from pydantic import BaseSettings


class Settings(BaseSettings):
    RAPIDAPI_KEY: str
    CM_API_KEY: str | None = None
    DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"

    class Config:
        env_file = ".env"


settings = Settings()