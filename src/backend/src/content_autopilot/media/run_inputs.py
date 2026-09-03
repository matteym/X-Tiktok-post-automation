"""Parse and validate CLI media inputs for content-autopilot runs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from content_autopilot.media.fingerprint import fingerprint_media_paths, media_set_hash

TITLE_MAX_LENGTH = 100


@dataclass(frozen=True)
class RunMediaInputs:
    """Validated media inputs collected from CLI flags."""

    video_paths: list[Path]
    filenames: list[str]
    description: str
    title: str
    github_url: str | None
    twitter_url: str | None
    tiktok_url: str | None
    youtube_url: str | None
    media_fingerprints: list[str]
    media_set_hash: str


def derive_title(description: str, title: str | None = None) -> str:
    """Use an explicit title or derive one from a truncated description."""
    if title is not None:
        return title
    return description[:TITLE_MAX_LENGTH]


def _validate_readable_media_path(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")

    with path.open("rb") as media_file:
        media_file.read(1)


def collect_run_media(
    video_paths: Sequence[Path | str],
    description: str,
    github_url: str | None = None,
    twitter_url: str | None = None,
    tiktok_url: str | None = None,
    title: str | None = None,
    youtube_url: str | None = None,
) -> RunMediaInputs:
    """Validate media paths and compute ordered fingerprints for a run."""
    if not video_paths:
        raise ValueError("At least one video path is required")

    paths = [Path(path) for path in video_paths]
    for path in paths:
        _validate_readable_media_path(path)

    fingerprints = fingerprint_media_paths(paths)

    return RunMediaInputs(
        video_paths=paths,
        filenames=[path.name for path in paths],
        description=description,
        title=derive_title(description, title=title),
        github_url=github_url,
        twitter_url=twitter_url,
        tiktok_url=tiktok_url,
        youtube_url=youtube_url,
        media_fingerprints=fingerprints,
        media_set_hash=media_set_hash(fingerprints),
    )
