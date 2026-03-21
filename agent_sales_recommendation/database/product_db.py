import re
import sqlite3
from difflib import SequenceMatcher
from typing import Optional

from config_db import PRODUCTS_DB_PATH

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


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(PRODUCTS_DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name
    return conn


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
        "(p.name LIKE ? OR p.description LIKE ? OR p.tags LIKE ?)" for _ in tokens
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
        sql += " AND c.name LIKE ?"
        token_params.append(f"%{category}%")
    if max_price is not None:
        sql += " AND p.price <= ?"
        token_params.append(max_price)
    if min_rating is not None:
        sql += " AND p.rating >= ?"
        token_params.append(min_rating)

    sql += " LIMIT ?"
    token_params.append(limit * 4)

    with _connect() as conn:
        rows = conn.execute(sql, token_params).fetchall()

    candidates = [dict(r) for r in rows]

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
        WHERE  p.id = ?
    """
    with _connect() as conn:
        row = conn.execute(sql, (product_id,)).fetchone()
    return dict(row) if row else None


def get_products_by_category(category: str, limit: int = 10) -> list[dict]:
    """Return top-rated products in a given category."""
    sql = """
        SELECT p.id, p.name, p.description, p.price, p.stock,
               p.rating, p.tags, c.name AS category
        FROM   products p
        JOIN   categories c ON c.id = p.category_id
        WHERE  c.name LIKE ?
        ORDER BY p.rating DESC
        LIMIT ?
    """
    with _connect() as conn:
        rows = conn.execute(sql, (f"%{category}%", limit)).fetchall()
    return [dict(r) for r in rows]


def get_all_categories() -> list[dict]:
    """Return all available product categories."""
    with _connect() as conn:
        rows = conn.execute("SELECT id, name, description FROM categories").fetchall()
    return [dict(r) for r in rows]


def reduce_stock(product_id: int, quantity: int) -> bool:
    """
    Decrement stock for a product.
    Returns True if successful, False if insufficient stock.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not row or row["stock"] < quantity:
            return False
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (quantity, product_id),
        )
        conn.commit()
    return True


# ── Personalisation helpers ────────────────────────────────────────────────────


def get_user_purchase_history(user_id: str) -> list[dict]:
    """Return product IDs and names a user has previously purchased."""
    sql = """
        SELECT p.id, p.name, p.category_id, c.name AS category
        FROM   user_purchase_history h
        JOIN   products p ON p.id = h.product_id
        JOIN   categories c ON c.id = p.category_id
        WHERE  h.user_id = ?
        ORDER  BY h.purchased_at DESC
    """
    with _connect() as conn:
        rows = conn.execute(sql, (user_id,)).fetchall()
    return [dict(r) for r in rows]


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
        WHERE  p.category_id = (SELECT category_id FROM products WHERE id = ?)
          AND  p.id != ?
        ORDER  BY p.rating DESC
        LIMIT  ?
    """
    with _connect() as conn:
        rows = conn.execute(sql, (product_id, product_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_trending_products(limit: int = 5) -> list[dict]:
    """Return top-rated products across all categories."""
    sql = """
        SELECT p.id, p.name, p.description, p.price, p.stock,
               p.rating, p.tags, c.name AS category
        FROM   products p
        JOIN   categories c ON c.id = p.category_id
        ORDER  BY p.rating DESC
        LIMIT  ?
    """
    with _connect() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(r) for r in rows]


def record_purchase_history(user_id: str, product_id: int) -> None:
    """Persist a purchase to the user's history (called after checkout)."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO user_purchase_history (user_id, product_id) VALUES (?, ?)",
            (user_id, product_id),
        )
        conn.commit()
