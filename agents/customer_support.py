import json
from pathlib import Path
from typing import Dict

# Logger
from helpers.observability.logger import log_event

# State
# from state import AgentState

import os

from langchain_openai import ChatOpenAI

from config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE

# Switch LLM provider via .env:
# LLM_PROVIDER=ollama  → free, local (default)
# LLM_PROVIDER=openai  → uses OPENAI_API_KEY

_provider = os.getenv("LLM_PROVIDER", "openai").lower()

if _provider == "openai":
    llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=OPENAI_API_KEY)
else:
    from langchain_ollama import OllamaLLM
    llm = OllamaLLM(model="llama3")

# ==========================================================
# Load FAQ Knowledge Base
# ==========================================================

def load_faq() -> str:
    faq_path = Path("data/faq.json")

    if not faq_path.exists():
        raise FileNotFoundError("FAQ file not found at data/faq.json")

    try:
        with open(faq_path, "r") as f:
            faq_data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError("faq.json is not valid JSON.")

    formatted = ""
    for item in faq_data:
        formatted += f"Q: {item['question']}\n"
        formatted += f"A: {item['answer']}\n\n"

    return formatted


# ==========================================================
# Responsible Prompt Design (Module 1)
# ==========================================================

def build_prompt(query: str, faq_context: str) -> str:
    return f"""
You are a responsible and professional e-commerce customer support agent.

STRICT RULES:
- Use only the FAQ context provided.
- If the answer is not clearly found in the FAQ, respond exactly with: ESCALATE
- Do not invent policies.
- Keep responses clear and short.

FAQ CONTEXT:
{faq_context}

Customer Question:
{query}

Answer:
"""


# ==========================================================
# Confidence Estimation (Explainability)
# ==========================================================

def estimate_confidence(response: str) -> float:
    if "ESCALATE" in response:
        return 0.0
    return 0.85  # simple static estimate for demo


# ==========================================================
# Main Agent Function (LangGraph Node)
# ==========================================================


def customer_support_agent(state: dict) -> dict:
    log_event("Customer Support Agent invoked")

    # Extract query from messages (LangGraph) or direct user_query (test)
    if "user_query" in state and state["user_query"]:
        query = state["user_query"]
    elif "messages" in state and state["messages"]:
        from langchain_core.messages import HumanMessage
        query = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            ""
        )
    else:
        query = ""

    # Extract query from messages (LangGraph) or direct user_query (test)
    if "user_query" in state and state["user_query"]:
        query = state["user_query"]
    elif "messages" in state and state["messages"]:
        from langchain_core.messages import HumanMessage
        query = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            ""
        )
    else:
        query = ""

    faq_context = load_faq()
    prompt = build_prompt(query=query, faq_context=faq_context)
    result = llm.invoke(prompt)
    if hasattr(result, "content"):
        result = result.content

    if "ESCALATE" in result:
        state["response"] = None
        state["escalate"] = True
        state["confidence"] = 0.0
        state["explanation"] = "No matching FAQ found. Escalated to human agent."
    else:
        state["response"] = result.strip()
        state["escalate"] = False
        state["confidence"] = estimate_confidence(result)
        state["explanation"] = "Response generated using internal FAQ knowledge base."

    log_event(f"Support Response Generated | Escalate={state.get('escalate', False)}")

    # When called from LangGraph (messages-based state)
    if "messages" in state:
        from langchain_core.messages import AIMessage
        reply = "I'm sorry, I don't have that information. Let me connect you with a human agent." \
            if state.get("escalate") else state.get("response", "")
        return {
            "messages": [AIMessage(content=reply)],
            "current_agent": "customer_support_agent",
        }

    # When called directly from test file
    # When called from LangGraph (messages-based state)
    if "messages" in state:
        from langchain_core.messages import AIMessage
        reply = "I'm sorry, I don't have that information. Let me connect you with a human agent." \
            if state.get("escalate") else state.get("response", "")
        return {
            "messages": [AIMessage(content=reply)],
            "current_agent": "customer_support_agent",
        }

    # When called directly from test file
    return state