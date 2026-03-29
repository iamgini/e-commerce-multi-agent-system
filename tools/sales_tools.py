import json
import os
import sys
from typing import Annotated, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from helpers.database import product_db

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from helpers.database import cart_db

# ── Product lookup tool ────────────────────────────────────────────────────────


@tool
def find_product(query: str) -> str:
    """
    Find a product by name or description and return its ID, price, and stock.

    Use this tool BEFORE calling add_to_cart whenever you have a product name
    but not yet a product_id. The search is fuzzy — partial names such as
    "wireless headphones" will correctly match
    "Wireless Noise-Cancelling Headphones".

    Returns up to 5 candidates ranked by relevance so you can pick the best
    match or ask the customer to confirm when multiple options exist.

    Args:
        query: Product name or descriptive phrase, e.g. "wireless headphones",
               "yoga mat", "python book".

    Returns:
        A JSON array of matches, each containing:
          id       - integer product ID required by add_to_cart
          name     - full product name
          price    - unit price in USD
          stock    - units currently available
          rating   - average customer rating
          category - product category name
        Or a plain-text message if no products are found.
    """
    results = product_db.search_products(query, limit=5)
    if not results:
        return f"No products found matching '{query}'."

    compact = [
        {
            "id": r["id"],
            "name": r["name"],
            "price": r["price"],
            "stock": r["stock"],
            "rating": r["rating"],
            "category": r["category"],
        }
        for r in results
    ]
    return json.dumps(compact, indent=2)


# ── Cart tools ─────────────────────────────────────────────────────────────────


@tool
def view_cart(user_id: Annotated[str, InjectedState("user_id")]) -> str:
    """
    Retrieve the current contents of a user's shopping cart,
    including all items, quantities, unit prices, and the grand total.

    Args:
        user_id: The unique identifier for the customer.

    Returns:
        A JSON string summarising the cart.
    """
    summary = cart_db.get_cart_summary(user_id)
    return json.dumps(summary, indent=2)


@tool
def add_to_cart(
    user_id: Annotated[str, InjectedState("user_id")],
    product_id: int,
    quantity: int = 1,
) -> str:
    """
    Add a product to the user's shopping cart.
    If the product is already in the cart its quantity is incremented.
    Validates that sufficient stock is available before adding.

    Args:
        user_id:    The unique identifier for the customer.
        product_id: The ID of the product to add.
        quantity:   Number of units to add (default 1).

    Returns:
        A confirmation message with the updated cart total, or an error.
    """
    if quantity <= 0:
        return "Quantity must be at least 1."

    product = product_db.get_product_by_id(product_id)
    if not product:
        return f"Product ID {product_id} does not exist."
    if product["stock"] < quantity:
        return (
            f"Sorry, only {product['stock']} unit(s) of '{product['name']}' "
            "are in stock."
        )

    summary = cart_db.add_item_to_cart(
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=product["price"],
    )
    return json.dumps(
        {
            "message": f"Added {quantity}x '{product['name']}' to cart.",
            "cart_total": summary["total"],
            "cart_item_count": summary["item_count"],
        },
        indent=2,
    )


@tool
def remove_from_cart(
    user_id: Annotated[str, InjectedState("user_id")], product_id: int
) -> str:
    """
    Remove a product line entirely from the user's cart.

    Args:
        user_id:    The unique identifier for the customer.
        product_id: The ID of the product to remove.

    Returns:
        A confirmation with the updated cart total.
    """
    summary = cart_db.remove_item_from_cart(user_id, product_id)
    return json.dumps(
        {
            "message": f"Product {product_id} removed from cart.",
            "cart_total": summary["total"],
            "cart_item_count": summary["item_count"],
        },
        indent=2,
    )


@tool
def update_cart_quantity(
    user_id: Annotated[str, InjectedState("user_id")], product_id: int, quantity: int
) -> str:
    """
    Change the quantity of a specific product already in the cart.
    Setting quantity to 0 removes the item.

    Args:
        user_id:    The unique identifier for the customer.
        product_id: The ID of the product to update.
        quantity:   New desired quantity (0 to remove).

    Returns:
        A JSON string with the updated cart state.
    """
    product = product_db.get_product_by_id(product_id)
    if product and quantity > product["stock"]:
        return f"Cannot set quantity to {quantity}: only {product['stock']} in stock."

    summary = cart_db.update_item_quantity(user_id, product_id, quantity)
    action = "removed" if quantity == 0 else f"updated to {quantity}"
    return json.dumps(
        {
            "message": f"Product {product_id} quantity {action}.",
            "cart_total": summary["total"],
            "cart_item_count": summary["item_count"],
        },
        indent=2,
    )


# ── Discount tools ─────────────────────────────────────────────────────────────


