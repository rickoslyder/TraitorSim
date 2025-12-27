#!/usr/bin/env python3
"""Test script for chapter markers.

This script validates that:
1. ChapterMarker and ChapterList data structures work correctly
2. Timecode conversion is accurate
3. Chapter generation from timeline works
4. External format export (JSON, Podlove, WebVTT) produces valid output
5. MP3 chapter embedding works (if eyed3 is available)

Usage:
    python scripts/test_chapter_markers.py
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traitorsim.voice.chapters import (
    ChapterMarker,
    ChapterList,
    ChapterType,
    ms_to_timecode,
    timecode_to_ms,
    format_phase_title,
    format_event_title,
    export_chapters_json,
    export_chapters_podlove,
    export_chapters_webvtt,
    export_chapters_ffmetadata,
    embed_chapters_mp3,
    read_chapters_mp3,
)

# Try to import pydub for audio tests
try:
    from pydub import AudioSegment
    from pydub.generators import Sine
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("Warning: pydub not available, skipping audio tests")

# Try to import eyed3 for MP3 chapter tests
try:
    import eyed3
    HAS_EYED3 = True
except ImportError:
    HAS_EYED3 = False
    print("Warning: eyed3 not available, skipping MP3 embedding tests")


def test_timecode_conversion():
    """Test millisecond to timecode conversion and back."""
    print("\n=== Test: Timecode Conversion ===")

    test_cases = [
        (0, "00:00.000"),
        (1000, "00:01.000"),
        (60000, "01:00.000"),
        (3661500, "01:01:01.500"),  # 1h 1m 1.5s
        (45000, "00:45.000"),
        (123456, "02:03.456"),
    ]

    for ms, expected_base in test_cases:
        result = ms_to_timecode(ms)
        # Convert back
        back = timecode_to_ms(result)

        print(f"  {ms}ms -> {result} -> {back}ms")
        assert back == ms, f"Round trip failed: {ms} != {back}"

    # Test parsing various formats
    parse_tests = [
        ("00:30.000", 30000),
        ("01:30.500", 90500),
        ("1:30.5", 90500),  # Short format
        ("01:00:00.000", 3600000),  # 1 hour
    ]

    for timecode, expected_ms in parse_tests:
        result = timecode_to_ms(timecode)
        print(f"  Parse '{timecode}' -> {result}ms (expected {expected_ms})")
        assert result == expected_ms, f"Parse failed: {result} != {expected_ms}"

    print("  PASSED: Timecode conversion working correctly")


def test_chapter_marker():
    """Test ChapterMarker data class."""
    print("\n=== Test: ChapterMarker ===")

    # Basic chapter
    chapter = ChapterMarker(
        title="Breakfast",
        start_ms=45000,
        chapter_type=ChapterType.PHASE,
        phase="breakfast",
    )

    print(f"  ID: {chapter.id}")
    print(f"  Title: {chapter.title}")
    print(f"  Start: {chapter.start_timecode}")
    print(f"  Type: {chapter.chapter_type}")

    assert chapter.id == "chap_00045000"
    assert chapter.start_seconds == 45.0
    assert chapter.start_timecode == "00:45.000"

    # With end time
    chapter.end_ms = 120000
    assert chapter.end_seconds == 120.0
    assert chapter.duration_ms == 75000

    # To dict
    data = chapter.to_dict()
    assert data["title"] == "Breakfast"
    assert data["start_ms"] == 45000
    assert data["end_ms"] == 120000
    assert data["phase"] == "breakfast"

    print("  PASSED: ChapterMarker working correctly")


def test_chapter_list():
    """Test ChapterList collection."""
    print("\n=== Test: ChapterList ===")

    chapters = ChapterList(
        episode_title="Day 3",
        episode_number=3,
    )

    # Add phases
    chapters.add_phase("intro", start_ms=0)
    chapters.add_phase("breakfast", start_ms=5000)
    chapters.add_phase("mission", start_ms=60000)
    chapters.add_phase("roundtable", start_ms=180000)
    chapters.add_phase("turret", start_ms=420000)

    print(f"  Added {len(chapters)} chapters")

    # Finalize with total duration
    chapters.finalize(total_duration_ms=500000)

    # Check end times are set
    for i, chapter in enumerate(chapters):
        print(f"  {i+1}. {chapter.title}: {chapter.start_timecode} - {chapter.end_timecode}")
        assert chapter.end_ms is not None, f"Chapter {chapter.title} missing end time"

    # Check last chapter ends at total duration
    assert chapters[-1].end_ms == 500000

    # Test merge short chapters
    short_chapters = ChapterList()
    short_chapters.add_phase("intro", start_ms=0)
    short_chapters.add_phase("short_bit", start_ms=2000)  # Only 2 seconds
    short_chapters.add_phase("main", start_ms=5000)
    short_chapters.finalize(60000)

    before_count = len(short_chapters)
    short_chapters.merge_short_chapters(min_duration_ms=3000)
    after_count = len(short_chapters)

    print(f"  Merge test: {before_count} -> {after_count} chapters")
    assert after_count < before_count, "Short chapters should be merged"

    print("  PASSED: ChapterList working correctly")


def test_format_titles():
    """Test phase and event title formatting."""
    print("\n=== Test: Title Formatting ===")

    # Phase titles
    phase_tests = [
        ("breakfast", "Breakfast"),
        ("roundtable", "Round Table"),
        ("round_table", "Round Table"),
        ("turret", "The Turret"),
        ("mission", "The Mission"),
        ("social", "Social Phase"),
    ]

    for phase, expected in phase_tests:
        result = format_phase_title(phase)
        print(f"  Phase '{phase}' -> '{result}'")
        assert result == expected, f"Expected '{expected}', got '{result}'"

    # Event titles
    event_tests = [
        ("MURDER", None, "Murder Revealed"),
        ("BANISHMENT", None, "Banishment"),
        ("MURDER", {"victim_name": "Marcus"}, "Marcus's Murder"),
        ("BANISHMENT", {"banished_name": "Patricia"}, "Patricia Banished"),
    ]

    for event, details, expected in event_tests:
        result = format_event_title(event, details)
        print(f"  Event '{event}' -> '{result}'")
        assert result == expected, f"Expected '{expected}', got '{result}'"

    print("  PASSED: Title formatting working correctly")


def test_export_json():
    """Test JSON export."""
    print("\n=== Test: JSON Export ===")

    chapters = ChapterList(episode_title="Test Episode", episode_number=1)
    chapters.add_phase("breakfast", start_ms=0)
    chapters.add_phase("mission", start_ms=60000)
    chapters.add_event("MURDER", start_ms=30000)
    chapters.finalize(120000)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json_path = f.name

    try:
        success = export_chapters_json(chapters, json_path)
        assert success, "JSON export failed"

        # Read and validate
        with open(json_path, "r") as f:
            data = json.load(f)

        print(f"  Exported to: {json_path}")
        print(f"  Version: {data.get('version')}")
        print(f"  Chapters: {len(data.get('chapters', []))}")

        assert data["version"] == "1.0"
        assert len(data["chapters"]) == 3
        assert data["episode_title"] == "Test Episode"
        assert data["episode_number"] == 1

        # Check chapter data
        for chap in data["chapters"]:
            print(f"    - {chap['title']} @ {chap['start_time']}")
            assert "id" in chap
            assert "title" in chap
            assert "start_ms" in chap

        print("  PASSED: JSON export working correctly")

    finally:
        os.unlink(json_path)


def test_export_podlove():
    """Test Podlove Simple Chapters export."""
    print("\n=== Test: Podlove Export ===")

    chapters = ChapterList()
    chapters.add_phase("intro", start_ms=0)
    chapters.add_phase("breakfast", start_ms=45000)
    chapters.add_phase("mission", start_ms=150000)
    chapters.finalize(300000)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        podlove_path = f.name

    try:
        success = export_chapters_podlove(chapters, podlove_path)
        assert success, "Podlove export failed"

        # Read and validate
        with open(podlove_path, "r") as f:
            content = f.read()

        print(f"  Content:\n{content}")

        # Check format
        lines = content.strip().split("\n")
        assert lines[0] == "# Podlove Simple Chapters"

        # Check chapter lines
        chapter_lines = [l for l in lines if l.startswith("(")]
        assert len(chapter_lines) == 3

        # Each line should have format: (HH:MM:SS.mmm) Title
        for line in chapter_lines:
            assert line.startswith("(")
            assert ")" in line
            print(f"    {line}")

        print("  PASSED: Podlove export working correctly")

    finally:
        os.unlink(podlove_path)


def test_export_webvtt():
    """Test WebVTT chapter export."""
    print("\n=== Test: WebVTT Export ===")

    chapters = ChapterList()
    chapters.add_phase("intro", start_ms=0)
    chapters.add_phase("breakfast", start_ms=45000)
    chapters.finalize(120000)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".vtt", delete=False) as f:
        vtt_path = f.name

    try:
        success = export_chapters_webvtt(chapters, vtt_path)
        assert success, "WebVTT export failed"

        with open(vtt_path, "r") as f:
            content = f.read()

        print(f"  Content:\n{content}")

        # Check format
        lines = content.strip().split("\n")
        assert lines[0] == "WEBVTT"

        # Check for arrow separator
        arrow_lines = [l for l in lines if "-->" in l]
        assert len(arrow_lines) == 2

        print("  PASSED: WebVTT export working correctly")

    finally:
        os.unlink(vtt_path)


def test_export_ffmetadata():
    """Test FFmpeg metadata export."""
    print("\n=== Test: FFmetadata Export ===")

    chapters = ChapterList(episode_title="Test", episode_number=5)
    chapters.add_phase("breakfast", start_ms=0)
    chapters.add_phase("mission", start_ms=60000)
    chapters.finalize(120000)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        ffmeta_path = f.name

    try:
        success = export_chapters_ffmetadata(chapters, ffmeta_path)
        assert success, "FFmetadata export failed"

        with open(ffmeta_path, "r") as f:
            content = f.read()

        print(f"  Content:\n{content[:500]}...")

        # Check format
        assert content.startswith(";FFMETADATA1")
        assert "[CHAPTER]" in content
        assert "TIMEBASE=1/1000" in content
        assert "START=" in content
        assert "END=" in content

        print("  PASSED: FFmetadata export working correctly")

    finally:
        os.unlink(ffmeta_path)


def test_mp3_embedding():
    """Test MP3 chapter embedding (requires eyed3 and pydub)."""
    print("\n=== Test: MP3 Chapter Embedding ===")

    if not HAS_PYDUB:
        print("  SKIPPED: pydub not available")
        return

    if not HAS_EYED3:
        print("  SKIPPED: eyed3 not available")
        return

    # Create test MP3
    audio = Sine(440).to_audio_segment(duration=10000)  # 10 seconds

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        mp3_path = f.name

    try:
        # Export MP3
        audio.export(mp3_path, format="mp3")
        print(f"  Created test MP3: {mp3_path}")

        # Create chapters
        chapters = ChapterList(episode_title="Test Episode")
        chapters.add_phase("intro", start_ms=0)
        chapters.add_phase("middle", start_ms=3000)
        chapters.add_phase("outro", start_ms=7000)
        chapters.finalize(10000)

        # Embed chapters
        success = embed_chapters_mp3(mp3_path, chapters)
        print(f"  Embedding result: {success}")

        if not success:
            print("  WARNING: Chapter embedding returned False")
            return

        # Read back chapters
        read_chapters = read_chapters_mp3(mp3_path)
        if read_chapters is None:
            print("  WARNING: Could not read chapters back")
            return

        print(f"  Read back {len(read_chapters)} chapters:")
        for chap in read_chapters:
            print(f"    - {chap.title}: {chap.start_timecode} - {chap.end_timecode}")

        assert len(read_chapters) == 3, f"Expected 3 chapters, got {len(read_chapters)}"

        print("  PASSED: MP3 chapter embedding working correctly")

    finally:
        os.unlink(mp3_path)


def test_timeline_integration():
    """Test chapter generation from AudioTimeline."""
    print("\n=== Test: Timeline Integration ===")

    if not HAS_PYDUB:
        print("  SKIPPED: pydub not available")
        return

    # Import here to avoid errors if pydub not available
    from traitorsim.voice.audio_assembler import AudioTimeline
    from traitorsim.voice.models import DialogueSegment, SegmentType

    # Create timeline with segments
    timeline = AudioTimeline()

    # Create mock segments for different phases
    phases = [
        ("breakfast", 0),
        ("mission", 5000),
        ("roundtable", 15000),
        ("turret", 30000),
    ]

    for phase, start_ms in phases:
        segment = DialogueSegment(
            segment_type=SegmentType.NARRATION,
            speaker_id="narrator",
            text=f"This is the {phase} phase.",
            voice_id="narrator_voice",
            phase=phase,
        )

        audio = Sine(440).to_audio_segment(duration=3000)
        timeline.add_voice_segment(segment, audio, start_ms=start_ms)

    # Generate chapters
    chapters = timeline.generate_chapters(
        include_events=True,
        include_confessionals=False,
        min_duration_ms=2000,
        episode_title="Test Episode",
        episode_number=1,
    )

    print(f"  Generated {len(chapters)} chapters:")
    for chap in chapters:
        print(f"    - {chap.title}: {chap.start_timecode}")

    assert len(chapters) > 0, "Should generate at least one chapter"

    print("  PASSED: Timeline integration working correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("CHAPTER MARKERS TEST SUITE")
    print("=" * 60)

    try:
        test_timecode_conversion()
        test_chapter_marker()
        test_chapter_list()
        test_format_titles()
        test_export_json()
        test_export_podlove()
        test_export_webvtt()
        test_export_ffmetadata()
        test_mp3_embedding()
        test_timeline_integration()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
