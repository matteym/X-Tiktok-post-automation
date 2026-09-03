"""Tests for LangGraph Analyze, Strategy, and Generate nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent

RESEARCHED_STATE: dict[str, Any] = {
    "description": "Launch day recap for our new CLI workflow",
    "filenames": ["clip.mp4", "cover.jpg"],
    "media_fingerprints": ["deadbeef:1024", "cafebabe:2048"],
    "github_url": "https://github.com/example/repo",
    "twitter_url": "https://x.com/example",
    "tiktok_url": "https://www.tiktok.com/@creator/video/1",
    "youtube_url": "https://www.youtube.com/watch?v=research-hint",
    "media_count": 2,
    "media_types": ["video", "photo"],
    "understanding_summary": "Understood launch recap with two media files",
    "x_context": "Recent X timeline context",
    "web_research": "Apify scraped supporting context",
    "research_summary": "Research synthesized for launch recap",
}


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")

    from content_autopilot.settings import load_settings

    return load_settings()


@pytest.fixture
def mock_grok_client() -> MagicMock:
    client = MagicMock()
    client.generate.return_value = "Grok synthesized insight"
    return client


STRATEGY_GROK_RESPONSE = (
    "Angle: builder journey\n"
    "Tone: confident and practical\n"
    "Hashtags: #buildinpublic #devtools #automation"
)

GENERATE_GROK_RESPONSE = (
    "X post: Ship faster with our new CLI workflow.\n"
    "TikTok proposal: 30s demo script showing ordered media upload and publish.\n"
    "YouTube title: Launch recap for our CLI workflow\n"
    "YouTube description: Watch how ordered media upload and publish works in practice."
)


def test_content_autopilot_state_includes_generation_fields() -> None:
    from content_autopilot.graph.state import ContentAutopilotState

    annotations = ContentAutopilotState.__annotations__
    assert "analysis_insights" in annotations
    assert "strategy_angle" in annotations
    assert "strategy_tone" in annotations
    assert "strategy_hashtags" in annotations
    assert "x_post_text" in annotations
    assert "tiktok_proposal" in annotations
    assert "youtube_url" in annotations
    assert "youtube_title" in annotations
    assert "youtube_description" in annotations
    assert "youtube_video_url" in annotations


def test_analyze_node_synthesizes_research_into_insights(
    mock_grok_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import analyze_node

    mock_grok_client.generate.return_value = (
        "Key insight: developers want faster publishing workflows"
    )

    result = analyze_node(RESEARCHED_STATE, grok_client=mock_grok_client)

    assert result["analysis_insights"] == (
        "Key insight: developers want faster publishing workflows"
    )
    mock_grok_client.generate.assert_called_once()
    prompt = mock_grok_client.generate.call_args.args[0]
    assert RESEARCHED_STATE["research_summary"] in prompt


def test_strategy_node_produces_x_and_tiktok_strategy(
    mock_grok_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import strategy_node

    state = {
        **RESEARCHED_STATE,
        "analysis_insights": "Key insight: developers want faster publishing workflows",
    }

    mock_grok_client.generate.return_value = STRATEGY_GROK_RESPONSE

    result = strategy_node(state, grok_client=mock_grok_client)

    assert "builder journey" in result["strategy_angle"].lower()
    assert "confident" in result["strategy_tone"].lower()
    assert "#buildinpublic" in result["strategy_hashtags"]
    assert "#devtools" in result["strategy_hashtags"]
    mock_grok_client.generate.assert_called_once()
    prompt = mock_grok_client.generate.call_args.args[0]
    assert state["analysis_insights"] in prompt


def test_generate_node_drafts_x_post_and_tiktok_proposal(
    mock_grok_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import generate_node

    state = {
        **RESEARCHED_STATE,
        "analysis_insights": "Key insight: developers want faster publishing workflows",
        "strategy_angle": "builder journey",
        "strategy_tone": "confident and practical",
        "strategy_hashtags": ["#buildinpublic", "#devtools", "#automation"],
    }

    mock_grok_client.generate.return_value = GENERATE_GROK_RESPONSE

    result = generate_node(state, grok_client=mock_grok_client)

    assert "CLI workflow" in result["x_post_text"]
    assert "GitHub: https://github.com/example/repo" in result["x_post_text"]
    assert "YouTube: https://www.youtube.com/watch?v=research-hint" in result["x_post_text"]
    assert "TikTok: https://www.tiktok.com/@creator/video/1" in result["x_post_text"]
    assert "TikTok proposal" in result["tiktok_proposal"]
    assert "Launch recap" in result["youtube_title"]
    assert "ordered media upload" in result["youtube_description"]
    assert "GitHub: https://github.com/example/repo" in result["youtube_description"]
    assert "X: https://x.com/example" in result["youtube_description"]
    assert "TikTok: https://www.tiktok.com/@creator/video/1" in result["youtube_description"]
    mock_grok_client.generate.assert_called_once()
    prompt = mock_grok_client.generate.call_args.args[0]
    assert state["strategy_angle"] in prompt
    assert "#buildinpublic" in prompt
    assert RESEARCHED_STATE["youtube_url"] in prompt


def test_generate_node_uses_cli_title_as_youtube_title_default(
    mock_grok_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import generate_node

    state = {
        **RESEARCHED_STATE,
        "title": "CLI provided title",
        "analysis_insights": "Key insight: developers want faster publishing workflows",
        "strategy_angle": "builder journey",
        "strategy_tone": "confident and practical",
        "strategy_hashtags": ["#buildinpublic", "#devtools", "#automation"],
    }

    mock_grok_client.generate.return_value = GENERATE_GROK_RESPONSE

    result = generate_node(state, grok_client=mock_grok_client)

    assert result["youtube_title"] == "CLI provided title"
    prompt = mock_grok_client.generate.call_args.args[0]
    assert "CLI provided title" in prompt


def test_build_content_autopilot_graph_chains_research_to_generate(
    settings,
) -> None:
    from content_autopilot.graph.workflow import build_content_autopilot_graph

    graph = build_content_autopilot_graph(settings)
    node_names = set(graph.get_graph().nodes.keys())

    assert "research" in node_names
    assert "analyze" in node_names
    assert "strategy" in node_names
    assert "generate" in node_names


def test_graph_invoke_stores_analyze_strategy_generate_outputs(
    settings,
    mock_grok_client: MagicMock,
) -> None:
    from content_autopilot.graph.workflow import build_content_autopilot_graph

    mock_grok_client.generate.side_effect = [
        "Understood launch recap with two media files",
        "Research synthesized for launch recap",
        "Key insight: developers want faster publishing workflows",
        STRATEGY_GROK_RESPONSE,
        GENERATE_GROK_RESPONSE,
    ]

    graph = build_content_autopilot_graph(
        settings,
        grok_client=mock_grok_client,
        x_client=MagicMock(fetch_context=lambda: None),
        apify_client=MagicMock(research_urls=lambda urls: None),
    )

    initial_state = {
        "description": RESEARCHED_STATE["description"],
        "filenames": RESEARCHED_STATE["filenames"],
        "media_fingerprints": RESEARCHED_STATE["media_fingerprints"],
        "github_url": RESEARCHED_STATE["github_url"],
        "tiktok_url": RESEARCHED_STATE["tiktok_url"],
        "youtube_url": RESEARCHED_STATE["youtube_url"],
        "title": "Launch recap title",
    }

    result = graph.invoke(initial_state)

    assert result["research_summary"]
    assert result["analysis_insights"]
    assert result["strategy_angle"]
    assert result["strategy_tone"]
    assert result["strategy_hashtags"]
    assert result["x_post_text"]
    assert result["tiktok_proposal"]
    assert result["youtube_title"] == "Launch recap title"
    assert result["youtube_description"]
    assert mock_grok_client.generate.call_count >= 5
