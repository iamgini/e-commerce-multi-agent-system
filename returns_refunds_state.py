from typing import Optional, List, Dict, Any
from typing import TypedDict
from datetime import datetime


class Message(TypedDict):
    sender: str
    content: str
    timestamp: str


class AgentState(TypedDict):
    
    user_query: str
    
    user_id: str
    
    session_id: str
    
    query_intent: str
    
    current_agent: str
    
    route_to_agent: Optional[str]
    
    conversation_history: List[Message]
    
    current_order_id: Optional[str]
    
    return_id: Optional[str]
    
    return_reason: Optional[str]
    
    return_status: Optional[str]
    
    refund_amount: Optional[float]
    
    product_condition: Optional[str]
    

    customer_info: Optional[Dict[str, Any]]
    
    response: Optional[str]
    
    tools_used: List[str]
    
    success: bool
    
    error_message: Optional[str]

    confidence_score: Optional[float]
    
    explanation: Optional[str]

def create_empty_state(
    user_query: str,
    user_id: str = "anonymous",
    session_id: str = "default"
) -> AgentState:
    
    return AgentState(
        user_query=user_query,
        user_id=user_id,
        session_id=session_id,
        query_intent="",
        current_agent="",
        route_to_agent=None,
        conversation_history=[],
        current_order_id=None,
        return_id=None,
        return_reason=None,
        return_status=None,
        refund_amount=None,
        product_condition=None,
        customer_info=None,
        response=None,
        tools_used=[],
        success=False,
        error_message=None,
        confidence_score=None, 
        explanation=None         
    )


def add_to_history(state: AgentState, sender: str, content: str) -> AgentState:
    message = Message(
        sender=sender,
        content=content,
        timestamp=datetime.now().isoformat()
    )
    state["conversation_history"].append(message)
    return state
