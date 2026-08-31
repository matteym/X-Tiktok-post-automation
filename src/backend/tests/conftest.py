"""Shared pytest fixtures for content-autopilot backend tests."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@pytest.fixture(scope="session")
def database_url() -> str:
    """Use DATABASE_URL from the environment, or an in-memory SQLite DB in tests."""
    configured = os.environ.get("DATABASE_URL")
    if configured:
        return configured
    return "sqlite+pysqlite:///:memory:"


@pytest.fixture
def engine(database_url: str) -> Engine:
    eng = create_engine(database_url)
    yield eng
    eng.dispose()
