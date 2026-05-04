# ShopBot — e-Commerce Multi-Agent System

A multi-agent e-commerce chatbot built with **LangGraph**, **Chainlit**, and **PostgreSQL**. Specialised agents handle recommendations, sales, order management, returns, and customer support — all orchestrated by a central coordinator.

**Live demo:** [https://shopbot.tbly.cc](https://shopbot.tbly.cc)
**Container image:** `quay.io/iamgini/shopbot`

## Table of Contents

- [ShopBot — e-Commerce Multi-Agent System](#shopbot--e-commerce-multi-agent-system)
  - [Table of Contents](#table-of-contents)
  - [Architecture](#architecture)
  - [Agents](#agents)
    - [Routing labels](#routing-labels)
  - [Project Structure](#project-structure)
  - [Prerequisites](#prerequisites)
  - [Local Setup](#local-setup)
    - [1. Clone and create a virtual environment](#1-clone-and-create-a-virtual-environment)
    - [2. Configure environment variables](#2-configure-environment-variables)
    - [3. Initialise the database](#3-initialise-the-database)
    - [4. (Optional) Switch to Ollama](#4-optional-switch-to-ollama)
  - [Running the App](#running-the-app)
    - [Chainlit UI](#chainlit-ui)
    - [CLI (no UI)](#cli-no-ui)
    - [FastAPI](#fastapi)
  - [API Access](#api-access)
    - [Smoke test (three turns)](#smoke-test-three-turns)
  - [Testing](#testing)
    - [Unit tests (CI-compatible)](#unit-tests-ci-compatible)
    - [Quick coordinator routing test](#quick-coordinator-routing-test)
    - [Full coordinator tests (requires Ollama)](#full-coordinator-tests-requires-ollama)
    - [Customer support evaluation (DeepEval)](#customer-support-evaluation-deepeval)
  - [CI/CD Pipeline](#cicd-pipeline)
  - [Container Build](#container-build)
    - [Build locally](#build-locally)
    - [Run locally](#run-locally)
    - [Pull from registry](#pull-from-registry)
  - [Configuration Reference](#configuration-reference)
  - [Module Coverage](#module-coverage)
    - [Module 1 — Responsible \& Explainable AI](#module-1--responsible--explainable-ai)
    - [Module 2 — AI \& Cybersecurity](#module-2--ai--cybersecurity)
    - [Module 3 — Architecting Agentic AI](#module-3--architecting-agentic-ai)
    - [Module 4 — Integration \& Deployment](#module-4--integration--deployment)



## Architecture

LangGraph StateGraph

```shell
  [START] ──▶ coordinator ──▶ recommendation_agent ──▶ recommendation_tools
                   │                                           │ (loops)
                   │
                   ├──────────▶ sales_agent ──▶ sales_tools
                   │                                  │ (loops)
                   │
                   ├──────────▶ customer_support_agent
                   │
                   ├──────────▶ order_inventory_agent ──▶ order_inventory_tools
                   │                                               │ (loops)
                   │
                   ├──────────▶ returns_refunds_agent ──▶ returns_tools
                   │                                           │ (loops)
                   │
                   └──────────▶ [END]
```

Infrastructure

```shell
  Chainlit UI  ──▶  FastAPI (api.py)  ──▶  LangGraph graph
                                                   │
                                              PostgreSQL
                                     ┌─────────────┼─────────────┐
                                checkpoints_db  products_db  cart_db
                                order_inv_db   returns_db   users_db
```

Deployment

```shell
  GitHub Actions  ──▶  Quay.io  ──▶  EC2 (ap-southeast-1)
                                            │
                                     Nginx + Cloudflare
                                      (TLS / WAF / DDoS)
```

The **coordinator** classifies each user message using keyword heuristics (fast path) and falls back to an LLM call when intent is ambiguous. After each agent turn, control returns to the coordinator for the next message.


## Agents

| Agent | Responsibility |
|---|---|
| **Coordinator** | Intent classification and routing |
| **Recommendation Agent** | Product discovery — keyword search, filtering, trending, comparisons, personalised picks |
| **Sales Agent** | Cart management, checkout, order history, discount codes |
| **Customer Support Agent** | FAQ lookup (confidence-scored), escalation to human when unsure |
| **Order & Inventory Agent** | Purchase orders, supply orders, stock management |
| **Returns & Refunds Agent** | Return eligibility checks, return requests, refund status, complaints |

Detailed docs for each agent live in [`agents/agents_readme/`](agents/agents_readme/).

### Routing labels

| Route constant | Target agent |
|---|---|
| `recommend` | Recommendation Agent |
| `sales` | Sales Agent |
| `customer_support` | Customer Support Agent |
| `orders_inventory` | Order & Inventory Agent |
| `returns_refunds` | Returns & Refunds Agent |
| `finish` | END |

## Project Structure

```
e-commerce-multi-agent-system/
├── agents/
│   ├── coordinator.py               # Routing agent (keyword + LLM fallback)
│   ├── customer_support.py          # FAQ + escalation agent
│   ├── order_inventory_agent.py     # Purchase / supply / stock agent
│   ├── recommendation_agent.py      # Product discovery agent
│   ├── returns_refunds_agent.py     # Returns & refunds agent
│   ├── sales_agent.py               # Cart / checkout agent
│   └── agents_readme/               # Per-agent documentation
│
├── tools/
│   ├── customer_support_tools.py    # FAQ lookup tool
│   ├── order_inventory_tools.py     # 10 inventory tools
│   ├── recommendation_tools.py      # 8 recommendation tools
│   ├── returns_tools.py             # 6 return tools
│   └── sales_tools.py               # 10 sales / cart tools
│
├── helpers/
│   ├── database/                    # DB query helpers (per domain)
│   ├── observability/               # Structured logging + S3 log handler
│   └── policy/                      # Guardrails validators
│
├── tests/
│   ├── test_customer_support_agent.py   # Runs in CI
│   ├── test_coordinator_agent.py        # Requires Ollama — excluded from CI
│   └── eval_customer_support.py         # DeepEval evaluation suite
│
├── scripts/
│   ├── db_setup.py                  # Creates PostgreSQL schemas
│   └── seed_data.py                 # Seeds demo product and order data
│
├── data/
│   ├── faq.json                     # Customer support knowledge base
│   ├── cart.db                      # Local SQLite (dev only)
│   └── order_inventory.db           # Local SQLite (dev only)
│
├── chainlit_setup/                  # Chainlit data layer + Prisma migrations
├── systemd-files-podman/            # Podman systemd unit files (EC2)
├── .github/workflows/
│   └── agent-pipeline.yml           # CI/CD pipeline
│
├── chainlit_app.py                  # Chainlit UI entry point
├── api.py                           # FastAPI programmatic interface
├── main.py                          # CLI entry point
├── config.py                        # Shared constants and routing labels
├── requirements.txt
├── Containerfile-ShopBot            # Container image definition
└── .env-sample                      # Environment variable template
```

## Prerequisites

- Python 3.12
- PostgreSQL (or use the provided Podman/Docker compose for local dev)
- An OpenAI API key (`gpt-4o-mini` by default; switchable to Ollama)
- [dotenvx](https://dotenvx.com/) for secret management
- [Podman](https://podman.io/) (preferred) or Docker

Optional for local LLM testing:

- [Ollama](https://ollama.com/) with `llama3` or `phi3`

## Local Setup

### 1. Clone and create a virtual environment

```shell
git clone <repo-url>
cd e-commerce-multi-agent-system

# Python 3.12 venv (required — system Python 3.14 breaks anyio)
uv venv --python 3.12 .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install chainlit
```

### 2. Configure environment variables

```shell
cp .env-sample .env
# Edit .env and fill in your values
```

Key variables:

```shell
OPENAI_API_KEY=<your-key>
LLM_PROVIDER=openai          # or: ollama

# PostgreSQL DSNs (avoid special characters in passwords)
MAINTENANCE_DB_DSN="postgresql://user:password@localhost:5432/postgres?sslmode=disable"
PRODUCTS_DB_DSN="postgresql://user:password@localhost:5432/products_db?sslmode=disable"
CART_DB_DSN="postgresql://user:password@localhost:5432/cart_db?sslmode=disable"
ORDER_INVENTORY_DB_DSN="postgresql://user:password@localhost:5432/order_inventory_db?sslmode=disable"
RETURNS_DB_DSN="postgresql://user:password@localhost:5432/returns_db?sslmode=disable"
CHECKPOINTER_DB_DSN="postgresql://user:password@localhost:5432/checkpoints_db?sslmode=disable"
USERS_DB_DSN="postgresql://user:password@localhost:5432/users_db?sslmode=disable"

CHAINLIT_AUTH_SECRET=<generate with: chainlit create-secret>
GUARDRAILS_API_KEY=<your-key>
```

> **Note:** Passwords with special characters (`^`, `&`, `!`, `%`, `@`) cause psycopg DSN parsing errors. Use alphanumeric passwords.

### 3. Initialise the database

```shell
python scripts/db_setup.py
python scripts/seed_data.py
```

### 4. (Optional) Switch to Ollama

```shell
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull llama3   # or: phi3 for lower resource usage

# Set in .env
LLM_PROVIDER=ollama
```

## Running the App

### Chainlit UI

```shell
# Always use the venv's chainlit — not ~/.local/bin/chainlit (Python 3.14)
.venv/bin/chainlit run chainlit_app.py --port 8001
```

Open [http://localhost:8001](http://localhost:8001).

### CLI (no UI)

```shell
python main.py
```

### FastAPI

```shell
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

## API Access

The FastAPI interface at `/chat` supports multi-turn sessions via a `session_id`.

### Smoke test (three turns)

```shell
# Turn 1 — start session
SESSION=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hi, what are your store hours?", "user_id": "user_001"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "Session: $SESSION"

# Turn 2 — continue session
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"what payment methods do you accept?\", \"session_id\": \"$SESSION\", \"user_id\": \"user_001\"}" \
  | python3 -m json.tool

# Turn 3 — trigger recommendation routing
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"show me wireless headphones under 200\", \"session_id\": \"$SESSION\", \"user_id\": \"user_001\"}" \
  | python3 -m json.tool
```

## Testing

### Unit tests (CI-compatible)

```shell
python -m tests.test_customer_support_agent
```

### Quick coordinator routing test

```shell
python -m tests.test_coordinator_agent_quick
```

Expected output:

```
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
```

### Full coordinator tests (requires Ollama)

```shell
python -m tests.test_coordinator_agent
```

> These are excluded from CI as they depend on a running Ollama instance.

### Customer support evaluation (DeepEval)

```shell
python tests/eval_customer_support.py
```

## CI/CD Pipeline

The GitHub Actions pipeline (`.github/workflows/agent-pipeline.yml`) runs on every push to `main`, `dev`, and `feature/**` branches.

| Job | Tool | Purpose |
|---|---|---|
| `secret-detection` | gitleaks | Scan git history for leaked secrets |
| `lint` | ruff | Lint `agents/` directory |
| `vulnerability-scan` | pip-audit | Check `requirements.txt` for CVEs |
| `build-and-push` | Podman + Quay.io | Build image and push with CalVer tag |
| `deploy` | appleboy/ssh-action | Pull new image and redeploy on EC2 |

The deploy job pulls the new image before stopping the running container — a failed pull leaves the existing container untouched.

## Container Build

### Build locally

```shell
podman build -t shopbot --file Containerfile-ShopBot .
```

### Run locally

```shell
podman run \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -p 8001:8001 \
  shopbot
```

### Pull from registry

```shell
podman pull quay.io/iamgini/shopbot:latest
```

## Configuration Reference

All constants are in `config.py`:

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `gpt-4o-mini` | Model used by all agents |
| `LLM_TEMPERATURE` | `0.0` | Deterministic outputs |
| `LLM_PROVIDER` | `openai` | Set to `ollama` for local LLM |
| `COORDINATOR_NODE` | `coordinator` | LangGraph node name |
| `ROUTE_SALES` | `sales` | Routing label |
| `ROUTE_RECOMMEND` | `recommend` | Routing label |
| `ROUTE_SUPPORT` | `customer_support` | Routing label |
| `ROUTE_ORDER_INVENTORY` | `order_inventory` | Routing label |
| `ROUTE_RETURNS` | `returns_refunds` | Routing label |


## Module Coverage

This project covers all four course modules:

### Module 1 — Responsible & Explainable AI
- FAQ-based responses with confidence scoring
- Escalation to human agent when confidence is below threshold
- Structured output with `response`, `escalate`, `confidence`, and `explanation` fields
- Guardrails validators for PII detection, toxicity filtering, and prompt injection detection

### Module 2 — AI & Cybersecurity
- No direct database access from agents — all queries go through tool wrappers
- Controlled knowledge source (FAQ JSON, no hallucination beyond the knowledge base)
- Structured logging with optional S3 upload (Garage-compatible)
- Secret management via dotenvx; `DOTENV_PRIVATE_KEY_CI` never stored in any `.env` file
- Cloudflare WAF + DDoS protection in front of the deployment

### Module 3 — Architecting Agentic AI
- Stateless node design compatible with LangGraph's StateGraph
- Shared `AgentState` TypedDict enables clean orchestration across agents
- Coordinator uses keyword heuristics (fast path) + LLM fallback for routing
- Each agent independently developed and testable in isolation

### Module 4 — Integration & Deployment
- Chainlit web UI + FastAPI programmatic interface
- Containerised with Podman; image published to Quay.io
- GitHub Actions CI/CD with security gates (gitleaks, pip-audit, ruff, Trivy)
- Deployed to AWS EC2 (ap-southeast-1) behind Nginx and Cloudflare
- Switchable LLM backend: OpenAI (production) or Ollama (local/free)