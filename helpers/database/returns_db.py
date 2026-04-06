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
              "INSERT INTO returns (order_id, user_id, reason) VALUES (%s, %s, %s) RETURNING id",
              (order_id, user_id, reason)
           )
           return_id = cur.fetchone()[0]
           conn.commit()
        
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


def get_refund_status(order_id: str) -> dict:
    """Get refund status for an order."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT order_id, status FROM refunds WHERE order_id = %s",
                (order_id,)
            )
            row = cur.fetchone()
            if not row:
                return {"error": f"No refund found for order {order_id}"}
            return {
                "order_id": row[0],
                "status": row[1],
                "message": "Refund will be processed within 5-7 business days."
            }

def create_complaint(order_id: str, issue: str) -> dict:
    """File a complaint for an order."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO complaints (order_id, issue) VALUES (%s, %s) RETURNING id",
                (order_id, issue)
            )
            ticket_id = cur.fetchone()[0]
            conn.commit()
            return {
                "ticket_id": f"TICKET-{ticket_id}",
                "status": "open",
                "message": "Your complaint has been filed."
            }