# Containerized Multi-Agent Architecture for TraitorSim

## Design Overview

Each player agent runs in its own Docker container with isolated resources, communicating with the game engine via HTTP/gRPC.

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Game Engine (Host Process)                      │
│  - GameState management                          │
│  - Gemini GM (no containerization needed)        │
│  - HTTP client to agent containers               │
│  - Game loop orchestration                       │
└──────────────┬───────────────────────────────────┘
               │
               │ HTTP/JSON-RPC
               │
    ┌──────────┴────────┬──────────┬──────────┐
    │                   │          │          │
    V                   V          V          V
┌─────────┐      ┌─────────┐  ...  ┌─────────┐
│Agent    │      │Agent    │        │Agent    │
│Container│      │Container│        │Container│
│#1       │      │#2       │        │#10      │
│         │      │         │        │         │
│Flask API│      │Flask API│        │Flask API│
│Port 8001│      │Port 8002│        │Port 8010│
│         │      │         │        │         │
│Claude   │      │Claude   │        │Claude   │
│SDK      │      │SDK      │        │SDK      │
│+ Bun    │      │+ Bun    │        │+ Bun    │
│         │      │         │        │         │
│Memory:  │      │Memory:  │        │Memory:  │
│512MB    │      │512MB    │        │512MB    │
└─────────┘      └─────────┘        └─────────┘
```

## Communication Protocol

### Agent API Endpoints

Each agent container exposes a REST API:

```
POST /vote
  Input: {
    "game_state": {...},
    "player": {...},
    "suspicions": {...}
  }
  Output: {
    "target_player_id": "player_05",
    "reasoning": "..."
  }

POST /choose_murder_victim
  Input: {
    "game_state": {...},
    "player": {...}
  }
  Output: {
    "target_player_id": "player_03",
    "reasoning": "..."
  }

POST /reflect
  Input: {
    "events": ["Player5 was banished", ...],
    "game_state": {...}
  }
  Output: {
    "suspicion_updates": {
      "player_02": 0.8,
      "player_07": 0.3
    }
  }

GET /health
  Output: {"status": "ok"}
```

## Implementation Steps

### Phase 1: Agent Service (Flask API)

Create `src/traitorsim/agents/agent_service.py`:

```python
from flask import Flask, request, jsonify
from player_agent_sdk import PlayerAgentSDK
import asyncio

app = Flask(__name__)

# Initialize agent (loaded from env vars)
agent = None

@app.route('/vote', methods=['POST'])
def vote():
    data = request.json
    # Update agent's game state
    agent.game_state = deserialize_game_state(data['game_state'])

    # Make decision
    target = asyncio.run(agent.cast_vote_async())

    return jsonify({
        'target_player_id': target,
        'reasoning': agent.tool_context.get('vote_result', {}).get('reasoning', '')
    })

@app.route('/choose_murder_victim', methods=['POST'])
def choose_murder():
    data = request.json
    agent.game_state = deserialize_game_state(data['game_state'])

    target = asyncio.run(agent.choose_murder_victim_async())

    return jsonify({
        'target_player_id': target,
        'reasoning': '...'
    })

@app.route('/reflect', methods=['POST'])
def reflect():
    data = request.json
    agent.game_state = deserialize_game_state(data['game_state'])

    asyncio.run(agent.reflect_on_day_async(data['events']))

    return jsonify({'status': 'ok'})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'agent': agent.player.name})

if __name__ == '__main__':
    # Read player config from env
    import os
    player_id = os.environ['PLAYER_ID']

    # Initialize agent
    agent = initialize_agent(player_id)

    # Start server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
