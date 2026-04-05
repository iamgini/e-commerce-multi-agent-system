import json
import logging
import os
import re
import sys

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    OPENAI_API_KEY,
    ROUTE_FINISH,
    ROUTE_ORDER_INVENTORY,
    ROUTE_RECOMMEND,
    ROUTE_RETURNS,
    ROUTE_SALES,
    ROUTE_SUPPORT,
)
from helpers.observability.log_formatting import format_agent_response

logger = logging.getLogger(__name__)


# ── Routing keywords ───────────────────────────────────────────────────────────
_ORDER_INVENTORY_KEYWORDS = {
    "purchase order",
    "purchase orders",
    "create po",
    "update po",
    "po status",
    "procurement",
    "supplier",
    "suppliers",
    "vendor",
    "vendors",
    "supply order",
    "supply orders",
    "goods receipt",
    "receive stock",
    "stock received",
    "inventory",
    "stock level",
    "stock levels",
    "stock by product",
    "view stock",
    "current stock",
    "warehouse stock",
    "low stock",
    "reorder level",
    "restock",
    "inventory movement",
    "inventory movements",
    "stock movement",
    "stock movements",
    "reduce stock",
    "deduct stock",
    "adjust stock",
}
_SALES_KEYWORDS = {
    "add to cart",
    "remove from cart",
    "update cart",
    "my cart",
    "view cart",
    "checkout",
    "place order",
    "buy",
    "purchase",
    "discount code",
    "promo code",
    "order history",
    "my orders",
    "order details",
    "pay",
    "total",
    "price",
    "how much",
    "apply code",
    "remove item",
    "delete item",
}

_RECOMMEND_KEYWORDS = {
    "recommend",
    "suggestion",
    "suggest",
    "looking for",
    "find",
    "search",
    "show me",
    "browse",
    "what do you have",
    "best",
    "popular",
    "trending",
    "similar",
    "like this",
    "alternatives",
    "compare",
    "category",
    "rating",
    "cheap",
    "budget",
    "under $",
    "top rated",
    "gift",
    "need a",
    "want a",
}

_RETURNS_KEYWORDS = {
    "return",
    "refund",
    "damaged",
    "broken",
    "complaint",
    "defective",
    "eligible",
    "return policy",
    "return window",
    "shipping back",
    "refund status",
    "money back",
    "reimbursement",
    "issue",
    "problem",
    "warranty",
    "exchange",
    "return label",
    "return tracking",
    "when will i get",
    "refund when",
    "can i return",
    "how do i return",
    "return process"}

_SUPPORT_KEYWORDS = {
    "help",
    "support",
    "contact",
    "human agent",
    "speak to someone",
    "talk to agent",
    "store hours",
    "opening hours",
    "account",
    "login",
    "password",
    "technical issue",
    "not working",
    "error",
    "problem with my account",
    "shipping",
    "how long does shipping",
    "delivery time",
    "how long",
    "payment methods",
    "payment"
}
# ── System prompt ──────────────────────────────────────────────────────────────

COORDINATOR_SYSTEM_PROMPT = """You are the Coordinator of an e-commerce multi-agent system.
Your only job is to read the customer's latest message and decide which agent
should handle it. You must respond with ONLY a valid JSON object - no prose.

Available routes:
- "support"   → Customer Support Agent (general inquiries, store hours, technical issues, human agent requests, account help)
- "order_inventory" → Order & Inventory Agent (purchase orders, supply orders, stock, procurement, warehouse operations)
- "returns_refunds"   → Returns and Refunds Agent (refund requests, damaged items, exchange policy, return labels, warranty claims)
- "recommend" → Product Recommendation Agent (browsing, searching, comparing products)
- "sales"     → Sales Agent (cart actions, checkout, discounts, order history)
- "finish"    → End the conversation (goodbye, thank you, done, exit)

Response format (strict JSON, nothing else):
{
  "route": "<recommend|sales|order_inventory|customer_support|returns_refunds|finish>",
  "reason": "<one sentence rationale>"
}

Rules:
1. If the message is about finding, browsing, comparing, or learning about products → "recommend".
2. If the message is about cart, buying, discounts, checkout, or past orders → "sales".
3. If the message is about stock levels, warehouse inventory, receiving stock, purchase orders, supply orders, supplier operations, or procurement → "order_inventory".
4. If the message is about returning items, refunds, damaged goods, exchange, warranty, or complaints → "returns_refunds".
5. If the message is a farewell or the user says they are done → "finish".
6. When in doubt, prefer "recommend".
"""

