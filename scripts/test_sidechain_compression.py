#!/usr/bin/env python3
"""Test script for sidechain compression (dynamic mixing).

This script validates that:
1. SidechainCompressor correctly extracts envelope from trigger signal
2. Gain reduction is applied proportionally based on trigger level
3. Attack/release timing creates smooth ducking transitions
4. AudioTimeline.apply_sidechain_compression works end-to-end
5. The resulting audio has proper dynamic mixing

Usage:
    python scripts/test_sidechain_compression.py
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traitorsim.voice.audio_assembler import (
    SidechainConfig,
    SidechainCompressor,
    AudioTimeline,
    AudioTrack,
    audio_segment_to_numpy,
    numpy_to_audio_segment,
)
from traitorsim.voice.models import DialogueSegment, SegmentType

# Try to import pydub
try:
    from pydub import AudioSegment
    from pydub.generators import Sine
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("Warning: pydub not available, using numpy-only tests")


def generate_test_signal(
    duration_s: float,
    sample_rate: int = 44100,
    frequency: float = 440.0,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Generate a sine wave test signal."""
    t = np.linspace(0, duration_s, int(duration_s * sample_rate), dtype=np.float32)
    return amplitude * np.sin(2 * np.pi * frequency * t)


def generate_voice_like_signal(
    duration_s: float,
    sample_rate: int = 44100,
    speech_ratio: float = 0.6,
) -> np.ndarray:
    """Generate a signal that simulates voice with pauses.

    Creates alternating speech and silence regions to test ducking behavior.
    """
    total_samples = int(duration_s * sample_rate)
    signal = np.zeros(total_samples, dtype=np.float32)

    # Create speech bursts of varying lengths
    position = 0
    is_speaking = True

    while position < total_samples:
        if is_speaking:
            # Speech segment (0.5 to 2 seconds)
            length = int(np.random.uniform(0.5, 2.0) * sample_rate)
            length = min(length, total_samples - position)

            # Generate voice-like content (multiple harmonics)
            t = np.arange(length) / sample_rate
            base_freq = np.random.uniform(120, 250)  # Voice fundamental

            voice = 0.3 * np.sin(2 * np.pi * base_freq * t)
            voice += 0.2 * np.sin(2 * np.pi * 2 * base_freq * t)
            voice += 0.1 * np.sin(2 * np.pi * 3 * base_freq * t)

            # Apply envelope (fade in/out)
            envelope = np.ones(length)
            fade_samples = int(0.05 * sample_rate)
            if length > 2 * fade_samples:
                envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
                envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

            signal[position:position + length] = voice * envelope
            position += length
        else:
            # Silence/pause segment (0.2 to 1 second)
            length = int(np.random.uniform(0.2, 1.0) * sample_rate)
            length = min(length, total_samples - position)
            position += length

        is_speaking = not is_speaking

    return signal


def test_envelope_extraction():
    """Test that envelope is correctly extracted from signal."""
    print("\n=== Test: Envelope Extraction ===")

    config = SidechainConfig()
    compressor = SidechainCompressor(config)

    # Create a signal with known envelope
    sample_rate = 44100
    duration = 1.0

    # Sine wave with amplitude ramp
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples)
    amplitude = np.linspace(0, 1, samples)  # Ramp from 0 to 1
    signal = amplitude * np.sin(2 * np.pi * 440 * t)

    # Extract envelope
    envelope = compressor._extract_envelope(signal, sample_rate)

    # Envelope should roughly follow amplitude ramp (in dB)
    # At the end, amplitude is 1.0 (RMS ~0.707), so dB should be around -3dB
    # At the start, amplitude is ~0, so dB should be very low

    mid_idx = len(envelope) // 2
    end_idx = len(envelope) - 1000

    print(f"  Start envelope: {envelope[1000]:.1f} dB (expected: low)")
    print(f"  Mid envelope: {envelope[mid_idx]:.1f} dB")
    print(f"  End envelope: {envelope[end_idx]:.1f} dB (expected: ~-3 dB)")

    # Basic sanity checks
    assert envelope[end_idx] > envelope[1000], "Envelope should increase with amplitude"
    assert envelope[end_idx] > -10, "End envelope should be close to 0 dB"

    print("  PASSED: Envelope extraction working correctly")


