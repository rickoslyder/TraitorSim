# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TraitorSim is a high-fidelity AI simulator for the reality TV show "The Traitors" - a social deduction game combining elements of Werewolf/Mafia with economic strategy and psychological manipulation. The system uses advanced multi-agent AI to simulate an entire season with distinct AI personalities exhibiting genuine social dynamics including deception, paranoia, alliance-building, and betrayal.

## Live Deployment

**Production URL:** https://traitorsim.rbnk.uk (port 8085 on server)

### Deployment Commands

```bash
# Deploy UI changes to production
cd /home/rkb/projects/TraitorSim/traitorsim-ui
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check container status
docker ps --filter "name=traitorsim-ui"

# View logs
docker logs traitorsim-ui-frontend-1
docker logs traitorsim-ui-backend-1

# Restart services
docker compose -f docker-compose.prod.yml restart
```

### Deployment Architecture

```
Internet → traitorsim.rbnk.uk → Nginx (port 8085)
                                   ├── /api/* → backend:8000 (FastAPI)
                                   └── /* → static React build
```

## Project Structure

```
/home/rkb/projects/TraitorSim/
├── src/traitorsim/                 # Core game engine
│   ├── core/                       # Game state management
│   │   ├── game_engine_containerized.py  # Main engine (HTTP to containers)
│   │   ├── game_engine_async.py    # Async parallel execution
│   │   ├── game_state.py           # GameState, Player, TrustMatrix
│   │   ├── config.py               # GameConfig (difficulty=0.3)
│   │   └── archetypes.py           # OCEAN personality traits
│   ├── agents/                     # AI decision-making
│   │   ├── game_master_interactions.py   # Gemini Interactions API
│   │   ├── player_agent_sdk.py     # Claude Agent SDK players
│   │   └── agent_service.py        # Flask API for containerized agents
│   ├── mcp/                        # Model Context Protocol tools
│   ├── missions/                   # Game challenges
│   │   └── skill_check.py          # Spectrum scoring (not binary)
│   └── voice/                      # Voice integration (ElevenLabs/Deepgram)
│
├── traitorsim-ui/                  # Web Dashboard (React + FastAPI)
│   ├── frontend/                   # React + TypeScript + Vite
│   │   ├── src/
│   │   │   ├── components/         # UI components
│   │   │   ├── stores/gameStore.ts # Zustand state management
│   │   │   ├── hooks/              # Custom React hooks
│   │   │   ├── types/game.ts       # TypeScript interfaces
│   │   │   └── api/client.ts       # API client (relative URLs)
│   │   ├── Dockerfile.prod         # Production: Node build → Nginx
│   │   └── nginx.conf              # Reverse proxy config
│   ├── backend/                    # FastAPI server
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI app + CORS
│   │   │   ├── db/database.py      # SQLite + auto-sync from reports
│   │   │   └── routers/            # games.py, analysis.py, runner.py
│   │   └── Dockerfile
│   ├── docker-compose.yml          # Development (hot reload)
│   └── docker-compose.prod.yml     # Production (port 8085)
│
├── docs/                           # Technical documentation
│   ├── DEVOPS_LESSONS.md           # Infrastructure debugging insights
│   ├── CONTAINERIZATION_DESIGN.md  # Docker architecture
│   ├── VOICE_INTEGRATION_DESIGN.md # Voice/audio system design
│   └── architectural_spec.md       # Original design spec
│
├── data/
│   ├── memories/                   # Agent memory files (runtime)
│   └── personas/                   # Character templates (100+ personas)
│       └── library/                # Generated personas with backstories
│
├── reports/                        # Game JSON exports (mounted to UI)
├── research/                       # Training data analysis (gitignored)
├── archive/                        # Old approaches & session artifacts (gitignored)
│
├── .env                            # API keys (GEMINI_API_KEY, CLAUDE_CODE_OAUTH_TOKEN)
├── run.sh                          # Main game runner script
├── CLAUDE.md                       # This file
├── ARCHITECTURE.md                 # Technical deep-dive
└── WORLD_BIBLE.md                  # In-universe lore
```

