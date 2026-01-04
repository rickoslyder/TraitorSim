"""Voice Emitter - Integration hooks for voice synthesis across TraitorSim.

This module provides the VoiceEmitter protocol that allows game components
(GameMaster, PlayerAgents, GameState) to emit voice events without directly
depending on ElevenLabs or the audio pipeline.

Architecture:
    Game Component → VoiceEmitter.emit() → VoiceEvent → Handler
                                                      ↓
    Episode Mode: Script queue → Batch synthesis → Audio timeline
    HITL Mode: Real-time synthesis → WebSocket stream

Usage:
    # In game component initialization
    self.voice_emitter = create_voice_emitter(
        mode="episode",  # or "hitl"
        voice_enabled=True,
    )

    # In game logic
    if self.voice_emitter:
        await self.voice_emitter.emit(VoiceEvent(
            event_type=VoiceEventType.NARRATOR,
            text="The Traitors have struck again...",
            speaker_id="narrator",
        ))
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
    runtime_checkable,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================


class VoiceEventType(Enum):
    """Types of voice events that can be emitted."""

    # Narrator events (Game Master)
    NARRATOR = "narrator"
    NARRATOR_DRAMATIC = "narrator_dramatic"  # Extra dramatic for banishments, murders
    NARRATOR_WHISPER = "narrator_whisper"  # Secretive tone for Turret phase

    # Player speech events
    PLAYER_SPEECH = "player_speech"  # General player statement
    PLAYER_ACCUSATION = "player_accusation"  # Accusatory statement
    PLAYER_DEFENSE = "player_defense"  # Defensive statement
    PLAYER_VOTE = "player_vote"  # Vote announcement

    # Confessional events (private thoughts)
    CONFESSIONAL = "confessional"  # Player's private reasoning
    CONFESSIONAL_DIARY = "confessional_diary"  # End-of-day diary entry

    # Game event audio (SFX + narration)
    EVENT_MURDER = "event_murder"
    EVENT_BANISHMENT = "event_banishment"
    EVENT_MISSION_START = "event_mission_start"
    EVENT_MISSION_COMPLETE = "event_mission_complete"
    EVENT_RECRUITMENT = "event_recruitment"
    EVENT_SHIELD = "event_shield"
    EVENT_DAGGER = "event_dagger"

    # System events
    SYSTEM_PHASE_TRANSITION = "system_phase_transition"
    SYSTEM_DAY_START = "system_day_start"
    SYSTEM_GAME_END = "system_game_end"


class VoiceMode(Enum):
    """Voice emission modes."""

    EPISODE = "episode"  # Batch mode for post-processing (high quality, no latency requirement)
    HITL = "hitl"  # Real-time mode for human-in-the-loop (low latency, Flash model)
    HYBRID = "hybrid"  # Both (record + stream)
    DISABLED = "disabled"  # No voice emission


class EmotionHint(Enum):
    """Emotion hints for voice synthesis."""

    NEUTRAL = "neutral"
    SUSPICIOUS = "suspicious"
    ACCUSATORY = "accusatory"
    DEFENSIVE = "defensive"
    FEARFUL = "fearful"
    CONFIDENT = "confident"
    TRIUMPHANT = "triumphant"
    DEFEATED = "defeated"
    CONSPIRATORIAL = "conspiratorial"  # Traitors in Turret
    DRAMATIC = "dramatic"  # Narrator reveal moments
    SOMBER = "somber"  # Death announcements


# ============================================================================
# Voice Event Dataclass
# ============================================================================


@dataclass
class VoiceEvent:
    """A voice event to be synthesized and played/recorded.

    Attributes:
        event_type: Type of voice event (affects routing and processing)
        text: The text to synthesize
        speaker_id: Player ID or "narrator" for narrator events
        speaker_name: Display name for the speaker
        emotion: Emotion hint for voice modulation
        day: Game day (for timeline)
        phase: Game phase (for context)
        priority: Higher priority events are processed first (HITL mode)
        metadata: Additional context (e.g., vote target, suspicion level)
        timestamp: When the event was created
    """

    event_type: VoiceEventType
    text: str
    speaker_id: str = "narrator"
    speaker_name: Optional[str] = None
    emotion: EmotionHint = EmotionHint.NEUTRAL
    day: int = 1
    phase: str = "unknown"
    priority: int = 5  # 1=highest, 10=lowest
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Set speaker_name from speaker_id if not provided."""
        if self.speaker_name is None:
            self.speaker_name = "Narrator" if self.speaker_id == "narrator" else self.speaker_id


