"""Tests for MCP game tools."""

import pytest
from src.traitorsim.core.game_state import GameState, Player, Role, TrustMatrix
from src.traitorsim.core.config import GameConfig
from src.traitorsim.mcp.game_tools import (
    get_game_state,
    get_my_suspicions,
    cast_vote,
    choose_murder_victim,
    update_suspicion,
    get_player_info,
)
from src.traitorsim.mcp.server import GameToolServer, get_tool_server
from src.traitorsim.memory.memory_manager import MemoryManager
import json


@pytest.fixture
def mock_game_state():
    """Create a mock game state for testing."""
    from src.traitorsim.core.enums import GamePhase

    config = GameConfig()
    game_state = GameState(config)

    # Create test players
    for i in range(5):
        player = Player(
            id=f"player_{i:02d}",
            name=f"Player{i}",
            role=Role.TRAITOR if i < 2 else Role.FAITHFUL,
            personality={
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
            },
            stats={
                "intellect": 0.7,
                "dexterity": 0.6,
                "social_influence": 0.8,
            },
        )
        game_state.players.append(player)

    # Initialize trust matrix
    player_ids = [f"player_{i:02d}" for i in range(5)]
    game_state.trust_matrix = TrustMatrix(player_ids)

    game_state.day = 3
    game_state.phase = GamePhase.SOCIAL  # Set to a valid game phase
    game_state.prize_pot = 15000.0
    game_state.last_murder_victim = "Player4"

    return game_state


@pytest.fixture
def tool_context(mock_game_state):
    """Create tool context for testing."""
    return {
        "player_id": "player_00",
        "player": mock_game_state.players[0],
        "game_state": mock_game_state,
        "memory_manager": None,  # Add if needed for specific tests
    }


def test_get_game_state_success(tool_context):
    """Test get_game_state returns correct information."""
    result = get_game_state({}, tool_context)

    assert "content" in result
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "text"

    # Parse the JSON response
    state_info = json.loads(result["content"][0]["text"])

    assert state_info["day"] == 3
    assert state_info["phase"] == "social"
    assert len(state_info["alive_players"]) == 5
    assert state_info["prize_pot"] == 15000.0
    assert state_info["last_murder_victim"] == "Player4"


def test_get_game_state_missing_context():
    """Test get_game_state with missing game state."""
    result = get_game_state({}, {})

    assert result["isError"] is True
    assert "Error" in result["content"][0]["text"]


def test_get_my_suspicions_success(tool_context):
    """Test get_my_suspicions returns suspicion scores."""
    result = get_my_suspicions({}, tool_context)

    assert "content" in result
    suspicions = json.loads(result["content"][0]["text"])

    # Should have suspicions for 4 other players (not self)
    assert len(suspicions) == 4
    assert "player_00" not in suspicions  # No self-suspicion

    # Check structure
    for player_id, data in suspicions.items():
        assert "name" in data
        assert "suspicion" in data
        assert "alive" in data
        assert 0.0 <= data["suspicion"] <= 1.0


def test_get_my_suspicions_missing_context():
    """Test get_my_suspicions with missing context."""
    result = get_my_suspicions({}, {})

    assert result["isError"] is True


def test_cast_vote_success(tool_context):
    """Test cast_vote with valid target."""
    args = {
        "target_player_id": "player_01",
        "reasoning": "They seem suspicious based on voting patterns.",
    }

    result = cast_vote(args, tool_context)

    assert "isError" not in result or result.get("isError") is False
    assert "Vote recorded" in result["content"][0]["text"]
    assert "vote_result" in tool_context
    assert tool_context["vote_result"]["target"] == "player_01"
    assert tool_context["vote_result"]["reasoning"] == args["reasoning"]


def test_cast_vote_missing_target(tool_context):
    """Test cast_vote without target_player_id."""
    result = cast_vote({}, tool_context)

    assert result["isError"] is True
    assert "target_player_id is required" in result["content"][0]["text"]


def test_cast_vote_invalid_target(tool_context):
    """Test cast_vote with invalid target."""
    args = {
        "target_player_id": "player_99",  # Doesn't exist
        "reasoning": "Test",
    }

    result = cast_vote(args, tool_context)

    assert result["isError"] is True
    assert "not a valid vote target" in result["content"][0]["text"]


def test_cast_vote_self_target(tool_context):
    """Test cast_vote trying to vote for self."""
    args = {
        "target_player_id": "player_00",  # Self
        "reasoning": "Test",
    }

    result = cast_vote(args, tool_context)

    assert result["isError"] is True
    assert "not a valid vote target" in result["content"][0]["text"]


def test_choose_murder_victim_success(tool_context):
    """Test choose_murder_victim by traitor."""
    args = {
        "victim_player_id": "player_02",  # Faithful player
        "reasoning": "Strategic elimination of vocal player.",
    }

    result = choose_murder_victim(args, tool_context)

    assert "isError" not in result or result.get("isError") is False
    assert "Murder target selected" in result["content"][0]["text"]
    assert "murder_choice" in tool_context
    assert tool_context["murder_choice"]["victim"] == "player_02"


