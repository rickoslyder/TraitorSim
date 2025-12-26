"""Deepgram STT client for TraitorSim real-time speech transcription.

Provides a comprehensive wrapper around Deepgram API for Human-in-the-Loop (HITL)
mode where human players need real-time speech-to-text transcription.

Supports:
- Streaming transcription via WebSocket
- Single-shot audio file transcription
- Voice Activity Detection (VAD)
- Interim (partial) and final transcripts
- Speaker diarization
- Automatic punctuation and smart formatting
- Dry-run mode for development without API calls

Usage:
    from traitorsim.voice import DeepgramClient

    # Initialize client
    client = DeepgramClient(api_key="your-key")

    # Stream transcription
    async for result in client.transcribe_stream(audio_stream):
        if result.is_final:
            print(f"Final: {result.text}")
        else:
            print(f"Interim: {result.text}")

    # Dry-run mode (no API calls, returns mock data)
    client = DeepgramClient(dry_run=True)
"""

import os
import asyncio
import aiohttp
import logging
import json
import time
import numpy as np
from typing import Dict, List, Optional, Any, AsyncIterator, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DeepgramModel(str, Enum):
    """Available Deepgram models."""
    NOVA_3 = "nova-3"              # Latest, most accurate (default)
    NOVA_2 = "nova-2"              # Previous generation
    NOVA_2_GENERAL = "nova-2-general"  # General purpose
    NOVA_2_MEETING = "nova-2-meeting"  # Optimized for meetings
    NOVA_2_PHONECALL = "nova-2-phonecall"  # Phone audio
    NOVA_2_VOICEMAIL = "nova-2-voicemail"  # Voicemail
    NOVA_2_FINANCE = "nova-2-finance"  # Financial terminology
    NOVA_2_CONVERSATIONALAI = "nova-2-conversationalai"  # Chatbots
    NOVA_2_VIDEO = "nova-2-video"  # Video content
    NOVA_2_MEDICAL = "nova-2-medical"  # Medical terminology
    NOVA_2_DRIVETHRU = "nova-2-drivethru"  # Drive-thru audio
    NOVA_2_AUTOMOTIVE = "nova-2-automotive"  # Automotive
    ENHANCED = "enhanced"          # Legacy enhanced model
    BASE = "base"                  # Legacy base model


@dataclass
class WordInfo:
    """Individual word timing and confidence information."""
    word: str                      # The word text
    start: float                   # Start time in seconds
    end: float                     # End time in seconds
    confidence: float              # Confidence score 0.0-1.0
    speaker: Optional[int] = None  # Speaker ID (if diarization enabled)

    @classmethod
    def from_deepgram(cls, data: Dict[str, Any]) -> "WordInfo":
        """Create from Deepgram API response."""
        return cls(
            word=data.get("word", ""),
            start=data.get("start", 0.0),
            end=data.get("end", 0.0),
            confidence=data.get("confidence", 0.0),
            speaker=data.get("speaker"),
        )


@dataclass
class TranscriptResult:
    """Result from a transcription request."""
    text: str                      # Transcribed text
    is_final: bool                 # Whether this is a final result
    confidence: float              # Overall confidence 0.0-1.0
    words: List[WordInfo]          # Word-level timing/confidence
    start_time: float              # Transcript start time in seconds
    end_time: float                # Transcript end time in seconds
    speaker_id: Optional[int] = None  # Speaker ID (if diarization enabled)
    language: Optional[str] = None    # Detected language
    is_dry_run: bool = False       # Whether this was a simulated result

    @classmethod
    def from_deepgram(cls, data: Dict[str, Any], is_final: bool = True) -> "TranscriptResult":
        """Create from Deepgram API response.

        Args:
            data: Deepgram channel data
            is_final: Whether this is a final transcript

        Returns:
            TranscriptResult instance
        """
        alternatives = data.get("alternatives", [{}])
        if not alternatives:
            alternatives = [{}]

        best = alternatives[0]
        words_data = best.get("words", [])
        words = [WordInfo.from_deepgram(w) for w in words_data]

        # Calculate time range
        start_time = words[0].start if words else 0.0
        end_time = words[-1].end if words else 0.0

        return cls(
            text=best.get("transcript", ""),
            is_final=is_final,
            confidence=best.get("confidence", 0.0),
            words=words,
            start_time=start_time,
            end_time=end_time,
            language=data.get("detected_language"),
        )


