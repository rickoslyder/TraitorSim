# TraitorSim Voice Integration Design

## Executive Summary

This document proposes a comprehensive voice integration strategy for TraitorSim using ElevenLabs' Text-to-Dialogue API (Eleven v3). Two primary modes are designed:

1. **Episode Mode** - Post-hoc narration of completed games as serialized audio drama
2. **HITL Mode** - Real-time voice interaction with 21 AI agents + 1 human player

---

## Current Architecture Analysis

Before designing voice integration, understanding the existing infrastructure is critical:

### Three Game Engine Variants

| Engine | File | Use Case | Voice Fit |
|--------|------|----------|-----------|
| `game_engine.py` | Sync, no SDK | Testing rules | Episode Mode only |
| `game_engine_async.py` | Async, local agents | Development | Both modes |
| `game_engine_containerized.py` | Docker agents (22 containers) | Production | Both modes |

### Existing Text Sources for Voice

1. **GameMasterInteractions** (`agents/game_master_interactions.py`)
   - Already generates dramatic narration via Gemini Interactions API
   - Methods: `announce_murder_async()`, `announce_banishment_async()`, `announce_finale_async()`
   - Has fallback methods if API unavailable
   - **Voice opportunity**: Direct TTS on GM output

2. **Agent Reasoning** (`agents/player_agent_sdk.py`)
   - Claude SDK generates reasoning via `tool_context['vote_result']['reasoning']`
   - Captured for vote decisions, murder choices, reflections
   - **Voice opportunity**: Convert reasoning to "confessional" audio

3. **Structured Events** (`core/game_state.py`)
   - `GameState.events` list with `narrative` field per event
   - Event types: `MURDER`, `BANISHMENT`, `VOTE_TALLY`, `MISSION_COMPLETE`, etc.
   - Trust snapshots captured per phase
   - **Voice opportunity**: Script generator reads events + narratives

4. **Agent Service API** (`agents/agent_service.py`)
   - Flask endpoints: `/vote`, `/choose_murder_victim`, `/reflect`, `/seer_result`
   - Returns JSON with `reasoning` field
   - **HITL opportunity**: Add `/speak` endpoint for voice synthesis

### Existing UI Infrastructure

- **WebSocket** (`traitorsim-ui/backend/app/routers/runner.py`) - Real-time game log streaming
- **Event Types** (`traitorsim-ui/frontend/src/types/events.ts`) - 20+ structured event types
- **TanStack Query hooks** - Server state management
- **D3 visualization** - Force graph, timeline, heatmap

**Key insight**: The infrastructure for streaming game events to the UI already exists. Voice can piggyback on this channel.

---

## Part 1: Technology Foundation

### ElevenLabs Eleven v3 Capabilities

The **Text-to-Dialogue API** (exclusively on v3) provides:

| Feature | Capability |
|---------|------------|
| **Speakers** | Unlimited per conversation |
| **Emotional Range** | High contextual understanding with audio tags |
| **Languages** | 70+ languages |
| **Character Limit** | 5,000 chars (~5 min audio) per request |
| **Latency** | Not real-time (designed for pre-generated content) |
| **Control** | Audio tags: `[interrupting]`, `[excited]`, `[nervous]`, etc. |

### Key Audio Tags for TraitorSim

```
[dramatic]    - Narrator reveals, murder announcements
[nervous]     - Accused players defending themselves
[confident]   - Players making accusations
[whispered]   - Traitor meetings
[suspicious]  - Pointed questions at Round Table
[laughing]    - Social bonding moments
[tense]       - Standoffs and confrontations
[relieved]    - Survival after close votes
[cold]        - Calculated Traitor murder decisions
```

### Voice Architecture (Updated for Current Codebase)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Voice Pipeline Architecture                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  EXISTING COMPONENTS (TraitorSim)          NEW VOICE LAYER               │
│  ─────────────────────────────────         ──────────────────            │
│                                                                          │
│  ┌─────────────────────────────┐          ┌──────────────────────────┐  │
│  │ GameMasterInteractions      │          │ VoiceScriptExtractor     │  │
│  │ (Gemini Interactions API)   │─────────▶│ - Parse GM narratives    │  │
│  │                             │          │ - Extract agent reasoning│  │
│  │ Methods:                    │          │ - Map events to dialogue │  │
│  │ • announce_murder_async()   │          └───────────┬──────────────┘  │
│  │ • announce_banishment_async()                      │                  │
│  │ • announce_finale_async()   │                      ▼                  │
│  └─────────────────────────────┘          ┌──────────────────────────┐  │
│              │                            │ CharacterVoiceLibrary    │  │
│              │                            │ (98 personas → 22 voices)│  │
│              ▼                            │                          │  │
│  ┌─────────────────────────────┐          │ • archetype_id mapping   │  │
│  │ GameState.events[]          │          │ • OCEAN → voice params   │  │
│  │ GameState.trust_snapshots[] │─────────▶│ • demographics → accent  │  │
│  │                             │          └───────────┬──────────────┘  │
│  │ Event types:                │                      │                  │
│  │ • MURDER {narrative}        │                      ▼                  │
│  │ • BANISHMENT {narrative}    │          ┌──────────────────────────┐  │
│  │ • VOTE_TALLY {data}         │          │ ElevenLabsClient         │  │
│  │ • MISSION_COMPLETE          │          │                          │  │
│  └─────────────────────────────┘          │ • text_to_dialogue() v3  │  │
│              │                            │ • text_to_speech_stream() │  │
│              │                            │ • voice_clone()          │  │
│              ▼                            └───────────┬──────────────┘  │
│  ┌─────────────────────────────┐                      │                  │
│  │ Agent tool_context          │                      ▼                  │
│  │ (from PlayerAgentSDK)       │          ┌──────────────────────────┐  │
│  │                             │          │ AudioAssembler           │  │
│  │ • vote_result.reasoning     │          │ (pydub + SFX library)    │  │
│  │ • murder_choice.reasoning   │          │                          │  │
│  │ • reflection_notes          │─────────▶│ • Sidechain compression  │  │
│  └─────────────────────────────┘          │ • Soundtrack layering    │  │
│                                           │ • Timing/pacing          │  │
│                                           └───────────┬──────────────┘  │
│                                                       │                  │
│                                                       ▼                  │
│                                           ┌──────────────────────────┐  │
│                                           │ Output Formats           │  │
│                                           │ • Episode MP3 (~15 min)  │  │
│                                           │ • WebSocket stream (HITL)│  │
│                                           │ • Per-phase audio chunks │  │
│                                           └──────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Precise Integration Points

**1. Hook into `GameMasterInteractions._send_message_async()`**
```python
# agents/game_master_interactions.py:102
async def _send_message_async(self, prompt: str) -> str:
    # ... existing code ...
    response_text = interaction.outputs[-1].text.strip()

    # NEW: Emit voice event for narrator
    if self.voice_enabled:
        await self.voice_emitter.emit_narrator(response_text)

    return response_text
```

**2. Hook into `PlayerAgentSDK.cast_vote_async()` for confessionals**
```python
# agents/player_agent_sdk.py:207
async def cast_vote_async(self) -> Optional[str]:
    # ... existing code ...
    vote_result = self.tool_context.get("vote_result")

    # NEW: Emit confessional voice event
    if vote_result and self.voice_enabled:
        await self.voice_emitter.emit_confessional(
            player_id=self.player.id,
            text=vote_result["reasoning"],
            emotion=self._infer_emotion("voting")
        )

    return vote_result["target"]
```

**3. Hook into `GameState.add_event()` for event-driven voice**
```python
# core/game_state.py:185
def add_event(self, event_type: str, phase: str, ..., narrative: Optional[str] = None):
    event = {...}
    self.events.append(event)

    # NEW: Queue voice generation for significant events
    if event_type in VOICE_ENABLED_EVENTS and narrative:
        self.voice_queue.append({
            "type": event_type,
            "narrative": narrative,
            "speaker": self._determine_speaker(event_type, actor)
        })
```

**4. Add `/speak` endpoint to Agent Service (HITL mode)**
```python
# agents/agent_service.py (new endpoint)
@app.route('/speak', methods=['POST'])
def speak():
    """Generate voice audio for agent statement (HITL mode)."""
    data = request.json
    text = data['text']
    emotion = data.get('emotion', 'neutral')

    # Generate voice via ElevenLabs Flash (low latency)
    audio = voice_client.text_to_speech(
        text=text,
        voice_id=agent.voice_config.voice_id,
        model_id="eleven_flash_v2_5"
    )

    return Response(audio, mimetype='audio/mpeg')
```

