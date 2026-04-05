import json
import logging
from pathlib import Path
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

FAQ_PATH = Path("data/faq.json")
TOP_K = 3  # number of FAQ entries to return


def _load_faq_data() -> list[dict]:
    if not FAQ_PATH.exists():
        raise FileNotFoundError("FAQ file not found at data/faq.json")
    with open(FAQ_PATH, "r") as f:
        return json.load(f)


def _score(query: str, item: dict) -> int:
    """Simple keyword overlap score against question + answer."""
    tokens = set(query.lower().split())
    text = (item["question"] + " " + item["answer"]).lower()
    return sum(1 for t in tokens if t in text)


@tool
def search_faq(query: str) -> str:
    """
    Search the FAQ knowledge base for entries relevant to the customer's query.

    Args:
        query: The customer's question or keywords to search for.

    Returns:
        A formatted string of the top matching FAQ entries (question + answer),
        or a message indicating nothing was found.
    """
    try:
        faq_data = _load_faq_data()
    except (FileNotFoundError, ValueError) as e:
        return f"FAQ unavailable: {e}"

    scored = sorted(faq_data, key=lambda item: _score(query, item), reverse=True)
    top = [item for item in scored[:TOP_K] if _score(query, item) > 0]

    if not top:
        return "No relevant FAQ entries found."

    result = ""
    for item in top:
        result += f"Q: {item['question']}\nA: {item['answer']}\n\n"
    return result.strip()


CUSTOMER_SUPPORT_TOOLS = [search_faq]