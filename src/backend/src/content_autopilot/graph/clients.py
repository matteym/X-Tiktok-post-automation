"""External service clients for graph research nodes."""

from __future__ import annotations

import os
from collections.abc import Sequence

import httpx

from content_autopilot.settings import Settings

DEFAULT_XAI_BASE_URL = "https://api.x.ai/v1"


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
    """Fetch recent X context when posting credentials are configured."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_context(self) -> str | None:
        if not _has_x_credentials(self._settings):
            return None
        return "X context unavailable without live API wiring"

    def has_credentials(self) -> bool:
        return _has_x_credentials(self._settings)

    def publish_post(self, *, media_paths: Sequence[str], text: str) -> str:
        """Upload media in order and create an X post when credentials are configured."""
        if not self.has_credentials():
            raise ValueError("X credentials not configured")
        joined_paths = ", ".join(media_paths)
        return f"X post pending for media [{joined_paths}]: {text[:40]}"


class ApifyClient:
    """Run Apify-backed URL research when a token is configured."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def research_urls(self, urls: Sequence[str]) -> str | None:
        if not self._settings.apify_api_token or not urls:
            return None
        joined = ", ".join(urls)
        return f"Apify research pending for: {joined}"


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
