import sqlite3
from typing import Optional

from config_db import ORDER_INVENTORY_DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(ORDER_INVENTORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_product_name(conn: sqlite3.Connection, product_id: int) -> str:
    row = conn.execute(
        "SELECT name FROM inventory_products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"Product with ID {product_id} not found.")
    return row["name"]


def create_purchase_order(
    supplier_name: str,
    items: list[dict],
    status: str = "draft",
    expected_date: Optional[str] = None,
    notes: str = "",
) -> dict:
    """
    Create a purchase order with line items.
    Each item must contain: product_id, quantity, unit_cost.
    """
    if not items:
        raise ValueError("Purchase order must contain at least one item.")

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO purchase_orders (supplier_name, status, expected_date, notes)
            VALUES (?, ?, ?, ?)
            """,
            (supplier_name, status, expected_date, notes),
        )
        purchase_order_id = cursor.lastrowid

        for item in items:
            product_name = _get_product_name(conn, item["product_id"])
            conn.execute(
                """
                INSERT INTO purchase_order_items
                    (purchase_order_id, product_id, product_name, quantity, unit_cost)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    purchase_order_id,
                    item["product_id"],
                    product_name,
                    item["quantity"],
                    item["unit_cost"],
                ),
            )

        conn.execute(
            """
            UPDATE purchase_orders
            SET updated_at = datetime('now')
            WHERE id = ?
            """,
            (purchase_order_id,),
        )
        conn.commit()

    return get_purchase_order(purchase_order_id)


