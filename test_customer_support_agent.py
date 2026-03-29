from agent_customer_support.customer_support import customer_support_agent

print("Customer Support Agent (type 'exit' to quit)")
print("=" * 40)

while True:
    query = input("\nAsk something: ").strip()

    if query.lower() in ("exit", "quit", "bye"):
        print("Goodbye!")
        break

    initial_state = {
        "user_query": query,
        "user_id": "user123",
        "intent": "support",
        "response": None,
        "escalate": False,
        "confidence": None,
        "explanation": None,
    }

    result = customer_support_agent(initial_state)

    print("\n===== RESULT =====")
    print("Response:", result["response"])
    print("Escalate:", result["escalate"])
    print("Confidence:", result["confidence"])
    print("Explanation:", result["explanation"])