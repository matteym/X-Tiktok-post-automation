"""LangGraph node implementations for understand and research phases."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from content_autopilot.graph.clients import ApifyClient, GrokClient, XClient
from content_autopilot.graph.state import ContentAutopilotState
from content_autopilot.settings import Settings

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


class GrokClientProtocol(Protocol):
    def generate(self, prompt: str) -> str: ...


class XClientProtocol(Protocol):
    def fetch_context(self) -> str | None: ...


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
