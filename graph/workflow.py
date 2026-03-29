import operator
import os
import sys
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.coordinator import coordinator_node
from agents.customer_support import customer_support_agent
from agents.order_inventory_agent import order_inventory_agent_node
from agents.recommendation_agent import recommendation_agent_node
from agents.sales_agent import sales_agent_node
from config import (
    CHECKPOINTER_DB_PATH,
    COORDINATOR_NODE,
    CUSTOMER_SUPPORT_NODE,
    DB_DIR,
    ORDER_INVENTORY_NODE,
    RECOMMENDATION_NODE,
    RETURNS_REFUNDS_NODE,
    ROUTE_FINISH,
    ROUTE_ORDER_INVENTORY,
    ROUTE_RECOMMEND,
    ROUTE_RETURNS,
    ROUTE_SALES,
    ROUTE_SUPPORT,
    SALES_NODE,
)
from tools.order_inventory_tools import ORDER_INVENTORY_TOOLS
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
    if route == ROUTE_ORDER_INVENTORY:
        return ORDER_INVENTORY_NODE
    if route == ROUTE_SUPPORT:
        return CUSTOMER_SUPPORT_NODE
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
    builder.add_node(ORDER_INVENTORY_NODE, order_inventory_agent_node)
    builder.add_node(CUSTOMER_SUPPORT_NODE, customer_support_agent)
    # builder.add_node(RETURNS_REFUNDS_NODE, )  ## Insert your agent node here

    # Tool executor nodes (LangGraph's built-in ToolNode handles tool dispatch)
    builder.add_node("sales_tools", ToolNode(SALES_TOOLS))
    builder.add_node("recommendation_tools", ToolNode(RECOMMENDATION_TOOLS))
    builder.add_node("order_inventory_tools", ToolNode(ORDER_INVENTORY_TOOLS))
    # builder.add_node() ## Insert your tool node here
    # builder.add_node() ## Insert your tool node here


    # ── Edges ──────────────────────────────────────────────────────────────────
    builder.add_edge(START, COORDINATOR_NODE)

    builder.add_conditional_edges(
        COORDINATOR_NODE,
        route_from_coordinator,
        {
            SALES_NODE: SALES_NODE,
            RECOMMENDATION_NODE: RECOMMENDATION_NODE,
            CUSTOMER_SUPPORT_NODE: CUSTOMER_SUPPORT_NODE,
            ORDER_INVENTORY_NODE: ORDER_INVENTORY_NODE,
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

    builder.add_conditional_edges(
        ORDER_INVENTORY_NODE,
        should_continue_sales,
        {
            "order_inventory_tools": "order_inventory_tools",
            END: END,
        },
    )

    builder.add_edge("sales_tools", SALES_NODE)
    builder.add_edge("recommendation_tools", RECOMMENDATION_NODE)
    builder.add_edge("order_inventory_tools", ORDER_INVENTORY_NODE)
    # builder.add_edge(CUSTOMER_SUPPORT_NODE, END) ## Not required

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
