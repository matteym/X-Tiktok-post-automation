"""Tests for PostgreSQL docker-compose and env example configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
ENV_EXAMPLE_FILE = REPO_ROOT / ".env.example"


def test_docker_compose_declares_postgres_service() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert "postgres:" in compose
    assert "image: postgres:16-alpine" in compose


def test_docker_compose_mounts_pgdata_volume() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert "pgdata:/var/lib/postgresql/data" in compose
    assert "pgdata:" in compose


def test_docker_compose_postgres_healthcheck_uses_pg_isready() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert "healthcheck:" in compose
    assert "pg_isready" in compose
    assert "${POSTGRES_USER}" in compose
    assert "${POSTGRES_DB}" in compose


def test_docker_compose_postgres_uses_env_backed_credentials() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert "POSTGRES_USER: ${POSTGRES_USER}" in compose
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}" in compose
    assert "POSTGRES_DB: ${POSTGRES_DB}" in compose


def test_env_example_documents_database_urls() -> None:
    env_example = ENV_EXAMPLE_FILE.read_text(encoding="utf-8")

    assert "DATABASE_URL=" in env_example
    assert "DATABASE_URL_HOST=" in env_example
