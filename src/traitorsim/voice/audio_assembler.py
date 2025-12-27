"""Audio assembler for TraitorSim voice integration.

Combines synthesized voice segments with background music and sound effects
to create complete episode audio files.

Features:
- Multi-track audio timeline
- Music bed layering with automatic ducking
- Sound effect triggers from script cue markers
- Crossfade and transition effects
- Export to various formats (MP3, WAV)

Usage:
    from traitorsim.voice import EpisodeAudioAssembler, MusicLibrary, SFXLibrary

    # Create assembler with libraries
    assembler = EpisodeAudioAssembler(
        elevenlabs_client=client,
        music_library=MusicLibrary(),
        sfx_library=SFXLibrary(),
    )

    # Assemble episode from script
    audio = await assembler.assemble_episode(script, episode_number=3)
    audio.export("episode_03.mp3", format="mp3")
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import io

import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

from .models import DialogueScript, DialogueSegment, SegmentType
from .chapters import (
    ChapterMarker,
    ChapterList,
    ChapterType,
    embed_chapters,
    export_chapters_json,
    export_chapters_podlove,
    export_chapters_webvtt,
    generate_episode_chapters,
    format_phase_title,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SIDECHAIN COMPRESSOR (DYNAMIC MIXING)
# =============================================================================

@dataclass
class SidechainConfig:
    """Configuration for sidechain compression.

    Sidechain compression uses a "trigger" signal (voice) to control
    the gain reduction applied to a "target" signal (music).

    This creates the "ducking" effect where music automatically gets
    quieter when someone is speaking.

    Attributes:
        threshold_db: Level above which compression engages (-60 to 0 dB)
        ratio: Compression ratio (1.0 = no compression, inf = limiting)
        attack_ms: Time to reach full compression (1-100ms typical)
        release_ms: Time to recover after trigger stops (50-500ms typical)
        makeup_gain_db: Gain applied after compression
        knee_db: Soft knee width (0 = hard knee, 6+ = soft knee)
        lookahead_ms: Delay target signal to anticipate trigger onset
        hold_ms: Time to hold compression after trigger falls below threshold
        range_db: Maximum gain reduction (limits ducking depth)
    """
    threshold_db: float = -24.0
    ratio: float = 4.0
    attack_ms: float = 10.0
    release_ms: float = 150.0
    makeup_gain_db: float = 0.0
    knee_db: float = 6.0
    lookahead_ms: float = 5.0
    hold_ms: float = 50.0
    range_db: float = -24.0  # Max 24dB of gain reduction


class SidechainCompressor:
    """Implements sidechain compression for automatic music ducking.

    This is the core DSP component for dynamic mixing. It analyzes
    the voice signal's envelope and applies proportional gain reduction
    to the music signal, creating smooth automatic ducking.

    The algorithm:
    1. Extract RMS envelope from trigger (voice) signal
    2. Apply attack/release smoothing to create gain control signal
    3. Compute gain reduction using compressor transfer function
    4. Apply gain to target (music) signal with optional lookahead

    Example:
        compressor = SidechainCompressor(SidechainConfig(
            threshold_db=-24,
            ratio=4.0,
            attack_ms=10,
            release_ms=150,
        ))

        ducked_music = compressor.process(
            trigger=voice_audio,
            target=music_audio,
            sample_rate=44100,
        )
    """

    def __init__(self, config: Optional[SidechainConfig] = None):
        """Initialize compressor with configuration.

        Args:
            config: Compression settings (uses defaults if None)
        """
        self.config = config or SidechainConfig()

    def process(
        self,
        trigger: np.ndarray,
        target: np.ndarray,
        sample_rate: int = 44100,
    ) -> np.ndarray:
        """Apply sidechain compression to target based on trigger.

        Args:
            trigger: Trigger signal (voice) as numpy array
            target: Target signal (music) to compress as numpy array
            sample_rate: Audio sample rate in Hz

        Returns:
            Compressed target signal as numpy array
        """
        if len(trigger) == 0 or len(target) == 0:
            return target

        # Ensure signals are same length (pad shorter with zeros)
        max_len = max(len(trigger), len(target))
        if len(trigger) < max_len:
            trigger = np.pad(trigger, (0, max_len - len(trigger)))
        if len(target) < max_len:
            target = np.pad(target, (0, max_len - len(target)))

        # Step 1: Extract envelope from trigger signal
        envelope_db = self._extract_envelope(trigger, sample_rate)

        # Step 2: Apply attack/release smoothing
        smoothed_envelope = self._apply_attack_release(envelope_db, sample_rate)

        # Step 3: Compute gain reduction
        gain_reduction_db = self._compute_gain_reduction(smoothed_envelope)

        # Step 4: Apply lookahead by delaying target
        lookahead_samples = int(self.config.lookahead_ms * sample_rate / 1000)
        if lookahead_samples > 0:
            # Delay target relative to gain envelope
            target = np.pad(target, (lookahead_samples, 0))[:max_len]

        # Step 5: Apply gain reduction
        gain_linear = self._db_to_linear(gain_reduction_db + self.config.makeup_gain_db)
        compressed = target * gain_linear

        return compressed

    def _extract_envelope(
        self,
        signal: np.ndarray,
        sample_rate: int,
        window_ms: float = 10.0,
    ) -> np.ndarray:
        """Extract RMS amplitude envelope from signal.

        Uses overlapping windows to compute local RMS, providing
        a smooth representation of the signal's loudness over time.

        Args:
            signal: Input signal
            sample_rate: Sample rate in Hz
            window_ms: Analysis window size in milliseconds

        Returns:
            Envelope in dB, same length as input
        """
        window_samples = max(1, int(window_ms * sample_rate / 1000))
        hop_samples = window_samples // 4  # 75% overlap

        # Compute RMS in overlapping windows
        num_frames = (len(signal) - window_samples) // hop_samples + 1
        if num_frames <= 0:
            # Signal too short, compute single RMS
            rms = np.sqrt(np.mean(signal ** 2))
            return np.full(len(signal), self._linear_to_db(rms))

        # Pre-allocate envelope
        envelope_frames = np.zeros(num_frames)

        for i in range(num_frames):
            start = i * hop_samples
            end = start + window_samples
            window = signal[start:end]
            rms = np.sqrt(np.mean(window ** 2))
            envelope_frames[i] = rms

        # Interpolate to full signal length
        frame_times = np.arange(num_frames) * hop_samples + window_samples // 2
        sample_times = np.arange(len(signal))
        envelope_linear = np.interp(sample_times, frame_times, envelope_frames)

        # Convert to dB
        return self._linear_to_db(envelope_linear)

    def _apply_attack_release(
        self,
        envelope_db: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """Apply attack/release smoothing to envelope.

        Attack: How fast the envelope rises (compression engages)
        Release: How fast the envelope falls (compression disengages)

        Uses first-order IIR filters for smooth transitions.

        Args:
            envelope_db: Raw envelope in dB
            sample_rate: Sample rate in Hz

        Returns:
            Smoothed envelope in dB
        """
        # Convert time constants to filter coefficients
        attack_coeff = np.exp(-1.0 / (self.config.attack_ms * sample_rate / 1000))
        release_coeff = np.exp(-1.0 / (self.config.release_ms * sample_rate / 1000))
        hold_samples = int(self.config.hold_ms * sample_rate / 1000)

        # Apply envelope follower with attack/release
        smoothed = np.zeros_like(envelope_db)
        current_level = envelope_db[0]
        hold_counter = 0

        for i in range(len(envelope_db)):
            input_level = envelope_db[i]

            if input_level > current_level:
                # Attack: input is louder, move up quickly
                current_level = attack_coeff * current_level + (1 - attack_coeff) * input_level
                hold_counter = hold_samples
            else:
                # Check hold time
                if hold_counter > 0:
                    hold_counter -= 1
                else:
                    # Release: input is quieter, move down slowly
                    current_level = release_coeff * current_level + (1 - release_coeff) * input_level

            smoothed[i] = current_level

        return smoothed

    def _compute_gain_reduction(self, envelope_db: np.ndarray) -> np.ndarray:
        """Compute gain reduction from envelope using compressor curve.

        Implements soft-knee compression transfer function:
        - Below threshold: no compression (0 dB gain reduction)
        - Above threshold: compress by ratio
        - In knee region: smooth transition

        Args:
            envelope_db: Smoothed envelope in dB

        Returns:
            Gain reduction in dB (negative values = attenuation)
        """
        threshold = self.config.threshold_db
        ratio = self.config.ratio
        knee = self.config.knee_db
        range_limit = self.config.range_db

        # Compute gain reduction for each sample
        gain_reduction = np.zeros_like(envelope_db)

        for i in range(len(envelope_db)):
            level = envelope_db[i]

            # Below knee region: no compression
            if level < threshold - knee / 2:
                reduction = 0.0

            # Above knee region: full compression
            elif level > threshold + knee / 2:
                over_threshold = level - threshold
                reduction = -over_threshold * (1 - 1 / ratio)

            # In knee region: soft transition
            else:
                # Quadratic interpolation in knee region
                x = level - (threshold - knee / 2)
                reduction = -(x ** 2) / (2 * knee) * (1 - 1 / ratio)

            # Limit gain reduction to range
            gain_reduction[i] = max(reduction, range_limit)

        return gain_reduction

    @staticmethod
    def _linear_to_db(linear: Union[float, np.ndarray], floor_db: float = -96.0) -> Union[float, np.ndarray]:
        """Convert linear amplitude to decibels.

        Args:
            linear: Linear amplitude value(s)
            floor_db: Minimum dB value for zero/negative inputs

        Returns:
            Value(s) in decibels
        """
        if isinstance(linear, np.ndarray):
            with np.errstate(divide='ignore', invalid='ignore'):
                db = 20 * np.log10(np.abs(linear))
                db = np.where(np.isfinite(db), db, floor_db)
                return np.maximum(db, floor_db)
        else:
            if linear <= 0:
                return floor_db
            return max(20 * np.log10(abs(linear)), floor_db)

    @staticmethod
    def _db_to_linear(db: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert decibels to linear amplitude.

        Args:
            db: Value(s) in decibels

        Returns:
            Linear amplitude value(s)
        """
        return 10 ** (db / 20)


