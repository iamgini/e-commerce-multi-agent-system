import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
LLM_MODEL: str = os.getenv("ORDER_INVENTORY_LLM_MODEL", "gpt-5-nano")
LLM_TEMPERATURE: float = float(os.getenv("ORDER_INVENTORY_LLM_TEMPERATURE", "0.0"))
