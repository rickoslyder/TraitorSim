# Deepgram STT Client for TraitorSim

Comprehensive Speech-to-Text client for Human-in-the-Loop (HITL) mode using Deepgram API.

## Overview

The Deepgram STT client provides real-time and batch speech-to-text transcription capabilities for TraitorSim's HITL mode, where human players interact with AI agents via voice.

### Features

- **Streaming Transcription**: Real-time WebSocket-based transcription with interim results
- **Batch Transcription**: Single-shot audio file transcription via REST API
- **Voice Activity Detection (VAD)**: Energy-based speech detection
- **Speaker Diarization**: Identify different speakers in multi-speaker scenarios
- **Smart Formatting**: Automatic punctuation, number formatting, date formatting
- **Interim Results**: Get partial transcripts while speech is ongoing
- **Dry-Run Mode**: Development mode without API calls
- **Usage Tracking**: Monitor API usage and estimated costs
- **Error Handling**: Automatic retry with exponential backoff

## Installation

The client requires these dependencies:

```bash
pip install aiohttp numpy
```

For production use with Silero VAD (optional):

```bash
pip install torch onnxruntime  # For Silero VAD
```

## Quick Start

### Basic Usage (Dry-Run Mode)

```python
from traitorsim.voice import create_deepgram_client, DeepgramConfig

# Create client in dry-run mode (no API calls)
client = create_deepgram_client(dry_run=True)

# Transcribe audio
config = DeepgramConfig(
    model="nova-3",
    language="en",
    punctuate=True,
)

result = await client.transcribe_audio(audio_bytes, config)
print(f"Transcript: {result.text}")

await client.close()
```

### Streaming Transcription

```python
from traitorsim.voice import DeepgramClient, DeepgramConfig

client = DeepgramClient(api_key="your-api-key")

# Configure streaming
config = DeepgramConfig(
    model="nova-3",
    interim_results=True,  # Get partial results
    utterance_end_ms=1000,  # Trigger final after 1s silence
)

# Stream audio
async for result in client.transcribe_stream(audio_stream, config):
    if result.is_final:
        print(f"FINAL: {result.text}")
    else:
        print(f"Interim: {result.text}")

await client.close()
```

## API Reference

### DeepgramClient

Main client class for interacting with Deepgram API.

#### Constructor

```python
client = DeepgramClient(
    api_key: Optional[str] = None,  # Or set DEEPGRAM_API_KEY env var
    model: str = "nova-3",           # Default model
    language: str = "en",            # Default language
    dry_run: bool = False,           # Simulate API calls
    log_requests: bool = True,       # Log requests
)
```

#### Methods

##### transcribe_stream()

Stream transcription via WebSocket.

```python
async for result in client.transcribe_stream(
    audio_stream: AsyncIterator[bytes],
    config: Optional[DeepgramConfig] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> AsyncIterator[TranscriptResult]:
    ...
```

**Parameters:**
- `audio_stream`: Async iterator yielding audio chunks (16-bit PCM)
- `config`: Transcription configuration (uses defaults if None)
- `max_retries`: Maximum reconnection attempts on failure
- `retry_delay`: Initial retry delay for exponential backoff

**Returns:** AsyncIterator yielding `TranscriptResult` objects

##### transcribe_audio()

Batch transcription via REST API.

```python
result = await client.transcribe_audio(
    audio_data: bytes,
    config: Optional[DeepgramConfig] = None,
) -> TranscriptResult
```

**Parameters:**
- `audio_data`: Complete audio file as bytes
- `config`: Transcription configuration

**Returns:** Single `TranscriptResult` with complete transcript

##### detect_voice_activity()

Energy-based Voice Activity Detection.

```python
vad_result = client.detect_voice_activity(
    audio_data: bytes,
    sample_rate: int = 16000,
    threshold: float = 0.01,
) -> VADResult
```

**Parameters:**
- `audio_data`: Audio chunk (16-bit PCM)
- `sample_rate`: Audio sample rate in Hz
- `threshold`: Energy threshold for speech detection

**Returns:** `VADResult` with speech detection info

##### get_usage_stats()

Get session usage statistics.

