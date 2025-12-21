# TraitorSim Architecture - Dual-SDK Deep Dive

## Overview

TraitorSim implements a **dual-SDK architecture** that leverages the unique strengths of two AI frameworks:

1. **Claude Agent SDK** (player agents) - Strategic decision-making with MCP tools
2. **Gemini Interactions API** (game master) - Narrative generation with server-side state

This document provides technical implementation details for developers.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                  GameEngineAsync                           │
│              (Async Orchestrator)                          │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │    GameMasterInteractions                        │    │
│  │    (Gemini Interactions API)                     │    │
│  │                                                   │    │
│  │  - Server-side state (previous_interaction_id)   │    │
│  │  - 55-day conversation persistence               │    │
│  │  - Dramatic TV-style narratives                  │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  ┌─────────────┬─────────────┬─────────────┬──────────┐  │
│  │ PlayerAgent │ PlayerAgent │ PlayerAgent │   ...    │  │
│  │   SDK #1    │   SDK #2    │   SDK #3    │  #10     │  │
│  │  (Claude)   │  (Claude)   │  (Claude)   │ (Claude) │  │
│  │             │             │             │          │  │
│  │  MCP Tools  │  MCP Tools  │  MCP Tools  │MCP Tools │  │
│  └──────┬──────┴──────┬──────┴──────┬──────┴────┬─────┘  │
│         │             │             │           │        │
│         └─────────────┴─────────────┴───────────┘        │
│                         │                                │
│              ┌──────────▼──────────┐                     │
│              │   Shared GameState  │                     │
│              │   + TrustMatrix     │                     │
│              │   (via tool context)│                     │
│              └─────────────────────┘                     │
└────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. GameEngineAsync

**File**: `src/traitorsim/core/game_engine_async.py`

The async orchestrator coordinates the entire game loop using `asyncio` for parallel execution.

**Key Responsibilities**:
- Initialize game state, players, trust matrix
- Create Game Master (Gemini) and Player Agents (Claude)
- Run 5-phase game loop (Breakfast → Mission → Social → Round Table → Turret)
- Coordinate parallel voting via `asyncio.gather()`
- Check win conditions after each phase

**Critical Methods**:

```python
async def run_game_async(self) -> str:
    """Main game loop with async/await."""
    self._initialize_players()

    while self.game_state.day <= self.config.max_days:
        await self._run_breakfast_phase_async()
        await self._run_mission_phase_async()
        await self._run_social_phase_async()
        await self._run_roundtable_phase_async()

        winner = self.game_state.check_win_condition()
        if winner:
            break

        await self._run_turret_phase_async()

    return winner.value.upper()
```

**Parallel Execution Pattern**:

```python
async def _collect_votes_parallel_async(self) -> Dict[str, str]:
    """Collect votes from all alive players in parallel."""

    async def vote_with_fallback(player_id: str, agent: PlayerAgentSDK):
        try:
            target = await agent.cast_vote_async()
            return (player_id, target or self._emergency_vote(player_id))
        except Exception as e:
            self.logger.error(f"Vote error: {e}")
            return (player_id, self._emergency_vote(player_id))

    # Execute all votes simultaneously
    vote_tasks = [vote_with_fallback(pid, agent) for pid, agent in alive_agents]
    vote_results = await asyncio.gather(*vote_tasks)

    return {pid: target for pid, target in vote_results}
```

**Performance**: Achieves 5-7x speedup by voting in parallel instead of sequentially.

---

### 2. GameMasterInteractions (Gemini)

**File**: `src/traitorsim/agents/game_master_interactions.py`

Uses Google's Interactions API with **server-side state management**.

**Key Innovation**: The `previous_interaction_id` parameter creates a conversation chain stored on Google's servers for 55 days (paid tier). No manual message history management needed!

**Implementation**:

