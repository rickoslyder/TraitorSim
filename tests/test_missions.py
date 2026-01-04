"""Tests for mission system."""

import pytest
from src.traitorsim.missions.skill_check import SkillCheckMission


def test_skill_check_mission_execution(game_state, game_config):
    """Test skill check mission execution."""
    mission = SkillCheckMission(game_state, game_config)

    result = mission.execute()

    # Check result structure
    assert result.earnings >= 0
    assert result.earnings <= game_config.mission_base_reward
    assert len(result.performance_scores) == len(game_state.alive_players)
    assert result.narrative != ""

    # Check performance scores are in valid range [0, 1]
    for score in result.performance_scores.values():
        assert 0.0 <= score <= 1.0


def test_skill_check_mission_description(game_state, game_config):
    """Test mission description."""
    mission = SkillCheckMission(game_state, game_config)

    description = mission.get_description()
    assert isinstance(description, str)
    assert len(description) > 0
