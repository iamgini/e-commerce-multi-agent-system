from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from IPython.display import Image

from graph import build_graph


def main():
    graph = build_graph()
    state = {"messages": []}

    while True:
        try:
            print("-" * 50)
            print("Sales & Product Recommendation Agent")
            print("Press 'q' to exit")
            print()

            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            
            # Add new user message to the history
            state["messages"].append(HumanMessage(content=user_input))
            
            # Invoke graph with the full state history
            state = graph.invoke(state)

            print("Agent:", state["messages"][-1].content)
            # print(state)
            
        except KeyboardInterrupt:
            print("\n\nConversation interrupted. Goodbye!")
            break

        except Exception as e:
            print(f"\nAn error occurred: {e}")
            print("Ending conversation...")
            break


if __name__ == "__main__":
    main()
