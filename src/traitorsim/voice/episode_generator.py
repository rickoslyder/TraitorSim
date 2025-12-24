"""Episode generator for complete audio drama production.

Orchestrates full episode scripts with:
- Cold opens and recaps
- Scene transitions
- Music cue integration
- Cliffhangers and previews

Episodes follow the structure from VOICE_INTEGRATION_DESIGN.md:
[0:00-0:45]   COLD OPEN - Recap + cliffhanger
[0:45-2:30]   BREAKFAST REVEAL
[2:30-5:00]   MISSION
[5:00-7:00]   SOCIAL PHASE
[7:00-12:00]  ROUND TABLE
[12:00-14:00] TURRET
[14:00-15:00] NEXT EPISODE PREVIEW
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

from .models import DialogueScript, DialogueSegment, EpisodeScript, SegmentType
from .script_extractor import VoiceScriptExtractor, ExtractionConfig
from .voice_library import NARRATOR_VOICE_ID


@dataclass
class EpisodeGeneratorConfig:
    """Configuration for episode generation."""
    include_cold_open: bool = True
    include_preview: bool = True
    include_social_phase: bool = True
    max_episode_duration_minutes: int = 15
    narrator_style: str = "dramatic"

    # Music cues
    theme_music: str = "main_theme"
    recap_music: str = "recap_theme"
    tension_music: str = "tension_build"


class EpisodeGenerator:
    """Generates complete episode scripts from game data.

    Takes raw game state and produces structured EpisodeScript
    objects with proper narrative structure, transitions, and
    production cues.
    """

    def __init__(self, config: Optional[EpisodeGeneratorConfig] = None):
        """Initialize the generator.

        Args:
            config: Episode generation configuration
        """
        self.config = config or EpisodeGeneratorConfig()
        self.extractor = VoiceScriptExtractor(ExtractionConfig(
            include_social_phase=self.config.include_social_phase
        ))

    def generate_episode(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        previous_day_events: Optional[List[Dict[str, Any]]] = None,
        agent_reasoning: Optional[Dict[str, Dict[str, Any]]] = None,
        season_context: Optional[Dict[str, Any]] = None
    ) -> EpisodeScript:
        """Generate a complete episode script for one game day.

        Args:
            day: Day number (becomes episode number)
            events: Events from GameState for this day
            players: Player data dict
            previous_day_events: Events from previous day (for recap)
            agent_reasoning: Agent reasoning context
            season_context: Season-level context (prize pot, eliminations, etc.)

        Returns:
            Complete EpisodeScript with all scenes
        """
        season_context = season_context or {}

        # Create episode
        episode = EpisodeScript(
            episode_number=day,
            day=day,
            title=self._generate_episode_title(day, events, players)
        )

        # Extract eliminated players
        banishment = next(
            (e for e in events if e.get("type") == "BANISHMENT"),
            None
        )
        murder = next(
            (e for e in events if e.get("type") in ("MURDER", "MURDER_SUCCESS")),
            None
        )

        if banishment:
            episode.eliminated_player_id = banishment.get("target")
        if murder:
            episode.murdered_player_id = murder.get("target")

        # Generate each scene
        if self.config.include_cold_open and previous_day_events:
            episode.cold_open = self._generate_cold_open(
                day, previous_day_events, players, season_context
            )

        episode.breakfast = self._generate_breakfast_scene(
            day, events, players
        )

        episode.mission = self._generate_mission_scene(
            day, events, players
        )

        if self.config.include_social_phase:
            episode.social = self._generate_social_scene(
                day, events, players
            )

        episode.roundtable = self._generate_roundtable_scene(
            day, events, players, agent_reasoning
        )

        episode.turret = self._generate_turret_scene(
            day, events, players
        )

        if self.config.include_preview:
            episode.preview = self._generate_preview(
                day, events, players, season_context
            )

        # Extract key moments for metadata
        episode.key_moments = self._extract_key_moments(events, players)

        return episode

    def generate_season(
        self,
        game_state: Any,
        agent_reasoning_by_day: Optional[Dict[int, Dict[str, Dict[str, Any]]]] = None
    ) -> List[EpisodeScript]:
        """Generate all episodes for a complete season.

        Args:
            game_state: Complete GameState with all events
            agent_reasoning_by_day: Reasoning context organized by day

        Returns:
            List of EpisodeScript objects, one per day
        """
        agent_reasoning_by_day = agent_reasoning_by_day or {}

        # Convert players to dict
        players_dict = {}
        for player in game_state.players:
            players_dict[player.id] = {
                "id": player.id,
                "name": player.name,
                "role": player.role.value if hasattr(player.role, 'value') else player.role,
                "alive": player.alive,
                "personality": player.personality,
                "archetype_id": player.archetype_id,
                "demographics": player.demographics,
                "backstory": player.backstory,
            }

        # Group events by day
        events_by_day: Dict[int, List[Dict[str, Any]]] = {}
        for event in game_state.events:
            day = event.get("day", 1)
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(event)

        # Generate episodes
        episodes = []
        days = sorted(events_by_day.keys())

        for i, day in enumerate(days):
            previous_events = events_by_day.get(days[i-1]) if i > 0 else None

            episode = self.generate_episode(
                day=day,
                events=events_by_day[day],
                players=players_dict,
                previous_day_events=previous_events,
                agent_reasoning=agent_reasoning_by_day.get(day),
                season_context={
                    "prize_pot": game_state.prize_pot,
                    "total_days": len(days),
                    "current_episode": i + 1,
                    "alive_count": len([p for p in players_dict.values() if p.get("alive", True)]),
                }
            )
            episodes.append(episode)

        return episodes

    # =========================================================================
    # SCENE GENERATORS
    # =========================================================================

    def _generate_cold_open(
        self,
        day: int,
        previous_events: List[Dict[str, Any]],
        players: Dict[str, Any],
        season_context: Dict[str, Any]
    ) -> DialogueScript:
        """Generate cold open / recap scene."""
        script = DialogueScript(
            title=f"Day {day} - Cold Open",
            metadata={"scene": "cold_open", "day": day}
        )

        # Theme music intro
        script.add_narrator(
            text="Previously on The Traitors...",
            emotion="dramatic",
            music_cue=self.config.recap_music,
            pause_after_ms=1000,
        )

        # Find key events from previous day
        prev_banishment = next(
            (e for e in previous_events if e.get("type") == "BANISHMENT"),
            None
        )
        prev_murder = next(
            (e for e in previous_events if e.get("type") in ("MURDER", "MURDER_SUCCESS")),
            None
        )

        # Recap banishment
        if prev_banishment:
            banished_id = prev_banishment.get("target")
            banished = players.get(banished_id, {})
            banished_name = banished.get("name", "Someone")
            banished_role = banished.get("role", "faithful")

            if isinstance(banished_role, str):
                role_str = banished_role
            else:
                role_str = banished_role.value if hasattr(banished_role, 'value') else "faithful"

            if role_str == "traitor":
                script.add_narrator(
                    text=f"{banished_name} was unmasked as a Traitor. "
                         f"But how many more remain hidden?",
                    emotion="triumphant",
                )
            else:
                script.add_narrator(
                    text=f"{banished_name} was banished... "
                         f"but they were innocent. The Traitors still lurk.",
                    emotion="somber",
                )

        # Teaser for today
        script.add_narrator(
            text="Tonight... more secrets will be revealed. "
                 "More alliances will be tested. "
                 "And someone else... will be going home.",
            emotion="tense",
            music_cue=self.config.tension_music,
        )

        return script

    def _generate_breakfast_scene(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any]
    ) -> DialogueScript:
        """Generate breakfast reveal scene."""
        script = DialogueScript(
            title=f"Day {day} - Breakfast",
            metadata={"scene": "breakfast", "day": day}
        )

        # Extract using main extractor
        breakfast_events = [e for e in events if e.get("phase", "").lower() in ("breakfast", "state_breakfast")]

        self.extractor._extract_breakfast(script, breakfast_events, players, day)

        return script

    def _generate_mission_scene(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any]
    ) -> DialogueScript:
        """Generate mission challenge scene."""
        script = DialogueScript(
            title=f"Day {day} - Mission",
            metadata={"scene": "mission", "day": day}
        )

        mission_events = [e for e in events if e.get("phase", "").lower() in ("mission", "state_mission")]

        self.extractor._extract_mission(script, mission_events, players, day)

        return script

    def _generate_social_scene(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any]
    ) -> DialogueScript:
        """Generate social/alliance building scene."""
        script = DialogueScript(
            title=f"Day {day} - Social",
            metadata={"scene": "social", "day": day}
        )

        social_events = [e for e in events if e.get("phase", "").lower() in ("social", "state_social")]

        self.extractor._extract_social(script, social_events, players, day)

        return script

    def _generate_roundtable_scene(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        agent_reasoning: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> DialogueScript:
        """Generate Round Table voting scene."""
        script = DialogueScript(
            title=f"Day {day} - Round Table",
            metadata={"scene": "roundtable", "day": day}
        )

        roundtable_events = [e for e in events if e.get("phase", "").lower() in ("roundtable", "state_roundtable")]

        self.extractor._extract_roundtable(
            script, roundtable_events, players, day, agent_reasoning
        )

        return script

    def _generate_turret_scene(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any]
    ) -> DialogueScript:
        """Generate Turret (Traitor meeting) scene."""
        script = DialogueScript(
            title=f"Day {day} - Turret",
            metadata={"scene": "turret", "day": day}
        )

        turret_events = [e for e in events if e.get("phase", "").lower() in ("turret", "state_turret")]

        self.extractor._extract_turret(script, turret_events, players, day)

        return script

    def _generate_preview(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any],
        season_context: Dict[str, Any]
    ) -> DialogueScript:
        """Generate next episode preview."""
        script = DialogueScript(
            title=f"Day {day} - Preview",
            metadata={"scene": "preview", "day": day}
        )

        alive_count = season_context.get("alive_count", 10)
        prize_pot = season_context.get("prize_pot", 0)

        script.add_narrator(
            text="Next time on The Traitors...",
            emotion="dramatic",
            music_cue=self.config.theme_music,
        )

        script.add_narrator(
            text=f"With {alive_count} players remaining "
                 f"and £{prize_pot:,} in the pot... "
                 f"the stakes have never been higher.",
            emotion="tense",
        )

        script.add_narrator(
            text="Alliances will shatter. Trust will be tested. "
                 "And another player... will meet their fate.",
            emotion="ominous",
            pause_after_ms=2000,
        )

        return script

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _generate_episode_title(
        self,
        day: int,
        events: List[Dict[str, Any]],
        players: Dict[str, Any]
    ) -> str:
        """Generate a dramatic episode title."""
        # Find key events
        banishment = next(
            (e for e in events if e.get("type") == "BANISHMENT"),
            None
        )

        if banishment:
            banished = players.get(banishment.get("target"), {})
            role = banished.get("role", "faithful")
            if isinstance(role, str):
                role_str = role
            else:
                role_str = role.value if hasattr(role, 'value') else "faithful"

            if role_str == "traitor":
                return f"Day {day}: The Unmasking"
            else:
                return f"Day {day}: An Innocent Falls"

        return f"Day {day}: The Hunt Continues"

    def _extract_key_moments(
        self,
        events: List[Dict[str, Any]],
        players: Dict[str, Any]
    ) -> List[str]:
        """Extract key moments for episode metadata."""
        moments = []

        for event in events:
            event_type = event.get("type", "")

            if event_type in ("MURDER", "MURDER_SUCCESS"):
                victim = players.get(event.get("target"), {})
                moments.append(f"Murder of {victim.get('name', 'unknown')}")

            elif event_type == "BANISHMENT":
                banished = players.get(event.get("target"), {})
                role = banished.get("role", "faithful")
                if isinstance(role, str):
                    role_str = role
                else:
                    role_str = role.value if hasattr(role, 'value') else "faithful"
                moments.append(
                    f"Banishment of {banished.get('name', 'unknown')} ({role_str})"
                )

            elif event_type == "SHIELD_AWARDED":
                winner = players.get(event.get("target"), {})
                moments.append(f"Shield awarded to {winner.get('name', 'unknown')}")

            elif event_type == "RECRUITMENT_ACCEPTED":
                recruit = players.get(event.get("target"), {})
                moments.append(f"New Traitor: {recruit.get('name', 'unknown')}")

        return moments


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def generate_episode_from_game_state(
    game_state: Any,
    day: Optional[int] = None,
    agent_reasoning: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[EpisodeGeneratorConfig] = None
) -> EpisodeScript:
    """Convenience function to generate episode from GameState.

    Args:
        game_state: GameState object
        day: Specific day (defaults to current)
        agent_reasoning: Agent reasoning context
        config: Generator configuration

    Returns:
        Complete EpisodeScript
    """
    generator = EpisodeGenerator(config)

    # Convert players
    players_dict = {}
    for player in game_state.players:
        players_dict[player.id] = {
            "id": player.id,
            "name": player.name,
            "role": player.role.value if hasattr(player.role, 'value') else player.role,
            "alive": player.alive,
            "personality": player.personality,
            "archetype_id": player.archetype_id,
            "demographics": player.demographics,
        }

    target_day = day or game_state.day

    # Get events for target day
    day_events = [e for e in game_state.events if e.get("day") == target_day]

    # Get previous day events for recap
    prev_day_events = [e for e in game_state.events if e.get("day") == target_day - 1]

    return generator.generate_episode(
        day=target_day,
        events=day_events,
        players=players_dict,
        previous_day_events=prev_day_events if prev_day_events else None,
        agent_reasoning=agent_reasoning,
        season_context={
            "prize_pot": game_state.prize_pot,
            "alive_count": len(game_state.alive_players),
        }
    )


def export_season_scripts(
    game_state: Any,
    output_path: str,
    agent_reasoning_by_day: Optional[Dict[int, Dict[str, Dict[str, Any]]]] = None,
    config: Optional[EpisodeGeneratorConfig] = None
) -> None:
    """Export all episode scripts for a season to JSON files.

    Args:
        game_state: Complete GameState
        output_path: Directory path for output files
        agent_reasoning_by_day: Reasoning context by day
        config: Generator configuration
    """
    import os

    generator = EpisodeGenerator(config)
    episodes = generator.generate_season(game_state, agent_reasoning_by_day)

    os.makedirs(output_path, exist_ok=True)

    # Export each episode
    for episode in episodes:
        filename = f"episode_{episode.episode_number:02d}.json"
        filepath = os.path.join(output_path, filename)

        with open(filepath, 'w') as f:
            f.write(episode.to_json())

    # Export season summary
    summary = {
        "season_title": "The Traitors: AI Edition",
        "episode_count": len(episodes),
        "total_duration": sum(
            sum(
                scene.estimate_duration_seconds()
                for scene in [ep.cold_open, ep.breakfast, ep.mission,
                             ep.social, ep.roundtable, ep.turret, ep.preview]
                if scene
            )
            for ep in episodes
        ),
        "total_credits_v3": sum(ep.estimate_credits("eleven_v3") for ep in episodes),
        "total_credits_flash": sum(ep.estimate_credits("flash") for ep in episodes),
        "episodes": [
            {
                "episode": ep.episode_number,
                "title": ep.title,
                "eliminated": ep.eliminated_player_id,
                "murdered": ep.murdered_player_id,
                "key_moments": ep.key_moments,
            }
            for ep in episodes
        ]
    }

    summary_path = os.path.join(output_path, "season_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