def audio_segment_to_numpy(audio: AudioSegment) -> Tuple[np.ndarray, int]:
    """Convert AudioSegment to numpy array.

    Args:
        audio: pydub AudioSegment

    Returns:
        Tuple of (samples as float32 array normalized to [-1, 1], sample_rate)
    """
    # Get raw samples
    samples = np.array(audio.get_array_of_samples())

    # Convert to float and normalize
    if audio.sample_width == 1:
        samples = samples.astype(np.float32) / 128.0 - 1.0
    elif audio.sample_width == 2:
        samples = samples.astype(np.float32) / 32768.0
    elif audio.sample_width == 4:
        samples = samples.astype(np.float32) / 2147483648.0

    # If stereo, convert to mono by averaging channels
    if audio.channels == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)

    return samples, audio.frame_rate


def numpy_to_audio_segment(
    samples: np.ndarray,
    sample_rate: int,
    sample_width: int = 2,
    channels: int = 1,
) -> AudioSegment:
    """Convert numpy array back to AudioSegment.

    Args:
        samples: Float32 samples normalized to [-1, 1]
        sample_rate: Sample rate in Hz
        sample_width: Bytes per sample (1, 2, or 4)
        channels: Number of channels

    Returns:
        pydub AudioSegment
    """
    # Clip to valid range
    samples = np.clip(samples, -1.0, 1.0)

    # Convert to integer samples
    if sample_width == 1:
        int_samples = ((samples + 1.0) * 128).astype(np.int8)
    elif sample_width == 2:
        int_samples = (samples * 32767).astype(np.int16)
    elif sample_width == 4:
        int_samples = (samples * 2147483647).astype(np.int32)
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

    # If mono but output needs stereo, duplicate
    if channels == 2 and len(int_samples.shape) == 1:
        int_samples = np.column_stack([int_samples, int_samples]).flatten()

    # Create AudioSegment
    return AudioSegment(
        data=int_samples.tobytes(),
        sample_width=sample_width,
        frame_rate=sample_rate,
        channels=channels,
    )


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class MusicMood(str, Enum):
    """Background music mood categories."""
    TENSION = "tension"           # Building suspense
    DRAMATIC = "dramatic"         # Big reveals, banishments
    SOMBER = "somber"             # Murder reveals, losses
    MYSTERIOUS = "mysterious"     # Traitor meetings, scheming
    TRIUMPHANT = "triumphant"     # Victories, successful missions
    NEUTRAL = "neutral"           # General background
    BREAKFAST = "breakfast"       # Morning scenes
    ROUNDTABLE = "roundtable"     # Voting discussions


class SFXType(str, Enum):
    """Sound effect categories."""
    GAVEL = "gavel"               # Vote conclusion
    DOOR_CREAK = "door_creak"     # Turret entrance
    CLOCK_TICK = "clock_tick"     # Tension building
    HEARTBEAT = "heartbeat"       # Dramatic moments
    REVEAL_STING = "reveal_sting" # Role reveals
    VOTE_CAST = "vote_cast"       # Each vote
    MURDER_STING = "murder_sting" # Murder reveal
    SHIELD_BLOCK = "shield_block" # Shield protection
    RECRUITMENT = "recruitment"   # Traitor recruitment
    WHISPER = "whisper"           # Secret conversations


