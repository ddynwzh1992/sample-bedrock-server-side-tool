# ShopAssist: E-Commerce Agent Demo

> **Bedrock Server-Side Tool Execution + AgentCore Gateway + AgentCore Runtime + Strands Agents SDK**

An AI-powered e-commerce shopping assistant demonstrating how **Amazon Bedrock executes tools server-side** — the model discovers, selects, and invokes tools automatically with zero client-side orchestration.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CloudFormation Stack                               │
│                                                                             │
│  ┌──────────┐    ┌─────────────────────────────────────────────────────┐    │
│  │  Client   │    │              Amazon Bedrock (Mantle)                │    │
│  │           │    │                                                     │    │
│  │ CLI / App ├───►│  Responses API  ──►  GPT OSS 120B                  │    │
│  │           │    │  POST /v1/responses   (server-side tool execution)  │    │
│  └──────────┘    │       │                      │                      │    │
│       ▲          │       │ ① Discover tools     │ ② Model decides to   │    │
│       │          │       │    (MCP list_tools)   │    call a tool       │    │
│       │          └───────┼──────────────────────┼──────────────────────┘    │
│       │                  ▼                      ▼                           │
│       │          ┌─────────────────────────────────────────────────┐        │
│       │          │          AgentCore Gateway (MCP Endpoint)       │        │
│       │          │                                                 │        │
│       │          │   ③ Routes tool call to correct Lambda target   │        │
│       │          │      (IAM authenticated, auto-discovered)       │        │
│       │          └────────┬──────────────┬──────────────┬──────────┘        │
│       │                   │              │              │                   │
│       │                   ▼              ▼              ▼                   │
│       │          ┌──────────────┐ ┌────────────┐ ┌─────────────┐           │
│       │          │   Products   │ │    Cart    │ │   Orders    │           │
│       │          │   Lambda     │ │   Lambda   │ │   Lambda    │           │
│       │          ├──────────────┤ ├────────────┤ ├─────────────┤           │
│       │          │search_products│ │add_to_cart │ │checkout     │           │
│       │          │get_details   │ │view_cart   │ │order_status │           │
│       │          │get_recommend │ │remove_item │ │list_orders  │           │
│       │          │              │ │apply_coupon│ │request_return│          │
│       │          └──────┬───────┘ └─────┬──────┘ └──────┬──────┘           │
│       │                 │               │               │                  │
│       │                 ▼               ▼               ▼                  │
│       │          ┌──────────────┐ ┌────────────┐ ┌─────────────┐           │
│       │          │  DynamoDB    │ │  DynamoDB  │ │  DynamoDB   │           │
│       │          │  Products    │ │   Carts    │ │   Orders    │           │
│       │          └──────────────┘ └────────────┘ └─────────────┘           │
│       │                                                                    │
│       │   ④ Results injected back into model context automatically         │
│       │   ⑤ Model generates final response with tool results              │
│       │                                                                    │
│       └─── ⑥ Streaming response returned to client ◄──────────────────    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    AgentCore Runtime (Optional)                      │    │
│  │  Managed Python 3.12 hosting  │  Auto-scaling  │  /invocations     │    │
│  │  Strands Agent + Bedrock SDK  │  Observability │  Health checks    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow (Server-Side Tool Execution)

```
┌────────┐          ┌──────────────┐          ┌─────────┐          ┌────────┐
│ Client │          │ Responses API│          │ Gateway │          │ Lambda │
└───┬────┘          └──────┬───────┘          └────┬────┘          └───┬────┘
    │                      │                       │                   │
    │  POST /v1/responses  │                       │                   │
    │  + Gateway ARN       │                       │                   │
    │─────────────────────►│                       │                   │
    │                      │                       │                   │
    │                      │  ① MCP list_tools     │                   │
    │                      │──────────────────────►│                   │
    │                      │  tools: [11 tools]    │                   │
    │                      │◄──────────────────────│                   │
    │                      │                       │                   │
    │                      │  ② Model reasons:     │                   │
    │                      │  "search_products"    │                   │
    │                      │                       │                   │
    │                      │  ③ MCP tools/call     │                   │
    │                      │──────────────────────►│  ④ Invoke Lambda  │
    │                      │                       │──────────────────►│
    │                      │                       │  products data    │
    │                      │                       │◄──────────────────│
    │                      │  tool result          │                   │
    │                      │◄──────────────────────│                   │
    │                      │                       │                   │
    │                      │  ⑤ Model generates    │                   │
    │                      │  final response       │                   │
    │                      │                       │                   │
    │  ⑥ SSE stream:       │                       │                   │
    │  tool events + text  │                       │                   │
    │◄─────────────────────│                       │                   │
    │                      │                       │                   │
```

