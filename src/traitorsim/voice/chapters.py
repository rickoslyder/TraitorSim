"""Chapter markers for TraitorSim episode export.

Provides chapter marker support for podcast-style navigation in exported
audio episodes. Chapters allow listeners to jump between game phases
(breakfast, mission, roundtable, etc.) and significant events.

Supported formats:
- MP3 with ID3v2.4 CHAP/CTOC frames (native chapter support)
- M4A with FFmpeg metadata chapters
- External formats: JSON, Podlove Simple Chapters, WebVTT

Usage:
    from traitorsim.voice import (
        ChapterMarker,
        ChapterList,
        embed_chapters,
        export_chapters_json,
    )

    # Create chapters
    chapters = ChapterList()
    chapters.add(ChapterMarker(
        title="Breakfast - Murder Reveal",
        start_ms=45000,
        phase="breakfast",
    ))

    # Embed in audio file
    embed_chapters("episode_03.mp3", chapters)

    # Export for podcast feeds
    export_chapters_json(chapters, "episode_03.chapters.json")
"""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class ChapterType(str, Enum):
    """Types of chapter markers."""
    PHASE = "phase"           # Game phase (breakfast, mission, etc.)
    EVENT = "event"           # Significant event (murder reveal, banishment)
    CONFESSIONAL = "confessional"  # Player confessional segment
    TRANSITION = "transition"  # Scene transition / recap
    INTRO = "intro"           # Episode intro
    OUTRO = "outro"           # Episode outro / preview