```python
class GameMasterInteractions:
    def __init__(self, game_state, api_key, model_name="gemini-3-flash-preview"):
        self.client = genai.Client(api_key=api_key)
        self.current_interaction_id: Optional[str] = None  # Tracks conversation
        self.model_name = model_name

    async def _send_message_async(self, prompt: str) -> str:
        """Send message with server-side state linking."""

        interaction = self.client.interactions.create(
            model=self.model_name,
            input=prompt,
            previous_interaction_id=self.current_interaction_id,  # Link to previous turn!
            system_instruction=self._get_system_instruction() if not self.current_interaction_id else None,
        )

        # Store interaction ID for next turn
        self.current_interaction_id = interaction.id

        return interaction.outputs[-1].text.strip()
```

**Benefits**:
- ✅ **No message history array** - Server handles it
- ✅ **Full game context** - Entire transcript available for coherent narratives
- ✅ **55-day persistence** - Can resume games across sessions
- ✅ **System instruction** - Only needed on first turn

**Narrative Methods**:
- `announce_game_start_async()` - Opening ceremony
- `announce_murder_async()` - Breakfast phase reveal
- `describe_mission_async()` - Mission briefing
- `announce_mission_result_async()` - Prize pot update
- `announce_banishment_async()` - Round Table reveal
- `announce_finale_async()` - Winner announcement

All methods use the same `_send_message_async()` pattern, building narrative continuity through the conversation chain.

---

### 3. PlayerAgentSDK (Claude)

**File**: `src/traitorsim/agents/player_agent_sdk.py`

Each player is an autonomous Claude agent using the **Claude Agent SDK** with **MCP tools**.

**Key Features**:
- 🎭 **Big Five Personality** (OCEAN traits) influences all decisions
- 🛠️ **6 MCP Tools** for structured decision-making (no regex!)
- 💾 **Hybrid Memory** - SDK sessions + file-based long-term storage
- 🧠 **Strategic Reasoning** - Claude Sonnet 4.5 excels at social deduction

**Initialization**:

```python
class PlayerAgentSDK:
    def __init__(self, player: Player, game_state: GameState, memory_manager: MemoryManager):
        self.player = player
        self.game_state = game_state
        self.memory_manager = memory_manager

        # Shared context for tool results
        self.tool_context: Dict[str, Any] = {
            "player_id": player.id,
            "player": player,
            "game_state": game_state,
        }

        # Create MCP tools with context injection via closure
        self.mcp_tools = create_game_tools_for_player(self.tool_context)
```

**Decision-Making Pattern** (cast_vote example):

```python
async def cast_vote_async(self) -> Optional[str]:
    """Vote for a player to banish using MCP tools."""

    # Clear previous vote result
    self.tool_context.pop("vote_result", None)

    prompt = """Round Table voting time.

Steps:
1. Use get_game_state to see alive players
2. Use get_my_suspicions to check your suspicion scores
3. Use cast_vote with target_player_id and reasoning

Consider your personality traits and strategic position."""

    # SDK handles tool loop automatically
    async for message in query(
        prompt=prompt,
        options=self._build_options(),
    ):
        if isinstance(message, ResultMessage):
            break

    # Extract vote from tool context (written by cast_vote tool)
    vote_result = self.tool_context.get("vote_result")

    if vote_result and "target" in vote_result:
        return vote_result["target"]
    else:
        # Fallback if tool wasn't called
        return self._emergency_fallback_vote()
```

**Context Sharing Pattern**:
Tools write results to `self.tool_context`, agent reads after query completes. This shared dictionary bridges the tool execution and agent decision extraction.

---

### 4. MCP Tools

**Files**:
- `src/traitorsim/mcp/game_tools.py` - Core tool implementations
- `src/traitorsim/mcp/sdk_tools.py` - SDK-compatible wrappers
- `src/traitorsim/mcp/server.py` - Tool server integration

#### Tool 1: get_game_state

