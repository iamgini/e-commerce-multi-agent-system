# from langgraph.graph import StateGraph, START, END

# from nodes import search_node, should_continue
# from tools import tool_node
# from state import State


# def build_graph():
#     builder = StateGraph(State)
#     builder.add_node("product_searcher", search_node)
#     builder.add_node("tools", tool_node)

#     builder.add_edge(START, "product_searcher")
#     builder.add_conditional_edges("product_searcher", should_continue, ["tools", END])
#     builder.add_edge("tools", "product_searcher")

#     return builder.compile()


from langgraph.graph import END, START, StateGraph
from nodes import (
    intent_node,
    intent_routing,
    response_node,
    search_node,
)

from state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("classify_intent", intent_node)
    builder.add_node("product_searcher", search_node)
    builder.add_node("final_response", response_node)

    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        intent_routing,
        {"Sales": END, "Recommend": "product_searcher", "None": END},
    )
    builder.add_edge("product_searcher", "final_response")
    # builder.add_conditional_edges("product_searcher", should_continue, ["tools", END])
    # builder.add_edge("tools", "product_searcher")

    return builder.compile()
