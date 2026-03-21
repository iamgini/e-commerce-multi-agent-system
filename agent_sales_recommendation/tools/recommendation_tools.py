import json
import os
import sys
from typing import Literal, Optional

from langchain_core.tools import tool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import product_db
from config_db import SEED_CATEGORIES

categories = (SEED_CATEGORIES[i][0] for i in range(len(SEED_CATEGORIES)))


@tool
def search_products(
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
def get_product_details(product_id: int) -> str:
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
def browse_by_category(category: str) -> str:
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
def list_categories() -> str:
    """
    Return all available product categories in the store.

    Returns:
        A JSON string listing all category names and descriptions.
    """
    categories = product_db.get_all_categories()
    return json.dumps(categories, indent=2)


@tool
def get_similar_products(product_id: int) -> str:
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
def get_trending_products() -> str:
    """
    Return the current top-rated / trending products across all categories.
    Use this when the user wants popular picks or doesn't know what to look for.

    Returns:
        A JSON string listing up to 6 trending products.
    """
    results = product_db.get_trending_products(limit=6)
    return json.dumps(results, indent=2)


@tool
def get_personalised_recommendations(user_id: str) -> str:
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
                "note": "No purchase history found – showing trending products instead.",
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


# ── Convenience export ─────────────────────────────────────────────────────────

RECOMMENDATION_TOOLS = [
    search_products,
    get_product_details,
    browse_by_category,
    list_categories,
    get_similar_products,
    get_trending_products,
    get_personalised_recommendations,
]