```python
{
    "name": "get_game_state",
    "description": "Get current game state including alive players, day, and phase",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "day": 3,
    "phase": "ROUNDTABLE",
    "alive_players": ["player_00", "player_02", "player_05", ...],
    "prize_pot": 15000.0,
    "last_murder_victim": "player_08",
    "banished_players": ["player_03"]
}
```

#### Tool 2: get_my_suspicions

```python
{
    "name": "get_my_suspicions",
    "description": "Get your current suspicion scores for all players",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
```

**Returns**:
```json
{
    "player_00": 0.2,
    "player_02": 0.8,  // High suspicion
    "player_05": 0.1,
    "player_07": 0.6
}
```

#### Tool 3: cast_vote

```python
{
    "name": "cast_vote",
    "description": "Submit your vote to banish a player at Round Table",
    "parameters": {
        "type": "object",
        "properties": {
            "target_player_id": {"type": "string"},
            "reasoning": {"type": "string"}
        },
        "required": ["target_player_id", "reasoning"]
    }
}
```

**Side effects**:
- Validates target is alive and not self
- Writes `{"target": target_player_id}` to `context["vote_result"]`
- Logs reasoning for analysis

#### Tool 4: choose_murder_victim

```python
{
    "name": "choose_murder_victim",
    "description": "Choose a Faithful player to murder (Traitors only)",
    "parameters": {
        "type": "object",
        "properties": {
            "target_player_id": {"type": "string"},
            "reasoning": {"type": "string"}
        },
        "required": ["target_player_id", "reasoning"]
    }
}
```

**Validation**:
- Caller must be a Traitor
- Target must be Faithful and alive
- Writes `{"target": target_player_id}` to context

#### Tool 5: update_suspicion

```python
{
    "name": "update_suspicion",
    "description": "Update your suspicion score for another player",
    "parameters": {
        "type": "object",
        "properties": {
            "target_player_id": {"type": "string"},
            "new_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "notes": {"type": "string"}
        },
        "required": ["target_player_id", "new_score"]
    }
}
```

**Side effects**:
- Updates `suspects.csv` in agent's memory directory
- Updates trust matrix in game state

#### Tool 6: get_player_info

```python
{
    "name": "get_player_info",
    "description": "Get detailed info about another player",
    "parameters": {
        "type": "object",
        "properties": {
            "target_player_id": {"type": "string"}
        },
        "required": ["target_player_id"]
    }
}
```

**Returns**:
```json
{
    "id": "player_02",
    "name": "Player3",
    "alive": true,
    "personality": {
        "openness": 0.65,
        "conscientiousness": 0.42,
        "extraversion": 0.78,
        "agreeableness": 0.31,
        "neuroticism": 0.55
    },
    "stats": {
        "intellect": 0.72,
        "dexterity": 0.48,
        "social_influence": 0.81
    }
}
```

**Note**: Role is intentionally NOT revealed (simulates real game).

---

## Data Flow

### Round Table Voting (Detailed Flow)

1. **Engine initiates parallel voting**:
   ```python
   votes = await self._collect_votes_parallel_async()
   ```

2. **Each agent query starts**:
   ```python
   async for message in query(prompt="Vote now...", options=...):
       # SDK handles tool loop
   ```

3. **Agent calls get_my_suspicions tool**:
   - Tool reads `data/memories/player_XX/suspects.csv`
   - Returns suspicion scores as JSON

4. **Agent reasons** based on:
   - Personality traits (e.g., high Neuroticism → more paranoid)
   - Suspicion scores
   - Recent events (murders, mission failures)

5. **Agent calls cast_vote tool**:
   ```python
   cast_vote({
       "target_player_id": "player_02",
       "reasoning": "Defensive behavior suggests guilt..."
   })
   ```

6. **Tool validates and writes**:
   - Checks target is alive and not self
   - Writes `{"target": "player_02"}` to `tool_context["vote_result"]`

7. **Agent extracts vote**:
   ```python
   vote_result = self.tool_context.get("vote_result")
   return vote_result["target"]
   ```

