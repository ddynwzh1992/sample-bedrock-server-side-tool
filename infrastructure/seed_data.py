"""Seed DynamoDB tables with sample product data."""

import boto3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.data import PRODUCTS


def seed_products(table_name: str = "ShopAssist-Products", region: str = "us-west-2"):
    """Write all sample products to DynamoDB."""
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    print(f"Seeding {len(PRODUCTS)} products to {table_name}...")

    with table.batch_writer() as batch:
        for product in PRODUCTS:
            # Convert float to Decimal for DynamoDB
            item = {
                "id": product["id"],
                "name": product["name"],
                "category": product["category"],
                "subcategory": product["subcategory"],
                "price": str(product["price"]),  # Store as string, parse in Lambda
                "rating": str(product["rating"]),
                "reviews": product["reviews"],
                "description": product["description"],
                "in_stock": product["in_stock"],
            }
            batch.put_item(Item=item)

    print(f"✓ Done! {len(PRODUCTS)} products seeded.")


if __name__ == "__main__":
    region = os.environ.get("AWS_REGION", "us-west-2")
    table_name = os.environ.get("PRODUCTS_TABLE", "ShopAssist-Products")
    seed_products(table_name, region)
