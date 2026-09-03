"""Database schema initialization helpers."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from content_autopilot.db.models import Base


def init_schema(engine: Engine) -> None:
    """Create database tables when they do not already exist."""
    Base.metadata.create_all(engine)
    if engine.dialect.name != "postgresql":
        return
    # Existing installs may still have json columns; equality needs jsonb.
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE post_runs "
                "ALTER COLUMN media_fingerprints TYPE jsonb "
                "USING media_fingerprints::jsonb, "
                "ALTER COLUMN filenames TYPE jsonb "
                "USING filenames::jsonb"
            )
        )
