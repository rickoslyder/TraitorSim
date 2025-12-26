# Docker Game Runner - Architecture & Lessons Learned

This document captures the architecture decisions and hard-won lessons from implementing the Game Runner feature in the TraitorSim UI Docker deployment.

## Overview

The Game Runner allows users to start TraitorSim game simulations directly from the web UI. Games run in the backend Docker container and stream logs via WebSocket to the frontend in real-time.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Host                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  traitorsim-ui-backend (Python/FastAPI)                 │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  runner.py                                      │    │    │
│  │  │  ├── POST /run - Start game                     │    │    │
│  │  │  ├── GET /run/status - Poll status              │    │    │
│  │  │  ├── POST /run/stop - Stop game                 │    │    │
│  │  │  └── WS /run/ws - Stream logs                   │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │                         │                                │    │
│  │                         ▼                                │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  subprocess (as gamerunner user)                │    │    │
│  │  │  └── python3 -m src.traitorsim                  │    │    │
│  │  │      ├── Game Engine (orchestration)            │    │    │
│  │  │      ├── Gemini GM (narratives)                 │    │    │
│  │  │      └── Claude Agents (player decisions)       │    │    │
│  │  │          └── claude-agent-sdk                   │    │    │
│  │  │              └── spawns: claude CLI             │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Mounted Volumes:                                                │
│  ├── ../reports:/app/reports (game output)                      │
│  └── ../:/app/traitorsim (game engine source)                   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Dependencies

### Claude Agent SDK Architecture

The `claude-agent-sdk` Python package is **not a standalone library** - it's a thin wrapper that spawns the Claude CLI as a subprocess:

```
Python App
    └── claude-agent-sdk (pip package)
            └── spawns subprocess: claude (npm package @anthropic-ai/claude-code)
                    └── connects to: Claude API
```

**Implication**: You must install BOTH:
1. `pip install claude-agent-sdk` (Python wrapper)
2. `npm install -g @anthropic-ai/claude-code` (actual CLI)

### Gemini API for Game Master

The Game Master uses Gemini's Interactions API for narrative generation. When uploading files (like the World Bible), you must specify `mime_type` explicitly:

```python
# Wrong - causes "Unknown mime type" warning
self.client.files.upload(file=path)

# Correct
self.client.files.upload(
    file=path,
    config={"mime_type": "text/markdown"}
)
```

## Critical Lessons Learned

### 1. Claude SDK Cannot Run as Root

The Claude Agent SDK's `bypassPermissions` mode has a security constraint that prevents execution as root/sudo:

```
Error: --dangerously-skip-permissions cannot be used with root/sudo privileges
```

**Solution**: Create a non-root user in the Dockerfile:

```dockerfile
# Create non-root user for game simulations
RUN useradd -m -s /bin/bash gamerunner && \
    mkdir -p /home/gamerunner/.cache /home/gamerunner/.claude && \
    chown -R gamerunner:gamerunner /home/gamerunner
```

Then run the game subprocess as that user:

```python
game_cmd = f"cd {project_root} && {env_str} python3 -m src.traitorsim"
cmd = ["su", "-c", game_cmd, "gamerunner"]
```

### 2. Environment Variables Must Be Explicitly Passed

When using `su -c`, environment variables from the parent process are NOT inherited. You must build an environment string:

```python
env_vars = []
for key in ["GEMINI_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"]:
    if os.environ.get(key):
        env_vars.append(f'{key}="{os.environ[key]}"')

# Critical paths for Claude CLI
env_vars.extend([
    'PATH="/usr/local/bin:/usr/bin:/bin"',
    'HOME="/home/gamerunner"',
    f'PYTHONPATH="{project_root}"',
    'PYTHONUNBUFFERED=1',
])
env_str = " ".join(env_vars)
```

### 3. Volume Mount Permissions

When running as a non-root user inside Docker, mounted volumes from the host may not be readable:

```
PermissionError: [Errno 13] Permission denied: '/app/traitorsim/src/...'
```

**Solution**: Make host files world-readable:

```bash
chmod -R o+rX /path/to/TraitorSim/src
chmod -R o+rX /path/to/TraitorSim/data
```

### 4. Node.js Required in Python Container

Since `claude-agent-sdk` spawns the Claude CLI, Node.js must be installed in a Python container:

```dockerfile
# Install Node.js for Claude CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] \
       https://deb.nodesource.com/node_20.x nodistro main" \
       | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs

# Install Claude CLI globally
RUN npm install -g @anthropic-ai/claude-code
```

### 5. Docker Compose Environment Files

Docker Compose warns about undefined variables during build. Use a symlink to the parent `.env`:

```bash
# In traitorsim-ui/
ln -sf ../.env .env
```

This allows `docker compose` to automatically load environment variables.

Also add defaults in `docker-compose.prod.yml` as a safety net:

```yaml
environment:
  - GEMINI_API_KEY=${GEMINI_API_KEY:-}
  - CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN:-}
```

## Debugging Checklist

When the Game Runner fails, check these in order:

1. **Is Claude CLI installed?**
   ```bash
   docker exec traitorsim-ui-backend-1 which claude
   docker exec traitorsim-ui-backend-1 claude --version
   ```

2. **Can gamerunner access the CLI?**
   ```bash
   docker exec traitorsim-ui-backend-1 su -c "claude --version" gamerunner
   ```

3. **Are environment variables set?**
   ```bash
   docker exec traitorsim-ui-backend-1 env | grep -E "(GEMINI|CLAUDE|ANTHROPIC)"
   ```

4. **Are mounted files readable?**
   ```bash
   docker exec traitorsim-ui-backend-1 su -c "ls -la /app/traitorsim/src" gamerunner
   ```

5. **Check subprocess output:**
   ```bash
   docker compose -f docker-compose.prod.yml logs backend --tail 100
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/games/run` | POST | Start a new game. Body: `{"num_players": 22, "num_traitors": 3, "rule_variant": "uk"}` |
| `/api/games/run/status` | GET | Get current game status (day, phase, alive players, etc.) |
| `/api/games/run/stop` | POST | Stop a running game |
| `/api/games/run/ws` | WebSocket | Real-time log streaming |

## WebSocket Message Types

```typescript
// Status update
{ type: "status", data: { id, status, current_day, current_phase, ... } }

// Log line
{ type: "log", data: { line: "..." } }

// Game complete
{ type: "complete", data: { winner, prize_pot, ... } }

// Heartbeat (every 30s)
{ type: "heartbeat" }
```

## Performance Notes

- A 6-player game completes in ~4 minutes
- A full 22-player game takes 15-30 minutes depending on API latency
- Log output is ~1000+ lines per game
- WebSocket streams logs in real-time with 100-line backfill on connect

## Related Files

- `traitorsim-ui/backend/Dockerfile` - Container setup with Node.js/Claude CLI
- `traitorsim-ui/backend/app/routers/runner.py` - Game runner API endpoints
- `traitorsim-ui/docker-compose.prod.yml` - Production deployment config
- `src/traitorsim/agents/game_master_interactions.py` - Gemini GM with Interactions API
