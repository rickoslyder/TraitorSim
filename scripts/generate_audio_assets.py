#!/usr/bin/env python3
"""Generate synthesized placeholder audio assets for TraitorSim.

This script creates simple synthesized audio files for development and testing.
The audio pipeline (audio_assembler.py) is source-agnostic, so these placeholders
can be replaced with professional assets later.

Audio Generation Techniques Used:
- Sine waves with ADSR envelopes for musical tones
- Filtered noise for atmospheric sounds (simplified without scipy)
- Frequency modulation for dramatic effects
- Layered harmonics for richer textures

Dependencies:
    numpy (only - no scipy required)

Usage:
    python scripts/generate_audio_assets.py

Output:
    assets/music/*.mp3     - 12 music cues
    assets/sfx/*.mp3       - 14 sound effects
    assets/ambient/*.mp3   - 7 ambient loops
    assets/AUDIO_MANIFEST.md - Documentation for future replacement
"""

import os
import wave
import struct
import numpy as np
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional, List, Tuple


# Audio parameters
SAMPLE_RATE = 44100
BIT_DEPTH = 16


@dataclass
class AudioSpec:
    """Specification for an audio asset."""
    filename: str
    duration_sec: float
    description: str
    replacement_keywords: str
    generator: str  # Name of generator function


# ============================================================================
# AUDIO SPECIFICATIONS
# ============================================================================

MUSIC_SPECS = [
    AudioSpec("breakfast_uneasy.mp3", 60.0,
              "Tense, uneasy music for murder reveal at breakfast",
              "suspenseful strings, minor key, building tension",
              "generate_uneasy_music"),
    AudioSpec("mission_pulse.mp3", 90.0,
              "Energetic, pulsing music for mission challenges",
              "action music, rhythmic, driving beat",
              "generate_pulse_music"),
    AudioSpec("social_whispers.mp3", 60.0,
              "Conspiratorial, whispery background for social phase",
              "mysterious, subtle, intrigue music",
              "generate_whisper_music"),
    AudioSpec("roundtable_suspicion.mp3", 120.0,
              "Building suspicion music for voting phase",
              "dramatic tension, rising stakes, orchestral",
              "generate_suspicion_music"),
    AudioSpec("turret_darkness.mp3", 45.0,
              "Dark, menacing music for Traitor murder selection",
              "horror elements, minor key, ominous",
              "generate_darkness_music"),
    AudioSpec("finale_climax.mp3", 60.0,
              "Epic climactic music for game finale",
              "triumphant, dramatic crescendo, orchestral",
              "generate_climax_music"),
    AudioSpec("tension_build.mp3", 30.0,
              "Short tension building cue",
              "rising tension, suspenseful, building",
              "generate_tension_build"),
    AudioSpec("dramatic_hit.mp3", 5.0,
              "Dramatic musical hit/sting",
              "orchestra hit, dramatic reveal, impact",
              "generate_dramatic_hit"),
    AudioSpec("somber_reflection.mp3", 45.0,
              "Sad, reflective music for aftermath of deaths",
              "melancholy, piano, strings, emotional",
              "generate_somber_music"),
    AudioSpec("mysterious_shadows.mp3", 60.0,
              "Mysterious underscore for unknown events",
              "mysterious, ambient, ethereal",
              "generate_mysterious_music"),
    AudioSpec("triumphant_brass.mp3", 30.0,
              "Victory fanfare for successful outcomes",
              "triumphant, brass, celebration, victory",
              "generate_triumphant_music"),
    AudioSpec("neutral_background.mp3", 120.0,
              "Neutral background music for transitions",
              "ambient, neutral, background, subtle",
              "generate_neutral_music"),
]

SFX_SPECS = [
    AudioSpec("murder_reveal_sting.mp3", 3.0,
              "Dramatic sting for murder reveal moment",
              "horror sting, dramatic reveal, shock",
              "generate_horror_sting"),
    AudioSpec("vote_drumroll.mp3", 8.0,
              "Tension-building drumroll for vote counting",
              "drumroll, tension, anticipation",
              "generate_drumroll"),
    AudioSpec("traitor_reveal_triumph.mp3", 4.0,
              "Triumphant sting when Traitor is correctly banished",
              "victory sting, revelation, triumph",
              "generate_triumph_sting"),
    AudioSpec("faithful_reveal_tragic.mp3", 4.0,
              "Tragic sting when Faithful is wrongly banished",
              "tragic sting, mistake, sad",
              "generate_tragic_sting"),
    AudioSpec("recruitment_sinister.mp3", 5.0,
              "Sinister music cue for Traitor recruitment",
              "sinister, dark, recruitment, joining evil",
              "generate_sinister_sting"),
    AudioSpec("mission_success_cheer.mp3", 3.0,
              "Celebratory sound for successful mission",
              "success sound, celebration, achievement",
              "generate_success_sound"),
    AudioSpec("mission_fail_disappointment.mp3", 3.0,
              "Disappointment sound for failed mission",
              "failure sound, disappointment, defeat",
              "generate_failure_sound"),
    AudioSpec("vote_cast_confirm.mp3", 1.0,
              "Confirmation sound for vote being cast",
              "UI sound, confirmation, click",
              "generate_confirm_sound"),
    AudioSpec("clock_tick_tension.mp3", 10.0,
              "Ticking clock for time pressure moments",
              "clock ticking, tension, countdown",
              "generate_clock_tick"),
    AudioSpec("shield_protect.mp3", 2.0,
              "Magical protection sound for Shield activation",
              "shield, protection, magic, deflect",
              "generate_shield_sound"),
    AudioSpec("dramatic_pause_whoosh.mp3", 2.0,
              "Whoosh sound for dramatic transitions",
              "whoosh, transition, dramatic pause",
              "generate_whoosh"),
    AudioSpec("gavel_final.mp3", 1.5,
              "Gavel bang for final decision moments",
              "gavel, bang, decision, final",
              "generate_gavel"),
    AudioSpec("heartbeat_intense.mp3", 10.0,
              "Intense heartbeat for high-tension moments",
              "heartbeat, tension, anxiety, pulse",
              "generate_heartbeat"),
    AudioSpec("whisper_voices.mp3", 5.0,
              "Eerie whisper sounds for Traitor scenes",
              "whispers, eerie, conspiracy, secrets",
              "generate_whispers"),
]