def test_attack_release():
    """Test attack and release timing characteristics."""
    print("\n=== Test: Attack/Release Timing ===")

    sample_rate = 44100

    # Fast attack, slow release
    config = SidechainConfig(
        attack_ms=5.0,
        release_ms=200.0,
        hold_ms=0.0,
    )
    compressor = SidechainCompressor(config)

    # Create impulse envelope (instant rise, then silence)
    duration = 0.5
    samples = int(duration * sample_rate)
    envelope = np.zeros(samples)

    # 100ms of signal, then silence
    signal_end = int(0.1 * sample_rate)
    envelope[:signal_end] = -6.0  # -6 dB
    envelope[signal_end:] = -60.0  # Very quiet

    # Apply attack/release
    smoothed = compressor._apply_attack_release(envelope, sample_rate)

    # Check attack: should reach target quickly
    attack_time_samples = int(0.02 * sample_rate)  # Check at 20ms
    attack_reached = smoothed[attack_time_samples]
    print(f"  Level at 20ms (attack): {attack_reached:.1f} dB (target: -6 dB)")

    # Check release: should decay slowly after signal ends
    release_check_samples = signal_end + int(0.1 * sample_rate)  # 100ms after signal ends
    release_level = smoothed[release_check_samples]
    print(f"  Level 100ms after signal ends: {release_level:.1f} dB (expected: still elevated)")

    # After 200ms (release time), should be much closer to floor
    release_done_samples = signal_end + int(0.4 * sample_rate)  # 400ms after (2x release)
    final_level = smoothed[min(release_done_samples, len(smoothed) - 1)]
    print(f"  Level 400ms after signal ends: {final_level:.1f} dB")

    assert attack_reached > -10, "Attack should have reached near target"
    assert release_level > -40, "Release should still be elevated after 100ms"

    print("  PASSED: Attack/release timing working correctly")


def test_gain_reduction():
    """Test that gain reduction follows compressor curve."""
    print("\n=== Test: Gain Reduction Curve ===")

    config = SidechainConfig(
        threshold_db=-24.0,
        ratio=4.0,
        knee_db=6.0,
        range_db=-24.0,
    )
    compressor = SidechainCompressor(config)

    # Test at various envelope levels
    test_levels = np.array([-40, -30, -24, -18, -12, -6, 0])

    for level in test_levels:
        envelope = np.array([level])
        reduction = compressor._compute_gain_reduction(envelope)[0]
        print(f"  Input: {level:4.0f} dB -> Reduction: {reduction:5.1f} dB")

    # At threshold (-24 dB), reduction should be minimal (in soft knee)
    # Well above threshold (0 dB), reduction should be significant
    below_threshold = compressor._compute_gain_reduction(np.array([-30]))[0]
    above_threshold = compressor._compute_gain_reduction(np.array([0]))[0]

    assert below_threshold > -2, "Below threshold should have minimal reduction"
    assert above_threshold < -10, "Well above threshold should have significant reduction"

    print("  PASSED: Gain reduction curve working correctly")