```python
stats = client.get_usage_stats()
# Returns:
# {
#     "total_audio_duration_s": 120.5,
#     "total_requests": 45,
#     "final_transcripts": 30,
#     "interim_transcripts": 15,
#     "estimated_cost_usd": {
#         "pay_as_you_go": 0.0863,
#         "growth": 0.0722,
#         "enterprise": 0.0502,
#     }
# }
```

### DeepgramConfig

Configuration for transcription requests.

```python
config = DeepgramConfig(
    model: str = "nova-3",           # Model to use
    language: str = "en",            # Language code
    punctuate: bool = True,          # Automatic punctuation
    diarize: bool = False,           # Speaker diarization
    smart_format: bool = True,       # Smart number/date formatting
    interim_results: bool = True,    # Return partial transcripts
    utterance_end_ms: int = 1000,    # Silence to trigger utterance end
    vad_events: bool = False,        # Emit VAD events
    profanity_filter: bool = False,  # Filter profanity
    redact: List[str] = [],          # PII to redact ["pci", "ssn"]
    keywords: List[str] = [],        # Boost these keywords
    sample_rate: int = 16000,        # Audio sample rate
    channels: int = 1,               # Audio channels
    encoding: str = "linear16",      # Audio encoding
    endpointing: int = 300,          # Endpointing delay (ms)
)
```

### TranscriptResult

Transcription result with timing and confidence.

```python
@dataclass
class TranscriptResult:
    text: str                      # Transcribed text
    is_final: bool                 # Final or interim result
    confidence: float              # Overall confidence 0.0-1.0
    words: List[WordInfo]          # Word-level timing/confidence
    start_time: float              # Start time in seconds
    end_time: float                # End time in seconds
    speaker_id: Optional[int]      # Speaker ID (if diarization)
    language: Optional[str]        # Detected language
    is_dry_run: bool               # Whether simulated
```

### WordInfo

Word-level timing and confidence.

```python
@dataclass
class WordInfo:
    word: str                      # The word text
    start: float                   # Start time in seconds
    end: float                     # End time in seconds
    confidence: float              # Confidence 0.0-1.0
    speaker: Optional[int]         # Speaker ID (if diarization)
```

### VADResult

Voice Activity Detection result.

```python
@dataclass
class VADResult:
    is_speech: bool                # Speech detected
    confidence: float              # Detection confidence
    duration: float                # Audio duration in seconds
    energy: Optional[float]        # Audio energy level
```

## Models

Deepgram provides several model variants optimized for different use cases:

| Model | Use Case | Accuracy | Speed |
|-------|----------|----------|-------|
| `nova-3` | General purpose (recommended) | Highest | Fast |
| `nova-2` | Previous generation | High | Fast |
| `nova-2-meeting` | Meetings, conferences | High | Fast |
| `nova-2-phonecall` | Phone audio | High | Fast |
| `nova-2-conversationalai` | Chatbots, voice assistants | High | Fast |

For TraitorSim HITL mode, we recommend **`nova-3`** for best accuracy.

## Usage Patterns

### HITL Mode: Real-Time Player Input

```python
from traitorsim.voice import DeepgramClient, DeepgramConfig

client = DeepgramClient(api_key=os.environ["DEEPGRAM_API_KEY"])

# Configure for low-latency streaming
config = DeepgramConfig(
    model="nova-3",
    language="en",
    interim_results=True,
    utterance_end_ms=800,  # Quick response
    endpointing=200,       # Fast endpointing
)

# Stream from microphone
async for result in client.transcribe_stream(mic_stream, config):
    if result.is_final:
        # Send to game engine
        await game.process_player_speech(result.text)
```

### Multi-Speaker Round Table

```python
# Enable speaker diarization
config = DeepgramConfig(
    model="nova-3",
    diarize=True,  # Identify speakers
    punctuate=True,
)

result = await client.transcribe_audio(roundtable_audio, config)

# Group by speaker
for word in result.words:
    print(f"Speaker {word.speaker}: {word.word}")
```

### VAD for Silence Detection

```python
# Detect when player stops speaking
vad = client.detect_voice_activity(
    audio_chunk,
    sample_rate=16000,
    threshold=0.01,
)

if not vad.is_speech:
    print("Player finished speaking, processing response...")
```

## Cost Estimation

The Deepgram client automatically tracks usage and estimates costs:

