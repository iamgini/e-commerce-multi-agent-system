
"""
Integrated multi-agent entrypoint for the e-commerce project proposal.

Place this file in the repository root and run:

    python integrated_multi_agent_system.py

What it integrates from the proposal:
- Conversation Agent
- Coordinator Agent
- Customer Support Agent
- Sales & Product Recommendation Agent
- Order & Inventory Management Agent
- Returns & Refunds Agent
- Human escalation fallback

This file is intentionally self-contained so you do not need to rewrite the
existing agent folders just to get an end-to-end demo running.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

ROOT = Path(__file__).resolve().parent
SALES_REC_DIR = ROOT / "agent_sales_recommendation"
ORDER_INV_DIR = ROOT / "agent_order_inventory"


def _load_module(module_name: str, file_path: Path):
    """Load a Python module from an exact file path under a unique name."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Root repo imports
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Compatibility patch for the returns agent.
# The uploaded repo has Message defined in returns_refunds_state.py rather than
# state.py, but agents/returns_refunds.py imports Message from state.py.
# This patch keeps the integration file working without forcing you to edit
# the original state.py file immediately.
# ---------------------------------------------------------------------------
try:
    import state as shared_state  # type: ignore
except Exception as exc:
    raise RuntimeError("Could not import root state.py from repository root.") from exc

if not hasattr(shared_state, "Message"):
    class Message(TypedDict):
        sender: str
        content: str
        timestamp: str

    shared_state.Message = Message  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Existing agents from the repo
# ---------------------------------------------------------------------------
try:
    from agent_customer_support.customer_support import customer_support_agent
except Exception:
    customer_support_agent = None

try:
    from agents.returns_refunds import ReturnsRefundsAgent
except Exception:
    ReturnsRefundsAgent = None  # type: ignore

try:
    from returns_refunds_state import create_empty_state, add_to_history
except Exception:
    create_empty_state = None
    add_to_history = None


# ---------------------------------------------------------------------------
# Dynamic imports for the sales/recommendation mini-system and the standalone
# order/inventory package.
# ---------------------------------------------------------------------------
sales_db_setup = None
sales_workflow = None
order_inv_db_setup = None
order_inv_agent_mod = None
order_inv_tools_mod = None

if SALES_REC_DIR.exists():
    sales_db_setup = _load_module(
        "sales_recommendation_db_setup",
        SALES_REC_DIR / "database" / "db_setup.py",
    )
    sales_workflow = _load_module(
        "sales_recommendation_workflow",
        SALES_REC_DIR / "graph" / "workflow.py",
    )

if ORDER_INV_DIR.exists():
    order_inv_db_setup = _load_module(
        "order_inventory_db_setup",
        ORDER_INV_DIR / "database" / "db_setup.py",
    )
    order_inv_agent_mod = _load_module(
        "order_inventory_agent_mod",
        ORDER_INV_DIR / "agents" / "order_inventory_agent.py",
    )
    order_inv_tools_mod = _load_module(
        "order_inventory_tools_mod",
        ORDER_INV_DIR / "tools" / "order_inventory_tools.py",
    )

# Optional imports used by the tool-loop runner
try:
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.prebuilt import ToolNode
except Exception:
    AIMessage = None
    HumanMessage = None
    ToolNode = None


# ---------------------------------------------------------------------------
# Integration state
# ---------------------------------------------------------------------------
@dataclass
class IntegrationState:
    user_id: str
    session_id: str
    user_query: str
    route: str | None = None
    current_agent: str | None = None
    response: str | None = None
    escalate: bool = False
    confidence: float | None = None
    explanation: str | None = None
    policy_passed: bool = True
    policy_reason: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Integrated system