@dataclass
class AudioCue:
    """A cue marker for audio events."""
    timestamp_ms: int             # When to trigger
    cue_type: str                 # "music", "sfx", "duck", "fade"
    asset_id: str                 # Music/SFX identifier
    duration_ms: Optional[int] = None
    volume_db: float = 0.0        # Relative volume adjustment
    fade_in_ms: int = 0
    fade_out_ms: int = 0


@dataclass
class AudioTrack:
    """A single track in the audio timeline."""
    name: str
    audio: AudioSegment
    start_ms: int = 0
    volume_db: float = 0.0
    pan: float = 0.0              # -1.0 (left) to 1.0 (right)
    duck_under_voice: bool = False
    duck_amount_db: float = -12.0  # How much to duck

    @property
    def end_ms(self) -> int:
        """Calculate end timestamp."""
        return self.start_ms + len(self.audio)


@dataclass
class VoiceSegmentAudio:
    """Audio for a single voice segment."""
    segment: DialogueSegment
    audio: AudioSegment
    start_ms: int = 0

    @property
    def duration_ms(self) -> int:
        return len(self.audio)

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


# =============================================================================
# SOUND LIBRARIES
# =============================================================================

class SoundLibrary:
    """Base class for managing audio assets."""

    def __init__(self, library_path: Optional[str] = None):
        """Initialize sound library.

        Args:
            library_path: Path to audio files directory
        """
        self.library_path = Path(library_path) if library_path else None
        self._cache: Dict[str, AudioSegment] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def get(self, asset_id: str) -> Optional[AudioSegment]:
        """Get audio asset by ID.

        Args:
            asset_id: Unique identifier for the asset

        Returns:
            AudioSegment or None if not found
        """
        if asset_id in self._cache:
            return self._cache[asset_id]

        # Try to load from file
        audio = self._load_asset(asset_id)
        if audio:
            self._cache[asset_id] = audio
        return audio

    def _load_asset(self, asset_id: str) -> Optional[AudioSegment]:
        """Load asset from file system.

        Args:
            asset_id: Asset identifier

        Returns:
            AudioSegment or None
        """
        if not self.library_path:
            return self._generate_placeholder(asset_id)

        # Try common extensions
        for ext in [".mp3", ".wav", ".ogg", ".m4a"]:
            filepath = self.library_path / f"{asset_id}{ext}"
            if filepath.exists():
                try:
                    return AudioSegment.from_file(str(filepath))
                except Exception as e:
                    logger.warning(f"Failed to load {filepath}: {e}")

        # Generate placeholder if file not found
        return self._generate_placeholder(asset_id)

    def _generate_placeholder(self, asset_id: str, duration_ms: int = 1000) -> AudioSegment:
        """Generate silent placeholder audio.

        Args:
            asset_id: Asset identifier (for logging)
            duration_ms: Duration of placeholder

        Returns:
            Silent AudioSegment
        """
        logger.debug(f"Generating placeholder for {asset_id} ({duration_ms}ms)")
        return AudioSegment.silent(duration=duration_ms)

    def list_assets(self) -> List[str]:
        """List all available asset IDs."""
        if not self.library_path or not self.library_path.exists():
            return list(self._metadata.keys())

        assets = set()
        for ext in [".mp3", ".wav", ".ogg", ".m4a"]:
            for filepath in self.library_path.glob(f"*{ext}"):
                assets.add(filepath.stem)
        return sorted(assets)

    def register_asset(self, asset_id: str, metadata: Dict[str, Any]) -> None:
        """Register asset metadata without loading audio.

        Args:
            asset_id: Unique identifier
            metadata: Asset metadata (duration, mood, etc.)
        """
        self._metadata[asset_id] = metadata


class MusicLibrary(SoundLibrary):
    """Library of background music tracks."""

    # Default music tracks with metadata
    DEFAULT_TRACKS = {
        MusicMood.TENSION: {
            "duration_ms": 120000,  # 2 min loop
            "bpm": 80,
            "description": "Building tension, strings and low synth",
        },
        MusicMood.DRAMATIC: {
            "duration_ms": 60000,
            "bpm": 100,
            "description": "Dramatic reveal, orchestral hit",
        },
        MusicMood.SOMBER: {
            "duration_ms": 90000,
            "bpm": 60,
            "description": "Sad, reflective piano",
        },
        MusicMood.MYSTERIOUS: {
            "duration_ms": 120000,
            "bpm": 70,
            "description": "Dark, sneaky, minor key",
        },
        MusicMood.TRIUMPHANT: {
            "duration_ms": 45000,
            "bpm": 120,
            "description": "Victorious, major key brass",
        },
        MusicMood.NEUTRAL: {
            "duration_ms": 180000,
            "bpm": 90,
            "description": "Neutral underscore",
        },
        MusicMood.BREAKFAST: {
            "duration_ms": 90000,
            "bpm": 85,
            "description": "Morning atmosphere, light strings",
        },
        MusicMood.ROUNDTABLE: {
            "duration_ms": 150000,
            "bpm": 75,
            "description": "Discussion tension, building suspense",
        },
    }

    def __init__(self, library_path: Optional[str] = None):
        super().__init__(library_path)

        # Register default tracks
        for mood, metadata in self.DEFAULT_TRACKS.items():
            self.register_asset(mood.value, metadata)

    def get_for_mood(self, mood: MusicMood, duration_ms: Optional[int] = None) -> AudioSegment:
        """Get music track for a specific mood.

        Args:
            mood: Desired music mood
            duration_ms: Optional duration to trim/loop to

        Returns:
            AudioSegment for the mood
        """
        audio = self.get(mood.value)

        if audio is None:
            metadata = self.DEFAULT_TRACKS.get(mood, {"duration_ms": 60000})
            audio = self._generate_placeholder(mood.value, metadata["duration_ms"])

        # Adjust duration if specified
        if duration_ms:
            if len(audio) < duration_ms:
                # Loop to fill duration
                audio = self._loop_to_duration(audio, duration_ms)
            elif len(audio) > duration_ms:
                # Trim with fade out
                audio = audio[:duration_ms].fade_out(2000)

        return audio

    def _loop_to_duration(self, audio: AudioSegment, target_ms: int) -> AudioSegment:
        """Loop audio to reach target duration.

        Args:
            audio: Source audio
            target_ms: Target duration

        Returns:
            Looped AudioSegment
        """
        result = audio
        while len(result) < target_ms:
            # Crossfade loop point
            result = result.append(audio, crossfade=500)
        return result[:target_ms]

    def get_phase_music(self, phase: str) -> Tuple[MusicMood, AudioSegment]:
        """Get appropriate music for a game phase.

        Args:
            phase: Game phase name

        Returns:
            Tuple of (mood, AudioSegment)
        """
        phase_moods = {
            "breakfast": MusicMood.BREAKFAST,
            "mission": MusicMood.TENSION,
            "social": MusicMood.NEUTRAL,
            "roundtable": MusicMood.ROUNDTABLE,
            "turret": MusicMood.MYSTERIOUS,
        }
        mood = phase_moods.get(phase.lower(), MusicMood.NEUTRAL)
        return mood, self.get_for_mood(mood)


