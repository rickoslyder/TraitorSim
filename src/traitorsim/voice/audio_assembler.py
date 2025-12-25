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

from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

from .models import DialogueScript, DialogueSegment, SegmentType

logger = logging.getLogger(__name__)


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
        """Apply volume ducking during voice regions.

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
    ):
        """Initialize episode assembler.

        Args:
            elevenlabs_client: ElevenLabs client for voice synthesis
            music_library: Background music library
            sfx_library: Sound effects library
            output_format: Output audio format
            output_bitrate: Output bitrate for MP3
        """
        self.client = elevenlabs_client
        self.music_library = music_library or MusicLibrary()
        self.sfx_library = sfx_library or SFXLibrary()
        self.output_format = output_format
        self.output_bitrate = output_bitrate

        # Timing configuration
        self.segment_gap_ms = 500       # Gap between dialogue segments
        self.phase_transition_ms = 2000  # Transition between phases
        self.intro_music_ms = 5000       # Intro music before content
        self.outro_music_ms = 3000       # Outro music after content

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

        # Mix everything
        mixed = timeline.mix(normalize_output=True)

        logger.info(f"Episode {episode_number} assembled: {len(mixed) / 1000:.1f}s")

        return mixed

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
    ) -> str:
        """Export episode audio to file.

        Args:
            audio: Episode AudioSegment
            output_path: Output file path
            format: Override output format

        Returns:
            Path to exported file
        """
        format = format or self.output_format
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Export with appropriate settings
        if format == "mp3":
            audio.export(
                str(output_path),
                format="mp3",
                bitrate=self.output_bitrate,
                tags={
                    "artist": "TraitorSim",
                    "album": "The Traitors AI Simulation",
                }
            )
        else:
            audio.export(str(output_path), format=format)

        logger.info(f"Episode exported: {output_path}")
        return str(output_path)


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