@dataclass
class VADResult:
    """Voice Activity Detection result."""
    is_speech: bool                # Whether speech was detected
    confidence: float              # Detection confidence 0.0-1.0
    duration: float                # Duration of audio segment in seconds
    energy: Optional[float] = None # Audio energy level (if using energy-based VAD)

    @classmethod
    def from_audio(cls, audio_data: bytes, sample_rate: int = 16000, threshold: float = 0.01) -> "VADResult":
        """Simple energy-based VAD.

        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            sample_rate: Audio sample rate
            threshold: Energy threshold for speech detection

        Returns:
            VADResult
        """
        # Convert bytes to numpy array
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception:
            # Return no speech if we can't parse audio
            return cls(is_speech=False, confidence=0.0, duration=0.0, energy=0.0)

        # Calculate energy (RMS)
        energy = float(np.sqrt(np.mean(audio_array ** 2)))

        # Calculate duration
        duration = len(audio_array) / sample_rate

        # Determine if speech
        is_speech = energy > threshold
        confidence = min(1.0, energy / threshold) if is_speech else 0.0

        return cls(
            is_speech=is_speech,
            confidence=confidence,
            duration=duration,
            energy=energy,
        )


@dataclass
class DeepgramConfig:
    """Configuration for Deepgram transcription."""
    model: str = DeepgramModel.NOVA_3.value  # Model to use
    language: str = "en"                     # Language code (en, es, fr, etc.)
    punctuate: bool = True                   # Automatic punctuation
    diarize: bool = False                    # Speaker diarization
    smart_format: bool = True                # Smart formatting (numbers, dates, etc.)
    interim_results: bool = True             # Return interim transcripts
    utterance_end_ms: int = 1000             # Silence duration to trigger utterance end
    vad_events: bool = False                 # Emit VAD events
    profanity_filter: bool = False           # Filter profanity
    redact: List[str] = field(default_factory=list)  # PII to redact (e.g., ["pci", "ssn"])
    keywords: List[str] = field(default_factory=list)  # Boost these keywords
    sample_rate: int = 16000                 # Audio sample rate
    channels: int = 1                        # Audio channels
    encoding: str = "linear16"               # Audio encoding
    endpointing: int = 300                   # Endpointing delay (ms)

    def to_params(self) -> Dict[str, Any]:
        """Convert to Deepgram API query parameters."""
        params = {
            "model": self.model,
            "language": self.language,
            "punctuate": str(self.punctuate).lower(),
            "diarize": str(self.diarize).lower(),
            "smart_format": str(self.smart_format).lower(),
            "interim_results": str(self.interim_results).lower(),
            "utterance_end_ms": str(self.utterance_end_ms),
            "vad_events": str(self.vad_events).lower(),
            "profanity_filter": str(self.profanity_filter).lower(),
            "endpointing": str(self.endpointing),
            "sample_rate": str(self.sample_rate),
            "channels": str(self.channels),
            "encoding": self.encoding,
        }

        if self.redact:
            params["redact"] = ",".join(self.redact)

        if self.keywords:
            params["keywords"] = ",".join(self.keywords)

        return params


@dataclass
class UsageStats:
    """Track API usage for monitoring."""
    total_audio_duration_s: float = 0.0      # Total audio processed (seconds)
    total_requests: int = 0                   # Total requests made
    total_errors: int = 0                     # Total errors encountered
    requests_by_model: Dict[str, int] = field(default_factory=dict)
    audio_by_model: Dict[str, float] = field(default_factory=dict)
    final_transcripts: int = 0                # Final transcript count
    interim_transcripts: int = 0              # Interim transcript count

    def record_request(self, model: str, duration_s: float, is_final: bool = True):
        """Record a transcription request."""
        self.total_audio_duration_s += duration_s
        self.total_requests += 1
        self.requests_by_model[model] = self.requests_by_model.get(model, 0) + 1
        self.audio_by_model[model] = self.audio_by_model.get(model, 0.0) + duration_s

        if is_final:
            self.final_transcripts += 1
        else:
            self.interim_transcripts += 1

    def record_error(self):
        """Record an error."""
        self.total_errors += 1

    def estimate_cost_usd(self, plan: str = "pay_as_you_go") -> float:
        """Estimate USD cost based on audio duration.

        Args:
            plan: Deepgram plan (pay_as_you_go, growth, enterprise)

        Returns:
            Estimated cost in USD
        """
        # Cost per minute by plan (approximate for Nova-3)
        cost_per_minute = {
            "pay_as_you_go": 0.0043,    # $0.0043/min
            "growth": 0.0036,            # $0.0036/min
            "enterprise": 0.0025,        # Custom pricing, approximate
        }

        rate = cost_per_minute.get(plan, cost_per_minute["pay_as_you_go"])
        minutes = self.total_audio_duration_s / 60
        return minutes * rate

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "total_audio_duration_s": round(self.total_audio_duration_s, 2),
            "total_audio_duration_min": round(self.total_audio_duration_s / 60, 2),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "final_transcripts": self.final_transcripts,
            "interim_transcripts": self.interim_transcripts,
            "requests_by_model": self.requests_by_model,
            "audio_by_model": {k: round(v, 2) for k, v in self.audio_by_model.items()},
            "estimated_cost_usd": {
                "pay_as_you_go": round(self.estimate_cost_usd("pay_as_you_go"), 4),
                "growth": round(self.estimate_cost_usd("growth"), 4),
                "enterprise": round(self.estimate_cost_usd("enterprise"), 4),
            }
        }


