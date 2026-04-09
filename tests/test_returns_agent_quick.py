import sys
sys.path.insert(0, '.')
from langchain_core.messages import HumanMessage
from agents.returns_refunds_agent import returns_refunds_agent_node
from state import create_empty_state
from langchain_core.runnables import RunnableConfig

test_cases = [
    # (description, query)
    ("Check eligibility",       "Can I return my laptop? I bought it 10 days ago, order ID is ORD-123"),
    ("Damaged item",            "My item arrived damaged, order ID is ORD-456"),
    ("Track return",            "Where is my return? Return ID is RET-789"),
    ("Return policy",           "What's your return policy?"),
    ("Refund status",           "I want a refund for order ORD-123"),
    ("Create return request",   "I want to return my headphones, order ID ORD-999, reason: wrong size"),
]

print("=" * 60)
print("RETURNS & REFUNDS AGENT - TESTING")
print("=" * 60)

for description, query in test_cases:
    print(f"\n[{description}]")
    print(f"User: {query}")

    state = create_empty_state(user_id="test_user_001")
    state["messages"].append(HumanMessage(content=query))

    config = RunnableConfig(configurable={"thread_id": "test_user_001"})
    result = returns_refunds_agent_node(state, config=config)

    if result.get("messages"):
        last_msg = result["messages"][-1]
        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                print(f"Agent: [calls tool] {tc['name']}({tc['args']})")
        else:
            response = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            print(f"Agent: {response}")

    print("-" * 60)

print("\nAll tests completed!")