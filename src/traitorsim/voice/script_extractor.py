"""Script extractor for converting game events to dialogue scripts.

Reads GameState.events and agent reasoning to produce DialogueScript
objects ready for voice synthesis.

The extractor handles all game phases:
- Breakfast: Murder reveal and survivor reactions
- Mission: Challenge narration and outcomes
- Social: Alliance conversations and whispered suspicions
- Round Table: Accusations, defenses, and voting drama
- Turret: Traitor deliberation and murder selection
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import random

from .models import DialogueScript, DialogueSegment, SegmentType, EmotionIntensity
from .voice_library import (
    get_voice_for_persona,
    get_voice_config_for_persona,
    NARRATOR_VOICE_ID,
    get_archetype_emotional_range,
)
from .emotion_engine import EmotionInferenceEngine, EmotionContext


@dataclass
class ExtractionConfig:
    """Configuration for script extraction."""
    include_all_votes: bool = False           # Include every individual vote
    include_confessionals: bool = True        # Add player internal monologues
    max_reactions_per_event: int = 3          # Limit survivor reactions
    narrator_style: str = "dramatic"          # Narrator emotional style
    include_social_phase: bool = True         # Include social phase dialogue
    social_conversation_limit: int = 3        # Max social conversations per day


class VoiceScriptExtractor:
    """Extracts voice-ready scripts from game state and events.

    Transforms structured game data into DialogueScript objects
    with appropriate emotional tags and production cues.
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """Initialize the extractor.

        Args:
            config: Extraction configuration options
        """
        self.config = config or ExtractionConfig()
        self.emotion_engine = EmotionInferenceEngine()

    def extract_day(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        agent_reasoning: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> DialogueScript:
        """Extract complete script for one game day.

        Args:
            day: Day number
            events: List of event dicts from GameState.events
            players: Dict of player_id -> player data
            agent_reasoning: Optional dict of player_id -> reasoning context

        Returns:
            DialogueScript containing all voiced segments for the day
        """
        script = DialogueScript(
            title=f"Day {day}",
            metadata={
                "day": day,
                "event_count": len(events),
                "player_count": len([p for p in players.values() if p.get("alive", True)]),
            }
        )

        # Filter events for this day
        day_events = [e for e in events if e.get("day") == day]

        # Group events by phase
        phases = self._group_by_phase(day_events)

        # Extract each phase
        if "breakfast" in phases:
            self._extract_breakfast(script, phases["breakfast"], players, day)

        if "mission" in phases:
            self._extract_mission(script, phases["mission"], players, day)

        if "social" in phases and self.config.include_social_phase:
            self._extract_social(script, phases["social"], players, day)

        if "roundtable" in phases:
            self._extract_roundtable(
                script, phases["roundtable"], players, day, agent_reasoning
            )

        if "turret" in phases:
            self._extract_turret(script, phases["turret"], players, day)

        return script

    def extract_phase(
        self,
        phase: str,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        day: int,
        agent_reasoning: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> DialogueScript:
        """Extract script for a single game phase.

        Args:
            phase: Phase name (breakfast, mission, social, roundtable, turret)
            events: List of events for this phase
            players: Dict of player data
            day: Current day number
            agent_reasoning: Optional reasoning context

        Returns:
            DialogueScript for this phase
        """
        script = DialogueScript(
            title=f"Day {day} - {phase.title()}",
            metadata={"day": day, "phase": phase}
        )

        if phase == "breakfast":
            self._extract_breakfast(script, events, players, day)
        elif phase == "mission":
            self._extract_mission(script, events, players, day)
        elif phase == "social":
            self._extract_social(script, events, players, day)
        elif phase == "roundtable":
            self._extract_roundtable(script, events, players, day, agent_reasoning)
        elif phase == "turret":
            self._extract_turret(script, events, players, day)

        return script

    # =========================================================================
    # BREAKFAST PHASE
    # =========================================================================

    def _extract_breakfast(
        self,
        script: DialogueScript,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        day: int
    ) -> None:
        """Extract breakfast phase script (murder reveal).

        Creates:
        - Narrator murder announcement
        - Survivor reactions (limited to top affected)
        - Confessional segments
        """
        # Find murder event
        murder_event = next(
            (e for e in events if e.get("type") in ("MURDER", "MURDER_SUCCESS")),
            None
        )

        if not murder_event:
            # No murder (rare - maybe first night or shield blocked)
            script.add_narrator(
                text="Morning breaks over Ardross Castle. "
                     "Remarkably... everyone is present at breakfast.",
                emotion="surprised",
                music_cue="morning_relief",
                phase="breakfast",
                day=day
            )
            return

        victim_id = murder_event.get("target")
        victim = players.get(victim_id, {})
        victim_name = victim.get("name", "Someone")

        # Narrator murder reveal
        script.add_narrator(
            text=f"Dawn breaks over the castle. As the players gather for breakfast... "
                 f"one chair sits empty. [pause] {victim_name}... "
                 f"will not be joining us today.",
            emotion="dramatic",
            music_cue="murder_reveal",
            sfx="revelation_sting",
            pause_before_ms=1000,
            pause_after_ms=1500,
            phase="breakfast",
            day=day,
            event_type="MURDER"
        )

        # Survivor reactions
        self._add_survivor_reactions(script, victim_id, victim_name, players, day)

    def _add_survivor_reactions(
        self,
        script: DialogueScript,
        victim_id: str,
        victim_name: str,
        players: Dict[str, Any],
        day: int
    ) -> None:
        """Add survivor reaction segments to murder reveal."""
        alive_players = [
            (pid, p) for pid, p in players.items()
            if p.get("alive", True) and pid != victim_id
        ]

        # Select top reactors (could be based on trust matrix, but simplified here)
        # For now, select randomly with archetype diversity
        reactors = self._select_reactors(alive_players, self.config.max_reactions_per_event)

        reaction_templates = [
            "No... not {victim}. I can't believe it.",
            "{victim}? But they were... I thought they were safe.",
            "This changes everything. Whoever did this...",
            "We're running out of time. The Traitors are getting bolder.",
            "I had my suspicions about {victim}, but... not like this.",
        ]

        for player_id, player in reactors:
            # Infer emotion based on personality
            emotion_result = self.emotion_engine.infer(
                context=EmotionContext.REACTION_MURDER,
                personality=player.get("personality", {}),
                role=player.get("role", "faithful"),
            )

            # Generate reaction text
            template = random.choice(reaction_templates)
            text = template.format(victim=victim_name)

            script.add_character(
                speaker_id=player_id,
                voice_id=get_voice_for_persona(player),
                text=text,
                emotions=emotion_result.to_tags(),
                segment_type=SegmentType.REACTION,
                phase="breakfast",
                day=day,
                related_player_ids=[victim_id],
            )

    # =========================================================================
    # MISSION PHASE
    # =========================================================================

    def _extract_mission(
        self,
        script: DialogueScript,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        day: int
    ) -> None:
        """Extract mission phase script.

        Creates:
        - Mission briefing narration
        - Key player moments
        - Outcome announcement
        """
        mission_complete = next(
            (e for e in events if e.get("type") == "MISSION_COMPLETE"),
            None
        )

        if not mission_complete:
            return

        mission_data = mission_complete.get("data", {})
        mission_name = mission_data.get("mission_name", "The Challenge")
        success = mission_data.get("success", True)
        prize_added = mission_data.get("prize_added", 0)

        # Mission intro
        script.add_narrator(
            text=f"Today's mission: {mission_name}. "
                 f"The prize pot hangs in the balance.",
            emotion="focused",
            music_cue="mission_energy",
            phase="mission",
            day=day,
        )

        # Mission outcome
        if success:
            script.add_narrator(
                text=f"Against the odds... they've done it! "
                     f"£{prize_added:,} added to the pot.",
                emotion="excited",
                sfx="mission_success_sting",
                phase="mission",
                day=day,
            )
        else:
            script.add_narrator(
                text=f"Disaster. The mission fails. "
                     f"The prize pot remains unchanged.",
                emotion="disappointed",
                sfx="mission_fail_sting",
                phase="mission",
                day=day,
            )

        # Shield/Dagger awards
        shield_event = next(
            (e for e in events if e.get("type") == "SHIELD_AWARDED"),
            None
        )
        if shield_event:
            winner_id = shield_event.get("target")
            winner = players.get(winner_id, {})
            script.add_narrator(
                text=f"{winner.get('name', 'Someone')} wins the Shield. "
                     f"Tonight... they are untouchable.",
                emotion="dramatic",
                sfx="shield_award",
                phase="mission",
                day=day,
            )

    # =========================================================================
    # SOCIAL PHASE
    # =========================================================================

    def _extract_social(
        self,
        script: DialogueScript,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        day: int
    ) -> None:
        """Extract social phase script (alliance building).

        Creates:
        - Key alliance conversations
        - Whispered suspicions
        - Confessional segments
        """
        # Social phase often has less structured events
        # Generate atmospheric narration
        script.add_narrator(
            text="As afternoon arrives, the players scatter across the castle. "
                 "Alliances form. Suspicions brew. Whispers fill the corridors.",
            emotion="tense",
            music_cue="social_ambiance",
            phase="social",
            day=day,
        )

        # Add confessionals for key players if configured
        if self.config.include_confessionals:
            self._add_social_confessionals(script, players, day)

    def _add_social_confessionals(
        self,
        script: DialogueScript,
        players: Dict[str, Any],
        day: int
    ) -> None:
        """Add confessional segments for social phase."""
        alive_players = [
            (pid, p) for pid, p in players.items()
            if p.get("alive", True)
        ]

        # Select a few players for confessionals
        confessors = random.sample(
            alive_players,
            min(2, len(alive_players))
        )

        confessional_templates = {
            "faithful": [
                "I'm watching everyone closely. Someone here is lying.",
                "The tension is unbearable. I don't know who to trust anymore.",
                "I need to find the Traitors before it's too late.",
            ],
            "traitor": [
                "They have no idea. And I intend to keep it that way.",
                "The game is going perfectly. Just need to stay patient.",
                "Watching them scramble... it's almost too easy.",
            ]
        }

        for player_id, player in confessors:
            role = player.get("role", "faithful")
            if isinstance(role, str):
                role_key = role
            else:
                role_key = role.value if hasattr(role, 'value') else "faithful"

            templates = confessional_templates.get(role_key, confessional_templates["faithful"])
            text = random.choice(templates)

            emotion_result = self.emotion_engine.infer(
                context=EmotionContext.CONFESSIONAL,
                personality=player.get("personality", {}),
                role=role_key,
            )

            script.add_character(
                speaker_id=player_id,
                voice_id=get_voice_for_persona(player),
                text=text,
                emotions=emotion_result.to_tags(),
                segment_type=SegmentType.CONFESSIONAL,
                phase="social",
                day=day,
            )

    # =========================================================================
    # ROUND TABLE PHASE
    # =========================================================================

    def _extract_roundtable(
        self,
        script: DialogueScript,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        day: int,
        agent_reasoning: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> None:
        """Extract Round Table phase script.

        Creates:
        - Narrator opening
        - Key accusations and defenses
        - Voting tension
        - Banishment reveal
        """
        agent_reasoning = agent_reasoning or {}

        # Narrator opens Round Table
        script.add_narrator(
            text="The Round Table convenes. "
                 "Suspicion hangs heavy in the air. "
                 "Who will face banishment tonight?",
            emotion="tense",
            music_cue="roundtable_deliberation",
            pause_after_ms=1000,
            phase="roundtable",
            day=day,
        )

        # Extract vote tally
        vote_tally = next(
            (e for e in events if e.get("type") == "VOTE_TALLY"),
            None
        )

        # Extract individual votes if configured
        if self.config.include_all_votes:
            vote_events = [e for e in events if e.get("type") == "VOTE"]
            self._add_vote_reasoning(script, vote_events, players, day, agent_reasoning)

        # Find banishment
        banishment = next(
            (e for e in events if e.get("type") == "BANISHMENT"),
            None
        )

        if banishment:
            banished_id = banishment.get("target")
            banished = players.get(banished_id, {})
            banished_name = banished.get("name", "Someone")
            banished_role = banished.get("role", "faithful")

            if isinstance(banished_role, str):
                role_str = banished_role
            else:
                role_str = banished_role.value if hasattr(banished_role, 'value') else "faithful"

            # Add defense from banished player
            self._add_defense(script, banished_id, banished, day, agent_reasoning)

            # Voting climax
            script.add_narrator(
                text="The votes are in. [long_pause] "
                     f"The person leaving us tonight is... [pause] "
                     f"{banished_name}.",
                emotion="dramatic",
                music_cue="vote_drumroll",
                sfx="revelation_sting",
                pause_before_ms=500,
                pause_after_ms=2000,
                phase="roundtable",
                day=day,
                event_type="BANISHMENT",
            )

            # Role reveal
            if role_str == "traitor":
                script.add_narrator(
                    text=f"{banished_name}... you were a Traitor.",
                    emotion="triumphant",
                    sfx="traitor_reveal_chord",
                    phase="roundtable",
                    day=day,
                )
            else:
                script.add_narrator(
                    text=f"{banished_name}... you were a Faithful.",
                    emotion="sad",
                    sfx="faithful_reveal_somber",
                    phase="roundtable",
                    day=day,
                )

    def _add_vote_reasoning(
        self,
        script: DialogueScript,
        vote_events: List[Dict[str, Any]],
        players: Dict[str, Any],
        day: int,
        agent_reasoning: Dict[str, Dict[str, Any]]
    ) -> None:
        """Add vote statements with reasoning."""
        for vote in vote_events[:5]:  # Limit to 5 key votes
            voter_id = vote.get("actor")
            target_id = vote.get("target")
            voter = players.get(voter_id, {})
            target = players.get(target_id, {})

            # Get reasoning if available
            reasoning = agent_reasoning.get(voter_id, {}).get("vote_result", {})
            reasoning_text = reasoning.get("reasoning", "")

            if reasoning_text:
                # Truncate to reasonable length
                text = reasoning_text[:200]
                if len(reasoning_text) > 200:
                    text += "..."
            else:
                # Generate generic vote statement
                text = f"I'm voting for {target.get('name', 'them')}."

            emotion_result = self.emotion_engine.infer(
                context=EmotionContext.VOTING,
                personality=voter.get("personality", {}),
                role=voter.get("role", "faithful") if isinstance(voter.get("role"), str)
                     else voter.get("role", "").value if hasattr(voter.get("role", ""), 'value') else "faithful",
            )

            script.add_character(
                speaker_id=voter_id,
                voice_id=get_voice_for_persona(voter),
                text=text,
                emotions=emotion_result.to_tags(),
                segment_type=SegmentType.DIALOGUE,
                phase="roundtable",
                day=day,
                event_type="VOTE",
                related_player_ids=[target_id],
            )

    def _add_defense(
        self,
        script: DialogueScript,
        player_id: str,
        player: Dict[str, Any],
        day: int,
        agent_reasoning: Dict[str, Dict[str, Any]]
    ) -> None:
        """Add defense statement from accused player."""
        # Get role for emotion inference
        role = player.get("role", "faithful")
        if isinstance(role, str):
            role_str = role
        else:
            role_str = role.value if hasattr(role, 'value') else "faithful"

        # Infer emotions
        emotion_result = self.emotion_engine.infer(
            context=EmotionContext.DEFENSE,
            personality=player.get("personality", {}),
            role=role_str,
            stress_level=0.7,  # Being banished = high stress
        )

        # Generate defense text
        if role_str == "traitor":
            templates = [
                "I've done nothing wrong. You're making a terrible mistake.",
                "This is exactly what the real Traitors want. Think about it.",
                "I can't believe you'd all turn on me like this.",
            ]
        else:
            templates = [
                "I'm not a Traitor! I've been fighting for us this whole time!",
                "You're banishing an innocent person. The Traitors win tonight.",
                "Please, listen to me. I have nothing to hide!",
            ]

        text = random.choice(templates)

        script.add_character(
            speaker_id=player_id,
            voice_id=get_voice_for_persona(player),
            text=text,
            emotions=emotion_result.to_tags(),
            intensity=EmotionIntensity.HEIGHTENED,
            segment_type=SegmentType.DIALOGUE,
            phase="roundtable",
            day=day,
            pause_before_ms=500,
        )

    # =========================================================================
    # TURRET PHASE
    # =========================================================================

    def _extract_turret(
        self,
        script: DialogueScript,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        day: int
    ) -> None:
        """Extract Turret phase script (Traitor meeting).

        Creates:
        - Whispered Traitor deliberation
        - Murder selection
        - Ominous narrator close
        """
        # Find traitors
        traitors = [
            (pid, p) for pid, p in players.items()
            if p.get("alive", True) and
               (p.get("role") == "traitor" or
                (hasattr(p.get("role", ""), 'value') and p.get("role").value == "traitor"))
        ]

        if not traitors:
            return

        # Narrator sets the scene
        script.add_narrator(
            text="Night falls. The castle sleeps. "
                 "But in the Turret... the Traitors gather.",
            emotion="cold",
            music_cue="turret_sinister",
            phase="turret",
            day=day,
        )

        # Find murder event
        murder_event = next(
            (e for e in events if e.get("type") in ("MURDER", "MURDER_ATTEMPT")),
            None
        )

        if murder_event:
            victim_id = murder_event.get("target")
            victim = players.get(victim_id, {})
            victim_name = victim.get("name", "someone")

            # Lead traitor announces decision
            lead_traitor_id, lead_traitor = traitors[0]

            emotion_result = self.emotion_engine.infer(
                context=EmotionContext.TURRET_DELIBERATION,
                personality=lead_traitor.get("personality", {}),
                role="traitor",
            )

            script.add_character(
                speaker_id=lead_traitor_id,
                voice_id=get_voice_for_persona(lead_traitor),
                text=f"It has to be {victim_name}. They're too dangerous to keep around.",
                emotions=["whispered", "cold", "calculating"],
                segment_type=SegmentType.WHISPER,
                phase="turret",
                day=day,
                related_player_ids=[victim_id],
            )

        # Narrator closes
        script.add_narrator(
            text="The decision is made. Come morning... "
                 "one more Faithful will be gone.",
            emotion="ominous",
            music_cue="murder_foreshadow",
            phase="turret",
            day=day,
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _group_by_phase(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group events by game phase."""
        phases: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            phase = event.get("phase", "unknown")
            # Normalize phase names
            phase = phase.lower().replace("state_", "")
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(event)
        return phases

    def _select_reactors(
        self,
        players: List[Tuple[str, Dict[str, Any]]],
        count: int
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Select players for reaction segments.

        Tries to ensure archetype diversity.
        """
        if len(players) <= count:
            return players

        # Group by archetype
        by_archetype: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        for pid, player in players:
            arch = player.get("archetype_id", "unknown")
            if arch not in by_archetype:
                by_archetype[arch] = []
            by_archetype[arch].append((pid, player))

        # Select one from each archetype until we have enough
        selected = []
        archetypes = list(by_archetype.keys())
        random.shuffle(archetypes)

        for arch in archetypes:
            if len(selected) >= count:
                break
            player = random.choice(by_archetype[arch])
            selected.append(player)

        return selected


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def extract_script_from_game_state(
    game_state: Any,
    day: Optional[int] = None,
    agent_reasoning: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[ExtractionConfig] = None
) -> DialogueScript:
    """Convenience function to extract script directly from GameState.

    Args:
        game_state: GameState object
        day: Specific day to extract (defaults to current day)
        agent_reasoning: Optional reasoning context from agents
        config: Extraction configuration

    Returns:
        DialogueScript for the specified day
    """
    extractor = VoiceScriptExtractor(config)

    # Convert players to dict format
    players_dict = {}
    for player in game_state.players:
        player_data = {
            "id": player.id,
            "name": player.name,
            "role": player.role,
            "alive": player.alive,
            "personality": player.personality,
            "archetype_id": player.archetype_id,
            "demographics": player.demographics,
        }
        players_dict[player.id] = player_data

    target_day = day or game_state.day

    return extractor.extract_day(
        day=target_day,
        events=game_state.events,
        players=players_dict,
        agent_reasoning=agent_reasoning
    )
