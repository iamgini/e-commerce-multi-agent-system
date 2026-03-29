# e-Commerce Multi-Agent System

Directory structure

```shell
ecommerce_multiagent/
│
├── main.py                     # builds LangGraph
├── state.py                    # shared state definition; All agents must use the same state.
├── agents/
│   ├── conversation.py
│   ├── coordinator.py
│   ├── customer_support.py
│   ├── sales_recommendation.py
│   ├── order_inventory.py
│   ├── returns_refunds.py
├── policy/
│   ├── compliance.py
├── observability/
│   ├── logger.py
├── data/
│   ├── faq.json
└── requirements.txt
```

## Testing main

```shell
$ uv run python main.py
```

## Testing coordinator

```shell
e-commerce-multi-agent-system  $  uv run python test_coordinator_agent_quick.py

Recommendation       | Can you recommend a good wireless mouse?
route -> recommend
--------------------------------------------------------------------------------
Sales                | Add the keyboard to my cart and show my total
route -> sales
--------------------------------------------------------------------------------
Order Inventory      | Create a purchase order and show low stock items
route -> orders_inventory
--------------------------------------------------------------------------------
Support              | I need help with my account
route -> customer_support
--------------------------------------------------------------------------------
Finish               | Thanks, bye
route -> finish
--------------------------------------------------------------------------------
```


## Agents Documentation

- TODO

## Try to cover all learning from 4 modules

### Module 1 – Responsible & Explainable AI

- No hallucination rule
- Escalation when unsure
- Confidence score
- Explanation field

### Module 2 – AI & Cybersecurity

- No external API
- No direct DB access
- Controlled knowledge source
- Logging enabled

### Module 3 – Architecting Agentic AI

- Stateless node design
- Works inside LangGraph
- Shared state architecture

### Module 4 – Integration & Deployment

- Local LLM
- Replaceable model
- Production-like structure

## Presentation Notes and Tips

- We used modular agent architecture.
- Each agent is independently developed.
- Shared state enables orchestration.
- Escalation logic ensures safe fallback.
- Local LLM reduces operational cost.
- System is scalable to API-based LLM in production.
