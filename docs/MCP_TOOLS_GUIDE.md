# The Traitors - MCP Tools Guide

This guide explains how to access and use the MCP (Model Context Protocol) tools for "The Traitors" game simulation.

## Overview

The TraitorSim game provides 6 MCP tools that allow Claude agents to interact with the game state and make decisions:

1. **get_game_state** - View current game information
2. **get_my_suspicions** - Check your suspicion scores
3. **get_player_info** - Query information about specific players
4. **cast_vote** - Vote to banish a player at Round Table
5. **choose_murder_victim** - Select a murder target (Traitors only)
6. **update_suspicion** - Update your suspicion score for another player

## Tool Locations

The MCP tools are implemented in the following files:

- **Implementation**: `/home/rkb/projects/TraitorSim/src/traitorsim/mcp/game_tools.py`
- **Server**: `/home/rkb/projects/TraitorSim/src/traitorsim/mcp/server.py`
- **SDK Wrappers**: `/home/rkb/projects/TraitorSim/src/traitorsim/mcp/sdk_tools.py`
- **Tests**: `/home/rkb/projects/TraitorSim/tests/test_mcp_tools.py`

## Recent Game State (from latest log)

Based on the most recent game log (`game_20251221_095209.log`):

- **Game**: Day 3, Traitors won
- **Initial Setup**: 10 players, 3 Traitors (Player4, Player5, Player8)
- **Deaths**: Player9 murdered, Player2 banished
- **Prize Pot**: $1,750
- **Final Status**: Traitors won

## Tool Descriptions

### 1. get_game_state

Get current game information including day, phase, alive players, and prize pot.

**Parameters**: None (empty dict)

**Returns**:
```json
{
  "day": 3,
  "phase": "social",
  "alive_players": [
    {"id": "player_00", "name": "Player1"},
    {"id": "player_02", "name": "Player3"}
  ],
  "prize_pot": 1750.0,
  "last_murder_victim": "Player9",
  "recent_banishments": ["Player2"]
}
```

**Example Usage**:
```python
from src.traitorsim.mcp.game_tools import get_game_state

context = {
    "game_state": game_state  # GameState object
}

result = get_game_state({}, context)
state_data = json.loads(result["content"][0]["text"])
```

### 2. get_my_suspicions

Read your current suspicion scores for all other players.

**Parameters**: None (empty dict)

**Returns**:
```json
{
  "player_02": {
    "name": "Player3",
    "suspicion": 0.5,
    "alive": true
  },
  "player_03": {
    "name": "Player4",
    "suspicion": 0.8,
    "alive": true
  }
}
```

**Suspicion Scale**:
- 0.0 = Complete trust
- 0.5 = Neutral
- 1.0 = Certain they are a Traitor

**Example Usage**:
```python
from src.traitorsim.mcp.game_tools import get_my_suspicions

context = {
    "player_id": "player_00",
    "game_state": game_state
}

result = get_my_suspicions({}, context)
suspicions = json.loads(result["content"][0]["text"])
```

### 3. get_player_info

Query stats and publicly known information about a specific player.

**Parameters**:
- `player_id` (string, required): ID of player to query (e.g., "player_03")

**Returns**:
```json
{
  "id": "player_03",
  "name": "Player4",
  "alive": true,
  "stats": {
    "intellect": 0.7,
    "dexterity": 0.6,
    "social_influence": 0.8
  },
  "role": "Unknown (alive)"
}
```

**Note**: Role is only revealed if the player is dead (banished or murdered).

**Example Usage**:
```python
from src.traitorsim.mcp.game_tools import get_player_info

context = {
    "game_state": game_state
}

args = {"player_id": "player_03"}
result = get_player_info(args, context)
player_info = json.loads(result["content"][0]["text"])
```

### 4. cast_vote

Submit your vote to banish a player at Round Table.

**Parameters**:
- `target_player_id` (string, required): ID of player to vote for (e.g., "player_03")
- `reasoning` (string, required): Brief explanation of your vote (1-2 sentences)

**Returns**:
```json
{
  "content": [{
    "type": "text",
    "text": "Vote recorded: Player4 (player_03). Reasoning: They seem suspicious..."
  }]
}
```

**Example Usage**:
```python
from src.traitorsim.mcp.game_tools import cast_vote

context = {
    "player_id": "player_00",
    "game_state": game_state
}

args = {
    "target_player_id": "player_03",
    "reasoning": "They defended a known traitor during the last Round Table."
}

result = cast_vote(args, context)
# Vote is stored in context["vote_result"]
```

### 5. choose_murder_victim

Choose which Faithful to murder tonight (Traitors only).

