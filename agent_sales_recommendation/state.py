from typing import TypedDict, Annotated, List, Literal, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Overall state of the entire LangGraph system.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    intent: Literal["sales", "recommend", "none"]
    products: Any
