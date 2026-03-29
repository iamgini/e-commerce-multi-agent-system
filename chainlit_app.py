"""
chainlit_app.py — Chainlit UI for the e-commerce multi-agent system.

Drop this file at the project root (same level as main.py and api.py).

Usage:
    uv run chainlit run chainlit_app.py --port 8001

Environment variables (same as the rest of the project):
    OPENAI_API_KEY   — required for OpenAI provider
    LLM_PROVIDER     — "openai" (default) or "ollama"
"""

import asyncio
import os
import sys
from functools import partial

import chainlit as cl
from langchain_core.messages import AIMessage, HumanMessage

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from graph.workflow import get_graph

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_ai_text(messages: list) -> str:
    """Extract text from the last AIMessage (mirrors main.py logic)."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if isinstance(msg.content, str):
                return msg.content
            if isinstance(msg.content, list):
                parts = [
                    block.get("text", "")
                    for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                return "\n".join(parts).strip()
    return "(no response)"


def _agent_label(result: dict) -> str:
    return (
        result.get("current_agent", "Assistant")
        .replace("_", " ")
        .title()
    )


# ---------------------------------------------------------------------------
# Chainlit lifecycle
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    """Called once when a user opens the chat window."""
    cl.user_session.set("message_history", [])
    cl.user_session.set("user_id", "user_001")

    await cl.Message(
        content=(
            "👋 Welcome to **ShopBot** — your e-commerce assistant!\n\n"
            "I can help you with:\n"
            "- 🔍 Product search & recommendations\n"
            "- 🛒 Cart & checkout\n"
            "- 📦 Order & inventory queries\n"
            "- 🔄 Returns & refunds\n"
            "- 🙋 General support\n\n"
            "How can I help you today?"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Called on every user message."""
    history: list = cl.user_session.get("message_history", [])
    user_id: str = cl.user_session.get("user_id", "user_001")

    # Append user turn
    history.append(HumanMessage(content=message.content))

    state_input = {
        "messages": history,
        "route": "",
        "current_agent": "",
        "user_id": user_id,
    }

    # Run the synchronous graph.invoke in a thread so it doesn't
    # block Chainlit's async event loop (Python 3.14 + anyio strict mode)
    async with cl.Step(name="Routing…", show_input=False) as step:
        try:
            graph = get_graph()
            result = await asyncio.to_thread(
                graph.invoke,
                state_input,
                {"configurable": {"thread_id": user_id}},
            )
        except Exception as exc:
            await cl.Message(content=f"⚠️ Error: {exc}").send()
            return
        finally:
            await step.remove()

    # Persist updated history
    cl.user_session.set("message_history", result["messages"])

    reply = _last_ai_text(result["messages"])
    agent = _agent_label(result)
    route = result.get("route", "")

    # Send reply with agent label as author
    await cl.Message(content=reply, author=agent).send()