@dataclass
class ChapterMarker:
    """A single chapter marker for audio navigation.

    Chapter markers provide navigation points in audio files, allowing
    listeners to jump to specific moments like game phases or events.

    Attributes:
        title: Display title shown in player UI
        start_ms: Start time in milliseconds from beginning of file
        end_ms: End time in milliseconds (auto-calculated if None)
        chapter_type: Type of chapter (phase, event, confessional, etc.)
        phase: Game phase name if applicable
        event_type: Event type if this marks a significant event
        speaker_id: Speaker ID for confessional chapters
        description: Optional longer description
        url: Optional URL for chapter (podcast 2.0 spec)
        image_path: Optional path to chapter artwork
        metadata: Additional metadata for export
    """
    title: str
    start_ms: int
    end_ms: Optional[int] = None
    chapter_type: ChapterType = ChapterType.PHASE
    phase: Optional[str] = None
    event_type: Optional[str] = None
    speaker_id: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    image_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Generate unique chapter ID."""
        return f"chap_{self.start_ms:08d}"

    @property
    def start_seconds(self) -> float:
        """Start time in seconds."""
        return self.start_ms / 1000.0

    @property
    def end_seconds(self) -> Optional[float]:
        """End time in seconds."""
        return self.end_ms / 1000.0 if self.end_ms else None

    @property
    def duration_ms(self) -> Optional[int]:
        """Duration in milliseconds."""
        if self.end_ms:
            return self.end_ms - self.start_ms
        return None

    @property
    def start_timecode(self) -> str:
        """Start time as HH:MM:SS.mmm timecode."""
        return ms_to_timecode(self.start_ms)

    @property
    def end_timecode(self) -> Optional[str]:
        """End time as HH:MM:SS.mmm timecode."""
        return ms_to_timecode(self.end_ms) if self.end_ms else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        result = {
            "id": self.id,
            "title": self.title,
            "start_ms": self.start_ms,
            "start_time": self.start_timecode,
        }

        if self.end_ms:
            result["end_ms"] = self.end_ms
            result["end_time"] = self.end_timecode

        if self.chapter_type != ChapterType.PHASE:
            result["type"] = self.chapter_type.value

        if self.phase:
            result["phase"] = self.phase
        if self.event_type:
            result["event_type"] = self.event_type
        if self.speaker_id:
            result["speaker_id"] = self.speaker_id
        if self.description:
            result["description"] = self.description
        if self.url:
            result["url"] = self.url
        if self.metadata:
            result["metadata"] = self.metadata

        return result


@dataclass
class ChapterList:
    """Collection of chapter markers with manipulation utilities.

    Manages a list of chapters, ensuring they're sorted and have
    proper end times calculated.

    Example:
        chapters = ChapterList()
        chapters.add(ChapterMarker(title="Intro", start_ms=0))
        chapters.add(ChapterMarker(title="Chapter 1", start_ms=30000))
        chapters.finalize(total_duration_ms=300000)
    """
    chapters: List[ChapterMarker] = field(default_factory=list)
    episode_title: Optional[str] = None
    episode_number: Optional[int] = None
    total_duration_ms: Optional[int] = None

    def add(self, chapter: ChapterMarker) -> None:
        """Add a chapter marker."""
        self.chapters.append(chapter)

    def add_phase(
        self,
        phase: str,
        start_ms: int,
        title: Optional[str] = None,
        end_ms: Optional[int] = None,
    ) -> ChapterMarker:
        """Add a phase-based chapter marker.

        Args:
            phase: Game phase name (breakfast, mission, etc.)
            start_ms: Start time
            title: Optional custom title (auto-generated if None)
            end_ms: Optional end time

        Returns:
            The created ChapterMarker
        """
        if title is None:
            title = format_phase_title(phase)

        chapter = ChapterMarker(
            title=title,
            start_ms=start_ms,
            end_ms=end_ms,
            chapter_type=ChapterType.PHASE,
            phase=phase,
        )
        self.add(chapter)
        return chapter

    def add_event(
        self,
        event_type: str,
        start_ms: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        speaker_id: Optional[str] = None,
    ) -> ChapterMarker:
        """Add an event-based chapter marker.

        Args:
            event_type: Type of event (MURDER, BANISHMENT, etc.)
            start_ms: Start time
            title: Optional custom title
            description: Optional description
            speaker_id: Optional speaker for the event

        Returns:
            The created ChapterMarker
        """
        if title is None:
            title = format_event_title(event_type)

        chapter = ChapterMarker(
            title=title,
            start_ms=start_ms,
            chapter_type=ChapterType.EVENT,
            event_type=event_type,
            description=description,
            speaker_id=speaker_id,
        )
        self.add(chapter)
        return chapter

    def add_confessional(
        self,
        speaker_name: str,
        speaker_id: str,
        start_ms: int,
        topic: Optional[str] = None,
    ) -> ChapterMarker:
        """Add a confessional chapter marker.

        Args:
            speaker_name: Display name of speaker
            speaker_id: Speaker ID
            start_ms: Start time
            topic: Optional topic of confessional

        Returns:
            The created ChapterMarker
        """
        if topic:
            title = f"{speaker_name}: {topic}"
        else:
            title = f"{speaker_name}'s Confessional"

        chapter = ChapterMarker(
            title=title,
            start_ms=start_ms,
            chapter_type=ChapterType.CONFESSIONAL,
            speaker_id=speaker_id,
        )
        self.add(chapter)
        return chapter

    def finalize(self, total_duration_ms: Optional[int] = None) -> None:
        """Sort chapters and calculate end times.

        Must be called before exporting. Sets end_ms for each chapter
        to the start of the next chapter (or total duration for last).

        Args:
            total_duration_ms: Total audio duration for last chapter end
        """
        if total_duration_ms:
            self.total_duration_ms = total_duration_ms

        # Sort by start time
        self.chapters.sort(key=lambda c: c.start_ms)

        # Calculate end times
        for i, chapter in enumerate(self.chapters):
            if chapter.end_ms is None:
                if i + 1 < len(self.chapters):
                    # End at next chapter's start
                    chapter.end_ms = self.chapters[i + 1].start_ms
                elif self.total_duration_ms:
                    # Last chapter ends at file end
                    chapter.end_ms = self.total_duration_ms

    def get_by_phase(self, phase: str) -> Optional[ChapterMarker]:
        """Get chapter marker for a specific phase."""
        for chapter in self.chapters:
            if chapter.phase == phase:
                return chapter
        return None

    def get_by_type(self, chapter_type: ChapterType) -> List[ChapterMarker]:
        """Get all chapters of a specific type."""
        return [c for c in self.chapters if c.chapter_type == chapter_type]

    def merge_short_chapters(self, min_duration_ms: int = 5000) -> None:
        """Merge chapters shorter than minimum duration into previous.

        Args:
            min_duration_ms: Minimum chapter duration (default 5 seconds)
        """
        if len(self.chapters) < 2:
            return

        merged = [self.chapters[0]]

        for chapter in self.chapters[1:]:
            prev = merged[-1]
            duration = chapter.start_ms - prev.start_ms

            if duration < min_duration_ms:
                # Extend previous chapter instead of adding new one
                prev.end_ms = chapter.end_ms
                # Append title if different type
                if chapter.chapter_type != prev.chapter_type:
                    prev.title = f"{prev.title} / {chapter.title}"
            else:
                merged.append(chapter)

        self.chapters = merged

    def __len__(self) -> int:
        return len(self.chapters)

    def __iter__(self):
        return iter(self.chapters)

    def __getitem__(self, index: int) -> ChapterMarker:
        return self.chapters[index]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        result = {
            "version": "1.0",
            "chapters": [c.to_dict() for c in self.chapters],
        }

        if self.episode_title:
            result["episode_title"] = self.episode_title
        if self.episode_number:
            result["episode_number"] = self.episode_number
        if self.total_duration_ms:
            result["total_duration_ms"] = self.total_duration_ms
            result["total_duration"] = ms_to_timecode(self.total_duration_ms)

        return result


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def ms_to_timecode(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS.mmm timecode.

    Args:
        ms: Time in milliseconds

    Returns:
        Formatted timecode string
    """
    total_seconds = ms // 1000
    milliseconds = ms % 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    else:
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def timecode_to_ms(timecode: str) -> int:
    """Convert HH:MM:SS.mmm timecode to milliseconds.

    Args:
        timecode: Formatted timecode string

    Returns:
        Time in milliseconds
    """
    parts = timecode.replace(",", ".").split(":")

    if len(parts) == 3:
        hours, minutes, seconds = parts
        hours = int(hours)
    elif len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    else:
        raise ValueError(f"Invalid timecode format: {timecode}")

    minutes = int(minutes)

    if "." in seconds:
        sec_parts = seconds.split(".")
        seconds = int(sec_parts[0])
        # Handle variable precision (e.g., .5 vs .500)
        ms_str = sec_parts[1].ljust(3, "0")[:3]
        milliseconds = int(ms_str)
    else:
        seconds = int(seconds)
        milliseconds = 0

    total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
    return total_ms


