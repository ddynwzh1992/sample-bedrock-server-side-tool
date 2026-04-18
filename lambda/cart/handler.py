"""Lambda handler for Cart tools — deployed behind AgentCore Gateway."""

from __future__ import annotations

import json
import boto3
from typing import Any

# In production: DynamoDB table for cart state
# For demo: in-memory (note: Lambda cold starts will reset state)

carts: dict[str, list] = {}
applied_coupons: dict[str, str] = {}

COUPONS = {
    "WELCOME10": {"discount_percent": 10, "min_order": 0},
    "SAVE20": {"discount_percent": 20, "min_order": 100},
    "FREESHIP": {"discount_percent": 0, "free_shipping": True, "min_order": 50},
    "TECH15": {"discount_percent": 15, "min_order": 200, "category": "Electronics"},
    "SPRING25": {"discount_percent": 25, "min_order": 75},
}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for cart-related MCP tool calls."""
    tool_name = event.get("tool_name") or event.get("name")
    params = event.get("parameters") or event.get("input", {})

    if tool_name == "add_to_cart":
        return add_to_cart(params)
    elif tool_name == "view_cart":
        return view_cart(params)
    elif tool_name == "remove_from_cart":
        return remove_from_cart(params)
    elif tool_name == "apply_coupon":
        return apply_coupon(params)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def add_to_cart(params: dict) -> dict:
    customer_id = params["customer_id"]
    product_id = params["product_id"]
    quantity = int(params.get("quantity", 1))

    if customer_id not in carts:
        carts[customer_id] = []

    for item in carts[customer_id]:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            return {"status": "updated", "product_id": product_id, "new_quantity": item["quantity"]}

    carts[customer_id].append({"product_id": product_id, "quantity": quantity})
    return {"status": "added", "product_id": product_id, "quantity": quantity}


def view_cart(params: dict) -> dict:
    customer_id = params["customer_id"]
    items = carts.get(customer_id, [])
    coupon = applied_coupons.get(customer_id)
    return {"items": items, "item_count": len(items), "applied_coupon": coupon}


def remove_from_cart(params: dict) -> dict:
    customer_id = params["customer_id"]
    product_id = params["product_id"]

    if customer_id not in carts:
        return {"status": "cart_empty"}

    for i, item in enumerate(carts[customer_id]):
        if item["product_id"] == product_id:
            carts[customer_id].pop(i)
            return {"status": "removed", "product_id": product_id}

    return {"status": "not_found", "product_id": product_id}


def apply_coupon(params: dict) -> dict:
    customer_id = params["customer_id"]
    coupon_code = params["coupon_code"].upper()

    if coupon_code not in COUPONS:
        return {"status": "invalid", "coupon_code": coupon_code}

    applied_coupons[customer_id] = coupon_code
    return {"status": "applied", "coupon_code": coupon_code, "details": COUPONS[coupon_code]}
