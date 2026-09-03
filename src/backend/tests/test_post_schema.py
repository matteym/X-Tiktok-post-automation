"""Tests for SQLAlchemy post-run schema and database initialization."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DB_PACKAGE = BACKEND_ROOT / "src" / "content_autopilot" / "db"

REQUIRED_POST_RUN_COLUMNS = {
    "id",
    "media_set_hash",
    "media_fingerprints",
    "filenames",
    "description",
    "title",
    "github_url",
    "tiktok_url",
    "x_post_url",
    "youtube_url",
    "youtube_video_url",
    "tiktok_proposal",
    "created_at",
}


def test_db_package_modules_exist() -> None:
    assert (DB_PACKAGE / "__init__.py").is_file()
    assert (DB_PACKAGE / "models.py").is_file()
    assert (DB_PACKAGE / "schema.py").is_file()


def test_app_db_source_has_no_hardcoded_localhost() -> None:
    db_modules = list(DB_PACKAGE.glob("*.py"))
    assert db_modules, "db package modules must exist"

    for path in db_modules:
        source = path.read_text(encoding="utf-8").lower()
        assert "localhost" not in source, f"{path.name} must not hardcode localhost"
        assert "127.0.0.1" not in source, f"{path.name} must not hardcode 127.0.0.1"


def test_init_schema_creates_post_runs_table(engine) -> None:
    from content_autopilot.db.models import PostRun
    from content_autopilot.db.schema import init_schema

    init_schema(engine)

    table_names = inspect(engine).get_table_names()
    assert PostRun.__tablename__ in table_names


def test_post_run_table_has_required_columns(engine) -> None:
    from content_autopilot.db.models import PostRun
    from content_autopilot.db.schema import init_schema

    init_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns(PostRun.__tablename__)}
    assert REQUIRED_POST_RUN_COLUMNS.issubset(columns)


@pytest.fixture
def db_session(engine):
    from content_autopilot.db.schema import init_schema

    init_schema(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.rollback()
    session.close()


def test_persist_post_run_with_ordered_media_metadata(db_session: Session) -> None:
    from content_autopilot.db.models import PostRun

    created_at = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
    run = PostRun(
        media_set_hash="set-hash-abc",
        media_fingerprints=["deadbeef:1024", "cafebabe:2048"],
        filenames=["clip.mp4", "cover.jpg"],
        description="Launch day recap",
        title="Launch day recap",
        github_url="https://github.com/example/repo",
        tiktok_url="https://www.tiktok.com/@creator/video/1",
        x_post_url="https://x.com/example/status/99",
        youtube_url="https://www.youtube.com/watch?v=research-hint",
        youtube_video_url="https://www.youtube.com/watch?v=published-id",
        tiktok_proposal='{"caption":"Try this workflow","hashtags":["#buildinpublic"]}',
        created_at=created_at,
    )
    db_session.add(run)
    db_session.commit()

    stored = db_session.query(PostRun).one()
    assert stored.media_set_hash == "set-hash-abc"
    assert stored.media_fingerprints == ["deadbeef:1024", "cafebabe:2048"]
    assert stored.filenames == ["clip.mp4", "cover.jpg"]
    assert stored.description == "Launch day recap"
    assert stored.title == "Launch day recap"
    assert stored.github_url == "https://github.com/example/repo"
    assert stored.tiktok_url == "https://www.tiktok.com/@creator/video/1"
    assert stored.x_post_url == "https://x.com/example/status/99"
    assert stored.youtube_url == "https://www.youtube.com/watch?v=research-hint"
    assert stored.youtube_video_url == "https://www.youtube.com/watch?v=published-id"
    assert "caption" in stored.tiktok_proposal
    assert stored.created_at == created_at


def test_persist_post_run_allows_optional_urls_to_be_null(db_session: Session) -> None:
    from content_autopilot.db.models import PostRun

    run = PostRun(
        media_set_hash="set-hash-minimal",
        media_fingerprints=["abc123:512"],
        filenames=["photo.png"],
        description="Minimal run",
        title=None,
        github_url=None,
        tiktok_url=None,
        x_post_url=None,
        youtube_url=None,
        youtube_video_url=None,
        tiktok_proposal=None,
        created_at=datetime.now(tz=UTC),
    )
    db_session.add(run)
    db_session.commit()

    stored = db_session.query(PostRun).filter_by(media_set_hash="set-hash-minimal").one()
    assert stored.title is None
    assert stored.github_url is None
    assert stored.tiktok_url is None
    assert stored.x_post_url is None
    assert stored.youtube_url is None
    assert stored.youtube_video_url is None
    assert stored.tiktok_proposal is None