def format_phase_title(phase: str) -> str:
    """Format a game phase name as a chapter title.

    Args:
        phase: Raw phase name (e.g., "breakfast", "roundtable")

    Returns:
        Formatted title (e.g., "Breakfast", "Round Table")
    """
    PHASE_TITLES = {
        "intro": "Introduction",
        "cold_open": "Previously On...",
        "breakfast": "Breakfast",
        "mission": "The Mission",
        "mission_briefing": "Mission Briefing",
        "mission_execution": "Mission",
        "social": "Social Phase",
        "roundtable": "Round Table",
        "round_table": "Round Table",
        "voting": "The Vote",
        "turret": "The Turret",
        "murder": "Murder Selection",
        "finale": "The Finale",
        "outro": "Next Time...",
    }

    phase_lower = phase.lower().replace(" ", "_")
    return PHASE_TITLES.get(phase_lower, phase.replace("_", " ").title())


def format_event_title(event_type: str, details: Optional[Dict] = None) -> str:
    """Format an event type as a chapter title.

    Args:
        event_type: Event type (e.g., "MURDER", "BANISHMENT")
        details: Optional event details (victim name, etc.)

    Returns:
        Formatted title
    """
    EVENT_TITLES = {
        "MURDER": "Murder Revealed",
        "BANISHMENT": "Banishment",
        "VOTE_TALLY": "The Votes Are In",
        "ROLE_REVEAL": "Role Revealed",
        "RECRUITMENT": "A New Traitor",
        "SHIELD_USE": "Shield Activated",
        "MISSION_COMPLETE": "Mission Complete",
        "MISSION_FAILED": "Mission Failed",
        "FINALE_START": "The Final Round",
        "WINNER": "The Winner",
    }

    base_title = EVENT_TITLES.get(event_type, event_type.replace("_", " ").title())

    # Add details if available
    if details:
        if "victim_name" in details and event_type == "MURDER":
            return f"{details['victim_name']}'s Murder"
        if "banished_name" in details and event_type == "BANISHMENT":
            return f"{details['banished_name']} Banished"
        if "revealed_role" in details and event_type == "ROLE_REVEAL":
            role = details["revealed_role"]
            name = details.get("player_name", "Unknown")
            return f"{name} Was {role}"

    return base_title


