#!/usr/bin/env python3
"""ShopAssist Interactive Demo — Local Mode.

Run with: python demo/run_demo.py
Requires: pip install strands-agents boto3
AWS credentials must be configured for Bedrock access.
"""

from __future__ import annotations

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.local_agent import create_agent


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🛍️  ShopAssist — AI E-Commerce Shopping Assistant          ║
║                                                              ║
║   Powered by:                                                ║
║   • Strands Agents SDK                                       ║
║   • Amazon Bedrock (Claude Sonnet)                           ║
║   • AgentCore Gateway (server-side tool execution)           ║
║                                                              ║
║   Mode: LOCAL (in-memory mock data, 50+ products)            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Commands:
  /help     — Show this help message
  /products — List all product categories
  /cart     — View your cart
  /orders   — View your orders
  /quit     — Exit the demo

Try asking:
  • "Show me wireless headphones under $100"
  • "What are your top-rated books?"
  • "Add the SoundWave headphones to my cart"
  • "I'd like to check on my order ORD-20260410-002"
  • "Apply coupon WELCOME10 to my cart"
  • "I want to return my last order"
"""


def main():
    print(BANNER)

    # Check for custom model/region
    model_id = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20250609-v1:0")
    region = os.environ.get("AWS_REGION", "us-west-2")

    print(f"  Model: {model_id}")
    print(f"  Region: {region}")
    print(f"  Customer: CUST-001")
    print()

    try:
        agent = create_agent(model_id=model_id, region=region)
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        print("\nMake sure you have:")
        print("  1. AWS credentials configured (aws configure)")
        print("  2. Bedrock model access enabled for Claude Sonnet")
        print("  3. strands-agents installed (pip install strands-agents)")
        sys.exit(1)

    print("✓ Agent ready! Type /help for commands.\n")
    print("─" * 60)

    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in ("/quit", "/exit", "/q"):
                print("\nThank you for shopping with ShopAssist! 👋")
                break
            elif cmd == "/help":
                print(HELP_TEXT)
                continue
            elif cmd == "/products":
                user_input = "List all product categories and how many products are in each"
            elif cmd == "/cart":
                user_input = "Show my cart"
            elif cmd == "/orders":
                user_input = "List my orders"

        print()
        try:
            response = agent(user_input)
            print(f"\n{'─' * 60}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("─" * 60)


if __name__ == "__main__":
    main()
