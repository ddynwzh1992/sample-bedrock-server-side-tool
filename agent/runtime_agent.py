"""ShopAssist Agent — AgentCore Runtime Deployment.

This file wraps the ShopAssist agent for deployment on Amazon Bedrock AgentCore Runtime.
Uses the Amazon Bedrock AgentCore Python SDK to expose the agent as an HTTP service.

Deploy with:
  agentcore deploy

The agent will be hosted on AgentCore Runtime with:
  - /invocations endpoint for agent interaction
  - /ping endpoint for health checks
"""

from __future__ import annotations

import json
from typing import Any

from bedrock_agentcore.runtime import App, InvocationContext

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
from agent.local_agent import ALL_TOOLS, SYSTEM_PROMPT

# ─── AgentCore Runtime App ──────────────────────────────────────────────────────

app = App()


@app.entrypoint
def invoke(context: InvocationContext) -> dict[str, Any]:
    """Main agent invocation endpoint.

    Receives user messages and returns agent responses.
    AgentCore Runtime routes /invocations requests here.
    """
    # Parse input
    body = context.request_body
    if isinstance(body, str):
        body = json.loads(body)

    user_message = body.get("message", body.get("input", ""))
    session_id = body.get("session_id", "default")
    customer_id = body.get("customer_id", "CUST-001")

    # Create agent (stateless per request; state lives in DynamoDB in production)
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        streaming=False,  # Non-streaming for Runtime compatibility
    )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )

    # Invoke agent
    response = agent(user_message)

    # Extract text response
    response_text = ""
    if hasattr(response, "message"):
        content = response.message.get("content", [])
        for block in content:
            if isinstance(block, dict) and "text" in block:
                response_text += block["text"]
            elif hasattr(block, "text"):
                response_text += block.text
    else:
        response_text = str(response)

    return {
        "response": response_text,
        "session_id": session_id,
        "customer_id": customer_id,
    }


# ─── Local testing ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # For local testing, run as HTTP server on port 8080
    app.configure(port=8080)
    app.launch()
