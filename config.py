import os

## Use load_dotenv for internal testing purposes
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
# OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY")
LLM_MODEL: str = "gpt-5-nano"  # model used by all agents
LLM_TEMPERATURE: float = 0.0  # deterministic outputs

# ── Agent identifiers (used as node names in the graph) ──────────────────────
COORDINATOR_NODE: str = "coordinator"
SALES_NODE: str = "sales_agent"
RECOMMENDATION_NODE: str = "recommendation_agent"
CUSTOMER_SUPPORT_NODE: str = "customer_support_agent"
ORDER_INVENTORY_NODE: str = "orders_inventory_agent"
RETURNS_REFUNDS_NODE: str = "returns_refunds_agent"

# ── Routing literals ──────────────────────────────────────────────────────────
ROUTE_SALES: str = "sales"
ROUTE_RECOMMEND: str = "recommend"
ROUTE_SUPPORT: str = "customer_support"
ROUTE_ORDER_INVENTORY: str = "orders_inventory"
ROUTE_RETURNS: str = "returns_refunds"
ROUTE_FINISH: str = "finish"

# ── Database ──────────────────────────────────────────────────────────────────
# DB_DIR: str = os.path.join(os.path.dirname(__file__), "data")
# PRODUCTS_DB_PATH: str = os.path.join(DB_DIR, "products.db")
# CART_DB_PATH: str = os.path.join(DB_DIR, "cart.db")
# ORDER_INVENTORY_DB_PATH: str = os.path.join(DB_DIR, "order_inventory.db")
# CHECKPOINTER_DB_PATH: str = os.path.join(DB_DIR, "checkpoints.db")

MAINTENANCE_DB_DSN = "postgresql://postgres:testing_only@felixpi:5432/postgres?sslmode=disable"
PRODUCTS_DB_DSN = "postgresql://postgres:testing_only@felixpi:5432/products_db?sslmode=disable"
CART_DB_DSN = "postgresql://postgres:testing_only@felixpi:5432/cart_db?sslmode=disable"
ORDER_INVENTORY_DB_DSN = "postgresql://postgres:testing_only@felixpi:5432/order_inventory_db?sslmode=disable"
CHECKPOINTER_DB_DSN = "postgresql://postgres:testing_only@felixpi:5432/checkpoints_db?sslmode=disable"

# ── Discount rules ────────────────────────────────────────────────────────────
DISCOUNT_CODES: dict[str, float] = {
    "SAVE10": 0.10,
    "SAVE20": 0.20,
    "WELCOME": 0.15,
}
