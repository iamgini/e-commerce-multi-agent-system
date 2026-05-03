import json
from ddgs import results
import pytest
from unittest.mock import patch, MagicMock

from tools.sales_tools import *

# ─────────────────────────────────────────────
# find_product
# ─────────────────────────────────────────────
@patch("tools.sales_tools.product_db")
@pytest.mark.parametrize(
    "query,db_return,expected_name,expected_len",
    [
        (
            "xbox",
            [
                {"id": 51, "name": "Microsoft Xbox Series X", "price": 499.99, "stock": 45, "category": 11, "rating": 4.8},
                {"id": 234, "name": "Xbox Series S", "price": 299.99, "stock": 65, "category": 11, "rating": 4.7},
                {"id": 243, "name": "Xbox Series S 1TB Carbon Black", "price": 349.99, "stock": 50, "category": 11, "rating": 4.7},
                ],
            [
                "Microsoft Xbox Series X",
                "Xbox Series S",
                "Xbox Series S 1TB Carbon Black"
                ],
            3
        ),
        (
            "bombs",
            [],
            "No products found matching 'bombs'",
            0
        )
    ]
)
def test_find_product(
    mock_db, query, db_return, expected_name, expected_len
):
    mock_db.search_products.return_value = db_return

    result = find_product.invoke({
        "config": {},
        "query": query
    })

    if expected_len != 0:
        parsed = json.loads(result)
        assert len(parsed) == expected_len
        assert [p["name"] for p in parsed] == expected_name
    else:
        assert f"No products found matching '{query}'." in result
        
        
# ─────────────────────────────────────────────
# find_product_by_id
# ─────────────────────────────────────────────
@patch("tools.sales_tools.product_db")
@pytest.mark.parametrize(
    "product_id,db_return,expect_json,expected_name",
    [
        (1, {"id": 1, "name": "Logitech MX Master 3", "description": "Ergonomic wireless mouse with precision tracking and customizable controls for productivity pros.", "price": 99.99, "stock": 150, "category": 1, "rating": 4.8}, True, "Logitech MX Master 3"),
        (2, {"id": 2, "name": "Razer DeathAdder V2", "description": "High-precision gaming mouse with optical switches and ergonomic grip for competitive play.", "price": 69.99, "stock": 120, "category": 1, "rating": 4.7}, True, "Razer DeathAdder V2"),
        (999, None, False, None),
    ]
)
def test_find_product_by_id(
    mock_db, product_id, db_return, expect_json, expected_name
):
    mock_db.get_product_by_id.side_effect = lambda pid: db_return

    result = find_product_by_id.invoke({
        "config": {},
        "product_id": product_id
    })
    
    if expect_json:
        parsed = json.loads(result)

        assert isinstance(parsed, list)
        assert parsed[0]["name"] == expected_name

    else:
        assert f"No products found matching ID: {product_id}." in result
    

# ─────────────────────────────────────────────
# view_cart
# ─────────────────────────────────────────────
@patch("tools.sales_tools.cart_db")
@pytest.mark.parametrize(
    "user_id,db_return,expected_total,expected_items",
    [
        (
            ## Multiple Items
            "alice",
            {
                "items": [
                    {"id": 1, "name": "Logitech MX Master 3", "qty": 1, "price": 99.99},
                    {"id": 2, "name": "Razer DeathAdder V2", "qty": 1, "price": 69.99},
                ],
                "total": 169.98,
            },
            169.98,
            2,
        ),
        (
            ## Single Item
            "brad",
            {
                "items": [
                    {"id": 1, "name": "Keyboard", "qty": 1, "price": 99.99},
                ],
                "total": 99.99,
            },
            99.99,
            1,
        ),

        ## No Items
        (
            "charlie",
            {
                "items": [],
                "total": 0,
            },
            0,
            0,
        ),
    ]
)
def test_view_cart(
    mock_db, user_id, db_return, expected_total, expected_items
):
    mock_db.get_cart_summary.return_value = db_return

    result = view_cart.invoke({
        "config": {},
        "user_id": user_id
    })
    
    parsed = json.loads(result)

    assert isinstance(parsed, dict)
    assert parsed["total"] == expected_total
    assert len(parsed["items"]) == expected_items


