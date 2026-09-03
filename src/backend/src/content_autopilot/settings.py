"""Environment-backed settings for content-autopilot."""

from __future__ import annotations

import os
import socket
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_dotenv_path() -> Path | None:
    """Walk cwd and the package tree to the nearest ``.env`` (product root)."""
    cwd_env = Path.cwd() / ".env"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return cwd_env if cwd_env.is_file() else None
    seen: set[Path] = set()
    starts = [Path.cwd().resolve(), Path(__file__).resolve().parent]
    for start in starts:
        for base in [start, *start.parents]:
            resolved = base.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidate = resolved / ".env"
            if candidate.is_file():
                return candidate
    return None


def sqlalchemy_url(raw: str) -> str:
    """Normalize postgres URLs for SQLAlchemy + psycopg."""
    if "+psycopg" in raw:
        return raw
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://") :]
    return raw


def resolve_database_url(settings: Settings) -> str:
    """Prefer the docker hostname URL when it resolves; otherwise the host URL."""
    primary = settings.database_url
    hostname = urlparse(primary).hostname
    if hostname and settings.database_url_host:
        try:
            socket.getaddrinfo(hostname, None)
        except OSError:
            return settings.database_url_host
    return primary


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    database_url: str
    database_url_host: str | None = None
    grok_api_key: str = Field(
        validation_alias=AliasChoices("GROK_API_KEY", "XAI_API_KEY")
    )

    x_api_key: str | None = None
    x_api_secret: str | None = None
    x_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("X_ACCESS_TOKEN", "X_ACCES_TOKEN"),
    )
    x_access_token_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "X_ACCESS_TOKEN_SECRET", "X_ACCES_SECRET", "X_ACCESS_SECRET"
        ),
    )
    apify_api_token: str | None = None
    tiktok_access_token: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    youtube_client_secrets_file: str | None = None
    youtube_token_file: str | None = None

    x_api_base_url: str = Field(
        default="https://api.twitter.com",
        validation_alias=AliasChoices("X_API_BASE_URL"),
    )
    x_upload_base_url: str = Field(
        default="https://upload.twitter.com",
        validation_alias=AliasChoices("X_UPLOAD_BASE_URL"),
    )
    apify_api_base_url: str = Field(
        default="https://api.apify.com",
        validation_alias=AliasChoices("APIFY_API_BASE_URL"),
    )
    tiktok_api_base_url: str = Field(
        default="https://open.tiktokapis.com",
        validation_alias=AliasChoices("TIKTOK_API_BASE_URL"),
    )


def load_settings() -> Settings:
    """Load and validate settings from the environment and local ``.env`` file."""
    dotenv_path = find_dotenv_path()
    if dotenv_path is not None:
        load_dotenv(dotenv_path, override=False)
    return Settings()