## Architecture

### Core Components

**Game Master Agent (Gemini 3.0 Flash ADK)**
- Orchestrates the game loop using Coordinator/Dispatcher pattern
- Manages state transitions between game phases
- Leverages 1M+ token context window to maintain entire season transcript
- Delegates to specialized sub-agents:
  - VotingAgent: Vote tallying and tie-breaking logic
  - NarrativeAgent: Dramatic descriptions and event generation
  - PsychAgent: Updates hidden stress/trust levels across all agents

**Player Agents (Claude Agents SDK)**
- Individual AI contestants with distinct personalities
- File-system-based memory architecture for progressive disclosure
- Custom SKILL.md files defining strategic behaviors
- Trust Matrix tracking (Bayesian belief updates about other players)
- Big Five personality traits (OCEAN) modulating all decisions

**Game Engine (Python)**
- Strict rule enforcement layer
- State machine managing day/night cycles
- Economic modeling for Prize Pot
- Mission execution and performance tracking
- Win condition evaluation

### Game State Machine

The simulation cycles through five phases per "day":

1. **STATE_BREAKFAST** - Murder victim reveal; agents update trust matrices based on "breakfast order tell"
2. **STATE_MISSION** - Cooperative/competitive challenges testing different agent stats (Intellect, Dexterity, Composure)
3. **STATE_SOCIAL** - Pre-voting alliance building and information warfare
4. **STATE_ROUNDTABLE** - Public accusations and banishment voting
5. **STATE_TURRET** - Traitors secretly murder a Faithful (or recruit new Traitors)

### Agent Memory System

Each agent maintains a private directory structure:
```
/memories/player_{id}/
  ├── profile.md              # Self-concept and role
  ├── suspects.csv            # Trust Matrix (suspicion scores)
  ├── diary/                  # Daily logs
  │   ├── day_01_morning.md
  │   └── day_01_roundtable.md
  └── skills/                 # Behavioral modules
      ├── skill-traitor-defense.md
      ├── skill-faithful-hunting.md
      └── skill-shield-logic.md
```

### Personality System

Agents are initialized with Big Five (OCEAN) traits that weight decision-making:

- **Openness**: Receptiveness to new theories vs. rigid thinking
- **Conscientiousness**: Mission reliability and voting consistency
- **Extraversion**: Round Table dominance vs. passive following
- **Agreeableness**: Alliance loyalty vs. confrontational "truth-telling"
- **Neuroticism**: Paranoia/defensiveness vs. stoic composure

Each trait (0.0-1.0) modulates agent behavior across all game phases.

## Key Simulation Mechanics

### Trust Matrix Updates

Agents maintain an M_ij matrix where M_ij = Agent i's suspicion of Agent j (0.0 = absolute trust, 1.0 = certain traitor).

Updates triggered by:
- **Voting records**: Voting for/defending revealed Traitors
- **Mission sabotage**: Unexplained failures (vs. baseline clumsiness)
- **Social cues**: "Too quiet" or "too knowledgeable" behavior
- **Breakfast tells**: Consistently entering last but never murdered (indicates Traitor or recruitment)

### Regional Rule Variants

The simulator must support multiple franchise rule sets:

**Recruitment Mechanics**
- Standard: Triggered when Traitor banished; Faithful can decline
- Ultimatum (Blackmail): Last Traitor forces "Join or Die"

**End Game Variants**
- Vote to End (UK/US): Final 4 vote to continue or end; unanimous required
- Traitor's Dilemma (Australia): Final 2 Traitors play Prisoner's Dilemma (Share/Steal)

**Tie-Breaking**
- Revote with tied players immune
- Countback (cumulative season votes)
- Random draw/coin toss

### Strategic Heuristics

