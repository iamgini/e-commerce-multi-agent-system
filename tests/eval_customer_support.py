"""
DeepEval evaluation suite for the Customer Support Agent.

What this covers:
  - Answer Relevancy  : does the response actually address the question?
  - Faithfulness      : is the response grounded in the FAQ context (no hallucination)?
  - Hallucination     : does the response introduce facts not in the FAQ?
  - Contextual Recall : does the FAQ retrieval capture the needed information?

Run locally (from project root, with venv activated):
  pip install deepeval
  deepeval test run tests/eval_customer_support.py

Or as plain pytest (skips DeepEval metrics, falls back to assertion-only):
  pytest tests/eval_customer_support.py -v

NOTE: DeepEval metrics use an LLM judge internally (gpt-4o-mini by default).
OPENAI_API_KEY must be set. Results are saved to deepeval_results.json.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ---------------------------------------------------------------------------
# DeepEval import — graceful fallback if not installed
# ---------------------------------------------------------------------------
try:
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        HallucinationMetric,
        ContextualRecallMetric,
    )
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Helpers — call the real agent with a real FAQ lookup, mock only the LLM
# so we don't burn tokens during eval runs.
# ---------------------------------------------------------------------------
from unittest.mock import patch, MagicMock
from agents.customer_support import customer_support_agent, build_prompt
from tools.customer_support_tools import search_faq, get_top_score


def _run_agent(query: str, llm_answer: str) -> dict:
    """Run agent with real FAQ search but mocked LLM response.
    Uses direct test call path (no 'messages' key) so result contains
    'response', 'escalate', 'confidence', 'explanation' keys directly.
    """
    state = {"user_query": query}
    with patch("agents.customer_support._get_llm") as mock_llm:
        mock_llm.return_value.invoke.return_value = MagicMock(content=llm_answer)
        return customer_support_agent(state)


def _faq_context_for(query: str) -> str:
    """Return the actual FAQ context the tool would return."""
    return search_faq.invoke(query)


# ---------------------------------------------------------------------------
# Test cases — (query, expected_answer, faq_ground_truth)
# Ground truth is what the FAQ actually says; used for Contextual Recall.
# ---------------------------------------------------------------------------
EVAL_CASES = [
    {
        "id": "return_policy",
        "query": "What is your return policy?",
        "llm_answer": "You can return items within 30 days of delivery.",
        "ground_truth": "You can return items within 30 days of delivery.",
    },
    {
        "id": "shipping_time",
        "query": "How long does shipping take?",
        "llm_answer": "Shipping takes 3-5 business days.",
        "ground_truth": "Shipping takes 3-5 business days.",
    },
    {
        "id": "payment_methods",
        "query": "What payment methods do you accept?",
        "llm_answer": "We accept credit cards and PayPal.",
        "ground_truth": "We accept credit cards and PayPal.",
    },
    {
        "id": "free_shipping",
        "query": "Do you offer free shipping?",
        "llm_answer": "Yes, free standard shipping is available on orders over $50.",
        "ground_truth": "Yes, we offer free standard shipping on orders over $50.",
    },
    {
        "id": "refund_time",
        "query": "How long does a refund take?",
        "llm_answer": "Refunds are processed within 3-5 business days after we receive the item.",
        "ground_truth": "Refunds are processed within 3-5 business days after we receive your returned item.",
    },
    {
        "id": "contact_support",
        "query": "How do I contact support?",
        "llm_answer": "You can email support@shopbot.tbly.cc or call 1-800-123-4567.",
        "ground_truth": "You can contact our support team via email at support@shopbot.tbly.cc or call 1-800-123-4567.",
    },
    {
        "id": "cancel_order",
        "query": "Can I cancel my order?",
        "llm_answer": "You can cancel your order within 1 hour of placing it.",
        "ground_truth": "You can cancel or modify your order within 1 hour of placing it.",
    },
    {
        "id": "hallucination_guard",
        "query": "What is your return policy?",
        # Hallucination test: agent claims 60-day policy — not in FAQ.
        "llm_answer": "You can return items within 60 days and get a full cash refund instantly.",
        "ground_truth": "You can return items within 30 days of delivery.",
    },
    {
        "id": "out_of_scope_escalates",
        "query": "Where is my specific order #98765?",
        # This is NOT in the FAQ — agent should escalate.
        "llm_answer": "ESCALATE",
        "ground_truth": None,  # escalation case — no ground truth expected
    },
]


# ---------------------------------------------------------------------------
# Assertion-based tests (run in plain pytest, no DeepEval needed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", [c for c in EVAL_CASES if c["ground_truth"] is not None], ids=[c["id"] for c in EVAL_CASES if c["ground_truth"] is not None])
def test_agent_answers_faq_queries(case):
    """Agent must not escalate for known FAQ questions and must return a response."""
    result = _run_agent(case["query"], case["llm_answer"])
    if case["llm_answer"] == "ESCALATE":
        assert result["escalate"] is True
    else:
        assert result["escalate"] is False, f"Unexpectedly escalated for: {case['query']}"
        assert result["response"] is not None
        assert len(result["response"]) > 5


def test_out_of_scope_escalates():
    """Queries outside FAQ must escalate with confidence=0."""
    result = _run_agent("Where is my specific order #98765?", "ESCALATE")
    assert result["escalate"] is True
    assert result["confidence"] == 0.0


def test_hallucinated_answer_structure():
    """Even if LLM hallucinates, agent state structure must be valid."""
    result = _run_agent("What is your return policy?", "You can return items within 60 days and get a full cash refund instantly.")
    assert "response" in result or "messages" in result
    assert "confidence" in result
    assert "escalate" in result


def test_faq_retrieval_finds_return_policy():
    """search_faq must retrieve return policy entry for a return query."""
    context = _faq_context_for("return policy")
    assert "30 days" in context.lower(), f"Expected '30 days' in FAQ context, got: {context}"


def test_faq_retrieval_finds_shipping():
    """search_faq must retrieve shipping info."""
    context = _faq_context_for("shipping time")
    assert "3-5 business days" in context.lower() or "shipping" in context.lower()


def test_faq_retrieval_no_match_returns_message():
    """search_faq must return a 'no entries' message for unknown queries."""
    context = _faq_context_for("xyzzy quantum flux capacitor")
    assert "no relevant" in context.lower() or context.strip() == ""


def test_confidence_reflects_faq_score():
    """Strong FAQ match must yield high confidence (>=0.70)."""
    result = _run_agent("What is your return policy?", "You can return items within 30 days.")
    assert result["confidence"] >= 0.70, f"Expected confidence >= 0.70, got {result['confidence']}"


def test_explanation_is_informative():
    """Explanation must be non-empty and mention score for successful answers."""
    result = _run_agent("What payment methods do you accept?", "We accept credit cards and PayPal.")
    assert result["explanation"]
    assert len(result["explanation"]) > 10


# ---------------------------------------------------------------------------
# DeepEval metric tests — only run when DeepEval is installed
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")
class TestDeepEvalMetrics:
    """
    LLM-judge–based evaluation using DeepEval metrics.
    These measure semantic quality beyond keyword matching.

    Thresholds (adjust after first run if needed):
      answer_relevancy  >= 0.7
      faithfulness      >= 0.7
      hallucination     <= 0.3  (lower is better)
    """

    def _make_test_case(self, case: dict) -> "LLMTestCase":
        context = _faq_context_for(case["query"])
        retrieval_context = [context] if context else ["No FAQ context available."]
        return LLMTestCase(
            input=case["query"],
            actual_output=case["llm_answer"],
            expected_output=case["ground_truth"] or "",
            retrieval_context=retrieval_context,
            context=retrieval_context,
        )

    @pytest.mark.parametrize("case", [c for c in EVAL_CASES if c["ground_truth"] is not None and c["llm_answer"] != "ESCALATE"], ids=[c["id"] for c in EVAL_CASES if c["ground_truth"] is not None and c["llm_answer"] != "ESCALATE"])
    def test_answer_relevancy(self, case):
        """Response must be relevant to the customer's question (>= 0.7)."""
        tc = self._make_test_case(case)
        metric = AnswerRelevancyMetric(threshold=0.7, model="gpt-4o-mini", include_reason=True)
        metric.measure(tc)
        print(f"\n[{case['id']}] Answer Relevancy: {metric.score:.2f} — {metric.reason}")
        assert metric.score >= 0.7, f"Answer relevancy too low: {metric.score:.2f}\nReason: {metric.reason}"

    @pytest.mark.parametrize("case", [c for c in EVAL_CASES if c["ground_truth"] is not None and c["llm_answer"] != "ESCALATE"], ids=[c["id"] for c in EVAL_CASES if c["ground_truth"] is not None and c["llm_answer"] != "ESCALATE"])
    def test_faithfulness(self, case):
        """Response must be grounded in the FAQ context (no hallucination >= 0.7)."""
        tc = self._make_test_case(case)
        metric = FaithfulnessMetric(threshold=0.7, model="gpt-4o-mini", include_reason=True)
        metric.measure(tc)
        print(f"\n[{case['id']}] Faithfulness: {metric.score:.2f} — {metric.reason}")
        assert metric.score >= 0.7, f"Faithfulness too low: {metric.score:.2f}\nReason: {metric.reason}"

    def test_hallucination_detected_on_bad_answer(self):
        """A response with fabricated facts must score HIGH on hallucination metric."""
        case = next(c for c in EVAL_CASES if c["id"] == "hallucination_guard")
        tc = self._make_test_case(case)
        metric = HallucinationMetric(threshold=0.5, model="gpt-4o-mini", include_reason=True)
        metric.measure(tc)
        print(f"\n[hallucination_guard] Hallucination score: {metric.score:.2f} — {metric.reason}")
        # Score > 0.5 means hallucination detected — this is expected for this case
        assert metric.score > 0.3, (
            f"Expected hallucination to be detected (score > 0.3), got {metric.score:.2f}. "
            "The fabricated '60 days' policy should have been flagged."
        )

    @pytest.mark.parametrize("case", [c for c in EVAL_CASES if c["ground_truth"] is not None and c["llm_answer"] != "ESCALATE"][:3], ids=[c["id"] for c in EVAL_CASES if c["ground_truth"] is not None and c["llm_answer"] != "ESCALATE"][:3])
    def test_contextual_recall(self, case):
        """FAQ retrieval must surface the information needed to answer (>= 0.7)."""
        tc = self._make_test_case(case)
        metric = ContextualRecallMetric(threshold=0.7, model="gpt-4o-mini", include_reason=True)
        metric.measure(tc)
        print(f"\n[{case['id']}] Contextual Recall: {metric.score:.2f} — {metric.reason}")
        assert metric.score >= 0.7, f"Contextual recall too low: {metric.score:.2f}\nReason: {metric.reason}"