# =============================================================================
# CHAPTER EMBEDDING - MP3 (ID3v2)
# =============================================================================

def embed_chapters_mp3(filepath: str, chapters: ChapterList) -> bool:
    """Embed ID3v2 chapter markers in MP3 file.

    Uses the CHAP and CTOC frames as specified in ID3v2.4.
    Requires the 'eyed3' library.

    Args:
        filepath: Path to MP3 file
        chapters: ChapterList to embed

    Returns:
        True if successful, False otherwise
    """
    try:
        import eyed3
        from eyed3.id3 import ID3_V2_4
    except ImportError:
        logger.warning("eyed3 not installed. Install with: pip install eyed3")
        return False

    try:
        audiofile = eyed3.load(filepath)
        if audiofile is None:
            logger.error(f"Could not load MP3 file: {filepath}")
            return False

        # Initialize tag if needed
        if audiofile.tag is None:
            audiofile.initTag(version=ID3_V2_4)
        else:
            # Ensure we're using ID3v2.4 for chapter support
            audiofile.tag.version = ID3_V2_4

        # Remove existing chapters
        existing_chapters = list(audiofile.tag.chapters)
        for chapter in existing_chapters:
            audiofile.tag.chapters.remove(chapter.element_id)

        # Remove existing TOC
        existing_tocs = list(audiofile.tag.table_of_contents)
        for toc in existing_tocs:
            audiofile.tag.table_of_contents.remove(toc.element_id)

        # Add new chapters
        chapter_ids = []
        for chapter in chapters:
            element_id = chapter.id.encode("latin-1")

            # Create chapter frame with times in milliseconds
            chap = audiofile.tag.chapters.set(
                element_id,
                times=(chapter.start_ms, chapter.end_ms or chapter.start_ms),
            )

            # Add title as TIT2 sub-frame
            chap.sub_frames.setTextFrame(b"TIT2", chapter.title)

            # Add description as TIT3 if available
            if chapter.description:
                chap.sub_frames.setTextFrame(b"TIT3", chapter.description)

            chapter_ids.append(element_id)

        # Add table of contents
        if chapter_ids:
            audiofile.tag.table_of_contents.set(
                b"toc",
                toplevel=True,
                ordered=True,
                child_ids=chapter_ids,
            )

        # Save with ID3v2.4
        audiofile.tag.save(version=ID3_V2_4)
        logger.info(f"Embedded {len(chapters)} chapters in {filepath}")
        return True

    except Exception as e:
        logger.error(f"Failed to embed chapters in MP3: {e}")
        return False