### Why Server-Side Tool Execution?

| Aspect | Client-Side (Traditional) | Server-Side (This Demo) |
|--------|--------------------------|------------------------|
| **Tool orchestration** | Client code loops: call model → parse tool → execute → send result → repeat | Single API call — Bedrock handles everything |
| **Code complexity** | 50+ lines of orchestration logic | 1 API call with Gateway ARN |
| **Latency** | Multiple round-trips (client ↔ model ↔ client) | All happens server-side, near-zero network overhead |
| **Security** | Client needs tool credentials | Tools run in AWS with IAM — client never sees credentials |
| **Scaling** | Client must handle concurrency | Bedrock + Lambda auto-scale |

## How It Works

### Single API Call — That's It

```python
# This is the ENTIRE agent logic. No orchestration loop.
response = requests.post(
    "https://bedrock-mantle.us-west-2.api.aws/v1/responses",
    json={
        "model": "openai.gpt-oss-120b",
        "stream": True,
        "background": False,
        "store": False,
        "tools": [{
            "type": "mcp",
            "server_label": "agentcore_tools",
            "connector_id": "<GATEWAY_ARN>",        # Gateway discovers tools automatically
            "require_approval": "never",
        }],
        "input": [{                                   # Must use message array format
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Find headphones under $100"}]
        }]
    }
)
# Stream SSE events → get tool calls + final text response
```

> **⚠️ Important:** The `input` field must use the full message array format (not a plain string). Using `"input": "plain text"` causes the model to loop tool calls indefinitely.

### Example Conversation

```
🧑 You: I'm looking for wireless headphones under $100

🤖 ShopAssist: I found some great options for you:

• [ELEC-001] SoundWave Pro Wireless Headphones — $79.99 | ★ 4.5 (2847 reviews)
  Premium ANC, 30-hour battery, memory foam cushions

• [ELEC-005] RunnerX Sport Earbuds — $69.99 | ★ 4.4 (3156 reviews)
  Secure-fit, bone conduction, IP67, 10-hour battery

• [ELEC-003] AirBud Mini Earbuds — $49.99 | ★ 4.2 (5621 reviews)
  True wireless, touch controls, IPX5, 24-hour total battery

Would you like details on any of these, or shall I add one to your cart?
```

## Quick Start

### Prerequisites

- AWS account with Bedrock model access enabled for `openai.gpt-oss-120b`
- AWS CLI configured (`aws configure`)
- Python 3.12+

> **Note:** Uses standard AWS IAM credentials (SigV4). No separate API key needed.

### Deploy (One Command)

```bash
# 1. Create S3 bucket & upload agent code
aws s3 mb s3://my-shopassist-artifacts --region us-west-2
./infrastructure/package_agent.sh my-shopassist-artifacts

# 2. Deploy entire stack
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-one-click.yaml \
  --stack-name shopassist-demo \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    AgentCodeS3Bucket=my-shopassist-artifacts \
    AgentCodeS3Key=shopassist-agent/agent.zip \
  --region us-west-2
```

This creates **everything** in one command:
- 3 DynamoDB tables (Products, Carts, Orders)
- 3 Lambda functions with 11 tool handlers
- AgentCore Gateway (MCP endpoint) with 3 Lambda targets
- AgentCore Runtime hosting the Strands agent
- All IAM roles with least-privilege policies

### Test

