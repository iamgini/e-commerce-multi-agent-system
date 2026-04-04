import sqlite3
from typing import Optional

from config import RETURNS_DB_PATH


def _connect() -> sqlite3.Connection:
    """Connect to returns database."""
    conn = sqlite3.connect(RETURNS_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────────


def _create_returns_schema(conn: sqlite3.Connection) -> None:
    """Create minimal returns table."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS returns (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            reason      TEXT,
            status      TEXT DEFAULT 'created',
            created_at  TEXT DEFAULT (datetime('now'))
        );
    """)


# ── CRUD ───────────────────────────────────────────────────────────────────────


def create_return(order_id: str, user_id: str, reason: str) -> dict:
    """Create a return request."""
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO returns (order_id, user_id, reason) VALUES (?, ?, ?)",
            (order_id, user_id, reason)
        )
        conn.commit()
        return_id = cursor.lastrowid
        
    return {
        "return_id": f"RET-{return_id}",
        "status": "created",
        "message": "Return created successfully."
    }


def get_return_status(return_id: int) -> dict:
    """Get return status."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, status FROM returns WHERE id = ?",
            (return_id,)
        ).fetchone()
    
    if not row:
        return {"error": f"Return RET-{return_id} not found"}
    
    return {
        "return_id": f"RET-{row['id']}",
        "status": row["status"],
        "message": "Your return is being processed."
    }


def check_eligibility(order_id: str, days_old: int) -> dict:
    """Check if order is eligible for return."""
    eligible = days_old <= 30
    days_remaining = max(0, 30 - days_old)
    
    return {
        "eligible": eligible,
        "days_remaining": days_remaining,
        "message": "Eligible to return." if eligible else "Outside 30-day window."
    }
