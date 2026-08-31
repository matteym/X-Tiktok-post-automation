"""Database schema initialization helpers."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from content_autopilot.db.models import Base


def init_schema(engine: Engine) -> None:
    """Create database tables when they do not already exist."""
    Base.metadata.create_all(engine)
