"""E-Commerce Shopping Assistant — Local Demo with Strands Agents SDK.

This agent uses @tool decorated functions with in-memory mock data.
No AWS deployment needed — just `pip install strands-agents boto3` and run.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from agent.data import (
    PRODUCTS,
    COUPONS,
    carts,
    orders,
    applied_coupons,
    get_product_by_id,
    search_products_in_catalog,
    get_recommendations_for,
)

# ─── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are ShopAssist, an AI-powered e-commerce shopping assistant. You help customers browse products, manage their cart, place orders, and handle returns.

## Your Capabilities
- Search and browse products across Electronics, Home & Kitchen, Sports & Outdoors, and Books
- Provide personalized product recommendations
- Manage shopping cart (add, remove, view items)
- Apply discount coupons
- Process checkout and place orders
- Check order status and tracking
- Handle return requests

## Guidelines
- Be friendly, helpful, and concise
- When showing products, include name, price, rating, and a brief description
- Proactively suggest related products or deals when appropriate
- If a customer seems undecided, ask clarifying questions about their needs
- Always confirm before placing orders or processing returns
- Format prices as USD (e.g., $79.99)
- Use the customer ID "CUST-001" for the current session unless told otherwise

## Available Coupons (don't proactively share unless asked)
- WELCOME10: 10% off first order
- SAVE20: 20% off orders over $100
- SPRING25: 25% off orders over $75
- TECH15: 15% off Electronics over $200
- FREESHIP: Free shipping on orders over $50
"""

# ─── Tool Definitions ───────────────────────────────────────────────────────────


@tool
def search_products(query: str = "", category: str = "", min_price: float = 0, max_price: float = 99999) -> str:
    """Search the product catalog by keyword, category, and price range.

    Args:
        query: Search keywords (e.g., "wireless headphones", "running shoes")
        category: Filter by category — one of: Electronics, Home & Kitchen, Sports & Outdoors, Books
        min_price: Minimum price filter in USD
        max_price: Maximum price filter in USD
    """
    results = search_products_in_catalog(query, category, min_price, max_price)
    if not results:
        return "No products found matching your criteria."
    lines = [f"Found {len(results)} product(s):\n"]
    for p in results[:10]:  # Limit display to 10
        stock = "✓ In Stock" if p["in_stock"] else "✗ Out of Stock"
        lines.append(f"• [{p['id']}] {p['name']} — ${p['price']:.2f} | ★ {p['rating']} ({p['reviews']} reviews) | {stock}")
    if len(results) > 10:
        lines.append(f"\n... and {len(results) - 10} more results. Narrow your search for more specific results.")
    return "\n".join(lines)


@tool
def get_product_details(product_id: str) -> str:
    """Get detailed information about a specific product.

    Args:
        product_id: The product ID (e.g., "ELEC-001", "HOME-003")
    """
    p = get_product_by_id(product_id)
    if not p:
        return f"Product '{product_id}' not found."
    return (
        f"**{p['name']}** ({p['id']})\n"
        f"Category: {p['category']} > {p['subcategory']}\n"
        f"Price: ${p['price']:.2f}\n"
        f"Rating: ★ {p['rating']}/5 ({p['reviews']} reviews)\n"
        f"Stock: {'✓ In Stock' if p['in_stock'] else '✗ Out of Stock'}\n\n"
        f"Description: {p['description']}"
    )


@tool
def get_recommendations(category: str = "", limit: int = 5) -> str:
    """Get personalized product recommendations based on top ratings and popularity.

    Args:
        category: Optional category filter (Electronics, Home & Kitchen, Sports & Outdoors, Books)
        limit: Number of recommendations to return (default: 5)
    """
    recs = get_recommendations_for(category, limit)
    if not recs:
        return "No recommendations available for this category."
    lines = ["🌟 Recommended for you:\n"]
    for p in recs:
        lines.append(f"• [{p['id']}] {p['name']} — ${p['price']:.2f} | ★ {p['rating']} ({p['reviews']} reviews)")
    return "\n".join(lines)