---

## Part 2: Episode Mode - Serialized Audio Drama

### Concept: "The Traitors: AI Edition"

Transform completed game logs into binge-worthy audio episodes with:

- **Alan Cumming-style narrator** - Theatrical, mysterious, dramatic
- **22 distinct character voices** - Matching OCEAN personality traits
- **Original soundtrack integration** - Tension stings, revelation cues
- **Confessional segments** - Inner monologue from diary entries

### Episode Structure (Per Day)

```
┌────────────────────────────────────────────────────────────────┐
│                     EPISODE: DAY {N}                            │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [0:00-0:45]   COLD OPEN                                       │
│  └─ Previous day recap + cliffhanger reminder                  │
│                                                                 │
│  [0:45-2:30]   BREAKFAST REVEAL                                │
│  └─ Narrator announces murder victim                           │
│  └─ Survivor reactions (2-3 selected confessionals)            │
│  └─ Breakfast table tension audio                              │
│                                                                 │
│  [2:30-5:00]   MISSION BRIEFING & EXECUTION                    │
│  └─ Narrator explains challenge                                │
│  └─ Team collaboration/conflict dialogue                       │
│  └─ Mission outcome narration                                  │
│                                                                 │
│  [5:00-7:00]   SOCIAL PHASE HIGHLIGHTS                         │
│  └─ Key alliance conversations (2-3 clips)                     │
│  └─ Whispered suspicions / confessionals                       │
│                                                                 │
│  [7:00-12:00]  ROUND TABLE                                     │
│  └─ Full accusation/defense dialogue                           │
│  └─ Voting tension build                                       │
│  └─ Dramatic reveal of banished player                         │
│  └─ Role reveal reaction shots (audio)                         │
│                                                                 │
│  [12:00-14:00] TURRET (Traitors Only)                          │
│  └─ [whispered] Traitor deliberation                           │
│  └─ Murder target selection                                    │
│  └─ Narrator foreshadowing                                     │
│                                                                 │
│  [14:00-15:00] NEXT EPISODE PREVIEW                            │
│  └─ Teaser audio clips from upcoming day                       │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Voice Script Generation Pipeline

```python
# src/traitorsim/voice/episode_generator.py

class EpisodeScriptGenerator:
    """Transforms game logs into voice-ready scripts."""

    def __init__(self, game_log: GameLog, character_voices: Dict[str, VoiceConfig]):
        self.game_log = game_log
        self.voices = character_voices
        self.narrator_voice = "narrator_host"  # Alan Cumming style

    def generate_day_script(self, day: int) -> DialogueScript:
        """Generate complete voice script for one day."""

        script = DialogueScript()

        # Cold Open
        script.add_segment(
            speaker=self.narrator_voice,
            text=self._generate_cold_open(day),
            emotion="[dramatic]"
        )

        # Breakfast Murder Reveal
        murder_event = self.game_log.get_murder(day)
        if murder_event:
            script.add_segment(
                speaker=self.narrator_voice,
                text=f"As dawn breaks over the castle... "
                     f"one chair sits empty. {murder_event.victim.name}... "
                     f"will not be joining us.",
                emotion="[dramatic][slow]"
            )

            # Survivor reactions (top 3 most affected by trust matrix)
            for reactor in self._get_top_reactors(murder_event.victim):
                confessional = self._generate_reaction_confessional(
                    reactor, murder_event.victim
                )
                script.add_segment(
                    speaker=self.voices[reactor.id],
                    text=confessional,
                    emotion=self._infer_emotion(reactor, "grief")
                )

        # Round Table (full dialogue)
        roundtable_events = self.game_log.get_roundtable(day)
        script.extend(self._script_roundtable(roundtable_events))

        # Turret (whispered)
        turret_events = self.game_log.get_turret(day)
        script.extend(self._script_turret(turret_events))

        return script

    def _script_roundtable(self, events: List[RoundTableEvent]) -> List[DialogueSegment]:
        """Convert Round Table events to dramatic dialogue."""

        segments = []

        # Narrator sets the scene
        segments.append(DialogueSegment(
            speaker=self.narrator_voice,
            text="The Round Table convenes. Suspicion hangs heavy in the air.",
            emotion="[tense]"
        ))

        for event in events:
            if event.type == "accusation":
                segments.append(DialogueSegment(
                    speaker=self.voices[event.accuser_id],
                    text=event.statement,
                    emotion="[suspicious][confident]"
                ))
            elif event.type == "defense":
                segments.append(DialogueSegment(
                    speaker=self.voices[event.defender_id],
                    text=event.statement,
                    emotion="[nervous]" if event.is_traitor else "[indignant]"
                ))
            elif event.type == "vote_reveal":
                # Dramatic pause before reveal
                segments.append(DialogueSegment(
                    speaker=self.narrator_voice,
                    text=f"[pause] The votes are in. "
                         f"{event.banished_name}... "
                         f"[long_pause] "
                         f"you have been banished.",
                    emotion="[dramatic]"
                ))

        return segments
```

### Character Voice Library Design

The existing 13 archetypes in `core/archetypes.py` map directly to voice profiles. The persona library (98 personas) includes rich demographic data that informs accent and speech patterns.

```python
# src/traitorsim/voice/voice_library.py

