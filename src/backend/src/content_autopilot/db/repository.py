"""PostgreSQL repository for post-run deduplication and persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from content_autopilot.db.models import PostRun
from content_autopilot.db.schema import init_schema
from content_autopilot.settings import Settings, resolve_database_url, sqlalchemy_url


class PostRunRepository:
    """Persist and query post-run metadata using ``DATABASE_URL`` from settings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @classmethod
    def from_settings(cls, settings: Settings) -> PostRunRepository:
        engine = create_engine(sqlalchemy_url(resolve_database_url(settings)))
        init_schema(engine)
        session = sessionmaker(bind=engine)()
        return cls(session)

    def find_existing_by_media_set(
        self,
        media_set_hash: str,
        media_fingerprints: Sequence[str] | None = None,
    ) -> PostRun | None:
        query = select(PostRun).where(PostRun.media_set_hash == media_set_hash)
        if media_fingerprints is not None:
            query = query.where(PostRun.media_fingerprints == list(media_fingerprints))

        return self._session.scalars(query).first()

    def save_post_metadata(
        self,
        media_set_hash: str,
        media_fingerprints: Sequence[str],
        filenames: Sequence[str],
        description: str,
        *,
        title: str | None = None,
        github_url: str | None = None,
        twitter_url: str | None = None,
        tiktok_url: str | None = None,
        x_post_url: str | None = None,
        youtube_url: str | None = None,
        youtube_video_url: str | None = None,
        tiktok_proposal: str | None = None,
        created_at: datetime | None = None,
    ) -> PostRun:
        run = PostRun(
            media_set_hash=media_set_hash,
            media_fingerprints=list(media_fingerprints),
            filenames=list(filenames),
            description=description,
            title=title,
            github_url=github_url,
            twitter_url=twitter_url,
            tiktok_url=tiktok_url,
            x_post_url=x_post_url,
            youtube_url=youtube_url,
            youtube_video_url=youtube_video_url,
            tiktok_proposal=tiktok_proposal,
            created_at=created_at or datetime.now(tz=UTC),
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run
