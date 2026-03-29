"""
api.py — FastAPI wrapper for the e-commerce multi-agent system.

Drop this file at the project root (same level as main.py).

Usage:
    uv run uvicorn api:app --host 0.0.0.0 --port 8000

Environment variables (same as the rest of the project):
    OPENAI_API_KEY   — required for OpenAI provider
    LLM_PROVIDER     — "openai" (default) or "ollama"
"""

import os
import sys
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

# Ensure the project root is on sys.path (same trick as main.py)
sys.path.insert(0, os.path.dirname(__file__))

from graph.workflow import get_graph

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="E-Commerce Multi-Agent System",
    description="REST API wrapper around the LangGraph multi-agent pipeline.",
    version="1.0.0",
)

# Allow Chainlit (or any front-end) running on a different origin to call us.
# Tighten this to your actual subdomain once you have one.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session store  { session_id: [BaseMessage, ...] }
# ---------------------------------------------------------------------------
# For a demo this is fine. For production, replace with Redis or a DB.

_sessions: dict[str, list] = {}


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message.")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Opaque session token. Create once per browser tab and reuse.",
    )
    user_id: str = Field(
        default="user_001",
        description="Customer identifier passed through the agent graph.",
    )


class ChatResponse(BaseModel):
    reply: str
    agent: str
    session_id: str
    route: str


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _last_ai_text(messages: list) -> str:
    """Extract the text of the last AIMessage (mirrors main.py logic)."""
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Liveness probe — Nginx / systemd can hit this."""
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(req: ChatRequest) -> ChatResponse:
    """
    Send a message to the multi-agent system and receive a reply.

    The caller must preserve `session_id` across turns to maintain
    conversation history. If a new `session_id` is sent, a fresh
    conversation is started.
    """
    # Retrieve or initialise message history for this session
    history = _sessions.get(req.session_id, [])

    # Append the new human turn
    history.append(HumanMessage(content=req.message))

    state_input = {
        "messages": history,
        "route": "",
        "current_agent": "",
        "user_id": req.user_id,
    }

    try:
        graph = get_graph()
        result = graph.invoke(
            state_input,
            config={"configurable": {"thread_id": req.session_id}},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Persist updated history
    _sessions[req.session_id] = result["messages"]

    reply = _last_ai_text(result["messages"])
    agent_label = (
        result.get("current_agent", "assistant").replace("_", " ").title()
    )
    route = result.get("route", "")

    return ChatResponse(
        reply=reply,
        agent=agent_label,
        session_id=req.session_id,
        route=route,
    )


@app.delete("/session/{session_id}", tags=["ops"])
def clear_session(session_id: str) -> JSONResponse:
    """Wipe the message history for a session (useful for testing)."""
    _sessions.pop(session_id, None)
    return JSONResponse({"cleared": session_id})