8. **Engine collects all votes** via `asyncio.gather()`

9. **Engine tallies votes**:
   ```python
   vote_counts = Counter(votes.values())
   banished_id = vote_counts.most_common(1)[0][0]
   ```

10. **GM announces banishment**:
    ```python
    narrative = await self.gm.announce_banishment_async(
        banished_name, role, votes, day
    )
    ```

11. **Agents reflect on outcome**:
    ```python
    await self._parallel_reflection_async([
        f"{banished_name} was banished",
        f"They were a {role.upper()}"
    ])
    ```

---

## Memory System

### File Structure

```
data/memories/player_00/
├── profile.md          # Role, personality, stats (written at init)
├── suspects.csv        # Suspicion tracking (updated via MCP tools)
└── diary/
    ├── day_01_breakfast.md
    ├── day_01_social.md
    ├── day_02_roundtable.md
    └── ...
```

### profile.md Example

```markdown
# Agent Profile: Player1

## Role
TRAITOR

## Personality Traits (Big Five)
- Openness: 0.65
- Conscientiousness: 0.42
- Extraversion: 0.78
- Agreeableness: 0.31
- Neuroticism: 0.55

## Stats
- Intellect: 0.72
- Dexterity: 0.48
- Social Influence: 0.81

## Mission
Survive undetected and eliminate Faithfuls.
```

### suspects.csv Example

```csv
player_id,name,suspicion_score,notes
player_02,Player3,0.80,Defensive of known traitors
player_05,Player6,0.60,Suspicious voting patterns
player_07,Player8,0.20,Consistent and trustworthy
```

### Diary Entry Example

```markdown
# Day 2 - Roundtable

Player4 was banished today. They were revealed as FAITHFUL - a critical loss
for our team. I voted for Player3 because their defensive behavior during the
mission discussion raised red flags. However, the vote went against Player4
instead, who I had lower suspicion of (0.35).

Updated suspicions:
- Player3: 0.65 → 0.80 (led the charge against Player4)
- Player7: 0.50 → 0.40 (made logical arguments)

Strategy: Need to deflect attention from myself. Will target Player3 next round.
```

---

## Performance Optimizations

### Parallel Execution

**Before (Sequential)**:
```python
votes = {}
for agent in alive_agents:
    votes[agent.player.id] = await agent.cast_vote_async()
# Total: 10 agents × 4s/vote = 40s
```

**After (Parallel)**:
```python
vote_tasks = [agent.cast_vote_async() for agent in alive_agents]
vote_results = await asyncio.gather(*vote_tasks)
votes = {pid: target for pid, target in vote_results}
# Total: max(4s) = ~7s (with API rate limits)
```

**Speedup**: 5-7x improvement on Round Table and Social phases

### Context Management

**Challenge**: MCP tools need access to game state and player context

**Solution**: Closure-based context injection

```python
def create_game_tools_for_player(context: Dict[str, Any]) -> List[SdkMcpTool]:
    """Create tools with captured context."""

    @tool("cast_vote", "Submit your vote", {...})
    async def cast_vote_sdk(args: Dict[str, Any]) -> Dict[str, Any]:
        # Context captured by closure!
        return game_tools.cast_vote(args, context)

    return [cast_vote_sdk, ...]
```

**Benefits**:
- ✅ Each agent has independent tool instances
- ✅ No global state pollution
- ✅ Type-safe context sharing
- ✅ Tools can modify shared state (e.g., write vote results)

---

## Testing Strategy

### Unit Tests (test_mcp_tools.py)

Tests each MCP tool in isolation with mock game state:

