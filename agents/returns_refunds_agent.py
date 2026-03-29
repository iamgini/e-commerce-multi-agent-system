import logging
import os
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import LLM_MODEL, LLM_TEMPERATURE, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def returns_refunds_agent_node(state: dict) -> dict:
    """
    Returns & Refunds Agent - Handle returns, refunds, and complaints.
    
    Responsibilities:
    1. Help customers check return eligibility
    2. Process returns and initiate refunds  
    3. Track return status
    4. Handle damage complaints
    5. Provide return policy information
    
    Args:
        state: The current AgentState containing messages and context
        
    Returns:
        Updated AgentState with agent response added
    """
    try:
        # Update current agent in state
        state["current_agent"] = "Returns & Refunds Agent"
        
        # Get user query from state
        user_query = state.get("user_query", "")
        if not user_query and state.get("messages"):
            # Fallback: extract from last HumanMessage
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    user_query = msg.content
                    break
        
        logger.info(f"Processing returns query: {user_query[:60]}...")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            api_key=OPENAI_API_KEY,
        )
        
        # System prompt with return policy and guidelines
        system_prompt = """You are a Returns & Refunds Agent for an e-commerce platform.

Your responsibilities:
1. Help customers check return eligibility
2. Process returns and initiate refunds  
3. Track return status
4. Handle damage complaints
5. Provide return policy information

Return Policy:
- Return Window: 30 days from purchase
- Refund by Condition:
  * Unopened: 100% refund
  * Used: 80% refund
  * Damaged by us: 100% refund
  * Defective: 100% refund
- Free return shipping
- Refund Timeline: 5-7 business days after inspection

When responding:
1. Be empathetic and professional
2. Understand customer needs clearly
3. Provide clear next steps
4. Offer solutions and alternatives
5. Be helpful and solution-oriented"""
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """Customer Query: {query}

Please help this customer with their returns/refunds inquiry.
1. Understand their need
2. Check eligibility if needed
3. Provide clear guidance
4. Be empathetic for complaints""")
        ])
        
        # Build chain and invoke
        chain = prompt | llm
        response = chain.invoke({
            "query": user_query or "Hello",
            "context": ""
        })
        
        # Extract response text
        response_text = response.content
        
        # Add agent response to messages
        state["messages"].append(AIMessage(
            content=response_text,
            name="returns_refunds_agent"
        ))
        
        logger.info(f"Returns agent response: {response_text[:100]}...")
        
    except Exception as e:
        logger.error(f"Error in returns agent: {str(e)}", exc_info=True)
        error_msg = f"I encountered an error processing your request: {str(e)}"
        state["messages"].append(AIMessage(
            content=error_msg,
            name="returns_refunds_agent"
        ))
    
    return state
