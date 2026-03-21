import sqlite3
from typing import Optional

from config import DISCOUNT_CODES
from config_db import CART_DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(CART_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Cart CRUD ──────────────────────────────────────────────────────────────────


def get_or_create_cart(user_id: str) -> int:
    """Return the cart ID for a user, creating one if necessary."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM carts WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return row["id"]
        cursor = conn.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return cursor.lastrowid


def get_cart_contents(user_id: str) -> list[dict]:
    """Return all items currently in the user's cart."""
    sql = """
        SELECT ci.id AS item_id,
               ci.product_id,
               ci.quantity,
               ci.unit_price,
               ci.quantity * ci.unit_price AS subtotal
        FROM   cart_items ci
        JOIN   carts c ON c.id = ci.cart_id
        WHERE  c.user_id = ?
    """
    with _connect() as conn:
        rows = conn.execute(sql, (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_cart_summary(user_id: str) -> dict:
    """Return cart item count and grand total."""
    items = get_cart_contents(user_id)
    total = sum(i["subtotal"] for i in items)
    return {
        "user_id": user_id,
        "item_count": len(items),
        "total": round(total, 2),
        "items": items,
    }


def add_item_to_cart(
    user_id: str, product_id: int, quantity: int, unit_price: float
) -> dict:
    """
    Add a product to the cart.
    If the product already exists, increment its quantity.
    Returns the updated cart summary.
    """
    cart_id = get_or_create_cart(user_id)
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id, quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
            (cart_id, product_id),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE cart_items SET quantity = quantity + ? WHERE id = ?",
                (quantity, existing["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO cart_items (cart_id, product_id, quantity, unit_price)
                   VALUES (?, ?, ?, ?)""",
                (cart_id, product_id, quantity, unit_price),
            )
        conn.execute(
            "UPDATE carts SET updated_at = datetime('now') WHERE id = ?", (cart_id,)
        )
        conn.commit()
    return get_cart_summary(user_id)


def remove_item_from_cart(user_id: str, product_id: int) -> dict:
    """Remove a product line from the cart. Returns updated cart summary."""
    cart_id = get_or_create_cart(user_id)
    with _connect() as conn:
        conn.execute(
            "DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?",
            (cart_id, product_id),
        )
        conn.commit()
    return get_cart_summary(user_id)


def update_item_quantity(user_id: str, product_id: int, quantity: int) -> dict:
    """Set the quantity of a cart item. Removes the item if quantity <= 0."""
    if quantity <= 0:
        return remove_item_from_cart(user_id, product_id)
    cart_id = get_or_create_cart(user_id)
    with _connect() as conn:
        conn.execute(
            "UPDATE cart_items SET quantity = ? WHERE cart_id = ? AND product_id = ?",
            (quantity, cart_id, product_id),
        )
        conn.commit()
    return get_cart_summary(user_id)


def clear_cart(user_id: str) -> None:
    """Remove all items from the user's cart (called after checkout)."""
    cart_id = get_or_create_cart(user_id)
    with _connect() as conn:
        conn.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
        conn.commit()


# ── Discount logic ─────────────────────────────────────────────────────────────


def validate_discount_code(code: str) -> Optional[float]:
    """
    Return the discount fraction (0–1) for a valid code, or None if invalid.
    E.g. 'SAVE10' → 0.10 means 10 % off.
    """
    return DISCOUNT_CODES.get(code.upper())


# ── Checkout / Orders ──────────────────────────────────────────────────────────


def create_order(user_id: str, discount_code: Optional[str] = None) -> dict:
    """
    Convert the current cart into an order record.
    Returns the full order dict including discount breakdown.
    Raises ValueError if the cart is empty or the discount code is invalid.
    """
    summary = get_cart_summary(user_id)
    if summary["item_count"] == 0:
        raise ValueError("Cannot checkout: cart is empty.")

    discount_fraction = 0.0
    if discount_code:
        discount_fraction = validate_discount_code(discount_code)
        if discount_fraction is None:
            raise ValueError(f"Invalid discount code: '{discount_code}'.")

    total = summary["total"]
    discount_amount = round(total * discount_fraction, 2)
    final_amount = round(total - discount_amount, 2)

    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO orders
                   (user_id, total_amount, discount_code, discount_amount, final_amount, status)
               VALUES (?, ?, ?, ?, ?, 'confirmed')""",
            (user_id, total, discount_code, discount_amount, final_amount),
        )
        order_id = cursor.lastrowid

        # Snapshot cart items into order_items
        # (product names must be fetched from products.db separately by the tool layer)
        for item in summary["items"]:
            conn.execute(
                """INSERT INTO order_items
                       (order_id, product_id, product_name, quantity, unit_price)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    order_id,
                    item["product_id"],
                    f"Product #{item['product_id']}",  # name resolved by tool layer
                    item["quantity"],
                    item["unit_price"],
                ),
            )
        conn.commit()

    return {
        "order_id": order_id,
        "user_id": user_id,
        "items": summary["items"],
        "total_amount": total,
        "discount_code": discount_code,
        "discount_amount": discount_amount,
        "final_amount": final_amount,
        "status": "confirmed",
    }


def get_order(order_id: int) -> Optional[dict]:
    """Fetch a single order by ID."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return None
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
        ).fetchall()
    return {**dict(row), "items": [dict(i) for i in items]}


def get_user_orders(user_id: str) -> list[dict]:
    """Return all past orders for a user, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]
