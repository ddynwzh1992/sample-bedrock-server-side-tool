# ShopAssist: E-Commerce Agent Demo

> **Bedrock Server-Side Tool Execution + AgentCore Gateway + AgentCore Runtime**

An AI-powered e-commerce shopping assistant where **Amazon Bedrock executes tools server-side** — the model discovers, selects, and invokes tools automatically with zero client-side orchestration.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│  ┌──────────┐    ┌──────────────────────────────────────────────────────────┐    │
│  │          │    │              AgentCore Runtime                            │    │
│  │  Client  │    │         Managed Python 3.12 · Auto-scaling               │    │
│  │          │    │                                                          │    │
│  │ CLI/App/ ├───►│  POST /invocations                                      │    │
│  │ API Call │    │    │                                                      │    │
│  └──────────┘    │    ▼                                                      │    │
│       ▲          │  ┌────────────────────────────────────────────────────┐   │    │
│       │          │  │  shopassist_runtime.py                            │   │    │
│       │          │  │  Calls Bedrock Responses API (Mantle)             │   │    │
│       │          │  │  with Gateway ARN as MCP connector                │   │    │
│       │          │  └───────────────────────┬────────────────────────────┘   │    │
│       │          └──────────────────────────┼───────────────────────────────┘    │
│       │                                     │                                    │
│       │                                     ▼                                    │
│       │          ┌──────────────────────────────────────────────────────────┐    │
│       │          │         Amazon Bedrock Responses API (Mantle)            │    │
│       │          │                                                          │    │
│       │          │  GPT OSS 120B  ───►  reasons + selects tools            │    │
│       │          │       │                      │                            │    │
│       │          │       │ ① Discover tools     │ ② Execute tool call       │    │
│       │          │       │    (MCP list_tools)   │    (MCP tools/call)       │    │
│       │          └───────┼──────────────────────┼───────────────────────────┘    │
│       │                  ▼                      ▼                                │
│       │          ┌──────────────────────────────────────────────────────────┐    │
│       │          │            AgentCore Gateway (MCP Endpoint)              │    │
│       │          │                                                          │    │
│       │          │   ③ Routes tool calls to Lambda targets (IAM auth)       │    │
│       │          └────────┬──────────────────┬──────────────────┬───────────┘    │
│       │                   ▼                  ▼                  ▼                │
│       │          ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│       │          │   Products   │   │     Cart     │   │    Orders    │         │
│       │          │   Lambda     │   │    Lambda    │   │    Lambda    │         │
│       │          ├──────────────┤   ├──────────────┤   ├──────────────┤         │
│       │          │search_products│  │add_to_cart   │   │checkout      │         │
│       │          │get_details   │   │view_cart     │   │order_status  │         │
│       │          │get_recommend │   │remove_item   │   │list_orders   │         │
│       │          │              │   │apply_coupon  │   │request_return│         │
│       │          └──────┬───────┘   └──────┬───────┘   └──────┬───────┘         │
│       │                 ▼                  ▼                  ▼                  │
│       │          ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│       │          │  DynamoDB    │   │  DynamoDB    │   │  DynamoDB    │         │
│       │          │  Products    │   │   Carts      │   │   Orders     │         │
│       │          └──────────────┘   └──────────────┘   └──────────────┘         │
│       │                                                                         │
│       └──── ④ Response returned via Runtime (tool results + final answer)       │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Why Server-Side Tool Execution?

| Aspect | Client-Side (Traditional) | Server-Side (This Demo) |
|--------|--------------------------|------------------------|
| **Orchestration** | Client loops: model → parse → execute → send result → repeat | Single API call — Bedrock handles the loop |
| **Code complexity** | 50+ lines of tool-call orchestration | 1 API call with Gateway ARN |
| **Latency** | Multiple client↔model round-trips | All server-side, near-zero network overhead |
| **Security** | Client needs tool credentials | Tools execute in AWS with IAM — client never sees credentials |

## Quick Start

### Prerequisites

- AWS account with Bedrock model access for `openai.gpt-oss-120b`
- AWS CLI configured (`aws configure`)
- Python 3.12+
- Docker (for container-based Runtime deployment)

### Deploy

```bash
# 0. Install dependencies
pip install bedrock-agentcore==1.0.7 bedrock-agentcore-starter-toolkit==0.2.1

# 1. Deploy CloudFormation stack (Gateway + Lambdas + DynamoDB)
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-one-click.yaml \
  --stack-name shopassist-demo \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-west-2

# 2. Deploy agent to AgentCore Runtime (container-based)
pip install boto3
python deploy_container.py
```

The deploy script will:
1. Build a Docker image with all dependencies
2. Push to ECR
3. Create an AgentCore Runtime with the container
4. Attach `AmazonBedrockMantleFullAccess` IAM policy automatically
5. Wait for READY status and run a test invocation

