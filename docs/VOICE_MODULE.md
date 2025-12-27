# TraitorSim Voice Module Documentation

Comprehensive documentation for the TraitorSim voice integration system, enabling both post-processed "Episode Mode" audio dramas and real-time "HITL Mode" voice interactions.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Episode Mode](#episode-mode)
5. [HITL Mode](#hitl-mode)
6. [Voice Library](#voice-library)
7. [Audio Assembly](#audio-assembly)
8. [Analytics & Monitoring](#analytics--monitoring)
9. [Load Testing](#load-testing)
10. [A/B Testing](#ab-testing)
11. [Caching Strategies](#caching-strategies)
12. [API Reference](#api-reference)
13. [Configuration](#configuration)
14. [Troubleshooting](#troubleshooting)

---

## Overview

The TraitorSim voice module transforms game simulation output into immersive audio experiences. It supports two primary modes:

### Episode Mode (Post-Processing)
- Batch processes completed game logs into serialized audio drama episodes
- Full music/SFX layering with sidechain compression
- Chapter markers for podcast platforms
- Suitable for publishing as podcast series

### HITL Mode (Real-Time)
- Human-in-the-loop voice interaction with AI agents
- Sub-500ms latency target for natural conversation
- WebSocket-based streaming architecture
- Speech-to-text integration via Deepgram

### Key Features

| Feature | Episode Mode | HITL Mode |
|---------|-------------|-----------|
| TTS Provider | ElevenLabs v3 | ElevenLabs Flash v2.5 |
| Latency | N/A (batch) | <500ms target |
| Music/SFX | Full mixing | Ambient only |
| Chapters | Yes | No |
| Multi-speaker | Sequential | Real-time coordination |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Voice Module Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ Game Engine │───▶│  VoiceEmitter    │───▶│ Mode Router   │  │
│  └─────────────┘    └──────────────────┘    └───────┬───────┘  │
│                                                      │          │
│                    ┌─────────────────────────────────┼──────┐   │
│                    ▼                                 ▼      │   │
│  ┌─────────────────────────────┐  ┌─────────────────────────┐  │
│  │      EPISODE MODE           │  │       HITL MODE         │  │
│  │                             │  │                         │  │
│  │  VoiceScriptExtractor       │  │  DeepgramClient (STT)   │  │
│  │  ↓                          │  │  ↓                      │  │
│  │  EmotionInferenceEngine     │  │  IntentClassifier       │  │
│  │  ↓                          │  │  ↓                      │  │
│  │  ElevenLabsClient (v3)      │  │  HITLVoiceHandler       │  │
│  │  ↓                          │  │  ↓                      │  │
│  │  EpisodeAudioAssembler      │  │  RoundTableOrchestrator │  │
│  │  ↓                          │  │  ↓                      │  │
│  │  ChapterMarker              │  │  ElevenLabsClient(Flash)│  │
│  │  ↓                          │  │  ↓                      │  │
│  │  MP3/WAV Output             │  │  WebSocket Streaming    │  │
│  └─────────────────────────────┘  └─────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   SHARED INFRASTRUCTURE                   │   │
│  │                                                           │   │
│  │  VoiceCacheManager     VoiceAnalytics     ABTestManager  │   │
│  │  AggressiveCacheManager  LoadTestRunner                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Installation

```bash
pip install elevenlabs deepgram-sdk pydub mutagen eyed3
```

### Episode Mode - Generate Episode from Game Log

```python
from traitorsim.voice import (
    EpisodeGenerator,
    generate_episode_from_game_state,
    embed_chapters,
)

# Simple one-liner
audio_path = generate_episode_from_game_state(
    game_state,
    day=3,
    output_path="episode_3.mp3"
)

# Or with full control
generator = EpisodeGenerator()
episode = await generator.generate_episode(
    day=3,
    events=game_state.events,
    players=game_state.players,
    include_music=True,
    include_sfx=True,
)

# Embed chapters for podcast platforms
embed_chapters(episode.audio_path, episode.chapters)
```

### HITL Mode - Real-Time Voice Server

```python
from traitorsim.voice import (
    create_hitl_server,
    run_hitl_server,
    GameEngineHITL,
)

# Start HITL game with voice
game = GameEngineHITL(config)
server = create_hitl_server(game, host="0.0.0.0", port=8765)

# Run server (blocks)
await run_hitl_server(server)
```

---

## Episode Mode

Episode Mode processes completed game logs into polished audio drama episodes.

### Script Extraction

The `VoiceScriptExtractor` transforms game events into dialogue scripts:

```python
from traitorsim.voice import VoiceScriptExtractor, ExtractionConfig

config = ExtractionConfig(
    include_inner_thoughts=True,  # Include character internal monologue
    narrator_style="dramatic",     # dramatic, neutral, documentary
    emotion_inference=True,        # Auto-detect emotions
)

extractor = VoiceScriptExtractor(config)
script = extractor.extract(game_state, day=3)

# Script contains ordered segments
for segment in script.segments:
    print(f"{segment.speaker}: {segment.text}")
    print(f"  Emotion: {segment.emotion}")
    print(f"  Type: {segment.segment_type}")
```

### Emotion Inference

The `EmotionInferenceEngine` analyzes context to determine appropriate voice emotions:

```python
from traitorsim.voice import EmotionInferenceEngine, EmotionContext

engine = EmotionInferenceEngine()

context = EmotionContext(
    speaker_role="traitor",
    game_phase="roundtable",
    is_accused=True,
    trust_level=0.3,
)

emotion = engine.infer(
    text="I assure you, I am completely innocent.",
    context=context,
)
# Returns: EmotionResult(primary="defensive", secondary="nervous", intensity=0.7)
```

### ElevenLabs Speech Synthesis

```python
from traitorsim.voice import ElevenLabsClient, ElevenLabsModel, VoiceSettings

client = ElevenLabsClient(api_key="your-key")

# Quality synthesis for episode mode
result = await client.synthesize(
    text="<emotion=suspicious>Are you hiding something?</emotion>",
    voice_id="narrator_voice_id",
    model=ElevenLabsModel.ELEVEN_V3,  # Highest quality
    settings=VoiceSettings(
        stability=0.5,
        similarity_boost=0.8,
        style=0.3,
    ),
)

# Save audio
with open("segment.mp3", "wb") as f:
    f.write(result.audio_data)
```

### Audio Assembly

The `EpisodeAudioAssembler` combines voice, music, and SFX with professional mixing:

```python
from traitorsim.voice import (
    EpisodeAudioAssembler,
    AudioTimeline,
    MusicMood,
    SFXType,
    SidechainConfig,
)

assembler = EpisodeAudioAssembler(
    sidechain_config=SidechainConfig(
        threshold_db=-20,
        ratio=4.0,
        attack_ms=5,
        release_ms=100,
        makeup_gain_db=0,
    )
)

# Create timeline
timeline = AudioTimeline()

# Add music bed
timeline.add_music(
    mood=MusicMood.SUSPENSE,
    start_ms=0,
    duration_ms=60000,
    volume_db=-15,
)

# Add voice with automatic ducking
for segment in voice_segments:
    timeline.add_voice(
        audio=segment.audio,
        start_ms=segment.start_ms,
        speaker=segment.speaker,
    )

# Add SFX
timeline.add_sfx(
    sfx_type=SFXType.GAVEL,
    start_ms=voting_start_ms,
)

# Export with sidechain compression (music ducks under voice)
episode_audio = await assembler.export(
    timeline,
    format="mp3",
    bitrate=192,
)
```

### Chapter Markers

Embed chapter markers for podcast platforms:

```python
from traitorsim.voice import (
    ChapterMarker,
    ChapterList,
    ChapterType,
    generate_episode_chapters,
    embed_chapters,
    export_chapters_json,
    export_chapters_podlove,
)

# Auto-generate from events
chapters = generate_episode_chapters(episode_events)

# Or create manually
chapters = ChapterList([
    ChapterMarker(
        title="Morning at the Castle",
        start_ms=0,
        chapter_type=ChapterType.BREAKFAST,
        description="The contestants gather after a tense night...",
    ),
    ChapterMarker(
        title="The Vault Challenge",
        start_ms=180000,
        chapter_type=ChapterType.MISSION,
    ),
    ChapterMarker(
        title="Round Table Vote",
        start_ms=420000,
        chapter_type=ChapterType.ROUNDTABLE,
    ),
])

# Embed in MP3
embed_chapters("episode.mp3", chapters)

# Export for different platforms
export_chapters_json(chapters, "chapters.json")
export_chapters_podlove(chapters, "chapters.psc")
```

---

## HITL Mode

HITL (Human-in-the-Loop) mode enables real-time voice interaction with AI agents.

### Speech-to-Text with Deepgram

```python
from traitorsim.voice import (
    DeepgramClient,
    DeepgramModel,
    DeepgramConfig,
)

client = DeepgramClient(api_key="your-key")

config = DeepgramConfig(
    model=DeepgramModel.NOVA_2,
    language="en-US",
    punctuate=True,
    smart_format=True,
    vad=True,  # Voice Activity Detection
)

# Transcribe audio
result = await client.transcribe(
    audio_data,
    config=config,
)

print(f"Transcript: {result.text}")
print(f"Confidence: {result.confidence}")
for word in result.words:
    print(f"  {word.word} ({word.start_ms}-{word.end_ms})")
```

### Intent Classification

```python
from traitorsim.voice import IntentClassifier, IntentType

classifier = IntentClassifier()

result = classifier.classify(
    text="I think Marcus is definitely a traitor",
    game_phase="roundtable",
)

print(f"Intent: {result.intent}")  # IntentType.ACCUSATION
print(f"Target: {result.target}")  # "Marcus"
print(f"Confidence: {result.confidence}")
```

### HITL Voice Handler

The `HITLVoiceHandler` manages conversation flow with human players:

```python
from traitorsim.voice import HITLVoiceHandler, HITLSession

handler = HITLVoiceHandler(
    game_engine=game,
    tts_client=tts_client,
    stt_client=stt_client,
)

session = HITLSession(
    player_id="human_player",
    voice_id="human_voice_id",
)

# Process human speech
response = await handler.process_speech(
    audio_data=audio_bytes,
    session=session,
)

# Response contains AI agent's response audio
await websocket.send(response.audio_data)
```

### Round Table Orchestrator

Manages multi-speaker coordination during debates:

```python
from traitorsim.voice import (
    RoundTableOrchestrator,
    SpeakerPriority,
    create_roundtable_orchestrator,
)

orchestrator = create_roundtable_orchestrator(
    game=game,
    tts_client=tts_client,
    human_player_id="human_player",
)

# Run orchestrated round table
async for event in orchestrator.run():
    if event.type == "speech":
        # Stream audio to clients
        await broadcast(event.audio_data)
    elif event.type == "human_turn":
        # Wait for human input
        audio = await wait_for_human_speech()
        orchestrator.submit_human_input(audio)
```

### WebSocket Server

```python
from traitorsim.voice import (
    create_hitl_server,
    run_hitl_server,
    AudioFormat,
    AudioConfig,
)

server = create_hitl_server(
    game=game,
    host="0.0.0.0",
    port=8765,
    audio_config=AudioConfig(
        format=AudioFormat.PCM_16,
        sample_rate=24000,
        channels=1,
    ),
)

# Message protocol
# Client -> Server: {"type": "audio", "data": "<base64>"}
# Client -> Server: {"type": "intent", "text": "I accuse Marcus"}
# Server -> Client: {"type": "speech", "speaker": "narrator", "audio": "<base64>"}
# Server -> Client: {"type": "turn_start", "speaker": "human"}

await run_hitl_server(server)
```

---

## Voice Library

The voice library maps character archetypes to ElevenLabs voices:

```python
from traitorsim.voice import (
    ARCHETYPE_VOICE_PROFILES,
    get_voice_for_persona,
    get_voice_config_for_persona,
    list_available_voices,
)

# Get voice for a persona
voice_id = get_voice_for_persona(persona_data)

# Get full voice config with settings
config = get_voice_config_for_persona(persona_data)
print(f"Voice ID: {config.voice_id}")
print(f"Stability: {config.stability}")
print(f"Style: {config.style}")

# List all available voices
voices = list_available_voices()
for voice in voices:
    print(f"{voice.name}: {voice.description}")
```

### Archetype Voice Mapping

| Archetype | Voice Profile | Characteristics |
|-----------|--------------|-----------------|
| The Prodigy | Young, energetic | High clarity, upbeat |
| The Sage | Mature, authoritative | Deep, measured |
| The Charming Sociopath | Warm, persuasive | Smooth, controlled |
| The Paranoid | Tense, rapid | Higher pitch, nervous |
| The Underdog | Earnest, vulnerable | Soft, hesitant |

---

## Analytics & Monitoring

### Voice Analytics

Track TTS/STT usage, costs, and performance:

```python
from traitorsim.voice import (
    VoiceAnalytics,
    create_analytics,
)

analytics = create_analytics(storage_path="./analytics")

# Start session
session_id = analytics.start_session(
    game_id="game_001",
    mode="hitl",
)

# Track requests (use context manager)
with analytics.track_tts_request(
    voice_id="voice_123",
    model="eleven_flash_v2_5",
    text_length=150,
) as tracker:
    audio = await tts_client.synthesize(text)
    tracker.set_success(audio_size=len(audio))

# End session and get metrics
metrics = analytics.end_session(session_id)

print(f"Total TTS requests: {metrics.tts_request_count}")
print(f"Total TTS credits: {metrics.tts_credits_used:.2f}")
print(f"P95 latency: {metrics.latency_stats.p95:.0f}ms")
print(f"Cache hit rate: {metrics.cache_hit_rate:.1%}")

# Project season costs
projection = analytics.project_season_cost(
    days=12,
    players=22,
    mode="hitl",
    plan="creator",
)
print(f"Estimated cost: ${projection['total_cost']:.2f}")
```

### Cost Tracking

```python
from traitorsim.voice import calculate_credits, estimate_cost

# Calculate credits for text
credits = calculate_credits(text_length=1000, model="eleven_v3")  # 1000 chars = 1000 credits

# Estimate dollar cost
cost = estimate_cost(credits=1000, plan="creator")  # Returns USD

# ElevenLabs pricing (as of 2024)
# - eleven_v3: 1.0 credit/char
# - eleven_flash_v2_5: 0.5 credit/char
# - eleven_turbo_v2_5: 0.25 credit/char

# Plan pricing
# - Free: $0 (10K chars/month)
# - Starter: $5 (30K chars/month)
# - Creator: $22 (100K chars/month)
# - Pro: $99 (500K chars/month)
```

---

## Load Testing

Test concurrent HITL game capacity:

```python
from traitorsim.voice import (
    LoadTestRunner,
    LoadTestConfig,
    run_quick_test,
    run_stress_test,
    analyze_bottlenecks,
)

# Quick test (1 game, 60 seconds)
results = await run_quick_test()
print(f"Success rate: {results.success_rate:.1%}")
print(f"P95 latency: {results.latency_p95:.0f}ms")

# Stress test (ramp up to 10 concurrent games)
results_list = await run_stress_test(
    max_concurrent_games=10,
    ramp_up_seconds=60,
)

for r in results_list:
    print(f"{r.concurrent_games} games: {r.success_rate:.1%}")

# Custom configuration
config = LoadTestConfig(
    concurrent_games=5,
    duration_seconds=300,
    requests_per_second_target=50,
    include_warmup=True,
    warmup_seconds=30,
    monitor_resources=True,
)

runner = LoadTestRunner(config)
results = await runner.run()

# Analyze bottlenecks
analysis = analyze_bottlenecks(results)
print(f"Bottleneck: {analysis['primary_bottleneck']}")
print(f"Recommendations: {analysis['recommendations']}")
```

---

## A/B Testing

Run experiments to optimize voice configurations:

```python
from traitorsim.voice import (
    ABTestManager,
    Experiment,
    Variant,
    create_model_comparison_experiment,
    calculate_confidence_interval,
)

manager = ABTestManager()

# Use pre-built experiment
experiment = create_model_comparison_experiment()
manager.register_experiment(experiment)

# Get variant for user
variant = manager.get_variant("tts_model_comparison", user_id="player_123")
print(f"Using model: {variant.config['model']}")

# Record outcome after request
manager.record_outcome(
    experiment_name="tts_model_comparison",
    user_id="player_123",
    latency_ms=320,
    quality_score=4.5,
    success=True,
)

# Complete experiment and get results
results = manager.complete_experiment("tts_model_comparison")
print(f"Winner: {results.winner}")
print(f"Statistical significance: {results.is_significant}")
print(f"P-value: {results.p_value:.4f}")
```

### Pre-Built Experiments

```python
from traitorsim.voice import (
    create_model_comparison_experiment,
    create_stability_experiment,
    create_caching_experiment,
)

# Compare v3 vs Flash models
model_exp = create_model_comparison_experiment()

# Test voice stability settings
stability_exp = create_stability_experiment()

# Evaluate caching strategies
cache_exp = create_caching_experiment()
```

---

## Caching Strategies

### Basic Caching

```python
from traitorsim.voice import (
    VoiceCacheManager,
    create_cache_manager,
    warm_game_cache,
)

cache = create_cache_manager(
    cache_dir="./voice_cache",
    max_size_mb=500,
    ttl_hours=24,
)

# Check cache before synthesis
cached = await cache.get(text, voice_id, model)
if cached:
    return cached

# Synthesize and cache
audio = await tts_client.synthesize(text)
await cache.put(text, voice_id, model, audio)

# Pre-warm cache for common phrases
await warm_game_cache(
    cache=cache,
    tts_client=tts_client,
    archetypes=["The Sage", "The Prodigy"],
)
```

### Aggressive Caching (Phase 6)

Advanced caching with semantic similarity and predictive prefetching:

```python
from traitorsim.voice import (
    AggressiveCacheManager,
    create_aggressive_cache,
    CachePriority,
)

cache = create_aggressive_cache(
    cache_dir="./voice_cache",
    max_size_mb=1000,
    semantic_threshold=0.85,  # Jaccard similarity threshold
    enable_compression=True,
)

# Semantic cache lookup (finds similar phrases)
audio = await cache.get_semantic(
    text="I believe Marcus is the traitor",
    voice_id=voice_id,
    model=model,
)
# May return cached audio for "I think Marcus is a traitor"

# Or use get_or_synthesize for automatic fallback
audio = await cache.get_or_synthesize_semantic(
    text=text,
    voice_id=voice_id,
    model=model,
    synthesize_fn=tts_client.synthesize,
    priority=CachePriority.HIGH,
)

# Predictive caching on phase changes
await cache.on_phase_change(
    new_phase="roundtable",
    narrator_voice_id=narrator_id,
)
# Pre-fetches likely phrases like "The votes are in"
```

### Cache Priority Levels

| Priority | Eviction Order | Use Cases |
|----------|---------------|-----------|
| CRITICAL | Last | Narrator intros, key phrases |
| HIGH | Third | Player-specific common phrases |
| MEDIUM | Second | General dialogue |
| LOW | First | One-time utterances |

---

## API Reference

### Core Classes

| Class | Module | Description |
|-------|--------|-------------|
| `ElevenLabsClient` | `elevenlabs_client` | TTS synthesis client |
| `DeepgramClient` | `deepgram_client` | STT transcription client |
| `VoiceScriptExtractor` | `script_extractor` | Game-to-script conversion |
| `EmotionInferenceEngine` | `emotion_engine` | Context-aware emotion detection |
| `EpisodeAudioAssembler` | `audio_assembler` | Multi-track audio mixing |
| `VoiceCacheManager` | `voice_cache` | Audio caching layer |
| `HITLVoiceHandler` | `hitl_handler` | Real-time interaction handler |
| `RoundTableOrchestrator` | `roundtable_voice` | Multi-speaker coordination |
| `VoiceAnalytics` | `analytics` | Metrics and cost tracking |
| `LoadTestRunner` | `load_test` | Concurrent load testing |
| `ABTestManager` | `ab_testing` | Experiment management |

### Factory Functions

```python
# Clients
create_client(api_key) -> ElevenLabsClient
create_deepgram_client(api_key) -> DeepgramClient

# Episode generation
generate_episode_from_game_state(state, day, output_path) -> Path

# HITL
create_hitl_server(game, host, port) -> HITLServer
create_roundtable_orchestrator(game, tts_client, human_id) -> RoundTableOrchestrator

# Caching
create_cache_manager(cache_dir, max_size_mb, ttl_hours) -> VoiceCacheManager
create_aggressive_cache(cache_dir, max_size_mb, semantic_threshold) -> AggressiveCacheManager

# Analytics
create_analytics(storage_path) -> VoiceAnalytics

# Testing
run_quick_test(concurrent_games, duration_seconds) -> LoadTestResults
run_stress_test(max_concurrent_games, ramp_up_seconds) -> List[LoadTestResults]
```

---

## Configuration

### Environment Variables

```bash
# Required
ELEVENLABS_API_KEY=your_elevenlabs_key
DEEPGRAM_API_KEY=your_deepgram_key

# Optional
VOICE_CACHE_DIR=/path/to/cache
VOICE_CACHE_MAX_MB=500
VOICE_LOG_LEVEL=INFO
```

### Configuration Objects

```python
from traitorsim.voice import (
    EpisodeGeneratorConfig,
    ExtractionConfig,
    DeepgramConfig,
    AudioConfig,
    LoadTestConfig,
)

# Episode generation
episode_config = EpisodeGeneratorConfig(
    include_music=True,
    include_sfx=True,
    narrator_style="dramatic",
    sidechain_enabled=True,
    output_format="mp3",
    bitrate=192,
)

# Script extraction
extraction_config = ExtractionConfig(
    include_inner_thoughts=True,
    narrator_style="dramatic",
    emotion_inference=True,
    max_segment_length=500,
)

# STT
stt_config = DeepgramConfig(
    model=DeepgramModel.NOVA_2,
    language="en-US",
    punctuate=True,
    smart_format=True,
    vad=True,
    interim_results=True,
)
```

---

## Troubleshooting

### Common Issues

#### "Rate limit exceeded" from ElevenLabs

```python
# Use caching to reduce API calls
cache = create_aggressive_cache(cache_dir="./cache")

# Use Flash model for lower credit consumption
model = ElevenLabsModel.ELEVEN_FLASH_V2_5  # 0.5 credits vs 1.0 for v3
```

#### High latency in HITL mode

```python
# 1. Use Flash model
model = ElevenLabsModel.ELEVEN_FLASH_V2_5

# 2. Enable aggressive caching
cache = create_aggressive_cache(semantic_threshold=0.80)

# 3. Pre-warm cache on phase transitions
await cache.on_phase_change(new_phase)

# 4. Reduce audio quality for faster streaming
client.default_output_format = "mp3_22050_32"
```

#### Memory issues with audio processing

```python
# Use streaming for large episodes
async for chunk in assembler.export_streaming(timeline):
    output_file.write(chunk)

# Limit concurrent synthesis
semaphore = asyncio.Semaphore(5)
async with semaphore:
    audio = await client.synthesize(text)
```

#### Chapter embedding fails

```python
# Ensure eyed3 is installed
pip install eyed3

# For M4A files, use mutagen
from traitorsim.voice import embed_chapters
embed_chapters("episode.m4a", chapters)  # Auto-detects format
```

### Debug Logging

```python
import logging

# Enable debug logging for voice module
logging.getLogger("traitorsim.voice").setLevel(logging.DEBUG)

# Or specific modules
logging.getLogger("traitorsim.voice.elevenlabs_client").setLevel(logging.DEBUG)
logging.getLogger("traitorsim.voice.voice_cache").setLevel(logging.DEBUG)
```

### Performance Profiling

```python
from traitorsim.voice import VoiceAnalytics, analyze_bottlenecks, LoadTestRunner

# Use analytics for per-request metrics
analytics = create_analytics()
session_id = analytics.start_session(game_id, mode="hitl")

# ... run game ...

metrics = analytics.end_session(session_id)
print(metrics.to_report())

# Run load test for capacity planning
results = await LoadTestRunner(config).run()
analysis = analyze_bottlenecks(results)
print(analysis)
```

---

## Version History

| Version | Release | Highlights |
|---------|---------|------------|
| 3.0.0 | Phase 6 | Analytics, load testing, A/B testing, aggressive caching |
| 2.1.0 | Phase 5 | Voice emitter integration hooks |
| 2.0.0 | Phase 4 | HITL mode, WebSocket server, Round Table orchestrator |
| 1.2.0 | Phase 3 | Chapter markers, sidechain compression |
| 1.1.0 | Phase 2 | Audio assembly, music/SFX integration |
| 1.0.0 | Phase 1 | Core TTS, script extraction, emotion inference |

---

## See Also

- [VOICE_INTEGRATION_DESIGN.md](./VOICE_INTEGRATION_DESIGN.md) - Original design document
- [CLAUDE.md](../CLAUDE.md) - TraitorSim project overview
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