@tool
def add_to_cart(customer_id: str, product_id: str, quantity: int = 1) -> str:
    """Add a product to the customer's shopping cart.

    Args:
        customer_id: Customer ID (e.g., "CUST-001")
        product_id: Product ID to add
        quantity: Number of items to add (default: 1)
    """
    product = get_product_by_id(product_id)
    if not product:
        return f"Product '{product_id}' not found."
    if not product["in_stock"]:
        return f"Sorry, '{product['name']}' is currently out of stock."

    if customer_id not in carts:
        carts[customer_id] = []

    # Check if product already in cart
    for item in carts[customer_id]:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            return f"Updated quantity: {product['name']} × {item['quantity']} in your cart."

    carts[customer_id].append({
        "product_id": product_id,
        "name": product["name"],
        "price": product["price"],
        "quantity": quantity,
    })
    return f"Added to cart: {product['name']} × {quantity} (${product['price'] * quantity:.2f})"


@tool
def view_cart(customer_id: str) -> str:
    """View the contents of a customer's shopping cart.

    Args:
        customer_id: Customer ID (e.g., "CUST-001")
    """
    if customer_id not in carts or not carts[customer_id]:
        return "Your cart is empty. Start shopping!"

    lines = ["🛒 Your Shopping Cart:\n"]
    subtotal = 0.0
    for item in carts[customer_id]:
        item_total = item["price"] * item["quantity"]
        subtotal += item_total
        lines.append(f"• {item['name']} × {item['quantity']} — ${item_total:.2f}")
    lines.append(f"\nSubtotal: ${subtotal:.2f}")

    # Check if coupon applied
    if customer_id in applied_coupons:
        coupon_code = applied_coupons[customer_id]
        coupon = COUPONS[coupon_code]
        discount = subtotal * coupon["discount_percent"] / 100
        lines.append(f"Coupon ({coupon_code}): -${discount:.2f}")
        lines.append(f"Total: ${subtotal - discount:.2f}")
    else:
        lines.append("No coupon applied. Use apply_coupon to add a discount!")

    return "\n".join(lines)


@tool
def remove_from_cart(customer_id: str, product_id: str) -> str:
    """Remove a product from the customer's shopping cart.

    Args:
        customer_id: Customer ID (e.g., "CUST-001")
        product_id: Product ID to remove
    """
    if customer_id not in carts or not carts[customer_id]:
        return "Your cart is already empty."

    for i, item in enumerate(carts[customer_id]):
        if item["product_id"] == product_id:
            removed = carts[customer_id].pop(i)
            return f"Removed from cart: {removed['name']}"

    return f"Product '{product_id}' not found in your cart."


@tool
def apply_coupon(customer_id: str, coupon_code: str) -> str:
    """Apply a discount coupon to the customer's cart.

    Args:
        customer_id: Customer ID (e.g., "CUST-001")
        coupon_code: The coupon code to apply (e.g., "WELCOME10", "SAVE20")
    """
    code_upper = coupon_code.upper()
    if code_upper not in COUPONS:
        return f"Invalid coupon code: '{coupon_code}'. Please check and try again."

    coupon = COUPONS[code_upper]

    # Check minimum order
    if customer_id in carts and carts[customer_id]:
        subtotal = sum(item["price"] * item["quantity"] for item in carts[customer_id])
        if subtotal < coupon.get("min_order", 0):
            return f"This coupon requires a minimum order of ${coupon['min_order']:.2f}. Your cart total is ${subtotal:.2f}."
    else:
        return "Add items to your cart before applying a coupon."

    applied_coupons[customer_id] = code_upper
    return f"✓ Coupon '{code_upper}' applied! {coupon['description']}."


