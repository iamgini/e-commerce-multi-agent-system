import json
import pytest
from unittest.mock import patch, MagicMock


from tools.recommendation_tools import *

# ─────────────────────────────────────────────
# search_products
# ─────────────────────────────────────────────
@patch("tools.recommendation_tools.product_db")
@pytest.mark.parametrize(
    "query,db_return,expected_name,expected_len",
    [
        (
            "xbox",
            [
                {"id": 30, "name": "Microsoft Xbox Series X"},
                {"id": 107, "name": "Xbox Series S"},
                {"id": 210, "name": "Xbox Series S 1TB Carbon Black"},
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
            "No products found matching your criteria.",
            0
        )
    ]
)
def test_search_products(
    mock_db, query, db_return, expected_name, expected_len
):
    mock_db.search_products.return_value = db_return

    result = search_products.invoke({
        "config": {},
        "query": query
    })

    if expected_len != 0:
        parsed = json.loads(result)
        assert len(parsed) == expected_len
        assert [p["name"] for p in parsed] == expected_name
    else:
        assert "No products found matching your criteria." in result


# ─────────────────────────────────────────────
# get_product_details
# ─────────────────────────────────────────────
@patch("tools.recommendation_tools.product_db")
@pytest.mark.parametrize(
    "product_id,db_return,expected_id,should_exist",
    [
        (1, {"id": 1, "name": "Logitech MX Master 3"}, 1, True),
        (2, {"id": 2, "name": "Razer DeathAdder V2"}, 2, True),
        (999, None, None, False),
    ]
)
def test_get_product_details(
    mock_db, product_id, db_return, expected_id, should_exist
):
    mock_db.get_product_by_id.side_effect = lambda pid: db_return

    result = get_product_details.invoke({
        "config": {},
        "product_id": product_id
    })
    
    if should_exist:
        parsed = json.loads(result)
        assert parsed["id"] == expected_id
    else:
        assert f"Product with ID {product_id} not found." in result


# ─────────────────────────────────────────────
# browse_by_category
# ─────────────────────────────────────────────
@patch("tools.recommendation_tools.product_db")
@pytest.mark.parametrize(
    "category,db_return,expected_len,expect_json",
    [
        ("Keyboards",
         [
            {"id": 4, "name": "Corsair K95 RGB Platinum"},
            {"id": 5, "name": "Logitech G915 TKL"}
            ], 
         2, True
         ),
        ("Toys", "No products found in category 'Toys'.", 0, False),
    ]
)
def test_browse_by_category(
    mock_db, category, db_return, expected_len, expect_json
):
    mock_db.get_products_by_category.return_value = db_return

    result = browse_by_category.invoke({
        "config": {},
        "category": category
    })
    
    if expect_json:
        parsed = json.loads(result)
        assert len(parsed) == expected_len
    else:
        assert f"No products found in category '{category}'." in result


# ─────────────────────────────────────────────
# list_categories
# ─────────────────────────────────────────────
@patch("tools.recommendation_tools.product_db")
@pytest.mark.parametrize(
    "db_return,expected_len",
    [
        (
            [
                {"name": "Mice & Pointing Devices", "description": "Computer mice and pointing input devices, covering productivity-grade wireless mice, gaming mice with high-precision sensors, and platform-optimised options for Mac and PC users."},
                {"name": "Wearables & Fitness", "description": "Smartwatches and fitness trackers offering health monitoring, built-in GPS, heart rate tracking, stress management tools, and seamless integration with iOS and Android ecosystems."},
                ],
         2)
    ],
)
def test_list_categories(
    mock_db, db_return, expected_len
):
    mock_db.get_all_categories.return_value = db_return

    result = list_categories.invoke({"config": {}})
    parsed = json.loads(result)

    assert isinstance(parsed, list)
    assert len(parsed) == expected_len


# ─────────────────────────────────────────────
# get_similar_products
# ─────────────────────────────────────────────
@patch("tools.recommendation_tools.product_db")
@pytest.mark.parametrize(
    "product_id,db_return,expected_len,should_json",
    [
        (1, [{"id": 2, "name": "Razer DeathAdder V2"}], 1, True),
        (8, [{"id": 7, "name": "Samsung Odyssey G7 27'"}], 1, True),
        (676, "No similar products found.", 0, False),
    ]
)
def test_get_similar_products(
    mock_db, product_id, db_return, expected_len, should_json
):
    mock_db.get_similar_products.return_value = db_return

    result = get_similar_products.invoke({
        "config": {},
        "product_id": product_id
    })
    
    if should_json:
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == expected_len
        
    else:
        assert "No similar products found." in result


# ─────────────────────────────────────────────
# get_trending_products
# ─────────────────────────────────────────────
@patch("tools.recommendation_tools.product_db")
@pytest.mark.parametrize(
    "db_return,expected_len,expected_first_id",
    [
        (
            [
                {"id": 19, "name": "Apple Watch Series 9", "rating": 4.9},
                {"id": 8, "name": "LG UltraGear 27GL850", "rating": 4.7},
                {"id": 21, "name": "Samsung Galaxy Watch 6", "rating": 4.6},
            ],
            3,
            19,
        ),
    ]
)
def test_get_trending_products(
    mock_db, db_return, expected_len, expected_first_id 
):
    mock_db.get_trending_products.return_value = db_return

    result = get_trending_products.invoke({"config": {}})
    parsed = json.loads(result)

    assert isinstance(parsed, list)
    assert len(parsed) == expected_len

    if expected_len > 0:
        assert parsed[0]["id"] == expected_first_id

