import psycopg
from config import RETURNS_DB_DSN

def _connect() -> psycopg.Connection:
    """Connect to returns database."""
    return psycopg.connect(RETURNS_DB_DSN)

def create_return(order_id: str, user_id: str, reason: str) -> dict:
    """Create a return request."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO returns (order_id, user_id, reason) VALUES (%s, %s, %s)",
                (order_id, user_id, reason)
            )
            conn.commit()
            cur.execute("SELECT lastval()")
            return_id = cur.fetchone()[0]
        
    return {
        "return_id": f"RET-{return_id}",
        "status": "created",
        "message": "Return created successfully."
    }

def get_return_status(return_id: int) -> dict:
    """Get return status."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status FROM returns WHERE id = %s",
                (return_id,)
            )
            row = cur.fetchone()
    
    if not row:
        return {"error": f"Return RET-{return_id} not found"}
    
    return {
        "return_id": f"RET-{row[0]}",
        "status": row[1],
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