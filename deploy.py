#!/usr/bin/env python3
"""Deploy ShopAssist agent to AgentCore Runtime.

Prerequisites:
  - pip install bedrock-agentcore-starter-toolkit==0.2.1
  - CloudFormation stack 'shopassist-demo' deployed (Gateway + Lambdas + DynamoDB)
  - AWS CLI configured with appropriate permissions

Usage:
  python deploy.py
"""

import json
import os
import shutil
import tempfile
import zipfile

import boto3


REGION = os.environ.get("AWS_REGION", "us-west-2")
STACK_NAME = os.environ.get("STACK_NAME", "shopassist-demo")
AGENT_NAME = os.environ.get("AGENT_NAME", "ShopAssistDemo")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "openai.gpt-oss-120b")


def get_stack_outputs(stack_name: str) -> dict:
    """Get CloudFormation stack outputs."""
    cfn = boto3.client("cloudformation", region_name=REGION)
    resp = cfn.describe_stacks(StackName=stack_name)
    outputs = resp["Stacks"][0].get("Outputs", [])
    return {o["OutputKey"]: o["OutputValue"] for o in outputs}


def inject_sdk_into_zip(zip_path: str) -> str:
    """Inject bedrock_agentcore SDK into deployment zip if missing.

    The toolkit's cross-compile mode (--only-binary :all:) skips pure-Python
    packages like bedrock-agentcore. This function patches the zip.
    """
    with zipfile.ZipFile(zip_path) as z:
        if any("bedrock_agentcore/" in n for n in z.namelist()):
            print("  ✓ bedrock_agentcore already in package")
            return zip_path

    print("  ⚠ bedrock_agentcore missing — injecting...")

    # Find local install
    import bedrock_agentcore
    sdk_dir = os.path.dirname(bedrock_agentcore.__file__)
    dist_info = sdk_dir.replace("bedrock_agentcore", f"bedrock_agentcore-{bedrock_agentcore.__version__}.dist-info")

    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmpdir)

    shutil.copytree(sdk_dir, os.path.join(tmpdir, "bedrock_agentcore"))
    if os.path.isdir(dist_info):
        shutil.copytree(dist_info, os.path.join(tmpdir, os.path.basename(dist_info)))

    fixed = zip_path.replace(".zip", "-fixed.zip")
    with zipfile.ZipFile(fixed, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(tmpdir):
            for fn in files:
                full = os.path.join(root, fn)
                zf.write(full, os.path.relpath(full, tmpdir))

    shutil.rmtree(tmpdir)
    shutil.move(fixed, zip_path)
    print(f"  ✓ Injected bedrock_agentcore into {zip_path}")
    return zip_path


def main():
    print(f"🛍️  Deploying ShopAssist to AgentCore Runtime")
    print(f"   Region: {REGION}")
    print(f"   Stack:  {STACK_NAME}")
    print()

    # 1. Get Gateway ARN from CFN outputs
    print("1️⃣  Getting Gateway ARN from CloudFormation...")
    try:
        outputs = get_stack_outputs(STACK_NAME)
        gateway_arn = outputs.get("GatewayArn", "")
        print(f"   Gateway: {gateway_arn}")
    except Exception as e:
        print(f"   ⚠ Could not read stack outputs: {e}")
        gateway_arn = input("   Enter Gateway ARN manually: ").strip()

    # 2. Deploy with toolkit
    print("\n2️⃣  Deploying agent code...")
    from bedrock_agentcore_starter_toolkit import Runtime

    runtime = Runtime()
    runtime.configure(
        entrypoint="agent/shopassist_runtime.py",
        auto_create_execution_role=True,
        auto_create_s3=True,
        requirements_file="requirements-runtime.txt",
        region=REGION,
        agent_name=AGENT_NAME,
        deployment_type="direct_code_deploy",
        runtime_type="PYTHON_3_12",
        memory_mode="NO_MEMORY",
        non_interactive=True,
    )
    result = runtime.launch()
    runtime_arn = result.agent_arn
    runtime_id = runtime_arn.split("/")[-1]
    print(f"   Runtime: {runtime_arn}")

    # 3. Inject SDK if needed
    print("\n3️⃣  Checking deployment package...")
    s3 = boto3.client("s3", region_name=REGION)
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    bucket = f"bedrock-agentcore-codebuild-sources-{account_id}-{REGION}"
    key = f"{AGENT_NAME}/deployment.zip"
    local_zip = "/tmp/shopassist-deploy.zip"

    s3.download_file(bucket, key, local_zip)
    inject_sdk_into_zip(local_zip)
    s3.upload_file(local_zip, bucket, key)
    os.remove(local_zip)

    # 4. Set environment variables
    print("\n4️⃣  Configuring environment variables...")
    ctrl = boto3.client("bedrock-agentcore-control", region_name=REGION)
    current = ctrl.get_agent_runtime(agentRuntimeId=runtime_id)

    ctrl.update_agent_runtime(
        agentRuntimeId=runtime_id,
        agentRuntimeArtifact=current["agentRuntimeArtifact"],
        roleArn=current["roleArn"],
        networkConfiguration=current["networkConfiguration"],
        environmentVariables={
            "AWS_REGION": REGION,
            "GATEWAY_ARN": gateway_arn,
            "BEDROCK_MODEL_ID": MODEL_ID,
        },
    )

    import time
    for _ in range(20):
        time.sleep(3)
        status = ctrl.get_agent_runtime(agentRuntimeId=runtime_id)["status"]
        if status == "READY":
            break
    print(f"   Status: {status}")

    # 5. Remind about IAM
    print(f"\n5️⃣  IAM Setup")
    role_name = current["roleArn"].split("/")[-1]
    print(f"   ⚠ Attach AmazonBedrockMantleFullAccess to: {role_name}")
    print(f"   Run:")
    print(f"   aws iam attach-role-policy \\")
    print(f"     --role-name {role_name} \\")
    print(f"     --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleFullAccess")

    # 6. Test
    print(f"\n6️⃣  Testing...")
    time.sleep(5)
    rt = boto3.client("bedrock-agentcore", region_name=REGION)
    try:
        resp = rt.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=json.dumps({"query": "Hello, what can you help me with?"}).encode(),
        )
        data = resp["response"].read().decode()
        for line in data.strip().split("\n"):
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event.get("type") == "text":
                    print(f"   🤖 {event['content'][:200]}")
        print("\n✅ Deployment complete!")
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        print(f"   Make sure AmazonBedrockMantleFullAccess is attached.")

    print(f"\n📋 Summary:")
    print(f"   Runtime ARN: {runtime_arn}")
    print(f"   Gateway ARN: {gateway_arn}")
    print(f"   Model:       {MODEL_ID}")


if __name__ == "__main__":
    main()
