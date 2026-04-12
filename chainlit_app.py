"""api.py
chainlit_app.py — Chainlit UI for the e-commerce multi-agent system.

Usage:
    uv run chainlit run chainlit_app.py --port 8001

Environment variables (same as the rest of the project):
    OPENAI_API_KEY   — required for OpenAI provider
    LLM_PROVIDER     — "openai" (default) or "ollama"
"""

import asyncio
import logging
import os
import sys

import chainlit as cl
from chainlit.types import ThreadDict
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, os.path.dirname(__file__))

from graph.chainlit_workflow import get_graph
from helpers.database.users_db import get_user, verify_password
from scripts.db_setup import initialise_databases
from scripts.logger_setup import initialise_logger
from scripts.guardrails_setup import initialize_guardrails

initialize_guardrails()
initialise_databases()
# logger = logging.getLogger(__name__)


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


# def _agent_label(result: dict) -> str:
#     return (
#         result.get("current_agent", "Assistant")
#         .replace("_", " ")
#         .title()
#     )


# ---------------------------------------------------------------------------
# Chainlit lifecycle
# ---------------------------------------------------------------------------


@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    user = get_user(username.strip())

    if not user:
        return None     # Authentication failed

    username, password_hash = user

    if verify_password(password, password_hash):
        return cl.User(
            identifier=username,
            metadata={"role": "user"}
        )

    return None


@cl.on_chat_start
async def on_chat_start():
    """Called once when a user opens the chat window."""

    ## Apply logging configurations
    global logger
    initialise_logger()
    logger = logging.getLogger(__name__)
    
    # Get the current thread ID from the session
    thread_id = cl.user_session.get("id")
    
    # Get user details from auth callback
    user = cl.user_session.get("user")
    
    if user:
        user_id = user.identifier  
        role = user.metadata.get("role", "user")
    else:
        user_id = "anonymous"   # Should not trigger unless auth goes wrong
        role = "guest"
    
    # Set user session
    cl.user_session.set("user_id", user_id)
    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("role", role)
    cl.user_session.set("message_history", [])

    await cl.Message(
        content=(
            f"👋 Hello {user_id.capitalize()}. Welcome to **ShopBot** — your e-commerce assistant!\n\n"
            "I can help you with:\n"
            "- 🔍 Product search & recommendations\n"
            "- 🛒 Cart & checkout\n"
            "- 📦 Order & inventory queries\n"
            "- 🔄 Returns & refunds\n"
            "- 🙋 General support\n\n"
            "How can I help you today?"
        )
    ).send()


## Working batched
# @cl.on_message
# async def on_message(message: cl.Message):
#     """Called on every user message."""
#     history: list = cl.user_session.get("message_history", [])
#     user_id: str = cl.user_session.get("user_id", "user_001")
#     session_id: str = cl.user_session.get("session_id", f"{user_id}_{int(time.time())}")
    
#     # logger.info(message.content) 
    
#     # Append user turn
#     history.append(HumanMessage(content=message.content))

#     state_input = {
#         "messages": history,
#         "route": "",
#         "current_agent": "",
#         "user_id": user_id,
#         "session_id": session_id,
#     }

#     # Run the synchronous graph.invoke in a thread so it doesn't
#     # block Chainlit's async event loop (Python 3.14 + anyio strict mode)
#     async with cl.Step(name="Routing…", show_input=False) as step:
#         try:
#             graph = get_graph()

#             result = await asyncio.to_thread(
#                 graph.invoke,
#                 state_input,
#                 {"configurable": {
#                     "user_id": user_id,
#                     "thread_id": session_id,
#                     }
#                  },
#             )

#         except Exception as exc:
#             await cl.Message(content=f"⚠️ Error: {exc}").send()
#             logger.error(f"\n[ERROR] Agent error: {exc}\n")
#             return
        
#         finally:
#             await step.remove()

#     # Persist updated history
#     cl.user_session.set("message_history", result["messages"])

#     reply = _last_ai_text(result["messages"])
#     agent = _agent_label(result)
#     route = result.get("route", "")

#     # Send reply with agent label as author
#     await cl.Message(content=reply, author=agent).send()


### Working streaming
@cl.on_message
async def on_message(message: cl.Message):
    """Called on every user message."""
    history: list = cl.user_session.get("message_history", [])
    user_id: str =  cl.user_session.get("user_id", "anonymous")
    session_id: str = cl.user_session.get("thread_id", "no_id")

    logger.info(message.content) 
    
    # Append user turn
    history.append(HumanMessage(content=message.content))

    state_input = {
        "messages": history,
        "route": "",
        "current_agent": "",
        "user_id": user_id,
        "thread_id": session_id,
    }

    final_message = cl.Message(content="")
    graph = get_graph()

    async with cl.Step(name="", type="run", show_input=False):
        try:
            graph = get_graph()

            result = await asyncio.to_thread(
                graph.invoke,
                state_input,
                {"configurable": {
                    "user_id": user_id,
                    "thread_id": session_id,
                    }
                 },
            )

        except Exception as exc:
            await cl.Message(content=f"⚠️ Error: {exc}").send()
            logger.error(f"\n[ERROR] Agent error: {exc}\n")
            return

    # Persist updated history
    cl.user_session.set("message_history", result["messages"])

    reply = _last_ai_text(result["messages"])
    
    for token in reply.split():
        await final_message.stream_token(token + " ")
        await asyncio.sleep(0.02)  # Delay for effect
        
    await final_message.send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    # Reconstruct message history from the resumed thread steps
    message_history = []
    for step in thread["steps"]:
        # Standard step types are often "user_message" and "ai_message"
        role = "user" if step["type"] == "user_message" else "assistant"
        message_history.append({"role": role, "content": step["output"]})
    
    # Store the history back in the user session
    cl.user_session.set("message_history", message_history)
    
    # await cl.Message(content="Welcome back! I've restored our conversation.").send()
