import operator
import os
import sys
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_coordinator.coordinator import coordinator_node
from agent_sales_recommendation.agents.recommendation_agent import recommendation_agent_node
from agent_sales_recommendation.agents.sales_agent import sales_agent_node
from config import (
    COORDINATOR_NODE,
    RECOMMENDATION_NODE,
    ROUTE_FINISH,
    ROUTE_RECOMMEND,
    ROUTE_SALES,
    SALES_NODE,
)
from config_db import CHECKPOINTER_DB_PATH, DB_DIR
from agent_sales_recommendation.tools.recommendation_tools import RECOMMENDATION_TOOLS
from agent_sales_recommendation.tools.sales_tools import SALES_TOOLS

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


# ── Graph ──────────────────────────────────────────────────────────────────────


def build_graph(checkpointer: SqliteSaver) -> StateGraph:
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
    builder.add_edge(START, COORDINATOR_NODE)

    builder.add_conditional_edges(
        COORDINATOR_NODE,
        route_from_coordinator,
        {
            SALES_NODE: SALES_NODE,
            RECOMMENDATION_NODE: RECOMMENDATION_NODE,
            END: END,
        },
    )

    builder.add_conditional_edges(
        SALES_NODE,
        should_continue_sales,
        {
            "sales_tools": "sales_tools",
            END: END,
        },
    )

    builder.add_conditional_edges(
        RECOMMENDATION_NODE,
        should_continue_recommendation,
        {
            "recommendation_tools": "recommendation_tools",
            END: END,
        },
    )

    builder.add_edge("sales_tools", SALES_NODE)
    builder.add_edge("recommendation_tools", RECOMMENDATION_NODE)

    return builder.compile(checkpointer=checkpointer)


# ── Singleton accessor ─────────────────────────────────────────────────────────

_graph = None
_checkpointer_ctx = None
_checkpointer = None


def get_graph():
    """
    Return a lazily-compiled singleton graph instance.

    The checkpointer database is created automatically inside DB_DIR on first
    call (same directory as products.db and cart.db).
    """
    global _graph, _checkpointer_ctx, _checkpointer
    if _graph is None:
        os.makedirs(DB_DIR, exist_ok=True)
        _checkpointer_ctx = SqliteSaver.from_conn_string(CHECKPOINTER_DB_PATH)
        _checkpointer = _checkpointer_ctx.__enter__()
        _graph = build_graph(checkpointer=_checkpointer)
    return _graph