def test_full_sidechain_process():
    """Test full sidechain compression pipeline."""
    print("\n=== Test: Full Sidechain Processing ===")

    sample_rate = 44100
    duration = 3.0

    config = SidechainConfig(
        threshold_db=-24.0,
        ratio=4.0,
        attack_ms=10.0,
        release_ms=150.0,
    )
    compressor = SidechainCompressor(config)

    # Generate voice-like trigger (with pauses)
    trigger = generate_voice_like_signal(duration, sample_rate)

    # Generate constant music target
    music = generate_test_signal(duration, sample_rate, frequency=440, amplitude=0.3)

    # Apply sidechain
    result = compressor.process(trigger, music, sample_rate)

    # Compare RMS during voice vs silence
    voice_present = np.abs(trigger) > 0.05
    voice_samples = result[voice_present]
    silence_samples = result[~voice_present]

    if len(voice_samples) > 0 and len(silence_samples) > 0:
        voice_rms = np.sqrt(np.mean(voice_samples ** 2))
        silence_rms = np.sqrt(np.mean(silence_samples ** 2))

        print(f"  Music RMS during voice: {20 * np.log10(voice_rms + 1e-10):.1f} dB")
        print(f"  Music RMS during silence: {20 * np.log10(silence_rms + 1e-10):.1f} dB")

        # Music should be quieter during voice
        assert voice_rms < silence_rms, "Music should be ducked during voice"
        print("  PASSED: Music properly ducks under voice")
    else:
        print("  SKIPPED: Not enough data for comparison")


def test_timeline_integration():
    """Test AudioTimeline.apply_sidechain_compression."""
    print("\n=== Test: Timeline Integration ===")

    if not HAS_PYDUB:
        print("  SKIPPED: pydub not available")
        return

    # Create timeline
    timeline = AudioTimeline()

    # Create mock voice segment
    voice_audio = Sine(300).to_audio_segment(duration=2000)  # 2 second voice
    voice_audio = voice_audio - 6  # Normalize

    # Create mock dialogue segment
    segment = DialogueSegment(
        segment_type=SegmentType.DIALOGUE,
        speaker_id="player_1",
        text="Test speech",
        voice_id="test_voice",
    )

    # Add voice to timeline
    timeline.add_voice_segment(segment, voice_audio, start_ms=500)

    # Create music track
    music_audio = Sine(440).to_audio_segment(duration=5000)  # 5 seconds music
    music_audio = music_audio - 12  # Quieter than voice

    timeline.add_track(
        name="music_background",
        audio=music_audio,
        start_ms=0,
        volume_db=0,
        duck_under_voice=True,
    )

    # Apply sidechain compression
    timeline.apply_sidechain_compression(
        trigger_tracks="voice",
        duck_tracks="music",
        config=SidechainConfig(
            threshold_db=-24,
            ratio=4.0,
        ),
    )

    # Check that music track was processed
    music_track = timeline.tracks[0]
    assert not music_track.duck_under_voice, "Track should be marked as processed"
    print(f"  Music track processed: {music_track.name}")
    print(f"  Music duration: {len(music_track.audio)}ms")

    # Mix and verify
    mixed = timeline.mix()
    print(f"  Mixed duration: {len(mixed)}ms")

    print("  PASSED: Timeline integration working correctly")


def test_numpy_audiosegment_conversion():
    """Test numpy to/from AudioSegment conversion."""
    print("\n=== Test: NumPy/AudioSegment Conversion ===")

    if not HAS_PYDUB:
        print("  SKIPPED: pydub not available")
        return

    # Create original audio
    original = Sine(440).to_audio_segment(duration=1000)

    # Convert to numpy
    samples, sample_rate = audio_segment_to_numpy(original)
    print(f"  Original: {len(original)}ms, {original.frame_rate}Hz")
    print(f"  NumPy: {len(samples)} samples, {sample_rate}Hz")

    # Verify sample count matches duration
    expected_samples = int(len(original) * sample_rate / 1000)
    assert abs(len(samples) - expected_samples) < 100, "Sample count mismatch"

    # Convert back
    reconstructed = numpy_to_audio_segment(samples, sample_rate)
    print(f"  Reconstructed: {len(reconstructed)}ms")

    # Verify duration is similar
    assert abs(len(reconstructed) - len(original)) < 100, "Duration mismatch"

    print("  PASSED: Conversion working correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("SIDECHAIN COMPRESSION TEST SUITE")
    print("=" * 60)

    try:
        test_envelope_extraction()
        test_attack_release()
        test_gain_reduction()
        test_full_sidechain_process()
        test_numpy_audiosegment_conversion()
        test_timeline_integration()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
