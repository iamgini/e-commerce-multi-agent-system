# e-Commerce Multi-Agent System

Directory structure

```shell
e-commerce_multi-agent-system/
├── main.py                     # builds LangGraph
├── requirements.txt
├── README.md
├── config.py
│
├── agents/
│   ├── conversation.py
│   ├── coordinator.py
│   ├── customer_support.py
│   ├── sales_recommendation.py
│   ├── order_inventory.py
│   └── returns_refunds.py
│
├── data/
│   ├── cart.db
│   ├── order_inventory.db
│   ├── products.db
│   ├── checkpointer.db
│   └── faq.json
│
├── graph/
│   └── workflow.py         ## Contains the graph map and state
│
├── helpers/
│   ├── database/
│   │   ├── db_setup.py
│   │   ├── cart_db.py
│   │   ├── order_inventory_db.py
│   │   ├── product_db.py
│   │   └── compliance.py
│   │
├── ├── observability/
│   │   └── logger.py
│   │
│   └── policy/
│       └── compliance.py
│
├── scripts/
│   ├── db_setup.py
│   └── seed_data.py
│
├── tests/
│   ├── test_coordinator_agent_quick.py
│   ├── test_customer_support_agent.py
│   ├── test_order_inventory_agent_quick.py
│   ├── test_order_inventory_state.py
│   └── test_returns_agent_quick.py
│
├── tools/
│   ├── order_inventory_tools.py
│   ├── recommendation_tools.py
│   └── sales_tools.py
```

## Testing main

```shell

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