**Traitor Strategies:**
- "Traitor Angel": Perfect Faithful performance with loyal "useful idiots"
- "Bus Throwing": Sacrificing fellow Traitor when suspicion > threshold
- "Silent Murder": Killing trusted/non-suspicious players to create chaos

**Faithful Strategies:**
- "Shield Bluff": False Shield claims to detect information leaks
- Voting bloc analysis: Identifying coordinated voting patterns
- "Poisoned Chalice": Tracking recruitment via sudden survival shifts

## Mission Types

Missions test different agent attributes and provide observables for trust updates:

- **The Funeral (Social/Memory)**: Question-answering reveals agent attentiveness
- **Laser Heist (Dexterity/Risk)**: Probabilistic skill checks; sabotage vs. clumsiness detection
- **Cabin Creepies (Fear/Willpower)**: Neuroticism trait tests; agents may fake fear to blend
- **Crossbow Challenge (Accuracy/Vindictiveness)**: Revealed preference game showing target priorities

## Implementation Notes

### When Writing Game Engine Code

1. **State transitions must be atomic** - Never leave the game in an intermediate state
2. **All randomness must be seeded** - For reproducible season replays
3. **Trust Matrix updates are append-only** - Maintain full history for agent "memory recall"
4. **Mission performance uses formula**: `Success = (Base_Stat * Personality_Modifier) - Stress_Level`

### When Writing Agent Logic

1. **Agents cannot access ground truth** - Only their knowledge base (role, observations, Trust Matrix)
2. **Traitors must maintain "Faithful mask"** - Their public statements cannot leak privileged information
3. **Bayesian updates required** - Don't hard-code suspicions; calculate from evidence
4. **Personality traits are weights, not absolutes** - High Agreeableness increases probability of cooperation, doesn't guarantee it

### When Implementing Memory System

1. **Progressive disclosure pattern** - Agents should query specific memory files, not load everything
2. **Skills are executable prompts** - SKILL.md files define contextual behavior (e.g., "how to defend when accused")
3. **Diary entries must be timestamped** - Format: `day_{N}_{phase}.md`
4. **Trust Matrix persists as CSV** - Format: `target_id,suspicion_score,last_updated,evidence_summary`

### API Integration

**Claude Agents SDK Usage:**
- Memory: File-system-based retrieval from `/memories/{agent_id}/`
- Skills: Load SKILL.md files for context-specific behavior modules
- Decision generation: Construct prompts with personality traits + recent memory + current context

**Gemini 3.0 Flash Usage:**
- Game Master orchestration with full season context
- Narrative generation for dramatic event descriptions
- Dispatcher pattern for coordinating sub-agents

## Configuration Vectors

When initializing a simulation, the following parameters must be configurable:

```python
{
  "rule_set": "UK" | "US" | "Australia",
  "recruitment_type": "standard" | "ultimatum",
  "end_game_mode": "vote_to_end" | "traitors_dilemma",
  "tie_break_method": "revote" | "countback" | "random",
  "enable_dramatic_entry": true | false,  # Breakfast order manipulation
  "shield_visibility": "public" | "secret",
  "num_players": 20,  # Typically 20-22
  "num_traitors": 3,  # Typically 3-4
  "starting_pot": 0,
  "personality_generation": "random" | "archetype" | "custom"
}
```

## Testing Considerations

When writing tests:
- **End-to-end season tests** should verify win condition logic across all rule variants
- **Trust Matrix tests** should validate Bayesian update formulas with known evidence sequences
- **Personality tests** should confirm trait weights properly modulate decision probabilities
- **Mission tests** should check both cooperative and sabotage scenarios
- **Recruitment tests** must handle acceptance, refusal, and ultimatum edge cases
- **Tie-break tests** should cover all resolution paths including countback edge cases

## Critical Edge Cases

