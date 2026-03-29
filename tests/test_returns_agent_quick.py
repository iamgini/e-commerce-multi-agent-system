import os
import sys

# from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.returns_refunds import ReturnsRefundsAgent
from state import AgentState

# load_dotenv()
agent = ReturnsRefundsAgent()


def create_test_state(user_query: str) -> AgentState:
    return AgentState(
        user_query=user_query,
        user_id="test_user",
        session_id="test_session",
        query_intent="",
        current_agent="",
        route_to_agent=None,
        conversation_history=[],
        current_order_id="ORD_001",
        return_id=None,
        return_reason=None,
        return_status=None,
        refund_amount=None,
        product_condition=None,
        customer_info={"name": "Test"},
        response=None,
        tools_used=[],
        success=False,
        error_message=None,
        confidence_score=None,
        explanation=None,
    )


def main():
    print("\n" + "=" * 70)
    print("QUICK TEST - 1 SCENARIO ONLY")
    print("=" * 70)

    scenarios = [
        ("Return Policy Question", "What is your return policy?"),
    ]

    for scenario_name, query in scenarios:
        print(f"\n{scenario_name}: {query}")
        state = create_test_state(query)
        result = agent.invoke(state)

        print(f"Response: {result['response'][:100]}...")
        print(f"Success: {result['success']}")
        print(f"Confidence: {result.get('confidence_score')}")
        print(f"Explanation: {result.get('explanation')}")


if __name__ == "__main__":
    main()
