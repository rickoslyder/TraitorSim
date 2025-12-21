"""Persona card loader for runtime use.

Loads pre-generated persona cards from the library and samples them for games,
ensuring archetype diversity and proper distribution.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter


class PersonaLoader:
    """Loads and samples persona cards from library."""

    def __init__(self, persona_dir: str = "data/personas/library"):
        """Initialize PersonaLoader.

        Args:
            persona_dir: Directory containing persona JSON files
        """
        self.persona_dir = Path(persona_dir)
        self.personas: List[Dict] = []
        self._load_library()

    def _load_library(self):
        """Load all persona JSON files from library."""
        if not self.persona_dir.exists():
            raise FileNotFoundError(
                f"Persona library not found: {self.persona_dir}\n"
                f"Generate personas first:\n"
                f"  ./scripts/generate_persona_library.sh"
            )

        loaded_files = 0

        for file in self.persona_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)

                    if isinstance(data, list):
                        self.personas.extend(data)
                    else:
                        self.personas.append(data)

                    loaded_files += 1

            except json.JSONDecodeError as e:
                print(f"Warning: Failed to load {file}: {e}")

        if len(self.personas) == 0:
            raise ValueError(
                f"No valid personas found in {self.persona_dir}\n"
                f"Generate personas first:\n"
                f"  ./scripts/generate_persona_library.sh"
            )

        print(f"✓ Loaded {len(self.personas)} personas from {loaded_files} files")

    def sample_personas(
        self,
        count: int,
        ensure_diversity: bool = True,
        max_per_archetype: int = 2
    ) -> List[Dict]:
        """Sample N personas for a game.

        Args:
            count: Number of personas to sample
            ensure_diversity: Ensure archetype distribution
            max_per_archetype: Maximum instances of same archetype

        Returns:
            List of persona cards

        Raises:
            ValueError: If not enough personas in library
        """
        if count > len(self.personas):
            raise ValueError(
                f"Not enough personas in library: requested {count}, "
                f"available {len(self.personas)}\n"
                f"Generate more personas:\n"
                f"  ./scripts/generate_persona_library.sh --count {count * 2}"
            )

        if ensure_diversity:
            return self._sample_with_diversity(count, max_per_archetype)
        else:
            return random.sample(self.personas, count)

    def _sample_with_diversity(
        self,
        count: int,
        max_per_archetype: int
    ) -> List[Dict]:
        """Sample personas ensuring archetype diversity.

        Args:
            count: Number to sample
            max_per_archetype: Max instances per archetype

        Returns:
            List of persona cards with diverse archetypes
        """
        archetype_counts = Counter()
        selected = []
        available = self.personas.copy()
        random.shuffle(available)

        # First pass: select up to max_per_archetype for each archetype
        for persona in available:
            archetype = persona.get("archetype", "unknown")

            if archetype_counts[archetype] < max_per_archetype:
                selected.append(persona)
                archetype_counts[archetype] += 1

            if len(selected) >= count:
                break

        # If still need more (e.g., not enough archetypes), relax constraint
        if len(selected) < count:
            remaining_needed = count - len(selected)
            selected_ids = [p.get("skeleton_id") for p in selected]

            # Sample from personas not yet selected
            remaining_pool = [
                p for p in available
                if p.get("skeleton_id") not in selected_ids
            ]

            if remaining_pool:
                additional = random.sample(
                    remaining_pool,
                    min(remaining_needed, len(remaining_pool))
                )
                selected.extend(additional)

        # Shuffle selected to randomize within archetype groups
        random.shuffle(selected)

        return selected[:count]

    def get_archetype_distribution(self) -> Dict[str, int]:
        """Get archetype distribution in library.

        Returns:
            Dict mapping archetype names to counts
        """
        return dict(Counter([
            p.get("archetype_name", "Unknown")
            for p in self.personas
        ]))

    def get_persona_by_id(self, skeleton_id: str) -> Optional[Dict]:
        """Get specific persona by skeleton_id.

        Args:
            skeleton_id: Skeleton ID to find

        Returns:
            Persona dict or None if not found
        """
        for persona in self.personas:
            if persona.get("skeleton_id") == skeleton_id:
                return persona
        return None


def load_persona_for_player(player_id: str, persona_library_path: str = "data/personas/library") -> Optional[Dict]:
    """Load specific persona for a player (utility function).

    This is a convenience function for container startup scripts.

    Args:
        player_id: Player ID (e.g., "player_00")
        persona_library_path: Path to persona library

    Returns:
        Persona dict or None if not found
    """
    # Look for pre-assigned persona mapping
    mapping_file = Path(persona_library_path) / "player_mapping.json"

    if mapping_file.exists():
        with open(mapping_file) as f:
            mapping = json.load(f)
            skeleton_id = mapping.get(player_id)

            if skeleton_id:
                loader = PersonaLoader(persona_library_path)
                return loader.get_persona_by_id(skeleton_id)

    return None