class SFXLibrary(SoundLibrary):
    """Library of sound effects."""

    # Default SFX with metadata
    DEFAULT_SFX = {
        SFXType.GAVEL: {"duration_ms": 800, "description": "Wooden gavel strike"},
        SFXType.DOOR_CREAK: {"duration_ms": 2000, "description": "Creaky door opening"},
        SFXType.CLOCK_TICK: {"duration_ms": 500, "description": "Clock ticking"},
        SFXType.HEARTBEAT: {"duration_ms": 1000, "description": "Heartbeat thump"},
        SFXType.REVEAL_STING: {"duration_ms": 1500, "description": "Dramatic reveal sting"},
        SFXType.VOTE_CAST: {"duration_ms": 300, "description": "Vote being cast"},
        SFXType.MURDER_STING: {"duration_ms": 2000, "description": "Dark murder reveal"},
        SFXType.SHIELD_BLOCK: {"duration_ms": 1200, "description": "Shield protection sound"},
        SFXType.RECRUITMENT: {"duration_ms": 1800, "description": "Recruitment offer"},
        SFXType.WHISPER: {"duration_ms": 600, "description": "Whispered secret"},
    }

    def __init__(self, library_path: Optional[str] = None):
        super().__init__(library_path)

        # Register default SFX
        for sfx_type, metadata in self.DEFAULT_SFX.items():
            self.register_asset(sfx_type.value, metadata)

    def get_sfx(self, sfx_type: SFXType) -> AudioSegment:
        """Get sound effect by type.

        Args:
            sfx_type: Type of sound effect

        Returns:
            AudioSegment for the effect
        """
        audio = self.get(sfx_type.value)

        if audio is None:
            metadata = self.DEFAULT_SFX.get(sfx_type, {"duration_ms": 500})
            audio = self._generate_placeholder(sfx_type.value, metadata["duration_ms"])

        return audio


# =============================================================================
# AUDIO TIMELINE
# =============================================================================

