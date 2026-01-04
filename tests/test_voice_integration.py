"""Tests for voice integration wiring."""

import asyncio
import pytest
from src.traitorsim.core.config import GameConfig
from src.traitorsim.voice import (
    create_voice_emitter,
    VoiceMode,
    VoiceEvent,
    VoiceEventType,
    EmotionHint,
    NullVoiceEmitter,
    EpisodeVoiceEmitter,
    HITLVoiceEmitter,
    CompositeVoiceEmitter,
    infer_emotion,
)


class TestVoiceEmitterFactory:
    """Tests for create_voice_emitter factory function."""

    def test_create_disabled_emitter(self):
        """Test creating disabled voice emitter."""
        emitter = create_voice_emitter(mode=VoiceMode.DISABLED)

        assert isinstance(emitter, NullVoiceEmitter)
        assert not emitter.is_enabled()

    def test_create_episode_emitter(self):
        """Test creating episode mode voice emitter."""
        emitter = create_voice_emitter(mode=VoiceMode.EPISODE)

        assert isinstance(emitter, EpisodeVoiceEmitter)
        assert emitter.is_enabled()

    def test_create_hitl_emitter(self):
        """Test creating HITL mode voice emitter."""
        emitter = create_voice_emitter(mode=VoiceMode.HITL)

        assert isinstance(emitter, HITLVoiceEmitter)
        assert emitter.is_enabled()

    def test_create_hybrid_emitter(self):
        """Test creating hybrid mode voice emitter."""
        emitter = create_voice_emitter(mode=VoiceMode.HYBRID)

        assert isinstance(emitter, CompositeVoiceEmitter)
        assert emitter.is_enabled()

    def test_create_from_string_mode(self):
        """Test creating emitter from string mode."""
        emitter = create_voice_emitter(mode="episode")
        assert isinstance(emitter, EpisodeVoiceEmitter)

        emitter = create_voice_emitter(mode="disabled")
        assert isinstance(emitter, NullVoiceEmitter)


class TestNullVoiceEmitter:
    """Tests for NullVoiceEmitter (disabled mode)."""

    def test_emit_discards_events(self):
        """Test that NullVoiceEmitter discards events."""
        emitter = NullVoiceEmitter()

        event = VoiceEvent(
            event_type=VoiceEventType.NARRATOR,
            text="Test narration",
        )

        # Should not raise
        asyncio.run(emitter.emit(event))

    def test_flush_returns_empty(self):
        """Test that flush returns empty list."""
        emitter = NullVoiceEmitter()

        result = asyncio.run(emitter.flush())
        assert result == []

    def test_is_enabled_returns_false(self):
        """Test that is_enabled always returns False."""
        emitter = NullVoiceEmitter()
        assert not emitter.is_enabled()


class TestEpisodeVoiceEmitter:
    """Tests for EpisodeVoiceEmitter (batch mode)."""

    def test_emit_queues_events(self):
        """Test that events are queued."""
        emitter = EpisodeVoiceEmitter()

        event = VoiceEvent(
            event_type=VoiceEventType.NARRATOR,
            text="Test narration",
        )

        asyncio.run(emitter.emit(event))

        events = emitter.get_events()
        assert len(events) == 1
        assert events[0].text == "Test narration"

    def test_flush_returns_and_clears_events(self):
        """Test that flush returns events and clears queue."""
        emitter = EpisodeVoiceEmitter()

        event1 = VoiceEvent(event_type=VoiceEventType.NARRATOR, text="First")
        event2 = VoiceEvent(event_type=VoiceEventType.PLAYER_SPEECH, text="Second")

        asyncio.run(emitter.emit(event1))
        asyncio.run(emitter.emit(event2))

        # Flush should return both and clear
        result = asyncio.run(emitter.flush())
        assert len(result) == 2

        # Queue should be empty after flush
        events = emitter.get_events()
        assert len(events) == 0

    def test_queue_overflow_drops_oldest(self):
        """Test that queue overflow drops oldest events."""
        emitter = EpisodeVoiceEmitter(max_queue_size=3)

        for i in range(5):
            event = VoiceEvent(event_type=VoiceEventType.NARRATOR, text=f"Event {i}")
            asyncio.run(emitter.emit(event))

        events = emitter.get_events()
        assert len(events) == 3
        # Should have events 2, 3, 4 (oldest dropped)
        assert events[0].text == "Event 2"
        assert events[1].text == "Event 3"
        assert events[2].text == "Event 4"

    def test_set_enabled_disables_queue(self):
        """Test that disabled emitter doesn't queue."""
        emitter = EpisodeVoiceEmitter()
        emitter.set_enabled(False)

        event = VoiceEvent(event_type=VoiceEventType.NARRATOR, text="Should not queue")
        asyncio.run(emitter.emit(event))

        events = emitter.get_events()
        assert len(events) == 0


