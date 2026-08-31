"""Environment-backed configuration for content-autopilot."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str | None = None
    xai_api_base_url: str | None = None


def load_settings() -> Settings:
    load_dotenv(find_dotenv(usecwd=True))
    return Settings(
        database_url=os.environ.get("DATABASE_URL"),
        xai_api_base_url=os.environ.get("XAI_API_BASE_URL"),
    )
