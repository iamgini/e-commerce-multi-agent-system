import argparse
import sys
import os

from langchain_core.messages import HumanMessage, AIMessage

# Ensure the project root is on the path so all imports resolve
sys.path.insert(0, os.path.dirname(__file__))

# from database.db_setup import initialise_databases
from graph.workflow import get_graph


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_last_ai_text(messages: list) -> str:
    """Pull the text content from the last AIMessage in the list."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if isinstance(msg.content, str):
                return msg.content
            # content can be a list of blocks (Anthropic format)
            if isinstance(msg.content, list):
                parts = [
                    block.get("text", "")
                    for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                return "\n".join(parts).strip()
    return "(no response)"


def run_interactive(user_id: str) -> None:
    """Start an interactive terminal session with the multi-agent system."""
    print(f"  Session user: {user_id}\n")

    graph = get_graph()

    # Persistent message history for the session
    message_history: list = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\nAssistant: Thank you for shopping with us! Goodbye! 👋\n")
            break

        # Append the new human message
        message_history.append(HumanMessage(content=user_input))

        # Run one turn through the graph
        state_input = {
            "messages": message_history,
            "route": "",
            "current_agent": "",
            "user_id": user_id,
        }

        try:
            # result = graph.invoke(state_input) ## ---- old
            result = graph.invoke(state_input, config={"configurable": {"thread_id": user_id}})

        except Exception as exc:
            print(f"\n[ERROR] Agent error: {exc}\n")
            continue

        # Extract and display the assistant's reply
        reply = _extract_last_ai_text(result["messages"])
        agent_label = result.get("current_agent", "assistant").replace("_", " ").title()
        print(f"\n[{agent_label}]: {reply}\n")

        # Update history with the full result messages (includes tool messages)
        message_history = result["messages"]


# def run_demo(user_id: str) -> None:
#     """
#     Run a scripted demo conversation without user interaction.
#     Useful for testing the full agent pipeline end-to-end.
#     """
#     demo_turns = [
#         "Hi! I'm looking for wireless headphones under $200.",
#         "Can you tell me more about the first one?",
#         "Show me similar products.",
#         "Add the Wireless Noise-Cancelling Headphones to my cart.",
#         "Also add a Yoga Mat Premium.",
#         "Show my cart.",
#         "I have a discount code SAVE10. What would my total be?",
#         "Go ahead and checkout with that discount code.",
#         "Thanks, goodbye!",
#     ]

#     print(BANNER)
#     print(f"  [DEMO MODE] user_id={user_id}\n")
#     print("─" * 60)

#     graph = get_graph()
#     message_history: list = []

#     for turn in demo_turns:
#         print(f"You: {turn}")
#         message_history.append(HumanMessage(content=turn))

#         state_input = {
#             "messages": message_history,
#             "route": "",
#             "current_agent": "",
#             "user_id": user_id,
#         }

#         result = graph.invoke(state_input)
#         reply = _extract_last_ai_text(result["messages"])
#         agent_label = result.get("current_agent", "assistant").replace("_", " ").title()
#         print(f"[{agent_label}]: {reply}\n")
#         print("─" * 60)

#         message_history = result["messages"]

#         if result.get("route") == "finish":
#             break


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="E-Commerce Multi-Agent System")
    parser.add_argument(
        "--user", default="user_001", help="User ID for the session (default: user_001)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a scripted demo instead of interactive mode",
    )
    parser.add_argument(
        "--setup-only", action="store_true", help="Initialise databases and exit"
    )
    args = parser.parse_args()

    # Always ensure databases exist
    # initialise_databases()

    if args.setup_only:
        print("Database setup complete. Exiting.")
        return

    if args.demo:
        run_demo(args.user)
    else:
        run_interactive(args.user)


if __name__ == "__main__":
    main()