# Setup Guide

## Local Mode (No AWS Deployment)

### Prerequisites
- Python 3.10+
- AWS credentials with Bedrock access (for model inference only)

### Steps

```bash
# 1. Clone
git clone https://github.com/ddynwzh1992/ecommerce-agent-demo.git
cd ecommerce-agent-demo

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install strands-agents boto3

# 4. Configure AWS (need Bedrock access in us-west-2)
aws configure
# Or set: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

# 5. Enable model access
# Go to: https://console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess
# Enable: Anthropic Claude Sonnet 4

# 6. Run
python demo/run_demo.py
```

### Custom Model
```bash
# Use a different model
export BEDROCK_MODEL_ID="us.anthropic.claude-haiku-4-5-20250609-v1:0"
export AWS_REGION="us-west-2"
python demo/run_demo.py
```

---

## AWS Deployment (Gateway Mode)

### Prerequisites
- AWS Account (412381761882 or your account)
- AWS SAM CLI installed
- Node.js 18+ (for AgentCore CLI)
- Python 3.12+
- Bedrock model access enabled

### Step 1: Deploy Lambda + DynamoDB

```bash
cd infrastructure

# Build
sam build

# Deploy (first time — interactive)
sam deploy --guided \
  --stack-name shopassist-demo \
  --capabilities CAPABILITY_IAM

# Note the outputs: ProductsFunctionArn, CartFunctionArn, OrdersFunctionArn
```

### Step 2: Seed Product Data

```bash
cd infrastructure
python seed_data.py
```

### Step 3: Create AgentCore Gateway

```bash
# Install AgentCore CLI
npm install -g @aws/agentcore

# Option A: CLI commands
agentcore create --name ShopAssist --defaults

# Add gateway (no auth for demo)
agentcore add gateway \
  --name ShopAssistGateway \
  --authorizer-type NONE \
  --runtimes ShopAssist

# Add targets (use ARNs from SAM deploy output)
agentcore add gateway-target \
  --name ProductTools \
  --type lambda-function-arn \
  --lambda-arn arn:aws:lambda:us-west-2:ACCOUNT:function:ShopAssist-Products \
  --tool-schema-file ../tools/tool_schemas.json \
  --gateway ShopAssistGateway

agentcore add gateway-target \
  --name CartTools \
  --type lambda-function-arn \
  --lambda-arn arn:aws:lambda:us-west-2:ACCOUNT:function:ShopAssist-Cart \
  --tool-schema-file ../tools/tool_schemas.json \
  --gateway ShopAssistGateway

agentcore add gateway-target \
  --name OrderTools \
  --type lambda-function-arn \
  --lambda-arn arn:aws:lambda:us-west-2:ACCOUNT:function:ShopAssist-Orders \
  --tool-schema-file ../tools/tool_schemas.json \
  --gateway ShopAssistGateway

# Deploy
agentcore deploy

# Get gateway URL
agentcore status
```

### Step 4: Run Agent

```bash
# Client-side execution (Strands + MCP → Gateway)
python -m agent.gateway_agent https://<gateway-id>.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp

# Server-side execution (Responses API)
python -m agent.serverside_agent arn:aws:bedrock-agentcore:us-west-2:<account>:gateway/<gateway-id>
```

---

## Cleanup

```bash
# Remove AgentCore resources
agentcore remove all

# Remove SAM stack
sam delete --stack-name shopassist-demo
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: strands` | `pip install strands-agents` |
| `AccessDeniedException` for Bedrock | Enable model access in Bedrock console |
| Gateway not responding | Wait 30-60s after creation for DNS |
| Lambda timeout | Increase timeout in template.yaml |
| `No module named 'mcp'` | `pip install mcp` (needed for gateway mode) |
