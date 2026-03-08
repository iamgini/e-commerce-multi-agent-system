from abc import ABC, abstractmethod
from typing import Optional
from state import AgentState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class BaseAgent(ABC):
    
    def __init__(self, agent_name: str, llm_model: str = "gpt-4"):
        self.agent_name = agent_name
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=0.7
        )
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        pass
    
    @abstractmethod
    def invoke(self, state: AgentState) -> AgentState:
        pass
    
    def _add_to_history(self, state: AgentState, content: str) -> None:
        from datetime import datetime
        from state import Message
        
        message = Message(
            sender=self.agent_name,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        state["conversation_history"].append(message)
    
    def _format_conversation_context(self, state: AgentState, max_messages: int = 5) -> str:
        recent = state["conversation_history"][-max_messages:]
        lines = [f"{msg['sender']}: {msg['content']}" for msg in recent]
        return "\n".join(lines)
    
    def _call_llm(self, state: AgentState, prompt: ChatPromptTemplate) -> str:
        chain = prompt | self.llm
        context = self._format_conversation_context(state)
        
        response = chain.invoke({
            "context": context,
            "query": state["user_query"],
            "customer_info": state.get("customer_info", {})
        })
        
        return response.content