def list_purchase_orders(status: Optional[str] = None) -> list[dict]:
    with _connect() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT * FROM purchase_orders
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM purchase_orders ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def update_purchase_order(
    purchase_order_id: int,
    status: Optional[str] = None,
    expected_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE id = ?",
            (purchase_order_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Purchase order #{purchase_order_id} not found.")

        conn.execute(
            """
            UPDATE purchase_orders
            SET status = COALESCE(?, status),
                expected_date = COALESCE(?, expected_date),
                notes = COALESCE(?, notes),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, expected_date, notes, purchase_order_id),
        )
        conn.commit()

    return get_purchase_order(purchase_order_id)


def get_purchase_order(purchase_order_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE id = ?",
            (purchase_order_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Purchase order #{purchase_order_id} not found.")
        items = conn.execute(
            """
            SELECT product_id, product_name, quantity, unit_cost
            FROM purchase_order_items
            WHERE purchase_order_id = ?
            ORDER BY id
            """,
            (purchase_order_id,),
        ).fetchall()
    return {**dict(row), "items": [dict(i) for i in items]}


def create_supply_order(
    supplier_name: str,
    items: list[dict],
    status: str = "draft",
    reference: str = "",
    notes: str = "",
) -> dict:
    """
    Create a supply order with line items.
    Each item must contain: product_id, quantity.
    """
    if not items:
        raise ValueError("Supply order must contain at least one item.")

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO supply_orders (supplier_name, status, reference, notes)
            VALUES (?, ?, ?, ?)
            """,
            (supplier_name, status, reference, notes),
        )
        supply_order_id = cursor.lastrowid

        for item in items:
            product_name = _get_product_name(conn, item["product_id"])
            conn.execute(
                """
                INSERT INTO supply_order_items
                    (supply_order_id, product_id, product_name, quantity)
                VALUES (?, ?, ?, ?)
                """,
                (
                    supply_order_id,
                    item["product_id"],
                    product_name,
                    item["quantity"],
                ),
            )

        conn.execute(
            """
            UPDATE supply_orders
            SET updated_at = datetime('now')
            WHERE id = ?
            """,
            (supply_order_id,),
        )
        conn.commit()

    return get_supply_order(supply_order_id)


def list_supply_orders(status: Optional[str] = None) -> list[dict]:
    with _connect() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT * FROM supply_orders
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM supply_orders ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def update_supply_order(
    supply_order_id: int,
    status: Optional[str] = None,
    reference: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM supply_orders WHERE id = ?",
            (supply_order_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Supply order #{supply_order_id} not found.")

        conn.execute(
            """
            UPDATE supply_orders
            SET status = COALESCE(?, status),
                reference = COALESCE(?, reference),
                notes = COALESCE(?, notes),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, reference, notes, supply_order_id),
        )
        conn.commit()

    return get_supply_order(supply_order_id)


def get_supply_order(supply_order_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM supply_orders WHERE id = ?",
            (supply_order_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Supply order #{supply_order_id} not found.")
        items = conn.execute(
            """
            SELECT product_id, product_name, quantity
            FROM supply_order_items
            WHERE supply_order_id = ?
            ORDER BY id
            """,
            (supply_order_id,),
        ).fetchall()
    return {**dict(row), "items": [dict(i) for i in items]}


def receive_stock(
    product_id: int,
    quantity: int,
    reference_type: str = "goods_receipt",
    reference_id: Optional[int] = None,
    note: str = "",
) -> dict:
    if quantity <= 0:
        raise ValueError("Received quantity must be greater than zero.")

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, name, stock, reorder_level, unit_cost, unit_price
            FROM inventory_products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Product with ID {product_id} not found.")

        conn.execute(
            """
            UPDATE inventory_products
            SET stock = stock + ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (quantity, product_id),
        )
        conn.execute(
            """
            INSERT INTO inventory_movements
                (product_id, movement_type, quantity, reference_type, reference_id, note)
            VALUES (?, 'stock_in', ?, ?, ?, ?)
            """,
            (product_id, quantity, reference_type, reference_id, note),
        )
        conn.commit()

    return view_stock_by_product(product_id=product_id)


def reduce_stock_on_customer_sale(
    user_id: str,
    items: list[dict],
    total_amount: float = 0.0,
    status: str = "confirmed",
) -> dict:
    """
    Create a customer order and reduce stock.
    Each item must contain: product_id, quantity.
    """
    if not items:
        raise ValueError("Customer order must contain at least one item.")

    with _connect() as conn:
        prepared_items = []
        computed_total = 0.0

        for item in items:
            row = conn.execute(
                """
                SELECT id, name, stock, unit_price
                FROM inventory_products
                WHERE id = ?
                """,
                (item["product_id"],),
            ).fetchone()
            if not row:
                raise ValueError(f"Product with ID {item['product_id']} not found.")

            quantity = int(item["quantity"])
            if quantity <= 0:
                raise ValueError("Sale quantity must be greater than zero.")
            if row["stock"] < quantity:
                raise ValueError(
                    f"Insufficient stock for {row['name']}. Available: {row['stock']}, requested: {quantity}."
                )

            line_total = round(row["unit_price"] * quantity, 2)
            computed_total += line_total
            prepared_items.append(
                {
                    "product_id": row["id"],
                    "product_name": row["name"],
                    "quantity": quantity,
                    "unit_price": row["unit_price"],
                }
            )

        order_total = round(total_amount or computed_total, 2)
        cursor = conn.execute(
            """
            INSERT INTO customer_orders (user_id, status, total_amount)
            VALUES (?, ?, ?)
            """,
            (user_id, status, order_total),
        )
        order_id = cursor.lastrowid

        for item in prepared_items:
            conn.execute(
                """
                INSERT INTO customer_order_items
                    (order_id, product_id, product_name, quantity, unit_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["product_name"],
                    item["quantity"],
                    item["unit_price"],
                ),
            )
            conn.execute(
                """
                UPDATE inventory_products
                SET stock = stock - ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (item["quantity"], item["product_id"]),
            )
            conn.execute(
                """
                INSERT INTO inventory_movements
                    (product_id, movement_type, quantity, reference_type, reference_id, note)
                VALUES (?, 'sale_out', ?, 'customer_order', ?, ?)
                """,
                (
                    item["product_id"],
                    -item["quantity"],
                    order_id,
                    f"Customer sale for user {user_id}",
                ),
            )

        conn.commit()

    return get_order(order_id)


def view_stock_by_product(
    product_id: Optional[int] = None,
    query: Optional[str] = None,
    low_stock_only: bool = False,
) -> dict | list[dict]:
    base_sql = """
        SELECT id, sku, name, description, stock, reorder_level, unit_cost, unit_price, updated_at,
               CASE WHEN stock <= reorder_level THEN 1 ELSE 0 END AS low_stock
        FROM inventory_products
    """
    conditions = []
    params: list = []

    if product_id is not None:
        conditions.append("id = ?")
        params.append(product_id)

    if query:
        conditions.append("(name LIKE ? OR sku LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

    if low_stock_only:
        conditions.append("stock <= reorder_level")

    if conditions:
        base_sql += " WHERE " + " AND ".join(conditions)

    base_sql += " ORDER BY name"

    with _connect() as conn:
        rows = conn.execute(base_sql, params).fetchall()

    results = [dict(r) for r in rows]
    if product_id is not None:
        if not results:
            raise ValueError(f"Product with ID {product_id} not found.")
        return results[0]
    return results


def get_order(order_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM customer_orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Order #{order_id} not found.")
        items = conn.execute(
            """
            SELECT product_id, product_name, quantity, unit_price
            FROM customer_order_items
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,),
        ).fetchall()
    return {**dict(row), "items": [dict(i) for i in items]}


def get_user_orders(user_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM customer_orders
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]
