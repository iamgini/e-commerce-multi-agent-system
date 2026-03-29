import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.order_inventory_agent import order_inventory_agent_node

load_dotenv()


def create_test_state(user_query: str) -> dict:
    return {
        "messages": [HumanMessage(content=user_query)],
        "user_id": "test_user",
    }


def main():
    print("\n" + "=" * 70)
    print("QUICK TEST - ORDER & INVENTORY AGENT RETURNED STATE")
    print("=" * 70)

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set, so this state-return test cannot call the LLM.")
        print("Set the key in your .env file, then run this file again.")
        return

    scenarios = [
        ("Stock Query", "Show me the stock for product 1"),
        ("Purchase Order Query", "Create a purchase order for supplier Tech Supplies Ltd"),
        ("Order History Query", "Show my order history"),
    ]

    for scenario_name, query in scenarios:
        print(f"\n{scenario_name}: {query}")
        state = create_test_state(query)
        result = order_inventory_agent_node(state)

        print("Returned keys:", list(result.keys()))
        print("Current agent:", result.get("current_agent"))

        messages = result.get("messages", [])
        if messages:
            message = messages[0]
            content = getattr(message, "content", None)
            tool_calls = getattr(message, "tool_calls", None)

            print("Has message content:", bool(content))
            print("Has tool calls:", bool(tool_calls))

            if content:
                print("Content preview:", str(content)[:200])
            if tool_calls:
                print("Tool calls:", tool_calls)


if __name__ == "__main__":
    main()
