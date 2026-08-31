"""Environment-backed settings for content-autopilot."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    grok_api_key: str

    x_api_key: str | None = None
    x_api_secret: str | None = None
    x_access_token: str | None = None
    x_access_token_secret: str | None = None
    apify_api_token: str | None = None
    tiktok_access_token: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None


def load_settings() -> Settings:
    """Load and validate settings from the environment and local ``.env`` file."""
    dotenv_path = Path(".env")
    if dotenv_path.is_file():
        load_dotenv(dotenv_path)
    return Settings()
