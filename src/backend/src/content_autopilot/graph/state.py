"""Typed LangGraph state for content-autopilot."""

from __future__ import annotations

from typing import TypedDict


class ContentAutopilotState(TypedDict, total=False):
    """Shared graph state for content generation and publishing."""

    description: str
    filenames: list[str]
    media_paths: list[str]
    media_fingerprints: list[str]
    github_url: str | None
    tiktok_url: str | None
    media_count: int
    media_types: list[str]
    understanding_summary: str
    x_context: str | None
    web_research: str | None
    research_summary: str
    analysis_insights: str
    strategy_angle: str
    strategy_tone: str
    strategy_hashtags: list[str]
    x_post_text: str
    tiktok_proposal: str
    validation_passed: bool
    validation_errors: list[str]
    x_post_url: str | None
    tiktok_proposal_structured: dict[str, str | list[str]]