AMBIENT_SPECS = [
    AudioSpec("castle_atmosphere.mp3", 60.0,
              "General castle ambiance (stone, echoes, distant sounds)",
              "castle ambiance, stone halls, medieval",
              "generate_castle_ambient"),
    AudioSpec("fireplace_crackle.mp3", 60.0,
              "Cozy fireplace crackling for social scenes",
              "fireplace, fire crackling, cozy",
              "generate_fire_ambient"),
    AudioSpec("wind_howl_cold.mp3", 60.0,
              "Cold wind howling for outdoor/turret scenes",
              "wind, howling, cold, desolate",
              "generate_wind_ambient"),
    AudioSpec("clock_tick_loop.mp3", 30.0,
              "Grandfather clock ticking loop",
              "clock, ticking, grandfather clock",
              "generate_clock_loop"),
    AudioSpec("night_crickets.mp3", 60.0,
              "Nighttime cricket sounds for evening scenes",
              "crickets, night, nature, evening",
              "generate_crickets_ambient"),
    AudioSpec("turret_dungeon.mp3", 60.0,
              "Dark dungeon/turret ambiance with drips and creaks",
              "dungeon, dripping, creaking, dark",
              "generate_dungeon_ambient"),
    AudioSpec("roundtable_room_tone.mp3", 30.0,
              "Quiet room tone with distant murmurs",
              "room tone, murmur, quiet crowd",
              "generate_room_tone"),
]


# ============================================================================
# AUDIO GENERATION UTILITIES
# ============================================================================