### Test

```bash
# Via AgentCore Runtime (production path)
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn <RUNTIME_ARN> \
  --payload '{"query": "Find headphones under $100", "customer_id": "CUST-001"}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  output.json && cat output.json
```

### Example

```
🧑 "Find headphones under $100"

🤖 Here are some headphones under $100:
   • SoundWave Pro Wireless Headphones — $79.99 ★4.5
   • AirBud Mini Earbuds — $49.99 ★4.2
   • RunnerX Sport Earbuds — $69.99 ★4.4

🧑 "Add the SoundWave Pro to my cart"

🤖 ✅ Added SoundWave Pro Wireless Headphones to your cart (1 × $79.99)

🧑 "Show me my cart"

🤖 Your cart:
   | Item | Qty | Price |
   | SoundWave Pro Wireless Headphones | 1 | $79.99 |
   Total: $79.99

🧑 "What's the status of order ORD-20260401-001?"

🤖 Your order ORD-20260401-001 has been delivered ✅
```

## Project Structure

```
ecommerce-agent-demo/
├── agent/
│   ├── shopassist_runtime.py    # ★ Production: Runtime + Responses API
│   ├── serverside_agent.py      # Standalone Responses API demo
│   ├── gateway_agent.py         # MCP Client → Gateway (client-side)
│   ├── local_agent.py           # Strands Agent + @tool (fully local)
│   └── data.py                  # 50+ sample products, in-memory state
├── lambda/
│   ├── products/handler.py      # Product search, details, recommendations
│   ├── cart/handler.py          # Cart CRUD operations
│   └── orders/handler.py        # Order management
├── infrastructure/
│   ├── cloudformation-one-click.yaml  # Full stack CFN template
│   ├── package_agent.sh         # Package agent → S3
│   └── seed_data.py             # Seed DynamoDB tables
├── deploy.py                    # Toolkit-based deployment script
├── requirements.txt             # Local dev dependencies
├── requirements-runtime.txt     # Runtime deployment dependencies
└── README.md
```

## Tools (11 Total)

| Tool | Lambda | Description |
|------|--------|-------------|
| `search_products` | Products | Search by keyword, category, price range |
| `get_product_details` | Products | Full product info by ID |
| `get_recommendations` | Products | Top-rated recommendations |
| `add_to_cart` | Cart | Add product with quantity |
| `view_cart` | Cart | View contents and totals |
| `remove_from_cart` | Cart | Remove item from cart |
| `apply_coupon` | Cart | Apply discount (WELCOME10, SAVE20, SPRING25, TECH15) |
| `checkout` | Orders | Place order from cart |
| `get_order_status` | Orders | Check order tracking |
| `list_orders` | Orders | Customer's order history |
| `request_return` | Orders | Request return/refund |

## Technical Details

### Responses API (Mantle)

- **Endpoint:** `https://bedrock-mantle.<region>.api.aws/v1/responses`
- **Auth:** SigV4 with service name `bedrock` + **AmazonBedrockMantleFullAccess** IAM policy
- **Model:** `openai.gpt-oss-120b` (only model family supporting server-side tool execution)
- **Streaming:** Required (`"stream": true`) — non-streaming times out for tool-heavy requests
- **Input format:** Must use message array — `[{"type": "message", "role": "user", "content": [...]}]`

### AgentCore Gateway

- Exposes Lambda functions as MCP-compatible tools
- Handles tool discovery (`tools/list`) and execution (`tools/call`)
- IAM-authenticated targets via `GATEWAY_IAM_ROLE` credential provider
- Tool schemas defined in CloudFormation using `SchemaDefinition` format

### AgentCore Runtime

- Managed Python 3.12 hosting for the agent
- Receives `/invocations` → calls Responses API internally
- S3 code package deployment (direct_code_deploy via toolkit)
- Gateway ARN injected via `environmentVariables`
- **Note:** Runtime does not preinstall `bedrock-agentcore` SDK — it must be bundled in the deployment package

### Deployment Notes

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: bedrock_agentcore` | Toolkit's cross-compile (`--only-binary :all:`) skips pure-Python packages. Manually inject `bedrock_agentcore` into the deployment zip |
| Runtime init > 30s timeout | Keep top-level imports minimal; heavy imports (boto3, etc.) inside functions |
| Responses API 401 from Runtime | Attach `AmazonBedrockMantleFullAccess` managed policy to the Runtime execution role |
| Model loops tool calls | Use message array format for `input` field, not plain string |

## References

- [Bedrock Responses API (Mantle)](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)
- [AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [Server-Side Tool Execution](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.html)
- [AmazonBedrockMantleFullAccess](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam-awsmanpol.html#security-iam-awsmanpol-AmazonBedrockMantleFullAccess)

## License

MIT
