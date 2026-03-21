# graph/workflow.py
# ─────────────────────────────────────────────────────────────────────────────
# LangGraph multi-agent workflow
#
# Graph topology:
#
#   [START]
#      │
#      ▼
#   coordinator ──── route="recommend" ──▶ recommendation_agent
#      │                                        │
#      ├──── route="sales"   ──▶ sales_agent    │ tool_calls?
#      │                              │         │
#      └──── route="finish"  ──▶ [END]          ▼
#                                     │   recommendation_tools
#                                     │         │ (loops back to agent)
#                                     │         ▼
#                                     │   recommendation_agent
#                                     │         │ no tool_calls
#                                     │         ▼
#                                     │        [END]  ← graph stops here;
#                                     │               main.py gets next input
#                                     │
#                                     │ tool_calls?
#                                     ▼
#                                 sales_tools
#                                     │ (loops back to agent)
#                                     ▼
#                                 sales_agent
#                                     │ no tool_calls
#                                     ▼
#                                    [END]
#
# KEY RULE: agents only loop back to themselves (via tool nodes).
# They NEVER route back to the coordinator.  The coordinator is only
# ever reached from START – i.e., once per user turn.
# ─────────────────────────────────────────────────────────────────────────────

import operator
import os
import sys
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.coordinator import coordinator_node
from agents.recommendation_agent import recommendation_agent_node
from agents.sales_agent import sales_agent_node
from config import (
    COORDINATOR_NODE,
    RECOMMENDATION_NODE,
    ROUTE_FINISH,
    ROUTE_RECOMMEND,
    ROUTE_SALES,
    SALES_NODE,
)
from tools.recommendation_tools import RECOMMENDATION_TOOLS
from tools.sales_tools import SALES_TOOLS

# ── Shared state schema ────────────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    route: str  # filled by coordinator
    current_agent: str  # which agent last responded
    user_id: str  # customer identifier passed through all nodes


# ── Edge conditions ────────────────────────────────────────────────────────────


def route_from_coordinator(state: AgentState) -> str:
    """Conditional edge: coordinator → specialist agent or END."""
    route = state.get("route", ROUTE_RECOMMEND)
    if route == ROUTE_SALES:
        return SALES_NODE
    if route == ROUTE_FINISH:
        return END
    return RECOMMENDATION_NODE  # default


def should_continue_sales(state: AgentState) -> str:
    """
    After the sales agent runs:
    - If it emitted tool calls  → go to the sales tool node.
    - Otherwise                 → END and return response to user.
    """
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "sales_tools"
    return END


def should_continue_recommendation(state: AgentState) -> str:
    """
    After the recommendation agent runs:
    - If it emitted tool calls  → go to the recommendation tool node.
    - Otherwise                 → END and return response to user.
    """
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "recommendation_tools"
    return END


# ── Graph construction ─────────────────────────────────────────────────────────


def build_graph() -> StateGraph:
    """Assemble and compile the full multi-agent LangGraph."""

    builder = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    builder.add_node(COORDINATOR_NODE, coordinator_node)
    builder.add_node(SALES_NODE, sales_agent_node)
    builder.add_node(RECOMMENDATION_NODE, recommendation_agent_node)

    # Tool executor nodes (LangGraph's built-in ToolNode handles tool dispatch)
    builder.add_node("sales_tools", ToolNode(SALES_TOOLS))
    builder.add_node("recommendation_tools", ToolNode(RECOMMENDATION_TOOLS))

    # ── Edges ──────────────────────────────────────────────────────────────────

    # Entry point
    builder.add_edge(START, COORDINATOR_NODE)

    # coordinator routes to an agent or finishes
    builder.add_conditional_edges(
        COORDINATOR_NODE,
        route_from_coordinator,
        {
            SALES_NODE: SALES_NODE,
            RECOMMENDATION_NODE: RECOMMENDATION_NODE,
            END: END,
        },
    )

    # Sales agent: either call tools or return to coordinator
    builder.add_conditional_edges(
        SALES_NODE,
        should_continue_sales,
        {
            "sales_tools": "sales_tools",
            END: END,
        },
    )

    # Recommendation agent: either call tools or return to coordinator
    builder.add_conditional_edges(
        RECOMMENDATION_NODE,
        should_continue_recommendation,
        {
            "recommendation_tools": "recommendation_tools",
            END: END,
        },
    )

    # After tool execution, loop back to the agent that triggered the call
    builder.add_edge("sales_tools", SALES_NODE)
    builder.add_edge("recommendation_tools", RECOMMENDATION_NODE)

    return builder.compile()


# ── Singleton accessor ─────────────────────────────────────────────────────────

_graph = None


def get_graph():
    """Return a lazily-compiled singleton graph instance."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
