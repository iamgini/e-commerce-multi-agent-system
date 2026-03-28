import json
from pathlib import Path
from typing import Dict

# Local LLM
from langchain_ollama import OllamaLLM

# cloud LLM
from langchain_openai import ChatOpenAI

from state import AgentState
from observability.logger import log_event


# ==========================================================
# Local LLM Setup (free, offline)
# ==========================================================
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

def customer_support_agent(state: AgentState) -> AgentState:
    log_event("Customer Support Agent invoked")

    faq_context = load_faq()

    prompt = build_prompt(
        query=state["user_query"],
        faq_context=faq_context
    )

    result = llm.invoke(prompt)

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

    log_event(f"Support Response Generated | Escalate={state['escalate']}")

    return state