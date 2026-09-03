"""Tests for PostgreSQL post-run deduplication and metadata persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_MODULE = BACKEND_ROOT / "src" / "content_autopilot" / "db" / "repository.py"

SAMPLE_FINGERPRINTS = ["deadbeef:1024", "cafebabe:2048"]
SAMPLE_FILENAMES = ["clip.mp4", "cover.jpg"]
SAMPLE_SET_HASH = "set-hash-abc"
OTHER_SET_HASH = "set-hash-other"


@pytest.fixture
def db_session(engine):
    from content_autopilot.db.schema import init_schema

    init_schema(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, database_url: str):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")

    from content_autopilot.settings import load_settings

    return load_settings()


def test_repository_module_exists() -> None:
    assert REPOSITORY_MODULE.is_file()


def test_repository_source_has_no_hardcoded_localhost() -> None:
    source = REPOSITORY_MODULE.read_text(encoding="utf-8").lower()

    assert "localhost" not in source
    assert "127.0.0.1" not in source


def test_repository_from_settings_uses_database_url(settings) -> None:
    from content_autopilot.db.repository import PostRunRepository

    repository = PostRunRepository.from_settings(settings)

    assert repository is not None


def test_find_existing_by_media_set_returns_none_when_empty(
    db_session: Session,
) -> None:
    from content_autopilot.db.repository import PostRunRepository

    repository = PostRunRepository(db_session)

    assert repository.find_existing_by_media_set(SAMPLE_SET_HASH) is None
    assert (
        repository.find_existing_by_media_set(
            SAMPLE_SET_HASH,
            media_fingerprints=SAMPLE_FINGERPRINTS,
        )
        is None
    )


def test_save_post_metadata_persists_post_run(db_session: Session) -> None:
    from content_autopilot.db.models import PostRun
    from content_autopilot.db.repository import PostRunRepository

    repository = PostRunRepository(db_session)
    created_at = datetime(2026, 8, 31, 15, 30, tzinfo=UTC)

    saved = repository.save_post_metadata(
        media_set_hash=SAMPLE_SET_HASH,
        media_fingerprints=SAMPLE_FINGERPRINTS,
        filenames=SAMPLE_FILENAMES,
        description="Launch recap",
        title="Launch recap",
        github_url="https://github.com/example/repo",
        twitter_url="https://x.com/example",
        tiktok_url="https://www.tiktok.com/@creator/video/1",
        x_post_url="https://x.com/example/status/99",
        youtube_url="https://www.youtube.com/watch?v=research-hint",
        youtube_video_url="https://www.youtube.com/watch?v=published-id",
        tiktok_proposal='{"caption":"Try this workflow"}',
        created_at=created_at,
    )

    stored = db_session.get(PostRun, saved.id)
    assert stored is not None
    assert stored.media_set_hash == SAMPLE_SET_HASH
    assert stored.media_fingerprints == SAMPLE_FINGERPRINTS
    assert stored.filenames == SAMPLE_FILENAMES
    assert stored.description == "Launch recap"
    assert stored.title == "Launch recap"
    assert stored.github_url == "https://github.com/example/repo"
    assert stored.twitter_url == "https://x.com/example"
    assert stored.tiktok_url == "https://www.tiktok.com/@creator/video/1"
    assert stored.x_post_url == "https://x.com/example/status/99"
    assert stored.youtube_url == "https://www.youtube.com/watch?v=research-hint"
    assert stored.youtube_video_url == "https://www.youtube.com/watch?v=published-id"
    assert stored.tiktok_proposal == '{"caption":"Try this workflow"}'
    assert stored.created_at == created_at


def test_save_post_metadata_allows_youtube_fields_to_be_null(
    db_session: Session,
) -> None:
    from content_autopilot.db.models import PostRun
    from content_autopilot.db.repository import PostRunRepository

    repository = PostRunRepository(db_session)

    saved = repository.save_post_metadata(
        media_set_hash=SAMPLE_SET_HASH,
        media_fingerprints=SAMPLE_FINGERPRINTS,
        filenames=SAMPLE_FILENAMES,
        description="Launch recap",
        title=None,
        youtube_url=None,
        youtube_video_url=None,
        created_at=datetime.now(tz=UTC),
    )

    stored = db_session.get(PostRun, saved.id)
    assert stored is not None
    assert stored.title is None
    assert stored.youtube_url is None
    assert stored.youtube_video_url is None


def test_find_existing_by_media_set_returns_saved_run(db_session: Session) -> None:
    from content_autopilot.db.repository import PostRunRepository

    repository = PostRunRepository(db_session)
    repository.save_post_metadata(
        media_set_hash=SAMPLE_SET_HASH,
        media_fingerprints=SAMPLE_FINGERPRINTS,
        filenames=SAMPLE_FILENAMES,
        description="Launch recap",
        x_post_url="https://x.com/example/status/99",
        created_at=datetime.now(tz=UTC),
    )

    existing = repository.find_existing_by_media_set(
        SAMPLE_SET_HASH,
        media_fingerprints=SAMPLE_FINGERPRINTS,
    )

    assert existing is not None
    assert existing.media_set_hash == SAMPLE_SET_HASH
    assert existing.media_fingerprints == SAMPLE_FINGERPRINTS
    assert existing.x_post_url == "https://x.com/example/status/99"


def test_find_existing_by_media_set_ignores_different_media_set(
    db_session: Session,
) -> None:
    from content_autopilot.db.repository import PostRunRepository

    repository = PostRunRepository(db_session)
    repository.save_post_metadata(
        media_set_hash=SAMPLE_SET_HASH,
        media_fingerprints=SAMPLE_FINGERPRINTS,
        filenames=SAMPLE_FILENAMES,
        description="Launch recap",
        created_at=datetime.now(tz=UTC),
    )

    assert repository.find_existing_by_media_set(OTHER_SET_HASH) is None
    assert (
        repository.find_existing_by_media_set(
            SAMPLE_SET_HASH,
            media_fingerprints=["different:999"],
        )
        is None
    )


def test_find_existing_by_media_set_ignores_reordered_fingerprints(
    db_session: Session,
) -> None:
    from content_autopilot.db.repository import PostRunRepository

    repository = PostRunRepository(db_session)
    repository.save_post_metadata(
        media_set_hash=SAMPLE_SET_HASH,
        media_fingerprints=SAMPLE_FINGERPRINTS,
        filenames=SAMPLE_FILENAMES,
        description="Launch recap",
        created_at=datetime.now(tz=UTC),
    )

    reordered = list(reversed(SAMPLE_FINGERPRINTS))
    assert (
        repository.find_existing_by_media_set(
            SAMPLE_SET_HASH,
            media_fingerprints=reordered,
        )
        is None
    )