def read_chapters_mp3(filepath: str) -> Optional[ChapterList]:
    """Read chapter markers from MP3 file.

    Args:
        filepath: Path to MP3 file

    Returns:
        ChapterList or None if no chapters found
    """
    try:
        import eyed3
    except ImportError:
        logger.warning("eyed3 not installed")
        return None

    try:
        audiofile = eyed3.load(filepath)
        if audiofile is None or audiofile.tag is None:
            return None

        chapters = ChapterList()

        for chap in audiofile.tag.chapters:
            # Extract times
            start_ms, end_ms = chap.times

            # Extract title from TIT2 sub-frame
            title = "Untitled"
            tit2 = chap.sub_frames.get(b"TIT2")
            if tit2:
                # sub_frames.get() returns a list
                frame = tit2[0] if isinstance(tit2, list) else tit2
                title = frame.text if hasattr(frame, 'text') else str(frame)

            # Extract description from TIT3
            description = None
            tit3 = chap.sub_frames.get(b"TIT3")
            if tit3:
                frame = tit3[0] if isinstance(tit3, list) else tit3
                description = frame.text if hasattr(frame, 'text') else str(frame)

            chapters.add(ChapterMarker(
                title=title,
                start_ms=start_ms,
                end_ms=end_ms if end_ms != start_ms else None,
                description=description,
            ))

        if len(chapters) > 0:
            # Get total duration
            if audiofile.info:
                chapters.total_duration_ms = int(audiofile.info.time_secs * 1000)
            return chapters

        return None

    except Exception as e:
        logger.error(f"Failed to read chapters from MP3: {e}")
        return None


# =============================================================================
# CHAPTER EMBEDDING - M4A/AAC (FFmpeg)
# =============================================================================

def embed_chapters_m4a(
    input_path: str,
    output_path: str,
    chapters: ChapterList,
) -> bool:
    """Embed chapters in M4A/AAC file using FFmpeg metadata.

    Creates a new file with chapters embedded. The original file
    is not modified.

    Args:
        input_path: Path to input M4A file
        output_path: Path for output file with chapters
        chapters: ChapterList to embed

    Returns:
        True if successful, False otherwise
    """
    # Check for FFmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("FFmpeg not available")
            return False
    except FileNotFoundError:
        logger.error("FFmpeg not installed")
        return False

    try:
        # Create FFmpeg metadata file
        metadata_content = ";FFMETADATA1\n"

        for chapter in chapters:
            end_ms = chapter.end_ms or chapter.start_ms
            # FFmpeg uses timebase, convert ms to proper format
            metadata_content += f"\n[CHAPTER]\n"
            metadata_content += f"TIMEBASE=1/1000\n"
            metadata_content += f"START={chapter.start_ms}\n"
            metadata_content += f"END={end_ms}\n"
            # Escape special characters in title
            safe_title = chapter.title.replace("=", "\\=").replace(";", "\\;")
            metadata_content += f"title={safe_title}\n"

        # Write metadata to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as metadata_file:
            metadata_file.write(metadata_content)
            metadata_path = metadata_file.name

        try:
            # Run FFmpeg to add chapters
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", input_path,
                "-i", metadata_path,
                "-map_metadata", "1",
                "-codec", "copy",
                output_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg failed: {result.stderr}")
                return False

            logger.info(f"Embedded {len(chapters)} chapters in {output_path}")
            return True

        finally:
            # Clean up temp file
            os.unlink(metadata_path)

    except Exception as e:
        logger.error(f"Failed to embed chapters in M4A: {e}")
        return False