@tool
def validate_discount_code(code: str) -> str:
    """
    Check whether a discount/promo code is valid and return its value.

    Args:
        code: The promotional code entered by the customer (case-insensitive).

    Returns:
        A message confirming the discount percentage, or an error for invalid codes.
    """
    fraction = cart_db.validate_discount_code(code)
    if fraction is None:
        return f"'{code}' is not a valid discount code."
    pct = int(fraction * 100)
    return f"Discount code '{code.upper()}' is valid – {pct}% off your order total."


@tool
def preview_order_total(
    user_id: Annotated[str, InjectedState("user_id")],
    discount_code: Optional[str] = None,
) -> str:
    """
    Show a price breakdown before the user commits to checkout.
    Includes subtotal, discount, and final amount due.

    Args:
        user_id:       The unique identifier for the customer.
        discount_code: Optional promo code to apply in the preview.

    Returns:
        A JSON string with the full pricing breakdown.
    """
    summary = cart_db.get_cart_summary(user_id)
    if summary["item_count"] == 0:
        return "Your cart is empty – nothing to preview."

    subtotal = summary["total"]
    discount_fraction = 0.0
    discount_note = "No discount applied."

    if discount_code:
        frac = cart_db.validate_discount_code(discount_code)
        if frac is None:
            discount_note = f"Invalid discount code '{discount_code}'."
        else:
            discount_fraction = frac
            discount_note = (
                f"Code '{discount_code.upper()}' applied – {int(frac * 100)}% off."
            )

    discount_amount = round(subtotal * discount_fraction, 2)
    final = round(subtotal - discount_amount, 2)

    return json.dumps(
        {
            "subtotal": subtotal,
            "discount_note": discount_note,
            "discount_amount": discount_amount,
            "final_total": final,
            "item_count": summary["item_count"],
        },
        indent=2,
    )


# ── Checkout tool ──────────────────────────────────────────────────────────────


@tool
def checkout(
    user_id: Annotated[str, InjectedState("user_id")],
    discount_code: Optional[str] = None,
) -> str:
    """
    Place an order for all items currently in the user's cart.
    Validates stock levels, applies the discount code if provided,
    creates an order record, and clears the cart.

    Args:
        user_id:       The unique identifier for the customer.
        discount_code: Optional promotional code to apply.

    Returns:
        A JSON string with the confirmed order details, or an error message.
    """
    try:
        # Re-validate stock for every item in the cart
        cart = cart_db.get_cart_summary(user_id)
        if cart["item_count"] == 0:
            return "Cannot checkout: your cart is empty."

        # Fetch every product record once for stock validation.
        # Reuse those records to build the product_names dict so create_order
        # can snapshot real names into order_items rather than "Product #<id>".
        product_records = {}
        for item in cart["items"]:
            product = product_db.get_product_by_id(item["product_id"])
            if not product:
                return f"Product ID {item['product_id']} is no longer available."
            if product["stock"] < item["quantity"]:
                return (
                    f"Insufficient stock for '{product['name']}' "
                    f"(requested {item['quantity']}, available {product['stock']})."
                )

            product_records[item["product_id"]] = product

        # Build {product_id: product_name} from already-fetched records.
        product_names = {pid: p["name"] for pid, p in product_records.items()}

        # Create the order
        order = cart_db.create_order(user_id, discount_code, product_names)

        # Decrement stock and record purchase history for recommendations
        for item in cart["items"]:
            product_db.reduce_stock(item["product_id"], item["quantity"])
            product_db.record_purchase_history(user_id, item["product_id"])

        # Clear the cart
        cart_db.clear_cart(user_id)

        return json.dumps(
            {
                "message": "Order placed successfully!",
                "order_id": order["order_id"],
                "items_purchased": len(order["items"]),
                "subtotal": order["total_amount"],
                "discount_applied": order["discount_amount"],
                "total_charged": order["final_amount"],
                "status": order["status"],
            },
            indent=2,
        )

    except ValueError as exc:
        return f"Checkout failed: {exc}"


# ── Order history tool ─────────────────────────────────────────────────────────


@tool
def get_order_history(user_id: Annotated[str, InjectedState("user_id")]) -> str:
    """
    Retrieve a summary of all past orders placed by the user.

    Args:
        user_id: The unique identifier for the customer.

    Returns:
        A JSON string listing orders (ID, date, total, status).
    """
    orders = cart_db.get_user_orders(user_id)
    if not orders:
        return "No past orders found for this account."
    return json.dumps(orders, indent=2)


@tool
def get_order_details(order_id: int) -> str:
    """
    Fetch full details for a specific order, including line items.

    Args:
        order_id: The unique integer order ID.

    Returns:
        A JSON string with the full order record.
    """
    order = cart_db.get_order(order_id)
    if not order:
        return f"Order #{order_id} not found."
    return json.dumps(order, indent=2)


# ── Convenience export ─────────────────────────────────────────────────────────

SALES_TOOLS = [
    find_product,
    view_cart,
    add_to_cart,
    remove_from_cart,
    update_cart_quantity,
    validate_discount_code,
    preview_order_total,
    checkout,
    get_order_history,
    get_order_details,
]