@tool
def checkout(customer_id: str, payment_method: str = "credit_card") -> str:
    """Process checkout and place an order.

    Args:
        customer_id: Customer ID (e.g., "CUST-001")
        payment_method: Payment method — credit_card, debit_card, or paypal
    """
    if customer_id not in carts or not carts[customer_id]:
        return "Your cart is empty. Add items before checkout."

    items = carts[customer_id]
    subtotal = sum(item["price"] * item["quantity"] for item in items)

    # Apply discount
    discount = 0.0
    if customer_id in applied_coupons:
        coupon = COUPONS[applied_coupons[customer_id]]
        discount = subtotal * coupon["discount_percent"] / 100

    total = subtotal - discount
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    orders[order_id] = {
        "order_id": order_id,
        "customer_id": customer_id,
        "items": [dict(item) for item in items],
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "payment_method": payment_method,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "estimated_delivery": "3-5 business days",
    }

    # Clear cart and coupon
    carts[customer_id] = []
    applied_coupons.pop(customer_id, None)

    return (
        f"✓ Order placed successfully!\n\n"
        f"Order ID: {order_id}\n"
        f"Items: {len(items)}\n"
        f"Subtotal: ${subtotal:.2f}\n"
        f"Discount: -${discount:.2f}\n"
        f"Total charged: ${total:.2f}\n"
        f"Payment: {payment_method}\n"
        f"Estimated delivery: 3-5 business days\n\n"
        f"Thank you for your purchase! 🎉"
    )


@tool
def get_order_status(order_id: str) -> str:
    """Check the status of an existing order.

    Args:
        order_id: The order ID (e.g., "ORD-20260401-001")
    """
    if order_id not in orders:
        return f"Order '{order_id}' not found. Please check the order ID."

    order = orders[order_id]
    lines = [
        f"📦 Order Status: {order['order_id']}\n",
        f"Status: {order['status'].upper()}",
        f"Placed: {order['created_at'][:10]}",
        f"Total: ${order['total']:.2f}",
        f"Items:",
    ]
    for item in order["items"]:
        lines.append(f"  • {item['name']} × {item['quantity']}")

    if order.get("tracking_number"):
        lines.append(f"\nTracking: {order['tracking_number']}")
    if order.get("estimated_delivery"):
        lines.append(f"Estimated delivery: {order['estimated_delivery'][:10]}")
    if order.get("delivered_at"):
        lines.append(f"Delivered: {order['delivered_at'][:10]}")

    return "\n".join(lines)


@tool
def list_orders(customer_id: str) -> str:
    """List all orders for a customer.

    Args:
        customer_id: Customer ID (e.g., "CUST-001")
    """
    customer_orders = [o for o in orders.values() if o["customer_id"] == customer_id]
    if not customer_orders:
        return "No orders found for this customer."

    customer_orders.sort(key=lambda x: x["created_at"], reverse=True)
    lines = [f"📋 Your Orders ({len(customer_orders)} total):\n"]
    for o in customer_orders:
        item_count = sum(item["quantity"] for item in o["items"])
        lines.append(f"• {o['order_id']} | {o['status'].upper()} | ${o['total']:.2f} | {item_count} item(s) | {o['created_at'][:10]}")
    return "\n".join(lines)


@tool
def request_return(order_id: str, reason: str) -> str:
    """Request a return/refund for a delivered order.

    Args:
        order_id: The order ID to return
        reason: Reason for the return (e.g., "defective", "wrong item", "not as described", "changed mind")
    """
    if order_id not in orders:
        return f"Order '{order_id}' not found."

    order = orders[order_id]
    if order["status"] not in ("delivered", "shipped"):
        return f"Cannot process return — order status is '{order['status']}'. Returns are only available for shipped or delivered orders."

    return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    order["status"] = "return_requested"
    order["return_id"] = return_id
    order["return_reason"] = reason

    return (
        f"✓ Return request submitted!\n\n"
        f"Return ID: {return_id}\n"
        f"Order: {order_id}\n"
        f"Reason: {reason}\n"
        f"Refund amount: ${order['total']:.2f}\n\n"
        f"You will receive a return shipping label via email within 24 hours. "
        f"Refund will be processed within 5-7 business days after we receive the item."
    )


# ─── Agent Factory ──────────────────────────────────────────────────────────────

ALL_TOOLS = [
    search_products,
    get_product_details,
    get_recommendations,
    add_to_cart,
    view_cart,
    remove_from_cart,
    apply_coupon,
    checkout,
    get_order_status,
    list_orders,
    request_return,
]


def create_agent(model_id: str = "us.anthropic.claude-haiku-4-5-20250609-v1:0", region: str = "us-west-2") -> Agent:
    """Create the ShopAssist agent with all e-commerce tools."""
    model = BedrockModel(
        model_id=model_id,
        region_name=region,
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