# ─────────────────────────────────────────────
# add_to_cart
# ─────────────────────────────────────────────
@patch("tools.sales_tools.product_db")
@patch("tools.sales_tools.cart_db")
@pytest.mark.parametrize(
    "product_id,db_return,quantity,expected_case,expected_key",
    # [
    #     (1, {"id": 1, "name": "Logitech MX Master 3", "description": "Ergonomic wireless mouse with precision tracking and customizable controls for productivity pros.", "price": 99.99, "stock": 150, "category": 1, "rating": 4.8}, True, "Logitech MX Master 3"),
    #     (2, {"id": 2, "name": "Razer DeathAdder V2", "description": "High-precision gaming mouse with optical switches and ergonomic grip for competitive play.", "price": 69.99, "stock": 120, "category": 1, "rating": 4.7}, True, "Razer DeathAdder V2"),
    #     (999, None, False, None),
    # ]
    [
        ## Case 1: invalid quantity
        (
            1,
            {"id": 1, "name": "Logitech MX Master 3", "stock": 1, "price": 99.99},
            0,
            "invalid_quantity",
            "Quantity must be at least 1.",
        ),

        # Case 2: product not found
        (
            999,
            None,
            1,
            "not_found",
            "No products found matching ID: 999.",
        ),

        # Case 3: insufficient stock
        (
            1,
            {"id": 1, "name": "Logitech MX Master 3", "stock": 1, "price": 99.99},
            5,
            "no_stock",
            "Sorry, only 1 unit(s) of 'Logitech MX Master 3'",
        ),

        # Case 4: successful add (normal)
        (
            2,
            {"id": 2, "name": "Razer DeathAdder V2", "stock": 120, "price": 69.99},
            2,
            "json",
            None,
        ),
    ]
)
def test_add_to_cart(
    mock_product_db, mock_cart_db, product_id, db_return, quantity, expected_case, expected_key
):
    mock_product_db.get_product_by_id.return_value = db_return

    mock_cart_db.add_item_to_cart.return_value = {
        "message": f"Added {quantity}x 'dummy_product' to cart.",
        "total": 199.98,
        "item_count": 2,
    }

    result = add_to_cart.invoke({
        "config": {},
        "user_id": "alice",
        "product_id": product_id,
        "quantity": quantity
    })
    
    if expected_case == "json":
        parsed = json.loads(result)

        assert "message" in parsed
        assert parsed["cart_total"] == 138.98
        assert parsed["cart_item_count"] == 2
        
    elif expected_case == "invalid_quantity":
        assert "Quantity must be at least 1." in result
    
    elif expected_case == "no_stock":
        assert "Sorry, only 1 unit(s) of 'Logitech MX Master 3'" in result
        
    elif expected_case == "not_found":
        assert "No products found matching ID: 999." in result
        
    else:
        pass
        

# ─────────────────────────────────────────────
# remove_from_cart
# ─────────────────────────────────────────────
@patch("tools.sales_tools.cart_db")
@pytest.mark.parametrize(
    "user_id,product_id,db_return,expected_total,expected_count",
    [
        (
            "alice",
            1,
            {"total": 69.99, "item_count": 1},
            69.99,
            1,
        ),
        (
            "brad",
            2,
            {"total": 0, "item_count": 0},
            0,
            0,
        ),
        (
            "charlie",
            3,
            {"total": 1399.97, "item_count": 3},
            1399.97,
            3,
        ),
    ]
)
def test_remove_from_cart(
    mock_db, user_id, product_id, db_return, expected_total, expected_count
):
    mock_db.remove_item_from_cart.return_value = db_return

    result = remove_from_cart.invoke({
        "config": {},
        "user_id": user_id,
        "product_id": product_id,
    })

    parsed = json.loads(result)

    assert parsed["message"] == f"Product {product_id} removed from cart."
    assert parsed["cart_total"] == expected_total
    assert parsed["cart_item_count"] == expected_count
    

