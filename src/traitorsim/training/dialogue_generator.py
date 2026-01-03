"""Dialogue generator for TraitorSim agents.

Uses training data to generate context-appropriate speech patterns,
emotional expressions, and dialogue that matches the agent's personality
and current game situation.
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .training_data_loader import (
    TrainingDataLoader,
    get_training_data,
    OCEANTraits,
)


@dataclass
class EmotionalState:
    """Represents an agent's current emotional state."""
    primary_emotion: str  # crying, nervous, confident, scared, angry, etc.
    intensity: float      # 0.0 - 1.0
    source: str          # What triggered this emotion

    def to_descriptor(self) -> str:
        """Convert to a descriptive string."""
        intensity_words = {
            (0.0, 0.3): "slightly",
            (0.3, 0.6): "noticeably",
            (0.6, 0.8): "clearly",
            (0.8, 1.0): "intensely",
        }
        for (low, high), word in intensity_words.items():
            if low <= self.intensity < high:
                return f"{word} {self.primary_emotion}"
        return self.primary_emotion


@dataclass
class DialogueSuggestion:
    """A suggested piece of dialogue with context."""
    text: str
    context: str  # accusation, defense, alliance_building, etc.
    emotion: EmotionalState
    personality_fit: float  # 0.0 - 1.0


