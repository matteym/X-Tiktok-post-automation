"""External service clients for graph research and publish nodes."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from pathlib import Path

import httpx

from content_autopilot.graph.oauth1 import oauth1_authorization_header
from content_autopilot.settings import Settings

DEFAULT_XAI_BASE_URL = "https://api.x.ai/v1"
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
CHUNK_SIZE = 4 * 1024 * 1024


class GrokClient:
    """Minimal xAI Grok chat client backed by ``GROK_API_KEY`` settings."""

    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = settings.grok_api_key
        self._base_url = base_url or os.environ.get("XAI_API_BASE_URL", DEFAULT_XAI_BASE_URL)
        self._http_client = http_client or httpx.Client(timeout=30.0)

    def generate(self, prompt: str) -> str:
        response = self._http_client.post(
            f"{self._base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.environ.get("XAI_MODEL", "grok-2-latest"),
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]


class XClient:
    """X API client: timeline context, media upload, and post creation."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client(timeout=60.0)

    def fetch_context(self) -> str | None:
        if not self.has_credentials():
            return None
        url = f"{self._settings.x_api_base_url.rstrip('/')}/1.1/statuses/user_timeline.json"
        response = self._signed_request(
            "GET",
            url,
            params={"count": "5", "trim_user": "true"},
        )
        response.raise_for_status()
        tweets = response.json()
        if not isinstance(tweets, list) or not tweets:
            return None
        texts = [str(item.get("text") or item.get("full_text") or "").strip() for item in tweets]
        joined = " | ".join(text for text in texts if text)
        return joined or None

    def has_credentials(self) -> bool:
        return _has_x_credentials(self._settings)

    def publish_post(self, *, media_paths: Sequence[str], text: str) -> str:
        """Upload media in order and create an X post when credentials are configured."""
        if not self.has_credentials():
            raise ValueError("X credentials not configured")
        media_ids = [self._upload_media(Path(path)) for path in media_paths]
        payload: dict[str, object] = {"text": text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        url = f"{self._settings.x_api_base_url.rstrip('/')}/2/tweets"
        response = self._signed_request("POST", url, json_body=payload)
        response.raise_for_status()
        tweet_id = response.json()["data"]["id"]
        return f"https://x.com/i/web/status/{tweet_id}"

    def _upload_media(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in VIDEO_EXTENSIONS:
            return self._upload_video(path)
        return self._upload_simple(path, "tweet_image" if suffix in PHOTO_EXTENSIONS else "tweet_image")

    def _upload_simple(self, path: Path, media_category: str) -> str:
        url = f"{self._settings.x_upload_base_url.rstrip('/')}/1.1/media/upload.json"
        with path.open("rb") as handle:
            response = self._signed_request(
                "POST",
                url,
                params={"media_category": media_category},
                files={"media": (path.name, handle.read())},
            )
        response.raise_for_status()
        return str(response.json()["media_id_string"])

    def _upload_video(self, path: Path) -> str:
        upload_url = f"{self._settings.x_upload_base_url.rstrip('/')}/1.1/media/upload.json"
        size = path.stat().st_size
        init = self._signed_request(
            "POST",
            upload_url,
            params={
                "command": "INIT",
                "total_bytes": str(size),
                "media_type": "video/mp4",
                "media_category": "tweet_video",
            },
        )
        init.raise_for_status()
        media_id = str(init.json()["media_id_string"])
        with path.open("rb") as handle:
            segment = 0
            while True:
                chunk = handle.read(CHUNK_SIZE)
                if not chunk:
                    break
                appended = self._signed_request(
                    "POST",
                    upload_url,
                    params={
                        "command": "APPEND",
                        "media_id": media_id,
                        "segment_index": str(segment),
                    },
                    files={"media": chunk},
                )
                appended.raise_for_status()
                segment += 1
        finalize = self._signed_request(
            "POST",
            upload_url,
            params={"command": "FINALIZE", "media_id": media_id},
        )
        finalize.raise_for_status()
        return media_id

    def _signed_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, object] | None = None,
        files: dict[str, object] | None = None,
    ) -> httpx.Response:
        request_url = url
        if params:
            query = "&".join(f"{key}={value}" for key, value in params.items())
            request_url = url + ("&" if "?" in url else "?") + query
        header = oauth1_authorization_header(
            method=method,
            url=request_url if json_body or files else request_url,
            consumer_key=self._settings.x_api_key or "",
            consumer_secret=self._settings.x_api_secret or "",
            token=self._settings.x_access_token or "",
            token_secret=self._settings.x_access_token_secret or "",
        )
        headers = {"Authorization": header}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            return self._http_client.request(
                method, request_url, headers=headers, content=json.dumps(json_body)
            )
        if files is not None:
            return self._http_client.request(
                method, request_url, headers=headers, files=files
            )
        return self._http_client.request(method, request_url, headers=headers)


