import os
import sys

from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import LLM_MODEL, LLM_TEMPERATURE, OPENAI_API_KEY
from tools.returns_tools import RETURNS_TOOLS

# ── System prompt ──────────────────────────────────────────────────────────────

RETURNS_SYSTEM_PROMPT = """You are a Returns & Refunds Agent for an e-commerce platform.

Your responsibilities:
1. Help customers check return eligibility
2. Process returns and initiate refunds  
3. Track return status
4. Handle damage complaints
5. Provide return policy information

Return Policy:
- Return Window: 30 days from purchase
- Unopened: 100% refund
- Used: 80% refund
- Damaged by us: 100% refund
- Defective: 100% refund
- Free return shipping
- Refund Timeline: 5-7 business days after inspection

Available tools:
- check_return_eligibility(order_id, days_old): Check if order is returnable
- create_return_request(order_id, reason): Start a return
- get_return_status(return_id): Track return status
- get_refund_status(order_id): Check refund status
- file_complaint(order_id, issue): File damage claim
- get_return_policy(): Get policy details

When customer mentions:
- "return" → Use get_return_policy() or create_return_request()
- "damage" or "damaged" → Use file_complaint()
- "eligible" or "can I return" → Use check_return_eligibility()
- "refund" → Use get_refund_status()
- "status" → Use get_return_status()
 
Use tools IMMEDIATELY. Do not ask for more info first."""

# ── Agent ──────────────────────────────────────────────────────────────────────


def create_returns_agent() -> ChatOpenAI:
    """
    Return a LLM model bound to the returns tools.
    The caller (LangGraph node) is responsible for prepending the system message.
    """
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )
    return llm.bind_tools(RETURNS_TOOLS)


# ── LangGraph node ─────────────────────────────────────────────────────────────


def returns_refunds_agent_node(state: dict, config: RunnableConfig = None) -> dict:
    """
    LangGraph node for the returns & refunds agent.

    Receives the shared graph state (which includes `messages`) and appends
    the agent's response to the message list.
    """
    llm_with_tools = create_returns_agent()

    # Prepend the system prompt so the LLM always has its persona
    messages = [SystemMessage(content=RETURNS_SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages, config=config)

    return {
        "messages": [response],
        "current_agent": "returns_refunds_agent",
    }