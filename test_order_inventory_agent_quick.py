import json
import os
import sys

ROOT = os.path.dirname(__file__)
AGENT_DIR = os.path.join(ROOT, "agent_order_inventory")
sys.path.insert(0, AGENT_DIR)

from database.db_setup import initialize_database
from database import order_inventory_db


def pretty(data):
    print(json.dumps(data, indent=2, default=str))


def main():
    initialize_database()

    print("\n" + "=" * 70)
    print("QUICK TEST - ORDER & INVENTORY AGENT BACKEND")
    print("=" * 70)

    print("\n1) View current stock")
    stock = order_inventory_db.view_stock_by_product()
    pretty(stock[:3] if isinstance(stock, list) else stock)

    print("\n2) Create purchase order")
    purchase_order = order_inventory_db.create_purchase_order(
        supplier_name="Tech Supplies Ltd",
        items=[
            {"product_id": 1, "quantity": 10, "unit_cost": 12.50},
            {"product_id": 2, "quantity": 5, "unit_cost": 20.00},
        ],
        status="draft",
        expected_date="2026-04-15",
        notes="Quick test purchase order",
    )
    pretty(purchase_order)

    print("\n3) Update purchase order")
    updated_purchase_order = order_inventory_db.update_purchase_order(
        purchase_order_id=purchase_order["id"],
        status="approved",
        notes="Approved in test script",
    )
    pretty(updated_purchase_order)

    print("\n4) Create supply order")
    supply_order = order_inventory_db.create_supply_order(
        supplier_name="Warehouse Partner",
        items=[
            {"product_id": 1, "quantity": 7},
        ],
        status="draft",
        reference="SUP-TEST-001",
        notes="Quick test supply order",
    )
    pretty(supply_order)

    print("\n5) Update supply order")
    updated_supply_order = order_inventory_db.update_supply_order(
        supply_order_id=supply_order["id"],
        status="in_transit",
        notes="Shipment dispatched",
    )
    pretty(updated_supply_order)

    print("\n6) Receive stock")
    stock_after_receipt = order_inventory_db.receive_stock(
        product_id=1,
        quantity=4,
        reference_type="supply_order",
        reference_id=supply_order["id"],
        note="Stock received in quick test",
    )
    pretty(stock_after_receipt)

    print("\n7) Reduce stock on customer sale")
    customer_order = order_inventory_db.reduce_stock_on_customer_sale(
        user_id="test_user",
        items=[
            {"product_id": 1, "quantity": 2},
        ],
        total_amount=0.0,
        status="confirmed",
    )
    pretty(customer_order)

    print("\n8) View order history")
    history = order_inventory_db.get_user_orders("test_user")
    pretty(history)

    print("\n9) View order status")
    order_status = order_inventory_db.get_order(customer_order["id"])
    pretty(order_status)


if __name__ == "__main__":
    main()
