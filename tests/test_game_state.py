"""Tests for game state data structures."""

import pytest
from src.traitorsim.core.game_state import GameState, Player, Role, TrustMatrix


def test_player_creation(sample_player):
    """Test player creation and initialization."""
    assert sample_player.id == "player_01"
    assert sample_player.name == "TestPlayer"
    assert sample_player.role == Role.FAITHFUL
    assert sample_player.alive is True
    assert len(sample_player.personality) == 5
    assert len(sample_player.stats) == 3


def test_trust_matrix_initialization():
    """Test trust matrix initialization."""
    player_ids = ["player_01", "player_02", "player_03"]
    matrix = TrustMatrix(player_ids)

    # Check initial values
    assert matrix.get_suspicion("player_01", "player_02") == 0.5
    assert matrix.get_suspicion("player_01", "player_01") == 0.0  # No self-suspicion


def test_trust_matrix_updates():
    """Test trust matrix suspicion updates."""
    player_ids = ["player_01", "player_02", "player_03"]
    matrix = TrustMatrix(player_ids)

    # Increase suspicion
    matrix.update_suspicion("player_01", "player_02", 0.2)
    assert matrix.get_suspicion("player_01", "player_02") == 0.7

    # Decrease suspicion
    matrix.update_suspicion("player_01", "player_02", -0.3)
    assert matrix.get_suspicion("player_01", "player_02") == pytest.approx(0.4)

    # Test clamping at bounds
    matrix.update_suspicion("player_01", "player_03", 1.0)
    assert matrix.get_suspicion("player_01", "player_03") == 1.0  # Clamped at 1.0


def test_game_state_alive_players(game_state):
    """Test alive players property."""
    assert len(game_state.alive_players) == 10

    # Kill a player
    game_state.players[0].alive = False
    assert len(game_state.alive_players) == 9


def test_game_state_role_filtering(game_state):
    """Test faithful and traitor filtering."""
    assert len(game_state.alive_faithful) == 7
    assert len(game_state.alive_traitors) == 3

    # Kill a traitor
    game_state.players[0].alive = False
    assert len(game_state.alive_traitors) == 2


def test_win_condition_faithful_victory(game_state):
    """Test win condition: Faithful victory."""
    # Kill all traitors
    for player in game_state.players[:3]:
        player.alive = False

    winner = game_state.check_win_condition()
    assert winner == Role.FAITHFUL


def test_win_condition_traitor_victory(game_state):
    """Test win condition: Traitor majority."""
    # Kill enough faithful to give traitors majority
    for player in game_state.players[3:10]:  # Kill 7 faithful
        player.alive = False

    # 3 traitors, 0 faithful
    winner = game_state.check_win_condition()
    assert winner == Role.TRAITOR


def test_win_condition_ongoing(game_state):
    """Test win condition: Game continues."""
    # Kill one player but game should continue
    game_state.players[0].alive = False

    winner = game_state.check_win_condition()
    assert winner is None


def test_get_player_by_id(game_state):
    """Test getting player by ID."""
    player = game_state.get_player("player_01")
    assert player is not None
    assert player.id == "player_01"

    # Non-existent player
    player = game_state.get_player("player_99")
    assert player is None


def test_get_player_by_name(game_state):
    """Test getting player by name."""
    player = game_state.get_player_by_name("Player1")
    assert player is not None
    assert player.name == "Player1"
