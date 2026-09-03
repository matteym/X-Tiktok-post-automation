"""Orchestrate CLI runs with dedup checks, LangGraph, and persistence."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import typer

from content_autopilot.db.models import PostRun
from content_autopilot.db.repository import PostRunRepository
from content_autopilot.graph.workflow import build_content_autopilot_graph
from content_autopilot.media.run_inputs import collect_run_media
from content_autopilot.settings import Settings, load_settings

DUPLICATE_WARNING = "Warning: This media set was already posted"

PIPELINE_STEPS = (
    "Understand",
    "Research",
    "Analyze",
    "Strategy",
    "Generate",
    "Validate",
    "Publish",
    "TikTok",
)


def default_confirm(message: str) -> bool:
    """Prompt for confirmation; default is no."""
    response = typer.prompt(f"{message} [y/N]", default="n")
    return response.strip().lower() in {"y", "yes"}


def _format_duplicate_warning(existing: PostRun) -> str:
    return "\n".join(
        (
            DUPLICATE_WARNING,
            f"description: {existing.description}",
            f"x_post_url: {existing.x_post_url or 'none'}",
            f"created_at: {existing.created_at.isoformat()}",
        )
    )


def _format_tiktok_summary(structured: dict[str, Any]) -> str:
    caption = structured.get("caption", "")
    hashtags = structured.get("hashtags", [])
    publish_mode = structured.get("publish_mode", "proposal")
    hashtag_text = " ".join(hashtags) if hashtags else "none"
    return (
        f"TikTok proposal ({publish_mode}): {caption} "
        f"Hashtags: {hashtag_text}"
    )


def execute_run(
    video_paths: Sequence[Path | str],
    description: str,
    *,
    github_url: str | None = None,
    tiktok_url: str | None = None,
    settings: Settings | None = None,
    repository: PostRunRepository | None = None,
    graph: Any | None = None,
    confirm: Callable[[str], bool] | None = None,
    echo: Callable[[str], None] | None = None,
) -> int:
    """Run dedup checks, LangGraph pipeline, and metadata persistence."""
    write = echo or typer.echo
    ask_confirm = confirm or default_confirm

    try:
        collected = collect_run_media(
            video_paths=video_paths,
            description=description,
            github_url=github_url,
            tiktok_url=tiktok_url,
        )
    except FileNotFoundError as exc:
        write(str(exc))
        return 1

    write(f"description: {collected.description}")
    write(f"media_fingerprints: {','.join(collected.media_fingerprints)}")
    write(f"media_set_hash: {collected.media_set_hash}")

    active_settings = settings or load_settings()
    repo = repository or PostRunRepository.from_settings(active_settings)

    existing = repo.find_existing_by_media_set(
        collected.media_set_hash,
        media_fingerprints=collected.media_fingerprints,
    )
    if existing is not None:
        write(_format_duplicate_warning(existing))
        if not ask_confirm("Proceed with posting this media set again?"):
            write("Aborted.")
            return 0

    compiled_graph = graph or build_content_autopilot_graph(active_settings)
    initial_state = {
        "description": collected.description,
        "filenames": collected.filenames,
        "media_paths": [str(path) for path in collected.video_paths],
        "media_fingerprints": collected.media_fingerprints,
        "github_url": collected.github_url,
        "tiktok_url": collected.tiktok_url,
    }

    write("Starting content-autopilot pipeline...")
    for step in PIPELINE_STEPS:
        write(f"-> {step}")

    result = compiled_graph.invoke(initial_state)

    if result.get("validation_passed") is False:
        errors = result.get("validation_errors") or []
        write("Validation failed: " + "; ".join(errors))
        return 1

    x_post_url = result.get("x_post_url")
    write(f"X post URL: {x_post_url or 'none'}")
    structured = result.get("tiktok_proposal_structured") or {}
    write(_format_tiktok_summary(structured))

    tiktok_proposal_value: str | None
    if structured:
        tiktok_proposal_value = json.dumps(structured)
    else:
        tiktok_proposal_value = result.get("tiktok_proposal")

    repo.save_post_metadata(
        media_set_hash=collected.media_set_hash,
        media_fingerprints=collected.media_fingerprints,
        filenames=collected.filenames,
        description=collected.description,
        github_url=collected.github_url,
        tiktok_url=collected.tiktok_url,
        x_post_url=x_post_url,
        tiktok_proposal=tiktok_proposal_value,
    )

    return 0
