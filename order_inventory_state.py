from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import HumanMessage


class InventoryMessage(TypedDict):
    sender: str
    content: str
    timestamp: str


class OrderInventoryState(TypedDict):
    user_query: str
    user_id: str
    session_id: str
    query_intent: str
    current_agent: str
    route_to_agent: Optional[str]
    conversation_history: List[InventoryMessage]
    purchase_order_id: Optional[int]
    supply_order_id: Optional[int]
    customer_order_id: Optional[int]
    product_id: Optional[int]
    response: Optional[str]
    tools_used: List[str]
    success: bool
    error_message: Optional[str]
    confidence_score: Optional[float]
    explanation: Optional[str]
    messages: List[Any]


def create_empty_order_inventory_state(
    user_query: str,
    user_id: str = "anonymous",
    session_id: str = "default",
) -> OrderInventoryState:
    return OrderInventoryState(
        user_query=user_query,
        user_id=user_id,
        session_id=session_id,
        query_intent="",
        current_agent="",
        route_to_agent=None,
        conversation_history=[],
        purchase_order_id=None,
        supply_order_id=None,
        customer_order_id=None,
        product_id=None,
        response=None,
        tools_used=[],
        success=False,
        error_message=None,
        confidence_score=None,
        explanation=None,
        messages=[HumanMessage(content=user_query)],
    )


def add_to_inventory_history(
    state: OrderInventoryState,
    sender: str,
    content: str,
) -> OrderInventoryState:
    state["conversation_history"].append(
        InventoryMessage(
            sender=sender,
            content=content,
            timestamp=datetime.now().isoformat(),
        )
    )
    return state
