"""Cabin Creepies - Fear and willpower mission.

Players face frightening scenarios testing their composure.
High neuroticism players struggle, but Traitors may fake fear to blend in.
"""

import random
from typing import Dict, List
from .base import BaseMission, MissionResult


class CabinCreepiesMission(BaseMission):
    """Fear-based mission testing composure under pressure.

    Each player faces scary scenarios. Performance is based on:
    - Neuroticism (inverse): Low neuroticism = better composure
    - Extraversion: Outgoing players may perform for the group
    - Conscientiousness: Dedication to pushing through fear

    Traitors may intentionally act scared to seem more "human" and
    avoid suspicion from being too calm.

    This mission can reveal personality tells - players who seem
    unusually composed might be concealing something.
    """

    def execute(self) -> MissionResult:
        """Execute the Cabin Creepies mission.

        Mechanics:
        1. Each player performs based on composure (inverse neuroticism)
        2. Traitors may fake fear to blend in
        3. Unusually calm players may draw suspicion
        """
        alive = list(self.game_state.alive_players)
        base_reward = self.config.mission_base_reward
        difficulty = self.config.mission_difficulty

        performance_scores: Dict[str, float] = {}
        suspiciously_calm: List[str] = []

        from ..core.game_state import Role

        # Track who seems "too calm"
        calm_threshold = 0.85

        for player in alive:
            # Composure is inverse of neuroticism
            neuroticism = player.personality.get("neuroticism", 0.5)
            composure = 1.0 - neuroticism

            extraversion = player.personality.get("extraversion", 0.5)
            conscientiousness = player.personality.get("conscientiousness", 0.5)

            # Base performance: composure + determination
            base_performance = composure * 0.7 + conscientiousness * 0.3

            # Extraverts may "perform" better (showing off courage)
            if extraversion > 0.6:
                base_performance *= (1 + extraversion * 0.1)

            # Apply difficulty
            base_performance *= (1 - difficulty * 0.3)

            # Traitor faking behavior
            if player.role == Role.TRAITOR:
                agreeableness = player.personality.get("agreeableness", 0.5)

                # Traitors with high agreeableness may fake fear to blend in
                if agreeableness > 0.5 and random.random() < agreeableness * 0.5:
                    # Fake moderate fear (not too scared, not too calm)
                    base_performance = random.uniform(0.4, 0.6)
                elif composure > 0.7:
                    # Very calm traitor - might draw suspicion
                    pass  # Keep high performance

            # Add natural variance
            random_factor = random.uniform(0.8, 1.2)
            performance = base_performance * random_factor

            # Clamp
            performance = max(0.0, min(1.0, performance))
            performance_scores[player.id] = round(performance, 2)

            # Track suspiciously calm players
            if performance >= calm_threshold:
                suspiciously_calm.append(player.id)

        # Players who seem TOO calm might draw subtle suspicion
        # This doesn't update trust directly but provides observables
        for calm_player_id in suspiciously_calm:
            calm_player = self.game_state.get_player(calm_player_id)
            if not calm_player:
                continue

            # Other players might notice
            for observer in alive:
                if observer.id == calm_player_id:
                    continue

                # Observant players (high openness, low agreeableness) notice
                openness = observer.personality.get("openness", 0.5)
                agreeableness = observer.personality.get("agreeableness", 0.5)

                notice_chance = openness * 0.3 - agreeableness * 0.1
                if random.random() < notice_chance:
                    # Slight suspicion increase
                    if hasattr(self.game_state, 'trust_matrix') and self.game_state.trust_matrix:
                        current = self.game_state.trust_matrix.get_suspicion(
                            observer.id, calm_player_id
                        )
                        new_suspicion = min(1.0, current + 0.05)
                        self.game_state.trust_matrix.update_suspicion(
                            observer.id, calm_player_id, new_suspicion
                        )

        # Calculate earnings
        total_successes = sum(1 for s in performance_scores.values() if s >= 0.5)
        avg_performance = sum(performance_scores.values()) / len(alive) if alive else 0
        earnings = base_reward * avg_performance

        # Find the most and least composed
        performances_sorted = sorted(performance_scores.items(), key=lambda x: x[1])
        most_scared = self.game_state.get_player(performances_sorted[0][0])
        most_calm = self.game_state.get_player(performances_sorted[-1][0])

        scared_name = most_scared.name if most_scared else "Someone"
        calm_name = most_calm.name if most_calm else "Someone"

        narrative_parts = [
            f"The contestants explored a haunted cabin filled with horrors. ",
            f"{total_successes}/{len(alive)} kept their composure. ",
            f"{scared_name} screamed the loudest, while {calm_name} barely flinched. ",
        ]

        if len(suspiciously_calm) > 1:
            narrative_parts.append(
                "Some wondered how certain players stayed so eerily calm... "
            )

        narrative_parts.append(f"${earnings:,.0f} added to the prize pot.")

        return MissionResult(
            success=(avg_performance >= 0.5),
            earnings=earnings,
            performance_scores=performance_scores,
            narrative="".join(narrative_parts),
        )

    def get_description(self) -> str:
        """Get mission description."""
        return (
            "Cabin Creepies: Face your fears in a haunted cabin. "
            "Those who keep their composure will be rewarded. "
            "But is anyone a little TOO calm?"
        )