**Parameters**:
- `victim_player_id` (string, required): ID of Faithful player to murder
- `reasoning` (string, required): Strategic reasoning for this choice

**Returns**:
```json
{
  "content": [{
    "type": "text",
    "text": "Murder target selected: Player3 (player_02). Reasoning: Strategic elimination..."
  }]
}
```

**Restrictions**:
- Only Traitor players can use this tool
- Can only target alive Faithful players
- Cannot target other Traitors

**Example Usage**:
```python
from src.traitorsim.mcp.game_tools import choose_murder_victim

context = {
    "player": player,  # Must be a Traitor
    "game_state": game_state
}

args = {
    "victim_player_id": "player_02",
    "reasoning": "They are leading the investigation and getting too close to identifying us."
}

result = choose_murder_victim(args, context)
# Choice is stored in context["murder_choice"]
```

### 6. update_suspicion

Update your suspicion score for another player.

**Parameters**:
- `player_id` (string, required): ID of player to update suspicion for
- `new_score` (number, required): New suspicion score (0.0 to 1.0)
- `reason` (string, required): Why you updated this score

**Returns**:
```json
{
  "content": [{
    "type": "text",
    "text": "Updated suspicion of Player4: 0.50 → 0.80. Reason: Defended a known traitor..."
  }]
}
```

**Example Usage**:
```python
from src.traitorsim.mcp.game_tools import update_suspicion

context = {
    "player_id": "player_00",
    "game_state": game_state,
    "memory_manager": memory_manager  # Optional
}

args = {
    "player_id": "player_03",
    "new_score": 0.8,
    "reason": "Defended a known traitor during Round Table discussion."
}

result = update_suspicion(args, context)
```

## Using GameToolServer

The `GameToolServer` class provides a unified interface to all tools:

```python
from src.traitorsim.mcp.server import GameToolServer, get_tool_server

# Create server instance
server = GameToolServer()

# Get all available tool names
tool_names = server.get_tool_names()
# Returns: ['get_game_state', 'get_my_suspicions', 'cast_vote',
#           'choose_murder_victim', 'update_suspicion', 'get_player_info']

# Execute a tool
context = {
    "player_id": "player_00",
    "game_state": game_state
}

result = server.execute_tool("get_game_state", {}, context)

# Or use the singleton pattern
server = get_tool_server()
```

## Demo Script

A complete demonstration script is available at:
`/home/rkb/projects/TraitorSim/demo_game_state.py`

Run it with:
```bash
python3 demo_game_state.py
```

This script shows:
1. How to create a game state
2. How to call each MCP tool
3. How to parse the results
4. Example output for each tool

## Integration with Claude Agent SDK

The tools are wrapped for use with Claude Agent SDK in `/home/rkb/projects/TraitorSim/src/traitorsim/mcp/sdk_tools.py`:

```python
from src.traitorsim.mcp.sdk_tools import create_game_mcp_server

# Create MCP server for a specific player
mcp_server = create_game_mcp_server(
    player_id="player_00",
    game_state=game_state,
    memory_manager=memory_manager
)

# Use with ClaudeAgentOptions
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    mcp_servers=[mcp_server]
)
```

## Game State Structure

The `GameState` object (from `/home/rkb/projects/TraitorSim/src/traitorsim/core/game_state.py`) contains:

- `day`: Current day number (starts at 1)
- `phase`: Current game phase (INIT, BREAKFAST, MISSION, SOCIAL, ROUND_TABLE, TURRET)
- `prize_pot`: Total prize money accumulated
- `players`: List of all Player objects
- `trust_matrix`: TrustMatrix tracking suspicion scores
- `murdered_players`: List of murdered player names
- `banished_players`: List of banished player names
- `last_murder_victim`: Most recent murder victim

## Error Handling

All tools return a consistent error format:

```json
{
  "content": [{
    "type": "text",
    "text": "Error: <error message>"
  }],
  "isError": true
}
```

Common errors:
- Missing required parameters
- Invalid player IDs
- Invalid suspicion scores (must be 0.0-1.0)
- Permission errors (e.g., non-Traitor trying to murder)
- Game state not available

## Testing

Comprehensive tests are available in:
`/home/rkb/projects/TraitorSim/tests/test_mcp_tools.py`

Run tests with:
```bash
pytest tests/test_mcp_tools.py -v
```

## Summary

The MCP tools provide a structured, reliable interface for Claude agents to:
1. Query game state and player information
2. Make strategic decisions (voting, murder)
3. Track and update suspicions
4. Maintain memory of game events

These tools replace fragile regex-based extraction with type-safe, validated function calls that integrate seamlessly with the Claude Agent SDK.
