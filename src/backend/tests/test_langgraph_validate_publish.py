"""Tests for LangGraph Validate, Publish X, and TikTok Proposal nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent

GENERATED_STATE: dict[str, Any] = {
    "description": "Launch day recap for our new CLI workflow",
    "filenames": ["clip.mp4", "cover.jpg"],
    "media_paths": ["/data/clip.mp4", "/data/cover.jpg"],
    "media_fingerprints": ["deadbeef:1024", "cafebabe:2048"],
    "github_url": "https://github.com/example/repo",
    "tiktok_url": "https://www.tiktok.com/@creator/video/1",
    "media_count": 2,
    "media_types": ["video", "photo"],
    "understanding_summary": "Understood launch recap with two media files",
    "x_context": "Recent X timeline context",
    "web_research": "Apify scraped supporting context",
    "research_summary": "Research synthesized for launch recap",
    "analysis_insights": "Key insight: developers want faster publishing workflows",
    "strategy_angle": "builder journey",
    "strategy_tone": "confident and practical",
    "strategy_hashtags": ["#buildinpublic", "#devtools", "#automation"],
    "x_post_text": "Ship faster with our new CLI workflow.",
    "tiktok_proposal": "30s demo script showing ordered media upload and publish.",
}


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.setenv("X_API_KEY", "x-key")
    monkeypatch.setenv("X_API_SECRET", "x-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "x-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "x-token-secret")

    from content_autopilot.settings import load_settings

    return load_settings()


@pytest.fixture
def settings_without_x_credentials(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.delenv("X_API_KEY", raising=False)
    monkeypatch.delenv("X_API_SECRET", raising=False)
    monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

    from content_autopilot.settings import load_settings

    return load_settings()


@pytest.fixture
def mock_grok_client() -> MagicMock:
    client = MagicMock()
    client.generate.return_value = "Grok synthesized insight"
    return client


@pytest.fixture
def mock_x_publish_client() -> MagicMock:
    client = MagicMock()
    client.has_credentials.return_value = True
    client.publish_post.return_value = "https://x.com/example/status/123456789"
    return client


@pytest.fixture
def mock_apify_client() -> MagicMock:
    client = MagicMock()
    client.research_urls.return_value = "Apify scraped supporting context"
    return client


def test_content_autopilot_state_includes_validate_and_publish_fields() -> None:
    from content_autopilot.graph.state import ContentAutopilotState

    annotations = ContentAutopilotState.__annotations__
    assert "media_paths" in annotations
    assert "validation_passed" in annotations
    assert "validation_errors" in annotations
    assert "x_post_url" in annotations
    assert "tiktok_proposal_structured" in annotations


def test_validate_node_passes_valid_generated_content() -> None:
    import content_autopilot.graph.nodes as graph_nodes

    assert hasattr(graph_nodes, "validate_node")
    validate_node = graph_nodes.validate_node

    result = validate_node(GENERATED_STATE)

    assert result["validation_passed"] is True
    assert result["validation_errors"] == []


def test_validate_node_rejects_oversized_x_post_text() -> None:
    import content_autopilot.graph.nodes as graph_nodes

    validate_node = graph_nodes.validate_node
    oversized_state = {
        **GENERATED_STATE,
        "x_post_text": "x" * 281,
    }

    result = validate_node(oversized_state)

    assert result["validation_passed"] is False
    assert any("length" in error.lower() for error in result["validation_errors"])


def test_validate_node_rejects_empty_x_post_text() -> None:
    import content_autopilot.graph.nodes as graph_nodes

    validate_node = graph_nodes.validate_node
    empty_state = {
        **GENERATED_STATE,
        "x_post_text": "   ",
    }

    result = validate_node(empty_state)

    assert result["validation_passed"] is False
    assert any("policy" in error.lower() for error in result["validation_errors"])


def test_validate_node_rejects_media_count_mismatch() -> None:
    import content_autopilot.graph.nodes as graph_nodes

    validate_node = graph_nodes.validate_node
    mismatched_state = {
        **GENERATED_STATE,
        "media_count": 3,
    }

    result = validate_node(mismatched_state)

    assert result["validation_passed"] is False
    assert any("media" in error.lower() for error in result["validation_errors"])


def test_publish_x_node_uploads_media_in_preserved_order(
    settings,
    mock_x_publish_client: MagicMock,
) -> None:
    import content_autopilot.graph.nodes as graph_nodes

    publish_x_node = graph_nodes.publish_x_node
    validated_state = {
        **GENERATED_STATE,
        "validation_passed": True,
        "validation_errors": [],
    }

    result = publish_x_node(
        validated_state,
        settings=settings,
        x_client=mock_x_publish_client,
    )

    mock_x_publish_client.publish_post.assert_called_once()
    call_kwargs = mock_x_publish_client.publish_post.call_args.kwargs
    assert call_kwargs["media_paths"] == GENERATED_STATE["media_paths"]
    assert call_kwargs["text"] == GENERATED_STATE["x_post_text"]
    assert result["x_post_url"] == "https://x.com/example/status/123456789"


def test_publish_x_node_skips_live_publish_without_credentials(
    settings_without_x_credentials,
) -> None:
    import content_autopilot.graph.nodes as graph_nodes
    from content_autopilot.graph.clients import XClient

    publish_x_node = graph_nodes.publish_x_node
    validated_state = {
        **GENERATED_STATE,
        "validation_passed": True,
        "validation_errors": [],
    }
    x_client = XClient(settings_without_x_credentials)

    result = publish_x_node(
        validated_state,
        settings=settings_without_x_credentials,
        x_client=x_client,
    )

    assert result["x_post_url"] is None


def test_tiktok_proposal_node_returns_structured_proposal_without_live_publish(
    settings_without_x_credentials,
) -> None:
    import content_autopilot.graph.nodes as graph_nodes

    tiktok_proposal_node = graph_nodes.tiktok_proposal_node
    published_state = {
        **GENERATED_STATE,
        "validation_passed": True,
        "validation_errors": [],
        "x_post_url": None,
    }

    result = tiktok_proposal_node(
        published_state,
        settings=settings_without_x_credentials,
    )

    structured = result["tiktok_proposal_structured"]
    assert isinstance(structured, dict)
    assert structured.get("publish_mode") == "proposal"
    assert structured.get("caption")
    assert structured.get("media_order") == GENERATED_STATE["media_paths"]
    assert "hashtags" in structured


def test_tiktok_proposal_node_uses_apify_mock_when_configured(
    settings,
    mock_apify_client: MagicMock,
) -> None:
    import content_autopilot.graph.nodes as graph_nodes

    tiktok_proposal_node = graph_nodes.tiktok_proposal_node
    published_state = {
        **GENERATED_STATE,
        "validation_passed": True,
        "validation_errors": [],
        "x_post_url": "https://x.com/example/status/123456789",
    }

    result = tiktok_proposal_node(
        published_state,
        settings=settings,
        apify_client=mock_apify_client,
    )

    structured = result["tiktok_proposal_structured"]
    assert structured["publish_mode"] == "proposal"
    assert structured["media_order"] == GENERATED_STATE["media_paths"]
    mock_apify_client.research_urls.assert_not_called()


def test_publish_x_node_skips_when_validation_failed(
    settings,
    mock_x_publish_client: MagicMock,
) -> None:
    import content_autopilot.graph.nodes as graph_nodes

    result = graph_nodes.publish_x_node(
        {
            **GENERATED_STATE,
            "validation_passed": False,
            "validation_errors": ["Length violation: X post exceeds 280 characters"],
        },
        settings=settings,
        x_client=mock_x_publish_client,
    )

    mock_x_publish_client.publish_post.assert_not_called()
    assert result["x_post_url"] is None


def test_route_after_validate_skips_publish_on_failure() -> None:
    from content_autopilot.graph.workflow import route_after_validate

    assert route_after_validate({"validation_passed": True}) == "publish_x"
    assert route_after_validate({"validation_passed": False}) == "tiktok_proposal"


def test_build_content_autopilot_graph_wires_generate_through_publish(settings) -> None:
    from content_autopilot.graph.workflow import build_content_autopilot_graph

    graph = build_content_autopilot_graph(settings)
    compiled = graph.get_graph()
    node_names = set(compiled.nodes.keys())
    edges = {(edge.source, edge.target) for edge in compiled.edges}

    assert "validate" in node_names
    assert "publish_x" in node_names
    assert "tiktok_proposal" in node_names
    assert ("generate", "validate") in edges
    assert ("validate", "publish_x") in edges or any(
        edge.source == "validate" and edge.target == "publish_x" for edge in compiled.edges
    )
    assert ("publish_x", "tiktok_proposal") in edges
    assert ("tiktok_proposal", "__end__") in edges
    assert ("generate", "__end__") not in edges


def test_graph_invoke_preserves_media_paths_through_publish_flow(
    settings,
    mock_grok_client: MagicMock,
    mock_x_publish_client: MagicMock,
) -> None:
    from content_autopilot.graph.workflow import build_content_autopilot_graph

    mock_grok_client.generate.side_effect = [
        "Understood launch recap with two media files",
        "Research synthesized for launch recap",
        "Key insight: developers want faster publishing workflows",
        (
            "Angle: builder journey\n"
            "Tone: confident and practical\n"
            "Hashtags: #buildinpublic #devtools #automation"
        ),
        (
            "X post: Ship faster with our new CLI workflow.\n"
            "TikTok proposal: 30s demo script showing ordered media upload and publish."
        ),
    ]

    graph = build_content_autopilot_graph(
        settings,
        grok_client=mock_grok_client,
        x_client=mock_x_publish_client,
        apify_client=MagicMock(research_urls=lambda urls: None),
    )

    initial_state = {
        "description": GENERATED_STATE["description"],
        "filenames": GENERATED_STATE["filenames"],
        "media_paths": GENERATED_STATE["media_paths"],
        "media_fingerprints": GENERATED_STATE["media_fingerprints"],
        "github_url": GENERATED_STATE["github_url"],
        "tiktok_url": GENERATED_STATE["tiktok_url"],
    }

    result = graph.invoke(initial_state)

    assert result["media_paths"] == GENERATED_STATE["media_paths"]
    assert result["validation_passed"] is True
    assert result["x_post_url"] == "https://x.com/example/status/123456789"
    assert result["tiktok_proposal_structured"]["media_order"] == GENERATED_STATE["media_paths"]
    mock_x_publish_client.publish_post.assert_called_once()
