"""Tests for Typer CLI media arguments and fingerprint wiring."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

BACKEND_ROOT = Path(__file__).resolve().parent.parent
CLI_MODULE = BACKEND_ROOT / "src" / "content_autopilot" / "cli.py"
RUN_INPUTS_MODULE = BACKEND_ROOT / "src" / "content_autopilot" / "media" / "run_inputs.py"

TITLE_MAX_LENGTH = 100

runner = CliRunner()


def _expected_fingerprint(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"{digest}:{len(content)}"


def _expected_set_hash(fingerprints: list[str]) -> str:
    payload = "\n".join(fingerprints)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.fixture
def media_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.jpg"
    third = tmp_path / "third.png"
    first.write_bytes(b"first-video-bytes")
    second.write_bytes(b"second-photo-bytes")
    third.write_bytes(b"third-photo-bytes")
    return first, second, third


def test_run_inputs_module_exists() -> None:
    assert RUN_INPUTS_MODULE.is_file()


def test_cli_module_defines_typer_app() -> None:
    from content_autopilot.cli import app

    assert app.info.name == "content-autopilot"


def test_cli_source_has_no_hardcoded_localhost() -> None:
    cli_source = CLI_MODULE.read_text(encoding="utf-8").lower()
    run_inputs_source = RUN_INPUTS_MODULE.read_text(encoding="utf-8").lower()

    assert "localhost" not in cli_source
    assert "127.0.0.1" not in cli_source
    assert "localhost" not in run_inputs_source
    assert "127.0.0.1" not in run_inputs_source


def test_collect_run_media_preserves_video_order_and_fingerprints(
    media_files: tuple[Path, Path, Path],
) -> None:
    from content_autopilot.media.run_inputs import collect_run_media

    first, second, third = media_files
    collected = collect_run_media(
        video_paths=[third, first, second],
        description="Launch recap",
    )

    assert collected.video_paths == [third, first, second]
    assert collected.filenames == ["third.png", "first.mp4", "second.jpg"]
    assert collected.media_fingerprints == [
        _expected_fingerprint(path.read_bytes())
        for path in (third, first, second)
    ]
    assert collected.media_set_hash == _expected_set_hash(collected.media_fingerprints)
    assert collected.description == "Launch recap"
    assert collected.github_url is None
    assert collected.twitter_url is None
    assert collected.tiktok_url is None


def test_collect_run_media_accepts_optional_urls(
    media_files: tuple[Path, Path, Path],
) -> None:
    from content_autopilot.media.run_inputs import collect_run_media

    first, _, _ = media_files
    collected = collect_run_media(
        video_paths=[first],
        description="With links",
        github_url="https://github.com/example/repo",
        twitter_url="https://x.com/example",
        tiktok_url="https://www.tiktok.com/@creator/video/1",
    )

    assert collected.github_url == "https://github.com/example/repo"
    assert collected.twitter_url == "https://x.com/example"
    assert collected.tiktok_url == "https://www.tiktok.com/@creator/video/1"


def test_collect_run_media_accepts_title_and_youtube_url(
    media_files: tuple[Path, Path, Path],
) -> None:
    from content_autopilot.media.run_inputs import collect_run_media

    first, _, _ = media_files
    collected = collect_run_media(
        video_paths=[first],
        description="Launch recap with research context",
        title="Launch recap",
        youtube_url="https://www.youtube.com/watch?v=research-hint",
    )

    assert collected.title == "Launch recap"
    assert collected.youtube_url == "https://www.youtube.com/watch?v=research-hint"


def test_collect_run_media_derives_title_from_truncated_description(
    media_files: tuple[Path, Path, Path],
) -> None:
    from content_autopilot.media.run_inputs import collect_run_media

    first, _, _ = media_files
    long_description = "x" * (TITLE_MAX_LENGTH + 25)
    collected = collect_run_media(
        video_paths=[first],
        description=long_description,
    )

    assert collected.title == long_description[:TITLE_MAX_LENGTH]
    assert len(collected.title) == TITLE_MAX_LENGTH


def test_collect_run_media_uses_full_description_as_title_when_short(
    media_files: tuple[Path, Path, Path],
) -> None:
    from content_autopilot.media.run_inputs import collect_run_media

    first, _, _ = media_files
    collected = collect_run_media(
        video_paths=[first],
        description="Short launch recap",
    )

    assert collected.title == "Short launch recap"


def test_collect_run_media_rejects_missing_video_path(tmp_path: Path) -> None:
    from content_autopilot.media.run_inputs import collect_run_media

    missing = tmp_path / "missing.mp4"

    with pytest.raises(FileNotFoundError, match="missing.mp4"):
        collect_run_media(
            video_paths=[missing],
            description="Missing media",
        )


def test_cli_run_requires_description(media_files: tuple[Path, Path, Path]) -> None:
    from content_autopilot.cli import app

    first, _, _ = media_files
    result = runner.invoke(
        app,
        ["run", "--video", str(first)],
    )

    assert result.exit_code != 0
    assert "description" in result.stderr.lower() or "description" in result.stdout.lower()


def test_cli_run_requires_at_least_one_video(tmp_path: Path) -> None:
    from content_autopilot.cli import app

    result = runner.invoke(
        app,
        ["run", "--description", "No media provided"],
    )

    assert result.exit_code != 0
    assert "video" in result.stderr.lower() or "video" in result.stdout.lower()


def test_cli_run_rejects_missing_video_path(tmp_path: Path) -> None:
    from content_autopilot.cli import app

    missing = tmp_path / "missing.mp4"
    result = runner.invoke(
        app,
        [
            "run",
            "--description",
            "Broken media path",
            "--video",
            str(missing),
        ],
    )

    assert result.exit_code != 0
    assert "missing.mp4" in result.stderr or "missing.mp4" in result.stdout


def test_cli_run_accepts_multiple_videos_and_optional_urls(
    media_files: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.cli import app

    first, second, third = media_files
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "x_post_url": "https://x.com/example/status/123456789",
        "tiktok_proposal": "Launch recap proposal",
        "tiktok_proposal_structured": {
            "publish_mode": "proposal",
            "caption": "Launch recap proposal",
            "hashtags": ["#launch"],
            "media_order": [str(first), str(second), str(third)],
        },
    }

    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.setattr(
        "content_autopilot.orchestration.build_content_autopilot_graph",
        lambda _settings, **kwargs: mock_graph,
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
            "--video",
            str(third),
            "--github",
            "https://github.com/example/repo",
            "--twitter",
            "https://x.com/example",
            "--tiktok",
            "https://www.tiktok.com/@creator/video/1",
            "--youtube",
            "https://www.youtube.com/@example",
        ],
    )

    assert result.exit_code == 0, result.stderr or result.stdout
    expected_fingerprints = [
        _expected_fingerprint(path.read_bytes()) for path in (first, second, third)
    ]
    for fingerprint in expected_fingerprints:
        assert fingerprint in result.stdout
    assert _expected_set_hash(expected_fingerprints) in result.stdout
    assert "Launch recap" in result.stdout


def test_cli_run_accepts_title_and_youtube_and_threads_graph_state(
    media_files: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.cli import app

    first, _, _ = media_files
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "x_post_url": "https://x.com/example/status/123456789",
        "tiktok_proposal": "Launch recap proposal",
        "tiktok_proposal_structured": {
            "publish_mode": "proposal",
            "caption": "Launch recap proposal",
            "hashtags": ["#launch"],
            "media_order": [str(first)],
        },
        "youtube_video_url": "https://www.youtube.com/watch?v=published-from-cli",
        "validation_passed": True,
    }

    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.setattr(
        "content_autopilot.orchestration.build_content_autopilot_graph",
        lambda _settings, **kwargs: mock_graph,
    )

    result = runner.invoke(
        app,
        [
            "run",
            "--description",
            "Launch recap with YouTube context",
            "--video",
            str(first),
            "--title",
            "Launch recap",
            "--youtube",
            "https://www.youtube.com/watch?v=research-hint",
            "--twitter",
            "https://x.com/example",
        ],
    )

    assert result.exit_code == 0, result.stderr or result.stdout
    mock_graph.invoke.assert_called_once()
    initial_state = mock_graph.invoke.call_args.args[0]
    assert initial_state["title"] == "Launch recap"
    assert initial_state["youtube_url"] == "https://www.youtube.com/watch?v=research-hint"
    assert initial_state["twitter_url"] == "https://x.com/example"
    assert "YouTube" in result.stdout
    assert "https://www.youtube.com/watch?v=published-from-cli" in result.stdout


def test_cli_run_derives_title_from_description_when_omitted(
    media_files: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.cli import app

    first, _, _ = media_files
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "x_post_url": "https://x.com/example/status/123456789",
        "validation_passed": True,
    }
    long_description = "y" * (TITLE_MAX_LENGTH + 10)

    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.setattr(
        "content_autopilot.orchestration.build_content_autopilot_graph",
        lambda _settings, **kwargs: mock_graph,
    )

    result = runner.invoke(
        app,
        [
            "run",
            "--description",
            long_description,
            "--video",
            str(first),
        ],
    )

    assert result.exit_code == 0, result.stderr or result.stdout
    initial_state = mock_graph.invoke.call_args.args[0]
    assert initial_state["title"] == long_description[:TITLE_MAX_LENGTH]
    assert initial_state.get("youtube_url") is None
