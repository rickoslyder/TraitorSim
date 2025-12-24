"""Emotion inference engine for voice synthesis.

Maps game context, OCEAN personality traits, and role to appropriate
emotion tags for ElevenLabs audio delivery.

The engine uses a multi-factor calculation:
1. Base emotion from context (accusation, defense, reaction, etc.)
2. Modifier from neuroticism (adds anxiety/nervousness)
3. Modifier from extraversion (adds boldness/loudness)
4. Modifier from agreeableness (softens or hardens tone)
5. Role overlay (Traitor mask vs Faithful authenticity)
6. Stress level adjustment (accumulated suspicion pressure)
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import EmotionIntensity


class EmotionContext(str, Enum):
    """Context types that influence emotional delivery."""
    ACCUSATION = "accusation"
    DEFENSE = "defense"
    REACTION_MURDER = "reaction_murder"
    REACTION_BANISHMENT = "reaction_banishment"
    REACTION_SHIELD = "reaction_shield"
    VOTING = "voting"
    TURRET_DELIBERATION = "turret_deliberation"
    CONFESSIONAL = "confessional"
    SOCIAL_CHAT = "social_chat"
    ALLIANCE_BUILDING = "alliance_building"
    MISSION_BRIEFING = "mission_briefing"
    MISSION_SUCCESS = "mission_success"
    MISSION_FAILURE = "mission_failure"
    REVELATION = "revelation"
    FAREWELL = "farewell"
    NEUTRAL = "neutral"


@dataclass
class EmotionResult:
    """Result of emotion inference containing tags and metadata."""
    primary_tag: str
    secondary_tags: List[str]
    intensity: EmotionIntensity
    confidence: float  # 0.0-1.0, how confident we are in this inference

    def to_tags(self) -> List[str]:
        """Get all tags as a flat list with primary first."""
        return [self.primary_tag] + self.secondary_tags

    def to_tag_string(self) -> str:
        """Format as ElevenLabs inline tags."""
        all_tags = self.to_tags()
        return "".join([f"[{tag}]" for tag in all_tags])


class EmotionInferenceEngine:
    """Infers emotional delivery from game state and personality.

    Uses OCEAN personality model combined with game context to determine
    appropriate voice emotion tags for ElevenLabs synthesis.
    """

    # Base emotions by context (before personality modification)
    CONTEXT_BASE_EMOTIONS: Dict[EmotionContext, str] = {
        EmotionContext.ACCUSATION: "confident",
        EmotionContext.DEFENSE: "defensive",
        EmotionContext.REACTION_MURDER: "shocked",
        EmotionContext.REACTION_BANISHMENT: "tense",
        EmotionContext.REACTION_SHIELD: "relieved",
        EmotionContext.VOTING: "thoughtful",
        EmotionContext.TURRET_DELIBERATION: "cold",
        EmotionContext.CONFESSIONAL: "reflective",
        EmotionContext.SOCIAL_CHAT: "friendly",
        EmotionContext.ALLIANCE_BUILDING: "earnest",
        EmotionContext.MISSION_BRIEFING: "focused",
        EmotionContext.MISSION_SUCCESS: "excited",
        EmotionContext.MISSION_FAILURE: "disappointed",
        EmotionContext.REVELATION: "dramatic",
        EmotionContext.FAREWELL: "emotional",
        EmotionContext.NEUTRAL: "neutral",
    }

    # Secondary emotions commonly paired with each context
    CONTEXT_SECONDARY_EMOTIONS: Dict[EmotionContext, List[str]] = {
        EmotionContext.ACCUSATION: ["suspicious", "certain"],
        EmotionContext.DEFENSE: ["indignant", "hurt"],
        EmotionContext.REACTION_MURDER: ["sad", "fearful"],
        EmotionContext.REACTION_BANISHMENT: ["relieved", "worried"],
        EmotionContext.REACTION_SHIELD: ["grateful", "surprised"],
        EmotionContext.VOTING: ["conflicted", "determined"],
        EmotionContext.TURRET_DELIBERATION: ["calculating", "whispered"],
        EmotionContext.CONFESSIONAL: ["honest", "conflicted"],
        EmotionContext.SOCIAL_CHAT: ["warm", "curious"],
        EmotionContext.ALLIANCE_BUILDING: ["hopeful", "trusting"],
        EmotionContext.MISSION_BRIEFING: ["determined", "attentive"],
        EmotionContext.MISSION_SUCCESS: ["proud", "triumphant"],
        EmotionContext.MISSION_FAILURE: ["frustrated", "apologetic"],
        EmotionContext.REVELATION: ["tense", "slow"],
        EmotionContext.FAREWELL: ["bittersweet", "resigned"],
        EmotionContext.NEUTRAL: [],
    }

    def __init__(self):
        """Initialize the emotion inference engine."""
        self._cache: Dict[str, EmotionResult] = {}

    def infer(
        self,
        context: EmotionContext,
        personality: Dict[str, float],
        role: str = "faithful",
        stress_level: float = 0.0,
        additional_factors: Optional[Dict[str, Any]] = None
    ) -> EmotionResult:
        """Infer emotional delivery based on multiple factors.

        Args:
            context: The type of game situation
            personality: OCEAN traits (openness, conscientiousness, extraversion,
                        agreeableness, neuroticism) as 0.0-1.0 values
            role: Player's role ("faithful" or "traitor")
            stress_level: Current stress from suspicion/pressure (0.0-1.0)
            additional_factors: Extra context like:
                - target_is_traitor: bool
                - accused_by_close_ally: bool
                - surviving_close_call: bool
                - is_lying: bool

        Returns:
            EmotionResult with tags and intensity
        """
        factors = additional_factors or {}

        # Start with base emotion from context
        primary = self._get_base_emotion(context)
        secondary: List[str] = []
        intensity = EmotionIntensity.NORMAL

        # Get OCEAN traits with defaults
        openness = personality.get("openness", 0.5)
        conscientiousness = personality.get("conscientiousness", 0.5)
        extraversion = personality.get("extraversion", 0.5)
        agreeableness = personality.get("agreeableness", 0.5)
        neuroticism = personality.get("neuroticism", 0.5)

        # Apply neuroticism modifier (anxiety, emotional instability)
        primary, secondary, intensity = self._apply_neuroticism(
            primary, secondary, intensity,
            neuroticism, context, stress_level
        )

        # Apply extraversion modifier (boldness, volume)
        primary, secondary, intensity = self._apply_extraversion(
            primary, secondary, intensity,
            extraversion, context
        )

        # Apply agreeableness modifier (softness vs confrontation)
        primary, secondary, intensity = self._apply_agreeableness(
            primary, secondary, intensity,
            agreeableness, context
        )

        # Apply role-specific overlays
        if role == "traitor":
            primary, secondary = self._apply_traitor_overlay(
                primary, secondary, context, factors
            )
        else:
            primary, secondary = self._apply_faithful_overlay(
                primary, secondary, context, factors
            )

        # Apply stress adjustment
        if stress_level > 0.6:
            secondary = self._add_stress_markers(secondary, stress_level)
            if intensity == EmotionIntensity.NORMAL:
                intensity = EmotionIntensity.HEIGHTENED

        # Add context-appropriate secondary emotions
        secondary = self._add_contextual_secondaries(secondary, context)

        # Deduplicate and limit secondary tags
        secondary = list(dict.fromkeys(secondary))[:3]

        # Calculate confidence based on how many modifiers applied
        confidence = self._calculate_confidence(
            personality, stress_level, len(secondary)
        )

        return EmotionResult(
            primary_tag=primary,
            secondary_tags=secondary,
            intensity=intensity,
            confidence=confidence
        )

    def infer_for_player(
        self,
        player: Any,  # Player dataclass from game_state
        context: EmotionContext,
        stress_level: float = 0.0,
        additional_factors: Optional[Dict[str, Any]] = None
    ) -> EmotionResult:
        """Convenience method that accepts a Player object directly.

        Args:
            player: Player dataclass with personality and role
            context: The game situation
            stress_level: Current stress level
            additional_factors: Extra context

        Returns:
            EmotionResult with inferred emotions
        """
        return self.infer(
            context=context,
            personality=player.personality,
            role=player.role.value if hasattr(player.role, 'value') else str(player.role),
            stress_level=stress_level,
            additional_factors=additional_factors
        )

    def _get_base_emotion(self, context: EmotionContext) -> str:
        """Get the base emotion for a context."""
        return self.CONTEXT_BASE_EMOTIONS.get(context, "neutral")

    def _apply_neuroticism(
        self,
        primary: str,
        secondary: List[str],
        intensity: EmotionIntensity,
        neuroticism: float,
        context: EmotionContext,
        stress_level: float
    ) -> Tuple[str, List[str], EmotionIntensity]:
        """Apply neuroticism modifier to emotions.

        High neuroticism adds nervousness, anxiety, emotional volatility.
        """
        if neuroticism < 0.4:
            # Low neuroticism = emotionally stable
            if context == EmotionContext.DEFENSE:
                primary = "calm"  # Calm under pressure
            secondary.append("composed")
            return primary, secondary, intensity

        if neuroticism > 0.7:
            # High neuroticism = anxious, volatile
            if context == EmotionContext.DEFENSE:
                secondary.insert(0, "nervous")
            elif context == EmotionContext.ACCUSATION:
                secondary.insert(0, "anxious")
            elif context == EmotionContext.REACTION_MURDER:
                primary = "panicked"

            # High stress + high neuroticism = breaking down
            if stress_level > 0.7:
                secondary.append("trembling")
                intensity = EmotionIntensity.HEIGHTENED

        return primary, secondary, intensity

    def _apply_extraversion(
        self,
        primary: str,
        secondary: List[str],
        intensity: EmotionIntensity,
        extraversion: float,
        context: EmotionContext
    ) -> Tuple[str, List[str], EmotionIntensity]:
        """Apply extraversion modifier to emotions.

        High extraversion adds boldness, loudness, assertiveness.
        Low extraversion adds quietness, hesitance.
        """
        if extraversion > 0.7:
            # High extraversion = bold, assertive
            if context == EmotionContext.ACCUSATION:
                secondary.insert(0, "loud")
                primary = "assertive"
            elif context == EmotionContext.DEFENSE:
                secondary.insert(0, "defiant")
            intensity = EmotionIntensity.HEIGHTENED

        elif extraversion < 0.4:
            # Low extraversion = quiet, hesitant
            if context in (EmotionContext.ACCUSATION, EmotionContext.DEFENSE):
                secondary.append("quiet")
                secondary.append("hesitant")
            intensity = EmotionIntensity.SUBTLE

        return primary, secondary, intensity

    def _apply_agreeableness(
        self,
        primary: str,
        secondary: List[str],
        intensity: EmotionIntensity,
        agreeableness: float,
        context: EmotionContext
    ) -> Tuple[str, List[str], EmotionIntensity]:
        """Apply agreeableness modifier.

        High agreeableness = warmer, more conciliatory.
        Low agreeableness = harsher, more confrontational.
        """
        if agreeableness > 0.7:
            # High agreeableness = soft, diplomatic
            if context == EmotionContext.ACCUSATION:
                secondary.append("reluctant")  # Doesn't like confrontation
            elif context == EmotionContext.DEFENSE:
                secondary.append("hurt")  # Takes it personally

        elif agreeableness < 0.4:
            # Low agreeableness = confrontational
            if context == EmotionContext.ACCUSATION:
                secondary.append("harsh")
                secondary.append("accusing")
            elif context == EmotionContext.DEFENSE:
                primary = "angry"  # Fights back hard
                secondary.append("indignant")

        return primary, secondary, intensity

    def _apply_traitor_overlay(
        self,
        primary: str,
        secondary: List[str],
        context: EmotionContext,
        factors: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """Apply Traitor-specific emotional overlays.

        Traitors need to maintain a "Faithful mask" - their delivery
        should be controlled, practiced, maybe too smooth.
        """
        is_lying = factors.get("is_lying", False)
        target_is_traitor = factors.get("target_is_traitor", False)

        if context == EmotionContext.DEFENSE:
            # Traitors defending = practiced, controlled
            primary = "measured"
            secondary = ["calm", "controlled"]

        elif context == EmotionContext.ACCUSATION:
            if target_is_traitor:
                # Bus-throwing fellow Traitor = calculated betrayal
                primary = "cold"
                secondary = ["calculated"]
            else:
                # Accusing Faithful = performance
                secondary.append("performative")

        elif context == EmotionContext.TURRET_DELIBERATION:
            # Private Traitor meetings = cold, strategic
            primary = "cold"
            secondary = ["whispered", "calculating"]

        elif context == EmotionContext.REACTION_MURDER:
            # Traitor reacting to their own kill = fake shock
            secondary.insert(0, "performative")

        elif context == EmotionContext.CONFESSIONAL:
            # Traitor confessional = revealing true feelings
            primary = "satisfied"
            secondary = ["smug", "calculated"]

        return primary, secondary

    def _apply_faithful_overlay(
        self,
        primary: str,
        secondary: List[str],
        context: EmotionContext,
        factors: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """Apply Faithful-specific emotional overlays.

        Faithfuls have authentic emotions - genuine shock, real fear,
        true indignation when falsely accused.
        """
        accused_by_close_ally = factors.get("accused_by_close_ally", False)

        if context == EmotionContext.DEFENSE and accused_by_close_ally:
            # Betrayed by friend = genuine hurt
            primary = "betrayed"
            secondary = ["hurt", "confused"]

        elif context == EmotionContext.REACTION_BANISHMENT:
            banished_was_traitor = factors.get("banished_was_traitor", False)
            if banished_was_traitor:
                primary = "relieved"
                secondary = ["vindicated"]
            else:
                primary = "guilty"
                secondary = ["sad", "regretful"]

        return primary, secondary

    def _add_stress_markers(
        self,
        secondary: List[str],
        stress_level: float
    ) -> List[str]:
        """Add stress-related emotion markers."""
        if stress_level > 0.8:
            secondary.insert(0, "strained")
            secondary.append("desperate")
        elif stress_level > 0.6:
            secondary.append("tense")

        return secondary

    def _add_contextual_secondaries(
        self,
        secondary: List[str],
        context: EmotionContext
    ) -> List[str]:
        """Add context-appropriate secondary emotions if none present."""
        if not secondary:
            context_secondaries = self.CONTEXT_SECONDARY_EMOTIONS.get(context, [])
            if context_secondaries:
                secondary.append(context_secondaries[0])
        return secondary

    def _calculate_confidence(
        self,
        personality: Dict[str, float],
        stress_level: float,
        modifier_count: int
    ) -> float:
        """Calculate confidence in the emotion inference.

        Higher confidence when:
        - More personality data available
        - More modifiers applied (clearer picture)
        - Moderate stress (extreme stress is harder to predict)
        """
        # Base confidence
        confidence = 0.5

        # More personality data = more confident
        trait_count = len([v for v in personality.values() if v != 0.5])
        confidence += trait_count * 0.1

        # More modifiers = clearer picture
        confidence += min(modifier_count * 0.05, 0.15)

        # Extreme stress reduces confidence (unpredictable)
        if stress_level > 0.8:
            confidence -= 0.1

        return min(1.0, max(0.0, confidence))


# =============================================================================
# EMOTION TAG REFERENCE
# =============================================================================

# All supported emotion tags for ElevenLabs
EMOTION_TAGS = {
    # Primary emotions
    "angry", "anxious", "calm", "cold", "concerned", "confident",
    "confused", "defensive", "dramatic", "excited", "fearful",
    "frustrated", "happy", "hesitant", "hopeful", "indignant",
    "nervous", "relieved", "sad", "sarcastic", "shocked",
    "suspicious", "tense", "triumphant", "whispered", "worried",

    # Secondary/modifier emotions
    "accusing", "apologetic", "assertive", "bittersweet", "calculated",
    "certain", "composed", "conflicted", "controlled", "curious",
    "defiant", "desperate", "determined", "earnest", "emotional",
    "focused", "friendly", "grateful", "guilty", "harsh", "honest",
    "hurt", "loud", "measured", "panicked", "performative", "proud",
    "quiet", "reflective", "regretful", "reluctant", "resigned",
    "satisfied", "slow", "smug", "strained", "surprised", "thoughtful",
    "trembling", "trusting", "vindicated", "warm",
}

# Delivery modifier tags
DELIVERY_TAGS = {
    "fast", "slow", "loud", "quiet", "pause", "long_pause",
    "interrupting", "overlapping", "whispered",
}

# Non-speech sounds
NON_SPEECH_TAGS = {
    "sigh", "laugh", "gasp", "crying", "clearing_throat", "deep_breath",
}


def get_emotion_for_context(
    context_type: str,
    personality: Optional[Dict[str, float]] = None,
    role: str = "faithful"
) -> List[str]:
    """Quick helper to get emotion tags for a context.

    Args:
        context_type: String context name (e.g., "accusation", "defense")
        personality: Optional OCEAN traits dict
        role: "faithful" or "traitor"

    Returns:
        List of emotion tag strings
    """
    engine = EmotionInferenceEngine()

    try:
        context = EmotionContext(context_type)
    except ValueError:
        context = EmotionContext.NEUTRAL

    result = engine.infer(
        context=context,
        personality=personality or {},
        role=role
    )

    return result.to_tags()
