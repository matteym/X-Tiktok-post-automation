"""LangGraph node implementations for understand and research phases."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from content_autopilot.graph.clients import (
    ApifyClient,
    GrokClient,
    XClient,
    _has_tiktok_credentials,
)
from content_autopilot.graph.state import ContentAutopilotState
from content_autopilot.settings import Settings

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MAX_X_POST_LENGTH = 280


class GrokClientProtocol(Protocol):
    def generate(self, prompt: str) -> str: ...


class XClientProtocol(Protocol):
    def fetch_context(self) -> str | None: ...

    def has_credentials(self) -> bool: ...

    def publish_post(self, *, media_paths: list[str], text: str) -> str: ...


class ApifyClientProtocol(Protocol):
    def research_urls(self, urls: list[str]) -> str | None: ...


def infer_media_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in PHOTO_EXTENSIONS:
        return "photo"
    return "media"


def understand_node(
    state: ContentAutopilotState,
    *,
    grok_client: GrokClientProtocol,
) -> ContentAutopilotState:
    """Interpret the post description, media set, and optional URL hints."""
    filenames = state.get("filenames", [])
    media_count = len(filenames)
    media_types = [infer_media_type(name) for name in filenames]
    description = state.get("description", "")
    github_url = state.get("github_url")
    tiktok_url = state.get("tiktok_url")

    prompt_parts = [
        "Understand this content-autopilot post request.",
        f"Description: {description}",
        f"Media count: {media_count}",
        f"Media types: {', '.join(media_types)}",
    ]
    if github_url:
        prompt_parts.append(f"GitHub hint: {github_url}")
    if tiktok_url:
        prompt_parts.append(f"TikTok hint: {tiktok_url}")

    grok_summary = grok_client.generate("\n".join(prompt_parts))
    summary_parts = [
        grok_summary,
        f"Description: {description}",
    ]
    if github_url:
        summary_parts.append(f"GitHub hint: {github_url}")
    if tiktok_url:
        summary_parts.append(f"TikTok hint: {tiktok_url}")

    return {
        "media_count": media_count,
        "media_types": media_types,
        "understanding_summary": "\n".join(summary_parts),
    }


def research_node(
    state: ContentAutopilotState,
    *,
    settings: Settings,
    grok_client: GrokClientProtocol,
    x_client: XClientProtocol,
    apify_client: ApifyClientProtocol,
) -> ContentAutopilotState:
    """Gather X context and optional Apify web research for the post."""
    x_context = x_client.fetch_context()

    research_urls: list[str] = []
    github_url = state.get("github_url")
    tiktok_url = state.get("tiktok_url")
    if github_url:
        research_urls.append(github_url)
    if tiktok_url:
        research_urls.append(tiktok_url)

    web_research: str | None = None
    if settings.apify_api_token and research_urls:
        web_research = apify_client.research_urls(research_urls)

    prompt_parts = [
        "Research supporting context for this content-autopilot post.",
        f"Understanding: {state.get('understanding_summary', '')}",
    ]
    if x_context:
        prompt_parts.append(f"X context: {x_context}")
    if web_research:
        prompt_parts.append(f"Web research: {web_research}")

    research_summary = grok_client.generate("\n".join(prompt_parts))

    return {
        "x_context": x_context,
        "web_research": web_research,
        "research_summary": research_summary,
    }


def _parse_strategy_response(text: str) -> tuple[str, str, list[str]]:
    angle = ""
    tone = ""
    hashtags: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if lowered.startswith("angle:"):
            angle = line.split(":", 1)[1].strip()
        elif lowered.startswith("tone:"):
            tone = line.split(":", 1)[1].strip()
        elif lowered.startswith("hashtags:"):
            hashtags = line.split(":", 1)[1].strip().split()
    return angle, tone, hashtags


def _parse_generate_response(text: str) -> tuple[str, str]:
    x_post_text = text.strip()
    tiktok_proposal = text.strip()
    for line in text.splitlines():
        lowered = line.lower()
        if lowered.startswith("x post:"):
            x_post_text = line.strip()
        elif lowered.startswith("tiktok proposal:"):
            tiktok_proposal = line.strip()
    return x_post_text, tiktok_proposal


def analyze_node(
    state: ContentAutopilotState,
    *,
    grok_client: GrokClientProtocol,
) -> ContentAutopilotState:
    """Synthesize research outputs into actionable insights."""
    prompt = "\n".join(
        [
            "Analyze this content-autopilot research and extract key insights.",
            f"Understanding: {state.get('understanding_summary', '')}",
            f"Research summary: {state.get('research_summary', '')}",
            f"X context: {state.get('x_context') or 'none'}",
            f"Web research: {state.get('web_research') or 'none'}",
        ]
    )
    analysis_insights = grok_client.generate(prompt)
    return {"analysis_insights": analysis_insights}


def strategy_node(
    state: ContentAutopilotState,
    *,
    grok_client: GrokClientProtocol,
) -> ContentAutopilotState:
    """Define the X and TikTok angle, tone, and hashtags."""
    prompt = "\n".join(
        [
            "Create a cross-platform content strategy for X and TikTok.",
            f"Description: {state.get('description', '')}",
            f"Analysis insights: {state.get('analysis_insights', '')}",
            "Return Angle, Tone, and Hashtags on separate lines.",
        ]
    )
    strategy_text = grok_client.generate(prompt)
    angle, tone, hashtags = _parse_strategy_response(strategy_text)
    return {
        "strategy_angle": angle,
        "strategy_tone": tone,
        "strategy_hashtags": hashtags,
    }


def generate_node(
    state: ContentAutopilotState,
    *,
    grok_client: GrokClientProtocol,
) -> ContentAutopilotState:
    """Draft the X post text and TikTok proposal caption/script."""
    hashtags = state.get("strategy_hashtags", [])
    prompt = "\n".join(
        [
            "Generate draft content for X and TikTok.",
            f"Description: {state.get('description', '')}",
            f"Strategy angle: {state.get('strategy_angle', '')}",
            f"Strategy tone: {state.get('strategy_tone', '')}",
            f"Strategy hashtags: {' '.join(hashtags)}",
            "Return X post and TikTok proposal on separate lines.",
        ]
    )
    generated = grok_client.generate(prompt)
    x_post_text, tiktok_proposal = _parse_generate_response(generated)
    return {
        "x_post_text": x_post_text,
        "tiktok_proposal": tiktok_proposal,
    }


def _resolved_media_paths(state: ContentAutopilotState) -> list[str]:
    media_paths = state.get("media_paths")
    if media_paths:
        return list(media_paths)
    return [str(path) for path in state.get("filenames", [])]


def validate_node(state: ContentAutopilotState) -> ContentAutopilotState:
    """Validate generated content length, policy, and media count."""
    errors: list[str] = []
    media_paths = _resolved_media_paths(state)
    media_count = state.get("media_count", len(state.get("filenames", [])))

    x_post_text = state.get("x_post_text", "").strip()
    if not x_post_text:
        errors.append("Policy violation: X post text is empty")
    elif len(x_post_text) > MAX_X_POST_LENGTH:
        errors.append(
            f"Length violation: X post exceeds {MAX_X_POST_LENGTH} characters"
        )

    if len(media_paths) != media_count:
        errors.append(
            "Media count mismatch between media_paths and media_count"
        )

    return {
        "media_paths": media_paths,
        "validation_passed": not errors,
        "validation_errors": errors,
    }


def publish_x_node(
    state: ContentAutopilotState,
    *,
    settings: Settings,
    x_client: XClientProtocol,
) -> ContentAutopilotState:
    """Publish to X with media uploaded in preserved CLI order."""
    _ = settings
    media_paths = _resolved_media_paths(state)
    result: ContentAutopilotState = {"media_paths": media_paths}

    if not x_client.has_credentials():
        result["x_post_url"] = None
        return result

    result["x_post_url"] = x_client.publish_post(
        media_paths=media_paths,
        text=state.get("x_post_text", ""),
    )
    return result


def tiktok_proposal_node(
    state: ContentAutopilotState,
    *,
    settings: Settings,
    apify_client: ApifyClientProtocol | None = None,
) -> ContentAutopilotState:
    """Build a structured TikTok proposal without live publish unless configured."""
    _ = apify_client
    media_paths = _resolved_media_paths(state)
    caption = state.get("tiktok_proposal", "") or state.get("description", "")
    hashtags = state.get("strategy_hashtags", [])

    publish_mode = "proposal"
    if _has_tiktok_credentials(settings):
        publish_mode = "live" if settings.tiktok_access_token else "proposal"

    structured: dict[str, str | list[str]] = {
        "publish_mode": publish_mode,
        "caption": caption,
        "hashtags": hashtags,
        "media_order": media_paths,
    }

    return {
        "media_paths": media_paths,
        "tiktok_proposal_structured": structured,
    }
