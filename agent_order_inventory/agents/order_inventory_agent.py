import os
import sys

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import LLM_MODEL, LLM_TEMPERATURE, OPENAI_API_KEY
from agent_order_inventory.tools.order_inventory_tools import ORDER_INVENTORY_TOOLS


ORDER_INVENTORY_SYSTEM_PROMPT = """You are the Order & Inventory Management Agent for an e-commerce business.

Your responsibilities are:
- create, list, and update purchase orders
- create, list, and update supply orders
- receive stock into inventory
- reduce stock when a customer sale happens
- view stock by product
- view customer order history and order status

## How to use your tools
- Use create_purchase_order, list_purchase_orders, update_purchase_order for procurement actions.
- Use create_supply_order, list_supply_orders, update_supply_order for supplier fulfilment actions.
- Use receive_stock when goods arrive and inventory must increase.
- Use reduce_stock_on_customer_sale when a customer order should be recorded and inventory must decrease.
- Use view_stock_by_product when the user asks about stock levels or low-stock products.
- Use view_order_history and view_order_status for customer order visibility.

## Important
- For reduce_stock_on_customer_sale and view_order_history, the current user ID is injected automatically by the system.
- Always use tools for operational data. Do not invent order IDs, stock values, or statuses.
- Keep responses concise and operationally clear.
"""


def create_order_inventory_agent() -> ChatOpenAI:
    """
    Return an LLM model bound to the order and inventory tools.
    """
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )
    return llm.bind_tools(ORDER_INVENTORY_TOOLS)


def order_inventory_agent_node(state: dict, config: RunnableConfig = None) -> dict:
    """
    LangGraph node for the order and inventory agent.
    """
    llm_with_tools = create_order_inventory_agent()

    messages = [SystemMessage(content=ORDER_INVENTORY_SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages, config=config)

    return {
        "messages": [response],
        "current_agent": "order_inventory_agent",
    }
