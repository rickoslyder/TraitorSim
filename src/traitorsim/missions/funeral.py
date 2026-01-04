"""The Funeral - Memory and social deduction mission.

Players must answer questions about events that occurred in the game.
Tests memory (past events) and social awareness (reading other players).
"""

import random
from typing import Dict, List, Tuple
from .base import BaseMission, MissionResult


class FuneralMission(BaseMission):
    """Memory-based mission testing player attentiveness and social awareness.

    Players answer questions about past game events. Performance is based on:
    - Intellect: Recall accuracy
    - Openness: Willingness to consider multiple interpretations
    - Social Influence: Reading other players' reactions

    This mission rewards players who have been paying attention to the game
    and can detect inconsistencies in others' stories.
    """

    def execute(self) -> MissionResult:
        """Execute the Funeral mission.

        Each player's performance is based on:
        1. Memory recall (intellect-based)
        2. Social reading (social_influence + openness)
        3. Traitor deception factor (traitors may fake poor memory)
        """
        alive = list(self.game_state.alive_players)
        base_reward = self.config.mission_base_reward
        difficulty = self.config.mission_difficulty

        performance_scores: Dict[str, float] = {}
        total_successes = 0

        # Generate "questions" based on game history
        num_questions = min(5, max(2, self.game_state.day))

        for player in alive:
            # Get relevant stats
            intellect = player.stats.get("intellect", 0.5)
            social_influence = player.stats.get("social_influence", 0.5)
            openness = player.personality.get("openness", 0.5)

            # Memory performance: intellect * openness
            memory_score = intellect * (0.7 + 0.3 * openness)

            # Social reading: ability to detect lies
            social_score = social_influence * openness

            # Combined base performance
            base_performance = (memory_score * 0.6 + social_score * 0.4)
            base_performance *= (1 - difficulty * 0.4)

            # Traitors may strategically underperform to avoid suspicion
            from ..core.game_state import Role
            if player.role == Role.TRAITOR:
                neuroticism = player.personality.get("neuroticism", 0.5)
                # High neuroticism traitors might slip up
                if random.random() < neuroticism * 0.3:
                    base_performance *= random.uniform(0.7, 0.9)

            # Add randomness
            random_factor = random.uniform(0.75, 1.25)
            performance = base_performance * random_factor

            # Clamp to valid range
            performance = max(0.0, min(1.0, performance))
            performance_scores[player.id] = round(performance, 2)

            if performance >= 0.5:
                total_successes += 1

        # Calculate earnings
        avg_performance = sum(performance_scores.values()) / len(alive) if alive else 0
        earnings = base_reward * avg_performance

        # Generate narrative
        best_performer = max(performance_scores.items(), key=lambda x: x[1])
        best_player = self.game_state.get_player(best_performer[0])
        best_name = best_player.name if best_player else "Someone"

        narrative = (
            f"The contestants gathered for a solemn memorial, sharing memories of fallen players. "
            f"{total_successes}/{len(alive)} showed keen attention to detail. "
            f"{best_name} displayed remarkable memory (score: {best_performer[1]:.0%}). "
            f"${earnings:,.0f} added to the prize pot."
        )

        return MissionResult(
            success=(avg_performance >= 0.5),
            earnings=earnings,
            performance_scores=performance_scores,
            narrative=narrative,
        )

    def get_description(self) -> str:
        """Get mission description."""
        return (
            "The Funeral: Answer questions about events that have occurred in the game. "
            "Your memory and attention to detail will be tested."
        )
