import re
from difflib import SequenceMatcher
from typing import Optional

import psycopg
from psycopg.rows import dict_row

from config import PRODUCTS_DB_DSN

# Stop-words that carry no search signal and should not be treated as tokens.
_STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "for",
    "in",
    "on",
    "at",
    "to",
    "of",
    "with",
    "is",
    "my",
    "i",
    "me",
    "do",
    "you",
    "have",
    "some",
    "any",
    "get",
    "need",
    "want",
    "looking",
}


def _tokenise(text: str) -> list[str]:
    """
    Lower-case, strip punctuation, split on whitespace, and remove stop-words.
    Returns a de-duplicated list of meaningful tokens.
    """
    words = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    seen, tokens = set(), []
    for w in words:
        if w not in _STOP_WORDS and w not in seen:
            seen.add(w)
            tokens.append(w)
    return tokens


def _relevance_score(product: dict, tokens: list[str], raw_query: str) -> float:
    """
    Compute a relevance score for a product against the search query.

    Scoring components (higher = better match):
    ┌──────────────────────────────────────────────────┬────────┐
    │ Component                                        │ Weight │
    ├──────────────────────────────────────────────────┼────────┤
    │ Exact phrase match in name                       │  3.0   │
    │ Token found in product name                      │  2.0   │
    │ Token found in tags                              │  1.5   │
    │ Token found in description                       │  1.0   │
    │ difflib fuzzy ratio on name vs raw query         │  2.0   │
    └──────────────────────────────────────────────────┴────────┘
    """
    name = (product.get("name") or "").lower()
    desc = (product.get("description") or "").lower()
    tags = (product.get("tags") or "").lower()
    q_low = raw_query.lower()

    score = 0.0

    # Exact phrase bonus
    if q_low in name:
        score += 3.0

    # Per-token hits
    for token in tokens:
        if token in name:
            score += 2.0
        if token in tags:
            score += 1.5
        if token in desc:
            score += 1.0

    # Fuzzy ratio between the raw query and the product name
    fuzzy = SequenceMatcher(None, q_low, name).ratio()
    score += fuzzy * 2.0

    return score


def _connect() -> psycopg.Connection:
    return psycopg.connect(PRODUCTS_DB_DSN)


# ── Product queries ────────────────────────────────────────────────────────────
def search_products(
    query: str,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Fuzzy token-based search across product name, description, and tags.

    How it works
    ────────────
    1. The query is split into individual tokens (e.g. "wireless headphones"
       → ["wireless", "headphones"]).
    2. SQL fetches every product where ANY single token appears in the name,
       description, or tags — this is deliberately broad so no real match
       is missed at the database level.
    3. Optional filters (category, max_price, min_rating) are applied in SQL.
    4. Python re-ranks the candidates by a relevance score that rewards:
       • exact phrase matches in the product name
       • the number of query tokens that hit each searchable field
       • a difflib fuzzy-ratio between the raw query and the product name
    5. The top `limit` results by score are returned.

    This means a query like "wireless headphones" will correctly surface
    "Wireless Noise-Cancelling Headphones" even though the exact phrase
    "wireless headphones" never appears in the product name.
    """
    tokens = _tokenise(query)
    if not tokens:
        return []

    token_clauses = " OR ".join(
        "(p.name LIKE %s OR p.description LIKE %s OR p.tags LIKE %s)" for _ in tokens
    )
    token_params = []
    for t in tokens:
        pat = f"%{t}%"
        token_params.extend([pat, pat, pat])

    sql = f"""
        SELECT p.id, p.name, p.description, p.price, p.stock,
               p.rating, p.tags, c.name AS category
        FROM   products p
        JOIN   categories c ON c.id = p.category_id
        WHERE  ({token_clauses})
    """

    if category:
        sql += " AND c.name LIKE %s"
        token_params.append(f"%{category}%")
    if max_price is not None:
        sql += " AND p.price <= %s"
        token_params.append(max_price)
    if min_rating is not None:
        sql += " AND p.rating >= %s"
        token_params.append(min_rating)

    sql += " LIMIT %s"
    token_params.append(limit * 4)

    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, token_params)
            candidates = [dict(r) for r in cur.fetchall()]

    scored = [(row, _relevance_score(row, tokens, query)) for row in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [row for row, _ in scored[:limit]]


def get_product_by_id(product_id: int) -> Optional[dict]:
    """Return a single product record or None if not found."""
    sql = """
        SELECT p.id, p.name, p.description, p.price, p.stock,
               p.rating, p.tags, c.name AS category
        FROM   products p
        JOIN   categories c ON c.id = p.category_id
        WHERE  p.id = %s
    """
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (product_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def get_products_by_category(category: str, limit: int = 10) -> list[dict]:
    """Return top-rated products in a given category."""
    sql = """
        SELECT p.id, p.name, p.description, p.price, p.stock,
               p.rating, p.tags, c.name AS category
        FROM   products p
        JOIN   categories c ON c.id = p.category_id
        WHERE  c.name LIKE %s
        ORDER BY p.rating DESC
        LIMIT %s
    """
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (f"%{category}%", limit))
            return [dict(r) for r in cur.fetchall()]


def get_all_categories() -> list[dict]:
    """Return all available product categories."""
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, name, description FROM categories")
            return [dict(r) for r in cur.fetchall()]


def reduce_stock(product_id: int, quantity: int) -> bool:
    """
    Decrement stock for a product.
    Returns True if successful, False if insufficient stock.
    """
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT stock FROM products WHERE id = %s", (product_id,)
            )
            row = cur.fetchone()
            if not row or row["stock"] < quantity:
                return False
            cur.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (quantity, product_id),
            )
    return True


# ── Personalisation helpers ────────────────────────────────────────────────────


def get_user_purchase_history(user_id: str) -> list[dict]:
    """Return product IDs and names a user has previously purchased."""
    sql = """
        SELECT p.id, p.name, p.category_id, c.name AS category
        FROM   user_purchase_history h
        JOIN   products p ON p.id = h.product_id
        JOIN   categories c ON c.id = p.category_id
        WHERE  h.user_id = %s
        ORDER  BY h.purchased_at DESC
    """
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (user_id,))
            return [dict(r) for r in cur.fetchall()]


def get_similar_products(product_id: int, limit: int = 5) -> list[dict]:
    """
    Return products in the same category as the given product,
    excluding the product itself, sorted by rating.
    """
    sql = """
        SELECT p.id, p.name, p.description, p.price, p.stock,
               p.rating, p.tags, c.name AS category
        FROM   products p
        JOIN   categories c ON c.id = p.category_id
        WHERE  p.category_id = (SELECT category_id FROM products WHERE id = %s)
          AND  p.id != %s
        ORDER  BY p.rating DESC
        LIMIT  %s
    """
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (product_id, product_id, limit))
            return [dict(r) for r in cur.fetchall()]


def get_trending_products(limit: int = 5) -> list[dict]:
    """Return top-rated products across all categories."""
    sql = """
        SELECT p.id, p.name, p.description, p.price, p.stock,
               p.rating, p.tags, c.name AS category
        FROM   products p
        JOIN   categories c ON c.id = p.category_id
        ORDER  BY p.rating DESC
        LIMIT  %s
    """
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (limit,))
            return [dict(r) for r in cur.fetchall()]


def record_purchase_history(user_id: str, product_id: int) -> None:
    """Persist a purchase to the user's history (called after checkout)."""
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO user_purchase_history (user_id, product_id) VALUES (%s, %s)",
                (user_id, product_id),
            )
