import sys
sys.path.insert(0, '.')

from langchain_core.messages import HumanMessage
from agents.returns_refunds_agent import returns_refunds_agent_node
from state import create_empty_state

test_queries = [
    "Can I return my laptop?",
    "My item arrived damaged",
    "Where is my return?",
    "What's your return policy?",
    "I want a refund"
]

print("=" * 60)
print("RETURNS & REFUNDS AGENT - TESTING")
print("=" * 60)

for query in test_queries:
    print(f"\n User: {query}")
    
    # Create empty state
    state = create_empty_state(user_id="test_user_001")
    
    # Add user message to state (like real system does via coordinator)
    state["messages"].append(HumanMessage(content=query))
    
    # Call agent function
    result = returns_refunds_agent_node(state)
    
    # Extract and display agent response
    if result.get("messages"):
        last_msg = result["messages"][-1]
        response = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        print(f"Agent: {response}")
    
    print("-" * 60)

print("\n All tests completed!")