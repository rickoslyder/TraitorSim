"""ElevenLabs API client for TraitorSim voice synthesis.

Provides a comprehensive wrapper around ElevenLabs API for both
Episode Mode (high-quality v3) and HITL Mode (low-latency Flash).

Supports:
- Text-to-Speech (single voice)
- Text-to-Dialogue (multiple voices) - Eleven v3 only
- Streaming audio for real-time playback
- Voice selection and configuration
- Cost estimation and tracking
- Dry-run mode for development without API calls

Usage:
    from traitorsim.voice import ElevenLabsClient

    # Initialize client
    client = ElevenLabsClient(api_key="your-key")

    # Generate audio
    audio = await client.text_to_speech(
        text="[dramatic] The traitors have struck again.",
        voice_id="daniel",
        model="eleven_flash_v2_5"
    )

    # Dry-run mode (no API calls, returns mock data)
    client = ElevenLabsClient(dry_run=True)
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, AsyncIterator, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import time

logger = logging.getLogger(__name__)


class ElevenLabsModel(str, Enum):
    """Available ElevenLabs models."""
    # High-quality models (Episode Mode)
    ELEVEN_V3 = "eleven_v3"                      # Text-to-Dialogue, dramatic
    ELEVEN_MULTILINGUAL_V2 = "eleven_multilingual_v2"  # Life-like, 29 languages

    # Low-latency models (HITL Mode)
    ELEVEN_FLASH_V2_5 = "eleven_flash_v2_5"      # <75ms latency, 0.5 credits/char
    ELEVEN_FLASH_V2 = "eleven_flash_v2"          # Original Flash

    # Legacy
    ELEVEN_TURBO_V2_5 = "eleven_turbo_v2_5"      # Balanced quality/latency


@dataclass
class VoiceSettings:
    """Voice synthesis settings for ElevenLabs API."""
    stability: float = 0.5          # 0.0-1.0, lower = more expressive
    similarity_boost: float = 0.75  # 0.0-1.0, voice clarity
    style: float = 0.5              # 0.0-1.0, style exaggeration (v3 only)
    use_speaker_boost: bool = True  # Enhanced clarity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
        }


@dataclass
class SynthesisResult:
    """Result from a synthesis request."""
    audio_data: bytes               # Raw audio bytes (MP3)
    character_count: int            # Characters processed
    credits_used: int               # ElevenLabs credits consumed
    model_used: str                 # Model that was used
    voice_id: str                   # Voice that was used
    duration_estimate_s: float      # Estimated audio duration
    latency_ms: Optional[float]     # Request latency (if measured)
    is_dry_run: bool = False        # Whether this was a simulated result


@dataclass
class UsageStats:
    """Track API usage for cost monitoring."""
    total_characters: int = 0
    total_credits: int = 0
    requests_made: int = 0
    requests_by_model: Dict[str, int] = field(default_factory=dict)
    characters_by_model: Dict[str, int] = field(default_factory=dict)

    def record_request(self, model: str, characters: int, credits: int):
        """Record a synthesis request."""
        self.total_characters += characters
        self.total_credits += credits
        self.requests_made += 1
        self.requests_by_model[model] = self.requests_by_model.get(model, 0) + 1
        self.characters_by_model[model] = self.characters_by_model.get(model, 0) + characters

    def estimate_cost_usd(self, plan: str = "pro") -> float:
        """Estimate USD cost based on credits used.

        Args:
            plan: ElevenLabs plan (pro, scale, business)

        Returns:
            Estimated cost in USD
        """
        # Cost per credit by plan (approximate)
        cost_per_credit = {
            "pro": 99 / 500_000,       # $0.000198
            "scale": 330 / 2_000_000,  # $0.000165
            "business": 1320 / 11_000_000,  # $0.00012
        }
        rate = cost_per_credit.get(plan, cost_per_credit["pro"])
        return self.total_credits * rate

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "total_characters": self.total_characters,
            "total_credits": self.total_credits,
            "requests_made": self.requests_made,
            "requests_by_model": self.requests_by_model,
            "characters_by_model": self.characters_by_model,
            "estimated_cost_usd": {
                "pro": round(self.estimate_cost_usd("pro"), 4),
                "scale": round(self.estimate_cost_usd("scale"), 4),
                "business": round(self.estimate_cost_usd("business"), 4),
            }
        }


class ElevenLabsClient:
    """Client for ElevenLabs Text-to-Speech and Text-to-Dialogue APIs.

    Supports both synchronous and asynchronous operations, with optional
    dry-run mode for development.
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    # Credits per character by model
    CREDITS_PER_CHAR = {
        ElevenLabsModel.ELEVEN_V3.value: 1.0,
        ElevenLabsModel.ELEVEN_MULTILINGUAL_V2.value: 1.0,
        ElevenLabsModel.ELEVEN_FLASH_V2_5.value: 0.5,
        ElevenLabsModel.ELEVEN_FLASH_V2.value: 0.5,
        ElevenLabsModel.ELEVEN_TURBO_V2_5.value: 0.5,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        dry_run: bool = False,
        default_model: str = ElevenLabsModel.ELEVEN_V3.value,
        log_requests: bool = True,
    ):
        """Initialize the ElevenLabs client.

        Args:
            api_key: ElevenLabs API key. If None, will check ELEVENLABS_API_KEY env var.
            dry_run: If True, simulate API calls without making them.
            default_model: Default model for synthesis.
            log_requests: Whether to log API requests.
        """
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self.dry_run = dry_run
        self.default_model = default_model
        self.log_requests = log_requests
        self.usage_stats = UsageStats()

        # Session for async requests
        self._session: Optional[aiohttp.ClientSession] = None

        # Rate limiting
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests

        if not self.api_key and not self.dry_run:
            logger.warning(
                "No ElevenLabs API key provided. Set ELEVENLABS_API_KEY or "
                "pass api_key parameter. Using dry_run mode."
            )
            self.dry_run = True

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"xi-api-key": self.api_key}
            )
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _calculate_credits(self, text: str, model: str) -> int:
        """Calculate credits for a synthesis request."""
        chars = len(text)
        rate = self.CREDITS_PER_CHAR.get(model, 1.0)
        return int(chars * rate)

    def _estimate_duration(self, text: str) -> float:
        """Estimate audio duration from text length.

        Average speaking rate: ~150 words/min = ~750 chars/min

        Args:
            text: Text to synthesize

        Returns:
            Estimated duration in seconds
        """
        chars = len(text)
        return (chars / 750) * 60

    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    # =========================================================================
    # TEXT-TO-SPEECH (Single Voice)
    # =========================================================================

    async def text_to_speech(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
        voice_settings: Optional[VoiceSettings] = None,
        output_format: str = "mp3_44100_128",
        optimize_streaming_latency: int = 0,
    ) -> SynthesisResult:
        """Generate speech from text using a single voice.

        Args:
            text: Text to synthesize (can include emotion tags like [excited])
            voice_id: ElevenLabs voice ID
            model: Model to use (defaults to client's default_model)
            voice_settings: Voice configuration (stability, style, etc.)
            output_format: Audio format (mp3_44100_128, pcm_16000, etc.)
            optimize_streaming_latency: 0-4, higher = lower latency, lower quality

        Returns:
            SynthesisResult with audio data and metadata
        """
        model = model or self.default_model
        voice_settings = voice_settings or VoiceSettings()
        credits = self._calculate_credits(text, model)
        duration = self._estimate_duration(text)

        if self.log_requests:
            logger.info(
                f"TTS request: {len(text)} chars, voice={voice_id}, "
                f"model={model}, credits={credits}"
            )

        # Dry run mode
        if self.dry_run:
            self.usage_stats.record_request(model, len(text), credits)
            return SynthesisResult(
                audio_data=self._generate_mock_audio(duration),
                character_count=len(text),
                credits_used=credits,
                model_used=model,
                voice_id=voice_id,
                duration_estimate_s=duration,
                latency_ms=None,
                is_dry_run=True,
            )

        # Real API call
        await self._rate_limit()
        session = await self._get_session()

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": voice_settings.to_dict(),
        }
        params = {
            "output_format": output_format,
            "optimize_streaming_latency": optimize_streaming_latency,
        }

        start_time = time.time()

        async with session.post(url, json=payload, params=params) as response:
            latency_ms = (time.time() - start_time) * 1000

            if response.status != 200:
                error_text = await response.text()
                logger.error(f"ElevenLabs API error: {response.status} - {error_text}")
                raise ElevenLabsAPIError(response.status, error_text)

            audio_data = await response.read()

        self.usage_stats.record_request(model, len(text), credits)

        return SynthesisResult(
            audio_data=audio_data,
            character_count=len(text),
            credits_used=credits,
            model_used=model,
            voice_id=voice_id,
            duration_estimate_s=duration,
            latency_ms=latency_ms,
            is_dry_run=False,
        )

    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
        voice_settings: Optional[VoiceSettings] = None,
        optimize_streaming_latency: int = 3,
        chunk_size: int = 1024,
    ) -> AsyncIterator[bytes]:
        """Stream speech from text for real-time playback.

        Use this for HITL mode where low latency is critical.

        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID
            model: Model to use (recommend eleven_flash_v2_5 for streaming)
            voice_settings: Voice configuration
            optimize_streaming_latency: 0-4, higher = lower latency
            chunk_size: Size of audio chunks to yield

        Yields:
            Audio data chunks (bytes)
        """
        model = model or ElevenLabsModel.ELEVEN_FLASH_V2_5.value
        voice_settings = voice_settings or VoiceSettings()
        credits = self._calculate_credits(text, model)

        if self.log_requests:
            logger.info(f"TTS stream: {len(text)} chars, voice={voice_id}")

        # Dry run mode
        if self.dry_run:
            duration = self._estimate_duration(text)
            mock_audio = self._generate_mock_audio(duration)
            self.usage_stats.record_request(model, len(text), credits)

            # Yield in chunks
            for i in range(0, len(mock_audio), chunk_size):
                yield mock_audio[i:i + chunk_size]
                await asyncio.sleep(0.01)  # Simulate streaming latency
            return

        # Real streaming API call
        await self._rate_limit()
        session = await self._get_session()

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}/stream"
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": voice_settings.to_dict(),
        }
        params = {
            "output_format": "mp3_44100_128",
            "optimize_streaming_latency": optimize_streaming_latency,
        }

        async with session.post(url, json=payload, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ElevenLabsAPIError(response.status, error_text)

            async for chunk in response.content.iter_chunked(chunk_size):
                yield chunk

        self.usage_stats.record_request(model, len(text), credits)

    # =========================================================================
    # TEXT-TO-DIALOGUE (Multiple Voices) - Eleven v3 Only
    # =========================================================================

    async def text_to_dialogue(
        self,
        segments: List[Dict[str, Any]],
        output_format: str = "mp3_44100_128",
    ) -> SynthesisResult:
        """Generate multi-voice dialogue (Text-to-Dialogue API).

        Uses Eleven v3 for dramatic, contextual dialogue generation.
        Each segment specifies a speaker and their dialogue.

        Args:
            segments: List of dialogue segments, each with:
                - voice_id: Speaker's voice ID
                - text: Dialogue text (can include emotion tags)
            output_format: Audio format

        Returns:
            SynthesisResult with combined audio

        Example:
            segments = [
                {"voice_id": "daniel", "text": "[dramatic] The traitors have struck."},
                {"voice_id": "aria", "text": "[shocked] No... not them."},
            ]
            result = await client.text_to_dialogue(segments)
        """
        model = ElevenLabsModel.ELEVEN_V3.value

        # Calculate total text and credits
        total_text = " ".join(seg["text"] for seg in segments)
        credits = self._calculate_credits(total_text, model)
        duration = self._estimate_duration(total_text)

        if self.log_requests:
            logger.info(
                f"Dialogue request: {len(segments)} segments, "
                f"{len(total_text)} chars, credits={credits}"
            )

        # Dry run mode
        if self.dry_run:
            self.usage_stats.record_request(model, len(total_text), credits)
            return SynthesisResult(
                audio_data=self._generate_mock_audio(duration),
                character_count=len(total_text),
                credits_used=credits,
                model_used=model,
                voice_id="multi",
                duration_estimate_s=duration,
                latency_ms=None,
                is_dry_run=True,
            )

        # Real API call
        await self._rate_limit()
        session = await self._get_session()

        url = f"{self.BASE_URL}/text-to-dialogue"
        payload = {
            "model_id": model,
            "dialogue": [
                {
                    "voice_id": seg["voice_id"],
                    "text": seg["text"],
                }
                for seg in segments
            ],
        }
        params = {"output_format": output_format}

        start_time = time.time()

        async with session.post(url, json=payload, params=params) as response:
            latency_ms = (time.time() - start_time) * 1000

            if response.status != 200:
                error_text = await response.text()
                raise ElevenLabsAPIError(response.status, error_text)

            audio_data = await response.read()

        self.usage_stats.record_request(model, len(total_text), credits)

        return SynthesisResult(
            audio_data=audio_data,
            character_count=len(total_text),
            credits_used=credits,
            model_used=model,
            voice_id="multi",
            duration_estimate_s=duration,
            latency_ms=latency_ms,
            is_dry_run=False,
        )

    # =========================================================================
    # VOICE MANAGEMENT
    # =========================================================================

    async def list_voices(self) -> List[Dict[str, Any]]:
        """Get available voices.

        Returns:
            List of voice metadata dicts
        """
        if self.dry_run:
            # Return mock voice list
            return [
                {"voice_id": "daniel", "name": "Daniel", "category": "premade"},
                {"voice_id": "aria", "name": "Aria", "category": "premade"},
                {"voice_id": "charlotte", "name": "Charlotte", "category": "premade"},
            ]

        session = await self._get_session()
        url = f"{self.BASE_URL}/voices"

        async with session.get(url) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ElevenLabsAPIError(response.status, error_text)

            data = await response.json()
            return data.get("voices", [])

    async def get_voice(self, voice_id: str) -> Dict[str, Any]:
        """Get metadata for a specific voice.

        Args:
            voice_id: Voice identifier

        Returns:
            Voice metadata dict
        """
        if self.dry_run:
            return {
                "voice_id": voice_id,
                "name": voice_id.title(),
                "category": "premade",
            }

        session = await self._get_session()
        url = f"{self.BASE_URL}/voices/{voice_id}"

        async with session.get(url) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ElevenLabsAPIError(response.status, error_text)

            return await response.json()

    # =========================================================================
    # SUBSCRIPTION & USAGE
    # =========================================================================

    async def get_subscription_info(self) -> Dict[str, Any]:
        """Get subscription details and remaining credits.

        Returns:
            Subscription info dict with character limits
        """
        if self.dry_run:
            return {
                "tier": "pro",
                "character_count": 0,
                "character_limit": 500_000,
                "can_extend_character_limit": True,
                "dry_run": True,
            }

        session = await self._get_session()
        url = f"{self.BASE_URL}/user/subscription"

        async with session.get(url) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ElevenLabsAPIError(response.status, error_text)

            return await response.json()

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
    # BATCH SYNTHESIS
    # =========================================================================

    async def synthesize_script(
        self,
        script: "DialogueScript",
        model: Optional[str] = None,
        use_dialogue_api: bool = True,
        batch_size: int = 10,
    ) -> List[SynthesisResult]:
        """Synthesize a complete DialogueScript.

        For Episode Mode, uses Text-to-Dialogue API for dramatic multi-voice.
        For HITL Mode (use_dialogue_api=False), uses individual TTS calls.

        Args:
            script: DialogueScript to synthesize
            model: Model to use (defaults to ELEVEN_V3 for dialogue)
            use_dialogue_api: Use Text-to-Dialogue (True) or individual TTS (False)
            batch_size: Segments per API call when using dialogue API

        Returns:
            List of SynthesisResult for each batch/segment
        """
        results = []
        segments = script.segments

        if use_dialogue_api and model in (None, ElevenLabsModel.ELEVEN_V3.value):
            # Use Text-to-Dialogue API (batched)
            for i in range(0, len(segments), batch_size):
                batch = segments[i:i + batch_size]
                dialogue_segments = [
                    {"voice_id": seg.voice_id, "text": seg.to_tagged_text()}
                    for seg in batch
                ]
                result = await self.text_to_dialogue(dialogue_segments)
                results.append(result)
        else:
            # Use individual TTS calls
            model = model or self.default_model
            for seg in segments:
                result = await self.text_to_speech(
                    text=seg.to_tagged_text(),
                    voice_id=seg.voice_id,
                    model=model,
                )
                results.append(result)

        return results

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _generate_mock_audio(self, duration_s: float) -> bytes:
        """Generate mock audio data for dry-run mode.

        Creates a minimal valid MP3 frame sequence that media players
        can recognize (though it will be silent).

        Args:
            duration_s: Desired duration in seconds

        Returns:
            Mock MP3 data bytes
        """
        # MP3 frame header for 128kbps, 44100Hz, stereo
        # This creates a valid MP3 that players can read
        frame_header = bytes([
            0xFF, 0xFB,  # Sync word + MPEG Audio Layer 3
            0x90,        # 128kbps, 44100Hz
            0x00,        # Additional flags
        ])

        # Each frame is ~418 bytes at 128kbps and represents ~26ms
        frames_needed = int((duration_s * 1000) / 26)
        frame_data = b'\x00' * 414  # Silence

        mock_audio = b''
        for _ in range(max(1, frames_needed)):
            mock_audio += frame_header + frame_data

        return mock_audio

    def estimate_cost(
        self,
        text: str,
        model: Optional[str] = None,
        plan: str = "pro"
    ) -> Dict[str, Any]:
        """Estimate cost for synthesizing text.

        Args:
            text: Text to synthesize
            model: Model to use
            plan: ElevenLabs plan (pro, scale, business)

        Returns:
            Cost estimation dict
        """
        model = model or self.default_model
        chars = len(text)
        credits = self._calculate_credits(text, model)

        # Cost per credit by plan
        cost_per_credit = {
            "pro": 99 / 500_000,
            "scale": 330 / 2_000_000,
            "business": 1320 / 11_000_000,
        }

        cost = credits * cost_per_credit.get(plan, cost_per_credit["pro"])

        return {
            "characters": chars,
            "credits": credits,
            "model": model,
            "plan": plan,
            "estimated_cost_usd": round(cost, 6),
            "estimated_duration_s": round(self._estimate_duration(text), 2),
        }


class ElevenLabsAPIError(Exception):
    """Exception for ElevenLabs API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"ElevenLabs API error {status_code}: {message}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_client(
    api_key: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> ElevenLabsClient:
    """Create an ElevenLabs client with sensible defaults.

    Args:
        api_key: API key (or use ELEVENLABS_API_KEY env var)
        dry_run: Force dry-run mode (auto-detected if no API key)

    Returns:
        Configured ElevenLabsClient
    """
    if dry_run is None:
        # Auto-detect based on API key availability
        dry_run = api_key is None and not os.environ.get("ELEVENLABS_API_KEY")

    return ElevenLabsClient(
        api_key=api_key,
        dry_run=dry_run,
    )


async def quick_synthesize(
    text: str,
    voice_id: str = "daniel",
    model: str = ElevenLabsModel.ELEVEN_V3.value,
    api_key: Optional[str] = None,
) -> bytes:
    """Quick one-off synthesis.

    Args:
        text: Text to synthesize
        voice_id: Voice to use
        model: Model to use
        api_key: Optional API key

    Returns:
        Audio bytes
    """
    client = create_client(api_key=api_key)
    try:
        result = await client.text_to_speech(text, voice_id, model)
        return result.audio_data
    finally:
        await client.close()
