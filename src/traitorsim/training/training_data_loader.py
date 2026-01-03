"""Training data loader for TraitorSim agents.

Loads and serves training data extracted from The Traitors UK Season 1 analysis.
Provides structured access to player profiles, strategies, dialogue templates,
relationship patterns, and phase norms.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class OCEANTraits:
    """Big Five personality traits (0.0 - 1.0 scale)."""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    def to_dict(self) -> Dict[str, float]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "OCEANTraits":
        return cls(
            openness=data.get("openness", 0.5),
            conscientiousness=data.get("conscientiousness", 0.5),
            extraversion=data.get("extraversion", 0.5),
            agreeableness=data.get("agreeableness", 0.5),
            neuroticism=data.get("neuroticism", 0.5),
        )

    def dominant_traits(self, threshold: float = 0.7) -> List[str]:
        """Get traits above the threshold."""
        traits = []
        if self.openness >= threshold:
            traits.append("openness")
        if self.conscientiousness >= threshold:
            traits.append("conscientiousness")
        if self.extraversion >= threshold:
            traits.append("extraversion")
        if self.agreeableness >= threshold:
            traits.append("agreeableness")
        if self.neuroticism >= threshold:
            traits.append("neuroticism")
        return traits

    def weak_traits(self, threshold: float = 0.3) -> List[str]:
        """Get traits below the threshold."""
        traits = []
        if self.openness <= threshold:
            traits.append("openness")
        if self.conscientiousness <= threshold:
            traits.append("conscientiousness")
        if self.extraversion <= threshold:
            traits.append("extraversion")
        if self.agreeableness <= threshold:
            traits.append("agreeableness")
        if self.neuroticism <= threshold:
            traits.append("neuroticism")
        return traits


@dataclass
class PlayerProfile:
    """Profile of a player from the training data."""
    name: str
    role: str  # "traitor" or "faithful"
    archetype: str
    ocean_traits: OCEANTraits
    key_moments: List[str] = field(default_factory=list)
    occupation: Optional[str] = None
    personality_observations: List[str] = field(default_factory=list)


@dataclass
class Strategy:
    """A gameplay strategy from the training data."""
    name: str
    description: str
    role: str  # "traitor", "faithful", or "universal"
    phase: str  # Which game phase this applies to
    effectiveness: float = 0.5  # 0.0 - 1.0
    counter_strategies: List[str] = field(default_factory=list)
    example_players: List[str] = field(default_factory=list)

    def matches_context(self, role: str, phase: str) -> bool:
        """Check if this strategy applies to the given context."""
        role_match = self.role == "universal" or self.role.lower() == role.lower()
        phase_match = self.phase == "all" or self.phase.lower() == phase.lower()
        return role_match and phase_match


@dataclass
class RelationshipPattern:
    """A relationship pattern between players."""
    pattern_type: str  # "alliance", "rivalry", "romantic", "suspicious", "trust"
    players: List[str]
    strength: float  # 0.0 - 1.0
    evolution: str  # Description of how it developed
    key_moments: List[str] = field(default_factory=list)


class TrainingDataLoader:
    """Loads and serves training data for agent enhancement."""

    DEFAULT_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "training"

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = Path(data_path) if data_path else self.DEFAULT_DATA_PATH

        # Loaded data caches
        self._player_profiles: Dict[str, PlayerProfile] = {}
        self._strategies: List[Strategy] = []
        self._dialogue_templates: Dict[str, Dict] = {}
        self._phase_norms: Dict[str, Dict] = {}
        self._relationship_patterns: Dict[str, List[RelationshipPattern]] = {}
        self._summary: Dict[str, Any] = {}

        # Derived indices
        self._traitor_names: List[str] = []
        self._faithful_names: List[str] = []
        self._strategies_by_role: Dict[str, List[Strategy]] = {}
        self._strategies_by_phase: Dict[str, List[Strategy]] = {}

        self._loaded = False

    def load(self) -> "TrainingDataLoader":
        """Load all training data files."""
        if self._loaded:
            return self

        self._load_player_profiles()
        self._load_strategies()
        self._load_dialogue_templates()
        self._load_phase_norms()
        self._load_relationship_patterns()
        self._load_summary()
        self._build_indices()

        self._loaded = True
        return self

    def _load_player_profiles(self):
        """Load player profiles from JSON."""
        path = self.data_path / "player_profiles.json"
        if not path.exists():
            return

        with open(path) as f:
            data = json.load(f)

        # Handle both list and dict formats
        profiles = data if isinstance(data, list) else data.values()

        for profile in profiles:
            name = profile.get("name", "Unknown")
            # Support both "ocean" and "ocean_traits" keys
            ocean = profile.get("ocean", profile.get("ocean_traits", {}))
            self._player_profiles[name.lower()] = PlayerProfile(
                name=name,
                role=profile.get("role", "unknown"),
                archetype=profile.get("archetype", "unknown"),
                ocean_traits=OCEANTraits.from_dict(ocean),
                key_moments=profile.get("key_moments", []),
                occupation=profile.get("occupation"),
                personality_observations=profile.get("observed_behaviors", profile.get("personality_observations", [])),
            )

    def _load_strategies(self):
        """Load strategy playbook from JSON."""
        path = self.data_path / "strategy_playbook.json"
        if not path.exists():
            return

        with open(path) as f:
            data = json.load(f)

        for role_type in ["traitor_strategies", "faithful_strategies", "universal_strategies"]:
            role = role_type.replace("_strategies", "")
            strategies = data.get(role_type, [])

            for s in strategies:
                strategy = Strategy(
                    name=s.get("strategy_name", s.get("name", "Unknown")),
                    description=s.get("description", ""),
                    role=role,
                    phase=s.get("phase", "all"),
                    effectiveness=s.get("effectiveness", 0.5),
                    counter_strategies=s.get("counter_strategies", []),
                    example_players=s.get("example_players", []),
                )
                self._strategies.append(strategy)

    def _load_dialogue_templates(self):
        """Load dialogue templates from JSON."""
        path = self.data_path / "dialogue_templates.json"
        if not path.exists():
            return

        with open(path) as f:
            self._dialogue_templates = json.load(f)

    def _load_phase_norms(self):
        """Load phase norms from JSON."""
        path = self.data_path / "phase_norms.json"
        if not path.exists():
            return

        with open(path) as f:
            self._phase_norms = json.load(f)

    def _load_relationship_patterns(self):
        """Load relationship patterns from JSON."""
        path = self.data_path / "relationship_patterns.json"
        if not path.exists():
            return

        with open(path) as f:
            data = json.load(f)

        for pattern_type in ["alliance", "rivalry", "romantic", "suspicious", "trust"]:
            patterns = data.get(pattern_type, [])
            self._relationship_patterns[pattern_type] = []

            for p in patterns:
                pattern = RelationshipPattern(
                    pattern_type=pattern_type,
                    players=p.get("players", []),
                    strength=p.get("strength", 0.5),
                    evolution=p.get("evolution", ""),
                    key_moments=p.get("key_moments", []),
                )
                self._relationship_patterns[pattern_type].append(pattern)

    def _load_summary(self):
        """Load training data summary."""
        path = self.data_path / "training_data_summary.json"
        if not path.exists():
            return

        with open(path) as f:
            self._summary = json.load(f)

        self._traitor_names = [n.lower() for n in self._summary.get("traitors", [])]
        self._faithful_names = [n.lower() for n in self._summary.get("faithfuls", [])]

    def _build_indices(self):
        """Build search indices for efficient lookups."""
        # Index strategies by role
        self._strategies_by_role = {"traitor": [], "faithful": [], "universal": []}
        for s in self._strategies:
            if s.role in self._strategies_by_role:
                self._strategies_by_role[s.role].append(s)

        # Index strategies by phase
        self._strategies_by_phase = {}
        for s in self._strategies:
            phase = s.phase.lower()
            if phase not in self._strategies_by_phase:
                self._strategies_by_phase[phase] = []
            self._strategies_by_phase[phase].append(s)

    # ─────────────────────────────────────────────────────────────────────────
    # Player Profile Access
    # ─────────────────────────────────────────────────────────────────────────

    def get_player_profile(self, name: str) -> Optional[PlayerProfile]:
        """Get a player profile by name (case-insensitive)."""
        self.load()
        return self._player_profiles.get(name.lower())

    def get_all_profiles(self) -> Dict[str, PlayerProfile]:
        """Get all player profiles."""
        self.load()
        return self._player_profiles.copy()

    def get_traitor_profiles(self) -> List[PlayerProfile]:
        """Get all confirmed traitor profiles."""
        self.load()
        return [p for p in self._player_profiles.values() if p.role.lower() == "traitor"]

    def get_faithful_profiles(self) -> List[PlayerProfile]:
        """Get all confirmed faithful profiles."""
        self.load()
        return [p for p in self._player_profiles.values() if p.role.lower() == "faithful"]

    def get_profiles_by_archetype(self, archetype: str) -> List[PlayerProfile]:
        """Get profiles matching an archetype (partial match)."""
        self.load()
        archetype_lower = archetype.lower()
        return [p for p in self._player_profiles.values()
                if archetype_lower in p.archetype.lower()]

    def sample_ocean_traits_for_role(self, role: str) -> OCEANTraits:
        """Sample OCEAN traits based on real players of that role.

        Uses the training data distribution to generate realistic personality traits.
        """
        self.load()

        profiles = (self.get_traitor_profiles() if role.lower() == "traitor"
                   else self.get_faithful_profiles())

        if not profiles:
            # Fallback to random sampling
            return OCEANTraits(
                openness=random.uniform(0.3, 0.8),
                conscientiousness=random.uniform(0.3, 0.8),
                extraversion=random.uniform(0.3, 0.8),
                agreeableness=random.uniform(0.3, 0.8),
                neuroticism=random.uniform(0.3, 0.8),
            )

        # Sample a random profile and add some noise
        base = random.choice(profiles)
        noise = lambda: random.uniform(-0.15, 0.15)
        clamp = lambda x: max(0.0, min(1.0, x))

        return OCEANTraits(
            openness=clamp(base.ocean_traits.openness + noise()),
            conscientiousness=clamp(base.ocean_traits.conscientiousness + noise()),
            extraversion=clamp(base.ocean_traits.extraversion + noise()),
            agreeableness=clamp(base.ocean_traits.agreeableness + noise()),
            neuroticism=clamp(base.ocean_traits.neuroticism + noise()),
        )

    def get_average_ocean_for_role(self, role: str) -> OCEANTraits:
        """Get average OCEAN traits for players of a given role."""
        self.load()

        profiles = (self.get_traitor_profiles() if role.lower() == "traitor"
                   else self.get_faithful_profiles())

        if not profiles:
            return OCEANTraits()

        n = len(profiles)
        return OCEANTraits(
            openness=sum(p.ocean_traits.openness for p in profiles) / n,
            conscientiousness=sum(p.ocean_traits.conscientiousness for p in profiles) / n,
            extraversion=sum(p.ocean_traits.extraversion for p in profiles) / n,
            agreeableness=sum(p.ocean_traits.agreeableness for p in profiles) / n,
            neuroticism=sum(p.ocean_traits.neuroticism for p in profiles) / n,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy Access
    # ─────────────────────────────────────────────────────────────────────────

    def get_strategies_for_context(
        self,
        role: str,
        phase: str,
        top_k: int = 3,
        min_effectiveness: float = 0.0
    ) -> List[Strategy]:
        """Get relevant strategies for the given role and phase.

        Args:
            role: "traitor" or "faithful"
            phase: Current game phase (e.g., "roundtable", "social")
            top_k: Maximum number of strategies to return
            min_effectiveness: Minimum effectiveness threshold

        Returns:
            List of applicable strategies, sorted by effectiveness
        """
        self.load()

        applicable = []
        for s in self._strategies:
            if s.matches_context(role, phase) and s.effectiveness >= min_effectiveness:
                applicable.append(s)

        # Sort by effectiveness (descending)
        applicable.sort(key=lambda x: x.effectiveness, reverse=True)

        return applicable[:top_k]

    def get_all_strategies(self) -> List[Strategy]:
        """Get all strategies."""
        self.load()
        return self._strategies.copy()

    def get_counter_strategies(self, strategy_name: str) -> List[str]:
        """Get counter-strategies for a given strategy."""
        self.load()
        for s in self._strategies:
            if s.name.lower() == strategy_name.lower():
                return s.counter_strategies
        return []

    def suggest_strategy(
        self,
        role: str,
        phase: str,
        personality: OCEANTraits,
        game_context: Optional[Dict] = None
    ) -> Tuple[Strategy, str]:
        """Suggest a strategy based on role, phase, and personality.

        Returns:
            Tuple of (strategy, reasoning)
        """
        self.load()

        strategies = self.get_strategies_for_context(role, phase, top_k=5)

        if not strategies:
            return None, "No applicable strategies found"

        # Weight strategies by personality fit
        scored = []
        for s in strategies:
            score = s.effectiveness

            # Adjust based on personality
            if "aggressive" in s.description.lower():
                score += personality.extraversion * 0.2
                score -= personality.agreeableness * 0.1

            if "cautious" in s.description.lower() or "subtle" in s.description.lower():
                score += personality.conscientiousness * 0.2
                score -= personality.extraversion * 0.1

            if "paranoid" in s.description.lower() or "suspicious" in s.description.lower():
                score += personality.neuroticism * 0.2

            if "alliance" in s.description.lower() or "trust" in s.description.lower():
                score += personality.agreeableness * 0.2

            if "analytical" in s.description.lower() or "logical" in s.description.lower():
                score += personality.openness * 0.2

            scored.append((s, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        best = scored[0][0]

        reasoning = f"'{best.name}' matches your {role} role in {phase} phase"
        dominant = personality.dominant_traits()
        if dominant:
            reasoning += f" and your dominant traits ({', '.join(dominant)})"

        return best, reasoning

    # ─────────────────────────────────────────────────────────────────────────
    # Dialogue Template Access
    # ─────────────────────────────────────────────────────────────────────────

    def get_dialogue_context(self, context: str) -> Optional[Dict]:
        """Get dialogue templates for a given context.

        Args:
            context: One of "accusation", "defense", "alliance_building",
                    "emotional_expression", "strategic_planning"
        """
        self.load()
        return self._dialogue_templates.get(context)

    def get_dialogue_phrases(self, context: str) -> List[str]:
        """Get dialogue phrases for a context."""
        self.load()
        ctx = self._dialogue_templates.get(context, {})
        return ctx.get("phrases", [])

    def get_emotional_markers(self, context: str) -> List[str]:
        """Get emotional markers observed in a context."""
        self.load()
        ctx = self._dialogue_templates.get(context, {})
        return ctx.get("emotional_markers", [])

    def sample_dialogue_phrase(self, context: str) -> Optional[str]:
        """Sample a random dialogue phrase for a context."""
        phrases = self.get_dialogue_phrases(context)
        return random.choice(phrases) if phrases else None

    # ─────────────────────────────────────────────────────────────────────────
    # Phase Norms Access
    # ─────────────────────────────────────────────────────────────────────────

    def get_phase_norms(self, phase: str) -> Optional[Dict]:
        """Get behavioral norms for a game phase.

        Args:
            phase: One of "arrival", "breakfast", "mission", "social",
                  "roundtable", "murder"
        """
        self.load()
        return self._phase_norms.get(phase)

    def get_expected_behaviors(self, phase: str, role: str = None) -> List[str]:
        """Get expected behaviors for a phase, optionally filtered by role."""
        self.load()
        norms = self._phase_norms.get(phase, {})

        if role:
            role_key = f"{role.lower()}_specific"
            return norms.get(role_key, [])

        return norms.get("expected_behaviors", [])

    def get_phase_guidance(self, phase: str, role: str) -> str:
        """Get combined behavioral guidance for a phase and role."""
        self.load()

        general = self.get_expected_behaviors(phase)
        role_specific = self.get_expected_behaviors(phase, role)

        guidance_parts = []

        if general:
            guidance_parts.append("General behaviors observed:")
            guidance_parts.extend(f"  - {b[:100]}..." if len(b) > 100 else f"  - {b}"
                                  for b in general[:3])

        if role_specific:
            guidance_parts.append(f"\n{role.title()}-specific behaviors:")
            guidance_parts.extend(f"  - {b[:100]}..." if len(b) > 100 else f"  - {b}"
                                  for b in role_specific[:3])

        return "\n".join(guidance_parts) if guidance_parts else ""

    # ─────────────────────────────────────────────────────────────────────────
    # Relationship Pattern Access
    # ─────────────────────────────────────────────────────────────────────────

    def get_relationship_patterns(self, pattern_type: str) -> List[RelationshipPattern]:
        """Get relationship patterns of a given type.

        Args:
            pattern_type: One of "alliance", "rivalry", "romantic",
                         "suspicious", "trust"
        """
        self.load()
        return self._relationship_patterns.get(pattern_type, [])

    def get_all_relationships(self) -> Dict[str, List[RelationshipPattern]]:
        """Get all relationship patterns."""
        self.load()
        return self._relationship_patterns.copy()

    def find_relationship_involving(self, player_name: str) -> List[RelationshipPattern]:
        """Find all relationships involving a player."""
        self.load()
        player_lower = player_name.lower()

        result = []
        for patterns in self._relationship_patterns.values():
            for p in patterns:
                if any(player_lower in name.lower() for name in p.players):
                    result.append(p)

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Summary and Stats
    # ─────────────────────────────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """Get training data summary."""
        self.load()
        return self._summary.copy()

    def get_confirmed_traitors(self) -> List[str]:
        """Get list of confirmed traitor names."""
        self.load()
        return self._traitor_names.copy()

    def get_confirmed_faithfuls(self) -> List[str]:
        """Get list of confirmed faithful names."""
        self.load()
        return self._faithful_names.copy()

    def stats(self) -> Dict[str, int]:
        """Get statistics about loaded training data."""
        self.load()
        return {
            "player_profiles": len(self._player_profiles),
            "traitors": len(self._traitor_names),
            "faithfuls": len(self._faithful_names),
            "strategies": len(self._strategies),
            "dialogue_contexts": len(self._dialogue_templates),
            "phase_norms": len(self._phase_norms),
            "relationship_types": len(self._relationship_patterns),
        }


# Global singleton instance
_loader: Optional[TrainingDataLoader] = None


def get_training_data() -> TrainingDataLoader:
    """Get the global training data loader instance."""
    global _loader
    if _loader is None:
        _loader = TrainingDataLoader().load()
    return _loader
