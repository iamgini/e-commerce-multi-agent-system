import argparse
import sys
import os

from langchain_core.messages import HumanMessage, AIMessage

# Ensure the project root is on the path so all imports resolve
sys.path.insert(0, os.path.dirname(__file__))

from scripts.db_setup import initialise_databases
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


def _make_config(user_id: str) -> dict:
    """
    Build the LangGraph config dict for a given user.

    thread_id ties this invocation to a specific checkpoint row in
    checkpoints.db.  Using user_id as the thread_id means each customer has
    exactly one persistent conversation thread across sessions.
    """
    return {"configurable": {"thread_id": user_id}}


def run_interactive(user_id: str) -> None:
    """Start an interactive terminal session with the multi-agent system."""
    print(f"**Session user: {user_id}**")
    print("**Checkpoint: data/checkpoints.db  (conversation persists)**\n")

    graph = get_graph()
    config = _make_config(user_id)

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

        # Run one turn through the graph
        state_input = {
            "messages": [HumanMessage(content=user_input)],
            "route": "",
            "current_agent": "",
            "user_id": user_id,
        }

        try:
            result = graph.invoke(state_input, config=config)

        except Exception as exc:
            print(f"\n[ERROR] Agent error: {exc}\n")
            continue

        # Extract and display the assistant's reply
        reply = _extract_last_ai_text(result["messages"])
        agent_label = result.get("current_agent", "assistant").replace("_", " ").title()
        print(f"\n[{agent_label}]: {reply}\n")


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

#     demo_thread_id = f"{user_id}_demo"

#     print(BANNER)
#     print(f"[DEMO MODE] user_id={user_id}  thread_id={demo_thread_id}\n")
#     print("─" * 60)

#     graph = get_graph()
#     config = _make_config(demo_thread_id)

#     for turn in demo_turns:
#         print(f"You: {turn}")

#         state_input = {
#             "messages": [HumanMessage(content=turn)],
#             "route": "",
#             "current_agent": "",
#             "user_id": user_id,
#         }

#         result = graph.invoke(state_input, config=config)
#         reply = _extract_last_ai_text(result["messages"])
#         agent_label = result.get("current_agent", "assistant").replace("_", " ").title()
#         print(f"[{agent_label}]: {reply}\n")
#         print("─" * 60)

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
    initialise_databases()

    if args.setup_only:
        print("Database setup complete. Exiting.")
        return

    # if args.demo:
    #     run_demo(args.user)
    # else:
    run_interactive(args.user)


if __name__ == "__main__":
    main()
