"""File-based memory system for player agents."""

import logging
from pathlib import Path
from typing import List, Dict, TYPE_CHECKING
import csv

if TYPE_CHECKING:
    from ..core.game_state import Player
    from ..core.config import GameConfig


class MemoryManager:
    """
    File-based memory system for player agents.
    Implements progressive disclosure pattern.
    """

    def __init__(self, player: "Player", config: "GameConfig"):
        """Initialize memory manager for a player."""
        self.player = player
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Memory directory: data/memories/player_{id}/
        self.base_path = Path("data/memories") / player.id
        self.base_path.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Initialize memory files."""
        try:
            # Create profile.md
            profile_path = self.base_path / "profile.md"
            profile_path.write_text(self._create_profile())

            # Create suspects.csv
            suspects_path = self.base_path / "suspects.csv"
            self._initialize_suspects_csv(suspects_path)

            # Create diary directory
            diary_path = self.base_path / "diary"
            diary_path.mkdir(exist_ok=True)

            self.logger.info(f"Memory initialized for {self.player.name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize memory for {self.player.name}: {e}")

    def _create_profile(self) -> str:
        """Create initial profile document with persona backstory."""
        # Base profile with role and personality
        profile = f"""# Agent Profile: {self.player.name}

## Role
{self.player.role.value.upper()}
"""

        # Add archetype if available
        if self.player.archetype_name:
            profile += f"""
## Archetype
{self.player.archetype_name}
"""

        # Personality traits
        profile += f"""
## Personality Traits (Big Five)
- Openness: {self.player.personality['openness']:.2f}
- Conscientiousness: {self.player.personality['conscientiousness']:.2f}
- Extraversion: {self.player.personality['extraversion']:.2f}
- Agreeableness: {self.player.personality['agreeableness']:.2f}
- Neuroticism: {self.player.personality['neuroticism']:.2f}

## Stats
- Intellect: {self.player.stats['intellect']:.2f}
- Dexterity: {self.player.stats['dexterity']:.2f}
- Social Influence: {self.player.stats['social_influence']:.2f}
"""

        # Add backstory and demographics if available
        if self.player.backstory:
            profile += f"""
## Backstory
{self.player.backstory}
"""

        if self.player.demographics:
            profile += f"""
## Demographics
- Age: {self.player.demographics.get('age', 'Unknown')}
- Location: {self.player.demographics.get('location', 'Unknown')}
- Occupation: {self.player.demographics.get('occupation', 'Unknown')}
- Background: {self.player.demographics.get('ethnicity', 'Unknown')}
"""

        # Add strategic approach if available
        if self.player.strategic_profile:
            profile += f"""
## Strategic Approach
{self.player.strategic_profile}
"""

        # Mission statement
        profile += f"""
## Mission
{"Find and eliminate all Traitors." if self.player.role.value == "faithful" else "Survive undetected and eliminate Faithfuls."}
"""

        return profile

    def _initialize_suspects_csv(self, path: Path):
        """Initialize suspicion tracking CSV."""
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["player_id", "name", "suspicion_score", "notes"])
        except Exception as e:
            self.logger.error(f"Failed to initialize suspects.csv: {e}")

    def write_diary_entry(self, day: int, phase: str, content: str):
        """Write diary entry for current phase."""
        try:
            filename = f"day_{day:02d}_{phase}.md"
            path = self.base_path / "diary" / filename

            path.write_text(f"# Day {day} - {phase.title()}\n\n{content}\n")
        except Exception as e:
            self.logger.error(f"Failed to write diary entry: {e}")

    def get_recent_observations(self, days: int = 1) -> str:
        """Get recent diary entries."""
        try:
            diary_path = self.base_path / "diary"
            if not diary_path.exists():
                return ""

            entries = sorted(diary_path.glob("*.md"))[-days * 4 :]  # Last N days (4 phases/day)

            content = []
            for entry in entries:
                content.append(entry.read_text())

            return "\n\n".join(content)
        except Exception as e:
            self.logger.error(f"Failed to read observations: {e}")
            return ""

    def get_suspicions(self) -> Dict[str, float]:
        """Read current suspicion scores."""
        suspects_path = self.base_path / "suspects.csv"

        if not suspects_path.exists():
            return {}

        suspicions = {}
        try:
            with open(suspects_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    suspicions[row["player_id"]] = float(row["suspicion_score"])
        except Exception as e:
            self.logger.error(f"Failed to read suspicions: {e}")

        return suspicions

    def update_suspicion(
        self, player_id: str, name: str, score: float, notes: str = ""
    ):
        """Update or add suspicion entry."""
        suspects_path = self.base_path / "suspects.csv"

        try:
            # Read existing
            rows = []
            if suspects_path.exists():
                with open(suspects_path, "r") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

            # Update or add
            found = False
            for row in rows:
                if row["player_id"] == player_id:
                    row["suspicion_score"] = str(score)
                    if notes:
                        row["notes"] = notes
                    found = True

            if not found:
                rows.append(
                    {
                        "player_id": player_id,
                        "name": name,
                        "suspicion_score": str(score),
                        "notes": notes,
                    }
                )

            # Write back
            with open(suspects_path, "w", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["player_id", "name", "suspicion_score", "notes"]
                )
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            self.logger.error(f"Failed to update suspicion: {e}")

    def get_profile(self) -> str:
        """Read profile document."""
        try:
            profile_path = self.base_path / "profile.md"
            if profile_path.exists():
                return profile_path.read_text()
        except Exception as e:
            self.logger.error(f"Failed to read profile: {e}")
        return ""
