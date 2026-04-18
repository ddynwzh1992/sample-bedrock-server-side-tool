"""Lambda handler for Order tools — deployed behind AgentCore Gateway."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

# In production: DynamoDB table for orders
orders: dict[str, dict] = {}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for order-related MCP tool calls."""
    tool_name = event.get("tool_name") or event.get("name")
    params = event.get("parameters") or event.get("input", {})

    if tool_name == "checkout":
        return checkout(params)
    elif tool_name == "get_order_status":
        return get_order_status(params)
    elif tool_name == "list_orders":
        return list_orders(params)
    elif tool_name == "request_return":
        return request_return(params)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def checkout(params: dict) -> dict:
    customer_id = params["customer_id"]
    payment_method = params.get("payment_method", "credit_card")

    order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    orders[order_id] = {
        "order_id": order_id,
        "customer_id": customer_id,
        "payment_method": payment_method,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "estimated_delivery": (datetime.now() + timedelta(days=4)).isoformat(),
    }

    return {"status": "confirmed", "order_id": order_id, "estimated_delivery": "3-5 business days"}


def get_order_status(params: dict) -> dict:
    order_id = params["order_id"]
    if order_id not in orders:
        return {"error": f"Order '{order_id}' not found"}
    return {"order": orders[order_id]}


def list_orders(params: dict) -> dict:
    customer_id = params["customer_id"]
    customer_orders = [o for o in orders.values() if o["customer_id"] == customer_id]
    return {"orders": customer_orders, "count": len(customer_orders)}


def request_return(params: dict) -> dict:
    order_id = params["order_id"]
    reason = params.get("reason", "not specified")

    if order_id not in orders:
        return {"error": f"Order '{order_id}' not found"}

    order = orders[order_id]
    if order["status"] not in ("delivered", "shipped"):
        return {"error": f"Cannot return order with status '{order['status']}'"}

    return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    order["status"] = "return_requested"

    return {"status": "return_requested", "return_id": return_id, "order_id": order_id, "reason": reason}
