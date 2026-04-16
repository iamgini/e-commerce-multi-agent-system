import json
import os
import sys
from datetime import date, datetime
from typing import Annotated, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from helpers.database import order_inventory_db

def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@tool
def create_purchase_order(
    supplier_name: str,
    items_json: str,
    status: str = "draft",
    expected_date: Optional[str] = None,
    notes: str = "",
) -> str:
    """
    Create a purchase order.

    Args:
        supplier_name: Supplier name.
        items_json: JSON array of items with product_id, quantity, unit_cost.
        status: Purchase order status.
        expected_date: Optional expected date in YYYY-MM-DD format.
        notes: Optional notes.

    Returns:
        JSON string of the created purchase order.
    """
    items = json.loads(items_json)
    order = order_inventory_db.create_purchase_order(
        supplier_name=supplier_name,
        items=items,
        status=status,
        expected_date=expected_date,
        notes=notes,
    )
   # return json.dumps(order, indent=2)
    return json.dumps(order, indent=2, default=_json_default)


@tool
def list_purchase_orders(status: Optional[str] = None) -> str:
    """
    List purchase orders, optionally filtered by status.
    """
    orders = order_inventory_db.list_purchase_orders(status=status)
    #return json.dumps(orders, indent=2)
    #return json.dumps(order, indent=2, default=_json_default)
    return json.dumps(orders, indent=2, default=_json_default)


@tool
def update_purchase_order(
    purchase_order_id: int,
    status: Optional[str] = None,
    expected_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update a purchase order.
    """
    order = order_inventory_db.update_purchase_order(
        purchase_order_id=purchase_order_id,
        status=status,
        expected_date=expected_date,
        notes=notes,
    )
    #return json.dumps(order, indent=2)
    return json.dumps(order, indent=2, default=_json_default)

@tool
def create_supply_order(
    supplier_name: str,
    items_json: str,
    status: str = "draft",
    reference: str = "",
    notes: str = "",
) -> str:
    """
    Create a supply order.

    Args:
        supplier_name: Supplier name.
        items_json: JSON array of items with product_id and quantity.
        status: Supply order status.
        reference: Optional external reference.
        notes: Optional notes.

    Returns:
        JSON string of the created supply order.
    """
    items = json.loads(items_json)
    order = order_inventory_db.create_supply_order(
        supplier_name=supplier_name,
        items=items,
        status=status,
        reference=reference,
        notes=notes,
    )
    #return json.dumps(order, indent=2)
    return json.dumps(order, indent=2, default=_json_default)


@tool
def list_supply_orders(status: Optional[str] = None) -> str:
    """
    List supply orders, optionally filtered by status.
    """
    orders = order_inventory_db.list_supply_orders(status=status)
    #return json.dumps(orders, indent=2)
    #return json.dumps(order, indent=2, default=_json_default)
    return json.dumps(orders, indent=2, default=_json_default)


@tool
def update_supply_order(
    supply_order_id: int,
    status: Optional[str] = None,
    reference: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update a supply order.
    """
    order = order_inventory_db.update_supply_order(
        supply_order_id=supply_order_id,
        status=status,
        reference=reference,
        notes=notes,
    )
   # return json.dumps(order, indent=2)
    return json.dumps(order, indent=2, default=_json_default)


@tool
def receive_stock(
    product_id: int,
    quantity: int,
    reference_type: str = "goods_receipt",
    reference_id: Optional[int] = None,
    note: str = "",
) -> str:
    """
    Receive stock into inventory for a product.
    """
    product = order_inventory_db.receive_stock(
        product_id=product_id,
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
    )
    #return json.dumps(product, indent=2)
    #return json.dumps(order, indent=2, default=_json_default)
    return json.dumps(product, indent=2, default=_json_default)


@tool
def reduce_stock_on_customer_sale(
    user_id: Annotated[str, InjectedState("user_id")],
    items_json: str,
    total_amount: float = 0.0,
    status: str = "confirmed",
) -> str:
    """
    Create a customer order and reduce stock from inventory.

    Args:
        user_id: Automatically injected from session state.
        items_json: JSON array of items with product_id and quantity.
        total_amount: Optional override for total amount.
        status: Order status.

    Returns:
        JSON string of the created customer order.
    """
    items = json.loads(items_json)
    order = order_inventory_db.reduce_stock_on_customer_sale(
        user_id=user_id,
        items=items,
        total_amount=total_amount,
        status=status,
    )
    #return json.dumps(order, indent=2)
    return json.dumps(order, indent=2, default=_json_default)


@tool
def view_stock_by_product(
    product_id: Optional[int] = None,
    query: Optional[str] = None,
    low_stock_only: bool = False,
) -> str:
    """
    View stock by product ID or search query. Can also show only low-stock items.
    """
    results = order_inventory_db.view_stock_by_product(
        product_id=product_id,
        query=query,
        low_stock_only=low_stock_only,
    )
    #return json.dumps(results, indent=2)
    #return json.dumps(order, indent=2, default=_json_default)
    return json.dumps(results, indent=2, default=_json_default)


@tool
def view_order_history(
    user_id: Annotated[str, InjectedState("user_id")],
) -> str:
    """
    View the current user's order history.
    """
    orders = order_inventory_db.get_user_orders(user_id)
    #return json.dumps(orders, indent=2)
    #return json.dumps(order, indent=2, default=_json_default)
    return json.dumps(orders, indent=2, default=_json_default)


@tool
def view_order_status(order_id: int) -> str:
    """
    View one order with its status and items.
    """
    order = order_inventory_db.get_order(order_id)
    #return json.dumps(order, indent=2)
    return json.dumps(order, indent=2, default=_json_default)


ORDER_INVENTORY_TOOLS = [
    create_purchase_order,
    list_purchase_orders,
    update_purchase_order,
    create_supply_order,
    list_supply_orders,
    update_supply_order,
    receive_stock,
    reduce_stock_on_customer_sale,
    view_stock_by_product,
    view_order_history,
    view_order_status,
]
