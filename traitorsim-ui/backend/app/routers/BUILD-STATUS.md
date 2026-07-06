## Arena Router — Ship Status (2026-07-06)

**Commit:** `79ee955` (main)

### What's live

| Endpoint | Method | Auth | Status |
|----------|--------|------|--------|
| /api/arena/register | POST | None | ✅ |
| /api/arena/games | GET | None | ✅ |
| /api/arena/games | POST | Bearer | ✅ |
| /api/arena/games/ID | GET | None | ✅ |
| /api/arena/games/ID/join | POST | Bearer | ✅ |
| /api/arena/games/ID/leave | POST | Bearer | ✅ |
| /api/arena/protocol | GET | None | ✅ |
| /api/arena/agents | GET | None | ✅ |
| /api/arena/agents/ID | GET | None | ✅ |
| /api/arena/status | GET | None | ✅ |

### Registration
- Health check validates agent's /health before registration
- Skip in dev: set `metadata.skip_health: true`
- Token format: `tsa_` prefix, 32 bytes urlsafe

### Reference agent
- `agent.py` — Flask-based
- `agent_stdlib.py` — Zero-dependency (Python stdlib http.server)
- Both implement full v1.0 protocol

### Projection pipeline (verified)
- Async engine: `events.jsonl` + `world_snapshot.json` per session
- Schema v1: players[].seat_index, alive, role_visible
- Verified: 6-player game → all 8 event types, Faithful win Day 1
- Containerized engine: EventBus patch at `52c8fec`

### Known issues
- Runner fails: missing gamerunner user, missing deps (aiohttp, pydub)
- API keys not passed through su -c

### Next
- Install deps in Docker image, add gamerunner user
- Wire game runner to arena (auto-register agents)
- Run 22-player arena game with reference agents
