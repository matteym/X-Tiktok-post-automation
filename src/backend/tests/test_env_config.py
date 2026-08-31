"""RED: secure environment loading for content-autopilot."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import PACKAGE_ROOT


LOCALHOST_RE = re.compile(r"https?://(localhost|127\.0\.0\.1)", re.IGNORECASE)


def _iter_python_sources() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py")) if PACKAGE_ROOT.is_dir() else []


def test_load_settings_reads_database_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://autopilot:secret@db.example.internal:5432/content_autopilot",
    )
    from content_autopilot.config import load_settings

    settings = load_settings()
    assert settings.database_url == (
        "postgresql://autopilot:secret@db.example.internal:5432/content_autopilot"
    )


def test_load_settings_reads_api_base_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XAI_API_BASE_URL", "https://api.x.ai/v1")
    from content_autopilot.config import load_settings

    settings = load_settings()
    assert settings.xai_api_base_url == "https://api.x.ai/v1"


def test_config_module_uses_dotenv_for_env_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://fromdotenv:pass@db.example.internal:5432/app\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from content_autopilot.config import load_settings

    settings = load_settings()
    assert settings.database_url == "postgresql://fromdotenv:pass@db.example.internal:5432/app"


def test_production_sources_do_not_hardcode_localhost_urls() -> None:
    offenders: list[str] = []
    for path in _iter_python_sources():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if LOCALHOST_RE.search(line):
                offenders.append(f"{path.relative_to(PACKAGE_ROOT.parent)}:{line_no}: {line.strip()}")
    assert not offenders, "hardcoded localhost URLs forbidden in application source:\n" + "\n".join(
        offenders
    )
