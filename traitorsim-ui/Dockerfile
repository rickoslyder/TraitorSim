# TraitorSim UI - Production Multi-Stage Build
# Combines React frontend + FastAPI backend in single container

# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies first (better caching)
COPY frontend/package.json ./
RUN npm install --silent

# Copy source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + nginx
FROM python:3.11-slim

# Install nginx and supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist /var/www/html

# Create data directory
RUN mkdir -p /app/data

# Nginx config - serve frontend + proxy API
RUN cat > /etc/nginx/sites-available/default << 'EOF'
server {
    listen 80;
    server_name _;

    root /var/www/html;
    index index.html;

    # Frontend routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy to FastAPI (including WebSocket support)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
EOF

# Supervisor config to run both nginx and uvicorn
RUN cat > /etc/supervisor/conf.d/traitorsim.conf << 'EOF'
[supervisord]
nodaemon=true
user=root

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:uvicorn]
command=uvicorn app.main:app --host 127.0.0.1 --port 8000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

# Expose port 80 (nginx)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Run supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
