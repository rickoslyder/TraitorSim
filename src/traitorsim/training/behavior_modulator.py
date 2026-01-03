"""Behavior modulator for TraitorSim agents.

Uses phase norms and personality traits to modulate agent behavior,
providing phase-appropriate guidance and behavioral constraints.
"""

import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from .training_data_loader import (
    TrainingDataLoader,
    get_training_data,
    OCEANTraits,
    RelationshipPattern,
)


@dataclass
class BehaviorGuidance:
    """Behavioral guidance for an agent in a specific context."""
    phase: str
    role: str
    personality_summary: str
    expected_behaviors: List[str]
    avoid_behaviors: List[str]
    relationship_context: List[str]
    strategic_considerations: List[str]
    emotional_baseline: str


@dataclass
class TrustUpdate:
    """Recommendation for updating trust/suspicion."""
    target_id: str
    target_name: str
    delta: float  # -0.3 to +0.3 typically
    reason: str
    confidence: float  # 0.0 - 1.0


class BehaviorModulator:
    """Modulates agent behavior based on training data and personality."""

    # Phase-to-behavior mode mapping
    PHASE_MODES = {
        "breakfast": "observation",
        "mission": "cooperation",
        "social": "alliance_building",
        "roundtable": "strategic_voting",
        "turret": "elimination",
    }

    # Personality-to-behavior mappings
    BEHAVIOR_TRAITS = {
        "aggressive_accusation": {
            "extraversion": 0.7,
            "agreeableness": -0.3,
            "neuroticism": 0.5,
        },
        "cautious_observation": {
            "conscientiousness": 0.7,
            "openness": 0.5,
            "neuroticism": 0.4,
        },
        "alliance_building": {
            "agreeableness": 0.7,
            "extraversion": 0.5,
        },
        "analytical_deduction": {
            "openness": 0.7,
            "conscientiousness": 0.6,
        },
        "emotional_appeal": {
            "agreeableness": 0.6,
            "neuroticism": 0.6,
            "extraversion": 0.5,
        },
        "defensive_deflection": {
            "neuroticism": 0.6,
            "conscientiousness": 0.4,
        },
    }

    def __init__(self, loader: Optional[TrainingDataLoader] = None):
        self.loader = loader or get_training_data()

    def get_phase_guidance(
        self,
        phase: str,
        role: str,
        personality: OCEANTraits,
        game_context: Optional[Dict] = None,
    ) -> BehaviorGuidance:
        """Get comprehensive behavioral guidance for the current phase.

        Args:
            phase: Current game phase
            role: "traitor" or "faithful"
            personality: Agent's OCEAN traits
            game_context: Optional dict with day, alive_players, suspicions, etc.

        Returns:
            BehaviorGuidance with detailed recommendations
        """
        # Get base phase norms from training data
        norms = self.loader.get_phase_norms(phase)
        phase_guidance = self.loader.get_phase_guidance(phase, role)

        # Get expected and avoid behaviors
        expected = self._get_expected_behaviors(phase, role, personality, norms)
        avoid = self._get_avoid_behaviors(phase, role, personality)

        # Get relationship context
        relationships = self._get_relationship_context(role, game_context)

        # Get strategic considerations
        strategic = self._get_strategic_considerations(phase, role, personality, game_context)

        # Determine emotional baseline
        emotional = self._get_emotional_baseline(personality, phase, game_context)

        # Personality summary
        personality_summary = self._summarize_personality(personality)

        return BehaviorGuidance(
            phase=phase,
            role=role,
            personality_summary=personality_summary,
            expected_behaviors=expected,
            avoid_behaviors=avoid,
            relationship_context=relationships,
            strategic_considerations=strategic,
            emotional_baseline=emotional,
        )

    def _get_expected_behaviors(
        self,
        phase: str,
        role: str,
        personality: OCEANTraits,
        norms: Optional[Dict],
    ) -> List[str]:
        """Get expected behaviors for the phase."""
        behaviors = []

        # Base phase behaviors
        phase_lower = phase.lower()
        role_lower = role.lower()

        if phase_lower == "breakfast":
            behaviors.append("Arrive and observe reactions to the murder reveal")
            behaviors.append("Note who seems genuinely shocked vs. performative")
            if role_lower == "traitor":
                behaviors.append("Display convincing grief - but not too much")
            else:
                behaviors.append("Watch for inconsistent emotional responses")

        elif phase_lower == "mission":
            behaviors.append("Participate actively in the challenge")
            if personality.conscientiousness >= 0.7:
                behaviors.append("Focus on doing your best for the team")
            if role_lower == "traitor" and personality.openness >= 0.6:
                behaviors.append("Consider strategic underperformance if safe")

        elif phase_lower == "social":
            if personality.extraversion >= 0.6:
                behaviors.append("Engage actively in group conversations")
            else:
                behaviors.append("Listen carefully and share selectively")

            if personality.agreeableness >= 0.6:
                behaviors.append("Build trust through genuine connection")
            else:
                behaviors.append("Maintain strategic distance")

            if role_lower == "traitor":
                behaviors.append("Cultivate relationships that provide cover")
            else:
                behaviors.append("Share suspicions carefully with trusted allies")

        elif phase_lower == "roundtable":
            behaviors.append("Contribute to the discussion - silence draws attention")

            if personality.extraversion >= 0.7:
                behaviors.append("Take an active role in directing conversation")
            else:
                behaviors.append("Make pointed observations when you speak")

            if role_lower == "traitor":
                behaviors.append("Vote with the majority when possible")
                behaviors.append("Deflect without being obvious about it")
            else:
                behaviors.append("Present evidence clearly and watch reactions")
                behaviors.append("Build consensus around strong suspects")

        elif phase_lower == "turret":
            if role_lower == "traitor":
                behaviors.append("Assess threat levels systematically")
                behaviors.append("Consider who suspects you most")
                behaviors.append("Think about chaos value - who would cause most disruption")

        # Add personality-specific behaviors
        if personality.neuroticism >= 0.7:
            behaviors.append("Be aware that anxiety may show - try to channel it productively")

        if personality.conscientiousness >= 0.7:
            behaviors.append("Keep mental notes organized for reference")

        return behaviors

    def _get_avoid_behaviors(
        self,
        phase: str,
        role: str,
        personality: OCEANTraits,
    ) -> List[str]:
        """Get behaviors to avoid for the phase."""
        avoid = []

        role_lower = role.lower()
        phase_lower = phase.lower()

        # Universal avoids
        avoid.append("Appearing too certain about anything without evidence")
        avoid.append("Isolating yourself from the group entirely")

        if role_lower == "traitor":
            avoid.append("Referencing information only Traitors would know")
            avoid.append("Being too quick to defend other Traitors")
            avoid.append("Showing relief when someone else is accused")
            avoid.append("Voting patterns that align perfectly with other Traitors")

        else:  # Faithful
            avoid.append("Tunnel vision on one suspect without considering alternatives")
            avoid.append("Blindly following the majority without your own analysis")
            avoid.append("Revealing your full suspicions to people you don't trust")

        # Phase-specific avoids
        if phase_lower == "breakfast":
            if role_lower == "traitor":
                avoid.append("Overacting grief or shock")
            avoid.append("Immediately accusing someone at breakfast")

        elif phase_lower == "roundtable":
            avoid.append("Staying completely silent throughout")
            if role_lower == "traitor":
                avoid.append("Being the first to accuse a fellow Traitor")
            else:
                avoid.append("Changing your vote at the last second without reason")

        elif phase_lower == "mission":
            avoid.append("Appearing to deliberately sabotage (unless strategic)")
            avoid.append("Blaming others for your own mistakes")

        # Personality-specific avoids
        if personality.neuroticism >= 0.7:
            avoid.append("Letting visible anxiety make you a target")

        if personality.extraversion >= 0.8:
            avoid.append("Dominating conversation so much that others resent it")

        if personality.agreeableness >= 0.8:
            avoid.append("Being too trusting of everyone")

        return avoid

    def _get_relationship_context(
        self,
        role: str,
        game_context: Optional[Dict],
    ) -> List[str]:
        """Get relationship context for behavior guidance."""
        context = []

        # Get relationship patterns from training data
        alliances = self.loader.get_relationship_patterns("alliance")
        rivalries = self.loader.get_relationship_patterns("rivalry")

        if alliances:
            sample = random.choice(alliances)
            context.append(
                f"Alliances can form quickly - like {sample.players[0]} and {sample.players[1]} "
                f"who bonded through {sample.evolution[:50]}..."
            )

        if rivalries:
            sample = random.choice(rivalries)
            context.append(
                f"Rivalries can emerge from accusations - watch for dynamics like "
                f"{sample.players[0]} vs {sample.players[1]}"
            )

        # Role-specific relationship advice
        if role.lower() == "traitor":
            context.append(
                "Build genuine-seeming friendships with Faithfuls who can vouch for you"
            )
            context.append(
                "Maintain plausible distance from fellow Traitors in public"
            )
        else:
            context.append(
                "Trust is valuable but dangerous - verify before committing"
            )
            context.append(
                "Small alliances can help you survive Round Tables"
            )

        return context

    def _get_strategic_considerations(
        self,
        phase: str,
        role: str,
        personality: OCEANTraits,
        game_context: Optional[Dict],
    ) -> List[str]:
        """Get strategic considerations for the phase."""
        considerations = []

        day = game_context.get("day", 1) if game_context else 1
        alive_count = game_context.get("alive_count", 20) if game_context else 20

        # Early game vs late game
        if day <= 3:
            considerations.append(
                "Early game: Focus on building relationships and gathering information"
            )
            considerations.append(
                "Avoid making yourself a target before you've established trust"
            )
        elif day >= 8 or alive_count <= 6:
            considerations.append(
                "Late game: Every decision matters more. Be decisive."
            )
            considerations.append(
                "The endgame is approaching - position yourself for the final votes"
            )
        else:
            considerations.append(
                "Mid game: Patterns are emerging. Use your observations."
            )

        # Role-specific strategic considerations
        if role.lower() == "traitor":
            if phase.lower() == "roundtable":
                considerations.append(
                    "Consider who would be a useful 'useful idiot' to keep alive"
                )
                considerations.append(
                    "Voting for a Faithful who's already under suspicion is safe cover"
                )
            elif phase.lower() == "turret":
                considerations.append(
                    "Eliminating vocal accusers removes threats"
                )
                considerations.append(
                    "Eliminating popular players creates chaos and grief"
                )
                considerations.append(
                    "Consider preserving 'useful idiots' who defend you"
                )
        else:
            if phase.lower() == "roundtable":
                considerations.append(
                    "Look for voting pattern clusters - Traitors often vote similarly"
                )
                considerations.append(
                    "Who benefits most from each banishment?"
                )

        # Personality-modulated considerations
        if personality.openness >= 0.7:
            considerations.append(
                "Your analytical mind is an asset - trust your pattern recognition"
            )

        if personality.agreeableness <= 0.4:
            considerations.append(
                "Your directness can be polarizing - use it strategically"
            )

        return considerations

    def _get_emotional_baseline(
        self,
        personality: OCEANTraits,
        phase: str,
        game_context: Optional[Dict],
    ) -> str:
        """Determine emotional baseline for the agent."""
        components = []

        # Neuroticism determines baseline anxiety
        if personality.neuroticism >= 0.7:
            components.append("anxious and hypervigilant")
        elif personality.neuroticism <= 0.3:
            components.append("calm and composed")
        else:
            components.append("appropriately tense")

        # Extraversion determines energy level
        if personality.extraversion >= 0.7:
            components.append("energetic and engaged")
        elif personality.extraversion <= 0.3:
            components.append("reserved and observant")
        else:
            components.append("moderately engaged")

        # Phase affects emotional state
        phase_emotions = {
            "breakfast": "anticipating the murder reveal",
            "mission": "focused on the challenge",
            "social": "navigating social dynamics",
            "roundtable": "managing the tension of voting",
            "turret": "contemplating the night's decision",
        }
        phase_emotion = phase_emotions.get(phase.lower(), "processing the game")
        components.append(phase_emotion)

        return ", ".join(components)

    def _summarize_personality(self, personality: OCEANTraits) -> str:
        """Create a brief personality summary."""
        dominant = personality.dominant_traits()
        weak = personality.weak_traits()

        parts = []
        if dominant:
            trait_labels = {
                "openness": "intellectually curious",
                "conscientiousness": "methodical and organized",
                "extraversion": "outgoing and vocal",
                "agreeableness": "cooperative and trusting",
                "neuroticism": "anxious and reactive",
            }
            dominant_labels = [trait_labels.get(t, t) for t in dominant]
            parts.append(f"Strong tendencies: {', '.join(dominant_labels)}")

        if weak:
            trait_labels = {
                "openness": "conventional thinker",
                "conscientiousness": "spontaneous and flexible",
                "extraversion": "quiet and reserved",
                "agreeableness": "direct and skeptical",
                "neuroticism": "emotionally stable",
            }
            weak_labels = [trait_labels.get(t, t) for t in weak]
            parts.append(f"Also: {', '.join(weak_labels)}")

        return "; ".join(parts) if parts else "Balanced personality profile"

    def suggest_trust_updates(
        self,
        observer_role: str,
        observer_personality: OCEANTraits,
        events: List[Dict],
        current_suspicions: Dict[str, float],
    ) -> List[TrustUpdate]:
        """Suggest trust matrix updates based on observed events.

        Args:
            observer_role: "traitor" or "faithful"
            observer_personality: Observer's personality
            events: List of events with {type, players, details}
            current_suspicions: Current suspicion scores {player_id: score}

        Returns:
            List of TrustUpdate recommendations
        """
        updates = []

        for event in events:
            event_type = event.get("type", "")
            players = event.get("players", [])
            details = event.get("details", {})

            if event_type == "vote_cast":
                voter_id = details.get("voter_id")
                target_id = details.get("target_id")
                target_revealed = details.get("target_revealed_as")

                if target_revealed == "traitor":
                    # Voting for revealed Traitor increases trust in voter
                    updates.append(TrustUpdate(
                        target_id=voter_id,
                        target_name=details.get("voter_name", "Unknown"),
                        delta=-0.1,  # Less suspicious
                        reason=f"Voted correctly for revealed Traitor",
                        confidence=0.7,
                    ))
                elif target_revealed == "faithful":
                    # Voting for revealed Faithful - suspicious but common
                    base_delta = 0.05
                    if observer_personality.neuroticism >= 0.7:
                        base_delta = 0.08  # More paranoid
                    updates.append(TrustUpdate(
                        target_id=voter_id,
                        target_name=details.get("voter_name", "Unknown"),
                        delta=base_delta,
                        reason=f"Voted for innocent Faithful",
                        confidence=0.4,
                    ))

            elif event_type == "accusation":
                accuser_id = details.get("accuser_id")
                accused_id = details.get("accused_id")

                # Accusations are noisy signals
                if observer_personality.openness >= 0.7:
                    # Analytical - consider both sides
                    updates.append(TrustUpdate(
                        target_id=accused_id,
                        target_name=details.get("accused_name", "Unknown"),
                        delta=0.03,
                        reason=f"Accused by another player",
                        confidence=0.3,
                    ))
                else:
                    # More likely to trust the accuser
                    updates.append(TrustUpdate(
                        target_id=accused_id,
                        target_name=details.get("accused_name", "Unknown"),
                        delta=0.05,
                        reason=f"Accused by another player",
                        confidence=0.4,
                    ))

            elif event_type == "mission_failure":
                participants = details.get("participants", [])
                for p_id in participants:
                    # Slight increase in suspicion for mission participants
                    delta = 0.02
                    if observer_personality.conscientiousness >= 0.7:
                        delta = 0.03  # More likely to blame
                    updates.append(TrustUpdate(
                        target_id=p_id,
                        target_name=details.get("participant_names", {}).get(p_id, "Unknown"),
                        delta=delta,
                        reason="Participated in failed mission",
                        confidence=0.3,
                    ))

            elif event_type == "defense":
                defender_id = details.get("defender_id")
                defended_id = details.get("defended_id")

                if observer_role.lower() == "faithful":
                    # Defending someone links their fates
                    updates.append(TrustUpdate(
                        target_id=defender_id,
                        target_name=details.get("defender_name", "Unknown"),
                        delta=0.02,  # Slightly more suspicious of defender
                        reason=f"Defended someone (link established)",
                        confidence=0.3,
                    ))

        return updates

    def modulate_decision(
        self,
        base_decision: str,
        personality: OCEANTraits,
        stress_level: float = 0.5,
    ) -> Tuple[str, str]:
        """Modulate a base decision based on personality and stress.

        Args:
            base_decision: The analytically optimal decision
            personality: Agent's personality
            stress_level: Current stress (0.0 - 1.0)

        Returns:
            Tuple of (final_decision, reasoning)
        """
        # High neuroticism + high stress = more likely to change decision
        change_probability = personality.neuroticism * stress_level * 0.3

        if random.random() < change_probability:
            return (
                f"{base_decision} (with hesitation)",
                "High stress is affecting your judgment"
            )

        # Low agreeableness = more likely to go against group
        if personality.agreeableness <= 0.3 and random.random() < 0.2:
            return (
                f"{base_decision} (contrarian)",
                "Your independent nature makes you question the group"
            )

        return (base_decision, "Decision made based on analysis")


# Convenience function
def get_behavior_modulator() -> BehaviorModulator:
    """Get a behavior modulator instance."""
    return BehaviorModulator()