# ============================================================================
# Voice Emitter Protocol
# ============================================================================


@runtime_checkable
class VoiceEmitter(Protocol):
    """Protocol for voice event emission.

    Implementations handle the actual synthesis and output:
    - EpisodeVoiceEmitter: Queues events for batch processing
    - HITLVoiceEmitter: Sends to WebSocket for real-time playback
    - CompositeVoiceEmitter: Combines multiple emitters
    """

    async def emit(self, event: VoiceEvent) -> None:
        """Emit a voice event for synthesis.

        Args:
            event: The voice event to emit
        """
        ...

    async def flush(self) -> List[VoiceEvent]:
        """Flush any pending events (for batch mode).

        Returns:
            List of flushed events (empty for HITL/Null emitters)
        """
        ...

    def is_enabled(self) -> bool:
        """Check if voice emission is enabled."""
        ...


# ============================================================================
# Null Emitter (no-op for disabled mode)
# ============================================================================


class NullVoiceEmitter:
    """No-op emitter for when voice is disabled."""

    async def emit(self, event: VoiceEvent) -> None:
        """Discard the event."""
        pass

    async def flush(self) -> List[VoiceEvent]:
        """No-op, returns empty list."""
        return []

    def is_enabled(self) -> bool:
        """Always returns False."""
        return False


# ============================================================================
# Episode Mode Emitter (batch processing)
# ============================================================================


class EpisodeVoiceEmitter:
    """Emitter for Episode Mode - queues events for batch synthesis.

    Events are collected and later processed by EpisodeGenerator
    to create full audio episodes with proper timing and mixing.
    """

    def __init__(self, max_queue_size: int = 10000):
        """Initialize episode emitter.

        Args:
            max_queue_size: Maximum events to queue before oldest are dropped
        """
        self._queue: List[VoiceEvent] = []
        self._max_queue_size = max_queue_size
        self._enabled = True

    async def emit(self, event: VoiceEvent) -> None:
        """Queue event for batch processing.

        Args:
            event: Voice event to queue
        """
        if not self._enabled:
            return

        self._queue.append(event)

        # Prevent unbounded growth
        if len(self._queue) > self._max_queue_size:
            dropped = len(self._queue) - self._max_queue_size
            self._queue = self._queue[dropped:]
            logger.warning(f"Episode queue overflow, dropped {dropped} oldest events")

    async def flush(self) -> List[VoiceEvent]:
        """Get all queued events and clear the queue.

        Returns:
            List of queued events
        """
        events = self._queue
        self._queue = []
        return events

    def get_events(self) -> List[VoiceEvent]:
        """Get all queued events without clearing.

        Returns:
            List of queued events
        """
        return list(self._queue)

    def get_and_clear_events(self) -> List[VoiceEvent]:
        """Get all queued events and clear the queue.

        Returns:
            List of queued events
        """
        events = self._queue
        self._queue = []
        return events

    def is_enabled(self) -> bool:
        """Check if emitter is enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the emitter."""
        self._enabled = enabled


# ============================================================================
# HITL Mode Emitter (real-time streaming)
# ============================================================================


