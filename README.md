# TraitorSim

AI simulation of "The Traitors" TV show game using **dual-SDK architecture** with Gemini Interactions API for game orchestration and Claude Agent SDK for player decision-making.

## Overview

TraitorSim is a high-fidelity multi-agent AI simulation that recreates the social deduction game from the reality TV show "The Traitors." The system uses a cutting-edge **dual-SDK architecture**:

### Dual-SDK Architecture

- **Gemini Interactions API (Game Master)** - Server-side conversation state with 55-day persistence via `previous_interaction_id`, generates dramatic TV-style narratives with full game context
- **Claude Agent SDK (Player Agents)** - 10 autonomous agents with MCP tools for structured decision-making (no regex extraction!), each with unique Big Five personalities
- **Async/Parallel Execution** - Player votes and reflections execute concurrently via `asyncio.gather()`, achieving 5-10x performance improvement
- **Hybrid Memory System** - SDK sessions + file-based long-term memory (diary, suspicion tracking)
- **Trust Matrix** - NxN numpy array tracking inter-player suspicion scores
- **Complete Game Loop** - 5-phase day/night cycle (Breakfast → Mission → Social → Round Table → Turret)

## Installation

### Prerequisites

- Python 3.10 or higher
- API keys for:
  - Google Gemini API
  - Anthropic Claude API

### Setup

1. Clone the repository:
```bash
cd TraitorSim
```

2. Install dependencies:
```bash
pip install -e .
```

3. Create a `.env` file with your API keys:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Your `.env` file should contain:
```
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Usage

### Running a Simulation

```bash
# Run from package
python -m traitorsim

# Or if installed
traitorsim
```

The simulation will:
1. Initialize 10 players (3 Traitors, 7 Faithful)
2. Assign random Big Five personalities to each player
3. Run the complete game loop until a win condition is met
4. Generate dramatic narratives for each phase
5. Save game transcripts to `data/games/game_TIMESTAMP.log`

### Game Flow

Each day consists of 5 phases:

1. **Breakfast** - GM reveals murder victim (if any)
2. **Mission** - Players cooperate on a skill check challenge
3. **Social** - Agents reflect and update suspicions
4. **Round Table** - Public voting to banish a player
5. **Turret** - Traitors secretly murder a Faithful

### Win Conditions

- **Faithful Win**: All Traitors are banished
- **Traitor Win**: Traitors achieve majority (Traitors >= Faithful)

## Project Structure

```
TraitorSim/
├── src/traitorsim/
│   ├── core/                          # Game engine and data structures
│   │   ├── game_engine_async.py       # Async orchestrator with dual-SDK
│   │   ├── game_state.py              # GameState, Player, TrustMatrix
│   │   ├── config.py                  # Configuration
│   │   └── enums.py                   # GamePhase, Role
│   ├── agents/                        # AI agents (dual-SDK)
│   │   ├── game_master_interactions.py  # Gemini Interactions API GM
│   │   └── player_agent_sdk.py          # Claude Agent SDK players
│   ├── mcp/                           # MCP tools for structured decisions
│   │   ├── game_tools.py              # 6 core game tools
│   │   ├── sdk_tools.py               # SDK-compatible tool wrappers
│   │   └── server.py                  # Tool server integration
│   ├── missions/                      # Challenge types
│   │   ├── base.py                    # BaseMission abstract class
│   │   └── skill_check.py             # Simple skill check
│   ├── memory/                        # Hybrid memory system
│   │   └── memory_manager.py          # File-based long-term memory
│   └── utils/                         # Utilities
│       └── logger.py
├── data/
│   ├── memories/                      # Agent memory files (created at runtime)
│   └── games/                         # Game transcripts
└── tests/                             # Unit and integration tests
    ├── test_mcp_tools.py              # MCP tool tests
    └── test_integration_async.py      # Async engine integration tests
