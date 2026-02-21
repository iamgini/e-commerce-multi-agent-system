## Customer Support Agent

## Recommended Architecture (Cheap + Clean)

- LLM runtime → Ollama (free, local)
- Model → Llama 3 8B (good balance)
- Orchestration → LangGraph
- Embeddings (optional) → local embedding model in Ollama
- Knowledge base → simple FAQ JSON or markdown files
- No OpenAI API needed. Zero cost.

## Customer Support Agent: Unified Capability List (In Plan)

### Core Knowledge & Response

- Answer FAQs: Address common questions regarding order status, shipping, payments, and company policies.
- Follow Policies: Ensure all responses strictly adhere to established return and service guidelines.
- Basic Troubleshooting: Provide step-by-step help for common user issues.
- Structured Output: Format all responses for clear user reading and system coordination.

### Safety & Reliability

- Avoid Hallucination: Stick strictly to the provided knowledge source to ensure factual accuracy.
- Escalate When Unsure: Trigger a hand-off to a human or coordinator based on specific escalation rules.
- Be Explainable & Secure: Maintain transparent reasoning for actions while keeping user data safe.

### System Operations

- Log Actions: Keep a detailed record of interactions for auditing and quality control.
- Knowledge Integration: Utilize a prompt template and a dedicated FAQ knowledge source for consistent performance.


## How to Integrates With Coordinator

In `coordinator.py`, we need to route as:

```python
.
.
.
if state["intent"] == "support":
    return "customer_support"
.
.
.
```

## Setup Local LLM

```shell
$ curl -fsSL https://ollama.com/install.sh | sh

$ ollama serve

$ ollama pull llama3

$ ollama run llama3
```

Tip: If you are facing termination issues, then check with lightweight models.

```shell
$ ollama run phi3
```

## Local Testing

```shell
$ python -m venv cs
$ source cs/bin/activate 

$ pip install -r requirements.txt
```