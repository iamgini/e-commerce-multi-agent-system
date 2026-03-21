import os
import sys

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import LLM_MODEL, LLM_TEMPERATURE, OPENAI_API_KEY
from tools.recommendation_tools import RECOMMENDATION_TOOLS

# ── System prompt ──────────────────────────────────────────────────────────────

RECOMMENDATION_SYSTEM_PROMPT = """You are the Product Recommendation Agent for an e-commerce store.

Your primary mission is to help customers **discover products they will love**.

## Your Capabilities
- Search the product catalogue by keyword, category, price range, or rating
- Browse products by category
- Fetch detailed information about any specific product
- Identify products similar to one the customer already likes
- Highlight trending / top-rated items store-wide
- Deliver personalised recommendations derived from the user's purchase history

## How You Operate
1. **Listen carefully** to the customer's request. Extract their intent:
   - Are they browsing (no specific need)?
   - Do they want something in a particular category?
   - Do they have a budget constraint?
   - Are they looking for gifts, replacements, or upgrades?
2. **Use your tools** to search or browse - do not guess at product details.
3. **Present options clearly**: include the product name, price, rating, and
   a one-line reason why it fits the customer's need.
4. **Limit unsolicited suggestions** to 3-5 products; offer to show more if
   the customer requests it.
5. When the customer indicates they want to **add an item to their cart or
   complete a purchase**, tell them you are passing them to the Sales Agent.

## Boundaries
- You do NOT manage carts, apply discounts, or process orders - refer all 
  pproduct-purchase questions to the Sales Agent.
- Never make up product names, prices, or ratings - always use your tools.
- If a product is out of stock, proactively suggest an alternative.

## Tone
Friendly, knowledgeable, and concise. Think of yourself as a helpful shop
assistant who genuinely wants the customer to find the right product.
"""

# ── Agent factory ──────────────────────────────────────────────────────────────


def create_recommendation_agent() -> ChatOpenAI:
    """
    Return a LLM model bound to the recommendation tools.
    The caller (LangGraph node) is responsible for prepending the system message.
    """
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )
    return llm.bind_tools(RECOMMENDATION_TOOLS)


# ── LangGraph node callable ────────────────────────────────────────────────────


def recommendation_agent_node(state: dict, config: RunnableConfig = None) -> dict:
    """
    LangGraph node for the recommendation agent.

    Receives the shared graph state (which includes `messages`) and appends
    the agent's response to the message list.
    """
    llm_with_tools = create_recommendation_agent()

    # Prepend the system prompt so the LLM always has its persona
    messages = [SystemMessage(content=RECOMMENDATION_SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages, config=config)

    return {
        "messages": [response],
        "current_agent": "recommendation_agent",
    }
