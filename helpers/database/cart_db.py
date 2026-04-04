from typing import Optional

import psycopg
from psycopg.rows import dict_row

from config import CART_DB_DSN, DISCOUNT_CODES


def _connect() -> psycopg.Connection:
    return psycopg.connect(CART_DB_DSN)


# ── Cart CRUD ──────────────────────────────────────────────────────────────────


def get_or_create_cart(user_id: str) -> int:
    """Return the cart ID for a user, creating one if necessary."""
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM carts WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        if row:
            return row["id"]
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO carts (user_id) VALUES (%s) RETURNING id", (user_id,)
            )
            return cur.fetchone()["id"]


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
        WHERE  c.user_id = %s
    """
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()
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
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, quantity FROM cart_items WHERE cart_id = %s AND product_id = %s",
                (cart_id, product_id),
            )
            existing = cur.fetchone()
        if existing:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "UPDATE cart_items SET quantity = quantity + %s WHERE id = %s",
                    (quantity, existing["id"]),
                )
        else:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """INSERT INTO cart_items (cart_id, product_id, quantity, unit_price)
                       VALUES (%s, %s, %s, %s)""",
                    (cart_id, product_id, quantity, unit_price),
                )
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("UPDATE carts SET updated_at = NOW() WHERE id = %s", (cart_id,))
    return get_cart_summary(user_id)


def remove_item_from_cart(user_id: str, product_id: int) -> dict:
    """Remove a product line from the cart. Returns updated cart summary."""
    cart_id = get_or_create_cart(user_id)
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "DELETE FROM cart_items WHERE cart_id = %s AND product_id = %s",
                (cart_id, product_id),
            )
    return get_cart_summary(user_id)


def update_item_quantity(user_id: str, product_id: int, quantity: int) -> dict:
    """Set the quantity of a cart item. Removes the item if quantity <= 0."""
    if quantity <= 0:
        return remove_item_from_cart(user_id, product_id)
    cart_id = get_or_create_cart(user_id)
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "UPDATE cart_items SET quantity = %s WHERE cart_id = %s AND product_id = %s",
                (quantity, cart_id, product_id),
            )
    return get_cart_summary(user_id)


def clear_cart(user_id: str) -> None:
    """Remove all items from the user's cart (called after checkout)."""
    cart_id = get_or_create_cart(user_id)
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart_id,))


# ── Discount logic ─────────────────────────────────────────────────────────────


def validate_discount_code(code: str) -> Optional[float]:
    """
    Return the discount fraction (0-1) for a valid code, or None if invalid.
    E.g. 'SAVE10' → 0.10 means 10 % off.
    """
    return DISCOUNT_CODES.get(code.upper())


# ── Checkout / Orders ──────────────────────────────────────────────────────────


def create_order(
    user_id: str,
    discount_code: Optional[str] = None,
    product_names: Optional[dict] = None,
) -> dict:
    """
    Convert the current cart into an order record.

    Args:
        user_id:       The customer placing the order.
        discount_code: Optional promo code; validated before use.
        product_names: Mapping of {product_id: product_name} supplied by the
                       checkout tool, which already fetched product records
                       during stock validation. If a product_id is missing
                       from this dict the name falls back to "Product #<id>".

    Returns the full order dict including discount breakdown.
    Raises ValueError if the cart is empty or the discount code is invalid.
    """
    product_names = product_names or {}

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
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """INSERT INTO orders
                       (user_id, total_amount, discount_code, discount_amount, final_amount, status)
                   VALUES (%s, %s, %s, %s, %s, 'confirmed')
                   RETURNING id""",
                (user_id, total, discount_code, discount_amount, final_amount),
            )
            order_id = cur.fetchone()["id"]

        # Snapshot cart items into order_items
        # (product names must be fetched from products.db separately by the tool layer)
        for item in summary["items"]:
            pid = item["product_id"]
            name = product_names.get(pid, f"Product #{pid}")
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """INSERT INTO order_items
                           (order_id, product_id, product_name, quantity, unit_price)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        order_id,
                        pid,
                        name,
                        item["quantity"],
                        item["unit_price"],
                    ),
                )

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
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            row = cur.fetchone()
        if not row:
            return None
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
            items = cur.fetchall()
    return {**dict(row), "items": [dict(i) for i in items]}


def get_user_orders(user_id: str) -> list[dict]:
    """Return all past orders for a user, newest first."""
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
    return [dict(r) for r in rows]