class AudioTimeline:
    """Multi-track audio timeline for mixing."""

    def __init__(self):
        self.tracks: List[AudioTrack] = []
        self.voice_segments: List[VoiceSegmentAudio] = []
        self.cues: List[AudioCue] = []
        self._sample_rate = 44100
        self._channels = 2

    @property
    def duration_ms(self) -> int:
        """Total timeline duration in milliseconds."""
        max_end = 0
        for track in self.tracks:
            max_end = max(max_end, track.end_ms)
        for segment in self.voice_segments:
            max_end = max(max_end, segment.end_ms)
        return max_end

    def add_voice_segment(
        self,
        segment: DialogueSegment,
        audio: AudioSegment,
        start_ms: Optional[int] = None,
        gap_after_ms: int = 500,
    ) -> VoiceSegmentAudio:
        """Add a voice segment to the timeline.

        Args:
            segment: DialogueSegment with metadata
            audio: Synthesized audio
            start_ms: Start time (auto-calculated if None)
            gap_after_ms: Gap after this segment

        Returns:
            VoiceSegmentAudio added to timeline
        """
        if start_ms is None:
            # Auto-calculate start time after last segment
            if self.voice_segments:
                start_ms = self.voice_segments[-1].end_ms + gap_after_ms
            else:
                start_ms = 0

        voice_audio = VoiceSegmentAudio(
            segment=segment,
            audio=audio,
            start_ms=start_ms,
        )
        self.voice_segments.append(voice_audio)

        # Add cues from segment
        self._add_segment_cues(voice_audio)

        return voice_audio

    def _add_segment_cues(self, voice_audio: VoiceSegmentAudio) -> None:
        """Add audio cues based on segment metadata."""
        segment = voice_audio.segment

        # Add SFX cues based on segment type and event
        if segment.event_type == "VOTE_TALLY":
            self.cues.append(AudioCue(
                timestamp_ms=voice_audio.end_ms,
                cue_type="sfx",
                asset_id=SFXType.GAVEL.value,
            ))
        elif segment.event_type == "MURDER":
            self.cues.append(AudioCue(
                timestamp_ms=voice_audio.start_ms,
                cue_type="sfx",
                asset_id=SFXType.MURDER_STING.value,
            ))

        # Add music cues from segment metadata
        if segment.music_cue:
            self.cues.append(AudioCue(
                timestamp_ms=voice_audio.start_ms,
                cue_type="music",
                asset_id=segment.music_cue,
                fade_in_ms=1000,
            ))

        # Add SFX cues from segment metadata
        if segment.sfx:
            self.cues.append(AudioCue(
                timestamp_ms=voice_audio.start_ms,
                cue_type="sfx",
                asset_id=segment.sfx,
            ))

    def add_track(
        self,
        name: str,
        audio: AudioSegment,
        start_ms: int = 0,
        volume_db: float = 0.0,
        duck_under_voice: bool = False,
    ) -> AudioTrack:
        """Add a background track to the timeline.

        Args:
            name: Track identifier
            audio: Audio content
            start_ms: Start time
            volume_db: Volume adjustment in dB
            duck_under_voice: Whether to duck under voice

        Returns:
            AudioTrack added to timeline
        """
        track = AudioTrack(
            name=name,
            audio=audio,
            start_ms=start_ms,
            volume_db=volume_db,
            duck_under_voice=duck_under_voice,
        )
        self.tracks.append(track)
        return track

    def add_music_bed(
        self,
        mood: MusicMood,
        music_library: MusicLibrary,
        start_ms: int = 0,
        duration_ms: Optional[int] = None,
        volume_db: float = -12.0,
    ) -> AudioTrack:
        """Add a music bed that ducks under voice.

        Args:
            mood: Music mood
            music_library: Library to get music from
            start_ms: Start time
            duration_ms: Duration (full timeline if None)
            volume_db: Base volume (will duck further under voice)

        Returns:
            AudioTrack for the music bed
        """
        if duration_ms is None:
            # Will be extended when mixing
            duration_ms = 60000  # 1 minute default

        audio = music_library.get_for_mood(mood, duration_ms)

        return self.add_track(
            name=f"music_{mood.value}",
            audio=audio,
            start_ms=start_ms,
            volume_db=volume_db,
            duck_under_voice=True,
        )

    def add_sfx(
        self,
        sfx_type: SFXType,
        sfx_library: SFXLibrary,
        start_ms: int,
        volume_db: float = 0.0,
    ) -> AudioTrack:
        """Add a sound effect at a specific time.

        Args:
            sfx_type: Type of sound effect
            sfx_library: Library to get SFX from
            start_ms: When to play the effect
            volume_db: Volume adjustment

        Returns:
            AudioTrack for the SFX
        """
        audio = sfx_library.get_sfx(sfx_type)

        return self.add_track(
            name=f"sfx_{sfx_type.value}_{start_ms}",
            audio=audio,
            start_ms=start_ms,
            volume_db=volume_db,
            duck_under_voice=False,
        )

    def mix(self, normalize_output: bool = True) -> AudioSegment:
        """Mix all tracks into final audio.

        Args:
            normalize_output: Whether to normalize the final mix

        Returns:
            Mixed AudioSegment
        """
        duration = self.duration_ms
        if duration == 0:
            return AudioSegment.silent(duration=1000)

        # Create base silent track
        mixed = AudioSegment.silent(duration=duration)

        # Calculate voice regions for ducking
        voice_regions = self._calculate_voice_regions()

        # Add music/SFX tracks with ducking
        for track in self.tracks:
            track_audio = track.audio + track.volume_db

            # Apply ducking if needed
            if track.duck_under_voice:
                track_audio = self._apply_ducking(track_audio, track.start_ms, voice_regions)

            # Overlay at correct position
            mixed = mixed.overlay(track_audio, position=track.start_ms)

        # Add voice segments (always on top)
        for voice in self.voice_segments:
            mixed = mixed.overlay(voice.audio, position=voice.start_ms)

        # Normalize if requested
        if normalize_output:
            mixed = normalize(mixed)

        return mixed

    def _calculate_voice_regions(self) -> List[Tuple[int, int]]:
        """Calculate time regions where voice is active.

        Returns:
            List of (start_ms, end_ms) tuples
        """
        regions = []
        for voice in self.voice_segments:
            regions.append((voice.start_ms, voice.end_ms))

        # Sort and merge overlapping regions
        regions.sort(key=lambda x: x[0])
        merged = []
        for start, end in regions:
            if merged and start <= merged[-1][1]:
                # Extend previous region
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        return merged

    def _apply_ducking(
        self,
        audio: AudioSegment,
        track_start: int,
        voice_regions: List[Tuple[int, int]],
        duck_db: float = -12.0,
        fade_ms: int = 200,
    ) -> AudioSegment:
        """Apply volume ducking during voice regions (simple cut-based).

        This is the legacy ducking method that applies fixed dB reduction
        during voice regions. For smoother, more professional results,
        use apply_sidechain_compression() instead.

        Args:
            audio: Audio to duck
            track_start: Track's start position in timeline
            voice_regions: List of (start, end) voice regions
            duck_db: Amount to duck in dB
            fade_ms: Fade time for ducking

        Returns:
            Ducked AudioSegment
        """
        track_end = track_start + len(audio)

        # Find overlapping voice regions
        for voice_start, voice_end in voice_regions:
            # Check for overlap
            if voice_end < track_start or voice_start > track_end:
                continue

            # Calculate overlap in track's time frame
            overlap_start = max(0, voice_start - track_start)
            overlap_end = min(len(audio), voice_end - track_start)

            if overlap_end <= overlap_start:
                continue

            # Extract and duck the overlapping section
            before = audio[:max(0, overlap_start - fade_ms)]
            duck_section = audio[overlap_start:overlap_end] + duck_db
            after = audio[min(len(audio), overlap_end + fade_ms):]

            # Add fades
            if overlap_start > fade_ms:
                fade_out = audio[overlap_start - fade_ms:overlap_start].fade_out(fade_ms)
                before = before + fade_out + duck_db

            if overlap_end + fade_ms < len(audio):
                fade_in = audio[overlap_end:overlap_end + fade_ms].fade_in(fade_ms)
                after = (fade_in + duck_db) + after

            # Reconstruct
            audio = before + duck_section + after

        return audio

    def apply_sidechain_compression(
        self,
        trigger_tracks: Union[str, List[str]] = "voice",
        duck_tracks: Union[str, List[str]] = "music",
        config: Optional[SidechainConfig] = None,
    ) -> None:
        """Apply sidechain compression to duck tracks under trigger tracks.

        This provides professional-quality dynamic mixing where music
        automatically ducks in response to voice levels, with smooth
        attack/release characteristics.

        The design doc API:
            timeline.apply_sidechain_compression(
                trigger_tracks="voice",
                duck_tracks="music",
                ratio=3.0,
                threshold=-24
            )

        Args:
            trigger_tracks: Track name pattern(s) to use as sidechain trigger.
                            "voice" matches all voice segments.
                            Can be a string or list of strings.
            duck_tracks: Track name pattern(s) to apply compression to.
                         "music" matches tracks starting with "music_".
                         Can be a string or list of strings.
            config: Sidechain compression configuration. If None, uses defaults
                    optimized for voice-over-music ducking.

        Example:
            timeline = AudioTimeline()
            # Add voice and music tracks...
            timeline.apply_sidechain_compression(
                trigger_tracks="voice",
                duck_tracks="music",
                config=SidechainConfig(
                    threshold_db=-24,
                    ratio=4.0,
                    attack_ms=10,
                    release_ms=150,
                ),
            )
            mixed = timeline.mix()
        """
        if config is None:
            # Default config optimized for voice-over-music
            config = SidechainConfig(
                threshold_db=-24.0,
                ratio=4.0,
                attack_ms=10.0,
                release_ms=150.0,
                knee_db=6.0,
                lookahead_ms=5.0,
                hold_ms=50.0,
                range_db=-18.0,  # Max 18dB reduction
            )

        compressor = SidechainCompressor(config)

        # Normalize input to lists
        if isinstance(trigger_tracks, str):
            trigger_tracks = [trigger_tracks]
        if isinstance(duck_tracks, str):
            duck_tracks = [duck_tracks]

        # Build combined trigger signal from matching tracks/segments
        trigger_signal = self._build_trigger_signal(trigger_tracks)
        if trigger_signal is None or len(trigger_signal) == 0:
            logger.warning("No trigger signal found for sidechain compression")
            return

        # Apply compression to each matching duck track
        for track in self.tracks:
            if not self._track_matches_patterns(track.name, duck_tracks):
                continue

            # Convert track audio to numpy
            target_samples, sample_rate = audio_segment_to_numpy(track.audio)

            # Align trigger signal with track position
            aligned_trigger = self._align_signal_to_track(
                trigger_signal,
                track.start_ms,
                len(target_samples),
                sample_rate
            )

            # Apply sidechain compression
            compressed_samples = compressor.process(
                trigger=aligned_trigger,
                target=target_samples,
                sample_rate=sample_rate,
            )

            # Convert back to AudioSegment
            track.audio = numpy_to_audio_segment(
                compressed_samples,
                sample_rate=sample_rate,
                sample_width=2,
                channels=1,
            )

            # Mark that this track has been processed (no longer needs legacy ducking)
            track.duck_under_voice = False

            logger.debug(f"Applied sidechain compression to track: {track.name}")

    def _build_trigger_signal(self, patterns: List[str]) -> Optional[np.ndarray]:
        """Build combined trigger signal from matching tracks/voice segments.

        Args:
            patterns: List of patterns to match. "voice" matches voice segments.

        Returns:
            Combined trigger signal as numpy array, or None if no matches.
        """
        duration_ms = self.duration_ms
        if duration_ms == 0:
            return None

        # Determine sample rate (use first track or default)
        sample_rate = self._sample_rate
        total_samples = int(duration_ms * sample_rate / 1000)
        combined = np.zeros(total_samples, dtype=np.float32)

        has_content = False

        # Check for "voice" pattern - combine all voice segments
        if "voice" in patterns:
            for voice in self.voice_segments:
                voice_samples, voice_sr = audio_segment_to_numpy(voice.audio)

                # Calculate position in combined signal
                start_sample = int(voice.start_ms * sample_rate / 1000)
                end_sample = start_sample + len(voice_samples)

                # Ensure within bounds
                if end_sample > total_samples:
                    voice_samples = voice_samples[:total_samples - start_sample]
                    end_sample = total_samples

                if start_sample < total_samples and len(voice_samples) > 0:
                    combined[start_sample:end_sample] = np.maximum(
                        combined[start_sample:end_sample],
                        np.abs(voice_samples[:end_sample - start_sample])
                    )
                    has_content = True

        # Check for named track patterns
        for track in self.tracks:
            if self._track_matches_patterns(track.name, patterns):
                track_samples, track_sr = audio_segment_to_numpy(track.audio)

                start_sample = int(track.start_ms * sample_rate / 1000)
                end_sample = start_sample + len(track_samples)

                if end_sample > total_samples:
                    track_samples = track_samples[:total_samples - start_sample]
                    end_sample = total_samples

                if start_sample < total_samples and len(track_samples) > 0:
                    combined[start_sample:end_sample] = np.maximum(
                        combined[start_sample:end_sample],
                        np.abs(track_samples[:end_sample - start_sample])
                    )
                    has_content = True

        return combined if has_content else None

    def _align_signal_to_track(
        self,
        signal: np.ndarray,
        track_start_ms: int,
        target_length: int,
        sample_rate: int,
    ) -> np.ndarray:
        """Align a timeline-wide signal to a specific track's time window.

        Args:
            signal: Full timeline signal
            track_start_ms: Track's start position in timeline
            target_length: Length of target track in samples
            sample_rate: Sample rate

        Returns:
            Signal segment aligned to track's time window
        """
        start_sample = int(track_start_ms * sample_rate / 1000)
        end_sample = start_sample + target_length

        if start_sample >= len(signal):
            return np.zeros(target_length, dtype=np.float32)

        if end_sample > len(signal):
            # Pad with zeros at end
            segment = signal[start_sample:]
            return np.pad(segment, (0, target_length - len(segment)))

        return signal[start_sample:end_sample]

    def _track_matches_patterns(self, track_name: str, patterns: List[str]) -> bool:
        """Check if a track name matches any of the given patterns.

        Args:
            track_name: Name of the track
            patterns: List of patterns to match

        Returns:
            True if track matches any pattern
        """
        track_lower = track_name.lower()

        for pattern in patterns:
            pattern_lower = pattern.lower()

            # Special handling for common patterns
            if pattern_lower == "music":
                if track_lower.startswith("music_"):
                    return True
            elif pattern_lower == "sfx":
                if track_lower.startswith("sfx_"):
                    return True
            elif pattern_lower == "voice":
                # Voice is handled separately via voice_segments
                continue
            else:
                # Direct match or prefix match
                if track_lower == pattern_lower or track_lower.startswith(pattern_lower):
                    return True

        return False

    def generate_chapters(
        self,
        include_events: bool = True,
        include_confessionals: bool = False,
        min_duration_ms: int = 10000,
        episode_title: Optional[str] = None,
        episode_number: Optional[int] = None,
    ) -> ChapterList:
        """Generate chapter markers from timeline content.

        Analyzes voice segments to identify phase transitions and
        significant events, creating chapter markers for podcast-style
        navigation.

        Args:
            include_events: Include event chapters (murder, banishment)
            include_confessionals: Include per-confessional chapters
            min_duration_ms: Minimum chapter duration (merge shorter)
            episode_title: Optional episode title for metadata
            episode_number: Optional episode number for metadata

        Returns:
            ChapterList with generated chapters
        """
        chapters = ChapterList(
            episode_title=episode_title,
            episode_number=episode_number,
            total_duration_ms=self.duration_ms,
        )

        if not self.voice_segments:
            return chapters

        # Track phase transitions
        current_phase = None
        phase_start_ms = 0

        for voice in self.voice_segments:
            segment = voice.segment

            # Get phase from segment
            phase = getattr(segment, "phase", None)
            if phase is None and hasattr(segment, "metadata"):
                phase = segment.metadata.get("phase")

            # Phase changed - add chapter
            if phase and phase != current_phase:
                chapters.add_phase(
                    phase=phase,
                    start_ms=voice.start_ms,
                )
                current_phase = phase
                phase_start_ms = voice.start_ms

            # Check for significant events
            if include_events:
                event_type = getattr(segment, "event_type", None)
                if event_type in ("MURDER", "BANISHMENT", "ROLE_REVEAL", "VOTE_TALLY"):
                    # Get event details for better titles
                    details = {}
                    if hasattr(segment, "speaker_name"):
                        if event_type == "MURDER":
                            details["victim_name"] = segment.speaker_name
                        elif event_type == "BANISHMENT":
                            details["banished_name"] = segment.speaker_name

                    from .chapters import format_event_title
                    chapters.add_event(
                        event_type=event_type,
                        start_ms=voice.start_ms,
                        title=format_event_title(event_type, details),
                    )

            # Check for confessionals
            if include_confessionals:
                seg_type = segment.segment_type
                if seg_type == SegmentType.CONFESSIONAL:
                    speaker_name = getattr(segment, "speaker_name", None)
                    speaker_id = getattr(segment, "speaker_id", None)
                    if speaker_name:
                        chapters.add_confessional(
                            speaker_name=speaker_name,
                            speaker_id=speaker_id or "unknown",
                            start_ms=voice.start_ms,
                        )

        # Finalize and clean up
        chapters.finalize(self.duration_ms)
        chapters.merge_short_chapters(min_duration_ms)

        return chapters


