"""E-Commerce Agent — Server-Side Tool Execution Mode.

Uses Bedrock Responses API with AgentCore Gateway for server-side tool execution.
No client-side orchestration loop needed — single API call handles everything.
"""

from __future__ import annotations

import json
import boto3


def create_response_with_server_side_tools(
    user_message: str,
    gateway_arn: str,
    model_id: str = "us.anthropic.claude-haiku-4-5-20250609-v1:0",
    region: str = "us-west-2",
    system_prompt: str = "You are ShopAssist, an AI-powered e-commerce shopping assistant.",
) -> dict:
    """Execute a single request with server-side tool execution via Bedrock Responses API.

    The Responses API discovers tools from the AgentCore Gateway, presents them to the model,
    and executes tool calls server-side — all in a single API call.

    Args:
        user_message: User's query
        gateway_arn: AgentCore Gateway ARN or URL
        model_id: Bedrock model ID
        region: AWS region
        system_prompt: System instructions for the agent

    Returns:
        Response dict from Bedrock Responses API
    """
    client = boto3.client("bedrock-runtime", region_name=region)

    response = client.create_response(
        modelId=model_id,
        system=[{"text": system_prompt}],
        input=[
            {
                "role": "user",
                "content": [{"text": user_message}],
            }
        ],
        tools=[
            {
                "mcpServerConnector": {
                    "mcpServerUri": gateway_arn,
                    "name": "ecommerce_tools",
                    "description": "E-commerce tools for product search, cart management, and order processing",
                }
            }
        ],
        toolExecution={"enabled": True},  # Enable server-side execution
    )

    return response


def run_server_side_demo(gateway_arn: str, model_id: str = "us.anthropic.claude-haiku-4-5-20250609-v1:0"):
    """Run interactive demo using server-side tool execution."""
    print("🛍️  ShopAssist (Server-Side Tool Execution Mode)")
    print(f"   Gateway ARN: {gateway_arn}")
    print(f"   Model: {model_id}")
    print("=" * 60)
    print("   Tools are executed SERVER-SIDE by Bedrock — no client orchestration loop!")
    print("=" * 60)

    system_prompt = """You are ShopAssist, an AI-powered e-commerce shopping assistant.
You help customers browse products, manage their cart, place orders, and handle returns.
Be friendly, helpful, and concise. Format prices as USD."""

    print("\nReady! Type your message or 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "bye"):
            print("\nThank you for shopping with us! 👋")
            break
        if not user_input:
            continue

        print("\n⏳ Processing (server-side)...\n")

        try:
            response = create_response_with_server_side_tools(
                user_message=user_input,
                gateway_arn=gateway_arn,
                model_id=model_id,
                system_prompt=system_prompt,
            )

            # Extract text response
            output = response.get("output", [])
            for item in output:
                if item.get("role") == "assistant":
                    for content in item.get("content", []):
                        if "text" in content:
                            print(f"Assistant: {content['text']}")

            # Show tool usage info
            usage = response.get("usage", {})
            if usage:
                print(f"\n  [Tokens: {usage.get('inputTokens', 0)} in / {usage.get('outputTokens', 0)} out]")

        except Exception as e:
            print(f"Error: {e}")

        print(f"\n{'─' * 60}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m agent.serverside_agent <GATEWAY_ARN>")
        print("\nExample:")
        print("  python -m agent.serverside_agent arn:aws:bedrock-agentcore:us-west-2:123456789:gateway/my-gateway")
        sys.exit(1)

    run_server_side_demo(sys.argv[1])
