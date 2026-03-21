
## Agent Roles & Tasks

### 🧠 Coordinator

Routes each user message to the correct specialist agent using keyword
heuristics (fast path) or an LLM call (fallback), then returns control back to the user after each agent turn for the next message.

---

### 🔍 Product Recommendation Agent

**Function**: Helps users to *discover* products that match their needs,
preferences, and budget. Plays the role of an intelligent virtual shop assistant.

| Task | Description |
|------|-------------|
| **Keyword search** | Searches product name, description, and tags |
| **Filtered search** | Narrows results by category, max price, min rating |
| **Category browsing** | Lists top-rated products in a given category |
| **Trending products** | Surfaces globally popular / top-rated items |
| **Product detail** | Returns full spec sheet for a specific product |
| **Similar products** | Finds alternatives in the same category (cross-sell) |
| **Personalised picks** | Analyses purchase history to surface relevant items |
| **Comparison** | Compares two or more products on price, rating, features |

**Does not perform sales-related tasks.** (ie: Touch carts, Process orders, Apply discounts, etc...)

---

### 🛒 Sales Agent

**Function**: Converts user intent into confirmed purchases. Handles all
transactional interactions from cart management through checkout.

| Task | Description |
|------|-------------|
| **View cart** | Displays all items, quantities, and the running total |
| **Add to cart** | Validates stock, then adds a product line to the cart |
| **Remove from cart** | Deletes a product line entirely |
| **Update quantity** | Changes the number of units for a cart item |
| **Validate discount code** | Confirms a promo code is real and shows its value |
| **Preview order total** | Shows subtotal → discount → final amount before checkout |
| **Checkout** | Validates stock, creates an order, decrements stock, clears cart |
| **Order history** | Lists all past orders for the user |
| **Order details** | Fetches full line-item breakdown for a specific order |

**Does not perform product-recommendation tasks.** (ie: Search, recommend or describe products)

---

## Architecture

```

                    LangGraph Graph                       
   
  [START] ──▶ coordinator ──▶ recommendation_agent
                   │                    │
                   │                    │ (loops back)
                   │                    │
                   │           recommendation_tools
                   │       
                   │     
                   └──────▶ sales_agent
                   │               │
                   │               │  (loops back)
                   │               │                      
                   │          sales_tools                 
                   │                        
                   │                                      
                   └──────▶ [END]                         


SQLite Databases
├── products.db  (products, categories, user_purchase_history)
└── cart.db      (carts, cart_items, orders, order_items)
```

---

## File Structure

```
ecommerce_agents/
├── .env                             # Sensitive variables (ie: API key)
├── main.py                          # CLI entry point
├── config.py                        # Constants, discount codes
├── config_db.py                     # Seed data
├── requirements.txt
│
├── database/
│   ├── __init__.py
│   ├── db_setup.py                  # Schema creation
│   ├── product_db.py                # Product / category / history queries
│   └── cart_db.py                   # Cart / order CRUD + discount logic
│
├── agents/
│   ├── __init__.py
│   ├── coordinator.py               # Routing agent (keyword + LLM)
│   ├── recommendation_agent.py      # Recommendation agent node
│   └── sales_agent.py               # Sales agent node
│
├── tools/
│   ├── __init__.py
│   ├── recommendation_tools.py      # 7 tools for recommendation agent
│   └── sales_tools.py               # 10 tools for sales agent
│
└── graph/
    ├── __init__.py
    └── workflow.py                  # LangGraph StateGraph definition

```

---

## Setup & Running

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your OpenAI API key into .env file

# 3. Initialise databases (creates .db files & seeds products)
python main.py --setup-only

# 4. Start interactive session
python main.py
```

---

## Available Discount Codes

| Code | Discount |
|------|----------|
| `SAVE10` | 10% off |
| `SAVE20` | 20% off |
| `WELCOME` | 15% off |

---
