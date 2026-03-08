from langchain_core.messages import SystemMessage
from langgraph.graph import END
from tools import query_products_db

from agents import chatbot_llm, intent_llm, search_llm
from state import AgentState

# def intent_node(state: State):
#     # Use full message history with a system prompt
#     system_prompt = (
#         "You are an intent classifier within a Sales and Product Recommendation agent of an E-Commerce multi agent system.\n",
#         "Your task is to analyze the user's latest message and classify it into exactly ONE of the following intents:\n",
#         "1. personalised_recommendation\n",
#         "- The user wants product suggestions tailored to preferences, needs, budget, usage, or profile.\n",
#         "- Examples:\n"
#         "- Recommend a laptop for video editing under $1500\n",
#         "- What shoes should I get for marathon training?\n",
#         "- I need a gift for my dad who likes photograph\n",
#         "2. product_search\n",
#         "- The user is searching for a specific product, category, brand, or feature without personalization.\n",
#         "- Examples:\n",
#         "- Show me Nike running shoes\n",
#         "- Wireless earbuds with noise cancelling\n",
#         "- iPhone 15 Pro price\n",
#         "3. cart_upsell\n",
#         "- The user already has a product in mind or in their cart and is asking for upgrades, add-ons, bundles, or better alternatives.\n",
#         "- Examples:\n",
#         "- Do I need a case for this phone?\n"
#         "- Any accessories I should add\n"
#         "- Is there a better version of this\n"
#         "Rules:\n",
#         "- Output ONLY one intent label.\n"
#         "- Do NOT include explanations, reasoning, or additional text.\n",
#         "- If multiple intents seem possible, choose the one that best reflects the user's primary goal.\n",
#         "- If the user mentions an existing product, cart item, or prior selection, prefer CART_UPSELL.\n",
#         "- If the user mentions preferences, use-cases, or personal constraints, prefer PERSONALISED_RECOMMENDATION.\n",
#         "- If the user is simply browsing or searching by product attributes, choose PRODUCT_SEARCH.\n"
#     )

#     messages = [SystemMessage(content=system_prompt)] + state["messages"]
#     result = intent_llm.invoke(messages)

#     return {"messages": state["messages"], "intent": state["result"]}


def intent_node(state: AgentState):
    system_prompt = """
        You are an intent classifier within a Sales and Product Recommendation agent of an E-Commerce multi agent system.
        Your task is to analyze the user's latest message and classify it into exactly ONE of the following intents.
        Only return one word:
        1. sales
        - The user is interacting with the cart, such as adding items or removing items from the cart.
        2. recommend
        - The user is searching for a specific product, category, brand, or feature.
        - The user already has a product in mind or in their cart and is asking for upgrades, add-ons, bundles, or better alternatives.
        3. none
        - The user does not fulfil either the sales or recommend intent.
        """

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = intent_llm.invoke(messages)
    print(f"=== Output of intent_node ===\n{response}\n\n")
    return {"intent": response.intent}


# def search_node(state: AgentState):
#     system_prompt = """
#         You are a searcher within a Sales and Product Recommendation agent of an E-Commerce multi agent system.
#         Your goal is to search through the product database to find the most suitable products (up to 5) for the user.
#         1. Use 'search_products' to find options.
#         2. Use 'get_product_details' to confirm stock before recommending.
#         Make sure to only provide only searches for items that are in stock.
#         If there are no suitable searches found, inform the user with the following message: 'There are currently no items that match your request. Would you like to search for other items instead?'
#         """

#     messages = [SystemMessage(content=system_prompt)] + state['messages']
#     response = search_llm.invoke(messages)
#     return {"messages": [response]}


def search_node(state: AgentState):
    system_prompt = """
        You are a searcher within a Sales and Product Recommendation agent of an E-Commerce multi-agent system.
        You have 2 tasks:
        1. Use 'query_products_db' to search through the product database to find the most suitable products for the user
        2. For products retrieved from the product database, select at most 5 items that most satisfies the user and recommend them
        Make sure to only provide only searches for items that are in stock.
        """

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    filters = search_llm.invoke(messages)
    print(f"=== Search_node filters ===\n{filters['parsed']}\n\n")

    products = query_products_db(filters["parsed"])
    print(f"=== Search_node output ===\n{products}\n\n")

    return {"products": products}

    # raw_message = response.get('raw')
    # parsed_output = response.get('parsed')

    # if parsed_output:
    #     return {"messages": messages + [raw_message], "final_structured_output": parsed_output}

    # else:
    #     return {"messages": [response]}


def response_node(state: AgentState):
    products = state["products"]

    system_prompt = f"""
        You are the response node within a Sales and Product Recommendation agent of an E-Commerce multi-agent system.
        Your task is based on the user's query, recommend ONLY products that had been retrieved from the product database.
        The products returned by the database follows the following schema: (product_id, product_name, product_description, product_category, product_subcategory, brand_name, price, stock, rating).
        
        The products that have been retrieved from the product database are as follows: {products}.
        
        Write a marketing response using ONLY the product description, brand and price to recommend these products. Do NOT mention about the product_id, rating and stock.
        If the products retrieved do not match with the users query, respond with the following: 'There are currently no items that match your request. Would you like to search for other items instead?'
        """

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = chatbot_llm.invoke(messages)
    return {"messages": [response]}


# -- Routing Conditions --------
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def intent_routing(state: AgentState):
    intent = state["intent"]
    if state["intent"] == "sales":
        return "Sales"
    elif state["intent"] == "recommend":
        return "Recommend"
    else:
        return "None"