# Maps to existing archetypes from core/archetypes.py
ARCHETYPE_VOICE_PROFILES = {
    # ===== From core/archetypes.py ARCHETYPE_REGISTRY =====
    # Voice IDs validated against ElevenLabs library (Dec 2025)
    # Sources: https://audio-generation-plugin.com/elevenlabs-premade-voices/
    #          https://help.scenario.com/en/articles/elevenlabs-family-the-essentials/
    #
    # Each archetype has BOTH male and female voice options since
    # personas can be any gender. Use persona.demographics.gender to select.

    "prodigy": {
        # The Prodigy: High intellect, low neuroticism
        "voice_description": "Young, sharp, analytical. Quick speech with occasional hesitation.",
        "male": {
            "base_voice_id": "liam",   # Articulate, clear young American
            "alt_voice_id": "josh",    # Deep, impactful young American
        },
        "female": {
            "base_voice_id": "aria",   # Expressive, young American (2024)
            "alt_voice_id": "jessica", # Expressive, youthful
        },
        "stability": 0.6,
        "style": 0.7,
        "emotional_range": ["confident", "nervous", "excited"],
    },

    "charming_sociopath": {
        # The Charming Sociopath: High extraversion, low agreeableness
        "voice_description": "Smooth, warm, disarming. Perfect control with coldness underneath.",
        "male": {
            "base_voice_id": "george",  # Warm, trustworthy British - hides malice
            "alt_voice_id": "roger",    # Confident, persuasive (2024)
        },
        "female": {
            "base_voice_id": "charlotte", # Seductive, playful - manipulation
            "alt_voice_id": "alice",      # Confident British
        },
        "stability": 0.75,
        "style": 0.5,
        "emotional_range": ["charming", "concerned", "cold"],
    },

    "bitter_traitor": {
        # The Bitter Traitor: Low agreeableness, high neuroticism
        "voice_description": "Resentful edge, defensive posture. Sarcastic undertone.",
        "male": {
            "base_voice_id": "callum",  # Hoarse, dramatic, intense
            "alt_voice_id": "clyde",    # War veteran, intense
        },
        "female": {
            "base_voice_id": "lily",    # Raspy, middle-aged British
            "alt_voice_id": "domi",     # Strong young American
        },
        "stability": 0.5,
        "style": 0.6,
        "emotional_range": ["bitter", "defensive", "vindictive"],
    },

    "misguided_survivor": {
        # The Misguided Survivor: High neuroticism, moderate agreeableness
        "voice_description": "Anxious, overcompensating confidence. Frequently second-guesses.",
        "male": {
            "base_voice_id": "harry",   # Anxious young American - PERFECT
            "alt_voice_id": "ethan",    # Young American, ASMR-style nervous
        },
        "female": {
            "base_voice_id": "jessica", # Expressive, youthful
            "alt_voice_id": "freya",    # Young American, versatile
        },
        "stability": 0.4,
        "style": 0.55,
        "emotional_range": ["nervous", "hopeful", "panicked"],
    },

    "zealot": {
        # The Zealot: High conscientiousness, low openness
        "voice_description": "Intense conviction, unwavering certainty. Righteous tone.",
        "male": {
            "base_voice_id": "josh",    # Deep, impactful
            "alt_voice_id": "bill",     # Strong, documentary-style
        },
        "female": {
            "base_voice_id": "alice",   # Confident British, news presenter
            "alt_voice_id": "domi",     # Strong young American
        },
        "stability": 0.8,
        "style": 0.4,
        "emotional_range": ["fervent", "judgmental", "indignant"],
    },

    "infatuated_faithful": {
        # The Infatuated Faithful: High agreeableness, high extraversion
        "voice_description": "Warm, trusting, emotionally open. Eager to connect.",
        "male": {
            "base_voice_id": "chris",   # Casual, relatable American
            "alt_voice_id": "eric",     # Friendly, approachable
        },
        "female": {
            "base_voice_id": "matilda", # Friendly, warm audiobook
            "alt_voice_id": "rachel",   # Calm, soothing
        },
        "stability": 0.55,
        "style": 0.7,
        "emotional_range": ["affectionate", "hurt", "loyal"],
    },

    "comedic_psychic": {
        # The Comedic Psychic: High openness, moderate extraversion
        "voice_description": "Whimsical, playful, slightly eccentric. Theatrical delivery.",
        "male": {
            "base_voice_id": "jeremy",  # Excited, American-Irish, energetic
            "alt_voice_id": "giovanni", # Young English-Italian, foreign flair
        },
        "female": {
            "base_voice_id": "mimi",    # Childish, English-Swedish, quirky
            "alt_voice_id": "gigi",     # Childish, animation-style
        },
        "stability": 0.4,
        "style": 0.85,
        "emotional_range": ["mystical", "silly", "dramatic"],
    },

    "incompetent_authority": {
        # The Incompetent Authority Figure: Low conscientiousness, high extraversion
        "voice_description": "Pompous bluster hiding uncertainty. Overconfident assertions.",
        "male": {
            "base_voice_id": "patrick", # Shouty, energetic - perfect bluster
            "alt_voice_id": "bill",     # Strong, documentary
        },
        "female": {
            "base_voice_id": "glinda",  # Middle-aged American, witch-like
            "alt_voice_id": "serena",   # Pleasant, interactive
        },
        "stability": 0.5,
        "style": 0.75,
        "emotional_range": ["pompous", "flustered", "indignant"],
    },

    "quirky_outsider": {
        # The Quirky Outsider: High openness, low extraversion
        "voice_description": "Quiet observation, unexpected insights. Deadpan delivery.",
        "male": {
            "base_voice_id": "thomas",  # Calm, meditation-style
            "alt_voice_id": "fin",      # Old Irish sailor, authentic
        },
        "female": {
            "base_voice_id": "emily",   # Calm young American
            "alt_voice_id": "nicole",   # Whispering, intimate
        },
        "non_binary": {
            "base_voice_id": "river",   # Non-binary, modern (2024)
            "alt_voice_id": "thomas",   # Neutral fallback
        },
        "stability": 0.7,
        "style": 0.3,
        "emotional_range": ["curious", "detached", "surprised"],
    },

    "romantic": {
        # The Romantic: High agreeableness, high openness
        "voice_description": "Emotionally rich, idealistic. Dramatic emotional range.",
        "male": {
            "base_voice_id": "brian",   # Deep, rich narration
            "alt_voice_id": "michael",  # Old American, audiobook
        },
        "female": {
            "base_voice_id": "dorothy", # Pleasant young British
            "alt_voice_id": "grace",    # Young American-Southern
        },
        "stability": 0.5,
        "style": 0.65,
        "emotional_range": ["hopeful", "heartbroken", "passionate"],
    },

    "mischievous_operator": {
        # The Mischievous Operator: Low conscientiousness, high extraversion
        "voice_description": "Playful chaos energy. Enjoys stirring the pot.",
        "male": {
            "base_voice_id": "charlie", # Casual Australian, playful
            "alt_voice_id": "jeremy",   # Excited, energetic
        },
        "female": {
            "base_voice_id": "laura",   # Upbeat, lively (2024)
            "alt_voice_id": "sarah",    # Expressive, energetic
        },
        "stability": 0.4,
        "style": 0.8,
        "emotional_range": ["amused", "scheming", "gleeful"],
    },

    "smug_player": {
        # The Smug Player: High extraversion, low agreeableness
        "voice_description": "Self-satisfied confidence. Condescending undertones.",
        "male": {
            "base_voice_id": "joseph",  # Formal British male
            "alt_voice_id": "daniel",   # Deep British, authoritative
        },
        "female": {
            "base_voice_id": "alice",   # Confident British, news presenter
            "alt_voice_id": "charlotte",# Seductive, playful edge
        },
        "stability": 0.7,
        "style": 0.5,
        "emotional_range": ["smug", "dismissive", "annoyed"],
    },

    "charismatic_leader": {
        # The Charismatic Leader: High extraversion, high conscientiousness
        "voice_description": "Inspiring presence, natural authority. Rallying tone.",
        "male": {
            "base_voice_id": "liam",    # Articulate, clear
            "alt_voice_id": "george",   # Warm, trustworthy
        },
        "female": {
            "base_voice_id": "aria",    # Expressive, engaging (2024)
            "alt_voice_id": "sarah",    # Soft, news delivery
        },
        "stability": 0.65,
        "style": 0.6,
        "emotional_range": ["inspiring", "determined", "compassionate"],
    },
}

def get_voice_for_persona(persona: Dict) -> str:
    """Get appropriate voice ID based on persona's archetype and gender.

    Args:
        persona: Dict with archetype_id and demographics.gender

    Returns:
        ElevenLabs voice ID string
    """
    archetype_id = persona.get("archetype_id", "prodigy")
    gender = persona.get("demographics", {}).get("gender", "female").lower()

    profile = ARCHETYPE_VOICE_PROFILES.get(archetype_id, ARCHETYPE_VOICE_PROFILES["prodigy"])

    # Handle non-binary if supported by archetype
    if gender == "non-binary" and "non_binary" in profile:
        return profile["non_binary"]["base_voice_id"]

    # Default to female if gender unknown
    gender_key = "male" if gender == "male" else "female"
    return profile[gender_key]["base_voice_id"]

def map_persona_to_voice(persona: Dict) -> VoiceConfig:
    """Map a persona from library to voice config.

    Uses archetype as base, then modifies by:
    1. OCEAN personality traits → stability/style
    2. Demographics location → accent selection
    3. Age → pitch adjustment
    """
    archetype_id = persona.get("archetype_id", "prodigy")
    base_profile = ARCHETYPE_VOICE_PROFILES.get(archetype_id, ARCHETYPE_VOICE_PROFILES["prodigy"])

    # Get OCEAN traits from persona
    personality = persona.get("personality", {})
    neuroticism = personality.get("neuroticism", 0.5)
    extraversion = personality.get("extraversion", 0.5)

    # Adjust stability: High neuroticism = less stable voice
    stability = base_profile["stability"] * (1.0 - (neuroticism * 0.3))

    # Adjust style: High extraversion = more expressive
    style = base_profile["style"] * (1.0 + (extraversion * 0.2))

    # Select accent based on demographics location
    location = persona.get("demographics", {}).get("location", "UK")
    accent = _select_accent(location, base_profile["accent_hint"])

    # Adjust pitch based on age
    age = persona.get("demographics", {}).get("age", 35)
    pitch_adjust = _age_to_pitch_adjust(age)

    return VoiceConfig(
        voice_id=_select_voice_id(base_profile["base_voice_id"], persona),
        stability=np.clip(stability, 0.3, 0.9),
        similarity_boost=0.75,
        style=np.clip(style, 0.2, 0.9),
        accent=accent,
        pitch_adjust=pitch_adjust,
        emotional_range=base_profile["emotional_range"]
    )

def _select_accent(location: str, hint: str) -> str:
    """Map UK location to accent."""
    LOCATION_ACCENTS = {
        "scotland": "scottish",
        "edinburgh": "scottish_urban",
        "glasgow": "scottish_urban",
        "northern ireland": "ulster",
        "wales": "welsh",
        "manchester": "mancunian",
        "liverpool": "scouse",
        "birmingham": "brummie",
        "newcastle": "geordie",
        "yorkshire": "yorkshire",
        "london": "estuary",
        "essex": "estuary",
        "cornwall": "west_country",
        "devon": "west_country",
    }

    location_lower = location.lower()
    for region, accent in LOCATION_ACCENTS.items():
        if region in location_lower:
            return accent

    # Default based on hint
    return hint if hint else "neutral_british"

