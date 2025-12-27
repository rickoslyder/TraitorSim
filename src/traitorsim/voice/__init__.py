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

# ElevenLabs client
from .elevenlabs_client import (
    ElevenLabsClient,
    ElevenLabsModel,
    ElevenLabsAPIError,
    VoiceSettings,
    SynthesisResult,
    UsageStats,
    create_client,
    quick_synthesize,
)

# Audio assembler
from .audio_assembler import (
    EpisodeAudioAssembler,
    AudioTimeline,
    AudioTrack,
    AudioCue,
    MusicLibrary,
    SFXLibrary,
    MusicMood,
    SFXType,
    SidechainConfig,
    SidechainCompressor,
    assemble_episode_from_script,
    audio_segment_to_numpy,
    numpy_to_audio_segment,
)

# Chapter markers
from .chapters import (
    ChapterMarker,
    ChapterList,
    ChapterType,
    embed_chapters,
    export_chapters_json,
    export_chapters_podlove,
    export_chapters_webvtt,
    generate_episode_chapters,
    ms_to_timecode,
    timecode_to_ms,
)

# Voice cache (HITL latency optimization)
from .voice_cache import (
    VoiceCacheManager,
    CacheEntry,
    CacheStats,
    create_cache_manager,
    warm_game_cache,
)

# Deepgram STT client (HITL speech-to-text)
from .deepgram_client import (
    DeepgramClient,
    DeepgramModel,
    DeepgramConfig,
    DeepgramAPIError,
    TranscriptResult,
    WordInfo,
    VADResult,
    create_client as create_deepgram_client,
    quick_transcribe,
)

# Soundtrack catalog (music and SFX)
from .soundtrack import (
    MusicCue,
    SFXCue,
    PHASE_MUSIC,
    EVENT_STINGS,
    AMBIENT_SOUNDS,
    get_music_for_phase,
    get_sfx_for_event,
    get_ambient_for_location,
)

# HITL voice handler (human input processing)
from .hitl_handler import (
    HITLVoiceHandler,
    IntentClassifier,
    IntentType,
    GamePhase as HITLGamePhase,
    IntentResult,
    ConversationResponse,
    HITLSession,
)

# Round Table voice orchestrator (multi-speaker coordination)
from .roundtable_voice import (
    RoundTableOrchestrator,
    RoundTableState,
    SpeakerPriority,
    SpeakerTurn,
    AccusationContext,
    VotingState,
    RoundTableSession,
    create_roundtable_orchestrator,
    run_orchestrated_roundtable,
)

# HITL WebSocket server
from .hitl_server import (
    HITLServer,
    MessageType,
    AudioFormat,
    AudioConfig,
    ClientSession,
    ServerStats,
    create_hitl_server,
    run_server as run_hitl_server,
)

# HITL game engine variant
from .game_engine_hitl import (
    GameEngineHITL,
    GamePhaseHITL,
    HumanInputRequest,
    create_hitl_game,
    run_hitl_game,
)

# Voice emitter (integration hooks)
from .voice_emitter import (
    VoiceEventType,
    VoiceMode,
    EmotionHint,
    VoiceEvent,
    VoiceEmitter,
    NullVoiceEmitter,
    EpisodeVoiceEmitter,
    HITLVoiceEmitter,
    CompositeVoiceEmitter,
    create_voice_emitter,
    infer_emotion,
)

# Voice analytics (Phase 6: metrics and cost tracking)
from .analytics import (
    VoiceAnalytics,
    MetricsCollector,
    TTSRequestMetrics,
    STTRequestMetrics,
    SessionMetrics,
    LatencyStats,
    TTSRequestTracker,
    create_analytics,
    calculate_credits,
    estimate_cost,
)

# Load testing (Phase 6: concurrent HITL simulation)
from .load_test import (
    LoadTestRunner,
    LoadTestConfig,
    LoadTestResults,
    RequestResult,
    GameSimulation,
    ResourceSample,
    MockTTSClient,
    MockSTTClient,
    MockLLMClient,
    run_quick_test,
    run_stress_test,
    run_soak_test,
    analyze_bottlenecks,
)

# A/B testing (Phase 6: voice experiment framework)
from .ab_testing import (
    ABTestManager,
    Experiment,
    Variant,
    ExperimentStatus,
    ExperimentResults,
    WinnerCriteria,
    ABTestVoiceConfig,
    create_model_comparison_experiment,
    create_stability_experiment,
    create_caching_experiment,
    calculate_confidence_interval,
)