1. **All Traitors Banished Early**: Faithful win immediately
2. **Traitor Majority**: Traitors can force "Vote to End" and auto-win
3. **Shield on Murder Target**: Murder fails; Traitors must select alternate
4. **Recruitment Declined**: Game continues with reduced Traitor count
5. **Final Two (Both Traitors)**: Triggers Dilemma or Share depending on rule set
6. **Perfect Tie in Countback**: Falls back to random if cumulative votes equal

## Code Style Expectations

- Use type hints for all function signatures
- Agent decision logic should be pure functions (no side effects except API calls)
- State mutations only in GameEngine methods
- Trust Matrix updates should emit event logs for debugging
- All personality trait access via getter methods (not direct dict access)

## TraitorSim UI System

The web dashboard (`traitorsim-ui/`) provides post-game analysis and visualization.

### Key UI Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `TrustGraph` | `components/trust-network/` | D3.js force-directed trust network visualization |
| `PlayerCard` | `components/players/` | Player info with OCEAN traits, behavioral stats |
| `EventFeed` | `components/events/` | Chronological event list with POV filtering |
| `TimelineScrubber` | `components/timeline/` | Navigate days/phases, animate trust evolution |
| `VoteFlow` | `components/voting/` | Sankey diagram of voting patterns |
| `POVSelector` | `components/layout/` | Toggle Omniscient/Faithful/Traitor viewing modes |
| `ScrollytellingView` | `components/recap/` | Narrative story mode for game recap |
| `BreakfastOrderChart` | `components/analysis/` | Suspicion analysis from breakfast entry patterns |
| `MissionBreakdown` | `components/analysis/` | Mission performance and sabotage detection |

### State Management (Zustand)

The `gameStore` (`stores/gameStore.ts`) manages:
- Current game session and metadata
- Selected player ID for cross-component highlighting
- Current day/phase for timeline navigation
- Trust matrix snapshots with animation interpolation
- POV viewing mode (omniscient, faithful, traitor)
- UI preferences (showRoles, showEliminatedPlayers, trustThreshold)

### POV System

The `usePOVVisibility` hook (`hooks/usePOVVisibility.ts`) provides:
- `shouldShowRole(player)` - Whether to display a player's role
- `shouldRevealTraitor(player)` - Whether to highlight as known traitor
- `filterVisibleEvents(events)` - Hide traitor-only events in faithful mode
- `getVisibleTrust(matrix)` - Filter trust matrix by POV player
- `isSpoilerFree` - True when in faithful mode (no spoilers)

### API Client

The API client (`api/client.ts`) uses **relative URLs** (`/api/*`) which nginx proxies to the backend. Key endpoints:
- `GET /api/games` - List all games
- `GET /api/games/{id}` - Full game with trust matrices
- `POST /api/games/sync` - Re-import from reports directory
- `GET /api/games/{id}/trust-matrix?day=N&phase=P` - Trust at specific point

### Building & Deploying UI

```bash
# Development (with hot reload)
cd traitorsim-ui
docker compose up --build

# Production deployment
cd traitorsim-ui
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Frontend-only rebuild
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend

# Check what ports are in use
sudo netstat -tlnp | grep -E ':(80|8080|8085|5173|8000)'
```

## Running Game Simulations

```bash
# Run a containerized game (recommended)
cd /home/rkb/projects/TraitorSim
./run.sh

# Or manually with environment:
source .env
python -m src.traitorsim

# Check game reports
ls -la reports/

# Sync new reports to UI
curl -X POST http://localhost:8085/api/games/sync
```

### Game Output

Successful games produce:
- **Console logs**: Real-time game progress with phase transitions
- **reports/game_YYYYMMDD_HHMMSS.json**: Full game state for UI analysis
- **reports/game_YYYYMMDD_HHMMSS.log**: Detailed execution log

## Environment Variables

Required in `.env`:
```
GEMINI_API_KEY=...          # For Game Master (Gemini Interactions API)
CLAUDE_CODE_OAUTH_TOKEN=... # For Player Agents (Claude Agent SDK)
```