```

### Phase 2: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  agent-1:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: traitorsim-agent-1
    environment:
      - PLAYER_ID=player_00
      - PORT=5000
      - CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}
    ports:
      - "8001:5000"
    mem_limit: 512m
    cpus: 0.5
    volumes:
      - ./data/memories/player_00:/app/data/memories/player_00

  agent-2:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: traitorsim-agent-2
    environment:
      - PLAYER_ID=player_01
      - PORT=5000
      - CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}
    ports:
      - "8002:5000"
    mem_limit: 512m
    cpus: 0.5
    volumes:
      - ./data/memories/player_01:/app/data/memories/player_01

  # ... repeat for agents 3-10 ...

  agent-10:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: traitorsim-agent-10
    environment:
      - PLAYER_ID=player_09
      - PORT=5000
      - CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN}
    ports:
      - "8010:5000"
    mem_limit: 512m
    cpus: 0.5
    volumes:
      - ./data/memories/player_09:/app/data/memories/player_09
```

### Phase 3: Game Engine Refactor

Create `src/traitorsim/core/game_engine_containerized.py`:

```python
import httpx
import asyncio

class GameEngineContainerized:
    def __init__(self, config):
        self.config = config
        self.game_state = GameState()
        self.gm = GameMasterInteractions(...)

        # Agent URLs
        self.agent_urls = {
            f"player_{i:02d}": f"http://localhost:{8001+i}"
            for i in range(10)
        }

    async def _collect_votes_parallel_async(self):
        """Vote via HTTP to containerized agents."""

        async def vote_via_http(player_id: str, url: str):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{url}/vote",
                    json={
                        "game_state": serialize_game_state(self.game_state),
                        "player": serialize_player(self.game_state.get_player(player_id))
                    },
                    timeout=60.0
                )
                data = response.json()
                return (player_id, data['target_player_id'])

        # Vote in parallel across containers
        vote_tasks = [
            vote_via_http(pid, url)
            for pid, url in self.agent_urls.items()
            if self.game_state.get_player(pid).alive
        ]

        results = await asyncio.gather(*vote_tasks)
        return {pid: target for pid, target in results}
```

## Resource Limits

Per container:
- **Memory**: 512MB (enough for Bun + Claude SDK)
- **CPU**: 0.5 cores
- **Network**: Bridge network for inter-container communication

Total for 10 agents: **5GB RAM, 5 CPU cores**

## Benefits

1. ✅ **Eliminates resource exhaustion** - Isolated per-agent limits
2. ✅ **No Bun crashes** - Each container has independent Bun runtime
3. ✅ **OAuth token works** - Pass as env var to containers
4. ✅ **True parallelism** - Containers run simultaneously
5. ✅ **Fault tolerance** - Container restart on crash
6. ✅ **Scalability** - Can run 100+ agents with orchestration

## Drawbacks

1. ❌ **Complexity** - More moving parts
2. ❌ **Setup overhead** - Docker Compose, networking
3. ❌ **Latency** - HTTP overhead vs in-process calls (~50ms per request)
4. ❌ **Resource usage** - 5GB RAM vs ~1GB for in-process
5. ❌ **State serialization** - Must serialize/deserialize GameState

## Alternative: Lightweight Containers

Use **Docker Python SDK** to spawn containers dynamically:

```python
import docker

client = docker.from_env()

# Spawn 10 agent containers
containers = []
for i in range(10):
    container = client.containers.run(
        'traitorsim-agent',
        detach=True,
        environment={
            'PLAYER_ID': f'player_{i:02d}',
            'CLAUDE_CODE_OAUTH_TOKEN': os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
        },
        mem_limit='512m',
        ports={5000: 8001+i}
    )
    containers.append(container)

# Use agents, then cleanup
for container in containers:
    container.stop()
    container.remove()
```

## Recommendation

**For MVP/Testing**: Containerization is overkill. Use API key instead (simpler, faster).

**For Production/Research**: Containerization enables:
- 100+ agent simulations
- Agent diversity (different models per container)
- Fault tolerance and monitoring
- Scalable to Kubernetes for large-scale experiments

## Next Steps

If you want to pursue containerization:

1. Create Flask agent service
2. Build Docker image
3. Create docker-compose.yml
4. Refactor game engine to HTTP client
5. Test with 2 agents first
6. Scale to 10 agents

Estimated effort: **4-6 hours**
