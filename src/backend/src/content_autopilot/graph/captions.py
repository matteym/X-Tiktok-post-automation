"""Append CLI account and repo links to generated captions."""

from __future__ import annotations

MAX_X_POST_LENGTH = 280


def labeled_link_lines(pairs: list[tuple[str, str | None]]) -> list[str]:
    """Build ``Label: url`` lines, skipping empty values."""
    return [
        f"{label}: {value.strip()}"
        for label, value in pairs
        if value and value.strip()
    ]


def append_link_block(
    body: str,
    lines: list[str],
    *,
    max_length: int | None = None,
) -> str:
    """Append labeled links after ``body``, truncating the body when capped."""
    body = (body or "").strip()
    if not lines:
        return body
    footer = "\n".join(lines)
    if max_length is None:
        if not body:
            return footer
        return f"{body}\n\n{footer}"

    separator = "\n\n"
    reserved = len(separator) + len(footer)
    if reserved >= max_length:
        return footer[:max_length]
    truncated = body[: max_length - reserved].rstrip()
    if not truncated:
        return footer[:max_length]
    return f"{truncated}{separator}{footer}"


def youtube_caption(
    body: str,
    *,
    github_url: str | None,
    twitter_url: str | None,
    tiktok_url: str | None,
) -> str:
    """YouTube description: generated text plus GitHub, X, and TikTok links."""
    return append_link_block(
        body,
        labeled_link_lines(
            [
                ("GitHub", github_url),
                ("X", twitter_url),
                ("TikTok", tiktok_url),
            ]
        ),
    )


def x_post_caption(
    body: str,
    *,
    github_url: str | None,
    youtube_url: str | None,
    tiktok_url: str | None,
) -> str:
    """X post text: generated text plus GitHub, YouTube, and TikTok links."""
    return append_link_block(
        body,
        labeled_link_lines(
            [
                ("GitHub", github_url),
                ("YouTube", youtube_url),
                ("TikTok", tiktok_url),
            ]
        ),
        max_length=MAX_X_POST_LENGTH,
    )


def tiktok_caption(
    body: str,
    *,
    github_url: str | None,
    twitter_url: str | None,
    youtube_url: str | None,
) -> str:
    """TikTok caption: generated text plus GitHub, X, and YouTube links."""
    return append_link_block(
        body,
        labeled_link_lines(
            [
                ("GitHub", github_url),
                ("X", twitter_url),
                ("YouTube", youtube_url),
            ]
        ),
    )