def map_persona_to_voice(persona: PersonaData) -> VoiceConfig:
    """Map a persona's archetype and OCEAN traits to voice config."""

    base_profile = CHARACTER_VOICE_PROFILES[persona.archetype]

    # Modify based on OCEAN traits
    config = VoiceConfig(
        voice_id=select_elevenlabs_voice(base_profile),
        stability=calculate_stability(persona.neuroticism),
        similarity_boost=0.75,
        style_exaggeration=calculate_style(persona.extraversion),
    )

    # High neuroticism = more voice variation (less stable)
    if persona.ocean.neuroticism > 0.7:
        config.stability *= 0.8

    # High extraversion = more expressive style
    if persona.ocean.extraversion > 0.7:
        config.style_exaggeration *= 1.2

    return config
```

### Episode Assembly Pipeline

```python
# src/traitorsim/voice/audio_assembler.py

class EpisodeAudioAssembler:
    """Assembles voice segments with music and SFX into final episode."""

    def __init__(self, elevenlabs_client: ElevenLabsClient):
        self.client = elevenlabs_client
        self.music_library = SoundtrackLibrary()
        self.sfx_library = SoundEffectLibrary()

    async def assemble_episode(
        self,
        script: DialogueScript,
        episode_number: int
    ) -> AudioFile:
        """Generate and mix complete episode audio."""

        # Phase 1: Generate all voice segments via ElevenLabs
        voice_segments = await self._generate_voice_segments_batch(script)

        # Phase 2: Add music beds
        timeline = AudioTimeline()

        # Dramatic opening music
        timeline.add_track(
            self.music_library.get("tension_build"),
            start=0,
            volume=-12  # Background level
        )

        # Layer voice segments
        current_time = 0
        for segment in voice_segments:
            timeline.add_track(segment.audio, start=current_time, volume=0)

            # Add SFX based on emotion tags
            if "[dramatic]" in segment.emotion:
                timeline.add_track(
                    self.sfx_library.get("revelation_sting"),
                    start=current_time - 0.5,  # Just before
                    volume=-6
                )

            current_time += segment.duration + self._calculate_pause(segment)

        # Phase 3: Dynamic mixing (duck music during dialogue)
        timeline.apply_sidechain_compression(
            trigger_tracks="voice",
            duck_tracks="music",
            ratio=3.0,
            threshold=-24
        )

        # Phase 4: Export
        return timeline.export(
            format="mp3",
            bitrate="192k",
            normalize=True
        )

    async def _generate_voice_segments_batch(
        self,
        script: DialogueScript
    ) -> List[VoiceSegment]:
        """Batch generate voice segments (respecting rate limits)."""

        segments = []

        # Group by speaker for ElevenLabs dialogue API efficiency
        speaker_groups = script.group_by_speaker()

        for speaker_id, speaker_segments in speaker_groups.items():
            # Use text-to-dialogue for multi-turn conversations
            dialogue_text = self._format_for_dialogue_api(speaker_segments)

            audio = await self.client.text_to_dialogue(
                text=dialogue_text,
                voice_ids=self._get_voice_ids(speaker_segments),
                model_id="eleven_v3"
            )

            # Split audio back into individual segments
            segments.extend(self._split_audio(audio, speaker_segments))

            # Rate limit: 2-3 concurrent requests on Pro plan
            await asyncio.sleep(0.5)

        return segments
```

### Soundtrack Design

The "Traitorized Pop" style (dark, haunting, à la Ruelle/London Grammar):

```python
# src/traitorsim/voice/soundtrack.py

SOUNDTRACK_CUES = {
    # Phase-specific music beds
    "breakfast_tension": {
        "file": "music/breakfast_strings.mp3",
        "bpm": 70,
        "mood": "uneasy_anticipation",
        "duration": "loop"
    },
    "mission_energy": {
        "file": "music/mission_pulse.mp3",
        "bpm": 120,
        "mood": "competitive_urgency",
        "duration": "scene"
    },
    "roundtable_deliberation": {
        "file": "music/deliberation_dark.mp3",
        "bpm": 60,
        "mood": "suspicion_brewing",
        "duration": "loop"
    },
    "turret_sinister": {
        "file": "music/traitor_whispers.mp3",
        "bpm": 50,
        "mood": "cold_calculation",
        "duration": "scene"
    },

    # Event stings
    "murder_reveal": {
        "file": "sfx/murder_reveal_sting.mp3",
        "duration": 3.5,
        "mood": "shock"
    },
    "banishment_vote": {
        "file": "sfx/vote_drumroll.mp3",
        "duration": 5.0,
        "mood": "tension_peak"
    },
    "role_reveal_traitor": {
        "file": "sfx/traitor_reveal_chord.mp3",
        "duration": 4.0,
        "mood": "triumphant_justice"
    },
    "role_reveal_faithful": {
        "file": "sfx/faithful_reveal_somber.mp3",
        "duration": 4.0,
        "mood": "tragic_mistake"
    }
}
```

### Cost Estimation: Episode Mode

For a realistic 10-day game (22→4 players via elimination, ~10-12 episodes):

| Component | Day 1 | Day 5 | Day 10 | Season Total |
|-----------|-------|-------|--------|--------------|
| Narrator | 1,800 | 1,800 | 1,800 | ~18,000 |
| Player dialogue (decays) | 19,300 | 12,300 | 3,500 | ~114,000 |
| Turret (traitors only) | 450 | 300 | 150 | ~3,400 |
| **Daily total** | ~21,500 | ~14,400 | ~5,500 | **~135,000** |

| Metric | Value |
|--------|-------|
| **Season characters** | ~135,000 |
| **Pro plan % used** | 27% |
| **Seasons/month on Pro** | 3-4 |
| **Cost per season** | ~$25-33 |

**On Pro plan ($99/month, 500K credits):** 3-4 full seasons per month

*Note: Real-world seasons run 9-12 days. Player count decays from 22→4, so daily character counts decrease significantly. If your simulation runs 15+ days, this indicates a game logic bug.*

---

## Part 3: HITL Mode - 21 AI + 1 Human

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HITL Voice Architecture                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐      ┌─────────────────────────────────────────┐ │
│  │    Human Player      │      │           Game Server                    │ │
│  │                      │      │                                          │ │
│  │  ┌───────────────┐   │      │  ┌───────────┐   ┌───────────────────┐  │ │
│  │  │ Microphone    │───┼──────┼─▶│ Deepgram  │──▶│ Game Engine       │  │ │
│  │  │ Input         │   │      │  │ STT       │   │ (Phase Router)    │  │ │
│  │  └───────────────┘   │      │  │ (<100ms)  │   └─────────┬─────────┘  │ │
│  │                      │      │  └───────────┘             │            │ │
│  │  ┌───────────────┐   │      │                            ▼            │ │
│  │  │ Speaker       │◀──┼──────┼──────────────────┐   ┌─────────────┐   │ │
│  │  │ Output        │   │      │                  │   │ 21 Claude   │   │ │
│  │  └───────────────┘   │      │                  │   │ Agents      │   │ │
│  │                      │      │                  │   │ (parallel)  │   │ │
│  │  ┌───────────────┐   │      │  ┌───────────┐  │   └──────┬──────┘   │ │
│  │  │ WebRTC        │───┼──────┼─▶│ ElevenLabs│  │          │          │ │
│  │  │ Connection    │◀──┼──────┼──│ TTS       │◀─┴──────────┘          │ │
│  │  └───────────────┘   │      │  │ (Flash)   │                        │ │
│  │                      │      │  └───────────┘                        │ │
│  └──────────────────────┘      │                                       │ │
│                                │  ┌───────────────────────────────────┐│ │
│                                │  │ Gemini Game Master                ││ │
│                                │  │ (Narrator Voice via ElevenLabs)   ││ │
│                                │  └───────────────────────────────────┘│ │
│                                └─────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Latency Budget Analysis

**Target: <500ms end-to-end for conversational responsiveness**

| Stage | Technology | Latency | Notes |
|-------|------------|---------|-------|
| Audio capture | Browser WebRTC | 10-20ms | Minimal |
| Network (upload) | WebRTC/UDP | 20-50ms | Depends on location |
| Speech-to-text | Deepgram Nova-3 | 50-100ms | Streaming transcription |
| Intent processing | Local logic | <10ms | Phase-appropriate routing |
| AI response generation | Claude (parallel) | 300-500ms | Main bottleneck |
| Text-to-speech | ElevenLabs Flash | 75-150ms | Use Flash for speed |
| Network (download) | WebSocket | 20-50ms | Streaming audio |
| **Total** | - | **~500-900ms** | Acceptable for turns |

### Human Input Processing

```python
# src/traitorsim/voice/hitl_handler.py

