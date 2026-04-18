# E-Commerce Agent Demo: Design Spec

## Overview
Build an e-commerce shopping assistant that demonstrates:
1. **Strands Agents SDK** — agent framework with custom tools
2. **Bedrock Server-Side Tool Execution** — via Responses API with AgentCore Gateway
3. **Amazon Bedrock AgentCore** — Gateway for tool hosting, Runtime for deployment

## Scenario: "ShopAssist" — AI-Powered E-Commerce Agent

An intelligent shopping assistant that helps customers:
- Browse and search products
- Get personalized recommendations
- Manage shopping cart
- Check order status
- Process returns/refunds
- Answer product questions

## Architecture

```
Customer (CLI/API) 
    → Strands Agent (with system prompt + tools)
        → Bedrock Model (Claude Sonnet)
            → AgentCore Gateway (MCP endpoint)
                → Lambda Functions (e-commerce tools)
                    → DynamoDB (products, orders, carts)
```

Two modes of operation:
1. **Client-side tool execution** (Strands Agent + MCP Client → Gateway)
2. **Server-side tool execution** (Bedrock Responses API → Gateway, single API call)

## Tools (Lambda Functions)

### Product Tools
- `search_products(query, category?, price_range?)` — Search product catalog
- `get_product_details(product_id)` — Get detailed product info
- `get_recommendations(customer_id?, category?)` — Personalized recommendations

### Cart Tools
- `add_to_cart(customer_id, product_id, quantity)` — Add item to cart
- `view_cart(customer_id)` — View cart contents
- `remove_from_cart(customer_id, product_id)` — Remove item from cart
- `apply_coupon(customer_id, coupon_code)` — Apply discount coupon

### Order Tools
- `checkout(customer_id, payment_method)` — Place order
- `get_order_status(order_id)` — Check order status
- `list_orders(customer_id)` — List customer orders
- `request_return(order_id, reason)` — Request return/refund

## Project Structure
```
ecommerce-agent-demo/
├── README.md
├── requirements.txt
├── agentcore.config.json          # AgentCore CLI config
├── infrastructure/
│   ├── template.yaml              # SAM/CDK template
│   └── seed_data.py               # Seed DynamoDB with sample products
├── lambda/
│   ├── products/
│   │   └── handler.py             # Product search, details, recommendations
│   ├── cart/
│   │   └── handler.py             # Cart operations
│   └── orders/
│       └── handler.py             # Order management
├── tools/
│   └── tool_schemas.json          # Tool schemas for Gateway
├── agent/
│   ├── client_side_agent.py       # Strands Agent with MCP Client → Gateway
│   ├── server_side_agent.py       # Bedrock Responses API with server-side execution
│   └── system_prompt.py           # Agent system prompt
├── demo/
│   ├── run_demo.py                # Interactive demo script
│   └── sample_conversations.md    # Example conversations
└── docs/
    ├── architecture.md            # Architecture diagram (Mermaid)
    └── setup.md                   # Setup guide
```

## Tech Stack
- Python 3.12
- strands-agents + strands-agents-tools
- boto3 (Bedrock, DynamoDB, Lambda)
- AWS SAM or AgentCore CLI for deployment
- DynamoDB for data storage (or mock in-memory for local demo)

## Key Implementation Notes

### Mode 1: Client-Side (Strands + MCP + Gateway)
```python
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

mcp_client = MCPClient(lambda: streamablehttp_client(gateway_url))
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(
        model=BedrockModel(model_id="openai.gpt-oss-120b"),
        system_prompt=ECOMMERCE_PROMPT,
        tools=tools
    )
    agent("I'm looking for wireless headphones under $100")
```

### Mode 2: Server-Side (Responses API + Gateway)
```python
import boto3
client = boto3.client('bedrock-runtime')
response = client.create_response(
    modelId="openai.gpt-oss-120b",
    input=[{"role": "user", "content": [{"text": "Show me wireless headphones under $100"}]}],
    tools=[{
        "mcpServerConnector": {
            "mcpServerUri": gateway_arn_or_url,
            "name": "ecommerce_tools"
        }
    }],
    toolExecution={"enabled": True}
)
```

### Local Demo Mode (No AWS deployment needed)
For quick testing, include a local mode with mock data (no DynamoDB/Lambda):
- In-memory product catalog (50+ products)
- In-memory cart/order state
- Strands @tool decorated Python functions
- Same system prompt, same agent behavior

## Sample Product Data
- Electronics (headphones, laptops, phones, tablets)
- Home & Kitchen (coffee makers, blenders, air fryers)
- Sports & Outdoors (running shoes, yoga mats, water bottles)
- Books (tech, fiction, business)

~50 products with realistic names, descriptions, prices, ratings, reviews count
