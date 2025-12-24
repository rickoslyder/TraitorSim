"""Voice library mapping archetypes to ElevenLabs voices.

Maps the 13 TraitorSim archetypes to appropriate ElevenLabs voices,
with gender-aware selection and OCEAN-based parameter adjustment.

Voice IDs validated against ElevenLabs library (December 2025).
Sources:
- https://audio-generation-plugin.com/elevenlabs-premade-voices/
- https://help.scenario.com/en/articles/elevenlabs-family-the-essentials/
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import numpy as np

from .models import VoiceConfig


# =============================================================================
# NARRATOR CONFIGURATION
# =============================================================================

# Primary narrator voice - dramatic, theatrical (Alan Cumming style)
NARRATOR_VOICE_ID = "daniel"  # Deep authoritative British male

# Alternative narrator options
NARRATOR_ALTERNATIVES = {
    "dramatic_male": "daniel",      # Deep, authoritative British
    "dramatic_female": "charlotte", # Dramatic British female
    "warm_male": "brian",           # Rich narration style
    "warm_female": "dorothy",       # Pleasant British female
}


# =============================================================================
# ARCHETYPE VOICE PROFILES
# =============================================================================

ARCHETYPE_VOICE_PROFILES: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # 1. THE PRODIGY
    # High intellect, low neuroticism
    # Voice: Young, sharp, analytical. Quick speech with occasional hesitation.
    # =========================================================================
    "prodigy": {
        "voice_description": "Young, sharp, analytical. Quick speech with occasional hesitation.",
        "male": {
            "base_voice_id": "liam",    # Articulate, clear young American
            "alt_voice_id": "josh",     # Deep, impactful young American
        },
        "female": {
            "base_voice_id": "aria",    # Expressive, young American (2024)
            "alt_voice_id": "jessica",  # Expressive, youthful
        },
        "stability": 0.6,               # Moderate - controlled but can show excitement
        "style": 0.7,                   # Higher style for analytical precision
        "emotional_range": ["confident", "nervous", "excited", "analytical"],
        "speech_rate_hint": "fast",
    },

    # =========================================================================
    # 2. THE CHARMING SOCIOPATH
    # High extraversion, low agreeableness
    # Voice: Smooth, warm, disarming. Perfect control with coldness underneath.
    # =========================================================================
    "charming_sociopath": {
        "voice_description": "Smooth, warm, disarming. Perfect control with coldness underneath.",
        "male": {
            "base_voice_id": "george",   # Warm, trustworthy British - hides malice
            "alt_voice_id": "roger",     # Confident, persuasive (2024)
        },
        "female": {
            "base_voice_id": "charlotte", # Seductive, playful - manipulation
            "alt_voice_id": "alice",      # Confident British
        },
        "stability": 0.75,               # High - very controlled
        "style": 0.5,                    # Moderate - not over-the-top
        "emotional_range": ["charming", "concerned", "cold", "calculating"],
        "speech_rate_hint": "measured",
    },

    # =========================================================================
    # 3. THE BITTER TRAITOR
    # Low agreeableness, high neuroticism
    # Voice: Resentful edge, defensive posture. Sarcastic undertone.
    # =========================================================================
    "bitter_traitor": {
        "voice_description": "Resentful edge, defensive posture. Sarcastic undertone.",
        "male": {
            "base_voice_id": "callum",   # Hoarse, dramatic, intense
            "alt_voice_id": "clyde",     # War veteran, intense
        },
        "female": {
            "base_voice_id": "lily",     # Raspy, middle-aged British
            "alt_voice_id": "domi",      # Strong young American
        },
        "stability": 0.5,                # Lower - more volatile
        "style": 0.6,
        "emotional_range": ["bitter", "defensive", "vindictive", "sarcastic"],
        "speech_rate_hint": "clipped",
    },

    # =========================================================================
    # 4. THE MISGUIDED SURVIVOR
    # High neuroticism, moderate agreeableness
    # Voice: Anxious, overcompensating confidence. Frequently second-guesses.
    # =========================================================================
    "misguided_survivor": {
        "voice_description": "Anxious, overcompensating confidence. Frequently second-guesses.",
        "male": {
            "base_voice_id": "harry",    # Anxious young American - PERFECT
            "alt_voice_id": "ethan",     # Young American, ASMR-style nervous
        },
        "female": {
            "base_voice_id": "jessica",  # Expressive, youthful
            "alt_voice_id": "freya",     # Young American, versatile
        },
        "stability": 0.4,                # Low - lots of variation (anxiety)
        "style": 0.55,
        "emotional_range": ["nervous", "hopeful", "panicked", "uncertain"],
        "speech_rate_hint": "variable",
    },

    # =========================================================================
    # 5. THE ZEALOT
    # High conscientiousness, low openness
    # Voice: Intense conviction, unwavering certainty. Righteous tone.
    # =========================================================================
    "zealot": {
        "voice_description": "Intense conviction, unwavering certainty. Righteous tone.",
        "male": {
            "base_voice_id": "josh",     # Deep, impactful
            "alt_voice_id": "bill",      # Strong, documentary-style
        },
        "female": {
            "base_voice_id": "alice",    # Confident British, news presenter
            "alt_voice_id": "domi",      # Strong young American
        },
        "stability": 0.8,                # High - very controlled, certain
        "style": 0.4,                    # Lower style - serious, not playful
        "emotional_range": ["fervent", "judgmental", "indignant", "righteous"],
        "speech_rate_hint": "deliberate",
    },

    # =========================================================================
    # 6. THE INFATUATED FAITHFUL
    # High agreeableness, high extraversion
    # Voice: Warm, trusting, emotionally open. Eager to connect.
    # =========================================================================
    "infatuated_faithful": {
        "voice_description": "Warm, trusting, emotionally open. Eager to connect.",
        "male": {
            "base_voice_id": "chris",    # Casual, relatable American
            "alt_voice_id": "eric",      # Friendly, approachable
        },
        "female": {
            "base_voice_id": "matilda",  # Friendly, warm audiobook
            "alt_voice_id": "rachel",    # Calm, soothing
        },
        "stability": 0.55,               # Moderate - emotionally expressive
        "style": 0.7,                    # Higher - warm and engaging
        "emotional_range": ["affectionate", "hurt", "loyal", "hopeful"],
        "speech_rate_hint": "warm",
    },

    # =========================================================================
    # 7. THE COMEDIC PSYCHIC
    # High openness, moderate extraversion
    # Voice: Whimsical, playful, slightly eccentric. Theatrical delivery.
    # =========================================================================
    "comedic_psychic": {
        "voice_description": "Whimsical, playful, slightly eccentric. Theatrical delivery.",
        "male": {
            "base_voice_id": "jeremy",   # Excited, American-Irish, energetic
            "alt_voice_id": "giovanni",  # Young English-Italian, foreign flair
        },
        "female": {
            "base_voice_id": "mimi",     # Childish, English-Swedish, quirky
            "alt_voice_id": "gigi",      # Childish, animation-style
        },
        "stability": 0.4,                # Low - lots of variation (theatrical)
        "style": 0.85,                   # High - very expressive
        "emotional_range": ["mystical", "silly", "dramatic", "excited"],
        "speech_rate_hint": "theatrical",
    },

    # =========================================================================
    # 8. THE INCOMPETENT AUTHORITY
    # Low conscientiousness, high extraversion
    # Voice: Pompous bluster hiding uncertainty. Overconfident assertions.
    # =========================================================================
    "incompetent_authority": {
        "voice_description": "Pompous bluster hiding uncertainty. Overconfident assertions.",
        "male": {
            "base_voice_id": "patrick",  # Shouty, energetic - perfect bluster
            "alt_voice_id": "bill",      # Strong, documentary
        },
        "female": {
            "base_voice_id": "glinda",   # Middle-aged American, witch-like
            "alt_voice_id": "serena",    # Pleasant, interactive
        },
        "stability": 0.5,                # Moderate - tries to be controlled but slips
        "style": 0.75,                   # Higher - pompous delivery
        "emotional_range": ["pompous", "flustered", "indignant", "defensive"],
        "speech_rate_hint": "blustering",
    },

    # =========================================================================
    # 9. THE QUIRKY OUTSIDER
    # High openness, low extraversion
    # Voice: Quiet observation, unexpected insights. Deadpan delivery.
    # =========================================================================
    "quirky_outsider": {
        "voice_description": "Quiet observation, unexpected insights. Deadpan delivery.",
        "male": {
            "base_voice_id": "thomas",   # Calm, meditation-style
            "alt_voice_id": "fin",       # Old Irish sailor, authentic
        },
        "female": {
            "base_voice_id": "emily",    # Calm young American
            "alt_voice_id": "nicole",    # Whispering, intimate
        },
        "non_binary": {
            "base_voice_id": "river",    # Non-binary, modern (2024)
            "alt_voice_id": "thomas",    # Neutral fallback
        },
        "stability": 0.7,                # Higher - deadpan requires control
        "style": 0.3,                    # Low - understated delivery
        "emotional_range": ["curious", "detached", "surprised", "thoughtful"],
        "speech_rate_hint": "measured",
    },

    # =========================================================================
    # 10. THE ROMANTIC
    # High agreeableness, high openness
    # Voice: Emotionally rich, idealistic. Dramatic emotional range.
    # =========================================================================
    "romantic": {
        "voice_description": "Emotionally rich, idealistic. Dramatic emotional range.",
        "male": {
            "base_voice_id": "brian",    # Deep, rich narration
            "alt_voice_id": "michael",   # Old American, audiobook
        },
        "female": {
            "base_voice_id": "dorothy",  # Pleasant young British
            "alt_voice_id": "grace",     # Young American-Southern
        },
        "stability": 0.5,                # Moderate - emotionally variable
        "style": 0.65,                   # Higher - expressive
        "emotional_range": ["hopeful", "heartbroken", "passionate", "loyal"],
        "speech_rate_hint": "emotional",
    },

    # =========================================================================
    # 11. THE MISCHIEVOUS OPERATOR
    # Low conscientiousness, high extraversion
    # Voice: Playful chaos energy. Enjoys stirring the pot.
    # =========================================================================
    "mischievous_operator": {
        "voice_description": "Playful chaos energy. Enjoys stirring the pot.",
        "male": {
            "base_voice_id": "charlie",  # Casual Australian, playful
            "alt_voice_id": "jeremy",    # Excited, energetic
        },
        "female": {
            "base_voice_id": "laura",    # Upbeat, lively (2024)
            "alt_voice_id": "sarah",     # Expressive, energetic
        },
        "stability": 0.4,                # Low - lots of playful variation
        "style": 0.8,                    # High - mischievous energy
        "emotional_range": ["amused", "scheming", "gleeful", "provocative"],
        "speech_rate_hint": "playful",
    },

    # =========================================================================
    # 12. THE SMUG PLAYER
    # High extraversion, low agreeableness
    # Voice: Self-satisfied confidence. Condescending undertones.
    # =========================================================================
    "smug_player": {
        "voice_description": "Self-satisfied confidence. Condescending undertones.",
        "male": {
            "base_voice_id": "joseph",   # Formal British male
            "alt_voice_id": "daniel",    # Deep British, authoritative
        },
        "female": {
            "base_voice_id": "alice",    # Confident British, news presenter
            "alt_voice_id": "charlotte", # Seductive, playful edge
        },
        "stability": 0.7,                # Higher - controlled superiority
        "style": 0.5,                    # Moderate - not over-the-top
        "emotional_range": ["smug", "dismissive", "annoyed", "superior"],
        "speech_rate_hint": "measured",
    },

    # =========================================================================
    # 13. THE CHARISMATIC LEADER
    # High extraversion, high conscientiousness
    # Voice: Inspiring presence, natural authority. Rallying tone.
    # =========================================================================
    "charismatic_leader": {
        "voice_description": "Inspiring presence, natural authority. Rallying tone.",
        "male": {
            "base_voice_id": "liam",     # Articulate, clear
            "alt_voice_id": "george",    # Warm, trustworthy
        },
        "female": {
            "base_voice_id": "aria",     # Expressive, engaging (2024)
            "alt_voice_id": "sarah",     # Soft, news delivery
        },
        "stability": 0.65,               # Moderate-high - controlled but engaging
        "style": 0.6,                    # Moderate - authoritative not theatrical
        "emotional_range": ["inspiring", "determined", "compassionate", "commanding"],
        "speech_rate_hint": "confident",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_voice_for_persona(persona: Dict[str, Any]) -> str:
    """Get appropriate ElevenLabs voice ID based on persona's archetype and gender.

    Args:
        persona: Dict containing archetype_id and demographics.gender

    Returns:
        ElevenLabs voice ID string
    """
    archetype_id = persona.get("archetype_id", "prodigy")
    demographics = persona.get("demographics", {})
    gender = demographics.get("gender", "female").lower()

    profile = ARCHETYPE_VOICE_PROFILES.get(
        archetype_id,
        ARCHETYPE_VOICE_PROFILES["prodigy"]  # Default fallback
    )

    # Handle non-binary if supported by archetype
    if gender == "non-binary" and "non_binary" in profile:
        return profile["non_binary"]["base_voice_id"]

    # Default to female if gender unknown or not male
    gender_key = "male" if gender == "male" else "female"
    return profile[gender_key]["base_voice_id"]


def get_voice_config_for_persona(persona: Dict[str, Any]) -> VoiceConfig:
    """Get full VoiceConfig for a persona with OCEAN-adjusted parameters.

    Args:
        persona: Dict containing archetype_id, demographics, and personality

    Returns:
        VoiceConfig with adjusted parameters
    """
    archetype_id = persona.get("archetype_id", "prodigy")
    demographics = persona.get("demographics", {})
    personality = persona.get("personality", {})

    gender = demographics.get("gender", "female").lower()

    profile = ARCHETYPE_VOICE_PROFILES.get(
        archetype_id,
        ARCHETYPE_VOICE_PROFILES["prodigy"]
    )

    # Get base voice ID
    voice_id = get_voice_for_persona(persona)

    # Get base stability and style from profile
    base_stability = profile.get("stability", 0.5)
    base_style = profile.get("style", 0.5)

    # Adjust stability based on neuroticism
    # High neuroticism = less stable voice (more emotional variation)
    neuroticism = personality.get("neuroticism", 0.5)
    stability_adj = base_stability * (1.0 - (neuroticism * 0.3))

    # Adjust style based on extraversion
    # High extraversion = more expressive style
    extraversion = personality.get("extraversion", 0.5)
    style_adj = base_style * (1.0 + (extraversion * 0.2))

    # Clamp values to valid range
    stability = max(0.1, min(0.9, stability_adj))
    style = max(0.1, min(0.9, style_adj))

    return VoiceConfig(
        voice_id=voice_id,
        stability=stability,
        style=style,
        similarity_boost=0.75,
        use_speaker_boost=True,
        gender=gender,
        age_range=_age_to_range(demographics.get("age", 35)),
        accent=_location_to_accent(demographics.get("location", "UK")),
    )


def get_archetype_emotional_range(archetype_id: str) -> List[str]:
    """Get list of appropriate emotions for an archetype.

    Args:
        archetype_id: Archetype identifier

    Returns:
        List of emotion tag strings
    """
    profile = ARCHETYPE_VOICE_PROFILES.get(archetype_id, {})
    return profile.get("emotional_range", ["neutral"])


def list_available_voices() -> Dict[str, List[str]]:
    """List all voice IDs used in the library, grouped by gender.

    Returns:
        Dict with 'male', 'female', 'non_binary' keys
    """
    voices = {"male": set(), "female": set(), "non_binary": set()}

    for archetype, profile in ARCHETYPE_VOICE_PROFILES.items():
        if "male" in profile:
            voices["male"].add(profile["male"]["base_voice_id"])
            voices["male"].add(profile["male"]["alt_voice_id"])
        if "female" in profile:
            voices["female"].add(profile["female"]["base_voice_id"])
            voices["female"].add(profile["female"]["alt_voice_id"])
        if "non_binary" in profile:
            voices["non_binary"].add(profile["non_binary"]["base_voice_id"])
            voices["non_binary"].add(profile["non_binary"]["alt_voice_id"])

    return {k: sorted(list(v)) for k, v in voices.items()}


def _age_to_range(age: int) -> str:
    """Convert numeric age to age range string."""
    if age < 25:
        return "young"
    elif age < 40:
        return "adult"
    elif age < 55:
        return "middle-aged"
    else:
        return "elderly"


def _location_to_accent(location: str) -> str:
    """Map UK location to accent hint."""
    LOCATION_ACCENTS = {
        "scotland": "scottish",
        "edinburgh": "scottish_urban",
        "glasgow": "scottish_urban",
        "northern ireland": "ulster",
        "wales": "welsh",
        "manchester": "mancunian",
        "liverpool": "scouse",
        "birmingham": "brummie",
        "newcastle": "geordie",
        "yorkshire": "yorkshire",
        "london": "estuary",
        "essex": "estuary",
        "cornwall": "west_country",
        "devon": "west_country",
        "brighton": "southern",
        "oxford": "rp",
        "cambridge": "rp",
    }

    location_lower = location.lower()
    for region, accent in LOCATION_ACCENTS.items():
        if region in location_lower:
            return accent

    return "neutral_british"


# =============================================================================
# VOICE CACHE FOR COMMON PHRASES
# =============================================================================

COMMON_PHRASES_BY_ARCHETYPE: Dict[str, List[str]] = {
    "prodigy": [
        "I've been analyzing the patterns...",
        "The evidence is clear.",
        "That doesn't add up.",
        "I trust my instincts on this one.",
        "We need to think strategically.",
        "Let me walk you through my reasoning.",
    ],
    "charming_sociopath": [
        "Now, let's not be hasty.",
        "I understand your concerns, but...",
        "We're all in this together.",
        "I have nothing to hide.",
        "Trust is everything in this game.",
        "I would never do that to you.",
    ],
    "bitter_traitor": [
        "I don't owe you an explanation.",
        "You want to blame someone? Fine.",
        "This is exactly what they want.",
        "I've had enough of this.",
        "You'll regret this decision.",
        "Don't say I didn't warn you.",
    ],
    "misguided_survivor": [
        "I... I think we should be careful.",
        "Maybe we're overthinking this?",
        "I just want to make it to the end.",
        "Are we sure about this?",
        "I've made it this far, haven't I?",
        "I'm doing my best here.",
    ],
    "zealot": [
        "This is a matter of principle.",
        "We must do what's right.",
        "I will not compromise on this.",
        "The truth will prevail.",
        "I stand by my convictions.",
        "Justice demands action.",
    ],
    "infatuated_faithful": [
        "I believe in them completely.",
        "They wouldn't do that to me.",
        "We have a connection.",
        "I know their heart.",
        "Love means trust.",
        "I'll stand by them no matter what.",
    ],
    "comedic_psychic": [
        "I'm getting a feeling about this...",
        "The spirits are telling me something!",
        "Wait, wait, I need to read the room.",
        "My sixth sense is tingling!",
        "Don't you see the signs?",
        "It's so obvious, isn't it?",
    ],
    "incompetent_authority": [
        "In my professional experience...",
        "I've seen this before, trust me.",
        "As someone with my background...",
        "This is clearly the answer.",
        "You should listen to me on this.",
        "I know what I'm doing.",
    ],
    "quirky_outsider": [
        "Hmm, interesting.",
        "That's not what I observed.",
        "Everyone's missing the obvious.",
        "I prefer to watch and learn.",
        "The patterns tell a different story.",
        "You might want to reconsider.",
    ],
    "romantic": [
        "I believe in the good in people.",
        "We're a family here.",
        "I couldn't betray my friends.",
        "This breaks my heart.",
        "Love is stronger than deceit.",
        "I won't give up on anyone.",
    ],
    "mischievous_operator": [
        "Ooh, this is getting interesting!",
        "Let me stir the pot a little...",
        "What if we tried something different?",
        "I love a good twist.",
        "Chaos is its own reward.",
        "Watch and learn, everyone.",
    ],
    "smug_player": [
        "I expected better from you all.",
        "Some of us actually think ahead.",
        "It's quite simple, really.",
        "I shouldn't have to explain this.",
        "Perhaps you should pay closer attention.",
        "I'll try to use smaller words.",
    ],
    "charismatic_leader": [
        "Team, we need to stay focused.",
        "I have faith in all of you.",
        "Let's make this decision together.",
        "We're stronger united.",
        "I'll take responsibility for this.",
        "Follow my lead on this one.",
    ],
}


def get_cacheable_phrases(archetype_id: str) -> List[str]:
    """Get phrases that can be pre-generated for zero-latency playback.

    Args:
        archetype_id: Archetype identifier

    Returns:
        List of common phrases for this archetype
    """
    return COMMON_PHRASES_BY_ARCHETYPE.get(archetype_id, [])
