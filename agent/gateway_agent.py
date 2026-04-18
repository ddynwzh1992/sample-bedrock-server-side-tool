"""E-Commerce Agent — Gateway Mode (Client-Side Tool Execution).

Connects to AgentCore Gateway via MCP Streamable HTTP transport.
Tools are hosted as Lambda functions behind the Gateway.
"""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

SYSTEM_PROMPT = """You are ShopAssist, an AI-powered e-commerce shopping assistant. You help customers browse products, manage their cart, place orders, and handle returns.

Be friendly, helpful, and concise. Format prices as USD. Use customer ID "CUST-001" for the current session unless told otherwise."""


def create_streamable_http_transport(gateway_url: str):
    """Create a Streamable HTTP transport for MCP."""
    return streamablehttp_client(gateway_url)


def get_all_tools(client: MCPClient) -> list:
    """Get all tools with pagination support."""
    tools = []
    pagination_token = None
    while True:
        page = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(page)
        if page.pagination_token is None:
            break
        pagination_token = page.pagination_token
    return tools


def create_gateway_agent(
    gateway_url: str,
    model_id: str = "openai.gpt-oss-120b",
    region: str = "us-west-2",
) -> tuple[Agent, MCPClient]:
    """Create agent connected to AgentCore Gateway.

    Args:
        gateway_url: AgentCore Gateway MCP endpoint URL
        model_id: Bedrock model ID
        region: AWS region

    Returns:
        Tuple of (Agent, MCPClient) — use with context manager

    Example:
        ```python
        gateway_url = "https://<gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp"
        agent, mcp_client = create_gateway_agent(gateway_url)

        with mcp_client:
            tools = get_all_tools(mcp_client)
            agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=tools)
            response = agent("Show me wireless headphones under $100")
        ```
    """
    model = BedrockModel(model_id=model_id, region_name=region, streaming=True)
    mcp_client = MCPClient(lambda: create_streamable_http_transport(gateway_url))
    return model, mcp_client


def run_gateway_agent(gateway_url: str, model_id: str = "openai.gpt-oss-120b"):
    """Run the gateway agent in interactive mode."""
    model, mcp_client = create_gateway_agent(gateway_url, model_id)

    print("🛍️  ShopAssist (Gateway Mode)")
    print(f"   Gateway: {gateway_url}")
    print(f"   Model: {model_id}")
    print("-" * 60)

    with mcp_client:
        tools = get_all_tools(mcp_client)
        print(f"   Tools discovered: {len(tools)}")
        print("-" * 60)

        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=tools)

        print("\nReady! Type your message or 'quit' to exit.\n")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "bye"):
                print("\nThank you for shopping with us! 👋")
                break
            if not user_input:
                continue
            print()
            response = agent(user_input)
            print(f"\n{'─' * 60}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m agent.gateway_agent <GATEWAY_URL>")
        sys.exit(1)

    run_gateway_agent(sys.argv[1])
