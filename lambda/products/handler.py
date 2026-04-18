"""Lambda handler for Product tools — deployed behind AgentCore Gateway."""

from __future__ import annotations

import json
from typing import Any

# In production, this would query DynamoDB
# For demo, using the same in-memory data
from data import PRODUCTS


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for product-related MCP tool calls."""
    tool_name = event.get("tool_name") or event.get("name")
    params = event.get("parameters") or event.get("input", {})

    if tool_name == "search_products":
        return search_products(params)
    elif tool_name == "get_product_details":
        return get_product_details(params)
    elif tool_name == "get_recommendations":
        return get_recommendations(params)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def search_products(params: dict) -> dict:
    query = params.get("query", "").lower()
    category = params.get("category", "")
    min_price = float(params.get("min_price", 0))
    max_price = float(params.get("max_price", 99999))

    results = []
    for p in PRODUCTS:
        if category and p["category"].lower() != category.lower():
            continue
        if p["price"] < min_price or p["price"] > max_price:
            continue
        if query:
            searchable = f"{p['name']} {p['description']} {p['category']} {p['subcategory']}".lower()
            if query not in searchable:
                continue
        results.append({
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "rating": p["rating"],
            "reviews": p["reviews"],
            "in_stock": p["in_stock"],
        })

    return {"products": results[:10], "total_results": len(results)}


def get_product_details(params: dict) -> dict:
    product_id = params.get("product_id", "")
    for p in PRODUCTS:
        if p["id"] == product_id:
            return {"product": p}
    return {"error": f"Product '{product_id}' not found"}


def get_recommendations(params: dict) -> dict:
    category = params.get("category", "")
    limit = int(params.get("limit", 5))

    pool = PRODUCTS if not category else [p for p in PRODUCTS if p["category"].lower() == category.lower()]
    sorted_pool = sorted(pool, key=lambda p: (-p["rating"], -p["reviews"]))

    return {"recommendations": [
        {"id": p["id"], "name": p["name"], "price": p["price"], "rating": p["rating"]}
        for p in sorted_pool[:limit]
    ]}