def read_chapters_m4a(filepath: str) -> Optional[ChapterList]:
    """Read chapter markers from M4A file using FFprobe.

    Args:
        filepath: Path to M4A file

    Returns:
        ChapterList or None if no chapters found
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_chapters",
            filepath,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        if "chapters" not in data or not data["chapters"]:
            return None

        chapters = ChapterList()

        for chap_data in data["chapters"]:
            # FFprobe returns times as strings with time_base
            start_time = float(chap_data.get("start_time", 0))
            end_time = float(chap_data.get("end_time", start_time))

            title = chap_data.get("tags", {}).get("title", "Untitled")

            chapters.add(ChapterMarker(
                title=title,
                start_ms=int(start_time * 1000),
                end_ms=int(end_time * 1000) if end_time != start_time else None,
            ))

        return chapters if len(chapters) > 0 else None

    except Exception as e:
        logger.error(f"Failed to read chapters from M4A: {e}")
        return None


# =============================================================================
# UNIVERSAL EMBEDDING FUNCTION
# =============================================================================

def embed_chapters(
    filepath: str,
    chapters: ChapterList,
    output_path: Optional[str] = None,
) -> bool:
    """Embed chapters in audio file (auto-detects format).

    For MP3: Modifies file in-place with ID3v2 chapters.
    For M4A: Creates new file with chapters (requires output_path).

    Args:
        filepath: Path to audio file
        chapters: ChapterList to embed
        output_path: Output path for formats that require it (M4A)

    Returns:
        True if successful, False otherwise
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    # Finalize chapters if not already done
    if any(c.end_ms is None for c in chapters):
        chapters.finalize()

    if ext == ".mp3":
        return embed_chapters_mp3(filepath, chapters)
    elif ext in (".m4a", ".aac", ".mp4"):
        if output_path is None:
            # Create temp output, then replace original
            output_path = str(path.with_suffix(".chapters" + ext))
            success = embed_chapters_m4a(filepath, output_path, chapters)
            if success:
                # Replace original with chaptered version
                os.replace(output_path, filepath)
            return success
        else:
            return embed_chapters_m4a(filepath, output_path, chapters)
    else:
        logger.warning(f"Unsupported format for chapter embedding: {ext}")
        return False


# =============================================================================
# EXTERNAL FORMAT EXPORT
# =============================================================================