class HITLVoiceHandler:
    """Handles human player voice input in real-time."""

    def __init__(
        self,
        stt_client: DeepgramClient,
        tts_client: ElevenLabsClient,
        game_engine: GameEngineAsync
    ):
        self.stt = stt_client
        self.tts = tts_client
        self.engine = game_engine
        self.human_player_id = "player_human"
        self.vad = SileroVAD()  # Voice Activity Detection

    async def process_voice_input(
        self,
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        """Process human voice and yield AI response audio."""

        # Stage 1: VAD + Streaming STT
        async for transcript in self.stt.transcribe_stream(audio_stream):
            if transcript.is_final:
                # Stage 2: Route based on game phase
                response = await self._route_to_phase_handler(
                    transcript.text,
                    self.engine.game_state.phase
                )

                # Stage 3: Generate spoken response
                async for audio_chunk in self._generate_response_audio(response):
                    yield audio_chunk

    async def _route_to_phase_handler(
        self,
        text: str,
        phase: GamePhase
    ) -> ConversationResponse:
        """Route human input to appropriate phase handler."""

        if phase == GamePhase.ROUNDTABLE:
            return await self._handle_roundtable_input(text)
        elif phase == GamePhase.SOCIAL:
            return await self._handle_social_input(text)
        elif phase == GamePhase.TURRET and self._is_human_traitor():
            return await self._handle_turret_input(text)
        else:
            # Passive phases - acknowledge but don't process
            return ConversationResponse(
                speaker="narrator",
                text="The game proceeds...",
                allow_interruption=False
            )

    async def _handle_roundtable_input(self, text: str) -> ConversationResponse:
        """Process human accusation/defense at Round Table."""

        # Parse intent
        intent = await self._classify_intent(text)

        if intent.type == "accusation":
            # Human accuses someone - trigger AI responses
            target_name = intent.target

            # Get accused AI's defense
            accused_agent = self.engine.get_agent(target_name)
            defense = await accused_agent.generate_defense_async(
                accusation=text,
                accuser="human player"
            )

            # Queue responses from other players (reactions)
            reaction_tasks = [
                self._generate_reaction(agent, text, target_name)
                for agent in self.engine.get_alive_agents()
                if agent.player.id not in [self.human_player_id, accused_agent.player.id]
            ]
            reactions = await asyncio.gather(*reaction_tasks)

            return ConversationResponse(
                speaker=target_name,
                text=defense,
                followup_speakers=reactions[:3]  # Limit to 3 reactions
            )

        elif intent.type == "defense":
            # Human defending themselves
            # Generate AI challenges
            challengers = self._select_challengers(num=2)
            challenges = await asyncio.gather(*[
                agent.challenge_defense_async(text)
                for agent in challengers
            ])

            return ConversationResponse(
                speaker=challengers[0].player.name,
                text=challenges[0],
                followup_speakers=[
                    {"speaker": c.player.name, "text": r}
                    for c, r in zip(challengers[1:], challenges[1:])
                ]
            )

        elif intent.type == "vote":
            # Human casting vote
            self.engine.register_vote(self.human_player_id, intent.target)

            return ConversationResponse(
                speaker="narrator",
                text=f"Your vote for {intent.target} has been recorded.",
                allow_interruption=False
            )
```

### AI Agent Voice Generation

```python
# src/traitorsim/voice/agent_voice.py

class AgentVoiceGenerator:
    """Generates voice audio for AI agents."""

    def __init__(self, elevenlabs_client: ElevenLabsClient):
        self.client = elevenlabs_client
        self.voice_cache = {}  # Cache pre-generated common phrases

    async def generate_agent_speech(
        self,
        agent: PlayerAgentSDK,
        text: str,
        emotion_context: str = None
    ) -> AsyncIterator[bytes]:
        """Generate voice audio for an agent's statement."""

        # Get agent's voice config
        voice_config = self._get_voice_config(agent)

        # Determine emotional delivery based on:
        # 1. Agent's current stress level
        # 2. Content of text
        # 3. Agent's personality (OCEAN)
        emotion_tag = self._calculate_emotion_tag(
            agent, text, emotion_context
        )

        # Wrap text with emotion tags
        tagged_text = f"{emotion_tag} {text}"

        # Stream audio generation (for low latency)
        async for chunk in self.client.text_to_speech_stream(
            text=tagged_text,
            voice_id=voice_config.voice_id,
            model_id="eleven_flash_v2_5",  # Use Flash for speed
            optimize_streaming_latency=3   # Maximum latency optimization
        ):
            yield chunk

    def _calculate_emotion_tag(
        self,
        agent: PlayerAgentSDK,
        text: str,
        context: str
    ) -> str:
        """Calculate appropriate emotion tag based on agent state."""

        personality = agent.player.personality

        # Base emotion from context
        base_emotion = {
            "accusation": "[confident]",
            "defense": "[defensive]",
            "agreement": "[supportive]",
            "challenge": "[suspicious]",
            "voting": "[tense]"
        }.get(context, "")

        # Modify based on neuroticism
        if personality.neuroticism > 0.7:
            if context == "defense":
                base_emotion = "[nervous][defensive]"
            elif context == "accusation":
                base_emotion = "[anxious][accusatory]"

        # Traitors speaking about their fellow traitors
        if agent.player.role == Role.TRAITOR:
            if "fellow traitor" in text.lower():
                base_emotion = "[calculated][cold]"

        return base_emotion
```

### Round Table Voice Flow

```python
# src/traitorsim/voice/roundtable_voice.py

class RoundTableVoiceOrchestrator:
    """Orchestrates multi-speaker Round Table with human participant."""

    async def run_roundtable_voice_session(
        self,
        game_state: GameState,
        human_handler: HITLVoiceHandler,
        agents: List[PlayerAgentSDK]
    ) -> RoundTableResult:
        """Run a full Round Table phase with voice interaction."""

        # Phase 1: Narrator opens
        await self._play_audio(
            self.narrator.generate("The Round Table convenes. "
                                   "Who do you suspect?")
        )

        # Phase 2: Initial accusations (AI agents go first to set context)
        initial_accusers = self._select_initial_accusers(agents, num=3)

        for accuser in initial_accusers:
            accusation = await accuser.generate_accusation_async()
            await self._stream_agent_audio(accuser, accusation)

            # Brief pause for human to potentially interrupt
            human_input = await asyncio.wait_for(
                human_handler.listen_for_input(),
                timeout=3.0  # 3 second window
            )

            if human_input:
                # Human wants to speak - process their input
                response = await human_handler.process_voice_input(human_input)
                await self._play_conversation_response(response)

        # Phase 3: Open floor (human can speak anytime)
        remaining_time = 120  # 2 minutes
        start_time = time.time()

        while time.time() - start_time < remaining_time:
            # Listen for human input with short timeout
            try:
                human_input = await asyncio.wait_for(
                    human_handler.listen_for_input(),
                    timeout=5.0
                )
                if human_input:
                    response = await human_handler.process_voice_input(human_input)
                    await self._play_conversation_response(response)
            except asyncio.TimeoutError:
                # No human input - let an AI agent speak
                speaker = self._select_next_speaker(agents)
                statement = await speaker.generate_statement_async()
                await self._stream_agent_audio(speaker, statement)

        # Phase 4: Voting
        await self._play_audio(
            self.narrator.generate("The time has come to vote. "
                                   "Who will you banish?")
        )

        # Collect votes (human via voice, AI in parallel)
        human_vote_task = human_handler.get_vote_via_voice()
        ai_vote_tasks = [agent.cast_vote_async() for agent in agents]

        all_votes = await asyncio.gather(human_vote_task, *ai_vote_tasks)

        return RoundTableResult(votes=all_votes)
```

### Pre-Generated Voice Cache (Latency Optimization)

```python
# src/traitorsim/voice/voice_cache.py

COMMON_PHRASES_BY_ARCHETYPE = {
    "the_prodigy": [
        "I've been analyzing the patterns...",
        "The evidence is clear.",
        "That doesn't add up.",
        "I trust my instincts on this one.",
        "We need to think strategically.",
    ],
    "the_charming_sociopath": [
        "Now, let's not be hasty.",
        "I understand your concerns, but...",
        "We're all in this together.",
        "I have nothing to hide.",
        "Trust is everything in this game.",
    ],
    # ... for all archetypes
}

class VoiceCacheManager:
    """Pre-generates common phrases for zero-latency playback."""

    async def warm_cache(self, characters: List[Character]):
        """Pre-generate voices for all common phrases."""

        for character in characters:
            archetype = character.archetype
            phrases = COMMON_PHRASES_BY_ARCHETYPE.get(archetype, [])

            for phrase in phrases:
                cache_key = f"{character.id}:{hash(phrase)}"

                if cache_key not in self.cache:
                    audio = await self.tts_client.text_to_speech(
                        text=phrase,
                        voice_id=character.voice_id,
                        model_id="eleven_v3"  # Quality for cache
                    )
                    self.cache[cache_key] = audio

    def get_cached_or_generate(
        self,
        character_id: str,
        text: str
    ) -> Union[bytes, Awaitable[bytes]]:
        """Return cached audio or generate new."""

        cache_key = f"{character_id}:{hash(text)}"

        if cache_key in self.cache:
            return self.cache[cache_key]  # Instant playback

        # Fall back to real-time generation
        return self._generate_realtime(character_id, text)
```

---

## Part 4: Integration with Existing Architecture

### New Components to Add

```
src/traitorsim/
├── voice/
│   ├── __init__.py
│   ├── elevenlabs_client.py      # ElevenLabs API wrapper
│   ├── deepgram_client.py        # Speech-to-text client
│   ├── voice_library.py          # Character voice configs
│   ├── episode_generator.py      # Episode Mode script generation
│   ├── audio_assembler.py        # Audio mixing and export
│   ├── hitl_handler.py           # HITL voice input processing
│   ├── roundtable_voice.py       # Voice orchestration for RT
│   ├── voice_cache.py            # Pre-generated phrase cache
│   └── soundtrack.py             # Music and SFX library
├── core/
│   ├── game_engine_hitl.py       # New engine variant for HITL
│   └── ...existing files...
└── ...
```

### Game Engine HITL Extension

```python
# src/traitorsim/core/game_engine_hitl.py

class GameEngineHITL(GameEngineAsync):
    """Game engine with Human-in-the-Loop voice support."""

    def __init__(self, config: GameConfig, human_websocket: WebSocket):
        super().__init__(config)

        # Voice components
        self.voice_handler = HITLVoiceHandler(
            stt_client=DeepgramClient(),
            tts_client=ElevenLabsClient(),
            game_engine=self
        )
        self.voice_orchestrator = RoundTableVoiceOrchestrator()
        self.narrator_voice = NarratorVoiceGenerator()
        self.human_ws = human_websocket

    async def _run_roundtable_phase_async(self):
        """Override to use voice-based Round Table."""

        # Stream narrator opening to human
        async for chunk in self.narrator_voice.generate_stream(
            "The Round Table convenes..."
        ):
            await self.human_ws.send_bytes(chunk)

        # Run voice-based Round Table
        result = await self.voice_orchestrator.run_roundtable_voice_session(
            self.game_state,
            self.voice_handler,
            self.player_agents
        )

        # Process banishment
        banished = self._process_votes(result.votes)

        # Dramatic reveal
        async for chunk in self.narrator_voice.generate_stream(
            f"{banished.name}... you have been banished. "
            f"You were a {banished.role.value}."
        ):
            await self.human_ws.send_bytes(chunk)
```

### WebSocket Server for HITL

```python
# src/traitorsim/server/hitl_server.py

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

app = FastAPI()

@app.websocket("/game/{game_id}/voice")
async def voice_websocket(websocket: WebSocket, game_id: str):
    """WebSocket endpoint for HITL voice communication."""

    await websocket.accept()

    # Create or join game
    engine = get_or_create_game(game_id, human_websocket=websocket)

    try:
        # Bidirectional audio streaming
        async def receive_audio():
            while True:
                data = await websocket.receive_bytes()
                yield data

        async def send_audio(audio_stream):
            async for chunk in audio_stream:
                await websocket.send_bytes(chunk)

        # Process human voice and send AI responses
        response_stream = engine.voice_handler.process_voice_input(
            receive_audio()
        )
        await send_audio(response_stream)

    except WebSocketDisconnect:
        # Handle disconnect gracefully
        await engine.handle_human_disconnect()
```

---

## Part 5: Cost Analysis

### ElevenLabs Pricing Structure (December 2025)

| Plan | Monthly Cost | Credits Included | Overage per 1K chars | Annual Discount |
|------|--------------|------------------|----------------------|-----------------|
| **Starter** | $5 | 30,000 | $0.30 | 2 months free |
| **Creator** | $22 | 100,000 | $0.30 | 2 months free |
| **Pro** | $99 | 500,000 | $0.24 | 2 months free |
| **Scale** | $330 | 2,000,000 | $0.18 | 2 months free |
| **Business** | $1,320 | 11,000,000 | $0.12 | 2 months free |

### Model Credit Costs

| Model | Credits/Char | Best For | Latency |
|-------|--------------|----------|---------|
| **Eleven v3 (Text-to-Dialogue)** | 1.0 | Episode Mode - dramatic delivery | Standard |
| **Flash v2.5** | 0.5 | HITL Mode - real-time response | <75ms |
| **Multilingual v2** | 1.0 | Life-like voiceovers | Standard |

---

### Character Count Estimates by Phase

#### BREAKFAST PHASE
| Component | Chars (Range) | Players | Total/Day |
|-----------|---------------|---------|-----------|
| Narrator murder announcement | 200-400 | 1 | 200-400 |
| Player reactions | 50-100 | 22 | 1,100-2,200 |
| **Phase Subtotal** | | | **1,300-2,600** |

#### MISSION PHASE
| Component | Chars (Range) | Players | Total/Day |
|-----------|---------------|---------|-----------|
| Narrator mission intro | 300-500 | 1 | 300-500 |
| Player performance descriptions | 100-150 | 22 | 2,200-3,300 |
| Mission outcome narration | 200-400 | 1 | 200-400 |
| **Phase Subtotal** | | | **2,700-4,200** |

#### SOCIAL PHASE
| Component | Chars (Range) | Conversations | Total/Day |
|-----------|---------------|---------------|-----------|
| Private conversations | 200-400 | 5-10 | 1,000-4,000 |
| Alliance discussions | 300-600 | 2-5 | 600-3,000 |
| **Phase Subtotal** | | | **1,600-7,000** |

#### ROUNDTABLE PHASE
| Component | Chars (Range) | Players | Total/Day |
|-----------|---------------|---------|-----------|
| Narrator intro | 200-300 | 1 | 200-300 |
| Player accusations/defenses | 150-300 | 22 | 3,300-6,600 |
| Vote reasoning (if voiced) | 100-200 | 22 | 2,200-4,400 |
| Banishment announcement | 300-500 | 1 | 300-500 |
| **Phase Subtotal** | | | **6,000-11,800** |

#### TURRET PHASE (Traitors only)
| Component | Chars (Range) | Players | Total/Day |
|-----------|---------------|---------|-----------|
| Murder deliberation | 300-500 | 3-4 traitors | 300-500 |
| Narrator murder description | 200-400 | 1 | 200-400 |
| **Phase Subtotal** | | | **500-900** |

---

### Daily & Seasonal Totals

#### Characters per Day (All Phases)

| Scenario | Breakfast | Mission | Social | Roundtable | Turret | **Daily Total** |
|----------|-----------|---------|--------|------------|--------|-----------------|
| **Minimal** | 1,300 | 2,700 | 1,600 | 6,000 | 500 | **12,100** |
| **Average** | 1,800 | 3,450 | 4,300 | 8,900 | 700 | **19,150** |
| **Maximum** | 2,600 | 4,200 | 7,000 | 11,800 | 900 | **26,500** |

#### Realistic Season Length Analysis

**Real-world reference** ([Wikipedia - The Traitors UK](https://en.wikipedia.org/wiki/The_Traitors_(British_TV_series))):
- UK Season 3 (2025): **12 episodes** across 3 weeks
- UK Celebrity Traitors: **9 episodes**
- US Season 3: **11 episodes** (10 game + 1 reunion)

**Game math**: Starting with 22 players, eliminating ~2/day (1 murder + 1 banishment):
- To reach final 4: eliminate 18 players
- At 2/day: ~9 days minimum
- With "no murder" nights (after Traitor banishment): 10-11 days typical
- **Realistic range: 9-12 days**

**Warning signs** (if season exceeds 12 days):
- Traitors failing to murder (shield overuse, broken logic)
- Faithfuls failing to banish (voting dysfunction)
- Tie-break loops or stalled Round Tables

#### Player Count Decay (Critical for Accurate Costing)

Players are eliminated daily (~1 murder + ~1 banishment = 2/day average):

| Day | Alive Players | Traitors | Cumulative Player-Days |
|-----|---------------|----------|------------------------|
| 1 | 22 | 3 | 22 |
| 2 | 20 | 3 | 42 |
| 3 | 18 | 3 | 60 |
| 4 | 16 | 2-3 | 76 |
| 5 | 14 | 2 | 90 |
| 6 | 12 | 2 | 102 |
| 7 | 10 | 2 | 112 |
| 8 | 8 | 1-2 | 120 |
| 9 | 6 | 1 | 126 |
| 10 | 4 | 1 | **130** |

**Key insight**: A 10-day season has **130 player-days**, not 220 (22×10). This is 59% of a flat calculation!

#### Corrected Day-by-Day Character Counts (Average Scenario)

| Day | Players | Player Chars (@877/player) | Narrator | Turret | **Daily Total** |
|-----|---------|---------------------------|----------|--------|-----------------|
| 1 | 22 | 19,294 | 1,800 | 450 | **21,544** |
| 2 | 20 | 17,540 | 1,800 | 450 | **19,790** |
| 3 | 18 | 15,786 | 1,800 | 450 | **18,036** |
| 4 | 16 | 14,032 | 1,800 | 450 | **16,282** |
| 5 | 14 | 12,278 | 1,800 | 300 | **14,378** |
| 6 | 12 | 10,524 | 1,800 | 300 | **12,624** |
| 7 | 10 | 8,770 | 1,800 | 300 | **10,870** |
| 8 | 8 | 7,016 | 1,800 | 300 | **9,116** |
| 9 | 6 | 5,262 | 1,800 | 200 | **7,262** |
| 10 | 4 | 3,508 | 1,800 | 150 | **5,458** |
| **TOTAL** | — | **114,010** | **18,000** | **3,350** | **~135,360** |

#### Characters per Season (Corrected with Player Decay)

| Season Length | Player-Days | Avg Chars | Pro Plan % | Credits (v3) | Credits (Flash) |
|---------------|-------------|-----------|------------|--------------|-----------------|
| **9 days** | 126 | ~125,000 | 25% | 125,000 | 62,500 |
| **10 days** | 130 | ~135,000 | 27% | 135,000 | 67,500 |
| **11 days** | 132 | ~142,000 | 28% | 142,000 | 71,000 |
| **12 days** | 134 | ~148,000 | 30% | 148,000 | 74,000 |
| ~~15+ days~~ | ~~N/A~~ | ~~BROKEN~~ | — | ~~INVESTIGATE~~ | — |

**Previous estimate was ~40% too high** due to not accounting for eliminations!

---

### Individual Player Agent Costs

#### Per Player Per Phase (Average Scenario)

| Phase | Chars/Player | Credits (v3) | Credits (Flash) |
|-------|--------------|--------------|-----------------|
| Breakfast reaction | 82 | 82 | 41 |
| Mission performance | 150 | 150 | 75 |
| Social conversations | 195 | 195 | 98 |
| Roundtable accusation/defense | 300 | 300 | 150 |
| Roundtable vote reasoning | 150 | 150 | 75 |
| **Total per player/day** | **877** | **877** | **439** |

#### Per Player Per Season (Accounting for Elimination)

Not all 22 players speak all 10 days! Average survival:
- Early eliminee (Day 2-3): ~2,600 chars
- Mid-game eliminee (Day 5-6): ~4,400 chars
- Late eliminee (Day 8-9): ~7,000 chars
- Finalist (Day 10): ~8,770 chars

| Mode | Avg Chars/Player | Credits/Player | Total 22 Players |
|------|------------------|----------------|------------------|
| Episode (v3) | ~5,180 | 5,180 | ~114,000 |
| HITL (Flash) | ~5,180 | 2,590 | ~57,000 |

---

### Episode Mode Cost Models (v3, Corrected for Player Decay)

| Season Length | Characters | Credits | Pro Plan ($99) | **Status** |
|---------------|------------|---------|----------------|------------|
| **9 days (fast)** | ~125,000 | 125,000 | ✅ Within (25%) | $99 |
| **10 days (typical)** | ~135,000 | 135,000 | ✅ Within (27%) | $99 |
| **11 days (extended)** | ~142,000 | 142,000 | ✅ Within (28%) | $99 |
| **12 days (max)** | ~148,000 | 148,000 | ✅ Within (30%) | $99 |

**Pro Plan handles ~3-4 average seasons/month** at $99 flat

---

### HITL Mode Cost Models (Flash v2.5, Corrected for Player Decay)

| Season Length | Characters | Credits (0.5/char) | Pro Plan ($99) | **Status** |
|---------------|------------|-------------------|----------------|------------|
| **9 days (fast)** | ~125,000 | 62,500 | ✅ Within (13%) | $99 |
| **10 days (typical)** | ~135,000 | 67,500 | ✅ Within (14%) | $99 |
| **11 days (extended)** | ~142,000 | 71,000 | ✅ Within (14%) | $99 |
| **12 days (max)** | ~148,000 | 74,000 | ✅ Within (15%) | $99 |

**Flash v2.5's 50% credit reduction means Pro handles ~7 HITL seasons/month**

---

### Hybrid Approach (Narrator v3 + Players Flash, Corrected)

Optimal quality/cost balance with player decay:

| Component | Season Total | Model | Credits/Char | Season Credits |
|-----------|--------------|-------|--------------|----------------|
| **Narrator** | ~18,000 | v3 | 1.0 | 18,000 |
| **Players** | ~117,000 | Flash v2.5 | 0.5 | 58,500 |
| **Season Total** | ~135,000 | Mixed | — | **76,500** |

| Season Length | Total Credits | Pro Plan | Status |
|---------------|---------------|----------|--------|
| 9 days | ~70,000 | ✅ Within (14%) | $99 |
| 10 days | ~76,500 | ✅ Within (15%) | $99 |
| 11 days | ~81,000 | ✅ Within (16%) | $99 |
| 12 days | ~85,000 | ✅ Within (17%) | $99 |

**Hybrid approach allows ~6 seasons/month on Pro with maximum quality for narrator**

---

### Annual Pricing Projection (12 Seasons/Year)

| Mode | Monthly Plan | Annual (10 months) | Cost/Season |
|------|--------------|-------------------|-------------|
| Episode (v3) | $99 × 10 | **$990** | **$82.50** |
| HITL (Flash) | $99 × 10 | **$990** | **$82.50** |
| Hybrid | $99 × 10 | **$990** | **$82.50** |

Annual billing saves 2 months = 17% discount

---

### Optimization Strategies

#### Content Prioritization

| Priority | Content | Voice Status | Savings |
|----------|---------|--------------|---------|
| **Essential** | Murder reveals, banishments, finale | Always voiced | 0% |
| **High Value** | Roundtable accusations, traitor deliberations | Always voiced | 0% |
| **Moderate** | Mission outcomes, key reactions | Voiced | 0% |
| **Optional** | Individual vote reasoning, social small talk | Text or summarized | 30-50% |

#### Caching Opportunities

| Cacheable Element | Frequency | Chars Saved/Season |
|-------------------|-----------|-------------------|
| Greetings ("Good morning") | Daily | ~1,000 |
| Mission type intros (templates) | Per mission type | ~2,000 |
| Standard voting phrases | 22 players × days | ~15,000 |
| **Total Savings** | | **~18,000 (5-10%)** |

#### Summarization Impact

Reducing social phase from 7,000 → 4,000 chars/day:
- Saves 3,000 chars/day
- Saves 60,000 chars/20-day season
- **Saves $14.40/season on Pro plan overage**

---

### Full Cost Summary Table (Corrected with Player Decay)

| Mode | Plan | Season | Chars | Credits | Plan % | Seasons/Mo |
|------|------|--------|-------|---------|--------|------------|
| Episode (fast) | Pro | 9 days | 125,000 | 125,000 | 25% | ~4 |
| Episode (typical) | Pro | 10 days | 135,000 | 135,000 | 27% | ~3-4 |
| Episode (extended) | Pro | 11 days | 142,000 | 142,000 | 28% | ~3 |
| Episode (max) | Pro | 12 days | 148,000 | 148,000 | 30% | ~3 |
| HITL (fast) | Pro | 9 days | 125,000 | 62,500 | 13% | ~8 |
| HITL (typical) | Pro | 10 days | 135,000 | 67,500 | 14% | ~7 |
| HITL (extended) | Pro | 11 days | 142,000 | 71,000 | 14% | ~7 |
| HITL (max) | Pro | 12 days | 148,000 | 74,000 | 15% | ~6-7 |
| Hybrid (typical) | Pro | 10 days | 135,000 | 76,500 | 15% | ~6 |

**Recommendation: Pro Plan ($99/month) handles 3-7 seasons/month with massive headroom**

⚠️ **If your simulation runs 15+ days, investigate game logic bugs before worrying about voice costs!**

---

### Additional API Costs (HITL Mode)

| Service | Usage/Game | Cost/Game |
|---------|------------|-----------|
| Deepgram STT (Nova-3) | ~45 min human speech | ~$0.35 |
| Claude API (21 agents) | ~500K tokens | ~$7.50 |
| Gemini API (Game Master) | ~100K tokens | ~$1.00 |
| **Total non-TTS/game** | | **~$8.85** |

**Complete HITL game cost: ~$99/month ElevenLabs + ~$8.85/game API = ~$108.85 for first game**

---

### Scale Considerations

For high-volume production:

| Plan | Monthly Cost | Credits | Episode Seasons/Mo | HITL Seasons/Mo | Cost/Season |
|------|--------------|---------|--------------------|-----------------| ------------|
| Pro | $99 | 500K | ~3-4 | ~7 | $14-$33 |
| Scale | $330 | 2M | ~15 | ~30 | $11-$22 |
| Business | $1,320 | 11M | ~81 | ~163 | $8-$16 |
| Enterprise | Custom | Negotiated | 150+ | 300+ | <$7 |

*Based on corrected 10-day seasons with ~135,000 chars/season (accounting for player elimination decay)*

---

## Part 6: Implementation Roadmap

### Phase 1: Episode Mode Foundation (2-3 weeks)

- [ ] ElevenLabs API integration
- [ ] Voice library design (13 archetypes → 22 voices)
- [ ] Script generator from game logs
- [ ] Basic audio assembly pipeline
- [ ] Narrator voice selection/cloning

### Phase 2: Episode Mode Polish (2-3 weeks)

- [ ] Soundtrack integration
- [ ] SFX library (stings, transitions)
- [ ] Dynamic mixing (sidechain compression)
- [ ] Confessional generation from diary entries
- [ ] Episode export pipeline (MP3, chapters)

### Phase 3: HITL Infrastructure (3-4 weeks)

- [ ] Deepgram STT integration
- [ ] WebSocket server for voice streaming
- [ ] VAD implementation
- [ ] Voice cache warm-up
- [ ] Basic Round Table voice orchestration

### Phase 4: HITL Intelligence (3-4 weeks)

- [ ] Intent classification for human input
- [ ] AI response generation with emotion tags
- [ ] Multi-speaker turn-taking logic
- [ ] Human vote capture via voice
- [ ] Graceful fallbacks (STT errors, timeouts)

### Phase 5: Frontend Integration (2-3 weeks)

- [ ] Browser WebRTC audio capture
- [ ] Real-time audio playback
- [ ] Visual indicators (who's speaking)
- [ ] Accessibility (captions, transcripts)
- [ ] Mobile compatibility

### Phase 6: Polish & Scale (2-3 weeks)

- [ ] Load testing (concurrent HITL games)
- [ ] Cost optimization (aggressive caching)
- [ ] Analytics dashboard
- [ ] A/B test voice configurations
- [ ] Documentation & tutorials

**Total estimated timeline: 14-20 weeks**

---

## Part 7: Alternative Approaches Considered

### Option A: Google NotebookLM-Style Podcast

**Pros:**
- Simpler implementation
- Two-host format well-suited for recap commentary

**Cons:**
- Only 2 voices (not immersive for 22 characters)
- No customization
- Not suitable for HITL

**Verdict:** Could be useful for "recap" episodes, not primary experience

### Option B: Local TTS (Coqui, XTTS)

**Pros:**
- Zero marginal cost
- Full control
- No rate limits

**Cons:**
- Lower quality
- Higher latency
- More complex deployment
- No instant voice cloning

**Verdict:** Worth exploring for non-critical content (mission narration)

### Option C: Hume AI for Emotion Detection

**Pros:**
- Real-time emotion analysis of human speech
- Could influence AI agent reactions

**Cons:**
- Additional integration complexity
- Extra cost

**Verdict:** Future enhancement for HITL emotional feedback loop

---

## Appendix A: Voice Mapping Table (Gender-Aware)

*Voice IDs validated against [ElevenLabs premade library](https://audio-generation-plugin.com/elevenlabs-premade-voices/) - Dec 2025*

| Archetype | Male Voice | Female Voice | Stability | Style |
|-----------|------------|--------------|-----------|-------|
| The Prodigy | Liam (articulate) | Aria (expressive) | 0.6 | 0.7 |
| The Charming Sociopath | George (warm, trustworthy) | Charlotte (seductive) | 0.75 | 0.5 |
| The Bitter Traitor | Callum (hoarse, dramatic) | Lily (raspy British) | 0.5 | 0.6 |
| The Misguided Survivor | Harry (anxious) | Jessica (expressive) | 0.4 | 0.55 |
| The Zealot | Josh (deep, impactful) | Alice (confident British) | 0.8 | 0.4 |
| The Infatuated Faithful | Chris (casual, relatable) | Matilda (friendly, warm) | 0.55 | 0.7 |
| The Comedic Psychic | Jeremy (excited, energetic) | Mimi (childish, quirky) | 0.4 | 0.85 |
| The Incompetent Authority | Patrick (shouty, bluster) | Glinda (witch-like) | 0.5 | 0.75 |
| The Quirky Outsider | Thomas (calm, deadpan) | Emily (calm) / River (NB) | 0.7 | 0.3 |
| The Romantic | Brian (deep, rich) | Dorothy (pleasant British) | 0.5 | 0.65 |
| The Mischievous Operator | Charlie (casual Australian) | Laura (upbeat, lively) | 0.4 | 0.8 |
| The Smug Player | Joseph (formal British) | Alice (confident British) | 0.7 | 0.5 |
| The Charismatic Leader | Liam (articulate, clear) | Aria (expressive, engaging) | 0.65 | 0.6 |

### Voice Selection Logic

```python
def get_voice_for_persona(persona: Dict) -> str:
    archetype = persona.get("archetype_id", "prodigy")
    gender = persona.get("demographics", {}).get("gender", "female").lower()
    profile = ARCHETYPE_VOICE_PROFILES[archetype]
    gender_key = "male" if gender == "male" else "female"
    return profile[gender_key]["base_voice_id"]
```

---

## Appendix B: Audio Tag Reference

```
# Emotion Tags
[angry]         [anxious]       [calm]          [cold]
[concerned]     [confident]     [confused]      [defensive]
[dramatic]      [excited]       [fearful]       [frustrated]
[happy]         [hesitant]      [hopeful]       [indignant]
[nervous]       [relieved]      [sad]           [sarcastic]
[shocked]       [suspicious]    [tense]         [triumphant]
[whispered]     [worried]

# Delivery Tags
[fast]          [slow]          [loud]          [quiet]
[pause]         [long_pause]    [interrupting]  [overlapping]

# Non-Speech
[sigh]          [laugh]         [gasp]          [crying]
[clearing_throat]               [deep_breath]
```

---

## Appendix C: Sample Episode Script

```json
{
  "episode": 3,
  "day": 3,
  "segments": [
    {
      "speaker": "narrator",
      "voice_id": "narrator_alan",
      "text": "Previously on The Traitors... Patricia's shocking banishment sent ripples through the castle. But was justice served... or did the Traitors claim another victim?",
      "emotion": "[dramatic]",
      "music_cue": "recap_theme"
    },
    {
      "speaker": "narrator",
      "voice_id": "narrator_alan",
      "text": "[pause] Morning breaks. [pause] And one chair... sits empty.",
      "emotion": "[tense][slow]",
      "music_cue": "murder_reveal"
    },
    {
      "speaker": "narrator",
      "voice_id": "narrator_alan",
      "text": "Keeley Barton... will not be joining us for breakfast.",
      "emotion": "[dramatic]",
      "sfx": "revelation_sting"
    },
    {
      "speaker": "rowan_achebe_campbell",
      "voice_id": "archetype_elder_statesperson",
      "text": "No. Not Keeley. [sigh] She was one of the good ones. I'm certain of it.",
      "emotion": "[sad][disappointed]",
      "type": "reaction"
    },
    {
      "speaker": "marcus_brightwell",
      "voice_id": "archetype_charming_sociopath",
      "text": "This is a tragedy. [pause] But it tells us something important. The Traitors are getting bolder.",
      "emotion": "[concerned][calculating]",
      "type": "confessional"
    }
  ]
}
```

---

*Document Version: 1.0*
*Last Updated: December 2025*
*Author: Claude Code + Human Collaboration*
