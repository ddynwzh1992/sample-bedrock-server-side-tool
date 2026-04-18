"""ShopAssist Agent — AgentCore Runtime Deployment.

Hosts the ShopAssist agent on Amazon Bedrock AgentCore Runtime.
On /invocations, calls the Bedrock Responses API with server-side tool execution
via AgentCore Gateway — the model discovers and invokes tools automatically.

Architecture:
  Client → Runtime /invocations → Responses API → GPT OSS → Gateway → Lambda → DynamoDB
                                       ↓
                              (tool results injected server-side)
                                       ↓
                              Final response streamed back

Environment variables (auto-injected by CloudFormation):
  GATEWAY_ARN: AgentCore Gateway ARN
  AWS_REGION: AWS region (default: us-west-2)
  BEDROCK_MODEL_ID: Model ID (default: openai.gpt-oss-120b)
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure bundled deps are on path (resolve otel version conflicts with Runtime preinstalls)
_deps = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deps")
if os.path.isdir(_deps):
    sys.path.insert(0, _deps)


# ─── Configuration ───────────────────────────────────────────────────────────────

REGION = os.environ.get("AWS_REGION", "us-west-2")
GATEWAY_ARN = os.environ.get("GATEWAY_ARN", "")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "openai.gpt-oss-120b")
SYSTEM_PROMPT = (
    "You are ShopAssist, an AI e-commerce shopping assistant. "
    "Use the available tools to search products, manage carts, and handle orders. "
    "Be concise and helpful. The customer_id is provided in each request."
)


# ─── Server-Side Tool Execution ─────────────────────────────────────────────────

def call_responses_api(user_message: str, customer_id: str = "CUST-001") -> str:
    """Call Bedrock Responses API with server-side tool execution via Gateway.

    Returns the final text response after all tool calls complete.
    """
    # Lazy imports to keep startup fast
    import boto3
    import requests
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    session = boto3.Session(region_name=REGION)
    credentials = session.get_credentials().get_frozen_credentials()
    url = f"https://bedrock-mantle.{REGION}.api.aws/v1/responses"

    prompt = f"{SYSTEM_PROMPT} Customer ID for this session: {customer_id}"

    payload = {
        "model": MODEL_ID,
        "stream": True,
        "background": False,
        "store": False,
        "instructions": prompt,
        "tools": [
            {
                "type": "mcp",
                "server_label": "agentcore_tools",
                "connector_id": GATEWAY_ARN,
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
    req = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    SigV4Auth(credentials, "bedrock", REGION).add_auth(req)

    resp = requests.post(
        url, data=body, headers=dict(req.headers), timeout=120, stream=True
    )
    resp.raise_for_status()

    # Parse SSE stream
    output_text = ""
    tool_calls = 0
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data = json.loads(line[6:])
        event_type = data.get("type", "")

        if event_type == "response.output_text.delta":
            output_text += data.get("delta", "")
        elif event_type == "response.mcp_call.completed":
            tool_calls += 1
        elif event_type == "response.completed":
            break

    return output_text


# ─── HTTP Handler (AgentCore Runtime Interface) ─────────────────────────────────

class RuntimeHandler(BaseHTTPRequestHandler):
    """HTTP handler for AgentCore Runtime.

    Endpoints:
      POST /invocations - Agent invocation
      GET  /ping        - Health check
    """

    def do_POST(self):
        if self.path == "/invocations":
            self._handle_invocation()
        else:
            self._send(404, {"error": "Not found"})

    def do_GET(self):
        if self.path == "/ping":
            self._send(200, {"status": "healthy", "agent": "ShopAssist"})
        else:
            self._send(404, {"error": "Not found"})

    def _handle_invocation(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            # Support multiple input formats
            user_message = (
                body.get("query")
                or body.get("message")
                or body.get("input")
                or ""
            )
            customer_id = body.get("customer_id", "CUST-001")

            if not user_message:
                self._send(400, {"error": "Missing 'query', 'message', or 'input' field"})
                return

            if not GATEWAY_ARN:
                self._send(500, {"error": "GATEWAY_ARN not configured"})
                return

            # Call Responses API with server-side tool execution
            response_text = call_responses_api(user_message, customer_id)

            self._send(200, {
                "response": response_text,
                "customer_id": customer_id,
                "model": MODEL_ID,
                "mode": "server-side-tool-execution",
            })

        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    def _send(self, code: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass


# ─── Entrypoint ──────────────────────────────────────────────────────────────────

def app():
    """AgentCore Runtime entrypoint.

    Starts HTTP server on port 8080 (Runtime default).
    """
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), RuntimeHandler)
    print(f"ShopAssist Runtime started on port {port}")
    print(f"  Model:   {MODEL_ID}")
    print(f"  Gateway: {GATEWAY_ARN}")
    print(f"  Region:  {REGION}")
    print(f"  Mode:    Server-Side Tool Execution (Responses API)")
    server.serve_forever()


if __name__ == "__main__":
    app()