```python
@pytest.fixture
def mock_game_state():
    """Create mock game state for testing."""
    game_state = MagicMock()
    game_state.players = [
        MagicMock(id=f"player_{i:02d}", name=f"Player{i+1}", alive=True, role=Role.FAITHFUL)
        for i in range(5)
    ]
    game_state.trust_matrix = TrustMatrix([p.id for p in game_state.players])
    return game_state

def test_cast_vote_valid():
    """Test cast_vote with valid target."""
    context = {"player_id": "player_00", "game_state": mock_game_state}

    result = game_tools.cast_vote({
        "target_player_id": "player_01",
        "reasoning": "Suspicious behavior"
    }, context)

    assert result["success"] is True
    assert context.get("vote_result") == {"target": "player_01"}
```

**Coverage**: 23 tests covering all 6 tools + edge cases

### Integration Tests (test_integration_async.py)

Tests the complete async dual-SDK system:

```python
def test_player_initialization():
    """Test players are initialized with correct roles."""
    engine = GameEngineAsync(config)
    engine._initialize_players()

    assert len(engine.game_state.players) == 5
    assert len(engine.player_agents) == 5

    traitors = [p for p in engine.game_state.players if p.role == Role.TRAITOR]
    assert len(traitors) == 2

@pytest.mark.asyncio
async def test_parallel_reflection():
    """Test parallel reflection doesn't crash."""
    engine = GameEngineAsync(config)
    engine._initialize_players()

    await engine._parallel_reflection_async(["Test event"])
```

**Coverage**: 8 tests covering engine initialization, role assignment, win conditions, parallel execution

---

## API Key Management

### Environment Variables

Create `.env` file:
```bash
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Fallback Behavior

**No Gemini API key**:
- GM uses basic fallback messages (non-dramatic)
- Game still runs normally

**No Anthropic API key**:
- PlayerAgentSDK will fail on tool queries
- Game cannot run (agents can't make decisions)

### Cost Estimation

**Per game (10 players, ~15 days, 150 turns)**:
- Claude API: ~500K tokens (input + output) = ~$5-10
- Gemini API: ~200K tokens (narratives) = ~$1-2

**Total**: ~$6-12 per complete game simulation

---

## Future Enhancements

### Potential Improvements

1. **Rate Limiting**:
   ```python
   semaphore = asyncio.Semaphore(5)  # Max 5 concurrent API calls
   async with semaphore:
       result = await agent.cast_vote_async()
   ```

2. **Traitor Conferencing**:
   - Add `traitor_conference_async()` method
   - Traitors discuss murder target in private
   - Current: First traitor decides alone

3. **Advanced Tie-Breaking**:
   - Revote mechanism
   - Countback to previous rounds
   - Current: Random selection

4. **Agent-to-Agent Conversations**:
   - Social phase private chats
   - Coalition building
   - Requires multi-agent conversation orchestration

5. **Resume Game from Checkpoint**:
   - Leverage Gemini's 55-day persistence
   - Store `current_interaction_id` to file
   - Resume from specific day

---

## Debugging Tips

### Enable Detailed Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Tool Calls

Add logging to SDK tools:
```python
@tool("cast_vote", ...)
async def cast_vote_sdk(args: Dict[str, Any]):
    logger.debug(f"Tool called: cast_vote({args})")
    result = game_tools.cast_vote(args, context)
    logger.debug(f"Tool result: {result}")
    return result
```

### Check Memory Files

```bash
# View agent's suspicion scores
cat data/memories/player_00/suspects.csv

# View agent's diary
cat data/memories/player_00/diary/day_01_roundtable.md
```

### Test Individual Phases

```python
async def test_single_phase():
    engine = GameEngineAsync(config)
    engine._initialize_players()
    await engine._run_roundtable_phase_async()
```

---

## Conclusion

The dual-SDK architecture demonstrates:

✅ **Optimal tool selection** - Right AI for the right job
✅ **Structured decisions** - MCP tools eliminate regex fragility
✅ **Server-side state** - Gemini Interactions API simplifies history management
✅ **Performance** - Async/parallel execution achieves 5-10x speedup
✅ **Maintainability** - Clear separation of concerns (GM vs Players)

This pattern can be applied to other multi-agent simulations requiring both orchestration and autonomous decision-making.
