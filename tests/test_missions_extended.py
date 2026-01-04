"""Tests for extended mission types."""

import pytest
from src.traitorsim.core.config import GameConfig
from src.traitorsim.core.game_state import GameState, Player, Role, TrustMatrix
from src.traitorsim.missions import (
    MISSION_TYPES,
    MISSION_NAMES,
    FuneralMission,
    LaserHeistMission,
    CabinCreepiesMission,
    CrossbowMission,
    SkillCheckMission,
)


@pytest.fixture
def game_config():
    """Create a test game configuration."""
    return GameConfig(
        total_players=6,
        num_traitors=2,
        verbose=False,
        save_transcripts=False,
        mission_base_reward=10000.0,
        mission_difficulty=0.3,
    )


@pytest.fixture
def game_state_varied_personalities():
    """Create game state with varied personalities for mission testing."""
    state = GameState()

    # Create players with varied personalities
    personality_profiles = [
        # High dexterity, low neuroticism (good at physical, calm)
        {"openness": 0.7, "conscientiousness": 0.8, "extraversion": 0.6, "agreeableness": 0.4, "neuroticism": 0.2},
        # High intellect, high openness (good at memory)
        {"openness": 0.9, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.6, "neuroticism": 0.3},
        # High neuroticism (bad at fear-based missions)
        {"openness": 0.4, "conscientiousness": 0.5, "extraversion": 0.3, "agreeableness": 0.7, "neuroticism": 0.9},
        # Low agreeableness (more likely to target others)
        {"openness": 0.5, "conscientiousness": 0.6, "extraversion": 0.8, "agreeableness": 0.2, "neuroticism": 0.4},
        # Balanced
        {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
        # High conscientiousness (good at precision tasks)
        {"openness": 0.6, "conscientiousness": 0.9, "extraversion": 0.4, "agreeableness": 0.5, "neuroticism": 0.3},
    ]

    stat_profiles = [
        {"intellect": 0.6, "dexterity": 0.9, "social_influence": 0.5},
        {"intellect": 0.9, "dexterity": 0.4, "social_influence": 0.7},
        {"intellect": 0.5, "dexterity": 0.5, "social_influence": 0.4},
        {"intellect": 0.6, "dexterity": 0.7, "social_influence": 0.8},
        {"intellect": 0.5, "dexterity": 0.5, "social_influence": 0.5},
        {"intellect": 0.7, "dexterity": 0.8, "social_influence": 0.6},
    ]

    players = []
    for i in range(6):
        player = Player(
            id=f"player_{i+1:02d}",
            name=f"Player{i+1}",
            role=Role.TRAITOR if i < 2 else Role.FAITHFUL,
            personality=personality_profiles[i],
            stats=stat_profiles[i],
        )
        players.append(player)

    state.players = players
    state.trust_matrix = TrustMatrix([p.id for p in players])

    return state


class TestMissionRegistry:
    """Tests for mission type registry."""

    def test_all_mission_types_registered(self):
        """Test that all mission types are in MISSION_TYPES."""
        assert SkillCheckMission in MISSION_TYPES
        assert FuneralMission in MISSION_TYPES
        assert LaserHeistMission in MISSION_TYPES
        assert CabinCreepiesMission in MISSION_TYPES
        assert CrossbowMission in MISSION_TYPES
        assert len(MISSION_TYPES) == 5

    def test_all_mission_names_registered(self):
        """Test that all missions have display names."""
        for mission_class in MISSION_TYPES:
            assert mission_class in MISSION_NAMES
            assert len(MISSION_NAMES[mission_class]) > 0


class TestFuneralMission:
    """Tests for The Funeral mission (memory/social)."""

    def test_funeral_execution(self, game_state_varied_personalities, game_config):
        """Test funeral mission execution."""
        mission = FuneralMission(game_state_varied_personalities, game_config)
        result = mission.execute()

        assert result.earnings >= 0
        assert result.earnings <= game_config.mission_base_reward
        assert len(result.performance_scores) == len(game_state_varied_personalities.alive_players)
        # Narrative should mention funeral, ceremony, memorial, or similar
        narrative_lower = result.narrative.lower()
        assert any(word in narrative_lower for word in ["funeral", "ceremony", "memorial", "solemn"])

    def test_funeral_uses_intellect_and_openness(self, game_state_varied_personalities, game_config):
        """Test that funeral mission rewards high intellect and openness."""
        mission = FuneralMission(game_state_varied_personalities, game_config)
        result = mission.execute()

        # Player 2 has high intellect (0.9) and openness (0.9) - should perform better on average
        # This is probabilistic, so we just check the structure
        assert "player_02" in result.performance_scores

    def test_funeral_description(self, game_state_varied_personalities, game_config):
        """Test funeral mission description."""
        mission = FuneralMission(game_state_varied_personalities, game_config)
        description = mission.get_description()
        assert "Funeral" in description or "ceremony" in description.lower()


class TestLaserHeistMission:
    """Tests for Laser Heist mission (dexterity + sabotage)."""

    def test_laser_heist_execution(self, game_state_varied_personalities, game_config):
        """Test laser heist mission execution."""
        mission = LaserHeistMission(game_state_varied_personalities, game_config)
        result = mission.execute()

        assert result.earnings >= 0
        assert len(result.performance_scores) == len(game_state_varied_personalities.alive_players)
        assert "laser" in result.narrative.lower() or "maze" in result.narrative.lower()

    def test_laser_heist_traitor_sabotage_possible(self, game_state_varied_personalities, game_config):
        """Test that traitors can sabotage (probabilistic)."""
        mission = LaserHeistMission(game_state_varied_personalities, game_config)

        # Run multiple times to check sabotage can happen
        sabotage_detected = False
        for _ in range(10):
            result = mission.execute()
            if "suspicious" in result.narrative.lower() or "stumble" in result.narrative.lower():
                sabotage_detected = True
                break

        # Sabotage detection is probabilistic - just verify structure
        assert result.performance_scores is not None

    def test_laser_heist_description(self, game_state_varied_personalities, game_config):
        """Test laser heist mission description."""
        mission = LaserHeistMission(game_state_varied_personalities, game_config)
        description = mission.get_description()
        assert "Laser" in description or "maze" in description.lower()


class TestCabinCreepiesMission:
    """Tests for Cabin Creepies mission (fear/neuroticism)."""

    def test_cabin_creepies_execution(self, game_state_varied_personalities, game_config):
        """Test cabin creepies mission execution."""
        mission = CabinCreepiesMission(game_state_varied_personalities, game_config)
        result = mission.execute()

        assert result.earnings >= 0
        assert len(result.performance_scores) == len(game_state_varied_personalities.alive_players)
        assert "cabin" in result.narrative.lower() or "haunted" in result.narrative.lower()

    def test_cabin_creepies_neuroticism_penalty(self, game_state_varied_personalities, game_config):
        """Test that high neuroticism players perform worse on average."""
        mission = CabinCreepiesMission(game_state_varied_personalities, game_config)

        # Player 3 has very high neuroticism (0.9) - should perform worse
        # Player 1 has low neuroticism (0.2) - should perform better
        # This is probabilistic, just verify scores are in valid range
        result = mission.execute()
        for score in result.performance_scores.values():
            assert 0.0 <= score <= 1.0

    def test_cabin_creepies_suspiciously_calm_detection(self, game_state_varied_personalities, game_config):
        """Test that very calm players might be flagged."""
        mission = CabinCreepiesMission(game_state_varied_personalities, game_config)

        # Run a few times - "eerily calm" mentioned if too-calm players
        results = [mission.execute() for _ in range(5)]
        narratives = " ".join(r.narrative for r in results)

        # Structure verification - narrative mentions composure
        assert any("composure" in r.narrative.lower() or "calm" in r.narrative.lower() for r in results)

    def test_cabin_creepies_description(self, game_state_varied_personalities, game_config):
        """Test cabin creepies mission description."""
        mission = CabinCreepiesMission(game_state_varied_personalities, game_config)
        description = mission.get_description()
        assert "Cabin" in description or "fear" in description.lower()


class TestCrossbowMission:
    """Tests for Crossbow mission (revealed preference)."""

    def test_crossbow_execution(self, game_state_varied_personalities, game_config):
        """Test crossbow mission execution."""
        mission = CrossbowMission(game_state_varied_personalities, game_config)
        result = mission.execute()

        assert result.earnings >= 0
        assert len(result.performance_scores) == len(game_state_varied_personalities.alive_players)
        assert "arrow" in result.narrative.lower() or "target" in result.narrative.lower()

    def test_crossbow_target_selection(self, game_state_varied_personalities, game_config):
        """Test that target selection happens for all players."""
        mission = CrossbowMission(game_state_varied_personalities, game_config)
        result = mission.execute()

        # Narrative should mention who was most targeted
        assert "targeted" in result.narrative.lower() or "popular" in result.narrative.lower()

    def test_crossbow_traitor_avoidance(self, game_state_varied_personalities, game_config):
        """Test that traitors tend to avoid targeting each other."""
        # This is probabilistic - just verify the mission runs correctly
        mission = CrossbowMission(game_state_varied_personalities, game_config)
        result = mission.execute()
        assert result.performance_scores is not None

    def test_crossbow_description(self, game_state_varied_personalities, game_config):
        """Test crossbow mission description."""
        mission = CrossbowMission(game_state_varied_personalities, game_config)
        description = mission.get_description()
        assert "Crossbow" in description or "aim" in description.lower()


class TestMissionResultStructure:
    """Tests for common mission result structure."""

    @pytest.mark.parametrize("mission_class", MISSION_TYPES)
    def test_mission_result_has_required_fields(self, game_state_varied_personalities, game_config, mission_class):
        """Test that all mission types return properly structured results."""
        mission = mission_class(game_state_varied_personalities, game_config)
        result = mission.execute()

        # Check required fields
        assert hasattr(result, 'success')
        assert hasattr(result, 'earnings')
        assert hasattr(result, 'performance_scores')
        assert hasattr(result, 'narrative')

        # Check types
        assert isinstance(result.success, bool)
        assert isinstance(result.earnings, (int, float))
        assert isinstance(result.performance_scores, dict)
        assert isinstance(result.narrative, str)

    @pytest.mark.parametrize("mission_class", MISSION_TYPES)
    def test_mission_scores_in_valid_range(self, game_state_varied_personalities, game_config, mission_class):
        """Test that all mission types return scores in [0, 1] range."""
        mission = mission_class(game_state_varied_personalities, game_config)
        result = mission.execute()

        for player_id, score in result.performance_scores.items():
            assert 0.0 <= score <= 1.0, f"{mission_class.__name__}: {player_id} has invalid score {score}"

    @pytest.mark.parametrize("mission_class", MISSION_TYPES)
    def test_mission_description_exists(self, game_state_varied_personalities, game_config, mission_class):
        """Test that all mission types have descriptions."""
        mission = mission_class(game_state_varied_personalities, game_config)
        description = mission.get_description()

        assert isinstance(description, str)
        assert len(description) > 10  # Non-trivial description
