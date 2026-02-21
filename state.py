from typing import TypedDict, Optional

class AgentState(TypedDict):
    user_query: str
    user_id: Optional[str]

    intent: Optional[str]

    response: Optional[str]
    escalate: bool

    confidence: Optional[float]
    explanation: Optional[str]