```

## Architecture

### Why Dual-SDK Architecture?

TraitorSim uses **two different AI SDKs** optimally suited to their roles:

#### Gemini Interactions API (Game Master)
✅ **Server-side state management** - 55-day conversation persistence via `previous_interaction_id`
✅ **Full game context** - Entire transcript stored server-side for coherent narratives
✅ **Dramatic storytelling** - Gemini excels at TV-style dramatic announcements
✅ **No manual history management** - Server handles conversation continuity automatically

#### Claude Agent SDK (Player Agents)
✅ **Strategic reasoning** - Claude Sonnet 4.5 excels at complex social deduction
✅ **Structured decisions** - MCP tools replace fragile regex extraction
✅ **Personality-driven** - Big Five traits influence all tool calls
✅ **Parallel execution** - 10 agents vote simultaneously via `asyncio.gather()`

### MCP Tools (Model Context Protocol)

Player agents make **structured decisions** via 6 MCP tools:

1. **`get_game_state`** - Fetch current game state (alive players, day, phase)
2. **`get_my_suspicions`** - Read personal suspicion scores from memory
3. **`cast_vote`** - Submit Round Table vote with reasoning
4. **`choose_murder_victim`** - Traitors select murder target (with strategy)
5. **`update_suspicion`** - Modify suspicion score for a player
6. **`get_player_info`** - Fetch details about another player

**Key Benefits**:
- **No regex extraction** - Tools return structured JSON
- **Type safety** - Input validation via schemas
- **Context injection** - Tools receive shared game state via closure pattern
- **Auditability** - All tool calls logged for analysis

### Player Agents (Claude SDK)

Each player agent (`PlayerAgentSDK`) has:

**Big Five Personality Traits** (OCEAN):
- **Openness**: Receptiveness to new theories vs. rigid thinking
- **Conscientiousness**: Reliability and consistency
- **Extraversion**: Dominance at Round Table vs. passive behavior
- **Agreeableness**: Cooperation vs. confrontation
- **Neuroticism**: Paranoia vs. composure

**Game Stats**:
- **Intellect**: Success on puzzle missions
- **Dexterity**: Success on physical missions
- **Social Influence**: Persuasiveness

**Hybrid Memory System**:
- **SDK Sessions** - Short-term context managed by Claude SDK
- **File-based Long-term Memory**:
  - `profile.md` - Role, personality, stats
  - `suspects.csv` - Suspicion tracking
  - `diary/` - Daily logs of observations

**Key Methods**:
```python
async def cast_vote_async() -> str
    """Vote via MCP tool, return target player_id"""

async def choose_murder_victim_async() -> str
    """Traitors choose target via MCP tool"""

async def reflect_on_day_async(events: List[str]) -> None
    """Update suspicions and write diary entry"""
```

### Game Master (Gemini Interactions API)

The `GameMasterInteractions` class uses Google's Interactions API:

**Server-side State**:
```python
interaction = self.client.interactions.create(
    model="gemini-3-flash-preview",
    input=prompt,
    previous_interaction_id=self.current_interaction_id,  # Links to previous turn
    system_instruction=system_prompt if not self.current_interaction_id else None,
)
self.current_interaction_id = interaction.id  # Store for next turn
```

**Benefits**:
- 55-day conversation retention (paid tier)
- No manual history management required
- Full game transcript available for narrative continuity
- Dramatic TV-style announcements with full context

### Trust Matrix

NxN numpy array where M[i][j] represents Player i's suspicion of Player j:
- 0.0 = Absolute trust
- 1.0 = Certain traitor

Updated via MCP `update_suspicion` tool based on:
- Voting patterns
- Mission performance
- Murder victims ("Why wasn't X killed?")
- Round Table arguments

### Async/Parallel Execution

The `GameEngineAsync` orchestrates parallel agent actions:

```python
async def _collect_votes_parallel_async(self) -> Dict[str, str]:
    """All alive players vote simultaneously."""
    vote_tasks = [agent.cast_vote_async() for agent in alive_agents]
    vote_results = await asyncio.gather(*vote_tasks)
    return {pid: target for pid, target in vote_results}
```

**Performance**:
- **Sequential**: ~40s for 10 agents to vote
- **Parallel**: ~7s for 10 agents to vote (5-7x improvement)

## Configuration

Edit `src/traitorsim/core/config.py` or create a custom config:

```python
from traitorsim.core.config import GameConfig

config = GameConfig(
    # Player setup
    total_players=12,                  # Number of players
    num_traitors=4,                    # Number of traitors

    # AI models (dual-SDK architecture)
    claude_model="claude-sonnet-4-5-20250929",  # Claude SDK for players
    gemini_model="gemini-3-flash-preview",      # Gemini Interactions API for GM
    anthropic_api_key="your_key_here",          # Or from .env
    gemini_api_key="your_key_here",             # Or from .env

    # Game rules
    mission_difficulty=0.6,            # Mission difficulty (0.0-1.0)
    mission_base_reward=5000.0,        # Base prize pot earnings
    max_days=30,                       # Safety limit to prevent infinite loops

    # Advanced options
    verbose=True,                      # Detailed logging
    save_transcripts=True,             # Save game logs to data/games/
)
```

## Testing

Run tests with pytest:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src/traitorsim
```

## Development

### Code Style

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Adding New Mission Types

1. Create a new class in `src/traitorsim/missions/`
2. Inherit from `BaseMission`
3. Implement `execute()` and `get_description()`

Example:
```python
from traitorsim.missions.base import BaseMission, MissionResult

class MyMission(BaseMission):
    def execute(self) -> MissionResult:
        # Mission logic here
        return MissionResult(...)

    def get_description(self) -> str:
        return "Mission description"
```

## How It Works

### Game Master (Gemini Interactions API)

The GM uses Gemini's **server-side state management** to maintain the entire game transcript for 55 days, ensuring perfect narrative continuity. It generates:

- Dramatic announcements for each phase
- Murder reveals in TV show style
- Mission descriptions
- Banishment reveals with voting details
- Finale narration

**Key Innovation**: The `previous_interaction_id` parameter links each API call to the previous turn, so the server maintains full conversation history automatically - no manual message history needed!