class DeepgramClient:
    """Client for Deepgram Speech-to-Text API.

    Supports both streaming (WebSocket) and batch (REST) transcription,
    with optional dry-run mode for development.
    """

    WEBSOCKET_URL = "wss://api.deepgram.com/v1/listen"
    REST_URL = "https://api.deepgram.com/v1/listen"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DeepgramModel.NOVA_3.value,
        language: str = "en",
        dry_run: bool = False,
        log_requests: bool = True,
    ):
        """Initialize the Deepgram client.

        Args:
            api_key: Deepgram API key. If None, will check DEEPGRAM_API_KEY env var.
            model: Default model for transcription.
            language: Default language code.
            dry_run: If True, simulate API calls without making them.
            log_requests: Whether to log API requests.
        """
        self.api_key = api_key or os.environ.get("DEEPGRAM_API_KEY")
        self.default_model = model
        self.default_language = language
        self.dry_run = dry_run
        self.log_requests = log_requests
        self.usage_stats = UsageStats()

        # Session for async requests
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None

        # Keep-alive task
        self._keepalive_task: Optional[asyncio.Task] = None

        # Mock transcript counter for dry-run mode
        self._mock_counter = 0

        if not self.api_key and not self.dry_run:
            logger.warning(
                "No Deepgram API key provided. Set DEEPGRAM_API_KEY or "
                "pass api_key parameter. Using dry_run mode."
            )
            self.dry_run = True

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Token {self.api_key}"}
            )
        return self._session

    async def close(self):
        """Close connections and cleanup resources."""
        # Stop keepalive
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self._ws and not self._ws.closed:
            await self._ws.close()

        # Close session
        if self._session and not self._session.closed:
            await self._session.close()

    async def _keepalive_loop(self, ws: aiohttp.ClientWebSocketResponse):
        """Send keepalive pings to maintain WebSocket connection."""
        try:
            while not ws.closed:
                await asyncio.sleep(5)  # Ping every 5 seconds
                if not ws.closed:
                    await ws.send_json({"type": "KeepAlive"})
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Keepalive loop error: {e}")

    # =========================================================================
    # STREAMING TRANSCRIPTION (WebSocket)
    # =========================================================================

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        config: Optional[DeepgramConfig] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> AsyncIterator[TranscriptResult]:
        """Transcribe streaming audio in real-time.

        Args:
            audio_stream: Async iterator yielding audio chunks (bytes)
            config: Transcription configuration
            max_retries: Maximum connection retry attempts
            retry_delay: Initial retry delay (exponential backoff)

        Yields:
            TranscriptResult for each transcript (interim and final)
        """
        config = config or DeepgramConfig(
            model=self.default_model,
            language=self.default_language,
        )

        if self.log_requests:
            logger.info(
                f"Starting stream transcription: model={config.model}, "
                f"language={config.language}, interim={config.interim_results}"
            )

        # Dry run mode
        if self.dry_run:
            async for result in self._mock_stream_transcription(audio_stream, config):
                yield result
            return

        # Real WebSocket streaming
        retry_count = 0
        while retry_count <= max_retries:
            try:
                async for result in self._stream_transcription_internal(audio_stream, config):
                    yield result
                break  # Success, exit retry loop
            except DeepgramAPIError as e:
                self.usage_stats.record_error()
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Max retries exceeded: {e}")
                    raise

                # Exponential backoff
                delay = retry_delay * (2 ** (retry_count - 1))
                logger.warning(f"Stream error, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)

    async def _stream_transcription_internal(
        self,
        audio_stream: AsyncIterator[bytes],
        config: DeepgramConfig,
    ) -> AsyncIterator[TranscriptResult]:
        """Internal WebSocket streaming implementation."""
        session = await self._get_session()

        # Build WebSocket URL with query params
        params = config.to_params()
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        ws_url = f"{self.WEBSOCKET_URL}?{param_str}"

        # Connect WebSocket
        async with session.ws_connect(ws_url) as ws:
            self._ws = ws

            # Start keepalive
            self._keepalive_task = asyncio.create_task(self._keepalive_loop(ws))

            # Create tasks for sending and receiving
            send_task = asyncio.create_task(self._send_audio(ws, audio_stream))
            receive_task = asyncio.create_task(self._receive_transcripts(ws, config))

            try:
                # Process transcripts as they arrive
                async for result in receive_task:
                    yield result
            finally:
                # Cleanup
                send_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass

    async def _send_audio(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        audio_stream: AsyncIterator[bytes],
    ):
        """Send audio chunks to WebSocket."""
        try:
            async for chunk in audio_stream:
                if ws.closed:
                    break
                await ws.send_bytes(chunk)

            # Send close message
            if not ws.closed:
                await ws.send_json({"type": "CloseStream"})
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            raise

    async def _receive_transcripts(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        config: DeepgramConfig,
    ) -> AsyncIterator[TranscriptResult]:
        """Receive and parse transcripts from WebSocket."""
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Parse transcript
                    if "channel" in data:
                        channel = data["channel"]
                        alternatives = channel.get("alternatives", [])

                        if not alternatives:
                            continue

                        # Determine if final
                        is_final = data.get("is_final", False)
                        speech_final = data.get("speech_final", False)
                        is_final = is_final or speech_final

                        # Create result
                        result = TranscriptResult.from_deepgram(channel, is_final)

                        # Skip empty transcripts
                        if not result.text.strip():
                            continue

                        # Record stats
                        duration = result.end_time - result.start_time
                        self.usage_stats.record_request(config.model, duration, is_final)

                        yield result

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    raise DeepgramAPIError(500, f"WebSocket error: {ws.exception()}")

        except Exception as e:
            logger.error(f"Error receiving transcripts: {e}")
            raise

    # =========================================================================
    # BATCH TRANSCRIPTION (REST API)
    # =========================================================================

    async def transcribe_audio(
        self,
        audio_data: bytes,
        config: Optional[DeepgramConfig] = None,
    ) -> TranscriptResult:
        """Transcribe a complete audio file.

        Args:
            audio_data: Raw audio bytes
            config: Transcription configuration

        Returns:
            TranscriptResult with complete transcript
        """
        config = config or DeepgramConfig(
            model=self.default_model,
            language=self.default_language,
            interim_results=False,  # No interim results for batch
        )

        # Estimate duration from audio size
        # Assuming 16kHz, 16-bit, mono: 32000 bytes/second
        bytes_per_second = config.sample_rate * 2 * config.channels
        duration_s = len(audio_data) / bytes_per_second

        if self.log_requests:
            logger.info(
                f"Batch transcription: {len(audio_data)} bytes, "
                f"~{duration_s:.2f}s, model={config.model}"
            )

        # Dry run mode
        if self.dry_run:
            await asyncio.sleep(0.1)  # Simulate latency
            self.usage_stats.record_request(config.model, duration_s, True)
            return self._generate_mock_transcript(duration_s, config)

        # Real API call
        session = await self._get_session()

        params = config.to_params()
        url = self.REST_URL

        headers = {
            "Content-Type": f"audio/{config.encoding}",
        }

        async with session.post(url, data=audio_data, params=params, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Deepgram API error: {response.status} - {error_text}")
                self.usage_stats.record_error()
                raise DeepgramAPIError(response.status, error_text)

            data = await response.json()

        # Parse response
        results = data.get("results", {})
        channels = results.get("channels", [])

        if not channels:
            raise DeepgramAPIError(500, "No channels in response")

        channel = channels[0]
        result = TranscriptResult.from_deepgram(channel, is_final=True)

        # Record stats
        self.usage_stats.record_request(config.model, duration_s, True)

        return result

    # =========================================================================
    # VOICE ACTIVITY DETECTION (VAD)
    # =========================================================================

    def detect_voice_activity(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        threshold: float = 0.01,
    ) -> VADResult:
        """Detect voice activity in audio data.

        Simple energy-based VAD. For production use, consider Silero VAD.

        Args:
            audio_data: Raw audio bytes (16-bit PCM)
            sample_rate: Audio sample rate
            threshold: Energy threshold for speech detection

        Returns:
            VADResult
        """
        return VADResult.from_audio(audio_data, sample_rate, threshold)

    # =========================================================================
    # USAGE STATS
    # =========================================================================

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this session.

        Returns:
            Usage stats dict
        """
        return self.usage_stats.to_dict()

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.usage_stats = UsageStats()

    # =========================================================================
    # DRY-RUN MODE HELPERS
    # =========================================================================

    async def _mock_stream_transcription(
        self,
        audio_stream: AsyncIterator[bytes],
        config: DeepgramConfig,
    ) -> AsyncIterator[TranscriptResult]:
        """Generate mock streaming transcripts for dry-run mode."""
        chunk_count = 0
        accumulated_duration = 0.0

        async for chunk in audio_stream:
            chunk_count += 1

            # Estimate duration
            bytes_per_second = config.sample_rate * 2 * config.channels
            chunk_duration = len(chunk) / bytes_per_second
            accumulated_duration += chunk_duration

            # Simulate latency
            await asyncio.sleep(0.1)

            # Generate interim results every few chunks
            if config.interim_results and chunk_count % 3 == 0:
                result = self._generate_mock_transcript(
                    accumulated_duration,
                    config,
                    is_final=False,
                )
                self.usage_stats.record_request(config.model, chunk_duration, False)
                yield result

            # Generate final result every ~2 seconds
            if accumulated_duration >= 2.0:
                result = self._generate_mock_transcript(
                    accumulated_duration,
                    config,
                    is_final=True,
                )
                self.usage_stats.record_request(config.model, accumulated_duration, True)
                yield result
                accumulated_duration = 0.0

    def _generate_mock_transcript(
        self,
        duration_s: float,
        config: DeepgramConfig,
        is_final: bool = True,
    ) -> TranscriptResult:
        """Generate mock transcript for dry-run mode."""
        self._mock_counter += 1

        # Generate plausible text
        mock_phrases = [
            "I think they might be a traitor",
            "We should vote them out",
            "I trust them completely",
            "That was definitely suspicious",
            "Let's work together on this mission",
            "I have a bad feeling about this",
            "We need to be strategic here",
            "I'm not sure who to believe",
            "This is getting intense",
            "I think we're making progress",
        ]

        phrase = mock_phrases[self._mock_counter % len(mock_phrases)]

        if not is_final:
            # Truncate for interim results
            words = phrase.split()
            phrase = " ".join(words[:len(words) // 2])

        # Generate word timings
        words = phrase.split()
        word_infos = []
        current_time = 0.0

        for word in words:
            word_duration = len(word) * 0.1  # ~0.1s per character
            word_infos.append(WordInfo(
                word=word,
                start=current_time,
                end=current_time + word_duration,
                confidence=0.95,
            ))
            current_time += word_duration + 0.05  # 50ms gap

        return TranscriptResult(
            text=phrase,
            is_final=is_final,
            confidence=0.95,
            words=word_infos,
            start_time=0.0,
            end_time=current_time,
            language=config.language,
            is_dry_run=True,
        )


class DeepgramAPIError(Exception):
    """Exception for Deepgram API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Deepgram API error {status_code}: {message}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_client(
    api_key: Optional[str] = None,
    dry_run: Optional[bool] = None,
    model: str = DeepgramModel.NOVA_3.value,
) -> DeepgramClient:
    """Create a Deepgram client with sensible defaults.

    Args:
        api_key: API key (or use DEEPGRAM_API_KEY env var)
        dry_run: Force dry-run mode (auto-detected if no API key)
        model: Default model to use

    Returns:
        Configured DeepgramClient
    """
    if dry_run is None:
        # Auto-detect based on API key availability
        dry_run = api_key is None and not os.environ.get("DEEPGRAM_API_KEY")

    return DeepgramClient(
        api_key=api_key,
        dry_run=dry_run,
        model=model,
    )


async def quick_transcribe(
    audio_data: bytes,
    model: str = DeepgramModel.NOVA_3.value,
    language: str = "en",
    api_key: Optional[str] = None,
) -> str:
    """Quick one-off transcription.

    Args:
        audio_data: Audio bytes to transcribe
        model: Model to use
        language: Language code
        api_key: Optional API key

    Returns:
        Transcript text
    """
    client = create_client(api_key=api_key, model=model)
    try:
        config = DeepgramConfig(model=model, language=language)
        result = await client.transcribe_audio(audio_data, config)
        return result.text
    finally:
        await client.close()
