from typing import Optional

import psycopg
from psycopg.rows import dict_row

from config import ORDER_INVENTORY_DB_DSN


def _connect() -> psycopg.Connection:
    return psycopg.connect(ORDER_INVENTORY_DB_DSN)


def _get_product_name(conn: psycopg.Connection, product_id: int) -> str:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT name FROM inventory_products WHERE id = %s",
            (product_id,),
        )
        row = cur.fetchone()
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
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO purchase_orders (supplier_name, status, expected_date, notes)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (supplier_name, status, expected_date, notes),
            )
            purchase_order_id = cur.fetchone()["id"]

        for item in items:
            product_name = _get_product_name(conn, item["product_id"])
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO purchase_order_items
                        (purchase_order_id, product_id, product_name, quantity, unit_cost)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        purchase_order_id,
                        item["product_id"],
                        product_name,
                        item["quantity"],
                        item["unit_cost"],
                    ),
                )

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE purchase_orders
                SET updated_at = NOW()
                WHERE id = %s
                """,
                (purchase_order_id,),
            )

    return get_purchase_order(purchase_order_id)


def list_purchase_orders(status: Optional[str] = None) -> list[dict]:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if status:
                cur.execute(
                    """
                    SELECT * FROM purchase_orders
                    WHERE status = %s
                    ORDER BY created_at DESC
                    """,
                    (status,),
                )
            else:
                cur.execute("SELECT * FROM purchase_orders ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def update_purchase_order(
    purchase_order_id: int,
    status: Optional[str] = None,
    expected_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM purchase_orders WHERE id = %s",
                (purchase_order_id,),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Purchase order #{purchase_order_id} not found.")

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE purchase_orders
                SET status = COALESCE(%s, status),
                    expected_date = COALESCE(%s, expected_date),
                    notes = COALESCE(%s, notes),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, expected_date, notes, purchase_order_id),
            )

    return get_purchase_order(purchase_order_id)


def get_purchase_order(purchase_order_id: int) -> dict:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM purchase_orders WHERE id = %s",
                (purchase_order_id,),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Purchase order #{purchase_order_id} not found.")

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT product_id, product_name, quantity, unit_cost
                FROM purchase_order_items
                WHERE purchase_order_id = %s
                ORDER BY id
                """,
                (purchase_order_id,),
            )
            items = cur.fetchall()
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
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO supply_orders (supplier_name, status, reference, notes)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (supplier_name, status, reference, notes),
            )
            supply_order_id = cur.fetchone()["id"]

        for item in items:
            product_name = _get_product_name(conn, item["product_id"])
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO supply_order_items
                        (supply_order_id, product_id, product_name, quantity)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        supply_order_id,
                        item["product_id"],
                        product_name,
                        item["quantity"],
                    ),
                )

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE supply_orders
                SET updated_at = NOW()
                WHERE id = %s
                """,
                (supply_order_id,),
            )

    return get_supply_order(supply_order_id)


def list_supply_orders(status: Optional[str] = None) -> list[dict]:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if status:
                cur.execute(
                    """
                    SELECT * FROM supply_orders
                    WHERE status = %s
                    ORDER BY created_at DESC
                    """,
                    (status,),
                )
            else:
                cur.execute("SELECT * FROM supply_orders ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def update_supply_order(
    supply_order_id: int,
    status: Optional[str] = None,
    reference: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM supply_orders WHERE id = %s",
                (supply_order_id,),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Supply order #{supply_order_id} not found.")

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE supply_orders
                SET status = COALESCE(%s, status),
                    reference = COALESCE(%s, reference),
                    notes = COALESCE(%s, notes),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (status, reference, notes, supply_order_id),
            )

    return get_supply_order(supply_order_id)


def get_supply_order(supply_order_id: int) -> dict:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM supply_orders WHERE id = %s",
                (supply_order_id,),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Supply order #{supply_order_id} not found.")

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT product_id, product_name, quantity
                FROM supply_order_items
                WHERE supply_order_id = %s
                ORDER BY id
                """,
                (supply_order_id,),
            )
            items = cur.fetchall()
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
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, name, stock, reorder_level, unit_cost, unit_price
                FROM inventory_products
                WHERE id = %s
                """,
                (product_id,),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Product with ID {product_id} not found.")

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE inventory_products
                SET stock = stock + %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (quantity, product_id),
            )
            cur.execute(
                """
                INSERT INTO inventory_movements
                    (product_id, movement_type, quantity, reference_type, reference_id, note)
                VALUES (%s, 'stock_in', %s, %s, %s, %s)
                """,
                (product_id, quantity, reference_type, reference_id, note),
            )

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
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, name, stock, unit_price
                    FROM inventory_products
                    WHERE id = %s
                    """,
                    (item["product_id"],),
                )
                row = cur.fetchone()
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
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO customer_orders (user_id, status, total_amount)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (user_id, status, order_total),
            )
            order_id = cur.fetchone()["id"]

        for item in prepared_items:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO customer_order_items
                        (order_id, product_id, product_name, quantity, unit_price)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        order_id,
                        item["product_id"],
                        item["product_name"],
                        item["quantity"],
                        item["unit_price"],
                    ),
                )
                cur.execute(
                    """
                    UPDATE inventory_products
                    SET stock = stock - %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (item["quantity"], item["product_id"]),
                )
                cur.execute(
                    """
                    INSERT INTO inventory_movements
                        (product_id, movement_type, quantity, reference_type, reference_id, note)
                    VALUES (%s, 'sale_out', %s, 'customer_order', %s, %s)
                    """,
                    (
                        item["product_id"],
                        -item["quantity"],
                        order_id,
                        f"Customer sale for user {user_id}",
                    ),
                )

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
        conditions.append("id = %s")
        params.append(product_id)

    if query:
        conditions.append("(name ILIKE %s OR sku ILIKE %s)")
        params.extend([f"%{query}%", f"%{query}%"])

    if low_stock_only:
        conditions.append("stock <= reorder_level")

    if conditions:
        base_sql += " WHERE " + " AND ".join(conditions)

    base_sql += " ORDER BY name"

    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(base_sql, params)
            rows = cur.fetchall()

    results = [dict(r) for r in rows]
    if product_id is not None:
        if not results:
            raise ValueError(f"Product with ID {product_id} not found.")
        return results[0]
    return results


def get_order(order_id: int) -> dict:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM customer_orders WHERE id = %s",
                (order_id,),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Order #{order_id} not found.")

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT product_id, product_name, quantity, unit_price
                FROM customer_order_items
                WHERE order_id = %s
                ORDER BY id
                """,
                (order_id,),
            )
            items = cur.fetchall()
    return {**dict(row), "items": [dict(i) for i in items]}


def get_user_orders(user_id: str) -> list[dict]:
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM customer_orders
                WHERE user_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [dict(r) for r in rows]
