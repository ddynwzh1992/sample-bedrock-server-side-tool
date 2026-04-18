# ShopAssist: E-Commerce Agent Demo

> **Strands Agents SDK + Bedrock Server-Side Tool Execution + AgentCore Gateway**

An AI-powered e-commerce shopping assistant that demonstrates three AWS technologies working together:

1. **[Strands Agents SDK](https://strandsagents.com)** — Open-source agent framework with `@tool` decorators
2. **[Amazon Bedrock Server-Side Tool Execution](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-bedrock-server-side-tool-execution-agentcore-gateway/)** — Execute tools server-side via Responses API (no client orchestration loop)
3. **[Amazon Bedrock AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)** — Managed MCP endpoint that turns Lambda functions into agent tools

## Architecture

```mermaid
graph TB
    subgraph "Client"
        U[Customer] --> CLI[Interactive CLI]
    end

    subgraph "Agent Layer"
        CLI --> SA[Strands Agent<br/>system prompt + tools]
    end

    subgraph "Amazon Bedrock"
        SA --> RA[Responses API<br/>Server-Side Tool Execution]
        RA --> MODEL[GPT OSS 120B<br/>bedrock-mantle endpoint]
    end

    subgraph "AgentCore Gateway"
        MODEL --> |tool calls| GW[Gateway MCP Endpoint<br/>Tool Discovery + Execution]
        GW --> |"search_products<br/>get_product_details<br/>get_recommendations"| LP[Lambda: Products]
        GW --> |"add_to_cart<br/>view_cart<br/>remove_from_cart<br/>apply_coupon"| LC[Lambda: Cart]
        GW --> |"checkout<br/>get_order_status<br/>list_orders<br/>request_return"| LO[Lambda: Orders]
    end

    subgraph "Data Layer"
        LP --> DB[(DynamoDB<br/>Products)]
        LC --> DB2[(DynamoDB<br/>Carts)]
        LO --> DB3[(DynamoDB<br/>Orders)]
    end

    subgraph "AgentCore Runtime"
        RT[Managed Python Runtime<br/>Auto-scaling + Observability] --> SA
    end

    style GW fill:#ff9900,color:#000
    style MODEL fill:#8b5cf6,color:#fff
    style SA fill:#06b6d4,color:#fff
    style RT fill:#10b981,color:#fff
```

## How It Works

### Server-Side Tool Execution (Bedrock Responses API)

```
Customer → Responses API (with Gateway ARN) → GPT OSS 120B (bedrock-mantle)
                    ↓ (server executes tools automatically)
              AgentCore Gateway → Lambda → result injected
                    ↓
              Final response returned in one API call
```

No client-side orchestration loop. Bedrock handles tool discovery, selection, execution, and result injection — all in a single API call.

### Production Deployment (AgentCore Runtime)

```
Client → AgentCore Runtime (/invocations) → Python Agent (Strands SDK) → Bedrock + Gateway
```

The agent is deployed as a managed Python service on AgentCore Runtime (default mode) with auto-scaling, health checks, and observability. No container needed — just upload your Python code to S3.

## Quick Start

### Prerequisites

- AWS account with Bedrock model access enabled for `openai.gpt-oss-120b`
- AWS CLI configured with appropriate permissions (`aws configure`)
- Python 3.12+

> **Note:** Authentication uses standard AWS IAM credentials (SigV4). No separate API key needed — just `aws configure`.

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

🧑 You: Add the SoundWave to my cart and apply WELCOME10

🤖 ShopAssist: Done! ✓

Added: SoundWave Pro Wireless Headphones × 1 ($79.99)
Coupon WELCOME10 applied: 10% off your first order

Your cart: $79.99 - $8.00 = $71.99

Ready to checkout, or would you like to keep browsing?
```

## AWS Deployment

### Step 1: Package & Upload Agent Code to S3

```bash
# Create S3 bucket (one-time)
aws s3 mb s3://my-shopassist-artifacts --region us-west-2

# Package agent code and upload
./infrastructure/package_agent.sh my-shopassist-artifacts
```

### Step 2: One-Click CloudFormation Deploy

Deploys **everything** in one command — DynamoDB, Lambda tools, AgentCore Gateway + Targets, and AgentCore Runtime:

```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-one-click.yaml \
  --stack-name shopassist-demo \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    AgentCodeS3Bucket=my-shopassist-artifacts \
    AgentCodeS3Key=shopassist-agent/agent.zip \
  --region us-west-2
```

This creates:
- **3 DynamoDB tables** (Products, Carts, Orders)
- **3 Lambda functions** with inline tool code
- **AgentCore Gateway** (MCP endpoint) with 3 Lambda targets and inline tool schemas
- **AgentCore Runtime** (Python 3.12, default mode) hosting the agent directly
- All IAM roles with least-privilege policies

### Step 3: Get Outputs & Test

```bash
# Get all endpoints
aws cloudformation describe-stacks --stack-name shopassist-demo \
  --query 'Stacks[0].Outputs' --output table
```

The stack outputs include:
- **RuntimeEndpoint** — The AgentCore Runtime `/invocations` endpoint (production)
- **GatewayUrl** — The Gateway MCP endpoint
- **GatewayArn** — The Gateway ARN (already injected into Runtime as env var)

Test the deployed agent:

```bash
# Call the Runtime endpoint directly (Gateway ARN is auto-injected)
curl -X POST <RuntimeEndpoint>/invocations \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me wireless headphones under $100", "customer_id": "CUST-001"}'
```

## Project Structure

```
ecommerce-agent-demo/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── DESIGN.md                          # Design specification
├── agent/
│   ├── __init__.py
│   ├── data.py                        # 50+ sample products, in-memory state
│   ├── local_agent.py                 # Local mode: Strands Agent + @tool functions
│   ├── gateway_agent.py              # Client-side: MCP Client → AgentCore Gateway
│   ├── serverside_agent.py           # Server-side: Responses API (OpenAI SDK + mantle)
│   └── runtime_agent.py             # AgentCore Runtime deployment wrapper
├── demo/
│   └── run_demo.py                    # Interactive CLI demo
├── lambda/
│   ├── products/handler.py            # Product search, details, recommendations
│   ├── cart/handler.py                # Cart operations
│   └── orders/handler.py             # Order management
├── infrastructure/
│   ├── cloudformation-one-click.yaml  # One-click CFN (DynamoDB+Lambda+Gateway+Runtime)
│   ├── package_agent.sh               # Package agent code → S3 for Runtime
│   ├── template.yaml                  # AWS SAM template (alternative)
│   └── seed_data.py                   # Seed DynamoDB with products
├── tools/
│   └── tool_schemas.json             # MCP tool schemas for Gateway
├── Dockerfile                         # Optional: container mode for AgentCore Runtime
└── docs/
    ├── architecture.md                # Detailed architecture docs
    └── setup.md                       # Step-by-step setup guide
```

## Tools Reference

| Tool | Category | Description |
|------|----------|-------------|
| `search_products` | Products | Search by keyword, category, price range |
| `get_product_details` | Products | Get full product info by ID |
| `get_recommendations` | Products | Top-rated product recommendations |
| `add_to_cart` | Cart | Add product to cart |
| `view_cart` | Cart | View cart contents and totals |
| `remove_from_cart` | Cart | Remove item from cart |
| `apply_coupon` | Cart | Apply discount code |
| `checkout` | Orders | Place order |
| `get_order_status` | Orders | Check order tracking |
| `list_orders` | Orders | List customer's orders |
| `request_return` | Orders | Request return/refund |

## Key Concepts Demonstrated

### Bedrock Server-Side Tool Execution
- Uses OpenAI SDK pointing to **bedrock-mantle** endpoint
- `client.responses.create()` with MCP tool type and Gateway ARN
- Single API call — no client-side orchestration loop
- Automatic tool discovery, selection, execution, and result injection

### AgentCore Gateway
- Converts Lambda functions into MCP-compatible tools
- Single managed endpoint for all tools
- Built-in auth (IAM, OAuth, JWT)
- Semantic tool search for large tool collections
- Works with any agent framework (Strands, LangGraph, CrewAI)

### AgentCore Runtime
- Serverless hosting for AI agents — no infra management
- Default mode: Python 3.12 runtime with S3 code package (like Lambda, but for agents)
- Alternative: Container mode with ECR image
- Built-in `/invocations` and `/ping` endpoints
- Auto-scaling, observability, and lifecycle management

### Strands Agents SDK
- `@tool` decorator converts any Python function into an agent tool
- Docstrings automatically become LLM-facing tool descriptions
- `Agent()` class handles the full agent loop
- `BedrockModel` for Amazon Bedrock integration

## Environment Variables

All injected automatically by CloudFormation into AgentCore Runtime. No manual config needed for production.

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `openai.gpt-oss-120b` | Bedrock model to use |
| `AWS_REGION` | `us-west-2` | AWS region |
| `GATEWAY_ARN` | (injected by CFN) | AgentCore Gateway ARN — auto-discovered by Runtime |

## License

MIT
