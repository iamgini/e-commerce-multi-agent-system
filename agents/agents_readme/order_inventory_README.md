# Order & Inventory Management Agent

This package has following:

- a **separate top-level folder** 
- split into **agents / tools / database** 
- minimal database setup, without extra schema or seed files scattered everywhere

## Folder structure

```text
agent_order_inventory/
├── __init__.py
├── config.py
├── config_db.py
├── README.md
├── requirements.txt
├── data/
│   └── order_inventory.db
├── agents/
│   ├── __init__.py
│   └── order_inventory_agent.py
├── tools/
│   ├── __init__.py
│   └── order_inventory_tools.py
└── database/
    ├── __init__.py
    ├── db_setup.py
    └── order_inventory_db.py
```

## What each file does

### `config.py`
Holds the OpenAI model settings for the agent.

### `config_db.py`
Defines where the SQLite database file lives.

### `agents/order_inventory_agent.py`
The main agent node:
- defines a system prompt
- binds tools to an LLM
- exposes `order_inventory_agent_node(...)`

### `tools/order_inventory_tools.py`
LangChain tool wrappers around the database functions.

### `database/order_inventory_db.py`
The actual operational logic for:
- create/list/update purchase orders
- create/list/update supply orders
- receive stock into inventory
- reduce stock on customer sale
- view stock by product
- view order history and status

### `database/db_setup.py`
Creates the SQLite tables and inserts a tiny bit of demo data if the database is empty.

### `data/order_inventory.db`
The SQLite database file used by this package.

## Database tables

The package keeps everything in a single SQLite database:

- `inventory_products`
- `customer_orders`
- `customer_order_items`
- `purchase_orders`
- `purchase_order_items`
- `supply_orders`
- `supply_order_items`
- `inventory_movements`

## Main operations supported

- `create_purchase_order`
- `list_purchase_orders`
- `update_purchase_order`
- `create_supply_order`
- `list_supply_orders`
- `update_supply_order`
- `receive_stock`
- `reduce_stock_on_customer_sale`
- `view_stock_by_product`
- `view_order_history`
- `view_order_status`

## How to initialise the database

From inside `agent_order_inventory/`:

```bash
python database/db_setup.py
```

That creates `data/order_inventory.db` and seeds a few demo products if the database is empty.

## How to use this package

Example import:

```python
from agent_order_inventory.agents.order_inventory_agent import order_inventory_agent_node
```

Example direct database use:

```python
from agent_order_inventory.database import order_inventory_db

print(order_inventory_db.view_stock_by_product(query="mouse"))
print(order_inventory_db.list_purchase_orders())
```

