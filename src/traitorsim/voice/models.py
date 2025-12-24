"""Core data models for TraitorSim voice generation.

This module defines the foundational data structures used throughout
the voice pipeline, from script extraction to audio assembly.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json


class SegmentType(str, Enum):
    """Type of dialogue segment."""
    NARRATION = "narration"          # Narrator/host commentary
    DIALOGUE = "dialogue"             # Character speaking
    CONFESSIONAL = "confessional"     # Private camera confessional
    WHISPER = "whisper"               # Traitor meetings
    REACTION = "reaction"             # Brief reaction to event
    INTERNAL = "internal"             # Inner monologue (voiceover)


class EmotionIntensity(str, Enum):
    """Intensity level for emotional delivery."""
    SUBTLE = "subtle"          # 0.3x normal expression
    NORMAL = "normal"          # Standard delivery
    HEIGHTENED = "heightened"  # 1.5x expression
    EXTREME = "extreme"        # 2x expression (rare moments)


@dataclass
class VoiceConfig:
    """Configuration for a character's voice in ElevenLabs.

    Maps personality traits and archetype to voice synthesis parameters.
    """
    voice_id: str                              # ElevenLabs voice identifier
    stability: float = 0.5                     # 0.0-1.0, lower = more expressive
    similarity_boost: float = 0.75             # 0.0-1.0, voice clarity
    style: float = 0.5                         # 0.0-1.0, style exaggeration
    use_speaker_boost: bool = True             # Enhanced clarity

    # Metadata for selection
    gender: str = "female"                     # male/female/non-binary
    age_range: str = "adult"                   # young/adult/middle-aged/elderly
    accent: str = "neutral_british"            # Accent hint

    # Dynamic modifiers based on game state
    stress_modifier: float = 0.0               # Applied to stability

    def get_adjusted_stability(self) -> float:
        """Get stability adjusted for current stress level."""
        # Higher stress = lower stability (more variation)
        adjusted = self.stability - (self.stress_modifier * 0.2)
        return max(0.1, min(0.9, adjusted))

    def to_api_params(self) -> Dict[str, Any]:
        """Convert to ElevenLabs API parameters."""
        return {
            "voice_id": self.voice_id,
            "voice_settings": {
                "stability": self.get_adjusted_stability(),
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost,
            }
        }


@dataclass
class DialogueSegment:
    """A single piece of voiced content in the script.

    Represents one speaker's turn, including all metadata needed
    for voice synthesis and audio assembly.
    """
    speaker_id: str                            # player_id or "narrator"
    voice_id: str                              # ElevenLabs voice ID
    text: str                                  # The actual dialogue content
    emotion_tags: List[str] = field(default_factory=list)  # e.g., ["nervous", "defensive"]

    # Segment classification
    segment_type: SegmentType = SegmentType.DIALOGUE
    intensity: EmotionIntensity = EmotionIntensity.NORMAL

    # Production elements
    music_cue: Optional[str] = None            # e.g., "tension_build", "murder_reveal"
    sfx: Optional[str] = None                  # e.g., "door_slam", "gasp_collective"
    sfx_timing: str = "before"                 # before, during, after

    # Game context
    phase: Optional[str] = None                # breakfast, mission, roundtable, turret
    day: Optional[int] = None
    event_type: Optional[str] = None           # MURDER, BANISHMENT, VOTE, etc.

    # Timing control
    pause_before_ms: int = 0                   # Silence before segment
    pause_after_ms: int = 500                  # Silence after segment (default 0.5s)

    # Reference data
    related_player_ids: List[str] = field(default_factory=list)  # For context
    source_event_index: Optional[int] = None   # Index in GameState.events

    def to_tagged_text(self) -> str:
        """Format text with emotion tags for ElevenLabs.

        Returns:
            Text with inline emotion tags, e.g., "[nervous][defensive] I didn't do it!"
        """
        if not self.emotion_tags:
            return self.text
        tags = "".join([f"[{tag}]" for tag in self.emotion_tags])
        return f"{tags} {self.text}"

    def estimate_duration_seconds(self) -> float:
        """Estimate spoken duration based on character count.

        Uses average speaking rate of ~150 words/min = ~750 chars/min.

        Returns:
            Estimated duration in seconds including pauses
        """
        chars = len(self.text)
        speech_time = (chars / 750) * 60  # Convert to seconds
        pause_time = (self.pause_before_ms + self.pause_after_ms) / 1000
        return speech_time + pause_time

    def estimate_credits(self, model: str = "eleven_v3") -> int:
        """Estimate ElevenLabs credits for this segment.

        Args:
            model: ElevenLabs model (eleven_v3 = 1 credit/char, flash = 0.5)

        Returns:
            Credit cost estimate
        """
        chars = len(self.to_tagged_text())
        if model in ("eleven_flash_v2_5", "flash"):
            return int(chars * 0.5)
        return chars  # v3 = 1 credit/char

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "speaker_id": self.speaker_id,
            "voice_id": self.voice_id,
            "text": self.text,
            "tagged_text": self.to_tagged_text(),
            "emotion_tags": self.emotion_tags,
            "segment_type": self.segment_type.value,
            "intensity": self.intensity.value,
            "music_cue": self.music_cue,
            "sfx": self.sfx,
            "sfx_timing": self.sfx_timing,
            "phase": self.phase,
            "day": self.day,
            "event_type": self.event_type,
            "pause_before_ms": self.pause_before_ms,
            "pause_after_ms": self.pause_after_ms,
            "estimated_duration_s": round(self.estimate_duration_seconds(), 2),
            "estimated_credits": self.estimate_credits(),
        }


@dataclass
class DialogueScript:
    """Container for multiple segments forming a scene or episode.

    Provides utilities for batch processing, grouping, and export.
    """
    title: str = ""
    segments: List[DialogueSegment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_segment(self, segment: DialogueSegment) -> None:
        """Add a segment to the script."""
        self.segments.append(segment)

    def add_narrator(
        self,
        text: str,
        emotion: str = "dramatic",
        music_cue: Optional[str] = None,
        sfx: Optional[str] = None,
        pause_before_ms: int = 0,
        pause_after_ms: int = 800,
        **kwargs
    ) -> DialogueSegment:
        """Convenience method for adding narrator segments.

        Args:
            text: Narrator dialogue
            emotion: Single emotion tag (default: dramatic)
            music_cue: Optional music cue
            sfx: Optional sound effect
            pause_before_ms: Silence before (default: 0)
            pause_after_ms: Silence after (default: 800ms for dramatic pacing)
            **kwargs: Additional DialogueSegment parameters

        Returns:
            The created DialogueSegment
        """
        from .voice_library import NARRATOR_VOICE_ID

        segment = DialogueSegment(
            speaker_id="narrator",
            voice_id=NARRATOR_VOICE_ID,
            text=text,
            emotion_tags=[emotion] if emotion else [],
            segment_type=SegmentType.NARRATION,
            music_cue=music_cue,
            sfx=sfx,
            pause_before_ms=pause_before_ms,
            pause_after_ms=pause_after_ms,
            **kwargs
        )
        self.segments.append(segment)
        return segment

    def add_character(
        self,
        speaker_id: str,
        voice_id: str,
        text: str,
        emotions: List[str],
        segment_type: SegmentType = SegmentType.DIALOGUE,
        **kwargs
    ) -> DialogueSegment:
        """Convenience method for adding character dialogue.

        Args:
            speaker_id: Player ID
            voice_id: ElevenLabs voice ID
            text: Dialogue content
            emotions: List of emotion tags
            segment_type: Type of segment
            **kwargs: Additional parameters

        Returns:
            The created DialogueSegment
        """
        segment = DialogueSegment(
            speaker_id=speaker_id,
            voice_id=voice_id,
            text=text,
            emotion_tags=emotions,
            segment_type=segment_type,
            **kwargs
        )
        self.segments.append(segment)
        return segment

    def group_by_speaker(self) -> Dict[str, List[DialogueSegment]]:
        """Group segments by speaker for batch TTS processing.

        Returns:
            Dict mapping speaker_id to list of their segments
        """
        groups: Dict[str, List[DialogueSegment]] = {}
        for seg in self.segments:
            if seg.speaker_id not in groups:
                groups[seg.speaker_id] = []
            groups[seg.speaker_id].append(seg)
        return groups

    def group_by_phase(self) -> Dict[str, List[DialogueSegment]]:
        """Group segments by game phase.

        Returns:
            Dict mapping phase name to list of segments
        """
        groups: Dict[str, List[DialogueSegment]] = {}
        for seg in self.segments:
            phase = seg.phase or "unknown"
            if phase not in groups:
                groups[phase] = []
            groups[phase].append(seg)
        return groups

    def get_speakers(self) -> List[str]:
        """Get unique speaker IDs in order of appearance."""
        seen = set()
        speakers = []
        for seg in self.segments:
            if seg.speaker_id not in seen:
                seen.add(seg.speaker_id)
                speakers.append(seg.speaker_id)
        return speakers

    def estimate_duration_seconds(self) -> float:
        """Estimate total audio duration.

        Returns:
            Total duration in seconds
        """
        return sum(seg.estimate_duration_seconds() for seg in self.segments)

    def estimate_duration_formatted(self) -> str:
        """Get formatted duration string (MM:SS).

        Returns:
            Duration string like "14:32"
        """
        total_seconds = int(self.estimate_duration_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def estimate_credits(self, model: str = "eleven_v3") -> int:
        """Estimate total ElevenLabs credits needed.

        Args:
            model: ElevenLabs model name

        Returns:
            Total credit cost estimate
        """
        return sum(seg.estimate_credits(model) for seg in self.segments)

    def estimate_character_count(self) -> int:
        """Get total character count (for cost estimation)."""
        return sum(len(seg.to_tagged_text()) for seg in self.segments)

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON for API or storage.

        Args:
            indent: JSON indentation (default: 2)

        Returns:
            JSON string representation
        """
        return json.dumps({
            "title": self.title,
            "metadata": self.metadata,
            "summary": {
                "segment_count": len(self.segments),
                "speaker_count": len(self.get_speakers()),
                "speakers": self.get_speakers(),
                "estimated_duration": self.estimate_duration_formatted(),
                "estimated_credits_v3": self.estimate_credits("eleven_v3"),
                "estimated_credits_flash": self.estimate_credits("flash"),
                "character_count": self.estimate_character_count(),
            },
            "segments": [seg.to_dict() for seg in self.segments]
        }, indent=indent)

    def to_elevenlabs_format(self) -> List[Dict[str, Any]]:
        """Convert to ElevenLabs Text-to-Dialogue API format.

        Returns:
            List of dicts ready for ElevenLabs API
        """
        return [
            {
                "voice_id": seg.voice_id,
                "text": seg.to_tagged_text(),
            }
            for seg in self.segments
        ]

    @classmethod
    def from_json(cls, json_str: str) -> "DialogueScript":
        """Create DialogueScript from JSON string.

        Args:
            json_str: JSON representation

        Returns:
            DialogueScript instance
        """
        data = json.loads(json_str)
        script = cls(
            title=data.get("title", ""),
            metadata=data.get("metadata", {})
        )

        for seg_data in data.get("segments", []):
            segment = DialogueSegment(
                speaker_id=seg_data["speaker_id"],
                voice_id=seg_data["voice_id"],
                text=seg_data["text"],
                emotion_tags=seg_data.get("emotion_tags", []),
                segment_type=SegmentType(seg_data.get("segment_type", "dialogue")),
                intensity=EmotionIntensity(seg_data.get("intensity", "normal")),
                music_cue=seg_data.get("music_cue"),
                sfx=seg_data.get("sfx"),
                sfx_timing=seg_data.get("sfx_timing", "before"),
                phase=seg_data.get("phase"),
                day=seg_data.get("day"),
                event_type=seg_data.get("event_type"),
                pause_before_ms=seg_data.get("pause_before_ms", 0),
                pause_after_ms=seg_data.get("pause_after_ms", 500),
            )
            script.add_segment(segment)

        return script


