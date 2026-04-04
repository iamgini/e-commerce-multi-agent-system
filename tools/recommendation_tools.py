import json
import logging
import os
import sys
from typing import Annotated, Literal, Optional

from ddgs import DDGS
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from helpers.database import product_db
from helpers.observability.log_formatting import tool_tracing
from scripts.seed_data import SEED_CATEGORIES

categories = (SEED_CATEGORIES[i][0] for i in range(len(SEED_CATEGORIES)))

logger = logging.getLogger(__name__)

@tool
@tool_tracing
def search_products(
    config: RunnableConfig,
    query: str,
    category: Optional[Literal[*categories]] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
) -> str:
    """
    Search the product catalogue by keyword.

    Args:
        query:      Keyword or phrase to search in product names, descriptions, and tags.
        category:   Optional category name to filter results (e.g. 'Electronics', 'Books').
        max_price:  Optional upper price bound in USD.
        min_rating: Optional minimum average customer rating (0-5).

    Returns:
        A JSON string listing matching products (id, name, price, rating, stock, category).
    """
    results = product_db.search_products(
        query=query,
        category=category,
        max_price=max_price,
        min_rating=min_rating,
        limit=8,
    )
    if not results:
        return "No products found matching your criteria."
    return json.dumps(results, indent=2)


@tool
@tool_tracing
def get_product_details(product_id: int, config: RunnableConfig) -> str:
    """
    Retrieve full details for a specific product.

    Args:
        product_id: The unique integer ID of the product.

    Returns:
        A JSON string with all product fields, or an error message.
    """
    product = product_db.get_product_by_id(product_id)
    if not product:
        return f"Product with ID {product_id} not found."
    return json.dumps(product, indent=2)


@tool
@tool_tracing
def browse_by_category(category: str, config: RunnableConfig) -> str:
    """
    List the top-rated products in a specific product category.

    Args:
        category: Category name (e.g. 'Electronics', 'Clothing', 'Books',
                  'Home & Kitchen', 'Sports').

    Returns:
        A JSON string of up to 8 products sorted by rating.
    """
    results = product_db.get_products_by_category(category, limit=8)
    if not results:
        return f"No products found in category '{category}'."
    return json.dumps(results, indent=2)


@tool
@tool_tracing
def list_categories(config: RunnableConfig) -> str:
    """
    Return all available product categories in the store.

    Returns:
        A JSON string listing all category names and descriptions.
    """
    categories = product_db.get_all_categories()
    return json.dumps(categories, indent=2)


@tool
@tool_tracing
def get_similar_products(product_id: int, config: RunnableConfig) -> str:
    """
    Find products similar to a given product (same category, different item).
    Useful for showing alternatives or complementary items.

    Args:
        product_id: The ID of the reference product.

    Returns:
        A JSON string with up to 5 similar products.
    """
    results = product_db.get_similar_products(product_id, limit=5)
    if not results:
        return "No similar products found."
    return json.dumps(results, indent=2)


@tool
@tool_tracing
def get_trending_products(config: RunnableConfig) -> str:
    """
    Return the current top-rated / trending products across all categories.
    Use this when the user wants popular picks or doesn't know what to look for.

    Returns:
        A JSON string listing up to 6 trending products.
    """
    results = product_db.get_trending_products(limit=6)
    return json.dumps(results, indent=2)


@tool
@tool_tracing
def get_personalised_recommendations(
    user_id: Annotated[str, InjectedState("user_id")],
    config: RunnableConfig
) -> str:
    """
    Generate personalised product recommendations based on the user's
    purchase history. Finds products in the same categories as past purchases.

    Args:
        user_id: The unique identifier of the customer.

    Returns:
        A JSON string with recommended products and a personalisation note.
    """
    history = product_db.get_user_purchase_history(user_id)
    if not history:
        # Fall back to trending when no history exists
        trending = product_db.get_trending_products(limit=5)
        return json.dumps(
            {
                "note": "No purchase history found - showing trending products instead.",
                "recommendations": trending,
            },
            indent=2,
        )

    # Collect unique category IDs from history, keeping order of recency
    seen_cats: list[int] = []
    for item in history:
        cat_id = item["category_id"]
        if cat_id not in seen_cats:
            seen_cats.append(cat_id)

    # Get top products from the user's two most recent categories
    recs: list[dict] = []
    purchased_ids = {item["id"] for item in history}
    for cat_id in seen_cats[:2]:
        category_name = history[[i["category_id"] for i in history].index(cat_id)][
            "category"
        ]
        candidates = product_db.get_products_by_category(category_name, limit=6)
        for p in candidates:
            if p["id"] not in purchased_ids:
                recs.append(p)
        if len(recs) >= 6:
            break

    return json.dumps(
        {
            "note": f"Based on your purchase history ({len(history)} past orders).",
            "recommendations": recs[:6],
        },
        indent=2,
    )


@tool
@tool_tracing
def web_search_product_comparison(
    config: RunnableConfig,
    query: str,
    max_results: Optional[int] = 5,
) -> str:
    """
    Search the web for real-world reviews, expert opinions, and comparisons
    for one or more products.

    Use this tool AFTER presenting catalogue results, when the customer wants
    to compare specific products or asks for external opinions.  Do NOT use
    it as the primary way to discover products — use search_products for that.

    Good use cases:
    - "Which of these headphones has better noise cancellation?"
    - "What do reviewers say about the LG C3 55" OLED evo?"
    - "Compare the Smart Watch Series X vs competitors"
    - "Is the mechanical keyboard worth it for office use?"

    Args:
        query:       A focused comparison or review query.  Include specific
                     product names for the most relevant results.
                     Examples:
                       "Wireless Noise-Cancelling Headphones vs Sony WH-1000XM5 review"
                       "Yoga Mat Premium vs Manduka PRO comparison"
                       "mechanical keyboard Cherry MX office use review 2024"
        max_results: Number of web results to fetch (default 5, max 8).

    Returns:
        A JSON object with:
          query        - the search query used
          results      - list of {title, url, snippet} dicts from top hits
          summary_note - reminder to synthesise these with catalogue data
        Or a plain-text error message if the search fails.
    """
    max_results = min(max_results or 5, 8)

    try:
        results = []
        for hit in DDGS().text(query, max_results=max_results):
            results.append(
                {
                    "title": hit.get("title", ""),
                    "url": hit.get("href", ""),
                    "snippet": hit.get("body", ""),
                }
            )
    except Exception as exc:
        return f"Web search failed: {exc}"

    if not results:
        return f"No web results found for query: '{query}'"

    return json.dumps(
        {
            "query": query,
            "results": results,
            "summary_note": (
                "Synthesise these external snippets with the catalogue data "
                "already shown.  Present a balanced comparison: highlight "
                "real-world strengths and weaknesses alongside our store's "
                "price, rating, and stock."
            ),
        },
        indent=2,
    )


# ── Convenience export ─────────────────────────────────────────────────────────

RECOMMENDATION_TOOLS = [
    search_products,
    get_product_details,
    browse_by_category,
    list_categories,
    get_similar_products,
    get_trending_products,
    get_personalised_recommendations,
    web_search_product_comparison,
]