```bash
# Get Gateway ARN
GATEWAY_ARN=$(aws cloudformation describe-stacks --stack-name shopassist-demo \
  --query 'Stacks[0].Outputs[?OutputKey==`GatewayArn`].OutputValue' --output text --region us-west-2)

# Run interactive demo
pip install boto3 requests strands-agents
export GATEWAY_ARN
python -m agent.serverside_agent
```

## Project Structure

```
ecommerce-agent-demo/
├── agent/
│   ├── data.py                  # 50+ sample products, in-memory state
│   ├── local_agent.py           # Strands Agent + @tool (client-side mode)
│   ├── gateway_agent.py         # MCP Client → AgentCore Gateway
│   ├── serverside_agent.py      # Responses API server-side tool execution
│   └── runtime_agent.py         # AgentCore Runtime deployment wrapper
├── lambda/
│   ├── products/handler.py      # Product search, details, recommendations
│   ├── cart/handler.py          # Cart operations
│   └── orders/handler.py       # Order management
├── infrastructure/
│   ├── cloudformation-one-click.yaml  # One-click CFN deployment
│   ├── package_agent.sh         # Package agent → S3
│   └── seed_data.py             # Seed DynamoDB with products
├── demo/
│   └── run_demo.py              # Interactive CLI demo
├── tools/
│   └── tool_schemas.json        # MCP tool schemas
├── docs/
│   ├── architecture.md          # Detailed architecture
│   └── setup.md                 # Setup guide
├── README.md
├── requirements.txt
├── DESIGN.md
└── Dockerfile                   # Optional container mode
```

## Tools (11 Total)

| Tool | Lambda | Description |
|------|--------|-------------|
| `search_products` | Products | Search by keyword, category, price range |
| `get_product_details` | Products | Full product info by ID |
| `get_recommendations` | Products | Top-rated recommendations |
| `add_to_cart` | Cart | Add product to cart |
| `view_cart` | Cart | View cart contents and totals |
| `remove_from_cart` | Cart | Remove item from cart |
| `apply_coupon` | Cart | Apply discount code (WELCOME10, SUMMER20, VIP30) |
| `checkout` | Orders | Place order from cart |
| `get_order_status` | Orders | Check order tracking |
| `list_orders` | Orders | List customer's order history |
| `request_return` | Orders | Request return/refund |

## Key Technical Details

### Server-Side Tool Execution (Responses API)

- **Endpoint:** `https://bedrock-mantle.<region>.api.aws/v1/responses`
- **Model:** `openai.gpt-oss-120b` (currently the only model supporting server-side tool execution)
- **Auth:** SigV4 with `bedrock` service name
- **Streaming:** Required — use `"stream": true`
- **Input format:** Must use message array: `[{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "..."}]}]`
- **Tool type:** `"type": "mcp"` with `"connector_id"` set to Gateway ARN

### AgentCore Gateway

- Converts Lambda functions into MCP-compatible tools
- Handles tool discovery (`tools/list`) and execution (`tools/call`)
- IAM-authenticated targets via `GATEWAY_IAM_ROLE` credential provider
- Tool schemas defined inline in CloudFormation using `SchemaDefinition` format

### AgentCore Runtime

- Managed Python 3.12 hosting for AI agents
- S3 code package deployment (like Lambda, but for long-running agents)
- Built-in `/invocations` and `/ping` endpoints
- Auto-scaling, observability, and lifecycle management
- Gateway ARN auto-injected via environment variables

### Model Support

| Model | Responses API | Server-Side Tools | Notes |
|-------|:---:|:---:|-------|
| GPT OSS 120B | ✅ | ✅ | Primary model for this demo |
| GPT OSS 20B | ✅ | ✅ | Lower cost alternative |
| Claude, Llama, etc. | ❌ | ❌ | Use Converse API for client-side tool calling |

> Server-side tool execution via Responses API is currently available for GPT OSS models. Other models support client-side tool calling via the Converse API.

## References

- [Bedrock Server-Side Tool Execution docs](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.html)
- [AgentCore Gateway docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [Responses API (Mantle) docs](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)
- [Strands Agents SDK](https://strandsagents.com)
- [Model Cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html)

## License

MIT
