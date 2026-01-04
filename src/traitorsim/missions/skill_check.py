"""Simple skill check mission for MVP."""

import random
from .base import BaseMission, MissionResult


class SkillCheckMission(BaseMission):
    """
    Simple intellect-based skill check mission.
    Each player makes an intellect check. Success rate determines prize pot earnings.
    """

    def execute(self) -> MissionResult:
        """Execute the skill check mission."""
        alive = list(self.game_state.alive_players)
        base_reward = self.config.mission_base_reward
        difficulty = self.config.mission_difficulty

        total_successes = 0
        performance_scores = {}

        for player in alive:
            # Get player's intellect stat (default 0.5)
            intellect = player.stats.get("intellect", 0.5)

            # Calculate performance as a spectrum (not binary)
            # Base performance influenced by intellect and difficulty
            # Formula: performance = intellect * (1 - difficulty/2) * random_factor
            # This gives a range roughly 0.2-1.0 for average players
            base_performance = intellect * (1 - difficulty * 0.5)

            # Add randomness: +/- 30% variance
            random_factor = random.uniform(0.7, 1.3)
            performance = base_performance * random_factor

            # Clamp to valid range [0.0, 1.0]
            performance = max(0.0, min(1.0, performance))

            # Round to 2 decimal places for cleaner display
            performance_scores[player.id] = round(performance, 2)

            # Count as "success" if performance >= 0.5
            if performance >= 0.5:
                total_successes += 1

        # Calculate earnings based on average performance (not just success count)
        avg_performance = sum(performance_scores.values()) / len(alive) if alive else 0
        earnings = base_reward * avg_performance

        # Generate narrative
        narrative = (
            f"The team tackled a series of puzzles. "
            f"{total_successes}/{len(alive)} players succeeded (avg score: {avg_performance:.1%}). "
            f"${earnings:,.0f} added to the prize pot!"
        )

        return MissionResult(
            success=(avg_performance >= 0.5),
            earnings=earnings,
            performance_scores=performance_scores,
            narrative=narrative,
        )

    def get_description(self) -> str:
        """Get mission description."""
        return "Solve a series of puzzles to add money to the prize pot."
