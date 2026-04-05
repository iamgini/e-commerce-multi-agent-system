import json
import os
import sys

from langchain_core.tools import tool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from helpers.database import returns_db
    USE_DB = True
except ImportError:
    USE_DB = False


@tool
def check_return_eligibility(order_id: str, days_old: int) -> str:
    """Check if order is within 30-day return window"""
    if USE_DB:
        result = returns_db.check_eligibility(order_id, days_old)
    else:
        eligible = days_old <= 30
        days_remaining = max(0, 30 - days_old)
        result = {
            "eligible": eligible,
            "days_remaining": days_remaining,
            "message": "Eligible to return." if eligible else "Outside 30-day window."
        }
    return json.dumps(result, indent=2)


@tool
def create_return_request(order_id: str, reason: str) -> str:
    """Create a return request"""
    if USE_DB:
        result = returns_db.create_return(order_id, "test_user", reason)
    else:
        result = {
            "return_id": f"RET-{order_id}",
            "status": "created",
            "message": "Return created successfully."
        }
    return json.dumps(result, indent=2)


@tool
def get_return_status(return_id: str) -> str:
    """Get return status"""
    if USE_DB:
        numeric_id = return_id.replace("RET-", "") if return_id.startswith("RET-") else return_id
        result = returns_db.get_return_status(int(numeric_id))
    else:
        result = {
            "return_id": return_id,
            "status": "in_transit",
            "message": "Your return is being processed."
        }
    return json.dumps(result, indent=2)


@tool
def get_refund_status(order_id: str) -> str:
    """Get refund status"""
    return json.dumps({
        "order_id": order_id,
        "status": "processing",
        "message": "Refund will be processed within 5-7 business days."
    }, indent=2)


@tool
def file_complaint(order_id: str, issue: str) -> str:
    """File a complaint"""
    return json.dumps({
        "ticket_id": f"TICKET-{order_id}",
        "status": "open",
        "message": "Your complaint has been filed."
    }, indent=2)


@tool
def get_return_policy() -> str:
    """Get return policy"""
    return json.dumps({
        "return_window": "30 days",
        "refund_unopened": "100%",
        "refund_used": "80%",
        "refund_damaged": "100%",
        "free_shipping": "Yes",
        "timeline": "5-7 business days"
    }, indent=2)


RETURNS_TOOLS = [
    check_return_eligibility,
    create_return_request,
    get_return_status,
    get_refund_status,
    file_complaint,
    get_return_policy,
]
