"""E-Commerce Agent — Server-Side Tool Execution Mode.

Uses Bedrock Mantle Responses API (OpenAI-compatible) with AgentCore Gateway
for server-side tool execution. No client-side orchestration loop needed.

Requires:
  pip install openai boto3

Environment variables:
  OPENAI_API_KEY: Bedrock long-term API key
  OPENAI_BASE_URL: https://bedrock-mantle.<region>.api.aws/v1
"""

from __future__ import annotations

import os
from openai import OpenAI


def create_client(region: str = "us-west-2", api_key: str | None = None) -> OpenAI:
    """Create OpenAI client pointing to Bedrock Mantle endpoint."""
    base_url = os.environ.get("OPENAI_BASE_URL", f"https://bedrock-mantle.{region}.api.aws/v1")
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    return OpenAI(base_url=base_url, api_key=key)


def create_response_with_server_side_tools(
    user_message: str,
    gateway_arn: str,
    region: str = "us-west-2",
    model_id: str = "openai.gpt-oss-120b",
    system_prompt: str = "You are ShopAssist, an AI-powered e-commerce shopping assistant.",
    api_key: str | None = None,
) -> dict:
    """Execute a single request with server-side tool execution via Responses API.

    The Responses API discovers tools from the AgentCore Gateway, presents them to the model,
    and executes tool calls server-side — all in a single API call.

    Args:
        user_message: User's query
        gateway_arn: AgentCore Gateway ARN
        region: AWS region
        model_id: Model ID (default: openai.gpt-oss-120b)
        system_prompt: System instructions for the agent
        api_key: Bedrock API key (or set OPENAI_API_KEY env var)

    Returns:
        Response from Bedrock Responses API
    """
    client = create_client(region=region, api_key=api_key)

    response = client.responses.create(
        model=model_id,
        instructions=system_prompt,
        input=user_message,
        tools=[
            {
                "type": "mcp",
                "server_label": "ecommerce_tools",
                "server_url": gateway_arn,
                "require_approval": "never",
            }
        ],
    )

    return response


def run_server_side_demo(
    gateway_arn: str,
    region: str = "us-west-2",
    model_id: str = "openai.gpt-oss-120b",
):
    """Run interactive demo using server-side tool execution."""
    print("🛍️  ShopAssist (Server-Side Tool Execution Mode)")
    print(f"   Endpoint: bedrock-mantle.{region}.api.aws/v1")
    print(f"   Model: {model_id}")
    print(f"   Gateway: {gateway_arn}")
    print("=" * 60)
    print("   Tools are executed SERVER-SIDE by Bedrock — no client orchestration!")
    print("=" * 60)

    system_prompt = """You are ShopAssist, an AI-powered e-commerce shopping assistant.
You help customers browse products, manage their cart, place orders, and handle returns.
Be friendly, helpful, and concise. Format prices as USD. Use customer ID "CUST-001"."""

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
                region=region,
                model_id=model_id,
                system_prompt=system_prompt,
            )

            # Extract text from response
            if hasattr(response, "output_text"):
                print(f"Assistant: {response.output_text}")
            elif hasattr(response, "output"):
                for item in response.output:
                    if hasattr(item, "content"):
                        for content in item.content:
                            if hasattr(content, "text"):
                                print(f"Assistant: {content.text}")

            # Show usage
            if hasattr(response, "usage"):
                usage = response.usage
                print(f"\n  [Tokens: {usage.input_tokens} in / {usage.output_tokens} out]")

        except Exception as e:
            print(f"Error: {e}")

        print(f"\n{'─' * 60}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m agent.serverside_agent <GATEWAY_ARN> [REGION]")
        print("\nEnvironment variables required:")
        print("  OPENAI_API_KEY: Bedrock long-term API key")
        print("  OPENAI_BASE_URL: (optional) defaults to bedrock-mantle.<region>.api.aws/v1")
        print("\nExample:")
        print("  export OPENAI_API_KEY='your-bedrock-api-key'")
        print("  python -m agent.serverside_agent arn:aws:bedrock-agentcore:us-west-2:123456789:gateway/my-gw")
        sys.exit(1)

    gw_arn = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "us-west-2"
    run_server_side_demo(gw_arn, region=region)
