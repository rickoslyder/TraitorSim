"""Tests for voting mechanics including dagger double-vote."""

import pytest
from collections import Counter
from src.traitorsim.core.config import GameConfig
from src.traitorsim.core.game_state import GameState, Player, Role, TrustMatrix


@pytest.fixture
def game_state_with_dagger():
    """Create game state with one player holding a dagger."""
    state = GameState()

    players = []
    for i in range(6):
        player = Player(
            id=f"player_{i+1:02d}",
            name=f"Player{i+1}",
            role=Role.FAITHFUL if i >= 2 else Role.TRAITOR,
            personality={
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
            },
            stats={"intellect": 0.5, "dexterity": 0.5, "social_influence": 0.5},
        )
        # Give first player a dagger
        if i == 0:
            player.has_dagger = True
        players.append(player)

    state.players = players
    state.trust_matrix = TrustMatrix([p.id for p in players])

    return state


class TestDaggerDoubleVote:
    """Tests for the dagger double-vote mechanic."""

    def test_dagger_holder_identified(self, game_state_with_dagger):
        """Test that dagger holder is correctly identified."""
        dagger_holders = [p for p in game_state_with_dagger.players if getattr(p, 'has_dagger', False)]
        assert len(dagger_holders) == 1
        assert dagger_holders[0].id == "player_01"

    def test_dagger_double_vote_weight(self, game_state_with_dagger):
        """Test that dagger holder's vote counts as 2."""
        # Simulate voting where dagger holder votes for target
        votes = {
            "player_01": "player_03",  # Dagger holder - should count as 2
            "player_02": "player_04",
            "player_03": "player_04",
            "player_04": "player_03",
            "player_05": "player_03",
            "player_06": "player_04",
        }

        # Tally votes (simulating async engine logic)
        vote_counts = Counter()
        for voter_id, target_id in votes.items():
            voter = game_state_with_dagger.get_player(voter_id)
            vote_weight = 2 if (voter and getattr(voter, 'has_dagger', False)) else 1
            vote_counts[target_id] += vote_weight

        # Player_03 should have: 2 (dagger) + 1 + 1 = 4 votes
        # Player_04 should have: 1 + 1 + 1 = 3 votes
        assert vote_counts["player_03"] == 4
        assert vote_counts["player_04"] == 3

    def test_dagger_vote_affects_banishment(self, game_state_with_dagger):
        """Test that dagger can swing a banishment vote."""
        # Without dagger: 3 votes each (tie)
        # With dagger: 4 vs 3 (clear winner)
        votes = {
            "player_01": "player_03",  # Dagger - 2 votes
            "player_02": "player_04",
            "player_03": "player_04",
            "player_04": "player_03",  # 1 vote
            "player_05": "player_03",  # 1 vote
            "player_06": "player_04",
        }

        vote_counts = Counter()
        for voter_id, target_id in votes.items():
            voter = game_state_with_dagger.get_player(voter_id)
            vote_weight = 2 if (voter and getattr(voter, 'has_dagger', False)) else 1
            vote_counts[target_id] += vote_weight

        # Get most voted
        banished_id, banished_votes = vote_counts.most_common(1)[0]
        assert banished_id == "player_03"
        assert banished_votes == 4


class TestTieBreaking:
    """Tests for vote tie-breaking mechanics."""

    def test_tie_detection(self, game_state):
        """Test that ties are correctly detected."""
        votes = {
            "player_01": "player_04",
            "player_02": "player_04",
            "player_03": "player_05",
            "player_04": "player_05",
            "player_05": "player_04",
        }

        vote_counts = Counter(votes.values())
        top_two = vote_counts.most_common(2)

        if len(top_two) >= 2:
            is_tie = top_two[0][1] == top_two[1][1]
        else:
            is_tie = False

        # 3 votes for player_04, 2 votes for player_05 - not a tie
        assert not is_tie

    def test_perfect_tie(self, game_state):
        """Test perfect tie scenario."""
        votes = {
            "player_01": "player_04",
            "player_02": "player_04",
            "player_03": "player_05",
            "player_04": "player_05",
        }

        vote_counts = Counter(votes.values())
        top_two = vote_counts.most_common(2)

        if len(top_two) >= 2:
            is_tie = top_two[0][1] == top_two[1][1]
        else:
            is_tie = False

        # 2 votes each - tie
        assert is_tie
        assert top_two[0][1] == 2
        assert top_two[1][1] == 2


class TestVoteRecording:
    """Tests for vote recording mechanics."""

    def test_vote_events_recorded(self, game_state):
        """Test that vote events can be tracked via game events."""
        # GameState tracks votes via add_event
        game_state.add_event(
            event_type="VOTE",
            phase="roundtable",
            actor="player_01",
            target="player_04",
            data={"vote_weight": 1},
        )

        # Verify event recorded
        vote_events = [e for e in game_state.events if e.get("type") == "VOTE"]
        assert len(vote_events) >= 1
        assert vote_events[0]["actor"] == "player_01"
        assert vote_events[0]["target"] == "player_04"

    def test_cumulative_votes_via_events(self, game_state):
        """Test cumulative vote counting via game events."""
        # Record votes as events
        game_state.add_event("VOTE", "roundtable", actor="player_01", target="player_04")
        game_state.add_event("VOTE", "roundtable", actor="player_02", target="player_04")
        game_state.add_event("VOTE", "roundtable", actor="player_03", target="player_05")

        # Count votes from events
        vote_events = [e for e in game_state.events if e.get("type") == "VOTE"]
        vote_counts = Counter(e["target"] for e in vote_events)

        assert vote_counts.get("player_04", 0) == 2
        assert vote_counts.get("player_05", 0) == 1
