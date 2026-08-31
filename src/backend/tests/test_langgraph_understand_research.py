"""Tests for LangGraph Understand and Research nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PACKAGE = BACKEND_ROOT / "src" / "content_autopilot" / "graph"

SAMPLE_STATE: dict[str, Any] = {
    "description": "Launch day recap for our new CLI workflow",
    "filenames": ["clip.mp4", "cover.jpg"],
    "media_fingerprints": ["deadbeef:1024", "cafebabe:2048"],
    "github_url": "https://github.com/example/repo",
    "tiktok_url": "https://www.tiktok.com/@creator/video/1",
}


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.setenv("X_API_KEY", "x-key")
    monkeypatch.setenv("X_API_SECRET", "x-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "x-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "x-token-secret")
    monkeypatch.setenv("APIFY_API_TOKEN", "apify-token")

    from content_autopilot.settings import load_settings

    return load_settings()


@pytest.fixture
def mock_grok_client() -> MagicMock:
    client = MagicMock()
    client.generate.return_value = "Grok synthesized insight"
    return client


@pytest.fixture
def mock_x_client() -> MagicMock:
    client = MagicMock()
    client.fetch_context.return_value = "Recent X timeline context"
    return client


@pytest.fixture
def mock_apify_client() -> MagicMock:
    client = MagicMock()
    client.research_urls.return_value = "Apify scraped supporting context"
    return client


def test_graph_package_modules_exist() -> None:
    assert (GRAPH_PACKAGE / "__init__.py").is_file()
    assert (GRAPH_PACKAGE / "state.py").is_file()
    assert (GRAPH_PACKAGE / "nodes.py").is_file()
    assert (GRAPH_PACKAGE / "workflow.py").is_file()


def test_graph_source_has_no_hardcoded_localhost() -> None:
    for filename in ("state.py", "nodes.py", "workflow.py"):
        source = (GRAPH_PACKAGE / filename).read_text(encoding="utf-8").lower()
        assert "localhost" not in source, filename
        assert "127.0.0.1" not in source, filename


def test_content_autopilot_state_is_typed_dict() -> None:
    from typing import TypedDict

    from content_autopilot.graph.state import ContentAutopilotState

    assert issubclass(ContentAutopilotState, dict) or hasattr(
        ContentAutopilotState, "__annotations__"
    )
    annotations = getattr(ContentAutopilotState, "__annotations__", {})
    assert "description" in annotations
    assert "understanding_summary" in annotations
    assert "research_summary" in annotations


def test_build_understand_research_graph_wires_start_understand_research(
    settings,
) -> None:
    from langgraph.graph import START

    from content_autopilot.graph.workflow import build_understand_research_graph

    graph = build_understand_research_graph(settings)
    node_names = set(graph.get_graph().nodes.keys())

    assert START in node_names or "__start__" in node_names
    assert "understand" in node_names
    assert "research" in node_names


def test_understand_node_interprets_description_media_count_and_types(
    mock_grok_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import understand_node

    result = understand_node(
        SAMPLE_STATE,
        grok_client=mock_grok_client,
    )

    assert result["media_count"] == 2
    assert result["media_types"] == ["video", "photo"]
    assert "Launch day recap" in result["understanding_summary"]
    mock_grok_client.generate.assert_called_once()


def test_understand_node_includes_optional_url_hints(
    mock_grok_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import understand_node

    result = understand_node(SAMPLE_STATE, grok_client=mock_grok_client)

    assert "github.com/example/repo" in result["understanding_summary"]
    assert "tiktok.com/@creator/video/1" in result["understanding_summary"]


def test_research_node_gathers_x_context_when_credentials_available(
    settings,
    mock_grok_client: MagicMock,
    mock_x_client: MagicMock,
    mock_apify_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import research_node

    state = {
        **SAMPLE_STATE,
        "understanding_summary": "Understood launch recap with two media files",
        "media_count": 2,
        "media_types": ["video", "photo"],
    }

    result = research_node(
        state,
        settings=settings,
        grok_client=mock_grok_client,
        x_client=mock_x_client,
        apify_client=mock_apify_client,
    )

    assert result["x_context"] == "Recent X timeline context"
    mock_x_client.fetch_context.assert_called_once()
    mock_grok_client.generate.assert_called_once()


def test_research_node_uses_apify_when_token_and_urls_available(
    settings,
    mock_grok_client: MagicMock,
    mock_x_client: MagicMock,
    mock_apify_client: MagicMock,
) -> None:
    from content_autopilot.graph.nodes import research_node

    state = {
        **SAMPLE_STATE,
        "understanding_summary": "Understood launch recap with two media files",
        "media_count": 2,
        "media_types": ["video", "photo"],
    }

    result = research_node(
        state,
        settings=settings,
        grok_client=mock_grok_client,
        x_client=mock_x_client,
        apify_client=mock_apify_client,
    )

    assert result["web_research"] == "Apify scraped supporting context"
    mock_apify_client.research_urls.assert_called_once()
    assert "research_summary" in result
    assert result["research_summary"]


def test_research_node_skips_apify_without_token(
    monkeypatch: pytest.MonkeyPatch,
    mock_grok_client: MagicMock,
    mock_x_client: MagicMock,
    mock_apify_client: MagicMock,
) -> None:
    from content_autopilot.settings import load_settings
    from content_autopilot.graph.nodes import research_node

    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-api-key")
    monkeypatch.delenv("APIFY_API_TOKEN", raising=False)
    settings = load_settings()

    state = {
        **SAMPLE_STATE,
        "understanding_summary": "Understood launch recap with two media files",
        "media_count": 2,
        "media_types": ["video", "photo"],
    }

    result = research_node(
        state,
        settings=settings,
        grok_client=mock_grok_client,
        x_client=mock_x_client,
        apify_client=mock_apify_client,
    )

    mock_apify_client.research_urls.assert_not_called()
    assert result["web_research"] is None
    assert result["research_summary"]


def test_graph_invoke_runs_understand_then_research(
    settings,
    mock_grok_client: MagicMock,
    mock_x_client: MagicMock,
    mock_apify_client: MagicMock,
) -> None:
    from content_autopilot.graph.workflow import build_understand_research_graph

    graph = build_understand_research_graph(
        settings,
        grok_client=mock_grok_client,
        x_client=mock_x_client,
        apify_client=mock_apify_client,
    )

    result = graph.invoke(SAMPLE_STATE)

    assert result["media_count"] == 2
    assert result["understanding_summary"]
    assert result["research_summary"]
    mock_grok_client.generate.assert_called()
    mock_x_client.fetch_context.assert_called_once()
    mock_apify_client.research_urls.assert_called_once()
