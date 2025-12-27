# TraitorSim Audio Assets Manifest

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
| `breakfast_uneasy.mp3` | 60.0s | Tense, uneasy music for murder reveal at breakfast | suspenseful strings, minor key, building tension |
| `mission_pulse.mp3` | 90.0s | Energetic, pulsing music for mission challenges | action music, rhythmic, driving beat |
| `social_whispers.mp3` | 60.0s | Conspiratorial, whispery background for social phase | mysterious, subtle, intrigue music |
| `roundtable_suspicion.mp3` | 120.0s | Building suspicion music for voting phase | dramatic tension, rising stakes, orchestral |
| `turret_darkness.mp3` | 45.0s | Dark, menacing music for Traitor murder selection | horror elements, minor key, ominous |
| `finale_climax.mp3` | 60.0s | Epic climactic music for game finale | triumphant, dramatic crescendo, orchestral |
| `tension_build.mp3` | 30.0s | Short tension building cue | rising tension, suspenseful, building |
| `dramatic_hit.mp3` | 5.0s | Dramatic musical hit/sting | orchestra hit, dramatic reveal, impact |
| `somber_reflection.mp3` | 45.0s | Sad, reflective music for aftermath of deaths | melancholy, piano, strings, emotional |
| `mysterious_shadows.mp3` | 60.0s | Mysterious underscore for unknown events | mysterious, ambient, ethereal |
| `triumphant_brass.mp3` | 30.0s | Victory fanfare for successful outcomes | triumphant, brass, celebration, victory |
| `neutral_background.mp3` | 120.0s | Neutral background music for transitions | ambient, neutral, background, subtle |

### Sound Effects (assets/sfx/)

| File | Duration | Description | Search Keywords |
|------|----------|-------------|-----------------|
| `murder_reveal_sting.mp3` | 3.0s | Dramatic sting for murder reveal moment | horror sting, dramatic reveal, shock |
| `vote_drumroll.mp3` | 8.0s | Tension-building drumroll for vote counting | drumroll, tension, anticipation |
| `traitor_reveal_triumph.mp3` | 4.0s | Triumphant sting when Traitor is correctly banished | victory sting, revelation, triumph |
| `faithful_reveal_tragic.mp3` | 4.0s | Tragic sting when Faithful is wrongly banished | tragic sting, mistake, sad |
| `recruitment_sinister.mp3` | 5.0s | Sinister music cue for Traitor recruitment | sinister, dark, recruitment, joining evil |
| `mission_success_cheer.mp3` | 3.0s | Celebratory sound for successful mission | success sound, celebration, achievement |
| `mission_fail_disappointment.mp3` | 3.0s | Disappointment sound for failed mission | failure sound, disappointment, defeat |
| `vote_cast_confirm.mp3` | 1.0s | Confirmation sound for vote being cast | UI sound, confirmation, click |
| `clock_tick_tension.mp3` | 10.0s | Ticking clock for time pressure moments | clock ticking, tension, countdown |
| `shield_protect.mp3` | 2.0s | Magical protection sound for Shield activation | shield, protection, magic, deflect |
| `dramatic_pause_whoosh.mp3` | 2.0s | Whoosh sound for dramatic transitions | whoosh, transition, dramatic pause |
| `gavel_final.mp3` | 1.5s | Gavel bang for final decision moments | gavel, bang, decision, final |
| `heartbeat_intense.mp3` | 10.0s | Intense heartbeat for high-tension moments | heartbeat, tension, anxiety, pulse |
| `whisper_voices.mp3` | 5.0s | Eerie whisper sounds for Traitor scenes | whispers, eerie, conspiracy, secrets |

### Ambient Sounds (assets/ambient/)

| File | Duration | Description | Search Keywords |
|------|----------|-------------|-----------------|
| `castle_atmosphere.mp3` | 60.0s | General castle ambiance (stone, echoes, distant sounds) | castle ambiance, stone halls, medieval |
| `fireplace_crackle.mp3` | 60.0s | Cozy fireplace crackling for social scenes | fireplace, fire crackling, cozy |
| `wind_howl_cold.mp3` | 60.0s | Cold wind howling for outdoor/turret scenes | wind, howling, cold, desolate |
| `clock_tick_loop.mp3` | 30.0s | Grandfather clock ticking loop | clock, ticking, grandfather clock |
| `night_crickets.mp3` | 60.0s | Nighttime cricket sounds for evening scenes | crickets, night, nature, evening |
| `turret_dungeon.mp3` | 60.0s | Dark dungeon/turret ambiance with drips and creaks | dungeon, dripping, creaking, dark |
| `roundtable_room_tone.mp3` | 30.0s | Quiet room tone with distant murmurs | room tone, murmur, quiet crowd |

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
