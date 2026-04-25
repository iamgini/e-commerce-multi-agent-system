import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
from agents.customer_support import customer_support_agent, estimate_confidence, build_prompt


# ── Module 1: Responsible & Explainable AI ────────────────────────────────────

def test_escalates_when_no_faq_match():
    """No FAQ match → escalate=True, confidence=0.0"""
    state = {"user_query": "xyzzy something totally unknown", "messages": []}
    with patch("agents.customer_support._get_llm") as mock_llm_fn:
        mock_llm_fn.return_value.invoke.return_value = MagicMock(content="ESCALATE")
        with patch("agents.customer_support.search_faq") as mock_faq:
            mock_faq.invoke.return_value = "No relevant FAQ entries found."
            with patch("agents.customer_support.get_top_score", return_value=0):
                result = customer_support_agent(state)
    assert result["escalate"] is True
    assert result["confidence"] == 0.0
    assert result["explanation"] is not None


def test_confidence_high_on_strong_faq_match():
    assert estimate_confidence("Here is your answer.", faq_score=4) == 0.90


def test_confidence_medium_on_weak_faq_match():
    assert estimate_confidence("Here is your answer.", faq_score=2) == 0.70


def test_confidence_low_on_minimal_faq_match():
    # score=1 hits _LOW_SCORE_THRESHOLD → _CONFIDENCE_MED (0.70)
    # score=0 with no ESCALATE → _CONFIDENCE_LOW (0.50)
    assert estimate_confidence("Here is your answer.", faq_score=1) == 0.70
    assert estimate_confidence("Here is your answer.", faq_score=0) == 0.50


def test_confidence_zero_on_escalate():
    assert estimate_confidence("ESCALATE", faq_score=5) == 0.0


def test_explanation_contains_score():
    """Explanation must be dynamic, not a static string."""
    state = {"user_query": "return policy", "messages": []}
    with patch("agents.customer_support._get_llm") as mock_llm_fn:
        mock_llm_fn.return_value.invoke.return_value = MagicMock(content="You can return within 30 days.")
        with patch("agents.customer_support.search_faq") as mock_faq:
            mock_faq.invoke.return_value = "Q: Return policy?\nA: 30 days."
            with patch("agents.customer_support.get_top_score", return_value=3):
                result = customer_support_agent(state)
    assert "score=3" in result["explanation"]
    assert result["escalate"] is False


# ── Module 2: Cybersecurity ────────────────────────────────────────────────────

def test_faq_unavailable_escalates_without_calling_llm():
    """If FAQ errors, agent must escalate before reaching LLM."""
    state = {"user_query": "anything", "messages": []}
    with patch("agents.customer_support._get_llm") as mock_llm_fn:
        with patch("agents.customer_support.search_faq") as mock_faq:
            mock_faq.invoke.return_value = "FAQ unavailable: file not found"
            result = customer_support_agent(state)
    mock_llm_fn.assert_not_called()
    assert result["escalate"] is True


def test_llm_exception_escalates_cleanly():
    """LLM failure must not raise — it should escalate."""
    state = {"user_query": "shipping time", "messages": []}
    with patch("agents.customer_support._get_llm") as mock_llm_fn:
        mock_llm_fn.return_value.invoke.side_effect = RuntimeError("timeout")
        with patch("agents.customer_support.search_faq") as mock_faq:
            mock_faq.invoke.return_value = "Q: Shipping?\nA: 3-5 days."
            with patch("agents.customer_support.get_top_score", return_value=2):
                result = customer_support_agent(state)
    assert result["escalate"] is True
    assert result["confidence"] == 0.0


# ── Module 3: Agentic Architecture ────────────────────────────────────────────

def test_langgraph_return_contains_required_keys():
    """Graph return dict must include messages, confidence, explanation, escalate."""
    from langchain_core.messages import HumanMessage
    state = {
        "messages": [HumanMessage(content="What is your return policy?")],
        "user_id": "u1",
    }
    with patch("agents.customer_support._get_llm") as mock_llm_fn:
        mock_llm_fn.return_value.invoke.return_value = MagicMock(content="30 day returns.")
        with patch("agents.customer_support.search_faq") as mock_faq:
            mock_faq.invoke.return_value = "Q: Return policy?\nA: 30 days."
            with patch("agents.customer_support.get_top_score", return_value=3):
                result = customer_support_agent(state)
    for key in ("messages", "current_agent", "confidence", "explanation", "escalate"):
        assert key in result, f"Missing key in graph return: {key}"


def test_state_not_mutated():
    """Original state dict must not be modified (stateless node)."""
    state = {"user_query": "hello", "messages": [], "response": "old"}
    original_response = state["response"]
    with patch("agents.customer_support._get_llm") as mock_llm_fn:
        mock_llm_fn.return_value.invoke.return_value = MagicMock(content="Hi there.")
        with patch("agents.customer_support.search_faq") as mock_faq:
            mock_faq.invoke.return_value = "Q: Hi?\nA: Hello."
            with patch("agents.customer_support.get_top_score", return_value=2):
                customer_support_agent(state)
    assert state["response"] == original_response


# ── Module 4: Integration & Deployment ────────────────────────────────────────

def test_llm_is_not_instantiated_at_import():
    """_get_llm must be lazy — importing the module must not create an LLM."""
    with patch("agents.customer_support.ChatOpenAI") as mock_openai:
        import importlib
        import agents.customer_support
        importlib.reload(agents.customer_support)
    mock_openai.assert_not_called()


def test_ollama_model_reads_env_var(monkeypatch):
    """OLLAMA_MODEL env var must control the Ollama model name."""
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    with patch("langchain_ollama.OllamaLLM") as mock_ollama:
        mock_ollama.return_value = MagicMock()
        from agents.customer_support import _get_llm
        _get_llm.cache_clear()
        _get_llm()
    mock_ollama.assert_called_once_with(model="mistral")