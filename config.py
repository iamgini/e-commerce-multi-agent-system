import os

# Use load_dotenv for internal testing purposes
from dotenv import load_dotenv
load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
# OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")           # Use this for internal testing
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY")    # Use this for actual deployment
LLM_MODEL: str = "gpt-5-nano"                               # model used by all agents
LLM_TEMPERATURE: float = 0.0                                # deterministic outputs

# ── Agent identifiers (used as node names in the graph) ──────────────────────
COORDINATOR_NODE: str = "coordinator"
SALES_NODE: str = "sales_agent"
RECOMMENDATION_NODE: str = "recommendation_agent"
CUSTOMER_SUPPORT_NODE: str = "customer_support_agent"
ORDER_INVENTORY_NODE: str = "order_inventory_agent"
RETURNS_REFUNDS_NODE: str = "returns_refunds_agent"

# ── Routing literals ──────────────────────────────────────────────────────────
ROUTE_SALES: str = "sales"
ROUTE_RECOMMEND: str = "recommend"
ROUTE_SUPPORT: str = "customer_support"
ROUTE_ORDER_INVENTORY: str = "order_inventory"
ROUTE_RETURNS: str = "returns_refunds"
ROUTE_FINISH: str = "finish"
ROUTE_ALERT: str = "alert"

# ── Database ──────────────────────────────────────────────────────────────────
# DB_DIR: str = os.path.join(os.path.dirname(__file__), "data")
# PRODUCTS_DB_PATH: str = os.path.join(DB_DIR, "products.db")
# CART_DB_PATH: str = os.path.join(DB_DIR, "cart.db")
# ORDER_INVENTORY_DB_PATH: str = os.path.join(DB_DIR, "order_inventory.db")
# RETURNS_DB_PATH = os.path.join(DB_DIR, "returns.db")
# CHECKPOINTER_DB_PATH: str = os.path.join(DB_DIR, "checkpoints.db")

# Use this for internal testing
# MAINTENANCE_DB_DSN: str = os.getenv("MAINTENANCE_DB_DSN")
# PRODUCTS_DB_DSN: str = os.getenv("PRODUCTS_DB_DSN")
# CART_DB_DSN: str = os.getenv("CART_DB_DSN")
# ORDER_INVENTORY_DB_DSN: str = os.getenv("ORDER_INVENTORY_DB_DSN")
# RETURNS_DB_DSN: str = os.getenv("RETURNS_DB_DSN")
# CHECKPOINTER_DB_DSN = os.getenv("CHECKPOINTER_DB_DSN")


# Use this for actual deployment
MAINTENANCE_DB_DSN: str = os.environ.get("MAINTENANCE_DB_DSN")
PRODUCTS_DB_DSN: str = os.environ.get("PRODUCTS_DB_DSN")
CART_DB_DSN: str = os.environ.get("CART_DB_DSN")
ORDER_INVENTORY_DB_DSN: str = os.environ.get("ORDER_INVENTORY_DB_DSN")
RETURNS_DB_DSN: str = os.getenv("RETURNS_DB_DSN")
CHECKPOINTER_DB_DSN = os.environ.get("CHECKPOINTER_DB_DSN")
USERS_DB_DSN: str = os.environ.get("USERS_DB_DSN")
CHAINLIT_DB_DSN: str =os.environ.get("DATABASE_URL")

# ── S3 Logging ────────────────────────────────────────────────────────────────
# Use this for internal testing
# S3_ENDPOINT: str = os.getenv("S3_ENDPOINT")
# S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY")
# S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY")  
# S3_REGION: str = os.getenv("S3_REGION")
# S3_BUCKETNAME: str = os.getenv("S3_BUCKETNAME")

# Use this for actual deployment
S3_ENDPOINT: str = os.environ.get("S3_ENDPOINT")
S3_ACCESS_KEY: str = os.environ.get("S3_ACCESS_KEY")
S3_SECRET_KEY: str = os.environ.get("S3_SECRET_KEY")  
S3_REGION: str = os.environ.get("S3_REGION")
S3_BUCKETNAME: str = os.environ.get("S3_BUCKETNAME")

# ── Discount rules ────────────────────────────────────────────────────────────
DISCOUNT_CODES: dict[str, float] = {
    "SAVE10": 0.10,
    "SAVE20": 0.20,
    "WELCOME": 0.15,
}
