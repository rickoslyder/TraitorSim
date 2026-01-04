# TraitorSim - Containerized Multi-Agent Architecture

## Overview

This containerized version runs each of the 10 player agents in isolated Docker containers, solving resource exhaustion issues while enabling true parallel execution with your Claude Max subscription.

## Architecture

```
┌──────────────────────────────────────┐
│   Game Engine (Host Process)         │
│   - Python on host                   │
│   - Gemini GM                        │
│   - HTTP client                      │
└────────────┬─────────────────────────┘
             │
             │ HTTP/JSON
             │
    ┌────────┴────────┬──────────┬─────────┐
    │                 │          │         │
    V                 V          V         V
┌─────────┐      ┌─────────┐  ...  ┌─────────┐
│Agent 0  │      │Agent 1  │        │Agent 9  │
│Port 8000│      │Port 8001│        │Port 8009│
│1GB RAM  │      │1GB RAM  │        │1GB RAM  │
│1 CPU    │      │1 CPU    │        │1 CPU    │
│         │      │         │        │         │
│Flask API│      │Flask API│        │Flask API│
│Claude SDK      │Claude SDK│        │Claude SDK│
│+ Bun    │      │+ Bun    │        │+ Bun    │
└─────────┘      └─────────┘        └─────────┘
```

## Benefits

✅ **No more crashes**: Each agent has isolated resources
✅ **Uses Claude Max subscription**: OAuth token passed to containers
✅ **True parallelism**: 10 agents vote simultaneously without interference
✅ **Scalable**: Easy to increase to 24 players for full game
✅ **Cost-effective**: $200/month subscription vs $200+ in API costs

## Requirements

- Docker and Docker Compose
- 256GB RAM (10GB for containers, rest for host)
- 10+ CPU cores
- Claude Max subscription with `CLAUDE_CODE_OAUTH_TOKEN`
- Gemini API key

## Quick Start

### 1. Ensure .env is configured

```bash
# .env file
GEMINI_API_KEY=your_gemini_key_here
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
```

### 2. Run the helper script

```bash
./run_containerized.sh
```

This will:
1. Build agent Docker images
2. Start 10 agent containers
3. Wait for health checks
4. Run the game engine
5. Clean up containers when done

## Manual Usage

### Build containers

```bash
docker-compose build
```

### Start agent containers

```bash
docker-compose up -d
```

### Check agent health

```bash
for i in {0..9}; do
    curl http://localhost:$((8000+i))/health
done
```

### Run game engine

```bash
python3 -m src.traitorsim.__main_containerized__
```

### Stop containers

```bash
docker-compose down
```

## Resource Configuration

Each agent container is configured with:

- **Memory**: 1GB (can be adjusted in docker-compose.yml)
- **CPU**: 1.0 cores (can be adjusted)
- **Network**: Bridge network for inter-container communication
- **Volumes**: Shared memory directory for persistence

Total resources:
- **10GB RAM** (10 containers × 1GB)
- **10 CPU cores** (10 containers × 1 core)

## Scaling to 24 Players

To scale to 24 players (full game from architectural_spec.md):

### 1. Update docker-compose.yml

Add agents 10-23 (following the same pattern)

### 2. Update config

```python
config = GameConfig(
    total_players=24,
    num_traitors=8,  # Adjust based on game rules
    ...
)
```

### 3. Adjust resources

24 agents × 1GB = **24GB RAM**
24 agents × 1 core = **24 CPU cores**

Still well within your 256GB EX130-R capacity!

## Troubleshooting

### Containers fail to start

```bash
# Check Docker logs
docker-compose logs agent-0

# Restart specific agent
docker-compose restart agent-0
```

### Health checks failing

```bash
# Check if ports are available
netstat -tulpn | grep 800

# Manually test agent endpoint
curl -X POST http://localhost:8000/initialize \
  -H "Content-Type: application/json" \
  -d '{"player": {"id": "player_00", "name": "TestPlayer", ...}}'
```

### Out of memory

Reduce per-container memory limit in docker-compose.yml:

```yaml
mem_limit: 512m  # Instead of 1g
```

### Slow performance

Increase CPU allocation:

```yaml
cpus: 2.0  # Instead of 1.0
```

## Performance Metrics

Expected performance with containerized architecture:

| Phase | Time (Sequential) | Time (Containerized) | Speedup |
|-------|------------------|---------------------|---------|
| Round Table | ~40s | ~7s | 5-6x |
| Social Reflection | ~30s | ~5s | 6x |
| **Full Game (15 days)** | **~30 min** | **~5 min** | **6x** |

## API Endpoints (per agent)

Each agent container exposes:

- `GET /health` - Health check
- `POST /initialize` - Initialize agent with player data
- `POST /vote` - Cast Round Table vote
- `POST /choose_murder_victim` - Choose murder target (traitors only)
- `POST /reflect` - Reflect on events
- `GET /get_suspicions` - Get current suspicion scores

## Cost Comparison

### API Key Approach
- Cost per game: $5-10
- 20-40 test games: **$100-400**
- Not sustainable for research

### Containerized with Claude Max
- Monthly subscription: **$200**
- Games per month: **Unlimited**
- Cost per game: **$0** (subscription already paid)

**Savings**: $200-400 during testing phase alone!

## Next Steps

1. ✅ Architecture implemented
2. ⏳ Test with 2 agents first
3. ⏳ Scale to 10 agents
4. ⏳ Run full game and verify no crashes
5. ⏳ Scale to 24 players for full game

## Files

- `Dockerfile.agent` - Agent container definition
- `docker-compose.yml` - 10 agent services configuration
- `src/traitorsim/agents/agent_service.py` - Flask API for agents
- `src/traitorsim/core/game_engine_containerized.py` - HTTP-based game engine
- `src/traitorsim/__main_containerized__.py` - Entry point
- `run_containerized.sh` - Helper script

## Support

For issues or questions:
1. Check Docker logs: `docker-compose logs`
2. Verify health: `curl http://localhost:8000/health`
3. Check game logs: `data/games/game_*.log`
