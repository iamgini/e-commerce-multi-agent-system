import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import errors

from config import (
    CART_DB_DSN,
    CHECKPOINTER_DB_DSN,
    MAINTENANCE_DB_DSN,
    ORDER_INVENTORY_DB_DSN,
    PRODUCTS_DB_DSN,
    RETURNS_DB_DSN,
    USERS_DB_DSN,
)
from helpers.database.users_db import encrypt_password
from scripts.seed_data import SEED_CATEGORIES, SEED_PRODUCTS, SEED_USERS

# ── Schema helpers ─────────────────────────────────────────────────────────────


def _create_products_schema(conn: psycopg.Connection) -> None:
    """Create products and categories tables."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id              SERIAL PRIMARY KEY,
                name            TEXT NOT NULL UNIQUE,
                description     TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id              SERIAL PRIMARY KEY,
                name            TEXT,
                description     TEXT,
                price           REAL NOT NULL,
                stock           INTEGER NOT NULL DEFAULT 0,
                category_id     INTEGER REFERENCES categories(id),
                rating          REAL DEFAULT 0.0,
                tags            TEXT DEFAULT ''
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_purchase_history (
                id              SERIAL PRIMARY KEY,
                user_id         TEXT NOT NULL,
                product_id      INTEGER REFERENCES products(id),
                purchased_at    TIMESTAMP DEFAULT NOW()
            );
            """
        )


def _create_cart_schema(conn: psycopg.Connection) -> None:
    """Create cart and orders tables."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS carts (
                id              SERIAL PRIMARY KEY,
                user_id         TEXT NOT NULL UNIQUE,
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cart_items (
                id              SERIAL PRIMARY KEY,
                cart_id         INTEGER REFERENCES carts(id) ON DELETE CASCADE,
                product_id      INTEGER NOT NULL,
                quantity        INTEGER NOT NULL DEFAULT 1,
                unit_price      REAL NOT NULL,
                added_at        TIMESTAMP DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id              SERIAL PRIMARY KEY,
                user_id         TEXT NOT NULL,
                total_amount    REAL NOT NULL,
                discount_code   TEXT,
                discount_amount REAL DEFAULT 0.0,
                final_amount    REAL NOT NULL,
                status          TEXT DEFAULT 'pending',
                created_at      TIMESTAMP DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id              SERIAL PRIMARY KEY,
                order_id        INTEGER REFERENCES orders(id),
                product_id      INTEGER NOT NULL,
                product_name    TEXT NOT NULL,
                quantity        INTEGER NOT NULL,
                unit_price      REAL NOT NULL
            );
            """
        )


