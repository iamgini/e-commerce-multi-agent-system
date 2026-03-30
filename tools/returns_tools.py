import json
from langchain_core.tools import tool

@tool
def check_return_eligibility(order_id: str, days_old: int) -> str:
    """Check if order is within 30-day return window"""
    eligible = days_old <= 30
    days_remaining = max(0, 30 - days_old)
    return json.dumps({
        "order_id": order_id,
        "eligible": eligible,
        "days_remaining": days_remaining,
        "message": f"Order is {days_old} days old. {'Eligible to return.' if eligible else 'Outside return window.'}"
    })

@tool
def create_return_request(order_id: str, reason: str) -> str:
    """Create a return request"""
    return json.dumps({
        "return_id": f"RET-{order_id}",
        "status": "created",
        "message": f"Return created. You'll receive a return label via email."
    })

@tool
def get_return_status(return_id: str) -> str:
    """Get return status"""
    return json.dumps({
        "return_id": return_id,
        "status": "in_transit",
        "message": "Your return is on the way to our warehouse."
    })

@tool
def get_refund_status(order_id: str) -> str:
    """Get refund status"""
    return json.dumps({
        "order_id": order_id,
        "status": "processing",
        "message": "Refund will be processed within 5-7 business days."
    })

@tool
def file_complaint(order_id: str, issue: str) -> str:
    """File a complaint"""
    return json.dumps({
        "ticket_id": f"TICKET-{order_id}",
        "status": "open",
        "message": "Your complaint has been filed. We'll investigate."
    })

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
    })

RETURNS_TOOLS = [
    check_return_eligibility,
    create_return_request,
    get_return_status,
    get_refund_status,
    file_complaint,
    get_return_policy,
]
