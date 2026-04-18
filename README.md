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
        SA --> |"Client-Side Mode"| BR[Bedrock Model<br/>Claude Sonnet]
        SA --> |"Server-Side Mode"| RA[Responses API<br/>toolExecution: enabled]
        RA --> BR
    end

    subgraph "AgentCore Gateway"
        BR --> |tool calls| GW[Gateway MCP Endpoint<br/>Tool Discovery + Execution]
        GW --> |"search_products<br/>get_product_details<br/>get_recommendations"| LP[Lambda: Products]
        GW --> |"add_to_cart<br/>view_cart<br/>remove_from_cart<br/>apply_coupon"| LC[Lambda: Cart]
        GW --> |"checkout<br/>get_order_status<br/>list_orders<br/>request_return"| LO[Lambda: Orders]
    end

    subgraph "Data Layer"
        LP --> DB[(DynamoDB<br/>Products)]
        LC --> DB2[(DynamoDB<br/>Carts)]
        LO --> DB3[(DynamoDB<br/>Orders)]
    end

    style GW fill:#ff9900,color:#000
    style BR fill:#8b5cf6,color:#fff
    style SA fill:#06b6d4,color:#fff
```

## Two Execution Modes

### Mode 1: Client-Side (Strands Agent + MCP Client → Gateway)

```
Customer → Strands Agent → Bedrock Model → returns tool_use
                ↓ (client executes)
           MCP Client → AgentCore Gateway → Lambda
                ↓ (sends result back)
           Strands Agent → Bedrock Model → final response
```

The agent orchestrates the tool execution loop client-side.

### Mode 2: Server-Side (Bedrock Responses API — Single Call)

```
Customer → Responses API (with Gateway ARN) → Bedrock Model
                    ↓ (server executes tools automatically)
              AgentCore Gateway → Lambda → result injected
                    ↓
              Final response returned in one API call
```

No client-side orchestration. Bedrock handles tool discovery, selection, execution, and result injection.

## Quick Start (Local Mode)

No AWS deployment needed — uses in-memory mock data with 50+ products.

```bash
# 1. Clone the repo
git clone https://github.com/ddynwzh1992/ecommerce-agent-demo.git
cd ecommerce-agent-demo

# 2. Install dependencies
pip install strands-agents boto3

# 3. Configure AWS credentials (for Bedrock model access)
aws configure  # Need access to Claude Sonnet in us-west-2

# 4. Run the demo
python demo/run_demo.py
```

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

## AWS Deployment (Gateway Mode)

### Prerequisites

- AWS Account with Bedrock model access (Claude Sonnet)
- Node.js 18+ (for AgentCore CLI)
- Python 3.12+
- AWS SAM CLI

### Step 1: Deploy Infrastructure

```bash
# Deploy Lambda + DynamoDB
cd infrastructure
sam build
sam deploy --guided
```

### Step 2: Create AgentCore Gateway

```bash
# Install AgentCore CLI
npm install -g @aws/agentcore

# Create gateway
agentcore create --name ShopAssist --defaults
agentcore add gateway --name ShopAssistGateway --authorizer-type NONE

# Add Lambda targets
agentcore add gateway-target --name Products \
  --type lambda-function-arn \
  --lambda-arn <PRODUCTS_FUNCTION_ARN> \
  --tool-schema-file tools/tool_schemas.json \
  --gateway ShopAssistGateway

# Deploy
agentcore deploy
```

### Step 3: Run in Gateway Mode

```bash
# Client-side execution
python -m agent.gateway_agent https://<gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp

# Server-side execution
python -m agent.serverside_agent arn:aws:bedrock-agentcore:<region>:<account>:gateway/<gateway-id>
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
│   ├── gateway_agent.py              # Gateway mode: MCP Client → AgentCore Gateway
│   └── serverside_agent.py           # Server-side mode: Responses API
├── demo/
│   └── run_demo.py                    # Interactive CLI demo
├── lambda/
│   ├── products/handler.py            # Product search, details, recommendations
│   ├── cart/handler.py                # Cart operations
│   └── orders/handler.py             # Order management
├── infrastructure/
│   └── template.yaml                  # AWS SAM template (DynamoDB + Lambda)
├── tools/
│   └── tool_schemas.json             # MCP tool schemas for Gateway
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

### Strands Agents SDK
- `@tool` decorator converts any Python function into an agent tool
- Docstrings automatically become LLM-facing tool descriptions
- `Agent()` class handles the full agent loop (model → tool → model)
- `BedrockModel` for Amazon Bedrock integration

### Bedrock Server-Side Tool Execution
- `create_response()` with `toolExecution={"enabled": True}`
- `mcpServerConnector` tool type with Gateway ARN
- Single API call — no client-side orchestration loop
- Automatic tool discovery, selection, execution, and result injection

### AgentCore Gateway
- Converts Lambda functions into MCP-compatible tools
- Single managed endpoint for all tools
- Built-in auth (IAM, OAuth, JWT)
- Semantic tool search for large tool collections
- Works with any agent framework (Strands, LangGraph, CrewAI)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-20250514-v1:0` | Bedrock model to use |
| `AWS_REGION` | `us-west-2` | AWS region |
| `GATEWAY_URL` | — | AgentCore Gateway MCP endpoint URL |
| `GATEWAY_ARN` | — | AgentCore Gateway ARN (for server-side mode) |

## License

MIT
