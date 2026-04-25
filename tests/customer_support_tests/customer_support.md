# Test Results - customer_support

```shell
$ pytest tests/eval_customer_support.py::test_agent_answers_faq_queries -v --tb=short 2>&1 | head -50
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /home/iamgini/community/e-commerce-multi-agent-system/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/iamgini/community/e-commerce-multi-agent-system
plugins: Faker-37.12.0, repeat-0.9.4, deepeval-3.9.7, anyio-4.13.0, asyncio-1.3.0, xdist-3.8.0, rerunfailures-16.1, langsmith-0.7.33
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 8 items

tests/eval_customer_support.py::test_agent_answers_faq_queries[return_policy] PASSED [ 12%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[shipping_time] PASSED [ 25%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[payment_methods] PASSED [ 37%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[free_shipping] PASSED [ 50%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[refund_time] PASSED [ 62%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[contact_support] PASSED [ 75%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[cancel_order] PASSED [ 87%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[hallucination_guard] PASSED [100%]Running teardown with pytest sessionfinish...
```
## run the full non-DeepEval tests first

```shell
$  cat eval_results_unit.txt
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /home/gmadappa/community/e-commerce-multi-agent-system/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/gmadappa/community/e-commerce-multi-agent-system
plugins: Faker-37.12.0, repeat-0.9.4, deepeval-3.9.7, anyio-4.13.0, asyncio-1.3.0, xdist-3.8.0, rerunfailures-16.1, langsmith-0.7.33
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 35 items / 20 deselected / 15 selected

tests/eval_customer_support.py::test_agent_answers_faq_queries[return_policy] PASSED [  6%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[shipping_time] PASSED [ 13%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[payment_methods] PASSED [ 20%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[free_shipping] PASSED [ 26%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[refund_time] PASSED [ 33%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[contact_support] PASSED [ 40%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[cancel_order] PASSED [ 46%]
tests/eval_customer_support.py::test_agent_answers_faq_queries[hallucination_guard] PASSED [ 53%]
tests/eval_customer_support.py::test_out_of_scope_escalates PASSED       [ 60%]
tests/eval_customer_support.py::test_hallucinated_answer_structure PASSED [ 66%]
tests/eval_customer_support.py::test_faq_retrieval_finds_return_policy PASSED [ 73%]
tests/eval_customer_support.py::test_faq_retrieval_finds_shipping PASSED [ 80%]
tests/eval_customer_support.py::test_faq_retrieval_no_match_returns_message PASSED [ 86%]
tests/eval_customer_support.py::test_confidence_reflects_faq_score PASSED [ 93%]
tests/eval_customer_support.py::test_explanation_is_informative PASSED   [100%]Running teardown with pytest sessionfinish...


====================== 15 passed, 20 deselected in 2.57s =======================
```

## Run DeepEval metrics separately (slow, uses OpenAI):

```shell
...
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_answer_relevancy[free_shipping]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_answer_relevancy[refund_time]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_answer_relevancy[cancel_order]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_faithfulness[return_policy]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_faithfulness[shipping_time]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_faithfulness[free_shipping]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_faithfulness[refund_time]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_faithfulness[cancel_order]
FAILED tests/eval_customer_support.py::TestDeepEvalMetrics::test_faithfulness[hallucination_guard]
============= 9 failed, 11 passed, 1 warning in 1515.17s (0:25:15) =============
```


```shell
$  python3 - <<'EOF'
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("OPENAI_API_KEY", "dummy")  # won't call LLM

from tools.customer_support_tools import search_faq, get_top_score

queries = [
    "What is your return policy?",
    "How long does shipping take?",
    "Do you offer free shipping?",
    "Where is my order #98765?",   # out of scope — should get no match
]

for q in queries:
    score = get_top_score(q)
    context = search_faq.invoke(q)
    print(f"Query   : {q}")
    print(f"Score   : {score}")
    print(f"Context : {context[:120]}...")
    print(f"Confidence: {'0.90 (high)' if score >= 3 else '0.70 (medium)' if score >= 1 else '0.50 (low)'}")
    print("-" * 60)
EOF
Query   : What is your return policy?
Score   : 5
Context : Q: What is your return policy?
A: You can return items within 30 days of delivery.

Q: What happens if an item I ordered...
Confidence: 0.90 (high)
------------------------------------------------------------
Query   : How long does shipping take?
Score   : 5
Context : Q: How long does shipping take?
A: Shipping takes 3-5 business days.

Q: How long does a refund take to process?
A: Refu...
Confidence: 0.90 (high)
------------------------------------------------------------
Query   : Do you offer free shipping?
Score   : 5
Context : Q: Do you offer free shipping?
A: Yes, we offer free standard shipping on orders over $50. Orders below that threshold h...
Confidence: 0.90 (high)
------------------------------------------------------------
Query   : Where is my order #98765?
Score   : 3
Context : Q: Can I get a copy of my invoice or receipt?
A: Yes, order confirmations with invoice details are sent to your email au...
Confidence: 0.90 (high)
------------------------------------------------------------
```