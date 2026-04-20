FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements-container.txt .
RUN pip install --no-cache-dir -r requirements-container.txt

# Copy agent code
COPY agent/ ./agent/

# AgentCore Runtime entrypoint with OpenTelemetry instrumentation for CloudWatch observability
CMD ["opentelemetry-instrument", "python", "agent/shopassist_runtime.py"]
