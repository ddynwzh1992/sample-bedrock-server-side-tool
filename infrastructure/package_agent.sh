#!/bin/bash
# Package agent code and upload to S3 for AgentCore Runtime deployment
# Usage: ./package_agent.sh <S3_BUCKET> [S3_KEY]

set -e

S3_BUCKET="${1:?Usage: $0 <S3_BUCKET> [S3_KEY]}"
S3_KEY="${2:-shopassist-agent/agent.zip}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📦 Packaging ShopAssist agent..."

# Create temp dir for packaging
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copy agent code
cp -r "$PROJECT_DIR/agent" "$TEMP_DIR/agent"
cp "$PROJECT_DIR/requirements.txt" "$TEMP_DIR/requirements.txt"

# Install dependencies into package
pip install --target "$TEMP_DIR" -r "$TEMP_DIR/requirements.txt" -q

# Create zip
cd "$TEMP_DIR"
zip -r agent.zip . -x "*.pyc" "__pycache__/*" "*.dist-info/*" > /dev/null

echo "✓ Package created: $(du -h agent.zip | cut -f1)"

# Upload to S3
echo "⬆️  Uploading to s3://${S3_BUCKET}/${S3_KEY}..."
aws s3 cp agent.zip "s3://${S3_BUCKET}/${S3_KEY}"

echo "✓ Done! Agent code uploaded to s3://${S3_BUCKET}/${S3_KEY}"
echo ""
echo "Next: Deploy with CloudFormation:"
echo "  aws cloudformation deploy \\"
echo "    --template-file infrastructure/cloudformation-one-click.yaml \\"
echo "    --stack-name shopassist-demo \\"
echo "    --capabilities CAPABILITY_NAMED_IAM \\"
echo "    --parameter-overrides AgentCodeS3Bucket=${S3_BUCKET} AgentCodeS3Key=${S3_KEY}"