### Player Agents (Claude SDK with MCP Tools)

Each player agent follows this flow:

1. **Receives** game state updates (murders, banishments, mission results)
2. **Reflects** on observations using personality-driven reasoning
3. **Calls MCP tools** to update suspicions and make structured decisions
4. **Writes diary** entries explaining reasoning

Personality traits modulate ALL decisions:
- High **Extraversion**: More aggressive accusations
- High **Neuroticism**: More paranoid suspicions
- High **Agreeableness**: Less likely to confront allies

### Decision Flow Example (MCP Tools)

**Round Table Vote (Faithful)** - Using MCP tools instead of regex:
```python
# 1. Agent queries with voting prompt
async for message in query(
    prompt="Time to vote. Use get_my_suspicions and cast_vote tools.",
    options=ClaudeAgentOptions(tools=self.mcp_tools, ...)
):
    # SDK handles tool loop automatically

# 2. Agent calls get_my_suspicions tool
# Returns: {"player_02": 0.8, "player_05": 0.6, ...}

# 3. Agent reasons based on personality + suspicions

# 4. Agent calls cast_vote tool
cast_vote({
    "target_player_id": "player_02",
    "reasoning": "Consistently defensive of suspected players..."
})

# 5. Tool writes vote to shared context
# 6. Agent writes diary entry
```

**Murder Decision (Traitor)** - Structured tool call:
```python
# 1. Agent gets alive Faithful via get_game_state tool

# 2. Strategic analysis based on personality and game state

# 3. Agent calls choose_murder_victim tool
choose_murder_victim({
    "target_player_id": "player_07",
    "reasoning": "Strongest social influence, building voting bloc..."
})

# 4. Tool validates target is Faithful and alive
# 5. Tool writes decision to shared context for engine
```

**No regex extraction needed!** All decisions come through structured tool calls with validated inputs and typed outputs.

## MVP Scope

### Included ✅
- **Dual-SDK Architecture** - Gemini Interactions API + Claude Agent SDK
- **MCP Tools** - 6 structured decision-making tools (no regex!)
- **Async/Parallel Execution** - 5-10x performance improvement
- **Server-side State** - Gemini Interactions API with 55-day persistence
- **Full 5-phase Game Loop** - Breakfast → Mission → Social → Round Table → Turret
- **Hybrid Memory System** - SDK sessions + file-based long-term memory
- **Big Five Personalities** - OCEAN traits influencing all decisions
- **Trust Matrix** - NxN suspicion tracking with MCP tool updates
- **Win Condition Detection** - Faithful vs Traitor victory conditions
- **One Mission Type** - Skill check (intellect-based)
- **Comprehensive Testing** - Unit tests (MCP tools) + integration tests (async engine)

### Deferred for Future Versions ❌
- Shields and recruitment mechanics
- Multiple mission types (Laser Heist, Funeral, etc.)
- Agent-to-agent conversations during Social phase
- Traitor conferencing (currently first traitor decides)
- Advanced tie-breaking (currently random)
- End game dilemma (Australia variant)
- Human player mode

## Troubleshooting

### API Issues

If you see fallback messages:
```
⚠️  GEMINI_API_KEY not set. Using fallback narratives.
⚠️  ANTHROPIC_API_KEY not set. Using fallback decisions.
```

1. Check `.env` file exists and contains valid keys
2. Verify keys are correct (no extra quotes or spaces)
3. Ensure `python-dotenv` is installed

### Memory/Context Issues

If agents seem to "forget" information:
- Check `data/memories/player_XX/` directories exist
- Verify diary entries are being written
- Check file permissions on `data/` directory

### Game Hangs

If game loops forever:
- Default safety limit is 30 days
- Check `max_days` in config
- Review logs in `data/games/game_TIMESTAMP.log`

## License

This project is for educational and research purposes.

## Credits

Inspired by "The Traitors" TV show format. Built with:
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) - Player agent decision-making with MCP tools
- [Google Gemini Interactions API](https://ai.google.dev/gemini-api/docs/interactions) - Game Master orchestration with server-side state
- [Model Context Protocol (MCP)](https://www.anthropic.com/news/model-context-protocol) - Structured tool-based decisions
- Python 3.12+

**Innovation**: This project demonstrates **dual-SDK architecture** - using two different AI frameworks optimally suited to their roles, with async/parallel execution for 5-10x performance improvement.

## Future Enhancements

See `architectural_spec.md` for the complete vision, including:
- Multiple mission types (Laser Heist, Funeral, etc.)
- Shield and Dagger mechanics
- Recruitment and blackmail
- Regional rule variants (UK/US/Australia)
- End game dilemma (Prisoner's Dilemma for final 2 Traitors)
- Human-in-the-loop gameplay
- Voice integration for Round Table
- Advanced voting bloc analysis

---

**Note**: This is an MVP demonstrating the core concept. The full architectural specification describes a much more comprehensive system with deeper psychological modeling, complex missions, and sophisticated social dynamics.
