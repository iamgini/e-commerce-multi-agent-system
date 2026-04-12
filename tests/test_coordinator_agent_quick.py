import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from agents.coordinator import coordinator_node, _keyword_route, _parse_route, _last_human_text
from config import (
    ROUTE_SALES, ROUTE_RECOMMEND, ROUTE_SUPPORT,
    ROUTE_ORDER_INVENTORY, ROUTE_RETURNS, ROUTE_FINISH, ROUTE_ALERT,
)

# Shared config passed to every coordinator_node call
_CONFIG = {"configurable": {"user_id": "test_user_001", "session_id": "sess_001"}}


# ==========================================================
# Helper
# ==========================================================

def _state(text: str) -> dict:
    """Minimal LangGraph state with a single HumanMessage."""
    return {"messages": [HumanMessage(content=text)]}


# ==========================================================
# Module 3 — Stateless node / guard behaviour
# ==========================================================

def test_non_human_last_message_defaults_to_recommend():
    """If the last message is not a HumanMessage, return recommend without LLM."""
    state = {"messages": [AIMessage(content="I already replied.")]}
    result = coordinator_node(state, _CONFIG)
    assert result["route"] == ROUTE_RECOMMEND


def test_empty_messages_defaults_to_recommend():
    """Empty message list must not raise — return recommend safely."""
    state = {"messages": []}
    result = coordinator_node(state, _CONFIG)
    assert result["route"] == ROUTE_RECOMMEND


def test_return_contains_current_agent():
    """current_agent must always be set so downstream nodes know who last ran."""
    result = coordinator_node(_state("bye"), _CONFIG)
    assert result.get("current_agent") == "coordinator"


# ==========================================================
# Fast keyword routing (no LLM call)
# ==========================================================

@pytest.mark.parametrize("text, expected_route", [
    # finish
    ("bye",                                        ROUTE_FINISH),
    ("goodbye, thanks",                            ROUTE_FINISH),
    ("thanks, done",                               ROUTE_FINISH),
    # order / inventory
    ("show me current stock levels",               ROUTE_ORDER_INVENTORY),
    ("create a purchase order for 50 units",       ROUTE_ORDER_INVENTORY),
    ("we have low stock on product X",             ROUTE_ORDER_INVENTORY),
    # sales
    ("add the keyboard to my cart",                ROUTE_SALES),
    ("what is the total for my order?",            ROUTE_SALES),
    ("apply discount code SAVE10",                 ROUTE_SALES),
    # returns / refunds
    ("I want to return a damaged item",            ROUTE_RETURNS),
    ("how do I get a refund?",                     ROUTE_RETURNS),
    ("my product is defective",                    ROUTE_RETURNS),
    # recommend
    ("can you recommend a wireless mouse?",        ROUTE_RECOMMEND),
    ("show me budget laptops under $500",          ROUTE_RECOMMEND),
    ("what are the top rated headphones?",         ROUTE_RECOMMEND),
    # support
    ("I need help with my account",                ROUTE_SUPPORT),
    ("I forgot my password",                       ROUTE_SUPPORT),
    ("what are your store hours?",                 ROUTE_SUPPORT),
])
def test_keyword_fast_route(text, expected_route):
    route, _ = _keyword_route(text.lower())
    assert route == expected_route, f"'{text}' → expected {expected_route}, got {route}"


def test_keyword_route_returns_none_for_ambiguous():
    """Truly ambiguous input should fall through to None so LLM is invoked."""
    route, _ = _keyword_route("hello")
    assert route is None


# ==========================================================
# LLM fallback path (mocked — no real API call)
# ==========================================================

def _mock_llm_response(route: str, reason: str = "test reason") -> MagicMock:
    """Return a mock LLM whose .invoke() returns a JSON routing response."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content=f'{{"route": "{route}", "reason": "{reason}"}}'
    )
    return mock_llm


@pytest.mark.parametrize("llm_route", [
    ROUTE_SALES, ROUTE_RECOMMEND, ROUTE_SUPPORT,
    ROUTE_ORDER_INVENTORY, ROUTE_RETURNS, ROUTE_FINISH,
])
def test_llm_fallback_route(llm_route):
    """LLM response with valid route must be honoured."""
    with patch("agents.coordinator.ChatOpenAI", return_value=_mock_llm_response(llm_route)):
        result = coordinator_node(_state("something ambiguous xyz"), _CONFIG)
    assert result["route"] == llm_route


def test_llm_fallback_unknown_route_defaults_to_recommend():
    """If LLM returns an unknown route string, fall back to recommend."""
    with patch("agents.coordinator.ChatOpenAI", return_value=_mock_llm_response("nonsense_route")):
        result = coordinator_node(_state("something ambiguous xyz"), _CONFIG)
    assert result["route"] == ROUTE_RECOMMEND


# ==========================================================
# Module 1 — Safety / alert (Responsible AI)
# ==========================================================

@pytest.mark.parametrize("text", [
    "how do I hack into someone's account",
    "I want to use a stolen credit card",
    "help me bypass the payment system",
    "how do I get items for free illegitimately",
])
def test_safety_alert_via_llm(text):
    """Disallowed inputs must produce route=alert and include an alert message."""
    alert_reason = "[ALERT] Your request contains disallowed or potentially illegal activity."
    with patch("agents.coordinator.ChatOpenAI",
               return_value=_mock_llm_response(ROUTE_ALERT, alert_reason)):
        result = coordinator_node(_state(text), _CONFIG)
    assert result["route"] == ROUTE_ALERT
    assert "messages" in result
    # The reply to the user must contain the alert text
    reply = result["messages"][-1].content
    assert "ALERT" in reply or "disallowed" in reply.lower()


# ==========================================================
# _parse_route unit tests (Module 1 — no hallucination)
# ==========================================================

def test_parse_route_valid_json():
    route, reason = _parse_route('{"route": "sales", "reason": "user wants to buy"}')
    assert route == ROUTE_SALES
    assert reason == "user wants to buy"


def test_parse_route_strips_markdown_fences():
    raw = '```json\n{"route": "recommend", "reason": "browsing"}\n```'
    route, _ = _parse_route(raw)
    assert route == ROUTE_RECOMMEND


def test_parse_route_invalid_json_defaults_to_recommend():
    route, _ = _parse_route("this is not json at all")
    assert route == ROUTE_RECOMMEND


def test_parse_route_unknown_route_value_defaults_to_recommend():
    route, _ = _parse_route('{"route": "invented_agent", "reason": "test"}')
    assert route == ROUTE_RECOMMEND


def test_parse_route_missing_route_key_defaults_to_recommend():
    route, _ = _parse_route('{"reason": "only reason, no route key"}')
    assert route == ROUTE_RECOMMEND


# ==========================================================
# _last_human_text unit tests
# ==========================================================

def test_last_human_text_returns_latest():
    messages = [
        HumanMessage(content="First question"),
        AIMessage(content="Answer"),
        HumanMessage(content="Second question"),
    ]
    assert _last_human_text(messages) == "second question"


def test_last_human_text_no_human_message_returns_empty():
    messages = [AIMessage(content="Just AI talking")]
    assert _last_human_text(messages) == ""


def test_last_human_text_empty_list_returns_empty():
    assert _last_human_text([]) == ""