from langchain.tools import tool
from langgraph.prebuilt import ToolNode
import sqlite3
# from mockdata import PRODUCT_DB
# import difflib


# @tool
# def search_products(query: str):
#     """Searches the product catalog using the user query. 
#     Retrieves products with names or categories similar to the query."""
#     query = query.lower()
#     results = [
#         product for product in PRODUCT_DB 
#         if query in product['name'].lower() or 
#            query in product['category'].lower() or 
#            difflib.SequenceMatcher(None, query, product['name'].lower()).ratio() > 0.6 or 
#            difflib.SequenceMatcher(None, query, product['category'].lower()).ratio() > 0.6
#     ]
#     return results if results else "No products found matching that query."


# @tool
# def get_product_details(product_id: int):
#     """Get full specifications and stock levels for a specific product ID."""
#     product = next((product for product in PRODUCT_DB if product['id'] == product_id), None)
#     return product if product else "Product not found."

# tools = [search_products, get_product_details]


def query_products_db(filters: dict):
    """
    Searches for products in the products database by incorporating filters given in the users' query
    with an SQL statement. Retrieves all products that fulfils the filter criteria.
    """
    conn = sqlite3.connect("./data/mockdata")
    cursor = conn.cursor()
    
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if filters.product_category:
        query += " AND product_category = ?"
        params.append(filters.product_category)

    if filters.product_subcategory:
        query += " AND product_subcategory = ?"
        params.append(filters.product_subcategory)

    if filters.brand_name:
        query += " AND brand_name = ?"
        params.append(filters.brand_name)
    
    if filters.min_price:
        query += " AND price >= ?"
        params.append(filters.min_price)
        
    if filters.max_price:
        query += " AND price <= ?"
        params.append(filters.max_price)
        
    if filters.min_rating:
        query += " AND rating >= ?"
        params.append(filters.min_rating)
        
    if filters.max_rating:
        query += " AND rating <= ?"
        params.append(filters.max_rating)

    cursor.execute(query, params)
    return cursor.fetchall()


# tools = [query_products_db]
# tool_node = ToolNode(tools)
