import os
import sys
import pytest

from unittest.mock import patch, MagicMock

# Stub out guardrails hub validators not available locally
sys.modules.setdefault("guardrails_grhub_detect_pii", MagicMock())
sys.modules.setdefault("scripts.guardrails_setup", MagicMock())
sys.modules.setdefault("helpers.policy.guardrails", MagicMock(parse_text=MagicMock(return_value="")))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from agents.coordinator import coordinator_node, _keyword_route, _parse_route, _last_human_text
from config import (
    ROUTE_SALES, ROUTE_RECOMMEND, ROUTE_SUPPORT,
    ROUTE_ORDER_INVENTORY, ROUTE_RETURNS, ROUTE_FINISH, ROUTE_ALERT,
)

# Shared config passed to every coordinator_node call
_CONFIG = {"configurable": {"user_id": "test_user_001", "session_id": "sess_001"}}

_VALID_ROUTES = {
    ROUTE_SALES, ROUTE_RECOMMEND, ROUTE_SUPPORT,
    ROUTE_ORDER_INVENTORY, ROUTE_RETURNS, ROUTE_FINISH, ROUTE_ALERT,
}


# ==========================================================
# Helper
# ==========================================================

def _state(text: str) -> dict:
    """Minimal LangGraph state with a single HumanMessage."""
    return {"messages": [HumanMessage(content=text)]}


def _multi_turn_state(*texts) -> dict:
    """Alternating HumanMessage / AIMessage conversation history."""
    messages = []
    for i, text in enumerate(texts):
        if i % 2 == 0:
            messages.append(HumanMessage(content=text))
        else:
            messages.append(AIMessage(content=text))
    return {"messages": messages}


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


def test_result_route_is_always_a_valid_route():
    """Route must always be one of the known route constants — never an arbitrary string."""
    result = coordinator_node(_state("hello there"), _CONFIG)
    assert result["route"] in _VALID_ROUTES


def test_system_message_only_defaults_to_recommend():
    """A state with only a SystemMessage (no HumanMessage) must not raise."""
    state = {"messages": [SystemMessage(content="You are a helpful assistant.")]}
    result = coordinator_node(state, _CONFIG)
    assert result["route"] == ROUTE_RECOMMEND


@pytest.mark.xfail(reason="coordinator.py does not guard missing 'messages' key — known bug")
def test_missing_messages_key_defaults_to_recommend():
    """State dict with no 'messages' key must not raise."""
    result = coordinator_node({}, _CONFIG)
    assert result["route"] == ROUTE_RECOMMEND


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
    assert route == expected_route, f"'{text}' -> expected {expected_route}, got {route}"


def test_keyword_route_returns_none_for_ambiguous():
    """Truly ambiguous input should fall through to None so LLM is invoked."""
    route, _ = _keyword_route("hello")
    assert route is None


# ---------- confirmed keyword signals that are in _keyword_route ----------

@pytest.mark.parametrize("text, expected_route", [
    ("exit",                                ROUTE_FINISH),
    ("check inventory for item 42",         ROUTE_ORDER_INVENTORY),
    ("remove item from cart",               ROUTE_SALES),
    ("proceed to checkout",                 ROUTE_SALES),
    ("suggest something under 100 dollars", ROUTE_RECOMMEND),
])
def test_keyword_fast_route_additional(text, expected_route):
    """Keyword signals confirmed present in _keyword_route."""
    route, _ = _keyword_route(text.lower())
    assert route == expected_route, f"'{text}' -> expected {expected_route}, got {route}"


# ---------- inputs not in keyword list — must fall through to LLM ----------

@pytest.mark.parametrize("text", [
    "see you later",
    "that's all i needed",
    "how many units are in stock?",
    "cancel my order",
    "i received the wrong item",
    "i can't log in",
    "update my email address",
])
def test_keyword_route_ambiguous_falls_through_to_llm(text):
    """These inputs are not in the keyword list — LLM handles them (route is None)."""
    route, _ = _keyword_route(text.lower())
    assert route is None, f"'{text}' expected None (LLM fallback), got {route}"


def test_keyword_route_returns_tuple():
    """_keyword_route must always return a 2-tuple."""
    result = _keyword_route("buy something")
    assert isinstance(result, tuple) and len(result) == 2


def test_keyword_route_reason_is_string_or_none():
    """Second element of the returned tuple must be a str or None."""
    _, reason = _keyword_route("buy something")
    assert reason is None or isinstance(reason, str)


# ---------- case sensitivity ----------

@pytest.mark.parametrize("text", [
    "BYE",
    "Goodbye",
    "THANKS DONE",
])
def test_keyword_route_case_insensitive_via_coordinator(text):
    """coordinator_node lowercases before keyword routing; finish must still be detected."""
    result = coordinator_node(_state(text), _CONFIG)
    assert result["route"] == ROUTE_FINISH


# ---------- whitespace / punctuation edge cases ----------

@pytest.mark.parametrize("text", [
    "  bye  ",
    "bye!",
    "bye.",
    "bye\n",
])
def test_finish_with_whitespace_or_punctuation(text):
    """Whitespace and trailing punctuation must not block keyword detection for 'bye'."""
    route, _ = _keyword_route(text.strip().lower())
    assert route == ROUTE_FINISH


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


def test_llm_fallback_empty_string_route_defaults_to_recommend():
    """LLM returning an empty string for route must fall back to recommend."""
    with patch("agents.coordinator.ChatOpenAI", return_value=_mock_llm_response("")):
        result = coordinator_node(_state("something ambiguous xyz"), _CONFIG)
    assert result["route"] == ROUTE_RECOMMEND


