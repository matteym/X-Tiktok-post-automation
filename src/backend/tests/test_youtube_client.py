"""Tests for YouTube Data API v3 OAuth upload client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
WATCH_URL_PREFIX = "https://www.youtube.com/watch?v="


@pytest.fixture
def base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")


@pytest.fixture
def youtube_settings(base_env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    secrets_path = tmp_path / "test-client.yt.json"
    token_path = tmp_path / "test-youtube-token.json"
    secrets_path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "test-client-id",
                    "client_secret": "test-client-secret",
                    "redirect_uris": ["http://127.0.0.1:8080/"],
                }
            }
        ),
        encoding="utf-8",
    )
    token_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRETS_FILE", str(secrets_path))
    monkeypatch.setenv("YOUTUBE_TOKEN_FILE", str(token_path))

    from content_autopilot.settings import load_settings

    return load_settings()


def test_youtube_client_is_exported_from_graph_clients() -> None:
    from content_autopilot.graph.clients import YouTubeClient

    assert YouTubeClient is not None


def test_youtube_client_source_has_no_hardcoded_oauth_secrets() -> None:
    import inspect

    from content_autopilot.graph import clients as clients_module

    assert hasattr(clients_module, "_build_youtube_service")
    source = inspect.getsource(clients_module._build_youtube_service).lower()

    assert "localhost" not in source
    assert "127.0.0.1" not in source
    assert "client_id" not in source
    assert "client_secret" not in source


def test_youtube_client_exposes_upload_scope_constant() -> None:
    from content_autopilot.graph.clients import YOUTUBE_UPLOAD_SCOPE as module_scope

    assert module_scope == YOUTUBE_UPLOAD_SCOPE


def test_youtube_client_has_credentials_false_without_oauth_paths(
    base_env,
) -> None:
    from content_autopilot.settings import load_settings
    from content_autopilot.graph.clients import YouTubeClient

    settings = load_settings()
    client = YouTubeClient(settings)

    assert client.has_credentials() is False


def test_youtube_client_has_credentials_true_when_oauth_paths_configured(
    youtube_settings,
) -> None:
    from content_autopilot.graph.clients import YouTubeClient

    client = YouTubeClient(youtube_settings)

    assert client.has_credentials() is True


def test_youtube_client_upload_video_raises_without_credentials(
    base_env,
    tmp_path: Path,
) -> None:
    from content_autopilot.settings import load_settings
    from content_autopilot.graph.clients import YouTubeClient

    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video-bytes")
    client = YouTubeClient(load_settings())

    with pytest.raises(ValueError, match="credentials"):
        client.upload_video(media_paths=[str(video)], title="Launch recap")


def test_youtube_client_upload_video_skips_photos_and_uploads_first_video(
    youtube_settings,
    tmp_path: Path,
) -> None:
    from content_autopilot.graph.clients import YouTubeClient

    cover = tmp_path / "cover.jpg"
    first_video = tmp_path / "first.mp4"
    second_video = tmp_path / "second.mp4"
    cover.write_bytes(b"photo-bytes")
    first_video.write_bytes(b"first-video-bytes")
    second_video.write_bytes(b"second-video-bytes")

    mock_service = MagicMock()
    insert_request = MagicMock()
    insert_request.execute.return_value = {"id": "uploaded-video-id"}
    mock_service.videos.return_value.insert.return_value = insert_request

    client = YouTubeClient(youtube_settings, youtube_service=mock_service)
    watch_url = client.upload_video(
        media_paths=[str(cover), str(first_video), str(second_video)],
        title="Launch recap",
    )

    assert watch_url == f"{WATCH_URL_PREFIX}uploaded-video-id"
    body = mock_service.videos.return_value.insert.call_args.kwargs["body"]
    assert body["snippet"]["title"] == "Launch recap"
    media_body = mock_service.videos.return_value.insert.call_args.kwargs["media_body"]
    assert media_body is not None
    assert str(first_video) in str(getattr(media_body, "filename", media_body))


def test_youtube_client_builds_service_from_settings_paths(
    youtube_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from content_autopilot.graph.clients import YouTubeClient

    captured: dict[str, object] = {}

    def fake_build_youtube_service(settings, *, scopes):
        captured["secrets_file"] = settings.youtube_client_secrets_file
        captured["token_file"] = settings.youtube_token_file
        captured["scopes"] = scopes
        return MagicMock()

    monkeypatch.setattr(
        "content_autopilot.graph.clients._build_youtube_service",
        fake_build_youtube_service,
    )

    YouTubeClient(youtube_settings)

    assert captured["secrets_file"] == youtube_settings.youtube_client_secrets_file
    assert captured["token_file"] == youtube_settings.youtube_token_file
    assert captured["scopes"] == [YOUTUBE_UPLOAD_SCOPE]