def test_choose_murder_victim_not_traitor(tool_context):
    """Test choose_murder_victim by non-traitor."""
    # Change player to Faithful
    tool_context["player"].role = Role.FAITHFUL

    args = {
        "victim_player_id": "player_02",
        "reasoning": "Test",
    }

    result = choose_murder_victim(args, tool_context)

    assert result["isError"] is True
    assert "Only Traitors can use this tool" in result["content"][0]["text"]


def test_choose_murder_victim_invalid_target(tool_context):
    """Test choose_murder_victim with traitor target."""
    args = {
        "victim_player_id": "player_01",  # Another traitor
        "reasoning": "Test",
    }

    result = choose_murder_victim(args, tool_context)

    assert result["isError"] is True
    assert "not a valid murder target" in result["content"][0]["text"]


def test_update_suspicion_success(tool_context, mock_game_state):
    """Test update_suspicion updates trust matrix."""
    args = {
        "player_id": "player_01",
        "new_score": 0.8,
        "reason": "Defended a known traitor during Round Table.",
    }

    # Get initial suspicion
    initial = mock_game_state.trust_matrix.get_suspicion("player_00", "player_01")

    result = update_suspicion(args, tool_context)

    assert "isError" not in result or result.get("isError") is False
    assert "Updated suspicion" in result["content"][0]["text"]

    # Check matrix was updated
    new_suspicion = mock_game_state.trust_matrix.get_suspicion("player_00", "player_01")
    assert new_suspicion == 0.8


def test_update_suspicion_out_of_range(tool_context):
    """Test update_suspicion with invalid score."""
    args = {
        "player_id": "player_01",
        "new_score": 1.5,  # Out of range
        "reason": "Test",
    }

    result = update_suspicion(args, tool_context)

    assert result["isError"] is True
    assert "between 0.0 and 1.0" in result["content"][0]["text"]


def test_update_suspicion_missing_params(tool_context):
    """Test update_suspicion with missing parameters."""
    result = update_suspicion({}, tool_context)

    assert result["isError"] is True
    assert "required" in result["content"][0]["text"]


def test_get_player_info_success(tool_context):
    """Test get_player_info for alive player."""
    args = {"player_id": "player_01"}

    result = get_player_info(args, tool_context)

    assert "isError" not in result or result.get("isError") is False

    player_info = json.loads(result["content"][0]["text"])
    assert player_info["id"] == "player_01"
    assert player_info["name"] == "Player1"
    assert player_info["alive"] is True
    assert player_info["role"] == "Unknown (alive)"  # Role hidden for living players
    assert "stats" in player_info


def test_get_player_info_dead_player(tool_context, mock_game_state):
    """Test get_player_info for dead player reveals role."""
    # Kill a player
    mock_game_state.players[1].alive = False

    args = {"player_id": "player_01"}

    result = get_player_info(args, tool_context)

    player_info = json.loads(result["content"][0]["text"])
    assert player_info["alive"] is False
    assert player_info["role"] == "traitor"  # Role revealed when dead


def test_get_player_info_missing_player(tool_context):
    """Test get_player_info with non-existent player."""
    args = {"player_id": "player_99"}

    result = get_player_info(args, tool_context)

    assert result["isError"] is True
    assert "not found" in result["content"][0]["text"]


def test_get_player_info_missing_param(tool_context):
    """Test get_player_info without player_id."""
    result = get_player_info({}, tool_context)

    assert result["isError"] is True
    assert "player_id is required" in result["content"][0]["text"]


def test_tool_server_initialization():
    """Test GameToolServer initialization."""
    server = GameToolServer()

    assert len(server.get_tool_names()) == 6
    assert "cast_vote" in server.get_tool_names()
    assert "choose_murder_victim" in server.get_tool_names()


def test_tool_server_get_tools_for_sdk():
    """Test tool formatting for SDK."""
    server = GameToolServer()
    tools = server.get_tools_for_sdk()

    assert len(tools) == 6
    for tool in tools:
        assert "name" in tool
        assert "function" in tool
        assert "description" in tool
        assert "input_schema" in tool


def test_tool_server_execute_tool(tool_context):
    """Test tool execution through server."""
    server = GameToolServer()

    result = server.execute_tool(
        "get_game_state",
        {},
        tool_context
    )

    assert "content" in result
    assert "isError" not in result or result.get("isError") is False


def test_tool_server_execute_unknown_tool(tool_context):
    """Test executing unknown tool."""
    server = GameToolServer()

    result = server.execute_tool("unknown_tool", {}, tool_context)

    assert result["isError"] is True
    assert "Unknown tool" in result["content"][0]["text"]


def test_tool_server_singleton():
    """Test singleton pattern for get_tool_server."""
    server1 = get_tool_server()
    server2 = get_tool_server()

    assert server1 is server2  # Same instance
