"""Sample e-commerce product data and state management."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
import random

# ─── Product Catalog ────────────────────────────────────────────────────────────

PRODUCTS: list[dict[str, Any]] = [
    # Electronics - Headphones
    {"id": "ELEC-001", "name": "SoundWave Pro Wireless Headphones", "category": "Electronics", "subcategory": "Headphones", "price": 79.99, "rating": 4.5, "reviews": 2847, "description": "Premium wireless headphones with active noise cancellation, 30-hour battery life, and memory foam ear cushions.", "in_stock": True},
    {"id": "ELEC-002", "name": "BassBoost Studio Over-Ear Headphones", "category": "Electronics", "subcategory": "Headphones", "price": 149.99, "rating": 4.7, "reviews": 1523, "description": "Audiophile-grade over-ear headphones with 50mm drivers, Hi-Res Audio certified, foldable design.", "in_stock": True},
    {"id": "ELEC-003", "name": "AirBud Mini Earbuds", "category": "Electronics", "subcategory": "Headphones", "price": 49.99, "rating": 4.2, "reviews": 5621, "description": "Compact true wireless earbuds with touch controls, IPX5 waterproof, 24-hour total battery with case.", "in_stock": True},
    {"id": "ELEC-004", "name": "NoiseFree Executive ANC Headphones", "category": "Electronics", "subcategory": "Headphones", "price": 249.99, "rating": 4.8, "reviews": 892, "description": "Premium business headphones with multi-point connection, crystal-clear microphone array, and adaptive ANC.", "in_stock": True},
    {"id": "ELEC-005", "name": "RunnerX Sport Earbuds", "category": "Electronics", "subcategory": "Headphones", "price": 69.99, "rating": 4.4, "reviews": 3156, "description": "Secure-fit sport earbuds with bone conduction awareness mode, IP67 rating, 10-hour battery.", "in_stock": True},
    # Electronics - Laptops
    {"id": "ELEC-006", "name": "UltraBook Pro 15 Laptop", "category": "Electronics", "subcategory": "Laptops", "price": 1299.99, "rating": 4.6, "reviews": 1834, "description": "15-inch 4K OLED display, Intel i7-13700H, 32GB RAM, 1TB SSD, all-day battery life.", "in_stock": True},
    {"id": "ELEC-007", "name": "CodeMaster Developer Laptop", "category": "Electronics", "subcategory": "Laptops", "price": 1599.99, "rating": 4.8, "reviews": 723, "description": "14-inch 2K display, M3 Pro chip, 36GB unified memory, 512GB SSD, perfect for developers.", "in_stock": True},
    {"id": "ELEC-008", "name": "BudgetBook Air 13", "category": "Electronics", "subcategory": "Laptops", "price": 499.99, "rating": 4.1, "reviews": 4521, "description": "Lightweight 13-inch laptop, AMD Ryzen 5, 16GB RAM, 256GB SSD, great for students.", "in_stock": True},
    {"id": "ELEC-009", "name": "GameForce RTX Laptop", "category": "Electronics", "subcategory": "Laptops", "price": 1899.99, "rating": 4.5, "reviews": 1247, "description": "16-inch 240Hz display, RTX 4070, Intel i9, 32GB RAM, 1TB SSD, RGB keyboard.", "in_stock": True},
    # Electronics - Phones & Tablets
    {"id": "ELEC-010", "name": "PixelMax Pro Smartphone", "category": "Electronics", "subcategory": "Phones", "price": 899.99, "rating": 4.6, "reviews": 6723, "description": "6.7-inch AMOLED 120Hz, triple 50MP camera system, 5000mAh battery, 5G enabled.", "in_stock": True},
    {"id": "ELEC-011", "name": "TabletX 11 Pro", "category": "Electronics", "subcategory": "Tablets", "price": 649.99, "rating": 4.5, "reviews": 2134, "description": "11-inch Liquid Retina display, M2 chip, Apple Pencil support, all-day battery.", "in_stock": True},
    {"id": "ELEC-012", "name": "SmartWatch Ultra", "category": "Electronics", "subcategory": "Wearables", "price": 399.99, "rating": 4.4, "reviews": 3892, "description": "Titanium case, always-on display, advanced health monitoring, 60-hour battery, GPS.", "in_stock": True},
    {"id": "ELEC-013", "name": "PowerBank 26800mAh", "category": "Electronics", "subcategory": "Accessories", "price": 39.99, "rating": 4.3, "reviews": 8921, "description": "Ultra-high capacity portable charger, 65W PD fast charging, charges laptop and phone simultaneously.", "in_stock": True},
    # Home & Kitchen
    {"id": "HOME-001", "name": "BrewMaster Elite Coffee Maker", "category": "Home & Kitchen", "subcategory": "Coffee", "price": 189.99, "rating": 4.7, "reviews": 3456, "description": "12-cup programmable coffee maker with built-in grinder, thermal carafe, and strength control.", "in_stock": True},
    {"id": "HOME-002", "name": "NutriBlend Pro Blender", "category": "Home & Kitchen", "subcategory": "Blenders", "price": 129.99, "rating": 4.5, "reviews": 2789, "description": "1500W professional blender with variable speed, 64oz container, and self-cleaning mode.", "in_stock": True},
    {"id": "HOME-003", "name": "CrispAir Digital Air Fryer", "category": "Home & Kitchen", "subcategory": "Air Fryers", "price": 99.99, "rating": 4.6, "reviews": 7234, "description": "5.8-quart digital air fryer with 8 presets, rapid air technology, dishwasher-safe basket.", "in_stock": True},
    {"id": "HOME-004", "name": "ChefPro Stand Mixer", "category": "Home & Kitchen", "subcategory": "Mixers", "price": 349.99, "rating": 4.8, "reviews": 1567, "description": "5.5-quart tilt-head stand mixer, 10 speeds, includes dough hook, flat beater, and wire whip.", "in_stock": True},
    {"id": "HOME-005", "name": "InstaCook Pressure Cooker 8-in-1", "category": "Home & Kitchen", "subcategory": "Cookers", "price": 89.99, "rating": 4.4, "reviews": 12456, "description": "6-quart multi-cooker: pressure cook, slow cook, rice, steam, sauté, yogurt, soup, warm.", "in_stock": True},
    {"id": "HOME-006", "name": "PureAir HEPA Purifier", "category": "Home & Kitchen", "subcategory": "Air Quality", "price": 199.99, "rating": 4.5, "reviews": 2345, "description": "Covers 1500 sq ft, H13 true HEPA filter, auto mode with air quality sensor, whisper-quiet.", "in_stock": True},
    {"id": "HOME-007", "name": "SmartVac Robot Vacuum", "category": "Home & Kitchen", "subcategory": "Cleaning", "price": 449.99, "rating": 4.3, "reviews": 4567, "description": "LiDAR navigation, 5000Pa suction, self-emptying base, app control, works with Alexa.", "in_stock": True},
    {"id": "HOME-008", "name": "CastIron Dutch Oven 6Qt", "category": "Home & Kitchen", "subcategory": "Cookware", "price": 79.99, "rating": 4.9, "reviews": 8923, "description": "Enameled cast iron, oven-safe to 500°F, perfect for braising, stewing, and baking bread.", "in_stock": True},
    {"id": "HOME-009", "name": "SilkTouch Bed Sheet Set (Queen)", "category": "Home & Kitchen", "subcategory": "Bedding", "price": 59.99, "rating": 4.4, "reviews": 15234, "description": "1800-thread count microfiber, deep pocket fitted sheet, wrinkle-resistant, hypoallergenic.", "in_stock": True},
    {"id": "HOME-010", "name": "AromaWave Essential Oil Diffuser", "category": "Home & Kitchen", "subcategory": "Home Decor", "price": 34.99, "rating": 4.2, "reviews": 6789, "description": "500ml ultrasonic diffuser, 7 LED colors, auto shut-off, runs up to 12 hours.", "in_stock": True},
    {"id": "HOME-011", "name": "SharpEdge Knife Set (15-piece)", "category": "Home & Kitchen", "subcategory": "Cutlery", "price": 119.99, "rating": 4.6, "reviews": 3456, "description": "German stainless steel, full-tang construction, ergonomic handles, includes knife block.", "in_stock": True},
    {"id": "HOME-012", "name": "FreshSeal Vacuum Sealer", "category": "Home & Kitchen", "subcategory": "Storage", "price": 69.99, "rating": 4.3, "reviews": 2890, "description": "Automatic vacuum sealing system, moist/dry modes, includes starter roll and bags.", "in_stock": True},
    # Sports & Outdoors
    {"id": "SPRT-001", "name": "CloudRun Ultra Running Shoes", "category": "Sports & Outdoors", "subcategory": "Running", "price": 139.99, "rating": 4.6, "reviews": 4523, "description": "Lightweight mesh upper, responsive foam midsole, carbon plate for energy return, 8.2oz.", "in_stock": True},
    {"id": "SPRT-002", "name": "ZenFlow Premium Yoga Mat", "category": "Sports & Outdoors", "subcategory": "Yoga", "price": 49.99, "rating": 4.7, "reviews": 6789, "description": "6mm thick, non-slip natural rubber, alignment lines, includes carrying strap, eco-friendly.", "in_stock": True},
    {"id": "SPRT-003", "name": "HydroMax Insulated Water Bottle 32oz", "category": "Sports & Outdoors", "subcategory": "Hydration", "price": 29.99, "rating": 4.5, "reviews": 18234, "description": "Triple-wall vacuum insulation, keeps cold 24hr/hot 12hr, BPA-free, leak-proof lid.", "in_stock": True},
    {"id": "SPRT-004", "name": "FlexFit Resistance Band Set", "category": "Sports & Outdoors", "subcategory": "Fitness", "price": 34.99, "rating": 4.4, "reviews": 9876, "description": "5 resistance levels (10-50lbs), latex-free TPE, includes door anchor, handles, ankle straps.", "in_stock": True},
    {"id": "SPRT-005", "name": "TrailBlazer 55L Hiking Backpack", "category": "Sports & Outdoors", "subcategory": "Hiking", "price": 89.99, "rating": 4.5, "reviews": 2345, "description": "Ventilated back panel, rain cover included, multiple compartments, hydration compatible.", "in_stock": True},
    {"id": "SPRT-006", "name": "PowerGrip Adjustable Dumbbells (5-52.5lb)", "category": "Sports & Outdoors", "subcategory": "Fitness", "price": 349.99, "rating": 4.7, "reviews": 1890, "description": "Replace 15 sets of dumbbells, quick-change weight selector, compact design.", "in_stock": True},
    {"id": "SPRT-007", "name": "CyclePro Indoor Exercise Bike", "category": "Sports & Outdoors", "subcategory": "Fitness", "price": 599.99, "rating": 4.3, "reviews": 3456, "description": "Magnetic resistance, 22-inch HD touchscreen, live and on-demand classes, adjustable seat.", "in_stock": True},
    {"id": "SPRT-008", "name": "CampLite 2-Person Tent", "category": "Sports & Outdoors", "subcategory": "Camping", "price": 79.99, "rating": 4.4, "reviews": 5678, "description": "3-season tent, waterproof rainfly, easy setup in under 5 minutes, weighs 4.5lbs.", "in_stock": True},
    {"id": "SPRT-009", "name": "SwimTech Pro Goggles", "category": "Sports & Outdoors", "subcategory": "Swimming", "price": 24.99, "rating": 4.3, "reviews": 7890, "description": "Anti-fog coating, UV protection, adjustable nose bridge, silicone gaskets, competition-grade.", "in_stock": True},
    {"id": "SPRT-010", "name": "GripMaster Climbing Chalk Bag", "category": "Sports & Outdoors", "subcategory": "Climbing", "price": 19.99, "rating": 4.6, "reviews": 2345, "description": "Drawstring closure, fleece-lined interior, brush holder loop, includes waist belt.", "in_stock": True},
    {"id": "SPRT-011", "name": "SpeedRope Pro Jump Rope", "category": "Sports & Outdoors", "subcategory": "Fitness", "price": 14.99, "rating": 4.5, "reviews": 11234, "description": "Ball-bearing handles, adjustable cable length, lightweight aluminum handles, 360° rotation.", "in_stock": True},
    {"id": "SPRT-012", "name": "FoamRoll Recovery Roller 18-inch", "category": "Sports & Outdoors", "subcategory": "Recovery", "price": 29.99, "rating": 4.4, "reviews": 8765, "description": "High-density EVA foam, textured surface for deep tissue massage, durable and lightweight.", "in_stock": True},
    # Books
    {"id": "BOOK-001", "name": "Building AI Agents: From Theory to Production", "category": "Books", "subcategory": "Technology", "price": 44.99, "rating": 4.7, "reviews": 567, "description": "Comprehensive guide to building production-ready AI agents, covers LLMs, tool use, and deployment.", "in_stock": True},
    {"id": "BOOK-002", "name": "The Cloud Architecture Handbook", "category": "Books", "subcategory": "Technology", "price": 54.99, "rating": 4.8, "reviews": 1234, "description": "Best practices for designing scalable, resilient cloud systems on AWS, Azure, and GCP.", "in_stock": True},
    {"id": "BOOK-003", "name": "Python Machine Learning (4th Edition)", "category": "Books", "subcategory": "Technology", "price": 49.99, "rating": 4.6, "reviews": 2890, "description": "Updated for 2026, covers PyTorch, transformers, reinforcement learning, and MLOps.", "in_stock": True},
    {"id": "BOOK-004", "name": "The Midnight Library", "category": "Books", "subcategory": "Fiction", "price": 14.99, "rating": 4.5, "reviews": 45678, "description": "A novel about all the lives we could have lived, between life and death there is a library.", "in_stock": True},
    {"id": "BOOK-005", "name": "Project Hail Mary", "category": "Books", "subcategory": "Fiction", "price": 16.99, "rating": 4.8, "reviews": 67890, "description": "A lone astronaut must save Earth. From the author of The Martian.", "in_stock": True},
    {"id": "BOOK-006", "name": "Atomic Habits", "category": "Books", "subcategory": "Business", "price": 18.99, "rating": 4.7, "reviews": 89012, "description": "Tiny changes, remarkable results. An easy & proven way to build good habits & break bad ones.", "in_stock": True},
    {"id": "BOOK-007", "name": "The Psychology of Money", "category": "Books", "subcategory": "Business", "price": 17.99, "rating": 4.6, "reviews": 34567, "description": "Timeless lessons on wealth, greed, and happiness. 20 short stories about money.", "in_stock": True},
    {"id": "BOOK-008", "name": "System Design Interview Volume 2", "category": "Books", "subcategory": "Technology", "price": 39.99, "rating": 4.5, "reviews": 4567, "description": "Step-by-step guide to designing large-scale systems. Real-world examples from FAANG companies.", "in_stock": True},
    {"id": "BOOK-009", "name": "Deep Work: Rules for Focused Success", "category": "Books", "subcategory": "Business", "price": 15.99, "rating": 4.4, "reviews": 23456, "description": "Cal Newport's guide to focused success in a distracted world.", "in_stock": True},
    {"id": "BOOK-010", "name": "The Rust Programming Language (2nd Edition)", "category": "Books", "subcategory": "Technology", "price": 44.99, "rating": 4.7, "reviews": 1890, "description": "The official Rust book, updated for Rust 2024 edition. From basics to advanced concurrency.", "in_stock": True},
    {"id": "BOOK-011", "name": "Dune (Deluxe Edition)", "category": "Books", "subcategory": "Fiction", "price": 24.99, "rating": 4.9, "reviews": 56789, "description": "Frank Herbert's masterpiece. A stunning blend of adventure and mysticism in an intergalactic setting.", "in_stock": True},
    {"id": "BOOK-012", "name": "Thinking, Fast and Slow", "category": "Books", "subcategory": "Business", "price": 16.99, "rating": 4.5, "reviews": 34567, "description": "Daniel Kahneman's groundbreaking exploration of the two systems that drive the way we think.", "in_stock": True},
]

# ─── Coupon Codes ───────────────────────────────────────────────────────────────

COUPONS: dict[str, dict[str, Any]] = {
    "WELCOME10": {"discount_percent": 10, "min_order": 0, "description": "10% off your first order"},
    "SAVE20": {"discount_percent": 20, "min_order": 100, "description": "20% off orders over $100"},
    "FREESHIP": {"discount_percent": 0, "free_shipping": True, "min_order": 50, "description": "Free shipping on orders over $50"},
    "TECH15": {"discount_percent": 15, "min_order": 200, "category": "Electronics", "description": "15% off Electronics over $200"},
    "SPRING25": {"discount_percent": 25, "min_order": 75, "description": "Spring sale - 25% off orders over $75"},
}

# ─── In-Memory State ────────────────────────────────────────────────────────────

# Carts: {customer_id: [{product_id, quantity, product_name, price}]}
carts: dict[str, list[dict[str, Any]]] = {}

# Orders: {order_id: {customer_id, items, total, status, created_at, ...}}
orders: dict[str, dict[str, Any]] = {
    "ORD-20260401-001": {
        "order_id": "ORD-20260401-001",
        "customer_id": "CUST-001",
        "items": [{"product_id": "ELEC-001", "name": "SoundWave Pro Wireless Headphones", "quantity": 1, "price": 79.99}],
        "subtotal": 79.99,
        "discount": 0,
        "total": 79.99,
        "status": "delivered",
        "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
        "delivered_at": (datetime.now() - timedelta(days=7)).isoformat(),
    },
    "ORD-20260410-002": {
        "order_id": "ORD-20260410-002",
        "customer_id": "CUST-001",
        "items": [
            {"product_id": "HOME-003", "name": "CrispAir Digital Air Fryer", "quantity": 1, "price": 99.99},
            {"product_id": "HOME-008", "name": "CastIron Dutch Oven 6Qt", "quantity": 1, "price": 79.99},
        ],
        "subtotal": 179.98,
        "discount": 17.998,
        "total": 161.98,
        "status": "shipped",
        "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
        "tracking_number": "1Z999AA10123456784",
        "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat(),
    },
}

# Applied coupons per customer
applied_coupons: dict[str, str] = {}


def get_product_by_id(product_id: str) -> dict[str, Any] | None:
    """Look up a product by ID."""
    for p in PRODUCTS:
        if p["id"] == product_id:
            return p
    return None


def search_products_in_catalog(
    query: str = "",
    category: str = "",
    min_price: float = 0,
    max_price: float = float("inf"),
) -> list[dict[str, Any]]:
    """Search products with filters."""
    results = []
    query_lower = query.lower()
    for p in PRODUCTS:
        if category and p["category"].lower() != category.lower():
            continue
        if p["price"] < min_price or p["price"] > max_price:
            continue
        if query_lower:
            searchable = f"{p['name']} {p['description']} {p['category']} {p['subcategory']}".lower()
            if query_lower not in searchable:
                continue
        results.append(p)
    return results


def get_recommendations_for(category: str = "", limit: int = 5) -> list[dict[str, Any]]:
    """Get top-rated products, optionally filtered by category."""
    pool = PRODUCTS if not category else [p for p in PRODUCTS if p["category"].lower() == category.lower()]
    sorted_pool = sorted(pool, key=lambda p: (-p["rating"], -p["reviews"]))
    return sorted_pool[:limit]