def normalize_audio(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """Normalize audio to target dB level."""
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        target_linear = 10 ** (target_db / 20)
        audio = audio * (target_linear / max_val)
    return np.clip(audio, -1.0, 1.0)


def apply_envelope(
    audio: np.ndarray,
    attack: float = 0.01,
    decay: float = 0.1,
    sustain: float = 0.7,
    release: float = 0.3,
    sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """Apply ADSR envelope to audio."""
    length = len(audio)
    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    release_samples = int(release * sample_rate)
    sustain_samples = length - attack_samples - decay_samples - release_samples

    if sustain_samples < 0:
        # Adjust for short audio
        attack_samples = int(length * 0.1)
        decay_samples = int(length * 0.1)
        release_samples = int(length * 0.3)
        sustain_samples = length - attack_samples - decay_samples - release_samples
        sustain_samples = max(0, sustain_samples)

    envelope = np.concatenate([
        np.linspace(0, 1, attack_samples),
        np.linspace(1, sustain, decay_samples),
        np.ones(sustain_samples) * sustain,
        np.linspace(sustain, 0, release_samples),
    ])

    # Ensure envelope matches audio length
    if len(envelope) < length:
        envelope = np.pad(envelope, (0, length - len(envelope)))
    elif len(envelope) > length:
        envelope = envelope[:length]

    return audio * envelope


def generate_sine(freq: float, duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a sine wave."""
    t = np.linspace(0, duration, int(duration * sample_rate), False)
    return np.sin(2 * np.pi * freq * t)


def generate_noise(duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate white noise."""
    samples = int(duration * sample_rate)
    return np.random.uniform(-1, 1, samples)


def lowpass_filter(audio: np.ndarray, cutoff: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply simple lowpass filter using moving average (no scipy needed)."""
    # Use FFT-based filtering for simplicity
    nyquist = sample_rate / 2
    normalized_cutoff = cutoff / nyquist

    # Simple averaging approximation - window size inversely proportional to cutoff
    window_size = max(1, int(sample_rate / cutoff / 4))
    kernel = np.ones(window_size) / window_size
    return np.convolve(audio, kernel, mode='same')


def highpass_filter(audio: np.ndarray, cutoff: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply highpass filter (subtract lowpass from original)."""
    lowpassed = lowpass_filter(audio, cutoff, sample_rate)
    return audio - lowpassed


def bandpass_filter(audio: np.ndarray, low: float, high: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply bandpass filter (lowpass then highpass)."""
    lowpassed = lowpass_filter(audio, high, sample_rate)
    return highpass_filter(lowpassed, low, sample_rate)


def mix_audio(*tracks: np.ndarray, weights: Optional[List[float]] = None) -> np.ndarray:
    """Mix multiple audio tracks together."""
    max_len = max(len(t) for t in tracks)
    if weights is None:
        weights = [1.0 / len(tracks)] * len(tracks)

    mixed = np.zeros(max_len)
    for track, weight in zip(tracks, weights):
        padded = np.pad(track, (0, max_len - len(track)))
        mixed += padded * weight

    return np.clip(mixed, -1.0, 1.0)


def loop_audio(audio: np.ndarray, target_duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Loop audio to reach target duration with crossfade."""
    target_samples = int(target_duration * sample_rate)
    if len(audio) >= target_samples:
        return audio[:target_samples]

    # Create looped version with crossfade
    crossfade_samples = min(int(0.1 * sample_rate), len(audio) // 4)
    result = np.zeros(target_samples)

    pos = 0
    while pos < target_samples:
        remaining = target_samples - pos
        chunk_len = min(len(audio), remaining)

        if pos > 0 and crossfade_samples > 0:
            # Crossfade
            fade_len = min(crossfade_samples, chunk_len, target_samples - pos)
            fade_out = np.linspace(1, 0, fade_len)
            fade_in = np.linspace(0, 1, fade_len)
            result[pos:pos + fade_len] = (
                result[pos:pos + fade_len] * fade_out +
                audio[:fade_len] * fade_in
            )
            result[pos + fade_len:pos + chunk_len] = audio[fade_len:chunk_len]
        else:
            result[pos:pos + chunk_len] = audio[:chunk_len]

        pos += len(audio) - crossfade_samples

    return result


# ============================================================================
# MUSIC GENERATORS
# ============================================================================

def generate_uneasy_music(duration: float) -> np.ndarray:
    """Generate tense, uneasy background music."""
    # Minor key drone with dissonant intervals
    base_freq = 110  # A2
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Fundamental + minor third + tritone for tension
    drone = (
        0.3 * np.sin(2 * np.pi * base_freq * t) +
        0.2 * np.sin(2 * np.pi * base_freq * 1.2 * t) +  # Minor third
        0.15 * np.sin(2 * np.pi * base_freq * 1.414 * t) +  # Tritone
        0.1 * np.sin(2 * np.pi * base_freq * 2 * t)  # Octave
    )

    # Add slow tremolo
    tremolo = 0.3 * np.sin(2 * np.pi * 0.5 * t) + 0.7
    drone *= tremolo

    # Add filtered noise layer
    noise = generate_noise(duration) * 0.05
    noise = lowpass_filter(noise, 500)

    return normalize_audio(mix_audio(drone, noise, weights=[0.8, 0.2]))


def generate_pulse_music(duration: float) -> np.ndarray:
    """Generate energetic pulsing music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
    bpm = 120
    beat_freq = bpm / 60

    # Kick-like pulse
    kick_env = np.abs(np.sin(2 * np.pi * beat_freq * t)) ** 4
    kick = np.sin(2 * np.pi * 60 * t) * kick_env

    # Synth pad
    pad = (
        0.2 * np.sin(2 * np.pi * 220 * t) +
        0.15 * np.sin(2 * np.pi * 330 * t) +
        0.1 * np.sin(2 * np.pi * 440 * t)
    )

    # Hi-hat like high frequency
    hihat = highpass_filter(generate_noise(duration), 8000) * 0.1
    hihat_env = np.abs(np.sin(2 * np.pi * beat_freq * 2 * t)) ** 2
    hihat *= hihat_env

    return normalize_audio(mix_audio(kick, pad, hihat, weights=[0.5, 0.3, 0.2]))


def generate_whisper_music(duration: float) -> np.ndarray:
    """Generate conspiratorial whisper-like music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Ethereal pad with slow modulation
    lfo = np.sin(2 * np.pi * 0.1 * t)
    pad = (
        0.3 * np.sin(2 * np.pi * (200 + 10 * lfo) * t) +
        0.2 * np.sin(2 * np.pi * (300 + 15 * lfo) * t)
    )

    # Whisper-like filtered noise
    whisper = bandpass_filter(generate_noise(duration), 1000, 4000) * 0.1
    whisper_env = 0.3 + 0.2 * np.sin(2 * np.pi * 0.2 * t)
    whisper *= whisper_env

    return normalize_audio(mix_audio(pad, whisper, weights=[0.7, 0.3]))


def generate_suspicion_music(duration: float) -> np.ndarray:
    """Generate building suspicion music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Rising pitch over time
    freq_ramp = np.linspace(100, 200, len(t))
    base = np.sin(2 * np.pi * freq_ramp * t / SAMPLE_RATE * np.cumsum(np.ones(len(t))))

    # Actually, simpler approach - oscillator with rising frequency
    base = 0.3 * np.sin(2 * np.pi * np.cumsum(freq_ramp) / SAMPLE_RATE)

    # Tension building harmonics
    harmonic = 0.2 * np.sin(2 * np.pi * np.cumsum(freq_ramp * 1.5) / SAMPLE_RATE)

    # Filtered noise that increases
    noise = generate_noise(duration)
    noise = lowpass_filter(noise, 800)
    noise_env = np.linspace(0.02, 0.1, len(t))
    noise *= noise_env

    return normalize_audio(mix_audio(base, harmonic, noise, weights=[0.5, 0.3, 0.2]))


def generate_darkness_music(duration: float) -> np.ndarray:
    """Generate dark, menacing music for Turret phase."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Very low drone
    drone = (
        0.4 * np.sin(2 * np.pi * 55 * t) +  # Low A
        0.3 * np.sin(2 * np.pi * 82.5 * t) +  # E (fifth)
        0.2 * np.sin(2 * np.pi * 65.4 * t)  # C (minor third from A)
    )

    # Ominous pulsing
    pulse = np.sin(2 * np.pi * 0.3 * t) * 0.3 + 0.7
    drone *= pulse

    # Dark rumble
    rumble = lowpass_filter(generate_noise(duration), 100) * 0.15

    return normalize_audio(mix_audio(drone, rumble, weights=[0.8, 0.2]))


def generate_climax_music(duration: float) -> np.ndarray:
    """Generate epic climactic music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Major chord progression feel
    fundamental = 220  # A3
    chord = (
        0.3 * np.sin(2 * np.pi * fundamental * t) +
        0.25 * np.sin(2 * np.pi * fundamental * 1.25 * t) +  # Major third
        0.2 * np.sin(2 * np.pi * fundamental * 1.5 * t) +  # Fifth
        0.15 * np.sin(2 * np.pi * fundamental * 2 * t)  # Octave
    )

    # Building intensity
    intensity = np.linspace(0.5, 1.0, len(t))
    chord *= intensity

    # Rhythmic element
    beat = np.abs(np.sin(2 * np.pi * 2 * t)) ** 2 * 0.3 + 0.7
    chord *= beat

    return normalize_audio(chord)


def generate_tension_build(duration: float) -> np.ndarray:
    """Generate short tension building cue."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Rising tone
    freq = np.linspace(100, 400, len(t))
    tone = 0.4 * np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)

    # Increasing intensity
    env = np.linspace(0.3, 1.0, len(t))
    tone *= env

    # Add noise riser
    noise = highpass_filter(generate_noise(duration), 2000)
    noise_env = np.linspace(0, 0.2, len(t))
    noise *= noise_env

    return normalize_audio(mix_audio(tone, noise, weights=[0.7, 0.3]))


def generate_dramatic_hit(duration: float) -> np.ndarray:
    """Generate dramatic musical hit."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Impact hit with fast decay
    freq = 100
    hit = (
        0.5 * np.sin(2 * np.pi * freq * t) +
        0.3 * np.sin(2 * np.pi * freq * 2 * t) +
        0.2 * np.sin(2 * np.pi * freq * 3 * t)
    )

    # Fast attack, long decay envelope
    env = np.exp(-t * 3)
    hit *= env

    # Add crash noise
    crash = highpass_filter(generate_noise(duration), 3000) * 0.3
    crash *= np.exp(-t * 5)

    return normalize_audio(mix_audio(hit, crash, weights=[0.6, 0.4]))


def generate_somber_music(duration: float) -> np.ndarray:
    """Generate sad, reflective music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Slow, sad melody simulation with minor intervals
    base_freq = 220
    melody = (
        0.3 * np.sin(2 * np.pi * base_freq * t) +
        0.2 * np.sin(2 * np.pi * base_freq * 1.2 * t) +  # Minor third
        0.15 * np.sin(2 * np.pi * base_freq * 1.5 * t)  # Fifth
    )

    # Slow tremolo
    trem = 0.15 * np.sin(2 * np.pi * 0.3 * t) + 0.85
    melody *= trem

    # Gentle envelope
    env = apply_envelope(np.ones(len(t)), attack=2.0, decay=1.0, sustain=0.6, release=3.0)
    melody *= env

    return normalize_audio(melody)


def generate_mysterious_music(duration: float) -> np.ndarray:
    """Generate mysterious ambient music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Ethereal tones with slow modulation
    lfo1 = np.sin(2 * np.pi * 0.05 * t)
    lfo2 = np.sin(2 * np.pi * 0.07 * t)

    tone1 = 0.3 * np.sin(2 * np.pi * (300 + 20 * lfo1) * t)
    tone2 = 0.2 * np.sin(2 * np.pi * (450 + 30 * lfo2) * t)

    # Pad
    pad = tone1 + tone2

    # Filtered noise bed
    noise = bandpass_filter(generate_noise(duration), 500, 2000) * 0.1

    return normalize_audio(mix_audio(pad, noise, weights=[0.8, 0.2]))


def generate_triumphant_music(duration: float) -> np.ndarray:
    """Generate victory fanfare music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Major chord
    base = 330  # E4
    fanfare = (
        0.35 * np.sin(2 * np.pi * base * t) +
        0.3 * np.sin(2 * np.pi * base * 1.25 * t) +  # Major third
        0.25 * np.sin(2 * np.pi * base * 1.5 * t) +  # Fifth
        0.15 * np.sin(2 * np.pi * base * 2 * t)  # Octave
    )

    # Brass-like envelope
    env = apply_envelope(np.ones(len(t)), attack=0.1, decay=0.2, sustain=0.8, release=0.5)
    fanfare *= env

    return normalize_audio(fanfare)


def generate_neutral_music(duration: float) -> np.ndarray:
    """Generate neutral background music."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Very subtle pad
    pad = (
        0.2 * np.sin(2 * np.pi * 220 * t) +
        0.15 * np.sin(2 * np.pi * 330 * t)
    )

    # Subtle modulation
    mod = 0.1 * np.sin(2 * np.pi * 0.1 * t) + 0.9
    pad *= mod

    # Low volume filtered noise
    noise = lowpass_filter(generate_noise(duration), 1000) * 0.03

    return normalize_audio(mix_audio(pad, noise, weights=[0.9, 0.1]), target_db=-12.0)


# ============================================================================
# SFX GENERATORS
# ============================================================================

def generate_horror_sting(duration: float) -> np.ndarray:
    """Generate horror reveal sting."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Dissonant cluster with fast attack
    sting = (
        0.4 * np.sin(2 * np.pi * 200 * t) +
        0.35 * np.sin(2 * np.pi * 283 * t) +  # Tritone
        0.3 * np.sin(2 * np.pi * 237 * t) +  # Minor second up
        0.25 * np.sin(2 * np.pi * 150 * t)
    )

    # Sharp attack, decay
    env = np.exp(-t * 2) * (1 - np.exp(-t * 50))
    sting *= env

    # Noise burst
    noise = highpass_filter(generate_noise(duration), 2000) * 0.3
    noise *= np.exp(-t * 4)

    return normalize_audio(mix_audio(sting, noise, weights=[0.7, 0.3]))


def generate_drumroll(duration: float) -> np.ndarray:
    """Generate tension drumroll."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Simulate snare roll with filtered noise
    roll = bandpass_filter(generate_noise(duration), 200, 4000)

    # Amplitude modulation for roll effect (increasing frequency)
    roll_freq = np.linspace(10, 30, len(t))
    roll_env = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(roll_freq) / SAMPLE_RATE)
    roll *= roll_env

    # Building intensity
    intensity = np.linspace(0.3, 1.0, len(t))
    roll *= intensity

    return normalize_audio(roll)


def generate_triumph_sting(duration: float) -> np.ndarray:
    """Generate triumphant revelation sting."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Major chord burst
    base = 440
    sting = (
        0.4 * np.sin(2 * np.pi * base * t) +
        0.35 * np.sin(2 * np.pi * base * 1.25 * t) +
        0.3 * np.sin(2 * np.pi * base * 1.5 * t)
    )

    env = apply_envelope(np.ones(len(t)), attack=0.05, decay=0.3, sustain=0.5, release=0.5)
    sting *= env

    return normalize_audio(sting)


def generate_tragic_sting(duration: float) -> np.ndarray:
    """Generate tragic mistake sting."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Minor/diminished feel
    base = 220
    sting = (
        0.4 * np.sin(2 * np.pi * base * t) +
        0.3 * np.sin(2 * np.pi * base * 1.2 * t) +  # Minor third
        0.25 * np.sin(2 * np.pi * base * 1.414 * t)  # Tritone
    )

    # Falling pitch slightly
    pitch_fall = np.linspace(1.0, 0.95, len(t))
    sting *= pitch_fall

    env = apply_envelope(np.ones(len(t)), attack=0.1, decay=0.5, sustain=0.4, release=1.0)
    sting *= env

    return normalize_audio(sting)


def generate_sinister_sting(duration: float) -> np.ndarray:
    """Generate sinister recruitment sting."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Low ominous tone with rise
    freq = np.linspace(80, 150, len(t))
    tone = 0.4 * np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)

    # Dissonant overtone
    overtone = 0.3 * np.sin(2 * np.pi * np.cumsum(freq * 1.414) / SAMPLE_RATE)

    sting = tone + overtone

    env = apply_envelope(np.ones(len(t)), attack=0.3, decay=0.5, sustain=0.6, release=0.8)
    sting *= env

    return normalize_audio(sting)


def generate_success_sound(duration: float) -> np.ndarray:
    """Generate success/achievement sound."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Rising major arpeggio feel
    freqs = [330, 415, 494, 660]  # E major arpeggio
    sound = np.zeros(len(t))

    for i, freq in enumerate(freqs):
        start = int(i * len(t) / (len(freqs) + 1))
        end = min(start + int(len(t) / 2), len(t))
        note = np.zeros(len(t))
        note[start:end] = np.sin(2 * np.pi * freq * t[start:end])
        note[start:end] *= np.exp(-(t[start:end] - t[start]) * 3)
        sound += 0.3 * note

    return normalize_audio(sound)


def generate_failure_sound(duration: float) -> np.ndarray:
    """Generate failure/disappointment sound."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Descending tones
    freq = np.linspace(400, 150, len(t))
    sound = 0.4 * np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)

    env = np.exp(-t * 1.5)
    sound *= env

    return normalize_audio(sound)


def generate_confirm_sound(duration: float) -> np.ndarray:
    """Generate UI confirmation click sound."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Short click
    click = np.sin(2 * np.pi * 1000 * t) * 0.5
    click += np.sin(2 * np.pi * 1500 * t) * 0.3

    env = np.exp(-t * 20)
    click *= env

    return normalize_audio(click)


def generate_clock_tick(duration: float) -> np.ndarray:
    """Generate ticking clock tension sound."""
    samples = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, samples, False)

    # Create individual ticks
    ticks_per_sec = 1
    tick_samples = int(SAMPLE_RATE / ticks_per_sec / 2)

    sound = np.zeros(samples)

    for i in range(int(duration * ticks_per_sec)):
        start = int(i * SAMPLE_RATE / ticks_per_sec)
        if start + tick_samples < samples:
            # Short click for tick
            tick_t = np.linspace(0, tick_samples / SAMPLE_RATE, tick_samples)
            tick = np.sin(2 * np.pi * 2000 * tick_t) * np.exp(-tick_t * 50)
            sound[start:start + tick_samples] += 0.4 * tick

    return normalize_audio(sound)


def generate_shield_sound(duration: float) -> np.ndarray:
    """Generate magical shield protection sound."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Shimmering high tones
    shimmer = (
        0.3 * np.sin(2 * np.pi * 800 * t) +
        0.25 * np.sin(2 * np.pi * 1200 * t) +
        0.2 * np.sin(2 * np.pi * 1600 * t)
    )

    # Fast tremolo for shimmer
    trem = 0.3 * np.sin(2 * np.pi * 20 * t) + 0.7
    shimmer *= trem

    env = apply_envelope(np.ones(len(t)), attack=0.05, decay=0.2, sustain=0.5, release=0.5)
    shimmer *= env

    return normalize_audio(shimmer)


def generate_whoosh(duration: float) -> np.ndarray:
    """Generate dramatic whoosh transition sound."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Noise sweep
    noise = generate_noise(duration)

    # Filter sweep
    center_freq = 500 + 3000 * np.sin(np.pi * t / duration)

    # Approximate with multiple filtered versions blended
    low = lowpass_filter(noise, 1000)
    mid = bandpass_filter(noise, 1000, 4000)
    high = highpass_filter(noise, 4000)

    blend = t / duration
    whoosh = low * (1 - blend) + mid * np.sin(np.pi * blend) + high * blend

    env = np.sin(np.pi * t / duration)
    whoosh *= env

    return normalize_audio(whoosh * 0.5)


def generate_gavel(duration: float) -> np.ndarray:
    """Generate gavel bang sound."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Impact
    impact = np.sin(2 * np.pi * 150 * t) * 0.5
    impact += lowpass_filter(generate_noise(duration), 500) * 0.3

    env = np.exp(-t * 10)
    impact *= env

    return normalize_audio(impact)


def generate_heartbeat(duration: float) -> np.ndarray:
    """Generate intense heartbeat sound."""
    samples = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, samples, False)

    # Heart rate around 80 bpm (faster = more tension)
    bpm = 100
    beat_period = 60 / bpm

    sound = np.zeros(samples)

    for beat_num in range(int(duration / beat_period)):
        beat_start = int(beat_num * beat_period * SAMPLE_RATE)

        # Lub (first beat)
        lub_samples = int(0.1 * SAMPLE_RATE)
        if beat_start + lub_samples < samples:
            lub_t = np.linspace(0, 0.1, lub_samples)
            lub = np.sin(2 * np.pi * 60 * lub_t) * np.exp(-lub_t * 30)
            sound[beat_start:beat_start + lub_samples] += 0.5 * lub

        # Dub (second beat, slightly after)
        dub_start = beat_start + int(0.15 * SAMPLE_RATE)
        dub_samples = int(0.08 * SAMPLE_RATE)
        if dub_start + dub_samples < samples:
            dub_t = np.linspace(0, 0.08, dub_samples)
            dub = np.sin(2 * np.pi * 50 * dub_t) * np.exp(-dub_t * 35)
            sound[dub_start:dub_start + dub_samples] += 0.4 * dub

    return normalize_audio(sound)


def generate_whispers(duration: float) -> np.ndarray:
    """Generate eerie whisper sounds."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Filtered noise to simulate whispers
    whisper = bandpass_filter(generate_noise(duration), 800, 3000)

    # Amplitude modulation for "words"
    words = np.abs(np.sin(2 * np.pi * 0.5 * t)) ** 0.5
    whisper *= words * 0.3

    # Add some sibilance
    sibilance = highpass_filter(generate_noise(duration), 5000) * 0.1
    sibilance *= words

    return normalize_audio(mix_audio(whisper, sibilance, weights=[0.8, 0.2]))


# ============================================================================
# AMBIENT GENERATORS
# ============================================================================

def generate_castle_ambient(duration: float) -> np.ndarray:
    """Generate castle ambiance with stone echoes."""
    # Base low rumble
    rumble = lowpass_filter(generate_noise(duration), 150) * 0.1

    # Distant echoes (random impulses with reverb-like decay)
    samples = int(duration * SAMPLE_RATE)
    echoes = np.zeros(samples)

    for _ in range(int(duration / 5)):  # One echo every ~5 seconds
        pos = np.random.randint(0, samples - SAMPLE_RATE)
        echo_len = int(0.5 * SAMPLE_RATE)
        echo_t = np.linspace(0, 0.5, echo_len)
        echo = bandpass_filter(generate_noise(0.5), 200, 2000) * np.exp(-echo_t * 4)
        echoes[pos:pos + echo_len] += 0.2 * echo

    return normalize_audio(mix_audio(rumble, echoes, weights=[0.7, 0.3]), target_db=-15.0)


def generate_fire_ambient(duration: float) -> np.ndarray:
    """Generate fireplace crackling."""
    samples = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, samples, False)

    # Base fire rumble
    rumble = lowpass_filter(generate_noise(duration), 300) * 0.15

    # Crackles (random clicks)
    crackles = np.zeros(samples)
    for _ in range(int(duration * 3)):  # ~3 crackles per second
        pos = np.random.randint(0, samples - 1000)
        crackle_len = np.random.randint(100, 500)
        crackle = highpass_filter(generate_noise(crackle_len / SAMPLE_RATE), 2000)
        crackle *= np.exp(-np.linspace(0, 1, len(crackle)) * 10)
        crackles[pos:pos + len(crackle)] += 0.3 * crackle * np.random.uniform(0.5, 1.0)

    return normalize_audio(mix_audio(rumble, crackles, weights=[0.6, 0.4]), target_db=-12.0)


def generate_wind_ambient(duration: float) -> np.ndarray:
    """Generate cold wind howling."""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)

    # Wind base
    wind = lowpass_filter(generate_noise(duration), 800)

    # Slow amplitude modulation for gusts
    gusts = 0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 0.1 * t + np.random.random() * 2 * np.pi))
    wind *= gusts

    # Howling tones
    howl_freq = 400 + 100 * np.sin(2 * np.pi * 0.05 * t)
    howl = 0.1 * np.sin(2 * np.pi * np.cumsum(howl_freq) / SAMPLE_RATE)

    return normalize_audio(mix_audio(wind, howl, weights=[0.8, 0.2]), target_db=-12.0)


def generate_clock_loop(duration: float) -> np.ndarray:
    """Generate grandfather clock ticking loop."""
    return generate_clock_tick(duration)  # Reuse clock tick generator


def generate_crickets_ambient(duration: float) -> np.ndarray:
    """Generate nighttime cricket sounds."""
    samples = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, samples, False)

    # Multiple cricket "voices"
    crickets = np.zeros(samples)

    for _ in range(5):  # 5 different crickets
        freq = np.random.uniform(3000, 5000)
        chirp_rate = np.random.uniform(4, 8)
        phase = np.random.random() * 2 * np.pi

        chirp_env = 0.5 + 0.5 * np.sin(2 * np.pi * chirp_rate * t + phase)
        chirp_env = np.where(chirp_env > 0.7, chirp_env, 0)

        cricket = np.sin(2 * np.pi * freq * t) * chirp_env * 0.1
        crickets += cricket

    return normalize_audio(crickets, target_db=-15.0)


def generate_dungeon_ambient(duration: float) -> np.ndarray:
    """Generate dark dungeon ambiance."""
    samples = int(duration * SAMPLE_RATE)

    # Deep rumble
    rumble = lowpass_filter(generate_noise(duration), 100) * 0.1

    # Dripping water
    drips = np.zeros(samples)
    for _ in range(int(duration / 3)):
        pos = np.random.randint(0, samples - 2000)
        drip_len = int(0.05 * SAMPLE_RATE)
        drip_t = np.linspace(0, 0.05, drip_len)
        drip = np.sin(2 * np.pi * 800 * drip_t) * np.exp(-drip_t * 50)
        drips[pos:pos + drip_len] += 0.3 * drip

    # Creaking
    creaks = np.zeros(samples)
    for _ in range(int(duration / 10)):
        pos = np.random.randint(0, samples - SAMPLE_RATE)
        creak_len = int(0.5 * SAMPLE_RATE)
        creak_t = np.linspace(0, 0.5, creak_len)
        creak_freq = np.linspace(100, 300, creak_len) + 50 * np.sin(2 * np.pi * 10 * creak_t)
        creak = 0.15 * np.sin(2 * np.pi * np.cumsum(creak_freq) / SAMPLE_RATE)
        creak *= np.sin(np.pi * creak_t / 0.5)
        creaks[pos:pos + creak_len] += creak

    return normalize_audio(
        mix_audio(rumble, drips, creaks, weights=[0.5, 0.3, 0.2]),
        target_db=-15.0
    )


def generate_room_tone(duration: float) -> np.ndarray:
    """Generate quiet room tone with distant murmurs."""
    # Very quiet noise floor
    room = lowpass_filter(generate_noise(duration), 500) * 0.02

    # Occasional distant murmurs
    samples = int(duration * SAMPLE_RATE)
    murmurs = np.zeros(samples)

    for _ in range(int(duration / 5)):
        pos = np.random.randint(0, samples - SAMPLE_RATE)
        murmur_len = int(np.random.uniform(0.5, 1.5) * SAMPLE_RATE)
        murmur = bandpass_filter(generate_noise(murmur_len / SAMPLE_RATE), 200, 800)
        murmur *= np.sin(np.pi * np.linspace(0, 1, len(murmur)))
        murmurs[pos:pos + len(murmur)] += 0.05 * murmur

    return normalize_audio(mix_audio(room, murmurs, weights=[0.7, 0.3]), target_db=-20.0)


# ============================================================================
# FILE EXPORT
# ============================================================================

def audio_to_wav(audio: np.ndarray, filepath: str, sample_rate: int = SAMPLE_RATE) -> None:
    """Save audio array as WAV file using stdlib wave module."""
    # Convert to 16-bit integer
    audio_int = (audio * 32767).astype(np.int16)

    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int.tobytes())


def convert_wav_to_mp3(wav_path: str, mp3_path: str) -> bool:
    """Convert WAV to MP3 using ffmpeg."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', wav_path, '-codec:a', 'libmp3lame', '-b:a', '192k', mp3_path],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("Warning: ffmpeg not found. Keeping WAV files instead of MP3.")
        return False


def generate_and_save(
    spec: AudioSpec,
    output_dir: str,
    generators: dict
) -> Tuple[bool, str]:
    """Generate audio and save to file.

    Returns:
        Tuple of (success, message)
    """
    generator_name = spec.generator
    if generator_name not in generators:
        return False, f"Unknown generator: {generator_name}"

    try:
        # Generate audio
        audio = generators[generator_name](spec.duration_sec)

        # For ambient/music, make it loop-friendly
        if spec.duration_sec >= 30:
            audio = loop_audio(audio, spec.duration_sec)

        # Save as WAV first
        base_name = spec.filename.replace('.mp3', '')
        wav_path = os.path.join(output_dir, f"{base_name}.wav")
        mp3_path = os.path.join(output_dir, spec.filename)

        audio_to_wav(audio, wav_path)

        # Try to convert to MP3
        if convert_wav_to_mp3(wav_path, mp3_path):
            os.remove(wav_path)  # Clean up WAV
            return True, f"Created {spec.filename}"
        else:
            # Keep as WAV, rename
            wav_final = os.path.join(output_dir, f"{base_name}.wav")
            return True, f"Created {base_name}.wav (MP3 conversion failed)"

    except Exception as e:
        return False, f"Failed to generate {spec.filename}: {e}"


def generate_manifest(output_path: str) -> None:
    """Generate audio manifest documentation."""
    manifest = """# TraitorSim Audio Assets Manifest

## Overview

These are **synthesized placeholder audio assets** generated for development and testing.
They are functional but should be replaced with professional audio for production.

## Recommended Professional Sources

1. **FreeSound.org** - CC0/CC-BY licensed sound effects and ambiance
2. **BBC Sound Effects** - Free for non-commercial use (archive.org/details/BBCSoundEffects)
3. **YouTube Audio Library** - Free music for content creators
4. **Epidemic Sound** - Professional subscription service
5. **Artlist.io** - Premium royalty-free music

## Asset Categories

### Music Cues (assets/music/)

| File | Duration | Description | Search Keywords |
|------|----------|-------------|-----------------|
"""

    for spec in MUSIC_SPECS:
        manifest += f"| `{spec.filename}` | {spec.duration_sec}s | {spec.description} | {spec.replacement_keywords} |\n"

    manifest += """
### Sound Effects (assets/sfx/)

| File | Duration | Description | Search Keywords |
|------|----------|-------------|-----------------|
"""

    for spec in SFX_SPECS:
        manifest += f"| `{spec.filename}` | {spec.duration_sec}s | {spec.description} | {spec.replacement_keywords} |\n"

    manifest += """
### Ambient Sounds (assets/ambient/)

| File | Duration | Description | Search Keywords |
|------|----------|-------------|-----------------|
"""

    for spec in AMBIENT_SPECS:
        manifest += f"| `{spec.filename}` | {spec.duration_sec}s | {spec.description} | {spec.replacement_keywords} |\n"

    manifest += """
## Technical Specifications

- **Format**: MP3 (192kbps) or WAV (16-bit, 44.1kHz if ffmpeg unavailable)
- **Channels**: Mono (can be mixed to stereo in audio_assembler.py)
- **Normalization**: -3 dB peak for music/SFX, -12 to -20 dB for ambient

## Replacement Guidelines

When replacing placeholder audio:

1. **Maintain exact filenames** - The audio_assembler.py references these by name
2. **Match durations approximately** - Ambient/music loops can be any length (will be looped)
3. **Use consistent loudness** - Music: -14 LUFS, SFX: -10 LUFS, Ambient: -20 LUFS
4. **Include loop points** - For ambient sounds, ensure seamless looping

## Generation Script

These files were generated by `scripts/generate_audio_assets.py` using:
- NumPy for waveform synthesis
- SciPy for filtering and signal processing
- FFmpeg for MP3 encoding

To regenerate: `python scripts/generate_audio_assets.py`
"""

    with open(output_path, 'w') as f:
        f.write(manifest)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Generate all audio assets."""
    # Build generator lookup
    generators = {
        # Music
        "generate_uneasy_music": generate_uneasy_music,
        "generate_pulse_music": generate_pulse_music,
        "generate_whisper_music": generate_whisper_music,
        "generate_suspicion_music": generate_suspicion_music,
        "generate_darkness_music": generate_darkness_music,
        "generate_climax_music": generate_climax_music,
        "generate_tension_build": generate_tension_build,
        "generate_dramatic_hit": generate_dramatic_hit,
        "generate_somber_music": generate_somber_music,
        "generate_mysterious_music": generate_mysterious_music,
        "generate_triumphant_music": generate_triumphant_music,
        "generate_neutral_music": generate_neutral_music,
        # SFX
        "generate_horror_sting": generate_horror_sting,
        "generate_drumroll": generate_drumroll,
        "generate_triumph_sting": generate_triumph_sting,
        "generate_tragic_sting": generate_tragic_sting,
        "generate_sinister_sting": generate_sinister_sting,
        "generate_success_sound": generate_success_sound,
        "generate_failure_sound": generate_failure_sound,
        "generate_confirm_sound": generate_confirm_sound,
        "generate_clock_tick": generate_clock_tick,
        "generate_shield_sound": generate_shield_sound,
        "generate_whoosh": generate_whoosh,
        "generate_gavel": generate_gavel,
        "generate_heartbeat": generate_heartbeat,
        "generate_whispers": generate_whispers,
        # Ambient
        "generate_castle_ambient": generate_castle_ambient,
        "generate_fire_ambient": generate_fire_ambient,
        "generate_wind_ambient": generate_wind_ambient,
        "generate_clock_loop": generate_clock_loop,
        "generate_crickets_ambient": generate_crickets_ambient,
        "generate_dungeon_ambient": generate_dungeon_ambient,
        "generate_room_tone": generate_room_tone,
    }

    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    music_dir = os.path.join(assets_dir, "music")
    sfx_dir = os.path.join(assets_dir, "sfx")
    ambient_dir = os.path.join(assets_dir, "ambient")

    # Create directories
    for d in [music_dir, sfx_dir, ambient_dir]:
        os.makedirs(d, exist_ok=True)

    print("=" * 60)
    print("TraitorSim Audio Asset Generator")
    print("=" * 60)

    # Check for ffmpeg
    has_ffmpeg = shutil.which('ffmpeg') is not None
    if has_ffmpeg:
        print("✓ ffmpeg found - will generate MP3 files")
    else:
        print("⚠ ffmpeg not found - will generate WAV files instead")

    # Generate music
    print(f"\n📀 Generating {len(MUSIC_SPECS)} music cues...")
    for spec in MUSIC_SPECS:
        success, msg = generate_and_save(spec, music_dir, generators)
        status = "✓" if success else "✗"
        print(f"  {status} {msg}")

    # Generate SFX
    print(f"\n🔊 Generating {len(SFX_SPECS)} sound effects...")
    for spec in SFX_SPECS:
        success, msg = generate_and_save(spec, sfx_dir, generators)
        status = "✓" if success else "✗"
        print(f"  {status} {msg}")

    # Generate ambient
    print(f"\n🌲 Generating {len(AMBIENT_SPECS)} ambient sounds...")
    for spec in AMBIENT_SPECS:
        success, msg = generate_and_save(spec, ambient_dir, generators)
        status = "✓" if success else "✗"
        print(f"  {status} {msg}")

    # Generate manifest
    manifest_path = os.path.join(assets_dir, "AUDIO_MANIFEST.md")
    generate_manifest(manifest_path)
    print(f"\n📋 Generated {manifest_path}")

    print("\n" + "=" * 60)
    print("Audio generation complete!")
    print(f"Total assets: {len(MUSIC_SPECS) + len(SFX_SPECS) + len(AMBIENT_SPECS)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
