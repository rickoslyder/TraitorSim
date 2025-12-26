FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for Claude CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI globally (required by claude-agent-sdk)
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create data directory
RUN mkdir -p data

# Create non-root user for running game simulations
# Claude Agent SDK's bypassPermissions mode requires non-root
RUN useradd -m -s /bin/bash gamerunner && \
    mkdir -p /home/gamerunner/.cache /home/gamerunner/.claude && \
    chown -R gamerunner:gamerunner /home/gamerunner

# Ensure Claude CLI is in PATH for all users
ENV PATH="/usr/local/bin:/usr/bin:${PATH}"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
