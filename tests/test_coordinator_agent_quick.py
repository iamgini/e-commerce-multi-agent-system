import os
import sys

from langchain_core.messages import HumanMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.coordinator import coordinator_node


def run_case(label: str, text: str):
    state = {"messages": [HumanMessage(content=text)]}
    result = coordinator_node(state)
    print(f"{label:20} | {text}")
    print("route ->", result.get("route"))
    print("-" * 80)


if __name__ == "__main__":
    run_case("Recommendation", "Can you recommend a good wireless mouse?")
    run_case("Sales", "Add the keyboard to my cart and show my total")
    run_case("Order Inventory", "Create a purchase order and show low stock items")
    run_case("Support", "I need help with my account")
    run_case("Finish", "Thanks, bye")
