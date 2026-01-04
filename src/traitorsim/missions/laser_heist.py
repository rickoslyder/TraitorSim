"""Laser Heist - Dexterity and risk mission with sabotage detection.

Players navigate a laser maze to collect treasure. Traitors may sabotage
but risk detection by observant Faithfuls.
"""

import random
from typing import Dict, List, Optional, Tuple
from .base import BaseMission, MissionResult


class LaserHeistMission(BaseMission):
    """Dexterity-based heist mission with sabotage mechanics.

    Each player navigates a laser maze. Performance is based on:
    - Dexterity: Physical precision
    - Conscientiousness: Careful planning
    - Intellect: Reading the maze patterns

    Traitors can choose to sabotage (intentionally fail) but risk detection
    by observant players with high conscientiousness.

    This mission creates opportunities for trust updates based on performance.
    """

    def execute(self) -> MissionResult:
        """Execute the Laser Heist mission.

        Mechanics:
        1. Each player performs based on dexterity * conscientiousness
        2. Traitors may sabotage (intentional poor performance)
        3. Observers can detect sabotage vs clumsiness
        4. Detected sabotage increases trust matrix suspicion
        """
        alive = list(self.game_state.alive_players)
        base_reward = self.config.mission_base_reward
        difficulty = self.config.mission_difficulty

        performance_scores: Dict[str, float] = {}
        sabotage_attempts: List[str] = []
        detected_sabotage: List[Tuple[str, str]] = []  # (saboteur, detector)

        from ..core.game_state import Role

        # Phase 1: Calculate individual performances
        for player in alive:
            dexterity = player.stats.get("dexterity", 0.5)
            conscientiousness = player.personality.get("conscientiousness", 0.5)
            intellect = player.stats.get("intellect", 0.5)

            # Base performance: dexterity + planning
            base_performance = dexterity * (0.6 + 0.4 * conscientiousness)
            base_performance *= (1 - difficulty * 0.5)

            # Intellect bonus for reading patterns
            intellect_bonus = intellect * 0.15
            base_performance = min(1.0, base_performance + intellect_bonus)

            # Traitor sabotage decision
            is_sabotaging = False
            if player.role == Role.TRAITOR:
                # Higher neuroticism = more likely to sabotage (nervous energy)
                neuroticism = player.personality.get("neuroticism", 0.5)
                agreeableness = player.personality.get("agreeableness", 0.5)

                # Sabotage probability based on personality
                sabotage_chance = 0.3 + (neuroticism * 0.2) - (agreeableness * 0.15)
                if random.random() < sabotage_chance:
                    is_sabotaging = True
                    sabotage_attempts.append(player.id)
                    # Sabotaged performance looks like failure
                    base_performance = random.uniform(0.1, 0.35)

            # Add natural variance
            random_factor = random.uniform(0.8, 1.2)
            performance = base_performance * random_factor

            # Clamp
            performance = max(0.0, min(1.0, performance))
            performance_scores[player.id] = round(performance, 2)

        # Phase 2: Sabotage detection
        # Observant players (high conscientiousness) may detect sabotage
        for saboteur_id in sabotage_attempts:
            saboteur = self.game_state.get_player(saboteur_id)
            if not saboteur:
                continue

            for observer in alive:
                if observer.id == saboteur_id:
                    continue

                # Detection based on observer's conscientiousness and intellect
                observer_conscientiousness = observer.personality.get("conscientiousness", 0.5)
                observer_intellect = observer.stats.get("intellect", 0.5)

                # Saboteur's extraversion makes them harder to detect (good poker face)
                saboteur_extraversion = saboteur.personality.get("extraversion", 0.5)

                detection_chance = (
                    (observer_conscientiousness * 0.5 + observer_intellect * 0.3)
                    - (saboteur_extraversion * 0.2)
                )

                if random.random() < detection_chance * 0.5:  # 50% base cap
                    detected_sabotage.append((saboteur_id, observer.id))
                    # Update trust matrix if available
                    if hasattr(self.game_state, 'trust_matrix') and self.game_state.trust_matrix:
                        current = self.game_state.trust_matrix.get_suspicion(observer.id, saboteur_id)
                        new_suspicion = min(1.0, current + 0.15)
                        self.game_state.trust_matrix.update_suspicion(
                            observer.id, saboteur_id, new_suspicion
                        )
                    break  # Only count one detection per saboteur

        # Calculate earnings
        total_successes = sum(1 for s in performance_scores.values() if s >= 0.5)
        avg_performance = sum(performance_scores.values()) / len(alive) if alive else 0

        # Sabotage reduces overall earnings
        sabotage_penalty = len(sabotage_attempts) * 0.05
        adjusted_performance = max(0.0, avg_performance - sabotage_penalty)
        earnings = base_reward * adjusted_performance

        # Generate narrative
        best_performer = max(performance_scores.items(), key=lambda x: x[1])
        best_player = self.game_state.get_player(best_performer[0])
        best_name = best_player.name if best_player else "Someone"

        narrative_parts = [
            f"The contestants navigated a deadly laser maze. ",
            f"{total_successes}/{len(alive)} made it through successfully. ",
            f"{best_name} showed exceptional agility (score: {best_performer[1]:.0%}). ",
        ]

        if detected_sabotage:
            narrative_parts.append(
                f"Some players noticed suspicious stumbles... "
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
            "Laser Heist: Navigate through a maze of laser beams to retrieve "
            "treasure. Precision and careful planning are key. "
            "Watch for those who stumble too conveniently..."
        )