## Common Issues & Solutions

### Port Already in Use
```bash
# Find and kill process on port
sudo lsof -ti:8085 | xargs -r kill -9
# Or use a different port in docker-compose.prod.yml
```

### Docker-in-Docker Thread Exhaustion
When running 22+ player games, you may hit `pthread_create failed: resource temporarily unavailable`.

**Root cause**: `kernel.threads-max` (system-wide) is the real limit, not `ulimit -u` (per-user).

```bash
# Check thread usage
echo "Threads: $(ps -eo nlwp | tail -n +2 | awk '{sum += $1} END {print sum}') / $(cat /proc/sys/kernel/threads-max)"

# Fix (runtime)
sudo sysctl -w kernel.threads-max=65536
sudo sysctl -w kernel.pid_max=65536

# Fix (permanent) - add to /etc/sysctl.conf
```

See `docs/DEVOPS_LESSONS.md` for full explanation.

### Backend Unhealthy
The healthcheck requires `curl` in the container. Check logs:
```bash
docker logs traitorsim-ui-backend-1 --tail 50
```

### Games Not Appearing in UI
```bash
# Check reports directory is mounted
docker exec traitorsim-ui-backend-1 ls /app/reports

# Force re-sync
curl -X POST http://localhost:8085/api/games/refresh
```

### CORS Errors
The backend allows these origins (see `backend/app/main.py`):
- `http://localhost:5173` (dev)
- `http://localhost:3000`
- `https://traitorsim.rbnk.uk`

Add new origins to the `origins` list if needed.

## Known Bug Patterns (Fixed)

See `docs/DEVOPS_LESSONS.md` for detailed debugging documentation.

### Logic Inversion Bugs
**Pattern**: Comments say one thing, code does the opposite.
**Example**: Revote logic at `game_engine_containerized.py:1269` said "tied players are candidates" but rejected votes for tied players.
**Prevention**: Trace logic with real data, don't trust comments alone.

### Dictionary Key Mismatch
**Pattern**: Dict keyed by `player_id` but lookup uses `player_name`.
**Example**: Vote count lookup in `game_master_interactions.py:400` always returned 0.
**Prevention**: Verify key types match at both ends of data flow.

### Binary Values Where Spectrum Expected
**Pattern**: Using `1.0 if success else 0.0` for intermediate scores.
**Example**: `skill_check.py` gave binary performance, making gameplay feel unrealistic.
**Prevention**: Use continuous values for intermediate scoring; reserve binary for final decisions.

### Miscalibrated Formulas
**Pattern**: Mathematical formula that looks reasonable but produces extreme values.
**Example**: `intellect * (1 - difficulty)` with difficulty=0.5 gave only 25% success rates.
**Prevention**: Always plug in actual numbers before deploying formula changes.

## Verification Checklist

After making game logic changes, verify:

- [ ] Vote counts appear correctly in banishment announcements (not always 0)
- [ ] Revotes select from tied candidates only (check logs for "tied players")
- [ ] Performance scores show variety (0.3, 0.45, 0.67, not just 0/1)
- [ ] Mission success rates are reasonable (40-60%, not 20-30%)
- [ ] Both Faithfuls and Traitors can win games
- [ ] Games complete without thread exhaustion errors

Run a full game with `./run.sh` and grep for key patterns:
```bash
grep -E "(votes|TIE|performance|Winner)" reports/game_*.log | tail -50
```

## Claude Code Skills

This project includes 8 Claude Code Agent Skills in `.claude/skills/`:
1. **persona-pipeline** - Orchestrate persona generation
2. **archetype-designer** - Design OCEAN personality archetypes
3. **world-bible-validator** - Check lore consistency
4. **quota-manager** - Manage Gemini API quotas
5. **game-analyzer** - Analyze completed games
6. **memory-debugger** - Debug agent memory systems
7. **simulation-config** - Configure game rules
8. **traitorsim-orchestrator** - Run complete workflows
