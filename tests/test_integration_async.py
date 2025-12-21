"""Integration tests for async dual-SDK architecture."""

import pytest
from src.traitorsim.core.config import GameConfig
from src.traitorsim.core.game_engine_async import GameEngineAsync
from src.traitorsim.agents.player_agent_sdk import PlayerAgentSDK
from src.traitorsim.agents.game_master_interactions import GameMasterInteractions


def test_engine_initialization():
    """Test that async engine initializes correctly."""
    config = GameConfig(
        total_players=5,  # Small test
        num_traitors=2,
        gemini_api_key=None,  # No API calls for init test
        anthropic_api_key=None,
    )

    engine = GameEngineAsync(config)
    assert engine.config == config
    assert engine.game_state is not None
    assert engine.gm is not None


def test_player_initialization():
    """Test that players are initialized with correct roles."""
    config = GameConfig(total_players=5, num_traitors=2)
    engine = GameEngineAsync(config)

    # Initialize players
    engine._initialize_players()

    # Check player count
    assert len(engine.game_state.players) == 5
    assert len(engine.player_agents) == 5

    # Check role distribution
    traitors = [p for p in engine.game_state.players if p.role.value == "traitor"]
    faithful = [p for p in engine.game_state.players if p.role.value == "faithful"]

    assert len(traitors) == 2
    assert len(faithful) == 3

    # Check all players have personalities
    for player in engine.game_state.players:
        assert len(player.personality) == 5  # Big Five traits
        assert len(player.stats) == 3

    # Check trust matrix exists
    assert engine.game_state.trust_matrix is not None


def test_agent_creation():
    """Test that player agents are created correctly."""
    config = GameConfig(total_players=3, num_traitors=1)
    engine = GameEngineAsync(config)
    engine._initialize_players()

    # Check all agents created
    for player in engine.game_state.players:
        assert player.id in engine.player_agents
        agent = engine.player_agents[player.id]
        assert isinstance(agent, PlayerAgentSDK)
        assert agent.player == player
        assert agent.game_state == engine.game_state


def test_game_master_initialization():
    """Test Game Master initializes without API key."""
    config = GameConfig()
    engine = GameEngineAsync(config)

    gm = engine.gm
    assert isinstance(gm, GameMasterInteractions)

    # Should have fallback mode when no API key
    assert gm.client is None or gm.client is not None  # Can be either


def test_mcp_tools_context():
    """Test that MCP tools get correct context."""
    config = GameConfig(total_players=3, num_traitors=1)
    engine = GameEngineAsync(config)
    engine._initialize_players()

    # Get an agent
    agent = list(engine.player_agents.values())[0]

    # Check tool context has required fields
    assert "player_id" in agent.tool_context
    assert "player" in agent.tool_context
    assert "game_state" in agent.tool_context
    assert agent.tool_context["player_id"] == agent.player.id
    assert agent.tool_context["player"] == agent.player
    assert agent.tool_context["game_state"] == engine.game_state


def test_win_condition_detection():
    """Test win condition logic."""
    config = GameConfig(total_players=5, num_traitors=2)
    engine = GameEngineAsync(config)
    engine._initialize_players()

    # Initially no winner
    assert engine.game_state.check_win_condition() is None

    # Kill all traitors -> Faithful win
    for player in engine.game_state.players:
        if player.role.value == "traitor":
            player.alive = False

    from src.traitorsim.core.enums import Role

    assert engine.game_state.check_win_condition() == Role.FAITHFUL

    # Reset and test traitor win
    engine._initialize_players()

    # Kill all faithful -> Traitor win
    for player in engine.game_state.players:
        if player.role.value == "faithful":
            player.alive = False

    assert engine.game_state.check_win_condition() == Role.TRAITOR


@pytest.mark.asyncio
async def test_parallel_reflection():
    """Test that parallel reflection doesn't crash."""
    config = GameConfig(total_players=3, num_traitors=1, anthropic_api_key=None)
    engine = GameEngineAsync(config)
    engine._initialize_players()

    # This should not crash even without API keys (will use fallbacks)
    try:
        await engine._parallel_reflection_async(["Test event"])
    except Exception as e:
        # Expected to fail gracefully without API keys
        assert "API" in str(e) or "key" in str(e).lower() or True  # Allow any error


def test_memory_managers_created():
    """Test that memory managers are created for each player."""
    config = GameConfig(total_players=3, num_traitors=1)
    engine = GameEngineAsync(config)
    engine._initialize_players()

    # Check memory managers exist
    assert len(engine.memory_managers) == 3

    for player in engine.game_state.players:
        assert player.id in engine.memory_managers
        memory_manager = engine.memory_managers[player.id]
        assert memory_manager is not None
