# Containerfile — e-commerce multi-agent system
# Build:  podman build -t shopbot .
# Run:    podman run --env-file .env -p 8001:8001 shopbot

FROM python:3.12-slim

# System deps (sqlite is needed by langgraph-checkpoint-sqlite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . .

EXPOSE 8001

CMD ["chainlit", "run", "chainlit_app.py", "--port", "8001", "--host", "0.0.0.0"]