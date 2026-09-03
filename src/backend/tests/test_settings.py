"""Tests for pydantic-settings based environment configuration."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent.parent
SETTINGS_MODULE = BACKEND_ROOT / "src" / "content_autopilot" / "settings.py"
ENV_EXAMPLE_FILE = REPO_ROOT / ".env.example"
GITIGNORE_FILE = REPO_ROOT / ".gitignore"

REQUIRED_ENV = {
    "DATABASE_URL": "postgres://app:secret@postgres:5432/app",
    "GROK_API_KEY": "test-grok-api-key",
}


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def _clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DATABASE_URL",
        "GROK_API_KEY",
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
        "APIFY_API_TOKEN",
        "TIKTOK_ACCESS_TOKEN",
        "TIKTOK_CLIENT_KEY",
        "TIKTOK_CLIENT_SECRET",
        "YOUTUBE_CLIENT_SECRETS_FILE",
        "YOUTUBE_TOKEN_FILE",
    ):
        monkeypatch.delenv(key, raising=False)


def test_settings_module_exists() -> None:
    assert SETTINGS_MODULE.is_file()


def test_settings_source_has_no_hardcoded_localhost() -> None:
    source = SETTINGS_MODULE.read_text(encoding="utf-8").lower()

    assert "localhost" not in source
    assert "127.0.0.1" not in source


def test_settings_class_is_pydantic_settings_model() -> None:
    from pydantic_settings import BaseSettings

    from content_autopilot.settings import Settings

    assert issubclass(Settings, BaseSettings)


def test_load_settings_reads_required_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.settings import load_settings

    _clear_settings_env(monkeypatch)
    _set_required_env(monkeypatch)

    settings = load_settings()

    assert settings.database_url == REQUIRED_ENV["DATABASE_URL"]
    assert settings.grok_api_key == REQUIRED_ENV["GROK_API_KEY"]


def test_load_settings_reads_optional_api_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.settings import load_settings

    _clear_settings_env(monkeypatch)
    _set_required_env(monkeypatch)
    monkeypatch.setenv("X_API_KEY", "x-key")
    monkeypatch.setenv("X_API_SECRET", "x-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "x-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "x-token-secret")
    monkeypatch.setenv("APIFY_API_TOKEN", "apify-token")
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "tiktok-token")
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "tiktok-client-key")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "tiktok-client-secret")

    settings = load_settings()

    assert settings.x_api_key == "x-key"
    assert settings.x_api_secret == "x-secret"
    assert settings.x_access_token == "x-token"
    assert settings.x_access_token_secret == "x-token-secret"
    assert settings.apify_api_token == "apify-token"
    assert settings.tiktok_access_token == "tiktok-token"
    assert settings.tiktok_client_key == "tiktok-client-key"
    assert settings.tiktok_client_secret == "tiktok-client-secret"


def test_load_settings_leaves_optional_credentials_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.settings import load_settings

    _clear_settings_env(monkeypatch)
    _set_required_env(monkeypatch)

    settings = load_settings()

    assert settings.x_api_key is None
    assert settings.x_api_secret is None
    assert settings.x_access_token is None
    assert settings.x_access_token_secret is None
    assert settings.apify_api_token is None
    assert settings.tiktok_access_token is None
    assert settings.tiktok_client_key is None
    assert settings.tiktok_client_secret is None
    assert settings.youtube_client_secrets_file is None
    assert settings.youtube_token_file is None


def test_load_settings_reads_youtube_oauth_file_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.settings import load_settings

    _clear_settings_env(monkeypatch)
    _set_required_env(monkeypatch)
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRETS_FILE", "secrets/client.yt.json")
    monkeypatch.setenv("YOUTUBE_TOKEN_FILE", "secrets/youtube_token.json")

    settings = load_settings()

    assert settings.youtube_client_secrets_file == "secrets/client.yt.json"
    assert settings.youtube_token_file == "secrets/youtube_token.json"


def test_env_example_documents_youtube_oauth_file_paths() -> None:
    env_example = ENV_EXAMPLE_FILE.read_text(encoding="utf-8")

    assert "YOUTUBE_CLIENT_SECRETS_FILE=" in env_example
    assert "YOUTUBE_TOKEN_FILE=" in env_example


def test_gitignore_ignores_youtube_oauth_artifacts() -> None:
    gitignore = GITIGNORE_FILE.read_text(encoding="utf-8")

    assert "client.yt.json" in gitignore
    assert "*.yt.json" in gitignore
    assert "youtube_token.json" in gitignore


def test_load_settings_missing_database_url_has_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.settings import load_settings

    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("GROK_API_KEY", REQUIRED_ENV["GROK_API_KEY"])

    with pytest.raises(ValidationError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    assert "DATABASE_URL" in message or "database_url" in message


def test_load_settings_missing_grok_api_key_has_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.settings import load_settings

    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", REQUIRED_ENV["DATABASE_URL"])

    with pytest.raises(ValidationError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    assert "GROK_API_KEY" in message or "grok_api_key" in message


def test_load_settings_accepts_xai_and_typo_x_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.settings import load_settings

    _clear_settings_env(monkeypatch)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", REQUIRED_ENV["DATABASE_URL"])
    monkeypatch.setenv("XAI_API_KEY", "from-xai")
    monkeypatch.setenv("X_ACCES_TOKEN", "typo-token")
    monkeypatch.setenv("X_ACCES_SECRET", "typo-secret")

    settings = load_settings()

    assert settings.grok_api_key == "from-xai"
    assert settings.x_access_token == "typo-token"
    assert settings.x_access_token_secret == "typo-secret"


def test_resolve_database_url_falls_back_to_host_when_docker_name_does_not_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import socket

    from content_autopilot.settings import Settings, resolve_database_url

    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgres://app:secret@postgres:5432/app")
    monkeypatch.setenv(
        "DATABASE_URL_HOST", "postgres://app:secret@example.invalid:5432/app"
    )
    monkeypatch.setenv("GROK_API_KEY", "k")

    def _fail_lookup(host, *args, **kwargs):
        del args, kwargs
        raise OSError("name not found")

    monkeypatch.setattr(socket, "getaddrinfo", _fail_lookup)
    settings = Settings()
    assert resolve_database_url(settings) == settings.database_url_host


def test_sqlalchemy_url_uses_psycopg_driver() -> None:
    from content_autopilot.settings import sqlalchemy_url

    assert sqlalchemy_url("postgres://app:x@postgres:5432/app").startswith(
        "postgresql+psycopg://"
    )


def test_load_settings_reads_dotenv_for_local_development(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot import settings as settings_module
    from content_autopilot.settings import load_settings

    importlib.reload(settings_module)

    _clear_settings_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgres://app:secret@postgres:5432/app",
                "GROK_API_KEY=dotenv-grok-key",
                "APIFY_API_TOKEN=dotenv-apify-token",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_settings()

    assert loaded.database_url == "postgres://app:secret@postgres:5432/app"
    assert loaded.grok_api_key == "dotenv-grok-key"
    assert loaded.apify_api_token == "dotenv-apify-token"
