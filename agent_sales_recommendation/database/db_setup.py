import os
import sqlite3

from config_db import (
    CART_DB_PATH,
    DB_DIR,
    PRODUCTS_DB_PATH,
    SEED_CATEGORIES,
    SEED_PRODUCTS,
)

# ── Schema helpers ─────────────────────────────────────────────────────────────


def _create_products_schema(conn: sqlite3.Connection) -> None:
    """Create products and categories tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT,
            description TEXT,
            price       REAL NOTE NULL,
            stock       INTEGER NOT NULL DEFAULT 0,
            category_id INTEGER REFERENCES categories(id),
            rating      REAL DEFAULT 0.0,
            tags        TEXT DEFAULT ''     -- comma-separated tags
            );
            
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT
        );
        
        CREATE TABLE IF NOT EXISTS user_purchase_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            product_id INTEGER REFERENCES products(id),
            purchased_at TEXT DEFAULT (datetime('now'))
        );
    """)


def _create_cart_schema(conn: sqlite3.Connection) -> None:
    """Create cart and orders tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS carts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cart_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_id    INTEGER REFERENCES carts(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL,
            quantity   INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            added_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            total_amount    REAL NOT NULL,
            discount_code   TEXT,
            discount_amount REAL DEFAULT 0.0,
            final_amount    REAL NOT NULL,
            status          TEXT DEFAULT 'pending',
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   INTEGER REFERENCES orders(id),
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity   INTEGER NOT NULL,
            unit_price REAL NOT NULL
        );
    """)


# TODO: Insert the SEED CATEGORIES and SEED PRODUCTS into db_config.py
def seed_products(conn: sqlite3.Connection) -> None:
    """Insert categories and products if they don't already exist."""
    existing = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if existing > 0:
        return  # already seeded

    conn.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        SEED_CATEGORIES,
    )
    conn.executemany(
        """INSERT INTO products
               (name, description, price, stock, category_id, rating, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        SEED_PRODUCTS,
    )
    conn.commit()


# ── Public entry point ─────────────────────────────────────────────────────────


def initialise_databases() -> None:
    """Create schema and seed data for both databases."""
    os.makedirs(DB_DIR, exist_ok=True)

    with sqlite3.connect(PRODUCTS_DB_PATH) as conn:
        _create_products_schema(conn)
        seed_products(conn)
        print(f"[DB] Products database ready → {PRODUCTS_DB_PATH}")

    with sqlite3.connect(CART_DB_PATH) as conn:
        _create_cart_schema(conn)
        print(f"[DB] Cart database ready     → {CART_DB_PATH}")


if __name__ == "__main__":
    initialise_databases()
