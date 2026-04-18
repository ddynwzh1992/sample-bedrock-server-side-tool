FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir bedrock-agentcore

# Copy agent code
COPY agent/ ./agent/

# AgentCore Runtime expects the app on port 8080
EXPOSE 8080

# Entry point for AgentCore Runtime
CMD ["python", "-m", "agent.runtime_agent"]
