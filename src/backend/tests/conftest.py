"""Shared pytest fixtures for content-autopilot scaffold tests."""

from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = BACKEND_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "content_autopilot"
PYPROJECT = BACKEND_ROOT / "pyproject.toml"