# =============================================================================
# EPISODE AUDIO ASSEMBLER
# =============================================================================

class EpisodeAudioAssembler:
    """Assembles complete episode audio from voice scripts."""

    def __init__(
        self,
        elevenlabs_client: Optional[Any] = None,
        music_library: Optional[MusicLibrary] = None,
        sfx_library: Optional[SFXLibrary] = None,
        output_format: str = "mp3",
        output_bitrate: str = "192k",
        use_sidechain: bool = True,
        sidechain_config: Optional[SidechainConfig] = None,
    ):
        """Initialize episode assembler.

        Args:
            elevenlabs_client: ElevenLabs client for voice synthesis
            music_library: Background music library
            sfx_library: Sound effects library
            output_format: Output audio format
            output_bitrate: Output bitrate for MP3
            use_sidechain: Use sidechain compression for dynamic mixing (default True).
                           If False, uses legacy simple ducking.
            sidechain_config: Custom sidechain compression settings. If None, uses
                              optimized defaults for voice-over-music.
        """
        self.client = elevenlabs_client
        self.music_library = music_library or MusicLibrary()
        self.sfx_library = sfx_library or SFXLibrary()
        self.output_format = output_format
        self.output_bitrate = output_bitrate
        self.use_sidechain = use_sidechain
        self.sidechain_config = sidechain_config

        # Timing configuration
        self.segment_gap_ms = 500       # Gap between dialogue segments
        self.phase_transition_ms = 2000  # Transition between phases
        self.intro_music_ms = 5000       # Intro music before content
        self.outro_music_ms = 3000       # Outro music after content

        # Store last assembled timeline for chapter generation
        self._last_timeline: Optional[AudioTimeline] = None
        self._last_episode_number: int = 0

    async def assemble_episode(
        self,
        script: DialogueScript,
        episode_number: int = 1,
        include_music: bool = True,
        include_sfx: bool = True,
    ) -> AudioSegment:
        """Assemble complete episode audio from script.

        Args:
            script: DialogueScript with all segments
            episode_number: Episode number for metadata
            include_music: Whether to include background music
            include_sfx: Whether to include sound effects

        Returns:
            Complete episode AudioSegment
        """
        logger.info(f"Assembling episode {episode_number} with {len(script.segments)} segments")

        # Create timeline
        timeline = AudioTimeline()

        # Generate voice audio for all segments
        await self._add_voice_segments(timeline, script)

        # Add intro music
        if include_music:
            timeline.add_music_bed(
                mood=MusicMood.TENSION,
                music_library=self.music_library,
                start_ms=0,
                duration_ms=self.intro_music_ms,
                volume_db=-6.0,  # Louder before voice starts
            )

        # Add phase-specific music beds
        if include_music:
            self._add_phase_music(timeline, script)

        # Add sound effects from cues
        if include_sfx:
            self._add_sfx_from_cues(timeline)

        # Apply sidechain compression for dynamic mixing
        if include_music and self.use_sidechain:
            timeline.apply_sidechain_compression(
                trigger_tracks="voice",
                duck_tracks="music",
                config=self.sidechain_config,
            )

        # Mix everything
        mixed = timeline.mix(normalize_output=True)

        # Store timeline for chapter generation
        self._last_timeline = timeline
        self._last_episode_number = episode_number

        logger.info(f"Episode {episode_number} assembled: {len(mixed) / 1000:.1f}s")

        return mixed

    def generate_chapters(
        self,
        episode_title: Optional[str] = None,
        include_events: bool = True,
        include_confessionals: bool = False,
        min_duration_ms: int = 10000,
    ) -> ChapterList:
        """Generate chapter markers from the last assembled episode.

        Must be called after assemble_episode(). Analyzes the assembled
        timeline to create chapter markers for podcast-style navigation.

        Args:
            episode_title: Optional title for episode metadata
            include_events: Include event chapters (murder, banishment)
            include_confessionals: Include per-confessional chapters
            min_duration_ms: Minimum chapter duration (merge shorter)

        Returns:
            ChapterList with generated chapters

        Raises:
            ValueError: If no episode has been assembled yet
        """
        if self._last_timeline is None:
            raise ValueError("No episode assembled yet. Call assemble_episode() first.")

        return self._last_timeline.generate_chapters(
            include_events=include_events,
            include_confessionals=include_confessionals,
            min_duration_ms=min_duration_ms,
            episode_title=episode_title,
            episode_number=self._last_episode_number,
        )

    async def _add_voice_segments(
        self,
        timeline: AudioTimeline,
        script: DialogueScript,
    ) -> None:
        """Generate and add all voice segments to timeline.

        Args:
            timeline: AudioTimeline to add to
            script: DialogueScript with segments
        """
        current_time = self.intro_music_ms

        for segment in script.segments:
            # Get voice audio (synthesized or mock)
            audio = await self._synthesize_segment(segment)

            # Add to timeline
            timeline.add_voice_segment(
                segment=segment,
                audio=audio,
                start_ms=current_time,
                gap_after_ms=self.segment_gap_ms,
            )

            current_time += len(audio) + self.segment_gap_ms

    async def _synthesize_segment(self, segment: DialogueSegment) -> AudioSegment:
        """Synthesize audio for a single segment.

        Args:
            segment: DialogueSegment to synthesize

        Returns:
            AudioSegment with voice audio
        """
        text = segment.to_tagged_text()

        if self.client:
            try:
                # Use ElevenLabs client
                result = await self.client.text_to_speech(
                    text=text,
                    voice_id=segment.voice_id,
                )

                # Convert bytes to AudioSegment
                audio = AudioSegment.from_mp3(io.BytesIO(result.audio_data))
                return audio

            except Exception as e:
                logger.warning(f"Voice synthesis failed for segment: {e}")

        # Generate placeholder based on text length
        # Average speaking rate: ~150 words/min = ~750 chars/min
        duration_ms = int((len(segment.text) / 750) * 60 * 1000)
        duration_ms = max(500, duration_ms)  # Minimum 500ms

        return AudioSegment.silent(duration=duration_ms)

    def _add_phase_music(self, timeline: AudioTimeline, script: DialogueScript) -> None:
        """Add phase-appropriate background music.

        Args:
            timeline: AudioTimeline to add to
            script: DialogueScript with phase info
        """
        # Group segments by phase
        phases = script.group_by_phase()

        for phase, segments in phases.items():
            if not segments:
                continue

            # Find phase time range
            phase_start = None
            phase_end = None

            for voice in timeline.voice_segments:
                if voice.segment in segments:
                    if phase_start is None:
                        phase_start = voice.start_ms
                    phase_end = voice.end_ms

            if phase_start is None:
                continue

            # Get appropriate music
            mood, _ = self.music_library.get_phase_music(phase)

            # Add music bed for this phase
            duration = phase_end - phase_start + 2000  # Extra buffer
            timeline.add_music_bed(
                mood=mood,
                music_library=self.music_library,
                start_ms=max(0, phase_start - 1000),  # Start slightly before
                duration_ms=duration,
                volume_db=-15.0,  # Quieter under voice
            )

    def _add_sfx_from_cues(self, timeline: AudioTimeline) -> None:
        """Add sound effects based on timeline cues.

        Args:
            timeline: AudioTimeline with cues
        """
        for cue in timeline.cues:
            if cue.cue_type != "sfx":
                continue

            # Try to parse as SFXType
            try:
                sfx_type = SFXType(cue.asset_id)
            except ValueError:
                # Custom SFX ID, try to load directly
                audio = self.sfx_library.get(cue.asset_id)
                if audio:
                    timeline.add_track(
                        name=f"sfx_{cue.asset_id}",
                        audio=audio,
                        start_ms=cue.timestamp_ms,
                        volume_db=cue.volume_db,
                    )
                continue

            timeline.add_sfx(
                sfx_type=sfx_type,
                sfx_library=self.sfx_library,
                start_ms=cue.timestamp_ms,
                volume_db=cue.volume_db,
            )

    def export_episode(
        self,
        audio: AudioSegment,
        output_path: str,
        format: Optional[str] = None,
        chapters: Optional[ChapterList] = None,
        embed_chapters: bool = True,
        export_chapter_files: bool = True,
    ) -> str:
        """Export episode audio to file with optional chapter markers.

        Exports the audio file and optionally embeds chapter markers
        for podcast-style navigation. Can also export external chapter
        files (JSON, Podlove) for podcast hosting platforms.

        Args:
            audio: Episode AudioSegment
            output_path: Output file path
            format: Override output format
            chapters: ChapterList to embed (auto-generated if None)
            embed_chapters: Whether to embed chapters in audio file
            export_chapter_files: Whether to export external chapter files

        Returns:
            Path to exported file
        """
        format = format or self.output_format
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Auto-generate chapters if not provided and we have a timeline
        if chapters is None and self._last_timeline is not None:
            try:
                chapters = self.generate_chapters()
            except ValueError:
                chapters = None

        # Export with appropriate settings
        if format == "mp3":
            audio.export(
                str(output_path),
                format="mp3",
                bitrate=self.output_bitrate,
                tags={
                    "artist": "TraitorSim",
                    "album": "The Traitors AI Simulation",
                    "track": str(self._last_episode_number) if self._last_episode_number else "1",
                }
            )

            # Embed chapters in MP3
            if embed_chapters and chapters and len(chapters) > 0:
                try:
                    from .chapters import embed_chapters as do_embed
                    success = do_embed(str(output_path), chapters)
                    if success:
                        logger.info(f"Embedded {len(chapters)} chapters in {output_path}")
                    else:
                        logger.warning(f"Failed to embed chapters in {output_path}")
                except Exception as e:
                    logger.warning(f"Chapter embedding failed: {e}")

        elif format in ("m4a", "aac"):
            # For M4A, we need to handle chapter embedding differently
            temp_path = output_path.with_suffix(".temp.m4a")
            audio.export(str(temp_path), format="ipod")

            if embed_chapters and chapters and len(chapters) > 0:
                try:
                    from .chapters import embed_chapters_m4a
                    success = embed_chapters_m4a(
                        str(temp_path),
                        str(output_path),
                        chapters,
                    )
                    if success:
                        temp_path.unlink()
                        logger.info(f"Embedded {len(chapters)} chapters in {output_path}")
                    else:
                        # Fall back to unchaptered version
                        temp_path.rename(output_path)
                        logger.warning(f"Chapter embedding failed, exported without chapters")
                except Exception as e:
                    temp_path.rename(output_path)
                    logger.warning(f"Chapter embedding failed: {e}")
            else:
                temp_path.rename(output_path)
        else:
            audio.export(str(output_path), format=format)

        # Export external chapter files
        if export_chapter_files and chapters and len(chapters) > 0:
            self._export_chapter_files(output_path, chapters)

        logger.info(f"Episode exported: {output_path}")
        return str(output_path)

    def _export_chapter_files(
        self,
        audio_path: Path,
        chapters: ChapterList,
    ) -> None:
        """Export chapter markers to external files.

        Creates companion files for podcast hosting platforms:
        - .chapters.json - Machine-readable format
        - .chapters.txt - Podlove Simple Chapters format
        - .chapters.vtt - WebVTT for HTML5 players

        Args:
            audio_path: Path to the audio file
            chapters: ChapterList to export
        """
        base_path = audio_path.with_suffix("")

        # Export JSON
        json_path = str(base_path) + ".chapters.json"
        try:
            export_chapters_json(chapters, json_path)
        except Exception as e:
            logger.warning(f"Failed to export JSON chapters: {e}")

        # Export Podlove Simple Chapters
        podlove_path = str(base_path) + ".chapters.txt"
        try:
            export_chapters_podlove(chapters, podlove_path)
        except Exception as e:
            logger.warning(f"Failed to export Podlove chapters: {e}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def assemble_episode_from_script(
    script: DialogueScript,
    elevenlabs_client: Optional[Any] = None,
    episode_number: int = 1,
    output_path: Optional[str] = None,
) -> Union[AudioSegment, str]:
    """Convenience function to assemble and optionally export an episode.

    Args:
        script: DialogueScript to assemble
        elevenlabs_client: Optional ElevenLabs client
        episode_number: Episode number
        output_path: Optional path to export to

    Returns:
        AudioSegment if no output_path, else path to exported file
    """
    assembler = EpisodeAudioAssembler(elevenlabs_client=elevenlabs_client)
    audio = await assembler.assemble_episode(script, episode_number)

    if output_path:
        return assembler.export_episode(audio, output_path)

    return audio


def create_test_audio(duration_s: float = 10.0) -> AudioSegment:
    """Create test audio with tones for debugging.

    Args:
        duration_s: Duration in seconds

    Returns:
        AudioSegment with test tones
    """
    from pydub.generators import Sine

    # Create a simple sine wave
    tone = Sine(440).to_audio_segment(duration=int(duration_s * 1000))
    tone = tone - 20  # Reduce volume

    return tone
