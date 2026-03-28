import json
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
    ROUTE_RECOMMEND,
    ROUTE_SALES,
)

# ── Routing keywords ───────────────────────────────────────────────────────────

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

# ── System prompt ──────────────────────────────────────────────────────────────

COORDINATOR_SYSTEM_PROMPT = """You are the Coordinator of an e-commerce multi-agent system.
Your only job is to read the customer's latest message and decide which agent
should handle it. You must respond with ONLY a valid JSON object - no prose.

Available routes:
- "recommend" → Product Recommendation Agent (browsing, searching, comparing products)
- "sales"     → Sales Agent (cart actions, checkout, discounts, order history)
- "finish"    → End the conversation (goodbye, thank you, done, exit)

Response format (strict JSON, nothing else):
{
  "route": "<recommend|sales|finish>",
  "reason": "<one sentence rationale>"
}

Rules:
1. If the message is about finding, browsing, comparing, or learning about products → "recommend".
2. If the message is about cart, buying, discounts, checkout, or past orders → "sales".
3. If the message is a farewell or the user says they are done → "finish".
4. When in doubt, prefer "recommend".
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

    # Fallback: Ask the LLM to reason and route based on context 
    # and user intent
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
    if any(kw in text for kw in _SALES_KEYWORDS):
        return ROUTE_SALES
    if any(kw in text for kw in _RECOMMEND_KEYWORDS):
        return ROUTE_RECOMMEND
    return None


def _parse_route(content: str) -> str:
    """Extract the route value from the LLM JSON response."""
    try:
        # Strip markdown fences if present
        clean = re.sub(r"```[a-z]*\n?", "", content).strip()
        data = json.loads(clean)
        route = data.get("route", ROUTE_RECOMMEND)
        if route not in (ROUTE_SALES, ROUTE_RECOMMEND, ROUTE_FINISH):
            return ROUTE_RECOMMEND
        return route
    except (json.JSONDecodeError, AttributeError):
        return ROUTE_RECOMMEND
