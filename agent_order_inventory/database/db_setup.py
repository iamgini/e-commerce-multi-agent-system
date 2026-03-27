import os
import sqlite3

from config_db import DB_DIR, ORDER_INVENTORY_DB_PATH


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS inventory_products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sku           TEXT UNIQUE,
            name          TEXT NOT NULL,
            description   TEXT DEFAULT '',
            stock         INTEGER NOT NULL DEFAULT 0,
            reorder_level INTEGER NOT NULL DEFAULT 10,
            unit_cost     REAL DEFAULT 0.0,
            unit_price    REAL DEFAULT 0.0,
            updated_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS customer_orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'confirmed',
            total_amount REAL NOT NULL DEFAULT 0.0,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS customer_order_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id      INTEGER NOT NULL REFERENCES customer_orders(id),
            product_id    INTEGER NOT NULL REFERENCES inventory_products(id),
            product_name  TEXT NOT NULL,
            quantity      INTEGER NOT NULL,
            unit_price    REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'draft',
            expected_date TEXT,
            notes         TEXT DEFAULT '',
            created_at    TEXT DEFAULT (datetime('now')),
            updated_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(id),
            product_id        INTEGER NOT NULL REFERENCES inventory_products(id),
            product_name      TEXT NOT NULL,
            quantity          INTEGER NOT NULL,
            unit_cost         REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS supply_orders (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'draft',
            reference     TEXT DEFAULT '',
            notes         TEXT DEFAULT '',
            created_at    TEXT DEFAULT (datetime('now')),
            updated_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS supply_order_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            supply_order_id INTEGER NOT NULL REFERENCES supply_orders(id),
            product_id      INTEGER NOT NULL REFERENCES inventory_products(id),
            product_name    TEXT NOT NULL,
            quantity        INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inventory_movements (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id     INTEGER NOT NULL REFERENCES inventory_products(id),
            movement_type  TEXT NOT NULL,
            quantity       INTEGER NOT NULL,
            reference_type TEXT DEFAULT '',
            reference_id   INTEGER,
            note           TEXT DEFAULT '',
            created_at     TEXT DEFAULT (datetime('now'))
        );
    """)


def _seed_demo_data(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) FROM inventory_products").fetchone()[0]
    if existing > 0:
        return

    conn.executemany(
        """
        INSERT INTO inventory_products
            (sku, name, description, stock, reorder_level, unit_cost, unit_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("LAP-001", "14-inch Laptop", "Mid-range productivity laptop", 25, 8, 550.0, 899.0),
            ("MOU-001", "Wireless Mouse", "Bluetooth mouse", 80, 20, 12.0, 29.99),
            ("KEY-001", "Mechanical Keyboard", "Backlit keyboard", 40, 10, 35.0, 89.99),
            ("MON-001", "27-inch Monitor", "QHD display", 18, 6, 170.0, 299.99),
        ],
    )

    conn.execute(
        "INSERT INTO customer_orders (user_id, status, total_amount) VALUES (?, ?, ?)",
        ("user_123", "delivered", 59.98),
    )
    order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.executemany(
        """
        INSERT INTO customer_order_items
            (order_id, product_id, product_name, quantity, unit_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (order_id, 2, "Wireless Mouse", 2, 29.99),
        ],
    )
    conn.execute(
        """
        INSERT INTO inventory_movements
            (product_id, movement_type, quantity, reference_type, reference_id, note)
        VALUES (?, 'sale_out', ?, 'customer_order', ?, ?)
        """,
        (2, -2, order_id, "Seed demo sale"),
    )
    conn.commit()


def initialise_database() -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(ORDER_INVENTORY_DB_PATH) as conn:
        _create_schema(conn)
        _seed_demo_data(conn)
        conn.commit()
    print(f"[DB] Order & inventory database ready -> {ORDER_INVENTORY_DB_PATH}")


if __name__ == "__main__":
    initialise_database()
