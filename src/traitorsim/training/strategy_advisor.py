"""Strategy advisor for TraitorSim agents.

Uses training data to recommend strategies based on:
- Role (traitor/faithful)
- Current game phase
- Personality traits
- Game state context
"""

import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .training_data_loader import (
    TrainingDataLoader,
    get_training_data,
    Strategy,
    OCEANTraits,
)


@dataclass
class StrategyRecommendation:
    """A strategy recommendation with context."""
    strategy: Strategy
    score: float
    reasoning: str
    personality_fit: Dict[str, str]  # trait -> how it aligns
    example_application: str


class StrategyAdvisor:
    """Provides strategic guidance to agents based on training data."""

    # Phase-specific strategy weights
    PHASE_PRIORITIES = {
        "breakfast": {
            "observation": 1.5,
            "reaction": 1.3,
            "suspicion": 1.2,
        },
        "mission": {
            "cooperation": 1.5,
            "sabotage": 1.3,
            "performance": 1.2,
        },
        "social": {
            "alliance": 1.5,
            "information": 1.3,
            "trust_building": 1.2,
        },
        "roundtable": {
            "voting": 1.5,
            "defense": 1.4,
            "accusation": 1.3,
        },
        "turret": {
            "murder": 1.5,
            "recruitment": 1.3,
        },
    }

    def __init__(self, loader: Optional[TrainingDataLoader] = None):
        self.loader = loader or get_training_data()

    def get_recommendations(
        self,
        role: str,
        phase: str,
        personality: OCEANTraits,
        game_context: Optional[Dict] = None,
        top_k: int = 3,
    ) -> List[StrategyRecommendation]:
        """Get strategy recommendations for the current context.

        Args:
            role: "traitor" or "faithful"
            phase: Current game phase
            personality: Agent's OCEAN personality traits
            game_context: Optional dict with day, alive_count, suspicion_on_me, etc.
            top_k: Maximum recommendations to return

        Returns:
            List of StrategyRecommendation sorted by score
        """
        strategies = self.loader.get_strategies_for_context(role, phase, top_k=10)

        if not strategies:
            return []

        recommendations = []
        for strategy in strategies:
            score, personality_fit = self._score_strategy(
                strategy, personality, phase, game_context
            )
            reasoning = self._generate_reasoning(strategy, personality, phase, score)
            example = self._generate_example(strategy, role, phase)

            recommendations.append(StrategyRecommendation(
                strategy=strategy,
                score=score,
                reasoning=reasoning,
                personality_fit=personality_fit,
                example_application=example,
            ))

        # Sort by score descending
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]

    def _score_strategy(
        self,
        strategy: Strategy,
        personality: OCEANTraits,
        phase: str,
        game_context: Optional[Dict],
    ) -> Tuple[float, Dict[str, str]]:
        """Score a strategy based on personality and context.

        Returns:
            Tuple of (score, personality_fit_explanations)
        """
        score = strategy.effectiveness
        personality_fit = {}

        desc_lower = strategy.description.lower()
        name_lower = strategy.name.lower()

        # ─────────────────────────────────────────────────────────────────────
        # Personality-based adjustments
        # ─────────────────────────────────────────────────────────────────────

        # Extraversion affects aggressive/vocal strategies
        if any(kw in desc_lower for kw in ["aggressive", "vocal", "dominant", "confront"]):
            if personality.extraversion >= 0.7:
                score += 0.15
                personality_fit["extraversion"] = "High extraversion suits your confrontational style"
            elif personality.extraversion <= 0.3:
                score -= 0.15
                personality_fit["extraversion"] = "Low extraversion may make this strategy feel unnatural"

        # Agreeableness affects alliance/cooperation strategies
        if any(kw in desc_lower for kw in ["alliance", "trust", "cooperat", "friend", "loyal"]):
            if personality.agreeableness >= 0.7:
                score += 0.15
                personality_fit["agreeableness"] = "High agreeableness helps build genuine trust"
            elif personality.agreeableness <= 0.3:
                score -= 0.1
                personality_fit["agreeableness"] = "Low agreeableness may make trust-building harder"

        # Conscientiousness affects methodical/analytical strategies
        if any(kw in desc_lower for kw in ["methodical", "systematic", "analytical", "logical", "evidence"]):
            if personality.conscientiousness >= 0.7:
                score += 0.15
                personality_fit["conscientiousness"] = "High conscientiousness supports systematic analysis"
            elif personality.conscientiousness <= 0.3:
                score -= 0.1
                personality_fit["conscientiousness"] = "Low conscientiousness may make this feel tedious"

        # Neuroticism affects defensive/paranoid strategies
        if any(kw in desc_lower for kw in ["paranoid", "defensive", "suspicious", "vigilant"]):
            if personality.neuroticism >= 0.7:
                score += 0.1
                personality_fit["neuroticism"] = "High neuroticism naturally aligns with vigilant behavior"
            # Note: Low neuroticism doesn't penalize - calm players can still be strategic

        # Openness affects creative/unconventional strategies
        if any(kw in desc_lower for kw in ["creative", "unconventional", "bluff", "misdirect", "unexpected"]):
            if personality.openness >= 0.7:
                score += 0.15
                personality_fit["openness"] = "High openness enables creative misdirection"
            elif personality.openness <= 0.3:
                score -= 0.1
                personality_fit["openness"] = "Low openness prefers conventional approaches"

        # ─────────────────────────────────────────────────────────────────────
        # Phase-specific adjustments
        # ─────────────────────────────────────────────────────────────────────

        phase_priorities = self.PHASE_PRIORITIES.get(phase.lower(), {})
        for keyword, weight in phase_priorities.items():
            if keyword in name_lower or keyword in desc_lower:
                score *= weight

        # ─────────────────────────────────────────────────────────────────────
        # Game context adjustments
        # ─────────────────────────────────────────────────────────────────────

        if game_context:
            day = game_context.get("day", 1)
            alive_count = game_context.get("alive_count", 20)
            suspicion_on_me = game_context.get("suspicion_on_me", 0.3)

            # Late game adjustments
            if day >= 8 and alive_count <= 6:
                if "endgame" in desc_lower or "final" in desc_lower:
                    score += 0.2

            # Under suspicion adjustments
            if suspicion_on_me >= 0.6:
                if any(kw in desc_lower for kw in ["defense", "deflect", "redirect", "innocent"]):
                    score += 0.2

            # Low suspicion - can be more aggressive
            if suspicion_on_me <= 0.3:
                if any(kw in desc_lower for kw in ["aggressive", "accusation", "proactive"]):
                    score += 0.1

        return max(0.0, min(1.0, score)), personality_fit

    def _generate_reasoning(
        self,
        strategy: Strategy,
        personality: OCEANTraits,
        phase: str,
        score: float,
    ) -> str:
        """Generate human-readable reasoning for the recommendation."""
        parts = []

        # Score assessment
        if score >= 0.8:
            parts.append(f"'{strategy.name}' is highly recommended (score: {score:.2f})")
        elif score >= 0.6:
            parts.append(f"'{strategy.name}' is a solid choice (score: {score:.2f})")
        else:
            parts.append(f"'{strategy.name}' is viable but situational (score: {score:.2f})")

        # Phase relevance
        if strategy.phase.lower() == phase.lower():
            parts.append(f"specifically designed for the {phase} phase")
        elif strategy.phase.lower() == "all":
            parts.append(f"applicable across all phases including {phase}")

        # Effectiveness note
        if strategy.effectiveness >= 0.8:
            parts.append("historically very effective")
        elif strategy.effectiveness <= 0.4:
            parts.append("use with caution - moderate success rate")

        # Personality alignment
        dominant = personality.dominant_traits()
        if dominant:
            parts.append(f"aligns with your dominant traits ({', '.join(dominant)})")

        return ". ".join(parts) + "."

    def _generate_example(
        self,
        strategy: Strategy,
        role: str,
        phase: str,
    ) -> str:
        """Generate an example application of the strategy."""
        examples = []

        if strategy.example_players:
            players = ", ".join(strategy.example_players[:2])
            examples.append(f"Used by: {players}")

        # Phase-specific example templates
        phase_lower = phase.lower()
        role_lower = role.lower()

        if phase_lower == "roundtable":
            if role_lower == "traitor":
                examples.append(
                    "At the Round Table, consider deflecting attention by questioning "
                    "those who have been quiet or inconsistent in their voting patterns."
                )
            else:
                examples.append(
                    "At the Round Table, present evidence methodically and watch for "
                    "defensive reactions that might indicate guilt."
                )

        elif phase_lower == "social":
            if role_lower == "traitor":
                examples.append(
                    "During social time, focus on building trust with influential "
                    "Faithfuls who can vouch for you later."
                )
            else:
                examples.append(
                    "During social time, share observations casually and note who "
                    "seems overly interested in your suspicions."
                )

        elif phase_lower == "breakfast":
            examples.append(
                "At breakfast, pay attention to who arrives when and how they "
                "react to the murder reveal - genuine shock vs. performance."
            )

        elif phase_lower == "mission":
            if role_lower == "traitor":
                examples.append(
                    "During the mission, perform well enough to avoid suspicion "
                    "but consider strategic 'mistakes' if you need to slow the pot."
                )
            else:
                examples.append(
                    "During the mission, note who underperforms and whether it "
                    "seems like genuine struggle or intentional sabotage."
                )

        return " ".join(examples) if examples else "Apply as situation demands."

    def get_voting_guidance(
        self,
        role: str,
        personality: OCEANTraits,
        candidates: List[Dict],
        game_context: Optional[Dict] = None,
    ) -> str:
        """Get specific guidance for the voting phase.

        Args:
            role: "traitor" or "faithful"
            personality: Agent's personality
            candidates: List of dicts with {id, name, suspicion_score}
            game_context: Optional context

        Returns:
            Strategic guidance string
        """
        recs = self.get_recommendations(role, "roundtable", personality, game_context)

        guidance_parts = []

        # Role-specific base guidance
        if role.lower() == "traitor":
            guidance_parts.append(
                "As a Traitor, your goal is to vote in a way that appears Faithful "
                "while protecting fellow Traitors. Consider:"
            )
            guidance_parts.append("- Voting for high-suspicion Faithfuls to blend in")
            guidance_parts.append("- Avoiding voting for fellow Traitors unless necessary for cover")
            guidance_parts.append("- Reading the room - go with majority if you have no strong preference")
        else:
            guidance_parts.append(
                "As a Faithful, your goal is to identify and banish Traitors. Consider:"
            )
            guidance_parts.append("- Players with inconsistent voting patterns")
            guidance_parts.append("- Those who deflect accusations without evidence")
            guidance_parts.append("- Mission performance anomalies")

        # Add personality-specific guidance
        if personality.neuroticism >= 0.7:
            guidance_parts.append("\nNote: Your paranoia may make you over-suspicious. "
                                 "Trust evidence over gut feelings.")
        if personality.agreeableness >= 0.7:
            guidance_parts.append("\nNote: Your agreeable nature may make you vulnerable "
                                 "to persuasion. Stand firm on strong suspicions.")
        if personality.extraversion <= 0.3:
            guidance_parts.append("\nNote: Your quiet nature means your vote speaks loudly. "
                                 "Make sure it counts.")

        # Add top strategy recommendation
        if recs:
            best = recs[0]
            guidance_parts.append(f"\nRecommended strategy: {best.strategy.name}")
            guidance_parts.append(f"  {best.strategy.description[:150]}...")

        return "\n".join(guidance_parts)

    def get_murder_guidance(
        self,
        personality: OCEANTraits,
        potential_victims: List[Dict],
        game_context: Optional[Dict] = None,
    ) -> str:
        """Get guidance for Traitor murder selection.

        Args:
            personality: Traitor's personality
            potential_victims: List of dicts with {id, name, threat_level}
            game_context: Optional context

        Returns:
            Strategic guidance string
        """
        recs = self.get_recommendations("traitor", "turret", personality, game_context)

        guidance_parts = [
            "Murder Target Selection Strategy:",
            "",
        ]

        # Standard considerations
        guidance_parts.extend([
            "Consider these factors when selecting a target:",
            "1. Threat Level - Who is closest to discovering Traitors?",
            "2. Social Connections - Who would cause maximum chaos if eliminated?",
            "3. Shield Status - Avoid protected players (murder fails if shielded)",
            "4. Suspicion Patterns - Who suspects you specifically?",
            "5. Alliance Disruption - Breaking Faithful alliances weakens opposition",
        ])

        # Personality-specific guidance
        guidance_parts.append("\nBased on your personality:")

        if personality.extraversion >= 0.7:
            guidance_parts.append(
                "- High extraversion: You might target vocal accusers who challenge you directly"
            )
        elif personality.extraversion <= 0.3:
            guidance_parts.append(
                "- Low extraversion: Consider quiet, analytical players who may be piecing things together"
            )

        if personality.agreeableness >= 0.7:
            guidance_parts.append(
                "- High agreeableness: You might struggle with the kill. Frame it as 'protecting your team'"
            )

        if personality.neuroticism >= 0.7:
            guidance_parts.append(
                "- High neuroticism: Target those who make you most anxious - your instincts may be right"
            )

        if personality.conscientiousness >= 0.7:
            guidance_parts.append(
                "- High conscientiousness: Make a systematic threat assessment, don't go on gut"
            )

        # Add strategy recommendation
        if recs:
            best = recs[0]
            guidance_parts.append(f"\nRecommended approach: {best.strategy.name}")
            guidance_parts.append(f"  {best.strategy.description[:150]}...")

        return "\n".join(guidance_parts)


# Convenience function
def get_strategy_advisor() -> StrategyAdvisor:
    """Get a strategy advisor instance."""
    return StrategyAdvisor()