class ApifyClient:
    """Run Apify website-content crawler when a token is configured."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client(timeout=90.0)

    def research_urls(self, urls: Sequence[str]) -> str | None:
        if not self._settings.apify_api_token or not urls:
            return None
        actor = os.environ.get("APIFY_ACTOR_ID", "apify~website-content-crawler")
        endpoint = (
            f"{self._settings.apify_api_base_url.rstrip('/')}/v2/acts/"
            f"{actor}/run-sync-get-dataset-items"
        )
        response = self._http_client.post(
            endpoint,
            params={"token": self._settings.apify_api_token},
            json={
                "startUrls": [{"url": url} for url in urls],
                "maxCrawlPages": 5,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return json.dumps(payload)
        snippets: list[str] = []
        for item in payload[:5]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or item.get("markdown") or item.get("url") or "")
            if text:
                snippets.append(text[:2000])
        return "\n\n".join(snippets) or None


class TikTokClient:
    """TikTok Content Posting API (inbox upload) when an access token is set."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client(timeout=120.0)

    def has_credentials(self) -> bool:
        return _has_tiktok_credentials(self._settings)

    def publish_video(self, *, media_paths: Sequence[str], caption: str) -> str | None:
        if not self.has_credentials():
            return None
        video_path = _first_video_path(media_paths)
        if video_path is None:
            return None
        size = video_path.stat().st_size
        headers = {
            "Authorization": f"Bearer {self._settings.tiktok_access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        init_url = (
            f"{self._settings.tiktok_api_base_url.rstrip('/')}"
            "/v2/post/publish/inbox/video/init/"
        )
        init = self._http_client.post(
            init_url,
            headers=headers,
            json={
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": size,
                    "total_chunk_count": 1,
                }
            },
        )
        init.raise_for_status()
        data = init.json().get("data") or {}
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")
        if not upload_url:
            raise ValueError("TikTok init did not return upload_url")
        with video_path.open("rb") as handle:
            uploaded = self._http_client.put(
                upload_url,
                content=handle.read(),
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(size),
                    "Content-Range": f"bytes 0-{size - 1}/{size}",
                },
            )
        uploaded.raise_for_status()
        _ = caption
        return str(publish_id) if publish_id else str(upload_url)


def _first_video_path(media_paths: Sequence[str]) -> Path | None:
    for raw in media_paths:
        path = Path(raw)
        if path.suffix.lower() in VIDEO_EXTENSIONS and path.is_file():
            return path
    return None


def _has_x_credentials(settings: Settings) -> bool:
    return all(
        (
            settings.x_api_key,
            settings.x_api_secret,
            settings.x_access_token,
            settings.x_access_token_secret,
        )
    )


def _has_tiktok_credentials(settings: Settings) -> bool:
    return all(
        (
            settings.tiktok_access_token,
            settings.tiktok_client_key,
            settings.tiktok_client_secret,
        )
    )