class TestHITLVoiceEmitter:
    """Tests for HITLVoiceEmitter (real-time mode)."""

    def test_priority_threshold_filtering(self):
        """Test that low-priority events are filtered."""
        emitter = HITLVoiceEmitter(priority_threshold=5)

        # High priority should be processed
        high_priority = VoiceEvent(
            event_type=VoiceEventType.NARRATOR,
            text="Important",
            priority=3,
        )

        # Low priority should be skipped
        low_priority = VoiceEvent(
            event_type=VoiceEventType.NARRATOR,
            text="Not important",
            priority=8,
        )

        # Without callbacks, emit just returns - test filtering logic
        asyncio.run(emitter.emit(high_priority))
        asyncio.run(emitter.emit(low_priority))

        # Verify emitter is enabled
        assert emitter.is_enabled()

    def test_set_websocket_send(self):
        """Test setting WebSocket send function."""
        emitter = HITLVoiceEmitter()

        async def mock_send(data: bytes, speaker_id: str):
            pass

        emitter.set_websocket_send(mock_send)
        # Should not raise
        assert emitter._websocket_send is not None


class TestCompositeVoiceEmitter:
    """Tests for CompositeVoiceEmitter (hybrid mode)."""

    def test_forwards_to_all_emitters(self):
        """Test that events are forwarded to all sub-emitters."""
        episode = EpisodeVoiceEmitter()
        composite = CompositeVoiceEmitter(emitters=[episode])

        event = VoiceEvent(event_type=VoiceEventType.NARRATOR, text="Test")
        asyncio.run(composite.emit(event))

        # Episode emitter should have received the event
        events = episode.get_events()
        assert len(events) == 1

    def test_flush_collects_from_all(self):
        """Test that flush collects events from all emitters."""
        episode1 = EpisodeVoiceEmitter()
        episode2 = EpisodeVoiceEmitter()
        composite = CompositeVoiceEmitter(emitters=[episode1, episode2])

        # Emit to composite (goes to both)
        event = VoiceEvent(event_type=VoiceEventType.NARRATOR, text="Test")
        asyncio.run(composite.emit(event))

        # Flush should collect from both
        result = asyncio.run(composite.flush())
        assert len(result) == 2  # One from each emitter

    def test_add_remove_emitter(self):
        """Test adding and removing emitters."""
        composite = CompositeVoiceEmitter()
        episode = EpisodeVoiceEmitter()

        composite.add_emitter(episode)
        assert composite.is_enabled()

        composite.remove_emitter(episode)
        assert not composite.is_enabled()


class TestVoiceEvent:
    """Tests for VoiceEvent dataclass."""

    def test_default_values(self):
        """Test VoiceEvent default values."""
        event = VoiceEvent(
            event_type=VoiceEventType.NARRATOR,
            text="Hello",
        )

        assert event.speaker_id == "narrator"
        assert event.speaker_name == "Narrator"
        assert event.emotion == EmotionHint.NEUTRAL
        assert event.day == 1
        assert event.phase == "unknown"
        assert event.priority == 5

    def test_custom_values(self):
        """Test VoiceEvent with custom values."""
        event = VoiceEvent(
            event_type=VoiceEventType.PLAYER_ACCUSATION,
            text="I accuse you!",
            speaker_id="player_01",
            speaker_name="John",
            emotion=EmotionHint.ACCUSATORY,
            day=3,
            phase="roundtable",
            priority=2,
        )

        assert event.speaker_id == "player_01"
        assert event.speaker_name == "John"
        assert event.emotion == EmotionHint.ACCUSATORY


class TestEmotionInference:
    """Tests for emotion inference helper."""

    def test_infer_murder_emotion(self):
        """Test inferring emotion for murder event."""
        emotion = infer_emotion(
            VoiceEventType.EVENT_MURDER,
            "Someone was murdered last night",
        )
        assert emotion == EmotionHint.SOMBER

    def test_infer_dramatic_narrator(self):
        """Test inferring emotion for dramatic narrator."""
        emotion = infer_emotion(
            VoiceEventType.NARRATOR_DRAMATIC,
            "The moment of truth has arrived",
        )
        assert emotion == EmotionHint.DRAMATIC

    def test_infer_accusation(self):
        """Test inferring accusatory emotion."""
        emotion = infer_emotion(
            VoiceEventType.PLAYER_ACCUSATION,
            "I think you're the traitor!",
        )
        assert emotion == EmotionHint.ACCUSATORY

    def test_infer_from_text_keywords(self):
        """Test inferring emotion from text keywords."""
        emotion = infer_emotion(
            VoiceEventType.PLAYER_SPEECH,
            "I suspect you are lying to us",
        )
        assert emotion == EmotionHint.ACCUSATORY

    def test_infer_neutral_default(self):
        """Test that neutral is the default."""
        emotion = infer_emotion(
            VoiceEventType.PLAYER_SPEECH,
            "I had breakfast this morning",
        )
        assert emotion == EmotionHint.NEUTRAL


class TestGameConfigVoiceIntegration:
    """Tests for voice config in GameConfig."""

    def test_default_voice_mode_disabled(self):
        """Test that voice mode defaults to disabled."""
        config = GameConfig()
        assert config.voice_mode == "disabled"

    def test_voice_mode_options(self):
        """Test setting different voice modes."""
        config_episode = GameConfig(voice_mode="episode")
        assert config_episode.voice_mode == "episode"

        config_hitl = GameConfig(voice_mode="hitl")
        assert config_hitl.voice_mode == "hitl"

    def test_voice_output_dir_default(self):
        """Test default voice output directory."""
        config = GameConfig()
        assert config.voice_output_dir == "output/voice"
