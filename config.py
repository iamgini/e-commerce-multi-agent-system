import os
from dotenv import load_dotenv

load_dotenv()

# LLM
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-5-nano")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# Agent identifiers (useful if you later wire the coordinator into a graph)
COORDINATOR_NODE: str = "coordinator"
RECOMMENDATION_NODE: str = "recommendation_agent"
SALES_NODE: str = "sales_agent"
ORDER_INVENTORY_NODE: str = "order_inventory_agent"
FINISH_NODE: str = "finish"

# Routing literals
ROUTE_RECOMMEND: str = "recommend"
ROUTE_SALES: str = "sales"
ROUTE_ORDER_INVENTORY: str = "order_inventory"
ROUTE_FINISH: str = "finish"
