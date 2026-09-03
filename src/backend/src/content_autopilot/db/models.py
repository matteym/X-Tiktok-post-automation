"""SQLAlchemy models for persisted content-autopilot post runs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class UTCDateTime(TypeDecorator[datetime]):
    """Persist timezone-aware timestamps and normalize naive reads to UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    """Declarative base for content-autopilot database models."""


class PostRun(Base):
    """Stored metadata for a processed or published media post run."""

    __tablename__ = "post_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_set_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    media_fingerprints: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    filenames: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    tiktok_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    x_post_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    youtube_video_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    tiktok_proposal: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
