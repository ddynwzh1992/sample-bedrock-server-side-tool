"""ShopAssist — AgentCore Runtime with Server-Side Tool Execution.

This is the production entrypoint deployed to AgentCore Runtime.
It uses the Bedrock Responses API (Mantle) with an MCP server connector
pointing to an AgentCore Gateway, enabling fully server-side tool execution.

The model (GPT OSS 120B) discovers tools from the Gateway, reasons about
which to call, executes them, and generates a final response — all within
a single API call. No client-side orchestration loop needed.
"""

import os
import json
import ssl
import urllib.request

# AgentCore SDK — must be bundled in the deployment package
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

# ---------------------------------------------------------------------------
# Configuration (injected via Runtime environmentVariables)
# ---------------------------------------------------------------------------
REGION = os.environ.get("AWS_REGION", "us-west-2")
GATEWAY_ARN = os.environ.get("GATEWAY_ARN", "")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "openai.gpt-oss-120b")
MANTLE_URL = f"https://bedrock-mantle.{REGION}.api.aws/v1/responses"

SYSTEM_PROMPT = (
    "You are ShopAssist, a friendly and helpful AI e-commerce shopping assistant. "
    "Use the available tools to search products, manage shopping carts, and handle orders. "
    "Always be concise, accurate, and proactive in suggesting next steps."
)

print(f"🛍️  ShopAssist Runtime")
print(f"   Model:   {MODEL_ID}")
print(f"   Gateway: {GATEWAY_ARN}")
print(f"   Region:  {REGION}")
print(f"   ✅ Ready for requests")


# ---------------------------------------------------------------------------
# Responses API caller (server-side tool execution)
# ---------------------------------------------------------------------------
def call_responses_api(user_message: str, customer_id: str = "CUST-001") -> tuple[str, int]:
    """Call Bedrock Responses API with server-side tool execution via Gateway.

    Returns:
        Tuple of (response_text, tool_call_count)
    """
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    session = boto3.Session(region_name=REGION)
    creds = session.get_credentials().get_frozen_credentials()

    payload = {
        "model": MODEL_ID,
        "stream": True,
        "background": False,
        "store": False,
        "instructions": f"{SYSTEM_PROMPT} Customer ID: {customer_id}",
        "tools": [
            {
                "type": "mcp",
                "server_label": "agentcore_tools",
                "connector_id": GATEWAY_ARN,
                "server_description": "E-commerce tools: product search, cart, orders",
                "require_approval": "never",
            }
        ],
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": user_message}],
            }
        ],
    }

    body = json.dumps(payload).encode()

    # SigV4 sign for bedrock-mantle
    awsreq = AWSRequest(
        method="POST",
        url=MANTLE_URL,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    SigV4Auth(creds, "bedrock", REGION).add_auth(awsreq)

    req = urllib.request.Request(MANTLE_URL, data=body, method="POST")
    for k, v in awsreq.headers.items():
        req.add_header(k, v)

    resp = urllib.request.urlopen(req, timeout=120, context=ssl.create_default_context())

    # Parse SSE stream
    output_text = ""
    tool_calls = 0
    buf = b""

    while True:
        chunk = resp.read(4096)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = line.decode("utf-8", errors="replace").strip()
            if not text.startswith("data: "):
                continue
            event = json.loads(text[6:])
            event_type = event.get("type", "")
            if event_type == "response.output_text.delta":
                output_text += event.get("delta", "")
            elif event_type == "response.mcp_call.completed":
                tool_calls += 1
            elif event_type == "response.completed":
                return output_text, tool_calls

    return output_text, tool_calls


# ---------------------------------------------------------------------------
# AgentCore entrypoint
# ---------------------------------------------------------------------------
@app.entrypoint
async def invoke(payload, context):
    """Handle an invocation from AgentCore Runtime."""
    if isinstance(payload, str):
        payload = json.loads(payload)

    user_message = (
        payload.get("query")
        or payload.get("prompt")
        or payload.get("message")
        or ""
    )
    customer_id = payload.get("customer_id", "CUST-001")

    if not user_message:
        yield {"type": "text", "content": "Please provide a query."}
        return

    if not GATEWAY_ARN:
        yield {"type": "text", "content": "Error: GATEWAY_ARN not configured."}
        return

    try:
        text, tc = call_responses_api(user_message, customer_id)
        print(f"✓ {len(text)} chars, {tc} tool calls")
        yield {"type": "text", "content": text}
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"type": "text", "content": f"Error: {e}"}


if __name__ == "__main__":
    app.run()