class HITLVoiceEmitter:
    """Emitter for HITL Mode - real-time synthesis and streaming.

    Events are immediately synthesized using ElevenLabs Flash
    and streamed to the connected WebSocket client.
    """

    def __init__(
        self,
        websocket_send: Optional[Callable[[bytes, str], Coroutine[Any, Any, None]]] = None,
        synthesis_callback: Optional[Callable[[VoiceEvent], Coroutine[Any, Any, bytes]]] = None,
        priority_threshold: int = 7,
    ):
        """Initialize HITL emitter.

        Args:
            websocket_send: Async function to send audio to client (data, speaker_id)
            synthesis_callback: Async function to synthesize event to audio bytes
            priority_threshold: Only process events with priority <= this value
        """
        self._websocket_send = websocket_send
        self._synthesis_callback = synthesis_callback
        self._priority_threshold = priority_threshold
        self._enabled = True
        self._pending_tasks: List[asyncio.Task] = []

    async def emit(self, event: VoiceEvent) -> None:
        """Emit event for real-time synthesis and streaming.

        Args:
            event: Voice event to emit
        """
        if not self._enabled:
            return

        # Skip low-priority events in HITL mode
        if event.priority > self._priority_threshold:
            logger.debug(f"Skipping low-priority event: {event.event_type.value}")
            return

        # Fire-and-forget synthesis + streaming
        task = asyncio.create_task(self._process_event(event))
        self._pending_tasks.append(task)

        # Clean up completed tasks
        self._pending_tasks = [t for t in self._pending_tasks if not t.done()]

    async def _process_event(self, event: VoiceEvent) -> None:
        """Process a single event (synthesize + stream)."""
        try:
            if self._synthesis_callback:
                audio_data = await self._synthesis_callback(event)

                if self._websocket_send and audio_data:
                    await self._websocket_send(audio_data, event.speaker_id)

        except Exception as e:
            logger.error(f"Error processing voice event: {e}")

    async def flush(self) -> List[VoiceEvent]:
        """Wait for all pending synthesis tasks to complete.

        Returns:
            Empty list (HITL doesn't queue events)
        """
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks = []
        return []

    def is_enabled(self) -> bool:
        """Check if emitter is enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the emitter."""
        self._enabled = enabled

    def set_websocket_send(
        self,
        send_func: Callable[[bytes, str], Coroutine[Any, Any, None]],
    ) -> None:
        """Set the WebSocket send function (for late binding)."""
        self._websocket_send = send_func

    def set_synthesis_callback(
        self,
        callback: Callable[[VoiceEvent], Coroutine[Any, Any, bytes]],
    ) -> None:
        """Set the synthesis callback (for late binding)."""
        self._synthesis_callback = callback


# ============================================================================
# Composite Emitter (multiple outputs)
# ============================================================================