def export_chapters_json(
    chapters: ChapterList,
    output_path: str,
    pretty: bool = True,
) -> bool:
    """Export chapters to JSON format.

    Args:
        chapters: ChapterList to export
        output_path: Output file path
        pretty: Whether to format JSON nicely

    Returns:
        True if successful
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                chapters.to_dict(),
                f,
                indent=2 if pretty else None,
                ensure_ascii=False,
            )
        logger.info(f"Exported {len(chapters)} chapters to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export chapters to JSON: {e}")
        return False


def export_chapters_podlove(chapters: ChapterList, output_path: str) -> bool:
    """Export chapters to Podlove Simple Chapters format.

    Podlove Simple Chapters is a lightweight format used by many
    podcast apps and players.

    Format: <psc:chapters> XML or simple text format
    Reference: https://podlove.org/simple-chapters/

    Args:
        chapters: ChapterList to export
        output_path: Output file path

    Returns:
        True if successful
    """
    try:
        lines = ["# Podlove Simple Chapters", ""]

        for chapter in chapters:
            # Format: (HH:MM:SS.mmm) Title
            line = f"({chapter.start_timecode}) {chapter.title}"
            if chapter.url:
                line += f" <{chapter.url}>"
            lines.append(line)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported {len(chapters)} chapters to Podlove format")
        return True
    except Exception as e:
        logger.error(f"Failed to export Podlove chapters: {e}")
        return False


def export_chapters_webvtt(chapters: ChapterList, output_path: str) -> bool:
    """Export chapters to WebVTT chapter format.

    WebVTT chapters can be used for HTML5 video/audio chapter tracks.

    Args:
        chapters: ChapterList to export
        output_path: Output file path

    Returns:
        True if successful
    """
    try:
        lines = ["WEBVTT", ""]

        for i, chapter in enumerate(chapters):
            lines.append(f"Chapter {i + 1}")

            # WebVTT uses HH:MM:SS.mmm --> HH:MM:SS.mmm format
            start = chapter.start_timecode
            end = chapter.end_timecode or chapter.start_timecode

            # Ensure HH:MM:SS format (pad if needed)
            if start.count(":") == 1:
                start = "00:" + start
            if end.count(":") == 1:
                end = "00:" + end

            lines.append(f"{start} --> {end}")
            lines.append(chapter.title)
            lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported {len(chapters)} chapters to WebVTT format")
        return True
    except Exception as e:
        logger.error(f"Failed to export WebVTT chapters: {e}")
        return False


def export_chapters_ffmetadata(chapters: ChapterList, output_path: str) -> bool:
    """Export chapters to FFmpeg metadata format.

    This format can be used with FFmpeg's -i metadata.txt option.

    Args:
        chapters: ChapterList to export
        output_path: Output file path

    Returns:
        True if successful
    """
    try:
        lines = [";FFMETADATA1"]

        if chapters.episode_title:
            lines.append(f"title={chapters.episode_title}")
        if chapters.episode_number:
            lines.append(f"track={chapters.episode_number}")

        for chapter in chapters:
            lines.append("")
            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={chapter.start_ms}")
            lines.append(f"END={chapter.end_ms or chapter.start_ms}")
            safe_title = chapter.title.replace("=", "\\=")
            lines.append(f"title={safe_title}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported {len(chapters)} chapters to FFmetadata format")
        return True
    except Exception as e:
        logger.error(f"Failed to export FFmetadata: {e}")
        return False


# =============================================================================
# CHAPTER GENERATION FROM GAME DATA
# =============================================================================

def generate_episode_chapters(
    voice_segments: List[Any],
    script: Optional[Any] = None,
    total_duration_ms: Optional[int] = None,
    include_events: bool = True,
    include_confessionals: bool = False,
    min_chapter_duration_ms: int = 10000,
) -> ChapterList:
    """Generate chapter markers from episode voice segments.

    Analyzes the voice segments and script to create meaningful
    chapter markers for navigation.

    Args:
        voice_segments: List of VoiceSegmentAudio objects from timeline
        script: Optional DialogueScript for additional metadata
        total_duration_ms: Total episode duration
        include_events: Include event-based chapters (murder, banishment)
        include_confessionals: Include per-confessional chapters
        min_chapter_duration_ms: Minimum chapter duration

    Returns:
        ChapterList with generated chapters
    """
    chapters = ChapterList(total_duration_ms=total_duration_ms)

    if not voice_segments:
        return chapters

    # Track phase changes
    current_phase = None
    phase_start_ms = 0

    for segment in voice_segments:
        seg_data = segment.segment if hasattr(segment, "segment") else segment

        # Get phase from segment
        phase = getattr(seg_data, "phase", None)
        if phase is None and hasattr(seg_data, "metadata"):
            phase = seg_data.metadata.get("phase")

        # Phase changed - add chapter
        if phase and phase != current_phase:
            if current_phase is not None:
                # End previous phase
                pass

            chapters.add_phase(
                phase=phase,
                start_ms=segment.start_ms,
            )
            current_phase = phase
            phase_start_ms = segment.start_ms

        # Check for significant events
        if include_events:
            event_type = getattr(seg_data, "event_type", None)
            if event_type in ("MURDER", "BANISHMENT", "ROLE_REVEAL"):
                chapters.add_event(
                    event_type=event_type,
                    start_ms=segment.start_ms,
                )

        # Check for confessionals
        if include_confessionals:
            seg_type = getattr(seg_data, "segment_type", None)
            if seg_type and str(seg_type).endswith("CONFESSIONAL"):
                speaker_name = getattr(seg_data, "speaker_name", None)
                speaker_id = getattr(seg_data, "speaker_id", None)
                if speaker_name:
                    chapters.add_confessional(
                        speaker_name=speaker_name,
                        speaker_id=speaker_id or "unknown",
                        start_ms=segment.start_ms,
                    )

    # Finalize and clean up
    chapters.finalize(total_duration_ms)
    chapters.merge_short_chapters(min_chapter_duration_ms)

    return chapters
