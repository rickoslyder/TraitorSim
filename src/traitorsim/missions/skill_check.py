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
        alive = self.game_state.alive_players
        base_reward = self.config.mission_base_reward
        difficulty = self.config.mission_difficulty

        total_successes = 0
        performance_scores = {}

        for player in alive:
            # Calculate success chance based on intellect
            intellect = player.stats.get("intellect", 0.5)
            # Success chance = intellect * (1 - difficulty)
            # So higher difficulty makes it harder
            success_chance = intellect * (1 - difficulty)

            # Roll for success
            success = random.random() < success_chance
            performance_scores[player.id] = 1.0 if success else 0.0

            if success:
                total_successes += 1

        # Calculate earnings (proportional to success rate)
        success_rate = total_successes / len(alive) if alive else 0
        earnings = base_reward * success_rate

        # Generate narrative
        narrative = (
            f"The team tackled a series of puzzles. "
            f"{total_successes}/{len(alive)} players succeeded. "
            f"${earnings:,.0f} added to the prize pot!"
        )

        return MissionResult(
            success=(success_rate >= 0.5),
            earnings=earnings,
            performance_scores=performance_scores,
            narrative=narrative,
        )

    def get_description(self) -> str:
        """Get mission description."""
        return "Solve a series of puzzles to add money to the prize pot."
