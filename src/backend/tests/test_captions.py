"""Tests for deterministic CLI link footers on generated captions."""

from __future__ import annotations

from content_autopilot.graph.captions import (
    MAX_X_POST_LENGTH,
    x_post_caption,
    youtube_caption,
)


def test_youtube_caption_appends_github_twitter_and_tiktok() -> None:
    caption = youtube_caption(
        "Watch the launch recap.",
        github_url="https://github.com/example/repo",
        twitter_url="https://x.com/example",
        tiktok_url="https://www.tiktok.com/@creator",
    )

    assert caption.startswith("Watch the launch recap.")
    assert "GitHub: https://github.com/example/repo" in caption
    assert "X: https://x.com/example" in caption
    assert "TikTok: https://www.tiktok.com/@creator" in caption


def test_x_post_caption_appends_github_youtube_and_tiktok() -> None:
    caption = x_post_caption(
        "Ship the CLI today.",
        github_url="https://github.com/example/repo",
        youtube_url="https://www.youtube.com/@example",
        tiktok_url="https://www.tiktok.com/@creator",
    )

    assert caption.startswith("Ship the CLI today.")
    assert "GitHub: https://github.com/example/repo" in caption
    assert "YouTube: https://www.youtube.com/@example" in caption
    assert "TikTok: https://www.tiktok.com/@creator" in caption
    assert len(caption) <= MAX_X_POST_LENGTH


def test_x_post_caption_truncates_body_to_keep_links_under_limit() -> None:
    caption = x_post_caption(
        "x" * 400,
        github_url="https://github.com/example/repo",
        youtube_url="https://www.youtube.com/@example",
        tiktok_url="https://www.tiktok.com/@creator",
    )

    assert "GitHub: https://github.com/example/repo" in caption
    assert "YouTube: https://www.youtube.com/@example" in caption
    assert "TikTok: https://www.tiktok.com/@creator" in caption
    assert len(caption) <= MAX_X_POST_LENGTH


def test_captions_skip_missing_urls() -> None:
    youtube = youtube_caption(
        "Body",
        github_url="https://github.com/example/repo",
        twitter_url=None,
        tiktok_url=None,
    )
    x_post = x_post_caption(
        "Body",
        github_url=None,
        youtube_url="https://www.youtube.com/@example",
        tiktok_url=None,
    )

    assert youtube == "Body\n\nGitHub: https://github.com/example/repo"
    assert "X:" not in youtube
    assert x_post == "Body\n\nYouTube: https://www.youtube.com/@example"
    assert "GitHub:" not in x_post
