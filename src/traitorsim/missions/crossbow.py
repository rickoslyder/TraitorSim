"""Crossbow Challenge - Revealed preference mission.

Players aim at targets representing other contestants.
Who they choose to "hit" reveals grudges and alliances.
"""

import random
from typing import Dict, List, Tuple
from .base import BaseMission, MissionResult


class CrossbowMission(BaseMission):
    """Accuracy-based mission that reveals player preferences and grudges.

    Each player aims a crossbow at targets representing other players.
    Performance is based on:
    - Dexterity: Accuracy with the crossbow
    - Agreeableness (inverse): Willingness to target others
    - Social Influence: Understanding group dynamics

    Target selection reveals:
    - Who players are suspicious of (they target threats)
    - Alliance patterns (who they avoid targeting)
    - Traitor coordination (traitors may coordinate targets)

    This mission creates observable data for trust matrix updates.
    """

    def execute(self) -> MissionResult:
        """Execute the Crossbow Challenge mission.

        Mechanics:
        1. Each player performs based on dexterity
        2. Each player selects a target (reveals preferences)
        3. Target patterns update trust observations
        """
        alive = list(self.game_state.alive_players)
        base_reward = self.config.mission_base_reward
        difficulty = self.config.mission_difficulty

        performance_scores: Dict[str, float] = {}
        target_selections: Dict[str, str] = {}  # shooter -> target

        from ..core.game_state import Role

        # Phase 1: Determine targets and accuracy for each player
        for player in alive:
            dexterity = player.stats.get("dexterity", 0.5)
            social_influence = player.stats.get("social_influence", 0.5)
            agreeableness = player.personality.get("agreeableness", 0.5)

            # Accuracy based on dexterity
            base_accuracy = dexterity * (1 - difficulty * 0.4)

            # Less agreeable players are more willing to aim well
            aggression_bonus = (1 - agreeableness) * 0.15
            base_accuracy = min(1.0, base_accuracy + aggression_bonus)

            # Target selection based on suspicion and personality
            target_id = self._select_target(player, alive)
            target_selections[player.id] = target_id

            # Add randomness
            random_factor = random.uniform(0.8, 1.2)
            performance = base_accuracy * random_factor

            # Clamp
            performance = max(0.0, min(1.0, performance))
            performance_scores[player.id] = round(performance, 2)

        # Phase 2: Analyze target patterns for trust updates
        self._analyze_targeting_patterns(target_selections, alive)

        # Calculate earnings
        total_successes = sum(1 for s in performance_scores.values() if s >= 0.5)
        avg_performance = sum(performance_scores.values()) / len(alive) if alive else 0
        earnings = base_reward * avg_performance

        # Count who got targeted most
        target_counts: Dict[str, int] = {}
        for target_id in target_selections.values():
            target_counts[target_id] = target_counts.get(target_id, 0) + 1

        most_targeted_id = max(target_counts.items(), key=lambda x: x[1])[0] if target_counts else None
        most_targeted = self.game_state.get_player(most_targeted_id) if most_targeted_id else None
        most_targeted_name = most_targeted.name if most_targeted else "Someone"
        most_targeted_count = target_counts.get(most_targeted_id, 0) if most_targeted_id else 0

        # Best shooter
        best_performer = max(performance_scores.items(), key=lambda x: x[1])
        best_player = self.game_state.get_player(best_performer[0])
        best_name = best_player.name if best_player else "Someone"

        narrative = (
            f"Arrows flew across the range as contestants took aim. "
            f"{total_successes}/{len(alive)} hit their marks with precision. "
            f"{best_name} proved the sharpest shooter (score: {best_performer[1]:.0%}). "
            f"{most_targeted_name} was the most popular target with {most_targeted_count} arrows. "
            f"${earnings:,.0f} added to the prize pot."
        )

        return MissionResult(
            success=(avg_performance >= 0.5),
            earnings=earnings,
            performance_scores=performance_scores,
            narrative=narrative,
        )

    def _select_target(self, shooter, alive_players) -> str:
        """Select who the shooter aims at.

        Selection based on:
        - Suspicion (high suspicion = more likely target)
        - Personality (agreeable people avoid friends)
        - Random variance

        Args:
            shooter: Player doing the shooting
            alive_players: List of all alive players

        Returns:
            Player ID of the target
        """
        from ..core.game_state import Role

        valid_targets = [p for p in alive_players if p.id != shooter.id]
        if not valid_targets:
            return shooter.id  # Shouldn't happen, but fallback

        # Get shooter's suspicions
        target_weights: Dict[str, float] = {}

        for target in valid_targets:
            weight = 0.5  # Base weight

            # Traitors avoid targeting each other
            if shooter.role == Role.TRAITOR and target.role == Role.TRAITOR:
                weight *= 0.3  # Much less likely

            # Use trust matrix if available
            if hasattr(self.game_state, 'trust_matrix') and self.game_state.trust_matrix:
                suspicion = self.game_state.trust_matrix.get_suspicion(shooter.id, target.id)
                # Higher suspicion = more likely to target
                weight += suspicion * 0.5

            # Social influence of target (less likely to target popular people)
            target_influence = target.stats.get("social_influence", 0.5)
            weight -= target_influence * 0.2

            # Shooter's agreeableness affects targeting
            shooter_agreeableness = shooter.personality.get("agreeableness", 0.5)
            if shooter_agreeableness > 0.6:
                # Agreeable shooters are more random (don't want to offend)
                weight = 0.5 + (weight - 0.5) * 0.5

            target_weights[target.id] = max(0.1, weight)

        # Weighted random selection
        total_weight = sum(target_weights.values())
        r = random.random() * total_weight
        cumulative = 0

        for target_id, weight in target_weights.items():
            cumulative += weight
            if r <= cumulative:
                return target_id

        # Fallback to random
        return random.choice(valid_targets).id

    def _analyze_targeting_patterns(self, target_selections: Dict[str, str], alive_players) -> None:
        """Analyze targeting patterns for trust updates.

        If multiple Traitors all avoid targeting each other, that's suspicious.
        If someone is targeted by many, they might be perceived as a threat.

        Args:
            target_selections: Dict of shooter_id -> target_id
            alive_players: List of alive players
        """
        from ..core.game_state import Role

        # Check for Traitor coordination (all traitors avoiding each other)
        traitors = [p for p in alive_players if p.role == Role.TRAITOR]
        traitor_ids = {t.id for t in traitors}

        if len(traitors) >= 2:
            traitor_targets = {target_selections.get(t.id) for t in traitors}

            # If no traitor targeted another traitor, observant players notice
            if len(traitor_targets & traitor_ids) == 0:
                # This is suspicious coordination
                for observer in alive_players:
                    if observer.id in traitor_ids:
                        continue

                    # Only very observant players notice
                    openness = observer.personality.get("openness", 0.5)
                    conscientiousness = observer.personality.get("conscientiousness", 0.5)

                    if random.random() < (openness + conscientiousness) * 0.1:
                        # Small suspicion increase for all traitors
                        if hasattr(self.game_state, 'trust_matrix') and self.game_state.trust_matrix:
                            for traitor in traitors:
                                current = self.game_state.trust_matrix.get_suspicion(
                                    observer.id, traitor.id
                                )
                                # Very small increase - subtle pattern
                                new_suspicion = min(1.0, current + 0.03)
                                self.game_state.trust_matrix.update_suspicion(
                                    observer.id, traitor.id, new_suspicion
                                )

    def get_description(self) -> str:
        """Get mission description."""
        return (
            "Crossbow Challenge: Take aim at targets representing your fellow players. "
            "Your accuracy will be tested - but so will your loyalties. "
            "Who will you choose to hit?"
        )
