# e-Commerce Multi-Agent System

Directory structure

```shell
ecommerce_multiagent/
│
├── main.py                     # builds LangGraph
├── state.py                    # shared state definition
│
├── agents/
│   ├── conversation.py
│   ├── coordinator.py
│   ├── customer_support.py
│   ├── sales_recommendation.py
│   ├── order_inventory.py
│   ├── returns_refunds.py
│
├── policy/
│   ├── compliance.py
│
├── observability/
│   ├── logger.py
│
├── data/
│   ├── faq.json
│
└── requirements.txt
```

Agents Documentation

- [Customer Support Agent](docs/customer-support.md)

## Setup Local LLM

```shell
$ curl -fsSL https://ollama.com/install.sh | sh

$ ollama pull llama3

$ ollama run llama3
```

## Presentation Notes and Tips

- We used modular agent architecture.
- Each agent is independently developed.
- Shared state enables orchestration.
- Escalation logic ensures safe fallback.
- Local LLM reduces operational cost.
- System is scalable to API-based LLM in production.