```python
stats = client.get_usage_stats()

print(f"Total audio: {stats['total_audio_duration_min']:.2f} minutes")
print(f"Estimated cost: ${stats['estimated_cost_usd']['pay_as_you_go']:.4f}")
```

**Pricing** (approximate, as of 2025):
- Pay-as-you-go: $0.0043/minute
- Growth plan: $0.0036/minute
- Enterprise: Custom pricing

For a 60-minute HITL game session with real-time transcription:
- Pay-as-you-go: ~$0.26
- Growth: ~$0.22

## Error Handling

The client includes automatic retry with exponential backoff:

```python
try:
    async for result in client.transcribe_stream(audio_stream, max_retries=3):
        process_transcript(result)
except DeepgramAPIError as e:
    logger.error(f"Transcription failed: {e.status_code} - {e.message}")
    # Fallback to text input
```

## Dry-Run Mode

For development and testing without API calls:

```python
# Automatic dry-run if no API key
client = DeepgramClient()  # No API key → dry-run mode

# Explicit dry-run
client = DeepgramClient(dry_run=True)

# Returns realistic mock transcripts
result = await client.transcribe_audio(audio_bytes)
assert result.is_dry_run == True
```

Dry-run mode:
- Returns plausible mock transcripts
- Simulates realistic latency (~100ms)
- Tracks usage stats (without costs)
- Perfect for testing game logic

## Advanced Features

### Custom Keywords

Boost recognition of game-specific terms:

```python
config = DeepgramConfig(
    keywords=[
        "traitor",
        "faithful",
        "banishment",
        "turret",
        "shield",
        "mission",
    ]
)
```

### PII Redaction

Redact sensitive information:

```python
config = DeepgramConfig(
    redact=["pci", "ssn", "numbers"]  # Redact credit cards, SSNs, numbers
)

result = await client.transcribe_audio(audio, config)
# Numbers will be replaced with [REDACTED]
```

### Utterance Segmentation

Control when to emit final transcripts:

```python
config = DeepgramConfig(
    utterance_end_ms=1500,  # Wait 1.5s of silence before finalizing
    endpointing=500,        # 500ms endpointing delay
)
```

## Integration with TraitorSim HITL Mode

Example integration with game engine:

```python
from traitorsim.voice import DeepgramClient, DeepgramConfig
from traitorsim.core import HITLGameEngine

async def run_hitl_game():
    # Initialize clients
    deepgram = DeepgramClient(api_key=os.environ["DEEPGRAM_API_KEY"])
    game = HITLGameEngine()

    # Configure transcription
    stt_config = DeepgramConfig(
        model="nova-3",
        interim_results=True,
        utterance_end_ms=1000,
    )

    # Stream player input
    async for transcript in deepgram.transcribe_stream(mic_stream, stt_config):
        if transcript.is_final:
            # Process player speech
            response = await game.process_player_input(
                player_id="human_1",
                text=transcript.text,
            )

            # Speak response (via ElevenLabs)
            await speak_response(response)

    await deepgram.close()
```

## Troubleshooting

### WebSocket Connection Issues

If streaming fails:
1. Check API key is valid
2. Verify network connectivity
3. Check firewall allows WebSocket connections
4. Review retry settings

```python
# Increase retries for unstable connections
async for result in client.transcribe_stream(
    audio_stream,
    max_retries=5,      # More retries
    retry_delay=2.0,    # Longer initial delay
):
    ...
```

### Low Transcription Accuracy

If transcripts are inaccurate:
1. Use `nova-3` model for best accuracy
2. Add game-specific keywords
3. Ensure audio quality (16kHz+, low noise)
4. Enable speaker diarization for multi-speaker scenarios

```python
config = DeepgramConfig(
    model="nova-3",
    keywords=["traitor", "faithful", "banishment"],
    smart_format=True,
)
```

### High Latency

For real-time HITL mode, minimize latency:

```python
config = DeepgramConfig(
    model="nova-3",           # Still fast
    interim_results=True,     # Get partial results immediately
    utterance_end_ms=800,     # Quick finalization
    endpointing=200,          # Fast endpointing
)
```

## See Also

- [Deepgram API Documentation](https://developers.deepgram.com/)
- [TraitorSim HITL Mode Design](./VOICE_INTEGRATION_DESIGN.md)
- [ElevenLabs TTS Client](./ELEVENLABS_CLIENT.md)