def _create_order_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_products (
                id            SERIAL PRIMARY KEY,
                sku           TEXT UNIQUE,
                name          TEXT NOT NULL,
                description   TEXT DEFAULT '',
                stock         INTEGER NOT NULL DEFAULT 0,
                reorder_level INTEGER NOT NULL DEFAULT 10,
                unit_cost     REAL DEFAULT 0.0,
                unit_price    REAL DEFAULT 0.0,
                updated_at    TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS customer_orders (
                id           SERIAL PRIMARY KEY,
                user_id      TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'confirmed',
                total_amount REAL NOT NULL DEFAULT 0.0,
                created_at   TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS customer_order_items (
                id            SERIAL PRIMARY KEY,
                order_id      INTEGER NOT NULL REFERENCES customer_orders(id),
                product_id    INTEGER NOT NULL REFERENCES inventory_products(id),
                product_name  TEXT NOT NULL,
                quantity      INTEGER NOT NULL,
                unit_price    REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS purchase_orders (
                id            SERIAL PRIMARY KEY,
                supplier_name TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'draft',
                expected_date TEXT,
                notes         TEXT DEFAULT '',
                created_at    TIMESTAMP DEFAULT NOW(),
                updated_at    TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS purchase_order_items (
                id                SERIAL PRIMARY KEY,
                purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(id),
                product_id        INTEGER NOT NULL REFERENCES inventory_products(id),
                product_name      TEXT NOT NULL,
                quantity          INTEGER NOT NULL,
                unit_cost         REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS supply_orders (
                id            SERIAL PRIMARY KEY,
                supplier_name TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'draft',
                reference     TEXT DEFAULT '',
                notes         TEXT DEFAULT '',
                created_at    TIMESTAMP DEFAULT NOW(),
                updated_at    TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS supply_order_items (
                id              SERIAL PRIMARY KEY,
                supply_order_id INTEGER NOT NULL REFERENCES supply_orders(id),
                product_id      INTEGER NOT NULL REFERENCES inventory_products(id),
                product_name    TEXT NOT NULL,
                quantity        INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory_movements (
                id             SERIAL PRIMARY KEY,
                product_id     INTEGER NOT NULL REFERENCES inventory_products(id),
                movement_type  TEXT NOT NULL,
                quantity       INTEGER NOT NULL,
                reference_type TEXT DEFAULT '',
                reference_id   INTEGER,
                note           TEXT DEFAULT '',
                created_at     TIMESTAMP DEFAULT NOW()
            );
        """
        )


def _seed_demo_data(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM inventory_products")
        if cur.fetchone()[0] > 0:
            return  # already seeded

        cur.executemany(
            """
            INSERT INTO inventory_products
                (sku, name, description, stock, reorder_level, unit_cost, unit_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                ("LAP-001", "14-inch Laptop", "Mid-range productivity laptop", 25, 8, 550.0, 899.0),
                ("MOU-001", "Wireless Mouse", "Bluetooth mouse", 80, 20, 12.0, 29.99),
                ("KEY-001", "Mechanical Keyboard", "Backlit keyboard", 40, 10, 35.0, 89.99),
                ("MON-001", "27-inch Monitor", "QHD display", 18, 6, 170.0, 299.99),
            ],
        )

        #cur.execute(
        #    "INSERT INTO customer_orders (user_id, status, total_amount) VALUES (%s, %s, %s)",
        #    ("user_123", "delivered", 59.98),
        #)
    
        #order_id = cur.execute("SELECT last_insert_rowid()").fetchone()[0]

        cur.execute(
            """
            INSERT INTO customer_orders (user_id, status, total_amount)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            ("user_123", "delivered", 59.98),
        )
        order_id = cur.fetchone()[0]
    
        cur.executemany(
            """
            INSERT INTO customer_order_items
                (order_id, product_id, product_name, quantity, unit_price)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (order_id, 2, "Wireless Mouse", 2, 29.99),
            ],
        )
    
        cur.execute(
            """
            INSERT INTO inventory_movements
                (product_id, movement_type, quantity, reference_type, reference_id, note)
            VALUES (%s, 'sale_out', %s, 'customer_order', %s, %s)
            """,
            (2, -2, order_id, "Seed demo sale"),
        )


def seed_products(conn: psycopg.Connection) -> None:
    """Insert categories and products if they don't already exist."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] > 0:
            return  # already seeded

        cur.executemany(
            """
            INSERT INTO categories 
                (name, description) 
            VALUES (%s, %s)
            """,
            SEED_CATEGORIES,
        )
        cur.executemany(
            """
            INSERT INTO products
                (name, description, price, stock, category_id, rating, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            SEED_PRODUCTS,
        )
        
def _create_returns_schema(conn: psycopg.Connection) -> None:
    """Create returns, refunds and complaints tables in PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS returns (
                id          SERIAL PRIMARY KEY,
                order_id    TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                reason      TEXT,
                status      TEXT DEFAULT 'created',
                created_at  TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS refunds (
                id          SERIAL PRIMARY KEY,
                order_id    TEXT NOT NULL,
                status      TEXT DEFAULT 'processing',
                created_at  TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id          SERIAL PRIMARY KEY,
                order_id    TEXT NOT NULL,
                issue       TEXT,
                status      TEXT DEFAULT 'open',
                created_at  TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()


def _create_users_schema(conn: psycopg.Connection) -> None:
    """Create users table in PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS citext")    # For case insensitive usernames
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username CITEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            );
        """)


def seed_users(conn: psycopg.Connection) -> None:
    """Insert users if they don't already exist."""
    hashed_users = []
    for username, password in SEED_USERS:
        hashed = encrypt_password(password)
        hashed_users.append((username, hashed))
        
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO users 
                (username, password_hash)
            VALUES (%s, %s)
            ON CONFLICT (username) DO NOTHING;
            """,
            hashed_users,
        )


# ── Entrypoint in main.py ──────────────────────────────────────────────────────


def initialise_databases() -> None:
    """Create schema and seed data for both databases."""
    db_names = [
        "products_db",
        "cart_db",
        "returns_db",
        "order_inventory_db",
        "checkpoints_db",
        "users_db",
        "chainlit_db"
        ]
    
    with psycopg.connect(MAINTENANCE_DB_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            for db_name in db_names:
                try:
                    cur.execute(f'CREATE DATABASE "{db_name}"')
                    print(f"Created database: {db_name}")
                    
                except errors.DuplicateDatabase:
                    print(f"Database: '{db_name}' already exists, skipping creation.")    

    with PostgresSaver.from_conn_string(CHECKPOINTER_DB_DSN) as checkpointer:
        target_db = "checkpoints_db"
        checkpointer.setup()
        print(f"[DB] Checkpoints database ready → {target_db}")

    with psycopg.connect(PRODUCTS_DB_DSN) as conn:
        target_db = "products_db"
        _create_products_schema(conn)
        seed_products(conn)
        print(f"[DB] Products database ready → {target_db}")

    with psycopg.connect(CART_DB_DSN) as conn:
        target_db = "cart_db"
        _create_cart_schema(conn)
        print(f"[DB] Cart database ready → {target_db}")
    
    with psycopg.connect(RETURNS_DB_DSN) as conn:
        target_db = "returns_db"
        _create_returns_schema(conn)
        print(f"[DB] Returns database ready → {target_db}")

    with psycopg.connect(ORDER_INVENTORY_DB_DSN) as conn:
        target_db = "order_inventory_db"
        _create_order_schema(conn)
        _seed_demo_data(conn)
        print(f"[DB] Order & inventory database ready → {target_db}")

    with psycopg.connect(USERS_DB_DSN) as conn:
        target_db = "users_db"
        _create_users_schema(conn)
        seed_users(conn)
        print(f"[DB] User database ready → {target_db}")

if __name__ == "__main__":
    initialise_databases()
