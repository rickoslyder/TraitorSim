"""Pytest configuration and fixtures."""

import pytest
from src.traitorsim.core.config import GameConfig
from src.traitorsim.core.game_state import GameState, Player, Role, TrustMatrix


@pytest.fixture
def game_config():
    """Create a test game configuration."""
    return GameConfig(
        total_players=10,
        num_traitors=3,
        verbose=False,
        save_transcripts=False,
        gemini_api_key="test_key",
        anthropic_api_key="test_key",
    )


@pytest.fixture
def game_state():
    """Create a test game state."""
    state = GameState()

    # Create test players
    players = []
    for i in range(10):
        player = Player(
            id=f"player_{i+1:02d}",
            name=f"Player{i+1}",
            role=Role.FAITHFUL if i >= 3 else Role.TRAITOR,
        )
        players.append(player)

    state.players = players
    state.trust_matrix = TrustMatrix([p.id for p in players])

    return state


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(
        id="player_01",
        name="TestPlayer",
        role=Role.FAITHFUL,
        personality={
            "openness": 0.7,
            "conscientiousness": 0.6,
            "extraversion": 0.8,
            "agreeableness": 0.5,
            "neuroticism": 0.4,
        },
        stats={"intellect": 0.8, "dexterity": 0.6, "social_influence": 0.7},
    )