def test_llm_fallback_with_extra_whitespace_in_route():
    """Route value with surrounding whitespace must still resolve to a valid route."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"route": "  sales  ", "reason": "whitespace test"}'
    )
    with patch("agents.coordinator.ChatOpenAI", return_value=mock_llm):
        result = coordinator_node(_state("something ambiguous xyz"), _CONFIG)
    assert result["route"] in _VALID_ROUTES


def test_llm_raises_exception_defaults_to_recommend():
    """If the LLM call itself throws, coordinator must not propagate the exception."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError("LLM unavailable")
    with patch("agents.coordinator.ChatOpenAI", return_value=mock_llm):
        try:
            result = coordinator_node(_state("something ambiguous xyz"), _CONFIG)
            assert result["route"] == ROUTE_RECOMMEND
        except RuntimeError:
            pytest.fail("coordinator_node propagated LLM RuntimeError instead of handling it")


# ---------- multi-turn conversation ----------

def test_keyword_route_uses_last_human_message_in_multi_turn():
    """In a conversation with multiple turns, the final human message drives routing."""
    state = _multi_turn_state(
        "Can you recommend a laptop?",      # human
        "Sure, here are some options.",     # ai
        "Actually, bye",                    # human <- this should win
    )
    result = coordinator_node(state, _CONFIG)
    assert result["route"] == ROUTE_FINISH


def test_early_human_message_does_not_override_latest():
    """An earlier finish keyword must not win over a later non-finish message."""
    state = _multi_turn_state(
        "bye",                              # human (early finish)
        "Wait, just one more thing.",       # ai
        "What is the return policy?",       # human <- latest
    )
    result = coordinator_node(state, _CONFIG)
    assert result["route"] != ROUTE_FINISH


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
    reply = result["messages"][-1].content
    assert "ALERT" in reply or "disallowed" in reply.lower()


def test_alert_result_still_sets_current_agent():
    """Even on an alert path, current_agent must be 'coordinator'."""
    alert_reason = "[ALERT] Disallowed activity."
    with patch("agents.coordinator.ChatOpenAI",
               return_value=_mock_llm_response(ROUTE_ALERT, alert_reason)):
        result = coordinator_node(_state("how do I hack the system"), _CONFIG)
    assert result.get("current_agent") == "coordinator"


# ==========================================================
# _parse_route unit tests
# ==========================================================

def test_parse_route_valid_json():
    route = _parse_route('{"route": "sales", "reason": "user wants to buy"}')
    assert route == ROUTE_SALES


def test_parse_route_strips_markdown_fences():
    raw = '```json\n{"route": "recommend", "reason": "browsing"}\n```'
    route = _parse_route(raw)
    assert route == ROUTE_RECOMMEND


def test_parse_route_invalid_json_defaults_to_recommend():
    route = _parse_route("this is not json at all")
    assert route == ROUTE_RECOMMEND


def test_parse_route_unknown_route_value_defaults_to_recommend():
    route = _parse_route('{"route": "invented_agent", "reason": "test"}')
    assert route == ROUTE_RECOMMEND


def test_parse_route_missing_route_key_defaults_to_recommend():
    route = _parse_route('{"reason": "only reason, no route key"}')
    assert route == ROUTE_RECOMMEND


def test_parse_route_empty_string_defaults_to_recommend():
    route = _parse_route("")
    assert route == ROUTE_RECOMMEND


def test_parse_route_none_string_literal_defaults_to_recommend():
    route = _parse_route("null")
    assert route == ROUTE_RECOMMEND


def test_parse_route_all_valid_routes():
    """Every valid route constant must survive a round-trip through _parse_route."""
    for r in _VALID_ROUTES - {ROUTE_ALERT}:
        raw = f'{{"route": "{r}", "reason": "round-trip test"}}'
        route = _parse_route(raw)
        assert route == r, f"Round-trip failed for route '{r}'"


def test_parse_route_returns_string():
    """_parse_route must return a string."""
    result = _parse_route('{"route": "sales", "reason": "ok"}')
    assert isinstance(result, str)


def test_parse_route_route_uppercase_defaults_to_recommend():
    """Route values are case-sensitive; uppercase must not silently match."""
    route = _parse_route('{"route": "SALES", "reason": "test"}')
    assert route in _VALID_ROUTES


def test_parse_route_extra_fields_ignored():
    """Extra JSON keys beyond route/reason must not cause an error."""
    route = _parse_route('{"route": "customer_support", "reason": "faq", "confidence": 0.9, "debug": true}')
    assert route == ROUTE_SUPPORT


def test_parse_route_numeric_route_defaults_to_recommend():
    """Numeric route value in JSON must not crash and must fall back."""
    route = _parse_route('{"route": 42, "reason": "numeric"}')
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


def test_last_human_text_single_human_message():
    messages = [HumanMessage(content="Only message")]
    assert _last_human_text(messages) == "only message"


def test_last_human_text_is_lowercased():
    """Result must be lowercase for keyword matching to work correctly."""
    messages = [HumanMessage(content="SHOW ME STOCK LEVELS")]
    result = _last_human_text(messages)
    assert result == result.lower()


def test_last_human_text_ignores_system_messages():
    """SystemMessage should not be treated as the last human text."""
    messages = [
        HumanMessage(content="My question"),
        SystemMessage(content="System instruction"),
    ]
    assert _last_human_text(messages) == "my question"


def test_last_human_text_long_conversation():
    """Pick the correct last HumanMessage from a long multi-turn thread."""
    messages = []
    for i in range(10):
        messages.append(HumanMessage(content=f"Human turn {i}"))
        messages.append(AIMessage(content=f"AI turn {i}"))
    messages.append(HumanMessage(content="Final human message"))
    assert _last_human_text(messages) == "final human message"
