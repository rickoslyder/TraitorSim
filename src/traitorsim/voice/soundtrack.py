"""Soundtrack catalog for TraitorSim voice integration.

Defines music cues, sound effects, and ambient sounds for episode generation.
Integrates with audio_assembler.py MusicMood and SFXType enums.

This module provides:
- Music cues for different game phases and moods
- Sound effects for specific events (murders, votes, reveals)
- Ambient soundscapes for atmosphere
- Helper functions to retrieve appropriate audio for context

Usage:
    from traitorsim.voice.soundtrack import (
        get_music_for_phase,
        get_sfx_for_event,
        PHASE_MUSIC,
        EVENT_STINGS,
    )

    # Get music for a game phase
    music = get_music_for_phase("roundtable")

    # Get sound effect for an event
    sfx = get_sfx_for_event("murder_reveal")

    # Get ambient sound for location
    ambient = get_ambient_for_location("castle_turret")

Note:
    File paths are placeholders until actual audio assets are created.
    The catalog uses standard naming conventions that match expected file locations.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, List, Union
from pathlib import Path
from enum import Enum

from .audio_assembler import MusicMood, SFXType

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MusicCue:
    """Configuration for a background music track.

    Attributes:
        file_path: Path to audio file (relative to assets directory)
        duration: Duration in seconds (or "loop" for looping tracks)
        bpm: Beats per minute (for synchronization)
        mood: Emotional mood category
        volume_db: Default volume adjustment in dB (0 = no change)
        fade_in_ms: Default fade-in duration in milliseconds
        fade_out_ms: Default fade-out duration in milliseconds
        description: Human-readable description
    """
    file_path: str
    duration: Union[float, str]  # seconds or "loop"
    bpm: int
    mood: str
    volume_db: float = -12.0
    fade_in_ms: int = 1000
    fade_out_ms: int = 2000
    description: str = ""

    @property
    def is_looping(self) -> bool:
        """Check if this is a looping track."""
        return self.duration == "loop"

    @property
    def duration_ms(self) -> Optional[int]:
        """Get duration in milliseconds (None if looping)."""
        if self.is_looping:
            return None
        return int(float(self.duration) * 1000)


@dataclass
class SFXCue:
    """Configuration for a sound effect.

    Attributes:
        file_path: Path to audio file (relative to assets directory)
        duration: Duration in seconds
        mood: Emotional impact category
        volume_db: Default volume adjustment in dB
        fade_in_ms: Fade-in duration in milliseconds (usually 0 for SFX)
        fade_out_ms: Fade-out duration in milliseconds
        description: Human-readable description
        loop: Whether this SFX should loop (for ambient sounds)
    """
    file_path: str
    duration: float  # seconds
    mood: str
    volume_db: float = 0.0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    description: str = ""
    loop: bool = False

    @property
    def duration_ms(self) -> int:
        """Get duration in milliseconds."""
        return int(self.duration * 1000)


# =============================================================================
# PHASE-SPECIFIC MUSIC CATALOG
# =============================================================================

PHASE_MUSIC: Dict[str, MusicCue] = {
    # Breakfast phase - Uneasy morning atmosphere
    "breakfast_tension": MusicCue(
        file_path="assets/music/breakfast_uneasy.mp3",
        duration="loop",
        bpm=70,
        mood="uneasy_anticipation",
        volume_db=-15.0,
        fade_in_ms=1500,
        fade_out_ms=2000,
        description="Sparse strings with subtle tension. Uneasy morning atmosphere before murder reveal.",
    ),

    # Mission phase - Competitive energy
    "mission_energy": MusicCue(
        file_path="assets/music/mission_pulse.mp3",
        duration="loop",
        bpm=120,
        mood="competitive_urgency",
        volume_db=-12.0,
        fade_in_ms=500,
        fade_out_ms=1000,
        description="Driving percussion with urgent synth. Competitive challenge atmosphere.",
    ),

    # Social phase - Whispered secrets
    "social_intrigue": MusicCue(
        file_path="assets/music/social_whispers.mp3",
        duration="loop",
        bpm=80,
        mood="whispered_secrets",
        volume_db=-16.0,
        fade_in_ms=2000,
        fade_out_ms=2000,
        description="Quiet piano with subtle electronic textures. Private conversations and scheming.",
    ),

    # Round Table - Building suspicion
    "roundtable_deliberation": MusicCue(
        file_path="assets/music/roundtable_suspicion.mp3",
        duration="loop",
        bpm=60,
        mood="suspicion_brewing",
        volume_db=-14.0,
        fade_in_ms=1000,
        fade_out_ms=2500,
        description="Dark strings with slow build. Accusation and defense tension.",
    ),

    # Turret phase - Cold calculation
    "turret_sinister": MusicCue(
        file_path="assets/music/turret_darkness.mp3",
        duration="loop",
        bpm=50,
        mood="cold_calculation",
        volume_db=-10.0,
        fade_in_ms=2000,
        fade_out_ms=1500,
        description="Low drones with metallic textures. Traitor murder deliberation.",
    ),

    # Finale - Climactic tension
    "finale_crescendo": MusicCue(
        file_path="assets/music/finale_climax.mp3",
        duration=90.0,
        bpm=90,
        mood="climactic_tension",
        volume_db=-8.0,
        fade_in_ms=2000,
        fade_out_ms=3000,
        description="Full orchestral build to climax. Final confrontations and reveals.",
    ),

    # Additional moods (matching audio_assembler.py MusicMood enum)
    "tension_general": MusicCue(
        file_path="assets/music/tension_build.mp3",
        duration="loop",
        bpm=80,
        mood="tension",
        volume_db=-12.0,
        fade_in_ms=1000,
        fade_out_ms=1500,
        description="General tension and suspense. Multi-purpose background.",
    ),

    "dramatic_reveal": MusicCue(
        file_path="assets/music/dramatic_hit.mp3",
        duration=15.0,
        bpm=100,
        mood="dramatic",
        volume_db=-6.0,
        fade_in_ms=0,
        fade_out_ms=1000,
        description="Dramatic orchestral hit for major reveals.",
    ),

    "somber_loss": MusicCue(
        file_path="assets/music/somber_reflection.mp3",
        duration=60.0,
        bpm=60,
        mood="somber",
        volume_db=-14.0,
        fade_in_ms=2000,
        fade_out_ms=3000,
        description="Sad reflective piano. Loss and tragedy.",
    ),

    "mysterious_scheming": MusicCue(
        file_path="assets/music/mysterious_shadows.mp3",
        duration="loop",
        bpm=70,
        mood="mysterious",
        volume_db=-13.0,
        fade_in_ms=1500,
        fade_out_ms=2000,
        description="Dark ambient with sneaky undertones. Mystery and scheming.",
    ),

    "triumphant_victory": MusicCue(
        file_path="assets/music/triumphant_brass.mp3",
        duration=45.0,
        bpm=120,
        mood="triumphant",
        volume_db=-8.0,
        fade_in_ms=500,
        fade_out_ms=2000,
        description="Victorious brass and percussion. Success and celebration.",
    ),

    "neutral_underscore": MusicCue(
        file_path="assets/music/neutral_background.mp3",
        duration="loop",
        bpm=90,
        mood="neutral",
        volume_db=-16.0,
        fade_in_ms=2000,
        fade_out_ms=2000,
        description="Neutral background music for general scenes.",
    ),
}


# =============================================================================
# EVENT-SPECIFIC SOUND EFFECTS CATALOG
# =============================================================================

EVENT_STINGS: Dict[str, SFXCue] = {
    # Murder reveal - Shock and dread
    "murder_reveal": SFXCue(
        file_path="assets/sfx/murder_reveal_sting.mp3",
        duration=3.5,
        mood="shock",
        volume_db=-3.0,
        fade_in_ms=0,
        fade_out_ms=500,
        description="Dark orchestral sting with impact. Murder victim announcement.",
    ),

    # Banishment vote - Tension peak
    "banishment_vote": SFXCue(
        file_path="assets/sfx/vote_drumroll.mp3",
        duration=5.0,
        mood="tension_peak",
        volume_db=-6.0,
        fade_in_ms=100,
        fade_out_ms=300,
        description="Building drumroll leading to reveal. Vote count tension.",
    ),

    # Role reveal - Traitor caught
    "role_reveal_traitor": SFXCue(
        file_path="assets/sfx/traitor_reveal_triumph.mp3",
        duration=4.0,
        mood="triumphant_justice",
        volume_db=-4.0,
        fade_in_ms=0,
        fade_out_ms=800,
        description="Triumphant chord progression. Traitor successfully banished.",
    ),

    # Role reveal - Faithful mistake
    "role_reveal_faithful": SFXCue(
        file_path="assets/sfx/faithful_reveal_tragic.mp3",
        duration=4.0,
        mood="tragic_mistake",
        volume_db=-4.0,
        fade_in_ms=0,
        fade_out_ms=1000,
        description="Somber strings with descending progression. Faithful wrongly banished.",
    ),

    # Recruitment offer - Sinister opportunity
    "recruitment_offer": SFXCue(
        file_path="assets/sfx/recruitment_sinister.mp3",
        duration=3.0,
        mood="sinister_opportunity",
        volume_db=-5.0,
        fade_in_ms=200,
        fade_out_ms=800,
        description="Dark whispered tones with subtle choir. Traitor recruitment.",
    ),

    # Mission success - Celebration
    "mission_success": SFXCue(
        file_path="assets/sfx/mission_success_cheer.mp3",
        duration=2.5,
        mood="celebration",
        volume_db=-8.0,
        fade_in_ms=0,
        fade_out_ms=500,
        description="Bright major chord with subtle crowd cheer. Mission completed successfully.",
    ),

    # Mission failure - Disappointment
    "mission_fail": SFXCue(
        file_path="assets/sfx/mission_fail_disappointment.mp3",
        duration=2.5,
        mood="disappointment",
        volume_db=-6.0,
        fade_in_ms=0,
        fade_out_ms=600,
        description="Descending tones with sighs. Mission sabotaged or failed.",
    ),

    # Vote cast confirmation
    "vote_cast": SFXCue(
        file_path="assets/sfx/vote_cast_confirm.mp3",
        duration=1.0,
        mood="confirmation",
        volume_db=-10.0,
        fade_in_ms=0,
        fade_out_ms=100,
        description="Subtle confirmation tone. Individual vote registered.",
    ),

    # Clock tick - Tension builder
    "clock_tick": SFXCue(
        file_path="assets/sfx/clock_tick_tension.mp3",
        duration=0.5,
        mood="tension",
        volume_db=-12.0,
        fade_in_ms=0,
        fade_out_ms=0,
        description="Single clock tick. Can be repeated for building tension.",
    ),

    # Shield activation
    "shield_activate": SFXCue(
        file_path="assets/sfx/shield_protect.mp3",
        duration=2.0,
        mood="protection",
        volume_db=-6.0,
        fade_in_ms=50,
        fade_out_ms=400,
        description="Magical shield sound. Shield protection activated.",
    ),

    # Dramatic pause/reveal
    "dramatic_pause": SFXCue(
        file_path="assets/sfx/dramatic_pause_whoosh.mp3",
        duration=1.5,
        mood="anticipation",
        volume_db=-8.0,
        fade_in_ms=0,
        fade_out_ms=300,
        description="Whoosh with reverb tail. Pause before major reveal.",
    ),

    # Gavel strike (vote conclusion)
    "gavel_strike": SFXCue(
        file_path="assets/sfx/gavel_final.mp3",
        duration=0.8,
        mood="finality",
        volume_db=-4.0,
        fade_in_ms=0,
        fade_out_ms=200,
        description="Wooden gavel strike. Decision finalized.",
    ),

    # Heartbeat (extreme tension)
    "heartbeat_anxiety": SFXCue(
        file_path="assets/sfx/heartbeat_intense.mp3",
        duration=2.0,
        mood="anxiety",
        volume_db=-8.0,
        fade_in_ms=100,
        fade_out_ms=500,
        description="Amplified heartbeat. Extreme anxiety and fear.",
    ),

    # Whisper ambience
    "whisper_conspiracy": SFXCue(
        file_path="assets/sfx/whisper_voices.mp3",
        duration=3.0,
        mood="conspiracy",
        volume_db=-15.0,
        fade_in_ms=500,
        fade_out_ms=500,
        description="Layered whispers. Conspiracy and secrets.",
    ),
}


# =============================================================================
# AMBIENT SOUNDS CATALOG
# =============================================================================

AMBIENT_SOUNDS: Dict[str, SFXCue] = {
    # Castle general ambience
    "castle_ambience": SFXCue(
        file_path="assets/ambient/castle_atmosphere.mp3",
        duration=120.0,  # 2 minute loop
        mood="atmospheric",
        volume_db=-20.0,
        fade_in_ms=3000,
        fade_out_ms=3000,
        description="General castle atmosphere. Distant echoes, stone reverb.",
        loop=True,
    ),

    # Fireplace crackling
    "fire_crackling": SFXCue(
        file_path="assets/ambient/fireplace_crackle.mp3",
        duration=60.0,
        mood="warm",
        volume_db=-18.0,
        fade_in_ms=2000,
        fade_out_ms=2000,
        description="Fireplace crackling. Warm social gathering atmosphere.",
        loop=True,
    ),

    # Wind howling (exterior/turret)
    "wind_howling": SFXCue(
        file_path="assets/ambient/wind_howl_cold.mp3",
        duration=90.0,
        mood="cold_isolation",
        volume_db=-16.0,
        fade_in_ms=2500,
        fade_out_ms=2500,
        description="Cold wind howling. Exterior scenes and turret isolation.",
        loop=True,
    ),

    # Clock ticking (background tension)
    "clock_ticking": SFXCue(
        file_path="assets/ambient/clock_tick_loop.mp3",
        duration=60.0,
        mood="time_pressure",
        volume_db=-22.0,
        fade_in_ms=1000,
        fade_out_ms=1000,
        description="Steady clock ticking. Subtle time pressure and tension.",
        loop=True,
    ),

    # Night crickets (outdoor scenes)
    "night_crickets": SFXCue(
        file_path="assets/ambient/night_crickets.mp3",
        duration=120.0,
        mood="nighttime",
        volume_db=-19.0,
        fade_in_ms=3000,
        fade_out_ms=3000,
        description="Cricket and night sounds. Outdoor nighttime scenes.",
        loop=True,
    ),

    # Turret dungeon ambience
    "turret_chamber": SFXCue(
        file_path="assets/ambient/turret_dungeon.mp3",
        duration=90.0,
        mood="sinister",
        volume_db=-17.0,
        fade_in_ms=2000,
        fade_out_ms=2000,
        description="Dark chamber ambience. Stone echo, dripping water. Turret meetings.",
        loop=True,
    ),

    # Round Table room tone
    "roundtable_room": SFXCue(
        file_path="assets/ambient/roundtable_room_tone.mp3",
        duration=120.0,
        mood="formal",
        volume_db=-21.0,
        fade_in_ms=2000,
        fade_out_ms=2000,
        description="Formal room tone. Subtle reverb for Round Table deliberations.",
        loop=True,
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_music_for_phase(phase: str) -> Optional[MusicCue]:
    """Get appropriate music cue for a game phase.

    Maps game phase names to music cues. Handles variations in naming.

    Args:
        phase: Game phase name (e.g., "roundtable", "STATE_ROUNDTABLE", "Round Table")

    Returns:
        MusicCue if found, None otherwise

    Examples:
        >>> music = get_music_for_phase("roundtable")
        >>> music = get_music_for_phase("STATE_BREAKFAST")
        >>> music = get_music_for_phase("Mission")
    """
    # Normalize phase name
    phase_normalized = phase.lower().replace("state_", "").replace(" ", "_")

    # Map normalized phase to music cue key
    phase_to_music = {
        "breakfast": "breakfast_tension",
        "mission": "mission_energy",
        "social": "social_intrigue",
        "roundtable": "roundtable_deliberation",
        "round_table": "roundtable_deliberation",
        "turret": "turret_sinister",
        "finale": "finale_crescendo",
    }

    music_key = phase_to_music.get(phase_normalized)
    if music_key:
        return PHASE_MUSIC.get(music_key)

    logger.warning(f"No music mapping found for phase: {phase}")
    return None


def get_sfx_for_event(event_type: str) -> Optional[SFXCue]:
    """Get sound effect for a specific event type.

    Maps event types to SFX cues. Handles variations in naming.

    Args:
        event_type: Event type (e.g., "murder_reveal", "MURDER", "Vote Tally")

    Returns:
        SFXCue if found, None otherwise

    Examples:
        >>> sfx = get_sfx_for_event("murder_reveal")
        >>> sfx = get_sfx_for_event("BANISHMENT")
        >>> sfx = get_sfx_for_event("vote_cast")
    """
    # Normalize event type
    event_normalized = event_type.lower().replace(" ", "_")

    # Direct lookup
    if event_normalized in EVENT_STINGS:
        return EVENT_STINGS[event_normalized]

    # Map common event types to SFX
    event_to_sfx = {
        "murder": "murder_reveal",
        "banishment": "banishment_vote",
        "vote_tally": "banishment_vote",
        "traitor_reveal": "role_reveal_traitor",
        "faithful_reveal": "role_reveal_faithful",
        "role_reveal": "dramatic_pause",  # Generic reveal
        "recruitment": "recruitment_offer",
        "mission_success": "mission_success",
        "mission_complete": "mission_success",
        "mission_fail": "mission_fail",
        "mission_failed": "mission_fail",
        "vote": "vote_cast",
        "shield": "shield_activate",
        "shield_block": "shield_activate",
    }

    sfx_key = event_to_sfx.get(event_normalized)
    if sfx_key:
        return EVENT_STINGS.get(sfx_key)

    logger.debug(f"No SFX mapping found for event: {event_type}")
    return None


def get_ambient_for_location(location: str) -> Optional[SFXCue]:
    """Get ambient sound for a location.

    Maps location names to ambient sound cues.

    Args:
        location: Location name (e.g., "castle", "turret", "outdoor")

    Returns:
        SFXCue if found, None otherwise

    Examples:
        >>> ambient = get_ambient_for_location("castle")
        >>> ambient = get_ambient_for_location("turret_chamber")
        >>> ambient = get_ambient_for_location("fireplace")
    """
    # Normalize location
    location_normalized = location.lower().replace(" ", "_")

    # Direct lookup
    if location_normalized in AMBIENT_SOUNDS:
        return AMBIENT_SOUNDS[location_normalized]

    # Map location keywords to ambience
    location_keywords = {
        "castle": "castle_ambience",
        "main_hall": "castle_ambience",
        "hall": "castle_ambience",
        "fire": "fire_crackling",
        "fireplace": "fire_crackling",
        "hearth": "fire_crackling",
        "turret": "turret_chamber",
        "dungeon": "turret_chamber",
        "chamber": "turret_chamber",
        "wind": "wind_howling",
        "exterior": "wind_howling",
        "outside": "wind_howling",
        "clock": "clock_ticking",
        "night": "night_crickets",
        "outdoor": "night_crickets",
        "roundtable": "roundtable_room",
        "round_table": "roundtable_room",
        "meeting": "roundtable_room",
    }

    for keyword, ambient_key in location_keywords.items():
        if keyword in location_normalized:
            return AMBIENT_SOUNDS.get(ambient_key)

    logger.debug(f"No ambient sound mapping found for location: {location}")
    return None


def map_music_mood_to_cue(mood: MusicMood) -> Optional[MusicCue]:
    """Map audio_assembler.py MusicMood enum to specific music cue.

    Bridges the gap between the MusicMood enum and the detailed music catalog.

    Args:
        mood: MusicMood enum value

    Returns:
        Corresponding MusicCue if found, None otherwise

    Examples:
        >>> from traitorsim.voice.audio_assembler import MusicMood
        >>> cue = map_music_mood_to_cue(MusicMood.TENSION)
        >>> cue = map_music_mood_to_cue(MusicMood.ROUNDTABLE)
    """
    mood_to_cue = {
        MusicMood.TENSION: "tension_general",
        MusicMood.DRAMATIC: "dramatic_reveal",
        MusicMood.SOMBER: "somber_loss",
        MusicMood.MYSTERIOUS: "mysterious_scheming",
        MusicMood.TRIUMPHANT: "triumphant_victory",
        MusicMood.NEUTRAL: "neutral_underscore",
        MusicMood.BREAKFAST: "breakfast_tension",
        MusicMood.ROUNDTABLE: "roundtable_deliberation",
    }

    cue_key = mood_to_cue.get(mood)
    if cue_key:
        return PHASE_MUSIC.get(cue_key)

    logger.warning(f"No music cue mapping for MusicMood: {mood}")
    return None


def map_sfx_type_to_cue(sfx_type: SFXType) -> Optional[SFXCue]:
    """Map audio_assembler.py SFXType enum to specific SFX cue.

    Bridges the gap between the SFXType enum and the detailed SFX catalog.

    Args:
        sfx_type: SFXType enum value

    Returns:
        Corresponding SFXCue if found, None otherwise

    Examples:
        >>> from traitorsim.voice.audio_assembler import SFXType
        >>> cue = map_sfx_type_to_cue(SFXType.MURDER_STING)
        >>> cue = map_sfx_type_to_cue(SFXType.GAVEL)
    """
    sfx_to_cue = {
        SFXType.GAVEL: "gavel_strike",
        SFXType.DOOR_CREAK: None,  # Not in EVENT_STINGS, would be in AMBIENT_SOUNDS
        SFXType.CLOCK_TICK: "clock_tick",
        SFXType.HEARTBEAT: "heartbeat_anxiety",
        SFXType.REVEAL_STING: "dramatic_pause",
        SFXType.VOTE_CAST: "vote_cast",
        SFXType.MURDER_STING: "murder_reveal",
        SFXType.SHIELD_BLOCK: "shield_activate",
        SFXType.RECRUITMENT: "recruitment_offer",
        SFXType.WHISPER: "whisper_conspiracy",
    }

    cue_key = sfx_to_cue.get(sfx_type)
    if cue_key:
        return EVENT_STINGS.get(cue_key)

    # Check if it's an ambient sound
    if sfx_type == SFXType.DOOR_CREAK:
        logger.debug(f"SFXType {sfx_type} maps to ambient sound, not event sting")
    else:
        logger.warning(f"No SFX cue mapping for SFXType: {sfx_type}")

    return None


# =============================================================================
# CATALOG UTILITIES
# =============================================================================

def list_all_music_cues() -> List[str]:
    """List all available music cue identifiers.

    Returns:
        Sorted list of music cue keys
    """
    return sorted(PHASE_MUSIC.keys())


def list_all_sfx_cues() -> List[str]:
    """List all available SFX cue identifiers.

    Returns:
        Sorted list of SFX cue keys
    """
    return sorted(EVENT_STINGS.keys())


def list_all_ambient_cues() -> List[str]:
    """List all available ambient sound identifiers.

    Returns:
        Sorted list of ambient cue keys
    """
    return sorted(AMBIENT_SOUNDS.keys())


def get_cue_info(cue_id: str) -> Optional[Dict[str, any]]:
    """Get detailed information about a specific cue.

    Searches all catalogs (music, SFX, ambient) for the cue ID.

    Args:
        cue_id: Cue identifier

    Returns:
        Dictionary with cue information, or None if not found
    """
    # Check music
    if cue_id in PHASE_MUSIC:
        cue = PHASE_MUSIC[cue_id]
        return {
            "type": "music",
            "id": cue_id,
            "cue": cue,
            "file_path": cue.file_path,
            "duration": cue.duration,
            "mood": cue.mood,
            "description": cue.description,
        }

    # Check SFX
    if cue_id in EVENT_STINGS:
        cue = EVENT_STINGS[cue_id]
        return {
            "type": "sfx",
            "id": cue_id,
            "cue": cue,
            "file_path": cue.file_path,
            "duration": cue.duration,
            "mood": cue.mood,
            "description": cue.description,
        }

    # Check ambient
    if cue_id in AMBIENT_SOUNDS:
        cue = AMBIENT_SOUNDS[cue_id]
        return {
            "type": "ambient",
            "id": cue_id,
            "cue": cue,
            "file_path": cue.file_path,
            "duration": cue.duration,
            "mood": cue.mood,
            "description": cue.description,
        }

    return None


def validate_all_cues() -> Dict[str, List[str]]:
    """Validate all cues and return any issues found.

    Checks for:
    - Invalid durations
    - Missing descriptions
    - Invalid BPM values
    - Volume levels outside reasonable range

    Returns:
        Dictionary with "warnings" and "errors" lists
    """
    warnings = []
    errors = []

    # Validate music cues
    for key, cue in PHASE_MUSIC.items():
        if not cue.description:
            warnings.append(f"Music '{key}' missing description")

        if cue.bpm < 30 or cue.bpm > 200:
            warnings.append(f"Music '{key}' has unusual BPM: {cue.bpm}")

        if cue.volume_db > 0:
            warnings.append(f"Music '{key}' has positive volume: {cue.volume_db}dB (may clip)")

        if not isinstance(cue.duration, str) and cue.duration <= 0:
            errors.append(f"Music '{key}' has invalid duration: {cue.duration}")

    # Validate SFX cues
    for key, cue in EVENT_STINGS.items():
        if not cue.description:
            warnings.append(f"SFX '{key}' missing description")

        if cue.duration <= 0:
            errors.append(f"SFX '{key}' has invalid duration: {cue.duration}")

        if cue.volume_db > 6:
            warnings.append(f"SFX '{key}' has high volume: {cue.volume_db}dB (may clip)")

    # Validate ambient sounds
    for key, cue in AMBIENT_SOUNDS.items():
        if not cue.description:
            warnings.append(f"Ambient '{key}' missing description")

        if cue.duration <= 0:
            errors.append(f"Ambient '{key}' has invalid duration: {cue.duration}")

        if not cue.loop:
            warnings.append(f"Ambient '{key}' is not set to loop (unusual for ambient)")

    return {
        "warnings": warnings,
        "errors": errors,
    }


# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

# Log catalog statistics on import
logger.debug(
    f"Soundtrack catalog loaded: "
    f"{len(PHASE_MUSIC)} music cues, "
    f"{len(EVENT_STINGS)} SFX cues, "
    f"{len(AMBIENT_SOUNDS)} ambient sounds"
)
