import functools
import os

# Logger
from helpers.observability.logger import log_event

from langchain_openai import ChatOpenAI

from config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from tools.customer_support_tools import search_faq, get_top_score

# ==========================================================
# LLM — lazy singleton (Module 4)
# Instantiated on first call, not at import time.
# Swap provider via LLM_PROVIDER env var:
#   LLM_PROVIDER=openai  (default) → uses OPENAI_API_KEY
#   LLM_PROVIDER=ollama             → local, no API key needed
# Swap Ollama model via OLLAMA_MODEL env var (default: llama3)
# ==========================================================

@functools.lru_cache(maxsize=1)
def _get_llm():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        return ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=OPENAI_API_KEY)
    from langchain_ollama import OllamaLLM
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
    return OllamaLLM(model=ollama_model)



# ==========================================================
# Markdown Response Formatter (UI improvement)
# ==========================================================

def _format_response(query: str, response: str) -> str:
    """
    Wrap the LLM plain-text answer in lightweight Markdown so
    Chainlit renders it cleanly in the chat UI.
    """
    return (
        f"**Here's what I found:**\n\n"
        f"{response}\n\n"
        f"---\n"
        f"*Need more help? Type your question or ask to speak to a human agent.*"
    )


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
# Confidence Estimation (Module 1 — Explainability)
# Score-aware: low keyword overlap → lower confidence.
# ==========================================================

_CONFIDENCE_HIGH  = 0.90
_CONFIDENCE_MED   = 0.70
_CONFIDENCE_LOW   = 0.50
_HIGH_SCORE_THRESHOLD = 3
_LOW_SCORE_THRESHOLD  = 1

def estimate_confidence(response: str, faq_score: int) -> float:
    """
    Return a confidence float based on the FAQ keyword-match score.
    0.0  → ESCALATE trigger
    0.50 → weak match  (score == 1)
    0.70 → medium match (score == 2)
    0.90 → strong match (score >= 3)
    """
    if "ESCALATE" in response:
        return 0.0
    if faq_score >= _HIGH_SCORE_THRESHOLD:
        return _CONFIDENCE_HIGH
    if faq_score >= _LOW_SCORE_THRESHOLD:
        return _CONFIDENCE_MED
    return _CONFIDENCE_LOW


# ==========================================================
# Main Agent Function (LangGraph Node) (Module 3)
# ==========================================================

def customer_support_agent(state: dict) -> dict:
    log_event("Customer Support Agent invoked")

    # --- Extract query (single block — duplicate removed) ---
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

    # Log query for audit trail (Module 2 — logging)
    log_event(f"Customer Support Query | length={len(query)} chars")

    # --- Retrieve FAQ context (controlled knowledge source, Module 2) ---
    faq_context = search_faq.invoke(query)

    # Guard: if FAQ tool itself errored, escalate immediately (Module 2)
    if faq_context.startswith("FAQ unavailable:"):
        log_event(f"FAQ unavailable — escalating | reason={faq_context}")
        escalate    = True
        confidence  = 0.0
        explanation = f"FAQ knowledge base unavailable: {faq_context}"
        response    = None
    else:
        # --- LLM call (Module 4 — lazy, replaceable LLM) ---
        prompt = build_prompt(query=query, faq_context=faq_context)
        try:
            result = _get_llm().invoke(prompt)
        except Exception as exc:
            log_event(f"LLM call failed | error={exc}")
            escalate    = True
            confidence  = 0.0
            explanation = "LLM unavailable. Escalated to human agent."
            response    = None
        else:
            if hasattr(result, "content"):
                result = result.content

            # --- Score-aware confidence (Module 1 — explainability) ---
            faq_score   = get_top_score(query)
            escalate    = "ESCALATE" in result
            confidence  = estimate_confidence(result, faq_score)
            if escalate:
                response    = None
                explanation = (
                    f"No FAQ match found (keyword score={faq_score}). "
                    "Escalated to human agent."
                )
            else:
                response    = result.strip()
                explanation = (
                    f"Response generated from FAQ knowledge base "
                    f"(keyword score={faq_score}, confidence={confidence:.2f})."
                )

    log_event(
        f"Support Response Generated | escalate={escalate} "
        f"| confidence={confidence} | explanation={explanation}"
    )

    # --- Return path: LangGraph (messages-based state) (Module 3) ---
    if "messages" in state:
        from langchain_core.messages import AIMessage
        if escalate:
            reply = (
                "I\'m sorry, I don\'t have that information. "
                "Let me connect you with a human agent. 🙏"
            )
        else:
            reply = _format_response(query, response or "")
        return {
            "messages":    [AIMessage(content=reply)],
            "current_agent": "customer_support_agent",
            # Confidence & explanation flow into shared AgentState
            "confidence":  confidence,
            "explanation": explanation,
            "escalate":    escalate,
        }

    # --- Return path: direct test call ---
    return {
        **state,
        "response":    response,
        "escalate":    escalate,
        "confidence":  confidence,
        "explanation": explanation,
    }