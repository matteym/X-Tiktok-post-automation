"""LangGraph workflow assembly for content-autopilot."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from content_autopilot.graph.clients import ApifyClient, GrokClient, XClient
from content_autopilot.graph.nodes import research_node, understand_node
from content_autopilot.graph.state import ContentAutopilotState
from content_autopilot.settings import Settings


def build_understand_research_graph(
    settings: Settings,
    *,
    grok_client: GrokClient | None = None,
    x_client: XClient | None = None,
    apify_client: ApifyClient | None = None,
):
    """Build START -> understand -> research graph."""
    grok = grok_client or GrokClient(settings)
    x = x_client or XClient(settings)
    apify = apify_client or ApifyClient(settings)

    def understand(state: ContentAutopilotState) -> ContentAutopilotState:
        return understand_node(state, grok_client=grok)

    def research(state: ContentAutopilotState) -> ContentAutopilotState:
        return research_node(
            state,
            settings=settings,
            grok_client=grok,
            x_client=x,
            apify_client=apify,
        )

    graph = StateGraph(ContentAutopilotState)
    graph.add_node("understand", understand)
    graph.add_node("research", research)
    graph.add_edge(START, "understand")
    graph.add_edge("understand", "research")
    graph.add_edge("research", END)
    return graph.compile()
