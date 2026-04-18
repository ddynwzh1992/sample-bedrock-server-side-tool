"""E-Commerce Agent — Server-Side Tool Execution Mode.

Uses Bedrock Mantle Responses API with AgentCore Gateway for
server-side tool execution. No client-side orchestration needed.

Bedrock automatically:
1. Discovers tools from Gateway (MCP list_tools)
2. Model reasons and selects tools
3. Executes tools via Gateway → Lambda
4. Injects results and continues reasoning
5. Returns final response

All in a single streaming API call.

Requires:
  pip install boto3 requests

Environment variables:
  AWS_REGION: AWS region (default: us-west-2)
  GATEWAY_ARN: AgentCore Gateway ARN
"""

from __future__ import annotations

import json
import os
import sys

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def create_response_with_server_side_tools(
    user_message: str,
    gateway_arn: str,
    region: str = "us-west-2",
    model_id: str = "openai.gpt-oss-120b",
    system_prompt: str = "You are ShopAssist, an AI-powered e-commerce shopping assistant. Use the available tools to help customers.",
) -> str:
    """Execute a request with server-side tool execution via Responses API (streaming).

    Returns the final text response after all tool calls complete.
    """
    session = boto3.Session(region_name=region)
    credentials = session.get_credentials().get_frozen_credentials()

    url = f"https://bedrock-mantle.{region}.api.aws/v1/responses"

    # IMPORTANT: input must use the full message array format, not a plain string.
    # Using a plain string causes the model to loop tool calls indefinitely.
    payload = {
        "model": model_id,
        "stream": True,
        "background": False,
        "store": False,
        "instructions": system_prompt,
        "tools": [
            {
                "type": "mcp",
                "server_label": "agentcore_tools",
                "connector_id": gateway_arn,
                "server_description": "AgentCore Gateway providing ecommerce tools",
                "require_approval": "never",
            }
        ],
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_message,
                    }
                ],
            }
        ],
    }

    body = json.dumps(payload)
    request = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    SigV4Auth(credentials, "bedrock", region).add_auth(request)

    resp = requests.post(
        url, data=body, headers=dict(request.headers), timeout=300, stream=True
    )
    resp.raise_for_status()

    # Parse SSE stream and extract final output text
    output_text = ""
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data = json.loads(line[6:])
        event_type = data.get("type", "")

        # Collect output text deltas
        if event_type == "response.output_text.delta":
            delta = data.get("delta", "")
            output_text += delta
            print(delta, end="", flush=True)

        # Show tool calls for visibility
        elif event_type == "response.mcp_call_arguments.done":
            tool_name = data.get("name", "")
            args = data.get("arguments", "")
            print(f"\n  [Tool: {tool_name}({args})]", flush=True)

        elif event_type == "response.completed":
            break

    print()  # Final newline
    return output_text


def run_server_side_demo(
    gateway_arn: str,
    region: str = "us-west-2",
    model_id: str = "openai.gpt-oss-120b",
):
    """Run interactive demo using server-side tool execution."""
    print("🛍️  ShopAssist — Server-Side Tool Execution Demo")
    print(f"   Model: {model_id}")
    print(f"   Gateway: {gateway_arn}")
    print("=" * 60)
    print("   Bedrock executes tools automatically — zero client orchestration!")
    print("=" * 60)

    system_prompt = (
        "You are ShopAssist, an AI e-commerce shopping assistant. "
        "Use the available tools to search products, manage carts, and handle orders. "
        "Be concise and helpful. Customer ID is CUST-001."
    )

    print("\nReady! Type your message or 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "bye"):
            print("\nThank you for shopping with us! 👋")
            break
        if not user_input:
            continue

        print("\nAssistant: ", end="", flush=True)
        try:
            create_response_with_server_side_tools(
                user_message=user_input,
                gateway_arn=gateway_arn,
                region=region,
                model_id=model_id,
                system_prompt=system_prompt,
            )
        except Exception as e:
            print(f"\nError: {e}")

        print(f"\n{'─' * 60}\n")


if __name__ == "__main__":
    gw_arn = os.environ.get("GATEWAY_ARN") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not gw_arn:
        print("Usage: python -m agent.serverside_agent <GATEWAY_ARN>")
        print("   or: export GATEWAY_ARN=arn:aws:bedrock-agentcore:...")
        sys.exit(1)

    region = os.environ.get("AWS_REGION", "us-west-2")
    model = os.environ.get("BEDROCK_MODEL_ID", "openai.gpt-oss-120b")
    run_server_side_demo(gw_arn, region=region, model_id=model)