class CompositeVoiceEmitter:
    """Emitter that forwards to multiple sub-emitters.

    Useful for hybrid mode where events go to both
    episode recording AND real-time streaming.
    """

    def __init__(self, emitters: Optional[List[VoiceEmitter]] = None):
        """Initialize composite emitter.

        Args:
            emitters: List of emitters to forward events to
        """
        self._emitters: List[VoiceEmitter] = emitters or []
        self._enabled = True

    def add_emitter(self, emitter: VoiceEmitter) -> None:
        """Add an emitter to the composite."""
        self._emitters.append(emitter)

    def remove_emitter(self, emitter: VoiceEmitter) -> None:
        """Remove an emitter from the composite."""
        self._emitters = [e for e in self._emitters if e is not emitter]

    async def emit(self, event: VoiceEvent) -> None:
        """Forward event to all sub-emitters.

        Args:
            event: Voice event to emit
        """
        if not self._enabled:
            return

        await asyncio.gather(
            *[e.emit(event) for e in self._emitters if e.is_enabled()],
            return_exceptions=True,
        )

    async def flush(self) -> List[VoiceEvent]:
        """Flush all sub-emitters and collect events.

        Returns:
            Combined list of events from all emitters
        """
        results = await asyncio.gather(
            *[e.flush() for e in self._emitters],
            return_exceptions=True,
        )
        # Flatten results, filtering out exceptions
        all_events: List[VoiceEvent] = []
        for result in results:
            if isinstance(result, list):
                all_events.extend(result)
        return all_events

    def is_enabled(self) -> bool:
        """Check if emitter is enabled."""
        return self._enabled and any(e.is_enabled() for e in self._emitters)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the composite emitter."""
        self._enabled = enabled


# ============================================================================
# Factory Function
# ============================================================================


def create_voice_emitter(
    mode: Union[VoiceMode, str] = VoiceMode.DISABLED,
    **kwargs,
) -> VoiceEmitter:
    """Create a voice emitter for the specified mode.

    Args:
        mode: Voice mode (episode, hitl, hybrid, disabled)
        **kwargs: Mode-specific arguments

    Returns:
        Configured VoiceEmitter instance
    """
    if isinstance(mode, str):
        mode = VoiceMode(mode.lower())

    if mode == VoiceMode.DISABLED:
        return NullVoiceEmitter()

    if mode == VoiceMode.EPISODE:
        return EpisodeVoiceEmitter(
            max_queue_size=kwargs.get("max_queue_size", 10000),
        )

    if mode == VoiceMode.HITL:
        return HITLVoiceEmitter(
            websocket_send=kwargs.get("websocket_send"),
            synthesis_callback=kwargs.get("synthesis_callback"),
            priority_threshold=kwargs.get("priority_threshold", 7),
        )

    if mode == VoiceMode.HYBRID:
        composite = CompositeVoiceEmitter()
        composite.add_emitter(EpisodeVoiceEmitter())
        composite.add_emitter(HITLVoiceEmitter(
            websocket_send=kwargs.get("websocket_send"),
            synthesis_callback=kwargs.get("synthesis_callback"),
        ))
        return composite

    raise ValueError(f"Unknown voice mode: {mode}")


# ============================================================================
# Helper: Infer emotion from event context
# ============================================================================


def infer_emotion(
    event_type: VoiceEventType,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> EmotionHint:
    """Infer emotion hint from event type and context.

    Args:
        event_type: Type of voice event
        text: Text content
        metadata: Additional context

    Returns:
        Inferred emotion hint
    """
    metadata = metadata or {}

    # Event type mappings
    type_emotions = {
        VoiceEventType.NARRATOR_DRAMATIC: EmotionHint.DRAMATIC,
        VoiceEventType.NARRATOR_WHISPER: EmotionHint.CONSPIRATORIAL,
        VoiceEventType.PLAYER_ACCUSATION: EmotionHint.ACCUSATORY,
        VoiceEventType.PLAYER_DEFENSE: EmotionHint.DEFENSIVE,
        VoiceEventType.EVENT_MURDER: EmotionHint.SOMBER,
        VoiceEventType.EVENT_BANISHMENT: EmotionHint.DRAMATIC,
        VoiceEventType.SYSTEM_GAME_END: EmotionHint.TRIUMPHANT,
    }

    if event_type in type_emotions:
        return type_emotions[event_type]

    # Check metadata
    if metadata.get("is_traitor"):
        return EmotionHint.CONSPIRATORIAL
    if metadata.get("suspicion_level", 0) > 0.7:
        return EmotionHint.SUSPICIOUS
    if metadata.get("is_accused"):
        return EmotionHint.DEFENSIVE

    # Text analysis (simple keyword matching)
    text_lower = text.lower()
    if any(word in text_lower for word in ["murder", "kill", "dead", "victim"]):
        return EmotionHint.SOMBER
    if any(word in text_lower for word in ["accuse", "suspect", "traitor", "liar"]):
        return EmotionHint.ACCUSATORY
    if any(word in text_lower for word in ["innocent", "faithful", "trust me"]):
        return EmotionHint.DEFENSIVE
    if any(word in text_lower for word in ["win", "victory", "triumph"]):
        return EmotionHint.TRIUMPHANT

    return EmotionHint.NEUTRAL


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "VoiceEventType",
    "VoiceMode",
    "EmotionHint",
    # Data classes
    "VoiceEvent",
    # Protocol and implementations
    "VoiceEmitter",
    "NullVoiceEmitter",
    "EpisodeVoiceEmitter",
    "HITLVoiceEmitter",
    "CompositeVoiceEmitter",
    # Factory
    "create_voice_emitter",
    # Helpers
    "infer_emotion",
]
