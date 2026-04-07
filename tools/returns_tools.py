import json
import os
import sys
from typing import Annotated
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool
import logging
from helpers.observability.log_formatting import tool_tracing

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

try:
    from helpers.database import returns_db
    USE_DB = True
except ImportError:
    USE_DB = False


@tool
@tool_tracing
def check_return_eligibility(order_id: str, days_old: int,config: RunnableConfig) -> str:
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
@tool_tracing
def create_return_request(
    config: RunnableConfig,
    user_id: Annotated[str, InjectedState("user_id")],
    order_id: str,
    reason: str,
) -> str:
    """Create a return request"""
    if USE_DB:
        result = returns_db.create_return(order_id, user_id, reason)
    else:
        result = {
            "return_id": f"RET-{order_id}",
            "status": "created",
            "message": "Return created successfully."
        }
    return json.dumps(result, indent=2)


@tool
@tool_tracing
def get_return_status(return_id: str,config: RunnableConfig) -> str:
    """Get return status"""
    if USE_DB:
       try:
         numeric_id = return_id.replace("RET-", "").replace("ORD-", "")
         result = returns_db.get_return_status(int(numeric_id))
       except ValueError:
        result = {"error": f"Invalid return ID format: {return_id}"}
    else:
        result = {
            "return_id": return_id,
            "status": "in_transit",
            "message": "Your return is being processed."
        }
    return json.dumps(result, indent=2)


@tool
@tool_tracing
def get_return_policy(config: RunnableConfig) -> str:
    """Get return policy"""
    return json.dumps({
        "return_window": "30 days",
        "refund_unopened": "100%",
        "refund_used": "80%",
        "refund_damaged": "100%",
        "free_shipping": "Yes",
        "timeline": "5-7 business days"
    }, indent=2)

@tool
@tool_tracing
def get_refund_status(order_id: str, config: RunnableConfig) -> str:
    """Get refund status"""
    if USE_DB:
        result = returns_db.get_refund_status(order_id)
    else:
        result = {
            "order_id": order_id,
            "status": "processing",
            "message": "Refund will be processed within 5-7 business days."
        }
    return json.dumps(result, indent=2)

@tool
@tool_tracing
def file_complaint(order_id: str, issue: str, config: RunnableConfig) -> str:
    """File a complaint"""
    if USE_DB:
        result = returns_db.create_complaint(order_id, issue)
    else:
        result = {
            "ticket_id": f"TICKET-{order_id}",
            "status": "open",
            "message": "Your complaint has been filed."
        }
    return json.dumps(result, indent=2)


RETURNS_TOOLS = [
    check_return_eligibility,
    create_return_request,
    get_return_status,
    get_refund_status,
    file_complaint,
    get_return_policy,
]