# ── Coordinator node ────────────────────────────────────────────────────────────


def coordinator_node(state: dict, config: RunnableConfig = None) -> dict:
    """
    LangGraph node: Inspect the latest user message and return a routing decision.
    The decision is stored in state["route"].

    Safety guard: If no HumanMessage is at the top of the stack (e.g. the node
    is somehow reached after an AI turn), default to ROUTE_RECOMMEND rather
    than re-routing mid-response.
    """
    # Guard: Only route when the most recent message is from the human,
    # prevents accidental re-entry if the graph topology is ever extended
    last_msg = state["messages"][-1] if state["messages"] else None
    if not isinstance(last_msg, HumanMessage):
        return {"route": ROUTE_RECOMMEND}

    # Fast keyword-based pre-routing (skips LLM call)
    last_human = _last_human_text(state["messages"])
    fast_route = _keyword_route(last_human)
    if fast_route:
        return {"route": fast_route}

    # Fallback: Ask the LLM to reason and route 
    # based on context and user intent
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )

    messages = (
        [SystemMessage(content=COORDINATOR_SYSTEM_PROMPT)]
        + state["messages"][:-1]
        + [HumanMessage(content=last_human or "Hello")]
    )

    response = llm.invoke(messages, config=config)
    route = _parse_route(response.content)

    user_id = config.get("configurable", {}).get("thread_id", "unknown_user")
    logger.info(
       f"USER_ID: {user_id} | "
       f"{format_agent_response(response)}"
       )

    return {"route": route}


# ── Helpers ────────────────────────────────────────────────────────────────────


def _last_human_text(messages: list) -> str:
    """Return the text of the most recent HumanMessage."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content.lower()
    return ""


def _keyword_route(text: str) -> str | None:
    """Return a route if obvious keywords are present, else None."""
    if any(
        kw in text
        for kw in ("bye", "goodbye", "thank you", "thanks", "done", "exit", "quit")
    ):
        return ROUTE_FINISH
    if any(kw in text for kw in _ORDER_INVENTORY_KEYWORDS):
        return ROUTE_ORDER_INVENTORY
    if any(kw in text for kw in _SALES_KEYWORDS):
        return ROUTE_SALES
    if any(kw in text for kw in _RETURNS_KEYWORDS):
        return ROUTE_RETURNS
    if any(kw in text for kw in _RECOMMEND_KEYWORDS):
        return ROUTE_RECOMMEND
    if any(kw in text for kw in _SUPPORT_KEYWORDS):
        return ROUTE_SUPPORT
    return None


def _parse_route(content: str) -> str:
    """Extract the route value from the LLM JSON response."""
    try:
        # Strip markdown fences if present
        clean = re.sub(r"```[a-z]*\n?", "", content).strip()
        data = json.loads(clean)
        route = data.get("route", ROUTE_RECOMMEND)
        # route = data.get("route", ROUTE_SUPPORT)
        if route not in (ROUTE_SALES, ROUTE_RECOMMEND, ROUTE_ORDER_INVENTORY,ROUTE_RETURNS,ROUTE_SUPPORT, ROUTE_FINISH):
            return ROUTE_RECOMMEND
            # return ROUTE_SUPPORT

        return route
    except (json.JSONDecodeError, AttributeError):
        return ROUTE_RECOMMEND
        # return ROUTE_SUPPORT
