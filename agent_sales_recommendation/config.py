import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
LLM_MODEL: str = "gpt-5-nano"  # model used by all agents
LLM_TEMPERATURE: float = 0.0  # deterministic outputs

# ── Agent identifiers (used as node names in the graph) ──────────────────────
COORDINATOR_NODE: str = "coordinator"
SALES_NODE: str = "sales_agent"
RECOMMENDATION_NODE: str = "recommendation_agent"
CUSTOMER_SUPPORT_NODE: str = "customer_support_agent"
ORDERS_INVENTORY_AGENT: str = "orders_inventory_agent"
RETURNS_REFUNDS_AGENT: str = "returns_refunds_agent"

# ── Routing literals ──────────────────────────────────────────────────────────
ROUTE_SALES: str = "sales"
ROUTE_RECOMMEND: str = "recommend"
ROUTE_SUPPORT: str = "customer_support"
ROUTE_INVENTORY: str = "orders_inventory"
ROUTE_RETURNS: str = "returns_refunds"
ROUTE_FINISH: str = "finish"

# ── Discount rules ────────────────────────────────────────────────────────────
DISCOUNT_CODES: dict[str, float] = {
    "SAVE10": 0.10,
    "SAVE20": 0.20,
    "WELCOME": 0.15,
}
