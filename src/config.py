"""Configuration management using Pydantic BaseSettings.

Loads settings from environment variables and/or a .env file.
Provides type-hinted access to configuration values like API keys and paths.
"""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    RAPIDAPI_KEY: str
    CM_API_KEY: str | None = None
    # Etherscan API Key (Optional)
    ETHERSCAN_API_KEY: str | None = None
    # Project root directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    # Data directory derived from BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    # Directory for raw API response snapshots
    RAW_SNAPSHOT_DIR: Path = BASE_DIR / "snapshots"

    class Config:
        """Pydantic configuration settings."""

        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from environment variables


settings = Settings()