class DialogueGenerator:
    """Generates contextual dialogue for agents."""

    # Emotion-to-personality mappings
    EMOTION_PERSONALITY_MAP = {
        "crying": {"neuroticism": 0.8, "extraversion": 0.4},
        "tears": {"neuroticism": 0.7, "agreeableness": 0.6},
        "shaking": {"neuroticism": 0.9},
        "nervous": {"neuroticism": 0.7},
        "confident": {"extraversion": 0.8, "neuroticism": -0.3},
        "scared": {"neuroticism": 0.85},
        "angry": {"extraversion": 0.6, "agreeableness": -0.4},
        "frustrated": {"neuroticism": 0.5, "conscientiousness": 0.6},
        "relieved": {"neuroticism": 0.4},
        "excited": {"extraversion": 0.8, "openness": 0.6},
        "disappointed": {"neuroticism": 0.5, "conscientiousness": 0.5},
    }

    # Context-to-phase mappings
    CONTEXT_PHASE_MAP = {
        "accusation": "roundtable",
        "defense": "roundtable",
        "alliance_building": "social",
        "emotional_expression": "all",
        "strategic_planning": "social",
    }

    def __init__(self, loader: Optional[TrainingDataLoader] = None):
        self.loader = loader or get_training_data()

    def suggest_dialogue(
        self,
        context: str,
        personality: OCEANTraits,
        role: str,
        target_name: Optional[str] = None,
        emotion: Optional[EmotionalState] = None,
    ) -> DialogueSuggestion:
        """Suggest dialogue for a given context.

        Args:
            context: One of "accusation", "defense", "alliance_building",
                    "emotional_expression", "strategic_planning"
            personality: Agent's personality traits
            role: "traitor" or "faithful"
            target_name: Optional name of player being addressed
            emotion: Optional current emotional state

        Returns:
            DialogueSuggestion with text, context, and personality fit
        """
        phrases = self.loader.get_dialogue_phrases(context)
        markers = self.loader.get_emotional_markers(context)

        if not phrases:
            return self._fallback_dialogue(context, role, target_name)

        # Score phrases by personality fit
        scored_phrases = []
        for phrase in phrases:
            score = self._score_phrase(phrase, personality, context, role)
            scored_phrases.append((phrase, score))

        scored_phrases.sort(key=lambda x: x[1], reverse=True)

        # Select from top phrases with some randomness
        top_phrases = scored_phrases[:5] if len(scored_phrases) >= 5 else scored_phrases
        selected_phrase, fit_score = random.choice(top_phrases)

        # Apply personalization
        text = self._personalize_phrase(selected_phrase, personality, target_name)

        # Determine emotion if not provided
        if not emotion:
            emotion = self._infer_emotion(context, personality, markers)

        return DialogueSuggestion(
            text=text,
            context=context,
            emotion=emotion,
            personality_fit=fit_score,
        )

    def _score_phrase(
        self,
        phrase: str,
        personality: OCEANTraits,
        context: str,
        role: str,
    ) -> float:
        """Score a phrase based on personality and context."""
        score = 0.5  # Base score
        phrase_lower = phrase.lower()

        # Extraversion scoring
        if any(kw in phrase_lower for kw in ["excited", "love", "amazing", "!"]):
            score += personality.extraversion * 0.2
            score -= (1 - personality.extraversion) * 0.1

        # Agreeableness scoring
        if any(kw in phrase_lower for kw in ["trust", "friend", "together", "we"]):
            score += personality.agreeableness * 0.2

        # Neuroticism scoring
        if any(kw in phrase_lower for kw in ["nervous", "scared", "worried", "afraid"]):
            score += personality.neuroticism * 0.15
            score -= (1 - personality.neuroticism) * 0.1

        # Openness scoring
        if any(kw in phrase_lower for kw in ["think", "believe", "theory", "idea"]):
            score += personality.openness * 0.15

        # Conscientiousness scoring
        if any(kw in phrase_lower for kw in ["evidence", "logical", "systematic", "carefully"]):
            score += personality.conscientiousness * 0.15

        # Context-specific scoring
        if context == "accusation":
            if role == "traitor":
                # Traitors should be careful with accusations
                if "traitor" in phrase_lower:
                    score -= 0.1  # Too on-the-nose
            else:
                # Faithfuls can be more direct
                if "traitor" in phrase_lower or "liar" in phrase_lower:
                    score += 0.1

        elif context == "defense":
            if role == "traitor":
                if "faithful" in phrase_lower:
                    score += 0.15  # Good cover
            else:
                if "honest" in phrase_lower or "trust" in phrase_lower:
                    score += 0.1

        elif context == "alliance_building":
            if "alliance" in phrase_lower or "together" in phrase_lower:
                score += 0.15
            if "trust" in phrase_lower:
                score += personality.agreeableness * 0.1

        return max(0.0, min(1.0, score))

    def _personalize_phrase(
        self,
        phrase: str,
        personality: OCEANTraits,
        target_name: Optional[str],
    ) -> str:
        """Personalize a phrase based on personality and target."""
        text = phrase

        # Add target name if available and phrase allows it
        if target_name:
            # Some phrases can be directed at someone
            if any(kw in text.lower() for kw in ["you", "your", "they", "them"]):
                pass  # Phrase already references someone
            elif random.random() < 0.3:
                # Sometimes add direct address
                text = f"{target_name}, {text.lower()}"

        # Add hedging for low confidence
        if personality.neuroticism >= 0.7 and random.random() < 0.4:
            hedges = ["I think ", "Maybe ", "It seems like ", "I'm not sure but "]
            if not any(text.startswith(h) for h in hedges):
                text = random.choice(hedges) + text.lower()

        # Add emphasis for high extraversion
        if personality.extraversion >= 0.8 and random.random() < 0.3:
            if not text.endswith("!"):
                text = text.rstrip(".") + "!"

        return text

    def _infer_emotion(
        self,
        context: str,
        personality: OCEANTraits,
        markers: List[str],
    ) -> EmotionalState:
        """Infer an emotional state based on context and personality."""
        # Parse markers like "nervous (31x)" to get emotions and weights
        emotion_weights = {}
        for marker in markers:
            # Extract emotion and count
            if "(" in marker:
                emotion = marker.split("(")[0].strip()
                count_str = marker.split("(")[1].replace(")", "").replace("x", "")
                try:
                    count = int(count_str)
                except ValueError:
                    count = 1
            else:
                emotion = marker.strip()
                count = 1

            emotion_weights[emotion] = count

        # Weight emotions by personality fit
        scored_emotions = []
        for emotion, base_weight in emotion_weights.items():
            weight = base_weight

            # Adjust by personality
            if emotion in self.EMOTION_PERSONALITY_MAP:
                for trait, trait_weight in self.EMOTION_PERSONALITY_MAP[emotion].items():
                    trait_value = getattr(personality, trait, 0.5)
                    if trait_weight < 0:
                        # Negative weight means high trait reduces this emotion
                        weight *= (1 - trait_value * abs(trait_weight))
                    else:
                        weight *= (1 + trait_value * trait_weight)

            scored_emotions.append((emotion, weight))

        # Select emotion with weighted random choice
        if scored_emotions:
            total = sum(w for _, w in scored_emotions)
            r = random.uniform(0, total)
            cumulative = 0
            for emotion, weight in scored_emotions:
                cumulative += weight
                if r <= cumulative:
                    intensity = min(1.0, weight / max(w for _, w in scored_emotions) * 0.8)
                    return EmotionalState(
                        primary_emotion=emotion,
                        intensity=intensity,
                        source=f"{context} context",
                    )

        # Fallback
        return EmotionalState(
            primary_emotion="neutral",
            intensity=0.3,
            source=f"{context} context",
        )

    def _fallback_dialogue(
        self,
        context: str,
        role: str,
        target_name: Optional[str],
    ) -> DialogueSuggestion:
        """Generate fallback dialogue when no training data is available."""
        fallbacks = {
            "accusation": {
                "traitor": "Something doesn't add up here. We need to look more carefully.",
                "faithful": "I'm getting a strong feeling about who might be a Traitor.",
            },
            "defense": {
                "traitor": "I'm as Faithful as anyone here. I want to win this together.",
                "faithful": "I've been playing honestly this whole time. Check my voting record.",
            },
            "alliance_building": {
                "traitor": "I think we should stick together. Safety in numbers.",
                "faithful": "Can I trust you? I need someone I can rely on in this game.",
            },
            "emotional_expression": {
                "traitor": "This is such an intense experience. I'm trying to stay focused.",
                "faithful": "I can't believe we're in this situation. It's unreal.",
            },
            "strategic_planning": {
                "traitor": "We need to think carefully about our next move.",
                "faithful": "Let's figure out who we can trust and work from there.",
            },
        }

        role_lower = role.lower()
        text = fallbacks.get(context, {}).get(role_lower, "I'm not sure what to say.")

        if target_name and random.random() < 0.5:
            text = f"{target_name}, {text.lower()}"

        return DialogueSuggestion(
            text=text,
            context=context,
            emotion=EmotionalState("neutral", 0.3, "fallback"),
            personality_fit=0.5,
        )

    def generate_reaction(
        self,
        event_type: str,
        personality: OCEANTraits,
        role: str,
        event_details: Optional[Dict] = None,
    ) -> str:
        """Generate an emotional reaction to a game event.

        Args:
            event_type: "murder_reveal", "banishment", "mission_success",
                       "mission_failure", "accusation_received"
            personality: Agent's personality
            role: "traitor" or "faithful"
            event_details: Optional details about the event

        Returns:
            Reaction text
        """
        reactions = {
            "murder_reveal": {
                "high_neuroticism": [
                    "Oh my god, I can't believe this. Who would do this?",
                    "This is terrifying. Any of us could be next.",
                    "I feel sick. We have to find out who did this.",
                ],
                "low_neuroticism": [
                    "This is a blow, but we need to stay focused.",
                    "Another one gone. Let's figure out who's responsible.",
                    "Sad to see them go. We need to be smarter about this.",
                ],
                "traitor_mask": [
                    "I'm devastated. They were such a good person.",
                    "This is awful. We really need to catch these Traitors.",
                    "I can't believe they're gone. This changes everything.",
                ],
            },
            "banishment": {
                "high_neuroticism": [
                    "I feel terrible. What if we got it wrong?",
                    "That was so tense. I hope we made the right call.",
                    "I'm shaking. This game is too much.",
                ],
                "low_neuroticism": [
                    "It had to be done. We'll see if we were right.",
                    "One down. Let's keep our focus.",
                    "Tough decision, but we stuck together.",
                ],
                "traitor_mask": [
                    "I really hope that was the right choice.",
                    "Such a difficult decision. I hate this part.",
                    "I feel for them, but we had to do something.",
                ],
            },
            "mission_success": {
                "high_extraversion": [
                    "Yes! That's what I'm talking about!",
                    "We smashed it! Great teamwork everyone!",
                    "Brilliant! The pot is looking healthy!",
                ],
                "low_extraversion": [
                    "Good work, everyone.",
                    "That went well. Money in the pot.",
                    "Solid performance from the team.",
                ],
            },
            "mission_failure": {
                "high_neuroticism": [
                    "Was that sabotage? Someone's not pulling their weight.",
                    "I'm worried. That shouldn't have happened.",
                    "Something's off. We need to talk about this.",
                ],
                "low_neuroticism": [
                    "Unfortunate. Let's learn from it.",
                    "Mistakes happen. We'll do better next time.",
                    "Not ideal, but we move on.",
                ],
            },
            "accusation_received": {
                "high_agreeableness": [
                    "I understand why you might think that, but you're wrong about me.",
                    "I hear your concerns, but I'm playing honestly.",
                    "Let me explain myself. I'm not who you think I am.",
                ],
                "low_agreeableness": [
                    "That's ridiculous. Look at your own voting record.",
                    "You're barking up the wrong tree and wasting our time.",
                    "Point the finger at me? Maybe you're deflecting.",
                ],
            },
        }

        event_reactions = reactions.get(event_type, {})

        # Determine which reaction pool to use based on personality and role
        pool = None
        role_lower = role.lower()

        if event_type in ["murder_reveal", "banishment"]:
            if role_lower == "traitor":
                pool = event_reactions.get("traitor_mask", [])
            elif personality.neuroticism >= 0.6:
                pool = event_reactions.get("high_neuroticism", [])
            else:
                pool = event_reactions.get("low_neuroticism", [])

        elif event_type in ["mission_success"]:
            if personality.extraversion >= 0.6:
                pool = event_reactions.get("high_extraversion", [])
            else:
                pool = event_reactions.get("low_extraversion", [])

        elif event_type == "mission_failure":
            if personality.neuroticism >= 0.6:
                pool = event_reactions.get("high_neuroticism", [])
            else:
                pool = event_reactions.get("low_neuroticism", [])

        elif event_type == "accusation_received":
            if personality.agreeableness >= 0.6:
                pool = event_reactions.get("high_agreeableness", [])
            else:
                pool = event_reactions.get("low_agreeableness", [])

        if pool:
            return random.choice(pool)

        return "I'm processing what just happened."

    def get_speech_style_modifiers(
        self,
        personality: OCEANTraits,
    ) -> Dict[str, str]:
        """Get speech style modifiers based on personality.

        Returns dict of modifiers that can be applied to any dialogue.
        """
        modifiers = {}

        # Extraversion affects volume and energy
        if personality.extraversion >= 0.8:
            modifiers["volume"] = "speaks loudly and energetically"
            modifiers["pace"] = "rapid, animated speech"
        elif personality.extraversion <= 0.3:
            modifiers["volume"] = "speaks quietly and deliberately"
            modifiers["pace"] = "measured, thoughtful speech"
        else:
            modifiers["volume"] = "speaks at normal volume"
            modifiers["pace"] = "even-paced speech"

        # Agreeableness affects warmth
        if personality.agreeableness >= 0.8:
            modifiers["warmth"] = "warm, inclusive language"
            modifiers["addressing"] = "frequently uses 'we' and 'us'"
        elif personality.agreeableness <= 0.3:
            modifiers["warmth"] = "direct, sometimes blunt"
            modifiers["addressing"] = "focuses on individual accountability"
        else:
            modifiers["warmth"] = "neutral, professional tone"
            modifiers["addressing"] = "balanced use of 'I' and 'we'"

        # Neuroticism affects confidence
        if personality.neuroticism >= 0.8:
            modifiers["confidence"] = "often hedges and qualifies statements"
            modifiers["stress"] = "shows signs of anxiety when challenged"
        elif personality.neuroticism <= 0.3:
            modifiers["confidence"] = "speaks with calm assurance"
            modifiers["stress"] = "remains composed under pressure"
        else:
            modifiers["confidence"] = "appropriately confident"
            modifiers["stress"] = "manages stress visibly but controlled"

        # Openness affects vocabulary
        if personality.openness >= 0.8:
            modifiers["vocabulary"] = "uses varied, sometimes unusual expressions"
            modifiers["reasoning"] = "explores multiple possibilities"
        elif personality.openness <= 0.3:
            modifiers["vocabulary"] = "prefers familiar, concrete language"
            modifiers["reasoning"] = "focuses on established facts"
        else:
            modifiers["vocabulary"] = "standard vocabulary"
            modifiers["reasoning"] = "balanced approach to new ideas"

        # Conscientiousness affects precision
        if personality.conscientiousness >= 0.8:
            modifiers["precision"] = "precise, organized statements"
            modifiers["evidence"] = "frequently cites specific examples"
        elif personality.conscientiousness <= 0.3:
            modifiers["precision"] = "loose, sometimes vague statements"
            modifiers["evidence"] = "relies more on intuition than evidence"
        else:
            modifiers["precision"] = "reasonably organized"
            modifiers["evidence"] = "uses evidence when available"

        return modifiers


# Convenience function
def get_dialogue_generator() -> DialogueGenerator:
    """Get a dialogue generator instance."""
    return DialogueGenerator()
