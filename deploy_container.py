#!/usr/bin/env python3
"""Deploy ShopAssist to AgentCore Runtime using container-based deployment.

This avoids the toolkit cross-compile bug by building a Docker image
with all dependencies pre-installed.

Prerequisites:
  - Docker installed and running
  - AWS CLI configured with permissions for ECR + AgentCore
  - CloudFormation stack deployed (gateway + lambdas + dynamodb)

Usage:
  python deploy_container.py
"""

import os
import json
import subprocess
import sys
import time

import boto3

# Configuration
REGION = "us-west-2"
STACK_NAME = "shopassist-demo"
AGENT_NAME = "ShopAssistDemo"
MODEL_ID = "openai.gpt-oss-120b"
REPO_NAME = "shopassist-demo"


def run(cmd, check=True, capture=False):
    """Run shell command."""
    print(f"   $ {cmd}")
    result = subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)
    return result.stdout.strip() if capture else None


def main():
    print("🛒 ShopAssist — Container-Based Deploy\n")

    # 1. Get Gateway ARN from CloudFormation
    print("1️⃣  Reading CloudFormation outputs...")
    cfn = boto3.client("cloudformation", region_name=REGION)
    try:
        resp = cfn.describe_stacks(StackName=STACK_NAME)
        outputs = {o["OutputKey"]: o["OutputValue"] for o in resp["Stacks"][0].get("Outputs", [])}
        gateway_arn = outputs.get("GatewayArn", "")
        print(f"   Gateway: {gateway_arn}")
    except Exception as e:
        print(f"   ⚠ Could not read stack outputs: {e}")
        gateway_arn = input("   Enter Gateway ARN manually: ").strip()

    # 2. Build & push Docker image to ECR
    print("\n2️⃣  Building & pushing Docker image...")
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    ecr_uri = f"{account_id}.dkr.ecr.{REGION}.amazonaws.com/{REPO_NAME}"

    # Create ECR repo if not exists
    ecr = boto3.client("ecr", region_name=REGION)
    try:
        ecr.create_repository(repositoryName=REPO_NAME)
        print(f"   Created ECR repo: {REPO_NAME}")
    except ecr.exceptions.RepositoryAlreadyExistsException:
        print(f"   ECR repo exists: {REPO_NAME}")

    # Login to ECR
    run(f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{REGION}.amazonaws.com")

    # Build & push
    run(f"docker build -t {REPO_NAME}:latest .")
    run(f"docker tag {REPO_NAME}:latest {ecr_uri}:latest")
    run(f"docker push {ecr_uri}:latest")
    image_uri = f"{ecr_uri}:latest"
    print(f"   Image: {image_uri}")

    # 3. Create/Update AgentCore Runtime with container config
    print("\n3️⃣  Deploying to AgentCore Runtime...")
    ctrl = boto3.client("bedrock-agentcore-control", region_name=REGION)

    # Check if runtime exists
    runtime_id = None
    try:
        runtimes = ctrl.list_agent_runtimes()
        for rt in runtimes.get("agentRuntimes", []):
            if AGENT_NAME in rt.get("agentRuntimeName", ""):
                runtime_id = rt["agentRuntimeId"]
                print(f"   Found existing runtime: {runtime_id}")
                break
    except Exception:
        pass

    # Get or create execution role
    iam = boto3.client("iam")
    role_name = f"{STACK_NAME}-ContainerRuntimeRole"
    role_arn = None

    try:
        role = iam.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]
        print(f"   Role exists: {role_arn}")
    except iam.exceptions.NoSuchEntityException:
        print(f"   Creating execution role: {role_name}")
        trust_policy = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        })
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=trust_policy,
            Description="ShopAssist AgentCore Runtime execution role"
        )
        role_arn = role["Role"]["Arn"]

        # Attach policies
        policies = [
            "arn:aws:iam::aws:policy/AmazonBedrockMantleFullAccess",
            "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
        ]
        for p in policies:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=p)

        # Inline policy for Gateway + ECR
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="AgentCoreAccess",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["bedrock-agentcore:*"],
                        "Resource": "*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchGetImage",
                            "ecr:GetAuthorizationToken"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["logs:*"],
                        "Resource": "*"
                    }
                ]
            })
        )
        print(f"   ✓ Created role: {role_arn}")
        print("   Waiting 10s for IAM propagation...")
        time.sleep(10)

    # Create or update runtime
    runtime_config = {
        "agentRuntimeName": AGENT_NAME,
        "roleArn": role_arn,
        "networkConfiguration": {"networkMode": "PUBLIC"},
        "protocolConfiguration": {"protocolType": "HTTP"},
        "environmentVariables": {
            "AWS_REGION": REGION,
            "GATEWAY_ARN": gateway_arn,
            "BEDROCK_MODEL_ID": MODEL_ID,
        },
        "agentRuntimeArtifact": {
            "containerConfiguration": {
                "containerUri": image_uri,
            }
        },
    }

    if runtime_id:
        # Delete existing and recreate with container config
        print(f"   Deleting old runtime: {runtime_id}")
        try:
            ctrl.delete_agent_runtime(agentRuntimeId=runtime_id)
            time.sleep(10)
        except Exception:
            pass
        runtime_id = None

    # Always create fresh
    result = ctrl.create_agent_runtime(**runtime_config)
    runtime_id = result["agentRuntimeId"]
    print(f"   Created runtime: {runtime_id}")

    runtime_arn = f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:runtime/{runtime_id}"

    # 4. Wait for READY
    print("\n4️⃣  Waiting for Runtime to become READY...")
    for i in range(40):
        time.sleep(5)
        status = ctrl.get_agent_runtime(agentRuntimeId=runtime_id)["status"]
        if status == "READY":
            break
        if i % 4 == 0:
            print(f"   [{i*5}s] {status}")
    print(f"   Status: {status}")

    if status != "READY":
        print(f"\n❌ Runtime did not reach READY state. Check CloudWatch logs.")
        sys.exit(1)

    # 5. Test
    print(f"\n5️⃣  Testing...")
    time.sleep(5)
    rt = boto3.client("bedrock-agentcore", region_name=REGION)
    for attempt in range(3):
        try:
            if attempt > 0:
                print(f"   Retry {attempt}/2 in 15s...")
                time.sleep(15)
            resp = rt.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                payload=json.dumps({"query": "Show me headphones under $100"}).encode(),
            )
            data = resp["response"].read().decode()
            for line in data.strip().split("\n"):
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if event.get("type") == "text":
                        print(f"   🤖 {event['content'][:200]}")
            print("\n✅ Deployment complete!")
            break
        except Exception as e:
            print(f"   ❌ Attempt {attempt+1}: {e}")

    print(f"\n📋 Summary:")
    print(f"   Runtime ARN: {runtime_arn}")
    print(f"   Runtime ID:  {runtime_id}")
    print(f"   Image:       {image_uri}")
    print(f"   Gateway ARN: {gateway_arn}")
    print(f"   Model:       {MODEL_ID}")


if __name__ == "__main__":
    main()
