"""Tests for live X, Apify, and TikTok HTTP clients."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.setenv("X_API_KEY", "x-key")
    monkeypatch.setenv("X_API_SECRET", "x-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "x-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "x-token-secret")
    monkeypatch.setenv("APIFY_API_TOKEN", "apify-token")
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "tt-token")
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "tt-key")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "tt-secret")
    from content_autopilot.settings import load_settings

    return load_settings()


def test_x_client_publish_post_uploads_then_creates_tweet(
    settings, tmp_path: Path
) -> None:
    photo = tmp_path / "cover.jpg"
    photo.write_bytes(b"jpeg-bytes")
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path.endswith("/1.1/media/upload.json"):
            return httpx.Response(200, json={"media_id_string": "media-1"})
        if request.url.path.endswith("/2/tweets"):
            return httpx.Response(201, json={"data": {"id": "999"}})
        return httpx.Response(404, json={"error": "unexpected"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    from content_autopilot.graph.clients import XClient

    url = XClient(settings, http_client=client).publish_post(
        media_paths=[str(photo)],
        text="Ship it",
    )
    assert url == "https://x.com/i/web/status/999"
    assert any("media/upload.json" in item for item in calls)
    assert any("/2/tweets" in item for item in calls)


def test_x_client_video_init_sends_form_body(settings, tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"0123456789")
    seen: dict[str, str] = {}
    status_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal status_calls
        if request.url.path.endswith("/1.1/media/upload.json"):
            content_type = request.headers.get("content-type", "")
            if "command=STATUS" in str(request.url):
                status_calls += 1
                return httpx.Response(
                    200,
                    json={"processing_info": {"state": "succeeded"}},
                )
            if content_type.startswith("application/x-www-form-urlencoded"):
                body = request.content.decode("utf-8")
                if "command=INIT" in body:
                    seen["init"] = body
                    return httpx.Response(200, json={"media_id_string": "vid-1"})
                if "command=FINALIZE" in body:
                    seen["finalize"] = body
                    return httpx.Response(
                        200,
                        json={
                            "media_id_string": "vid-1",
                            "processing_info": {
                                "state": "pending",
                                "check_after_secs": 0,
                            },
                        },
                    )
            if "command=APPEND" in str(request.url):
                return httpx.Response(200, json={})
            return httpx.Response(400, json={"error": "unexpected upload shape"})
        if request.url.path.endswith("/2/tweets"):
            return httpx.Response(201, json={"data": {"id": "42"}})
        return httpx.Response(404, json={"error": str(request.url)})

    from content_autopilot.graph.clients import XClient

    url = XClient(
        settings, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    ).publish_post(media_paths=[str(video)], text="vid")
    assert url.endswith("/42")
    assert "command=INIT" in seen["init"]
    assert "media_category=tweet_video" in seen["init"]
    assert status_calls >= 1


def test_apify_client_posts_start_urls(settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "website-content-crawler" in str(request.url)
        return httpx.Response(
            200,
            json=[{"url": "https://example.com", "text": "scraped page body"}],
        )

    from content_autopilot.graph.clients import ApifyClient

    result = ApifyClient(
        settings, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    ).research_urls(["https://example.com"])
    assert result is not None
    assert "scraped page body" in result


def test_x_client_fetch_context_returns_none_on_forbidden(settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/1.1/statuses/user_timeline.json")
        return httpx.Response(403, json={"errors": [{"message": "Forbidden"}]})

    from content_autopilot.graph.clients import XClient

    result = XClient(
        settings, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    ).fetch_context()
    assert result is None


def test_x_client_fetch_context_joins_timeline_texts(settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"text": "first post"}, {"full_text": "second post"}],
        )

    from content_autopilot.graph.clients import XClient

    result = XClient(
        settings, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    ).fetch_context()
    assert result == "first post | second post"


def test_tiktok_client_inits_and_uploads(settings, tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video-bytes")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/inbox/video/init/"):
            return httpx.Response(
                200,
                json={"data": {"upload_url": "https://upload.example/video", "publish_id": "pub-1"}},
            )
        if str(request.url) == "https://upload.example/video":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404, json={"error": str(request.url)})

    from content_autopilot.graph.clients import TikTokClient

    publish_id = TikTokClient(
        settings, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    ).publish_video(media_paths=[str(video)], caption="hello")
    assert publish_id == "pub-1"
