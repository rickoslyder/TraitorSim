"""TraitorSim Voice Integration Module.

Provides voice synthesis capabilities for TraitorSim using ElevenLabs API.
Supports two modes:
- Episode Mode: Post-processing game logs into serialized audio drama
- HITL Mode: Real-time voice interaction with AI agents

Usage:
    from traitorsim.voice import (
        VoiceScriptExtractor,
        EpisodeGenerator,
        get_voice_for_persona,
        extract_script_from_game_state,
    )

    # Extract script from game state
    script = extract_script_from_game_state(game_state, day=3)

    # Generate full episode
    generator = EpisodeGenerator()
    episode = generator.generate_episode(day=3, events=events, players=players)

    # Get voice ID for a persona
    voice_id = get_voice_for_persona(persona_data)
"""

# Core data models
from .models import (
    DialogueSegment,
    DialogueScript,
    EpisodeScript,
    VoiceConfig,
    SegmentType,
    EmotionIntensity,
)

# Voice library
from .voice_library import (
    ARCHETYPE_VOICE_PROFILES,
    NARRATOR_VOICE_ID,
    NARRATOR_ALTERNATIVES,
    COMMON_PHRASES_BY_ARCHETYPE,
    get_voice_for_persona,
    get_voice_config_for_persona,
    get_archetype_emotional_range,
    get_cacheable_phrases,
    list_available_voices,
)

# Emotion inference
from .emotion_engine import (
    EmotionInferenceEngine,
    EmotionContext,
    EmotionResult,
    EMOTION_TAGS,
    DELIVERY_TAGS,
    NON_SPEECH_TAGS,
    get_emotion_for_context,
)

# Script extraction
from .script_extractor import (
    VoiceScriptExtractor,
    ExtractionConfig,
    extract_script_from_game_state,
)

# Episode generation
from .episode_generator import (
    EpisodeGenerator,
    EpisodeGeneratorConfig,
    generate_episode_from_game_state,
    export_season_scripts,
)


__all__ = [
    # Models
    "DialogueSegment",
    "DialogueScript",
    "EpisodeScript",
    "VoiceConfig",
    "SegmentType",
    "EmotionIntensity",
    # Voice library
    "ARCHETYPE_VOICE_PROFILES",
    "NARRATOR_VOICE_ID",
    "NARRATOR_ALTERNATIVES",
    "COMMON_PHRASES_BY_ARCHETYPE",
    "get_voice_for_persona",
    "get_voice_config_for_persona",
    "get_archetype_emotional_range",
    "get_cacheable_phrases",
    "list_available_voices",
    # Emotion engine
    "EmotionInferenceEngine",
    "EmotionContext",
    "EmotionResult",
    "EMOTION_TAGS",
    "DELIVERY_TAGS",
    "NON_SPEECH_TAGS",
    "get_emotion_for_context",
    # Script extraction
    "VoiceScriptExtractor",
    "ExtractionConfig",
    "extract_script_from_game_state",
    # Episode generation
    "EpisodeGenerator",
    "EpisodeGeneratorConfig",
    "generate_episode_from_game_state",
    "export_season_scripts",
]


# Version
__version__ = "1.0.0"