# ---------------------------------------------------------------------------
class IntegratedMultiAgentSystem:
    """
    Single-file integration layer for the project proposal architecture.

    It acts as:
    - Conversation Agent: stores history, basic policy checks
    - Coordinator Agent: routes to the correct specialist agent
    - Integration Hub: invokes specialist agents and normalises outputs
    """

    def __init__(self) -> None:
        self.session_store: dict[str, list[dict[str, str]]] = {}
        self.returns_agent = ReturnsRefundsAgent() if ReturnsRefundsAgent else None

        self._initialise_databases()

    # ---------------------- Conversation Agent duties ----------------------

    def _initialise_databases(self) -> None:
        """Prepare the existing SQLite databases if those agent folders exist."""
        if sales_db_setup and hasattr(sales_db_setup, "initialise_databases"):
            try:
                sales_db_setup.initialise_databases()
            except Exception:
                # Non-fatal; repo may already be set up
                pass

        if order_inv_db_setup and hasattr(order_inv_db_setup, "initialise_database"):
            try:
                order_inv_db_setup.initialise_database()
            except Exception:
                pass

    def _get_history(self, session_id: str) -> list[dict[str, str]]:
        return self.session_store.setdefault(session_id, [])

    def _store_message(self, session_id: str, sender: str, content: str) -> None:
        self._get_history(session_id).append(
            {
                "sender": sender,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _policy_check(self, query: str) -> tuple[bool, str]:
        """
        Minimal policy/compliance gate for the conversation agent.

        The proposal explicitly includes a policy-compliance step before routing.
        The current repo's policy/compliance.py is empty, so this file provides
        a basic gate instead of pretending that part already exists.
        """
        text = (query or "").strip()
        if not text:
            return False, "Empty query."
        blocked = [
            "drop database",
            "delete all data",
            "hack the system",
            "steal customer data",
        ]
        lowered = text.lower()
        for phrase in blocked:
            if phrase in lowered:
                return False, f"Blocked by policy rule: {phrase!r}"
        return True, "Passed basic compliance checks."

    # ---------------------- Coordinator Agent duties -----------------------

    def _route_query(self, query: str) -> tuple[str, str]:
        """
        Top-level coordinator route across all proposal agents.

        The sales/recommendation sub-system keeps its own internal coordinator
        between product discovery and sales execution.
        """
        text = query.lower().strip()

        if any(word in text for word in ["bye", "goodbye", "done", "exit", "quit"]):
            return "finish", "User ended the conversation."

        if any(
            phrase in text
            for phrase in [
                "return", "refund", "defective", "damaged", "replace",
                "complaint", "wrong item", "money back", "track return",
            ]
        ):
            return "returns_refunds", "Returns/refunds language detected."

        if any(
            phrase in text
            for phrase in [
                "purchase order", "purchase orders", "supply order", "supply orders",
                "receive stock", "inventory", "stock level", "low stock",
                "stock by product", "order history", "order status", "view stock",
                "reduce stock", "procurement", "supplier",
            ]
        ):
            return "order_inventory", "Order/inventory or procurement language detected."

        if any(
            phrase in text
            for phrase in [
                "recommend", "compare", "find product", "show me", "browse",
                "search", "best", "popular", "trending", "looking for",
                "add to cart", "checkout", "discount code", "promo code",
                "my cart", "buy", "purchase this",
            ]
        ):
            return "sales_recommendation", "Shopping or product-discovery language detected."

        if any(
            phrase in text
            for phrase in [
                "shipping policy", "delivery", "faq", "help", "support",
                "contact", "hours", "payment methods", "how long does shipping take",
            ]
        ):
            return "customer_support", "General support/FAQ language detected."

        return "customer_support", "Defaulted to customer support."

    # ------------------------ Specialist invocation ------------------------

    def _run_customer_support(self, state: IntegrationState) -> IntegrationState:
        if customer_support_agent is None:
            return self._escalate(
                state,
                "Customer Support Agent could not be imported.",
                confidence=0.0,
            )

        support_state = {
            "user_query": state.user_query,
            "user_id": state.user_id,
            "intent": "support",
            "response": None,
            "escalate": False,
            "confidence": None,
            "explanation": None,
        }

        try:
            result = customer_support_agent(support_state)
            state.current_agent = "Customer Support Agent"
            state.response = result.get("response")
            state.escalate = bool(result.get("escalate", False))
            state.confidence = result.get("confidence")
            state.explanation = result.get("explanation")
            if state.escalate:
                state.response = (
                    state.response
                    or "Customer support could not answer confidently. Escalated to human agent."
                )
            return state
        except Exception as exc:
            return self._escalate(
                state,
                f"Customer Support Agent failed: {exc}",
                confidence=0.0,
            )

    def _run_returns_refunds(self, state: IntegrationState) -> IntegrationState:
        if self.returns_agent is None or create_empty_state is None:
            return self._escalate(
                state,
                "Returns & Refunds Agent could not be imported.",
                confidence=0.0,
            )

        try:
            rr_state = create_empty_state(
                user_query=state.user_query,
                user_id=state.user_id,
                session_id=state.session_id,
            )
            if add_to_history is not None:
                add_to_history(rr_state, "user", state.user_query)

            result = self.returns_agent.invoke(rr_state)
            state.current_agent = "Returns & Refunds Agent"
            state.response = result.get("response")
            state.escalate = bool(result.get("route_to_agent") == "coordinator") or (
                not bool(result.get("success", True))
            )
            state.confidence = result.get("confidence_score")
            state.explanation = result.get("explanation")
            return state
        except Exception as exc:
            return self._escalate(
                state,
                f"Returns & Refunds Agent failed: {exc}",
                confidence=0.0,
            )

    def _run_sales_recommendation(self, state: IntegrationState) -> IntegrationState:
        if sales_workflow is None or HumanMessage is None:
            return self._escalate(
                state,
                "Sales & Recommendation subsystem could not be imported.",
                confidence=0.0,
            )

        try:
            graph = sales_workflow.get_graph()
            result = graph.invoke(
                {
                    "messages": [HumanMessage(content=state.user_query)],
                    "route": "",
                    "current_agent": "",
                    "user_id": state.user_id,
                },
                config={"configurable": {"thread_id": state.session_id}},
            )

            last_message = result["messages"][-1] if result.get("messages") else None
            state.current_agent = result.get("current_agent") or "Sales/Recommendation Agent"
            state.response = getattr(last_message, "content", None) or str(last_message)
            state.escalate = False
            state.confidence = 0.85
            state.explanation = (
                "Handled by the sales & product recommendation LangGraph workflow."
            )
            return state
        except Exception as exc:
            return self._escalate(
                state,
                f"Sales & Recommendation subsystem failed: {exc}",
                confidence=0.0,
            )

    def _run_order_inventory(self, state: IntegrationState) -> IntegrationState:
        if (
            order_inv_agent_mod is None
            or order_inv_tools_mod is None
            or ToolNode is None
            or HumanMessage is None
            or AIMessage is None
        ):
            return self._escalate(
                state,
                "Order & Inventory Management Agent could not be imported.",
                confidence=0.0,
            )

        try:
            tool_node = ToolNode(order_inv_tools_mod.ORDER_INVENTORY_TOOLS)
            local_state: dict[str, Any] = {
                "messages": [HumanMessage(content=state.user_query)],
                "current_agent": "",
                "user_id": state.user_id,
            }

            # Same loop shape as the sales/recommendation LangGraph agents:
            # agent -> tools -> agent -> finish
            while True:
                agent_result = order_inv_agent_mod.order_inventory_agent_node(local_state)
                local_state["messages"].extend(agent_result["messages"])
                local_state["current_agent"] = agent_result.get("current_agent", "")

                last = local_state["messages"][-1]
                if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
                    tool_result = tool_node.invoke(local_state)
                    local_state["messages"].extend(tool_result["messages"])
                    continue
                break

            final_message = local_state["messages"][-1]
            state.current_agent = "Order & Inventory Management Agent"
            state.response = getattr(final_message, "content", None) or str(final_message)
            state.escalate = False
            state.confidence = 0.9
            state.explanation = (
                "Handled by the order & inventory agent with SQLite-backed tools."
            )
            return state
        except Exception as exc:
            tb = traceback.format_exc(limit=2)
            return self._escalate(
                state,
                f"Order & Inventory Management Agent failed: {exc}\n{tb}",
                confidence=0.0,
            )

    def _escalate(
        self,
        state: IntegrationState,
        reason: str,
        confidence: float | None = None,
    ) -> IntegrationState:
        state.current_agent = "Human Escalation"
        state.response = (
            "I could not complete that automatically, so this should be escalated "
            "to a human agent."
        )
        state.escalate = True
        state.confidence = confidence
        state.explanation = reason
        return state

    # ----------------------------- Public API -----------------------------

    def process_query(
        self,
        query: str,
        user_id: str = "user_123",
        session_id: str = "default_session",
    ) -> dict[str, Any]:
        """
        End-to-end processing path following the proposal flow:

        user query
            -> conversation agent (store + policy check)
            -> coordinator agent (route)
            -> specialist agent
            -> response / escalation
        """
        state = IntegrationState(
            user_id=user_id,
            session_id=session_id,
            user_query=query,
            history=list(self._get_history(session_id)),
        )

        self._store_message(session_id, "user", query)

        policy_passed, policy_reason = self._policy_check(query)
        state.policy_passed = policy_passed
        state.policy_reason = policy_reason

        if not policy_passed:
            state = self._escalate(
                state,
                f"Conversation Agent blocked query: {policy_reason}",
                confidence=0.0,
            )
            self._store_message(session_id, "system", state.response or "")
            return self._serialise_state(state)

        route, route_reason = self._route_query(query)
        state.route = route
        state.explanation = route_reason

        if route == "finish":
            state.current_agent = "Coordinator Agent"
            state.response = "Goodbye. The integrated multi-agent session is now closed."
            state.escalate = False
            state.confidence = 1.0

        elif route == "customer_support":
            state = self._run_customer_support(state)

        elif route == "returns_refunds":
            state = self._run_returns_refunds(state)

        elif route == "sales_recommendation":
            state = self._run_sales_recommendation(state)

        elif route == "order_inventory":
            state = self._run_order_inventory(state)

        else:
            state = self._escalate(
                state,
                f"Coordinator produced unsupported route: {route}",
                confidence=0.0,
            )

        self._store_message(session_id, "assistant", state.response or "")
        return self._serialise_state(state)

    def _serialise_state(self, state: IntegrationState) -> dict[str, Any]:
        return {
            "user_id": state.user_id,
            "session_id": state.session_id,
            "user_query": state.user_query,
            "route": state.route,
            "current_agent": state.current_agent,
            "response": state.response,
            "escalate": state.escalate,
            "confidence": state.confidence,
            "explanation": state.explanation,
            "policy_passed": state.policy_passed,
            "policy_reason": state.policy_reason,
            "history_length": len(self._get_history(state.session_id)),
        }


def main() -> None:
    system = IntegratedMultiAgentSystem()

    print("=" * 72)
    print("Integrated E-Commerce Multi-Agent System")
    print("Routes across support, sales/recommendation, returns, and order/inventory")
    print("Type 'exit' to stop.")
    print("=" * 72)

    user_id = "user_123"
    session_id = "demo_session"

    while True:
        query = input("\nYou: ").strip()
        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            print("System: Goodbye.")
            break

        result = system.process_query(query, user_id=user_id, session_id=session_id)

        print("\n--- RESULT ---")
        print(f"Route:        {result['route']}")
        print(f"Agent:        {result['current_agent']}")
        print(f"Escalate:     {result['escalate']}")
        print(f"Confidence:   {result['confidence']}")
        print(f"Explanation:  {result['explanation']}")
        print(f"Response:     {result['response']}")


if __name__ == "__main__":
    main()
