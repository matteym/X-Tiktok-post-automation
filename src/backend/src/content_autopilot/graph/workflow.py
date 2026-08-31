"""LangGraph workflow assembly for content-autopilot."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from content_autopilot.graph.clients import ApifyClient, GrokClient, XClient
from content_autopilot.graph.nodes import (
    analyze_node,
    generate_node,
    publish_x_node,
    research_node,
    strategy_node,
    tiktok_proposal_node,
    understand_node,
    validate_node,
)
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


def build_content_autopilot_graph(
    settings: Settings,
    *,
    grok_client: GrokClient | None = None,
    x_client: XClient | None = None,
    apify_client: ApifyClient | None = None,
):
    """Build START -> understand -> research -> analyze -> strategy -> generate -> validate -> publish_x -> tiktok_proposal."""
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

    def analyze(state: ContentAutopilotState) -> ContentAutopilotState:
        return analyze_node(state, grok_client=grok)

    def strategy(state: ContentAutopilotState) -> ContentAutopilotState:
        return strategy_node(state, grok_client=grok)

    def generate(state: ContentAutopilotState) -> ContentAutopilotState:
        return generate_node(state, grok_client=grok)

    def validate(state: ContentAutopilotState) -> ContentAutopilotState:
        return validate_node(state)

    def publish_x(state: ContentAutopilotState) -> ContentAutopilotState:
        return publish_x_node(state, settings=settings, x_client=x)

    def tiktok_proposal(state: ContentAutopilotState) -> ContentAutopilotState:
        return tiktok_proposal_node(
            state,
            settings=settings,
            apify_client=apify,
        )

    graph = StateGraph(ContentAutopilotState)
    graph.add_node("understand", understand)
    graph.add_node("research", research)
    graph.add_node("analyze", analyze)
    graph.add_node("strategy", strategy)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate)
    graph.add_node("publish_x", publish_x)
    graph.add_node("tiktok_proposal", tiktok_proposal)
    graph.add_edge(START, "understand")
    graph.add_edge("understand", "research")
    graph.add_edge("research", "analyze")
    graph.add_edge("analyze", "strategy")
    graph.add_edge("strategy", "generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", "publish_x")
    graph.add_edge("publish_x", "tiktok_proposal")
    graph.add_edge("tiktok_proposal", END)
    return graph.compile()