@dataclass
class EpisodeScript:
    """Complete episode script with multiple scenes.

    An episode typically covers one game day with all phases.
    """
    episode_number: int
    day: int
    title: str = ""

    # Scene scripts in order
    cold_open: Optional[DialogueScript] = None        # Recap/cliffhanger
    breakfast: Optional[DialogueScript] = None        # Murder reveal
    mission: Optional[DialogueScript] = None          # Challenge
    social: Optional[DialogueScript] = None           # Alliance building
    roundtable: Optional[DialogueScript] = None       # Voting
    turret: Optional[DialogueScript] = None           # Traitor meeting
    preview: Optional[DialogueScript] = None          # Next episode tease

    # Episode metadata
    eliminated_player_id: Optional[str] = None        # Banished this episode
    murdered_player_id: Optional[str] = None          # Murdered this episode
    key_moments: List[str] = field(default_factory=list)  # Highlight descriptions

    def get_all_segments(self) -> List[DialogueSegment]:
        """Get all segments across all scenes in order."""
        all_segments = []
        for scene in [
            self.cold_open, self.breakfast, self.mission,
            self.social, self.roundtable, self.turret, self.preview
        ]:
            if scene:
                all_segments.extend(scene.segments)
        return all_segments

    def estimate_duration_formatted(self) -> str:
        """Get total episode duration."""
        total = sum(
            scene.estimate_duration_seconds()
            for scene in [
                self.cold_open, self.breakfast, self.mission,
                self.social, self.roundtable, self.turret, self.preview
            ]
            if scene
        )
        minutes = int(total) // 60
        seconds = int(total) % 60
        return f"{minutes}:{seconds:02d}"

    def estimate_credits(self, model: str = "eleven_v3") -> int:
        """Get total credit cost for episode."""
        return sum(
            scene.estimate_credits(model)
            for scene in [
                self.cold_open, self.breakfast, self.mission,
                self.social, self.roundtable, self.turret, self.preview
            ]
            if scene
        )

    def to_json(self, indent: int = 2) -> str:
        """Export episode as JSON."""
        return json.dumps({
            "episode_number": self.episode_number,
            "day": self.day,
            "title": self.title,
            "eliminated_player_id": self.eliminated_player_id,
            "murdered_player_id": self.murdered_player_id,
            "key_moments": self.key_moments,
            "summary": {
                "duration": self.estimate_duration_formatted(),
                "credits_v3": self.estimate_credits("eleven_v3"),
                "credits_flash": self.estimate_credits("flash"),
                "segment_count": len(self.get_all_segments()),
            },
            "scenes": {
                "cold_open": json.loads(self.cold_open.to_json()) if self.cold_open else None,
                "breakfast": json.loads(self.breakfast.to_json()) if self.breakfast else None,
                "mission": json.loads(self.mission.to_json()) if self.mission else None,
                "social": json.loads(self.social.to_json()) if self.social else None,
                "roundtable": json.loads(self.roundtable.to_json()) if self.roundtable else None,
                "turret": json.loads(self.turret.to_json()) if self.turret else None,
                "preview": json.loads(self.preview.to_json()) if self.preview else None,
            }
        }, indent=indent)


# Type alias for easier imports
Script = Union[DialogueScript, EpisodeScript]