# Aggressive cache (Phase 6: advanced caching strategies)
from .voice_cache import (
    CachePriority,
    SemanticCacheIndex,
    PredictiveCache,
    AggressiveCacheManager,
    create_aggressive_cache,
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
    # ElevenLabs client
    "ElevenLabsClient",
    "ElevenLabsModel",
    "ElevenLabsAPIError",
    "VoiceSettings",
    "SynthesisResult",
    "UsageStats",
    "create_client",
    "quick_synthesize",
    # Audio assembler
    "EpisodeAudioAssembler",
    "AudioTimeline",
    "AudioTrack",
    "AudioCue",
    "MusicLibrary",
    "SFXLibrary",
    "MusicMood",
    "SFXType",
    "SidechainConfig",
    "SidechainCompressor",
    "assemble_episode_from_script",
    "audio_segment_to_numpy",
    "numpy_to_audio_segment",
    # Chapter markers
    "ChapterMarker",
    "ChapterList",
    "ChapterType",
    "embed_chapters",
    "export_chapters_json",
    "export_chapters_podlove",
    "export_chapters_webvtt",
    "generate_episode_chapters",
    "ms_to_timecode",
    "timecode_to_ms",
    # Voice cache
    "VoiceCacheManager",
    "CacheEntry",
    "CacheStats",
    "create_cache_manager",
    "warm_game_cache",
    # Deepgram STT client
    "DeepgramClient",
    "DeepgramModel",
    "DeepgramConfig",
    "DeepgramAPIError",
    "TranscriptResult",
    "WordInfo",
    "VADResult",
    "create_deepgram_client",
    "quick_transcribe",
    # Soundtrack catalog
    "MusicCue",
    "SFXCue",
    "PHASE_MUSIC",
    "EVENT_STINGS",
    "AMBIENT_SOUNDS",
    "get_music_for_phase",
    "get_sfx_for_event",
    "get_ambient_for_location",
    # HITL voice handler
    "HITLVoiceHandler",
    "IntentClassifier",
    "IntentType",
    "HITLGamePhase",
    "IntentResult",
    "ConversationResponse",
    "HITLSession",
    # Round Table orchestrator
    "RoundTableOrchestrator",
    "RoundTableState",
    "SpeakerPriority",
    "SpeakerTurn",
    "AccusationContext",
    "VotingState",
    "RoundTableSession",
    "create_roundtable_orchestrator",
    "run_orchestrated_roundtable",
    # HITL WebSocket server
    "HITLServer",
    "MessageType",
    "AudioFormat",
    "AudioConfig",
    "ClientSession",
    "ServerStats",
    "create_hitl_server",
    "run_hitl_server",
    # HITL game engine
    "GameEngineHITL",
    "GamePhaseHITL",
    "HumanInputRequest",
    "create_hitl_game",
    "run_hitl_game",
    # Voice emitter (integration hooks)
    "VoiceEventType",
    "VoiceMode",
    "EmotionHint",
    "VoiceEvent",
    "VoiceEmitter",
    "NullVoiceEmitter",
    "EpisodeVoiceEmitter",
    "HITLVoiceEmitter",
    "CompositeVoiceEmitter",
    "create_voice_emitter",
    "infer_emotion",
    # Voice analytics (Phase 6)
    "VoiceAnalytics",
    "MetricsCollector",
    "TTSRequestMetrics",
    "STTRequestMetrics",
    "SessionMetrics",
    "LatencyStats",
    "TTSRequestTracker",
    "create_analytics",
    "calculate_credits",
    "estimate_cost",
    # Load testing (Phase 6)
    "LoadTestRunner",
    "LoadTestConfig",
    "LoadTestResults",
    "RequestResult",
    "GameSimulation",
    "ResourceSample",
    "MockTTSClient",
    "MockSTTClient",
    "MockLLMClient",
    "run_quick_test",
    "run_stress_test",
    "run_soak_test",
    "analyze_bottlenecks",
    # A/B testing (Phase 6)
    "ABTestManager",
    "Experiment",
    "Variant",
    "ExperimentStatus",
    "ExperimentResults",
    "WinnerCriteria",
    "ABTestVoiceConfig",
    "create_model_comparison_experiment",
    "create_stability_experiment",
    "create_caching_experiment",
    "calculate_confidence_interval",
    # Aggressive cache (Phase 6)
    "CachePriority",
    "SemanticCacheIndex",
    "PredictiveCache",
    "AggressiveCacheManager",
    "create_aggressive_cache",
]


# Version
__version__ = "3.0.0"  # Phase 6: Production optimization release
