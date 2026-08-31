"""Tests for the full content-autopilot CLI orchestration run flow."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

BACKEND_ROOT = Path(__file__).resolve().parent.parent
CLI_MODULE = BACKEND_ROOT / "src" / "content_autopilot" / "cli.py"
ORCHESTRATION_MODULE = BACKEND_ROOT / "src" / "content_autopilot" / "orchestration.py"

runner = CliRunner()

DUPLICATE_WARNING = "Warning: This media set was already posted"

PROGRESS_STEPS = (
    "Understand",
    "Research",
    "Analyze",
    "Strategy",
    "Generate",
    "Validate",
    "Publish",
    "TikTok",
)

MOCK_GRAPH_RESULT: dict[str, Any] = {
    "x_post_url": "https://x.com/example/status/123456789",
    "tiktok_proposal": "30s demo script showing ordered media upload and publish.",
    "tiktok_proposal_structured": {
        "publish_mode": "proposal",
        "caption": "30s demo script showing ordered media upload and publish.",
        "hashtags": ["#buildinpublic", "#devtools"],
        "media_order": [],
    },
    "validation_passed": True,
}


def _expected_fingerprint(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"{digest}:{len(content)}"


def _expected_set_hash(fingerprints: list[str]) -> str:
    payload = "\n".join(fingerprints)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.fixture
def media_files(tmp_path: Path) -> tuple[Path, Path]:
    first = tmp_path / "clip.mp4"
    second = tmp_path / "cover.jpg"
    first.write_bytes(b"first-video-bytes")
    second.write_bytes(b"second-photo-bytes")
    return first, second


@pytest.fixture
def db_session(engine):
    from content_autopilot.db.schema import init_schema

    init_schema(engine)
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=engine)()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, database_url: str):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.setenv("X_API_KEY", "x-key")
    monkeypatch.setenv("X_API_SECRET", "x-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "x-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "x-token-secret")

    from content_autopilot.settings import load_settings

    return load_settings()


@pytest.fixture
def repository(db_session):
    from content_autopilot.db.repository import PostRunRepository

    return PostRunRepository(db_session)


@pytest.fixture
def mock_compiled_graph(media_files: tuple[Path, Path]) -> MagicMock:
    first, second = media_files
    graph = MagicMock()
    graph.invoke.return_value = {
        **MOCK_GRAPH_RESULT,
        "tiktok_proposal_structured": {
            **MOCK_GRAPH_RESULT["tiktok_proposal_structured"],
            "media_order": [str(first), str(second)],
        },
    }
    return graph


def test_orchestration_module_exists() -> None:
    assert ORCHESTRATION_MODULE.is_file()


def test_orchestration_source_has_no_hardcoded_localhost() -> None:
    assert ORCHESTRATION_MODULE.is_file()
    source = ORCHESTRATION_MODULE.read_text(encoding="utf-8").lower()
    assert "localhost" not in source
    assert "127.0.0.1" not in source


def test_cli_run_wires_orchestration_module() -> None:
    source = CLI_MODULE.read_text(encoding="utf-8")
    assert "orchestration" in source


def test_execute_run_invokes_full_langgraph_dag(
    media_files: tuple[Path, Path],
    settings,
    repository,
    mock_compiled_graph: MagicMock,
) -> None:
    import content_autopilot.orchestration as orchestration

    assert hasattr(orchestration, "execute_run")
    execute_run = orchestration.execute_run

    first, second = media_files
    output: list[str] = []

    exit_code = execute_run(
        video_paths=[first, second],
        description="Launch recap",
        settings=settings,
        repository=repository,
        graph=mock_compiled_graph,
        confirm=lambda _: True,
        echo=output.append,
    )

    assert exit_code == 0
    mock_compiled_graph.invoke.assert_called_once()
    invoked_state = mock_compiled_graph.invoke.call_args.args[0]
    assert invoked_state["media_paths"] == [str(first), str(second)]
    assert invoked_state["description"] == "Launch recap"


def test_execute_run_persists_metadata_after_success(
    media_files: tuple[Path, Path],
    settings,
    repository,
    mock_compiled_graph: MagicMock,
    db_session,
) -> None:
    import content_autopilot.orchestration as orchestration
    from content_autopilot.db.models import PostRun
    from sqlalchemy import select

    execute_run = orchestration.execute_run
    first, second = media_files
    fingerprints = [
        _expected_fingerprint(path.read_bytes()) for path in (first, second)
    ]

    exit_code = execute_run(
        video_paths=[first, second],
        description="Launch recap",
        settings=settings,
        repository=repository,
        graph=mock_compiled_graph,
        confirm=lambda _: True,
        echo=lambda _line: None,
    )

    assert exit_code == 0
    stored = db_session.scalars(select(PostRun)).all()
    assert len(stored) == 1
    assert stored[0].media_fingerprints == fingerprints
    assert stored[0].x_post_url == MOCK_GRAPH_RESULT["x_post_url"]
    assert stored[0].description == "Launch recap"


def test_execute_run_emits_progress_steps_and_final_summary(
    media_files: tuple[Path, Path],
    settings,
    repository,
    mock_compiled_graph: MagicMock,
) -> None:
    import content_autopilot.orchestration as orchestration

    execute_run = orchestration.execute_run
    first, second = media_files
    output: list[str] = []

    execute_run(
        video_paths=[first, second],
        description="Launch recap",
        settings=settings,
        repository=repository,
        graph=mock_compiled_graph,
        confirm=lambda _: True,
        echo=output.append,
    )

    combined = "\n".join(output)
    for step in PROGRESS_STEPS:
        assert step in combined
    assert MOCK_GRAPH_RESULT["x_post_url"] in combined
    assert "TikTok proposal" in combined or "TikTok" in combined


def test_execute_run_warns_on_duplicate_media_set(
    media_files: tuple[Path, Path],
    settings,
    repository,
    mock_compiled_graph: MagicMock,
) -> None:
    import content_autopilot.orchestration as orchestration

    execute_run = orchestration.execute_run
    first, second = media_files
    fingerprints = [
        _expected_fingerprint(path.read_bytes()) for path in (first, second)
    ]
    media_set_hash = _expected_set_hash(fingerprints)

    repository.save_post_metadata(
        media_set_hash=media_set_hash,
        media_fingerprints=fingerprints,
        filenames=[first.name, second.name],
        description="Prior launch recap",
        x_post_url="https://x.com/example/status/prior",
        created_at=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
    )

    output: list[str] = []
    execute_run(
        video_paths=[first, second],
        description="Launch recap again",
        settings=settings,
        repository=repository,
        graph=mock_compiled_graph,
        confirm=lambda _: False,
        echo=output.append,
    )

    combined = "\n".join(output)
    assert DUPLICATE_WARNING in combined
    assert "Prior launch recap" in combined
    assert "https://x.com/example/status/prior" in combined


def test_execute_run_aborts_duplicate_when_confirmation_declined(
    media_files: tuple[Path, Path],
    settings,
    repository,
    mock_compiled_graph: MagicMock,
    db_session,
) -> None:
    import content_autopilot.orchestration as orchestration
    from sqlalchemy import func, select

    from content_autopilot.db.models import PostRun

    execute_run = orchestration.execute_run
    first, second = media_files
    fingerprints = [
        _expected_fingerprint(path.read_bytes()) for path in (first, second)
    ]

    repository.save_post_metadata(
        media_set_hash=_expected_set_hash(fingerprints),
        media_fingerprints=fingerprints,
        filenames=[first.name, second.name],
        description="Prior launch recap",
        x_post_url="https://x.com/example/status/prior",
        created_at=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
    )

    exit_code = execute_run(
        video_paths=[first, second],
        description="Launch recap again",
        settings=settings,
        repository=repository,
        graph=mock_compiled_graph,
        confirm=lambda _: False,
        echo=lambda _line: None,
    )

    assert exit_code == 0
    mock_compiled_graph.invoke.assert_not_called()
    assert db_session.scalar(select(func.count()).select_from(PostRun)) == 1


def test_execute_run_proceeds_on_duplicate_when_user_confirms(
    media_files: tuple[Path, Path],
    settings,
    repository,
    mock_compiled_graph: MagicMock,
    db_session,
) -> None:
    import content_autopilot.orchestration as orchestration
    from sqlalchemy import func, select

    from content_autopilot.db.models import PostRun

    execute_run = orchestration.execute_run
    first, second = media_files
    fingerprints = [
        _expected_fingerprint(path.read_bytes()) for path in (first, second)
    ]

    repository.save_post_metadata(
        media_set_hash=_expected_set_hash(fingerprints),
        media_fingerprints=fingerprints,
        filenames=[first.name, second.name],
        description="Prior launch recap",
        x_post_url="https://x.com/example/status/prior",
        created_at=datetime(2026, 8, 30, 12, 0, tzinfo=UTC),
    )

    exit_code = execute_run(
        video_paths=[first, second],
        description="Launch recap again",
        settings=settings,
        repository=repository,
        graph=mock_compiled_graph,
        confirm=lambda _: True,
        echo=lambda _line: None,
    )

    assert exit_code == 0
    mock_compiled_graph.invoke.assert_called_once()
    assert db_session.scalar(select(func.count()).select_from(PostRun)) == 2


def test_cli_run_end_to_end_with_mocked_graph(
    media_files: tuple[Path, Path],
    settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.cli import app

    first, second = media_files
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        **MOCK_GRAPH_RESULT,
        "tiktok_proposal_structured": {
            **MOCK_GRAPH_RESULT["tiktok_proposal_structured"],
            "media_order": [str(first), str(second)],
        },
    }

    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("GROK_API_KEY", settings.grok_api_key)

    def _build_graph(_settings, **kwargs):
        del _settings, kwargs
        return mock_graph

    monkeypatch.setattr(
        "content_autopilot.orchestration.build_content_autopilot_graph",
        _build_graph,
    )

    result = runner.invoke(
        app,
        [
            "run",
            "--description",
            "Launch recap",
            "--video",
            str(first),
            "--video",
            str(second),
        ],
    )

    assert result.exit_code == 0, result.stderr or result.stdout
    mock_graph.invoke.assert_called_once()
    assert MOCK_GRAPH_RESULT["x_post_url"] in result.stdout
    assert any(step in result.stdout for step in PROGRESS_STEPS)
