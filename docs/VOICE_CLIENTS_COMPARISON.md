# TraitorSim Voice Clients Comparison

## ElevenLabs TTS Client vs Deepgram STT Client

| Feature | ElevenLabs (TTS) | Deepgram (STT) |
|---------|------------------|----------------|
| **Purpose** | Text-to-Speech synthesis | Speech-to-Text transcription |
| **Use Case** | Episode Mode, HITL responses | HITL player input |
| **API Type** | REST (batch), WebSocket (stream) | REST (batch), WebSocket (stream) |
| **Models** | 5 models (v3, Flash, etc.) | 14+ models (Nova-3, etc.) |
| **Dry-Run Mode** | ✓ Yes | ✓ Yes |
| **Usage Tracking** | ✓ Yes | ✓ Yes |
| **Cost Estimation** | ✓ Yes | ✓ Yes |
| **File Size** | 770 lines | 815 lines |

## Common Patterns

Both clients follow the same architectural patterns:

1. **Dry-Run Mode**: Development without API calls
2. **Usage Stats**: Track API usage and costs
3. **Async/Await**: Full async support
4. **Error Handling**: Retry logic with exponential backoff
5. **Configuration**: Dataclass-based configuration
6. **Type Hints**: Comprehensive type annotations
7. **Logging**: Structured logging support

## Example Usage Together

```python
from traitorsim.voice import (
    ElevenLabsClient,
    DeepgramClient,
    DeepgramConfig,
)

# HITL game loop
async def hitl_round_table(game, player_audio_stream):
    # Initialize clients
    deepgram = DeepgramClient(api_key=DG_KEY)
    elevenlabs = ElevenLabsClient(api_key=EL_KEY)

    # Configure STT
    stt_config = DeepgramConfig(
        model="nova-3",
        interim_results=True,
        utterance_end_ms=1000,
    )

    # Transcribe player speech
    async for transcript in deepgram.transcribe_stream(player_audio_stream, stt_config):
        if transcript.is_final:
            # Player finished speaking
            response = await game.process_player_input(transcript.text)

            # Synthesize agent response
            audio = await elevenlabs.text_to_speech(
                text=response.text,
                voice_id=response.agent_voice_id,
                model="eleven_flash_v2_5",  # Low latency
            )

            # Play audio
            await play_audio(audio.audio_data)

    await deepgram.close()
    await elevenlabs.close()
```

## Cost Analysis

For a 60-minute HITL game with 4 players:

**Deepgram STT:**
- 60 minutes of audio
- Nova-3 model
- Cost: ~$0.26 (pay-as-you-go)

**ElevenLabs TTS:**
- ~500 AI responses
- ~10,000 characters
- Flash model (0.5 credits/char)
- Cost: ~$0.99 (pro plan)

**Total per game:** ~$1.25

## Architecture Comparison

### ElevenLabs Client Structure

```
elevenlabs_client.py (770 lines)
├── Enums
│   └── ElevenLabsModel
├── Dataclasses
│   ├── VoiceSettings
│   ├── SynthesisResult
│   └── UsageStats
├── Client
│   ├── text_to_speech()
│   ├── text_to_speech_stream()
│   ├── text_to_dialogue()
│   ├── list_voices()
│   └── get_subscription_info()
└── Helpers
    ├── create_client()
    └── quick_synthesize()
```

### Deepgram Client Structure

```
deepgram_client.py (815 lines)
├── Enums
│   └── DeepgramModel
├── Dataclasses
│   ├── WordInfo
│   ├── TranscriptResult
│   ├── VADResult
│   ├── DeepgramConfig
│   └── UsageStats
├── Client
│   ├── transcribe_stream()
│   ├── transcribe_audio()
│   ├── detect_voice_activity()
│   └── get_usage_stats()
└── Helpers
    ├── create_client()
    └── quick_transcribe()
```

## Performance Characteristics

| Metric | ElevenLabs | Deepgram |
|--------|------------|----------|
| **Latency (Stream)** | 75-150ms | 100-200ms |
| **Latency (Batch)** | 500-2000ms | 300-1000ms |
| **Throughput** | ~150 chars/s | ~3x real-time |
| **Max Audio Length** | Unlimited | Unlimited |

## Integration with HITL Mode

### Player Input Pipeline

```
Microphone → Audio Chunks → Deepgram STT → Game Engine
```

```python
async def capture_player_input(player_id: str):
    deepgram = DeepgramClient()

    # Stream from microphone
    async for transcript in deepgram.transcribe_stream(mic_stream):
        if transcript.is_final:
            await game.submit_player_action(
                player_id=player_id,
                text=transcript.text,
            )
```

### Agent Response Pipeline

```
Game Engine → Response Text → ElevenLabs TTS → Audio Output
```

```python
async def synthesize_agent_response(agent_id: str, text: str):
    elevenlabs = ElevenLabsClient()

    # Get agent's voice
    voice_id = get_voice_for_agent(agent_id)

    # Stream synthesis for low latency
    async for chunk in elevenlabs.text_to_speech_stream(text, voice_id):
        await audio_player.queue_chunk(chunk)
```

## Development Workflow

### Without API Keys (Dry-Run Mode)

Both clients support development without API keys:

```python
# Automatic dry-run when no API key
deepgram = DeepgramClient()  # DEEPGRAM_API_KEY not set
elevenlabs = ElevenLabsClient()  # ELEVENLABS_API_KEY not set

# Both return realistic mock data
transcript = await deepgram.transcribe_audio(audio)
audio = await elevenlabs.text_to_speech(text, voice_id)

assert transcript.is_dry_run == True
assert audio.is_dry_run == True
```

### Testing

Both clients track usage for testing:

```python
async def test_hitl_session():
    deepgram = DeepgramClient(dry_run=True)
    elevenlabs = ElevenLabsClient(dry_run=True)

    # Run game session
    await run_game_session(deepgram, elevenlabs)

    # Verify usage
    stt_stats = deepgram.get_usage_stats()
    tts_stats = elevenlabs.get_usage_stats()

    assert stt_stats['total_requests'] > 0
    assert tts_stats['total_requests'] > 0
```

## Future Enhancements

### Deepgram

- [ ] Silero VAD integration (more accurate than energy-based)
- [ ] WebRTC audio preprocessing
- [ ] Custom vocabulary for game-specific terms
- [ ] Real-time language detection
- [ ] Sentiment analysis integration

### ElevenLabs

- [ ] Voice cloning for custom player voices
- [ ] Emotion control API integration
- [ ] Multi-voice scene generation
- [ ] Background music mixing
- [ ] Voice effects (radio, phone, etc.)

### Integration

- [ ] Unified voice session manager
- [ ] Audio pipeline with VAD + STT + TTS
- [ ] Latency optimization (<100ms total)
- [ ] Multi-language HITL support
- [ ] Voice activity visualization
