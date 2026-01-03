#!/usr/bin/env python3
"""
Multi-Pass Training Data Extraction Pipeline

Extracts structured training data from The Traitors UK Season 1 analysis
for use in TraitorSim AI agent training.

Passes:
1. Player Profiles → OCEAN traits, archetypes, demographics
2. Strategic Patterns → Traitor/Faithful playbooks, what worked/failed
3. Dialogue Corpus → Speech patterns by context (accusation, defense, etc.)
4. Social Dynamics → Trust evolution, alliance formation, betrayal patterns
5. Game Flow → Phase-specific behavioral norms and expectations
6. Outcome Analysis → Win/loss correlation with strategies

Usage:
    python scripts/extract_training_data.py --all
    python scripts/extract_training_data.py --pass 1
    python scripts/extract_training_data.py --pass 1 2 3
"""

import json
import re
import os
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from collections import defaultdict
import hashlib


# =============================================================================
# DATA MODELS
# =============================================================================

class Role(Enum):
    TRAITOR = "traitor"
    FAITHFUL = "faithful"
    UNKNOWN = "unknown"


class GamePhase(Enum):
    ARRIVAL = "arrival"
    BREAKFAST = "breakfast"
    MISSION = "mission"
    SOCIAL = "social"
    ROUNDTABLE = "roundtable"
    MURDER = "murder"
    RECRUITMENT = "recruitment"
    FINALE = "finale"


class StrategyType(Enum):
    # Traitor strategies
    TRAITOR_ANGEL = "traitor_angel"  # Perfect faithful performance
    BUS_THROWING = "bus_throwing"  # Sacrifice fellow traitor
    SILENT_MURDER = "silent_murder"  # Kill trusted players
    CHAOS_AGENT = "chaos_agent"  # Sow discord
    PUPPET_MASTER = "puppet_master"  # Control through manipulation

    # Faithful strategies
    SHIELD_BLUFF = "shield_bluff"  # False claims to detect leaks
    VOTING_ANALYSIS = "voting_analysis"  # Track voting patterns
    ALLIANCE_BUILDER = "alliance_builder"  # Form trusted groups
    DIRECT_ACCUSER = "direct_accuser"  # Confront suspects head-on
    QUIET_OBSERVER = "quiet_observer"  # Watch and wait

    # Universal strategies
    LOW_PROFILE = "low_profile"  # Avoid attention
    HIGH_PROFILE = "high_profile"  # Establish dominance
    TRANSPARENCY = "transparency"  # Appear open
    SELECTIVE_SHARING = "selective_sharing"  # Strategic information control


@dataclass
class OCEANTraits:
    """Big Five personality traits (0.0-1.0 scale)."""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    # Evidence for each trait
    openness_evidence: list = field(default_factory=list)
    conscientiousness_evidence: list = field(default_factory=list)
    extraversion_evidence: list = field(default_factory=list)
    agreeableness_evidence: list = field(default_factory=list)
    neuroticism_evidence: list = field(default_factory=list)


@dataclass
class PlayerProfile:
    """Complete player profile extracted from show analysis."""
    name: str
    age: Optional[int] = None
    occupation: Optional[str] = None
    role: Role = Role.UNKNOWN

    # Personality
    ocean_traits: OCEANTraits = field(default_factory=OCEANTraits)
    archetype: Optional[str] = None
    archetype_confidence: float = 0.0

    # Behavioral observations
    self_descriptions: list = field(default_factory=list)
    observed_behaviors: list = field(default_factory=list)
    strategies_used: list = field(default_factory=list)

    # Outcomes
    survived_until_episode: Optional[int] = None
    elimination_type: Optional[str] = None  # "murdered", "banished", "winner"
    was_correctly_identified: Optional[bool] = None  # For traitors

    # Relationships
    allies: list = field(default_factory=list)
    enemies: list = field(default_factory=list)
    trust_given: dict = field(default_factory=dict)  # name -> score
    trust_received: dict = field(default_factory=dict)  # name -> score


@dataclass
class DialoguePattern:
    """Speech pattern for a specific context."""
    context: str  # "accusation", "defense", "alliance_building", etc.
    phase: GamePhase = GamePhase.ROUNDTABLE
    speaker_role: Role = Role.UNKNOWN

    # The actual patterns
    phrases: list = field(default_factory=list)
    emotional_markers: list = field(default_factory=list)
    rhetorical_devices: list = field(default_factory=list)

    # Effectiveness
    success_rate: Optional[float] = None  # Did this work?
    examples: list = field(default_factory=list)


@dataclass
class StrategicPattern:
    """A strategic pattern observed in the show."""
    name: str
    strategy_type: StrategyType = StrategyType.LOW_PROFILE
    applicable_roles: list = field(default_factory=list)  # [Role.TRAITOR] or [Role.FAITHFUL] or both

    # Description
    description: str = ""
    when_to_use: str = ""
    risks: str = ""

    # Observed usage
    used_by: list = field(default_factory=list)  # Player names
    success_cases: list = field(default_factory=list)
    failure_cases: list = field(default_factory=list)

    # Effectiveness metrics
    times_used: int = 0
    times_successful: int = 0


@dataclass
class AllianceEvent:
    """An alliance formation, maintenance, or dissolution event."""
    episode: int
    phase: GamePhase
    event_type: str  # "formation", "strengthening", "strain", "dissolution", "betrayal"

    members: list = field(default_factory=list)
    initiator: Optional[str] = None

    description: str = ""
    outcome: str = ""


@dataclass
class TrustUpdate:
    """A trust matrix update event."""
    episode: int
    phase: GamePhase

    from_player: str = ""
    to_player: str = ""

    previous_trust: Optional[float] = None
    new_trust: Optional[float] = None
    delta: float = 0.0

    trigger: str = ""  # What caused this update
    evidence: str = ""


@dataclass
class EliminationEvent:
    """A murder or banishment event."""
    episode: int
    victim: str = ""
    victim_role: Role = Role.UNKNOWN

    elimination_type: str = ""  # "murder" or "banishment"

    # For murders
    murdered_by: list = field(default_factory=list)  # Traitor names
    murder_rationale: str = ""

    # For banishments
    votes_received: int = 0
    key_accusers: list = field(default_factory=list)
    defense_attempted: str = ""
    was_correct: Optional[bool] = None  # Did they banish a traitor?


@dataclass
class PhaseNorms:
    """Behavioral norms for a specific game phase."""
    phase: GamePhase

    expected_behaviors: list = field(default_factory=list)
    common_topics: list = field(default_factory=list)
    typical_alliances_activity: str = ""
    suspicion_dynamics: str = ""

    traitor_specific: list = field(default_factory=list)
    faithful_specific: list = field(default_factory=list)


# =============================================================================
# EXTRACTION UTILITIES
# =============================================================================

def load_json_data(path: Path) -> dict:
    """Load JSON training data."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_markdown_data(path: Path) -> str:
    """Load markdown analysis."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_player_mentions(text: str) -> list[dict]:
    """Extract player name mentions with context."""
    # Pattern for player introductions: **Name** or 1. **Name**
    pattern = r'\*\*([A-Z][a-z]+)\*\*'
    matches = []

    for match in re.finditer(pattern, text):
        name = match.group(1)
        # Get surrounding context (200 chars before and after)
        start = max(0, match.start() - 200)
        end = min(len(text), match.end() + 200)
        context = text[start:end]

        matches.append({
            'name': name,
            'context': context,
            'position': match.start(),
        })

    return matches


def extract_age_occupation(text: str, player_name: str) -> tuple[Optional[int], Optional[str]]:
    """Extract age and occupation for a player."""
    # Pattern: Age/Occupation: 54, Estate Agent
    pattern = rf'{player_name}.*?(?:Age(?:/Occupation)?|Age & Occupation):\s*(\d+),?\s*([^*\n]+)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        age = int(match.group(1))
        occupation = match.group(2).strip().rstrip('.')
        return age, occupation

    return None, None


def extract_role(text: str, player_name: str) -> Role:
    """Extract player role from analysis."""
    # Look for explicit role mentions
    traitor_pattern = rf'{player_name}.*?(?:Role|role):\s*Traitor'
    faithful_pattern = rf'{player_name}.*?(?:Role|role):\s*Faithful'

    if re.search(traitor_pattern, text, re.IGNORECASE):
        return Role.TRAITOR
    elif re.search(faithful_pattern, text, re.IGNORECASE):
        return Role.FAITHFUL

    return Role.UNKNOWN


def infer_ocean_from_description(description: str) -> OCEANTraits:
    """Infer OCEAN traits from personality description."""
    traits = OCEANTraits()
    desc_lower = description.lower()

    # Openness indicators
    openness_high = ['strategic', 'creative', 'curious', 'imaginative', 'adventurous', 'open-minded']
    openness_low = ['rigid', 'conventional', 'practical', 'traditional']

    for word in openness_high:
        if word in desc_lower:
            traits.openness = min(1.0, traits.openness + 0.15)
            traits.openness_evidence.append(word)
    for word in openness_low:
        if word in desc_lower:
            traits.openness = max(0.0, traits.openness - 0.15)
            traits.openness_evidence.append(f"NOT {word}")

    # Conscientiousness indicators
    consc_high = ['dependable', 'reliable', 'organized', 'focused', 'analytical', 'methodical', 'determined']
    consc_low = ['chaotic', 'impulsive', 'scattered', 'unreliable']

    for word in consc_high:
        if word in desc_lower:
            traits.conscientiousness = min(1.0, traits.conscientiousness + 0.15)
            traits.conscientiousness_evidence.append(word)
    for word in consc_low:
        if word in desc_lower:
            traits.conscientiousness = max(0.0, traits.conscientiousness - 0.15)
            traits.conscientiousness_evidence.append(f"NOT {word}")

    # Extraversion indicators
    extra_high = ['enthusiastic', 'outgoing', 'confident', 'charismatic', 'vocal', 'loud', 'energetic', 'friendly']
    extra_low = ['quiet', 'reserved', 'shy', 'introverted', 'withdrawn']

    for word in extra_high:
        if word in desc_lower:
            traits.extraversion = min(1.0, traits.extraversion + 0.15)
            traits.extraversion_evidence.append(word)
    for word in extra_low:
        if word in desc_lower:
            traits.extraversion = max(0.0, traits.extraversion - 0.15)
            traits.extraversion_evidence.append(f"NOT {word}")

    # Agreeableness indicators
    agree_high = ['trustworthy', 'supportive', 'warm', 'cooperative', 'kind', 'helpful', 'maternal', 'paternal']
    agree_low = ['confrontational', 'competitive', 'ruthless', 'manipulative', 'cunning', 'deceptive']

    for word in agree_high:
        if word in desc_lower:
            traits.agreeableness = min(1.0, traits.agreeableness + 0.15)
            traits.agreeableness_evidence.append(word)
    for word in agree_low:
        if word in desc_lower:
            traits.agreeableness = max(0.0, traits.agreeableness - 0.15)
            traits.agreeableness_evidence.append(f"NOT {word}")

    # Neuroticism indicators
    neuro_high = ['anxious', 'nervous', 'worried', 'paranoid', 'defensive', 'emotional', 'vulnerable', 'stressed']
    neuro_low = ['calm', 'composed', 'stable', 'confident', 'relaxed', 'stoic']

    for word in neuro_high:
        if word in desc_lower:
            traits.neuroticism = min(1.0, traits.neuroticism + 0.15)
            traits.neuroticism_evidence.append(word)
    for word in neuro_low:
        if word in desc_lower:
            traits.neuroticism = max(0.0, traits.neuroticism - 0.15)
            traits.neuroticism_evidence.append(f"NOT {word}")

    return traits


def map_to_archetype(traits: OCEANTraits, role: Role, behaviors: list[str]) -> tuple[str, float]:
    """Map OCEAN traits and behaviors to TraitorSim archetype."""
    # TraitorSim archetypes with their trait signatures
    archetypes = {
        "The Prodigy": {
            "traits": {"openness": 0.8, "conscientiousness": 0.7, "extraversion": 0.6, "agreeableness": 0.4, "neuroticism": 0.3},
            "keywords": ["intelligent", "ambitious", "confident", "young", "phd", "degree", "achievement"],
        },
        "The Sage": {
            "traits": {"openness": 0.6, "conscientiousness": 0.8, "extraversion": 0.5, "agreeableness": 0.7, "neuroticism": 0.3},
            "keywords": ["wise", "advice", "dependable", "calm", "mature", "experienced", "trustworthy"],
        },
        "The Charming Sociopath": {
            "traits": {"openness": 0.7, "conscientiousness": 0.6, "extraversion": 0.8, "agreeableness": 0.3, "neuroticism": 0.2},
            "keywords": ["charismatic", "manipulative", "persuasive", "puppet master", "cunning", "charming"],
        },
        "The Paranoid": {
            "traits": {"openness": 0.4, "conscientiousness": 0.6, "extraversion": 0.5, "agreeableness": 0.4, "neuroticism": 0.8},
            "keywords": ["suspicious", "paranoid", "anxious", "worried", "nervous", "distrust"],
        },
        "The Underdog": {
            "traits": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.4, "agreeableness": 0.7, "neuroticism": 0.6},
            "keywords": ["underestimated", "humble", "low profile", "unassuming", "quiet"],
        },
        "The Alpha": {
            "traits": {"openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.9, "agreeableness": 0.4, "neuroticism": 0.3},
            "keywords": ["leader", "dominant", "confident", "assertive", "competitive", "alpha"],
        },
        "The Social Butterfly": {
            "traits": {"openness": 0.7, "conscientiousness": 0.4, "extraversion": 0.9, "agreeableness": 0.8, "neuroticism": 0.4},
            "keywords": ["friendly", "outgoing", "social", "talkative", "popular", "likeable"],
        },
        "The Analyst": {
            "traits": {"openness": 0.7, "conscientiousness": 0.8, "extraversion": 0.3, "agreeableness": 0.5, "neuroticism": 0.4},
            "keywords": ["analytical", "observer", "strategic", "calculating", "logical", "methodical"],
        },
        "The Wildcard": {
            "traits": {"openness": 0.9, "conscientiousness": 0.3, "extraversion": 0.7, "agreeableness": 0.4, "neuroticism": 0.6},
            "keywords": ["unpredictable", "chaotic", "impulsive", "dramatic", "emotional", "volatile"],
        },
        "The Matriarch": {
            "traits": {"openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.6, "agreeableness": 0.7, "neuroticism": 0.4},
            "keywords": ["maternal", "protective", "nurturing", "mother", "grandmother", "caring"],
        },
        "The Entertainer": {
            "traits": {"openness": 0.8, "conscientiousness": 0.4, "extraversion": 0.9, "agreeableness": 0.6, "neuroticism": 0.5},
            "keywords": ["magician", "actor", "performer", "entertainer", "showman", "comedian"],
        },
        "The Truthseeker": {
            "traits": {"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.6, "agreeableness": 0.5, "neuroticism": 0.5},
            "keywords": ["detective", "police", "investigator", "spot a liar", "truth", "honest"],
        },
    }

    best_match = None
    best_score = 0.0

    behavior_text = " ".join(behaviors).lower()

    for archetype_name, archetype_data in archetypes.items():
        # Calculate trait similarity (Euclidean distance inverted)
        trait_diff = 0.0
        for trait_name, target_value in archetype_data["traits"].items():
            actual_value = getattr(traits, trait_name)
            trait_diff += (actual_value - target_value) ** 2

        trait_similarity = 1.0 / (1.0 + (trait_diff ** 0.5))

        # Calculate keyword match score
        keyword_matches = sum(1 for kw in archetype_data["keywords"] if kw in behavior_text)
        keyword_score = keyword_matches / len(archetype_data["keywords"])

        # Combined score (70% traits, 30% keywords)
        combined_score = 0.7 * trait_similarity + 0.3 * keyword_score

        if combined_score > best_score:
            best_score = combined_score
            best_match = archetype_name

    return best_match, best_score


# =============================================================================
# PASS 1: PLAYER PROFILE EXTRACTION
# =============================================================================

def pass1_extract_players(data_dir: Path) -> dict[str, PlayerProfile]:
    """
    Pass 1: Extract comprehensive player profiles.

    Extracts:
    - Demographics (name, age, occupation)
    - Role (traitor/faithful)
    - OCEAN personality traits
    - Archetype mapping
    - Self-descriptions and observed behaviors
    """
    print("\n" + "=" * 60)
    print("PASS 1: PLAYER PROFILE EXTRACTION")
    print("=" * 60)

    players: dict[str, PlayerProfile] = {}

    # Load the synthesis data
    synthesis_path = data_dir / "SIMULATOR_SYNTHESIS.md"
    synthesis_text = load_markdown_data(synthesis_path)

    # Also load JSON for structured data
    json_path = data_dir / "simulator_training_data.json"
    json_data = load_json_data(json_path)

    # Extract all player mentions
    mentions = extract_player_mentions(synthesis_text)
    unique_names = set(m['name'] for m in mentions)

    print(f"Found {len(unique_names)} unique player names")

    for name in sorted(unique_names):
        # Skip common false positives
        if name in ['Episode', 'Season', 'Traitor', 'Faithful', 'Round', 'Table', 'Mission', 'Claudia']:
            continue

        profile = PlayerProfile(name=name)

        # Extract age and occupation
        age, occupation = extract_age_occupation(synthesis_text, name)
        profile.age = age
        profile.occupation = occupation

        # Extract role
        profile.role = extract_role(synthesis_text, name)

        # Extract all personality observations for this player
        pattern = rf'\*\*{name}\*\*.*?(?:Personality Observations?|Personality):\s*([^*]+?)(?=\n\n|\n\d+\.|\Z)'
        observations = re.findall(pattern, synthesis_text, re.IGNORECASE | re.DOTALL)

        for obs in observations:
            clean_obs = obs.strip()
            if clean_obs:
                profile.observed_behaviors.append(clean_obs)

        # Extract self-descriptions (quotes)
        quote_pattern = rf'{name}[^"]*"([^"]+)"'
        quotes = re.findall(quote_pattern, synthesis_text)
        profile.self_descriptions = list(set(quotes))[:10]  # Limit to 10

        # Infer OCEAN traits from observations
        all_observations = " ".join(profile.observed_behaviors)
        profile.ocean_traits = infer_ocean_from_description(all_observations)

        # Map to archetype
        archetype, confidence = map_to_archetype(
            profile.ocean_traits,
            profile.role,
            profile.observed_behaviors
        )
        profile.archetype = archetype
        profile.archetype_confidence = confidence

        players[name] = profile

        if profile.role != Role.UNKNOWN:
            print(f"  {name}: {profile.role.value}, age {age}, {occupation}")
            print(f"    → Archetype: {archetype} ({confidence:.0%} confidence)")

    print(f"\nExtracted {len(players)} player profiles")
    print(f"  - Traitors: {sum(1 for p in players.values() if p.role == Role.TRAITOR)}")
    print(f"  - Faithfuls: {sum(1 for p in players.values() if p.role == Role.FAITHFUL)}")
    print(f"  - Unknown: {sum(1 for p in players.values() if p.role == Role.UNKNOWN)}")

    return players


# =============================================================================
# PASS 2: STRATEGIC PATTERN EXTRACTION
# =============================================================================

def pass2_extract_strategies(data_dir: Path, players: dict[str, PlayerProfile]) -> list[StrategicPattern]:
    """
    Pass 2: Extract strategic patterns.

    Extracts:
    - Traitor strategies (hiding, murdering, deflecting)
    - Faithful strategies (detecting, accusing, allying)
    - Success/failure cases for each strategy
    """
    print("\n" + "=" * 60)
    print("PASS 2: STRATEGIC PATTERN EXTRACTION")
    print("=" * 60)

    patterns: list[StrategicPattern] = []

    synthesis_path = data_dir / "SIMULATOR_SYNTHESIS.md"
    synthesis_text = load_markdown_data(synthesis_path)

    # Strategy sections to look for
    strategy_sections = [
        ("How Traitors Hide Their Identity", [Role.TRAITOR]),
        ("How Faithfuls Detect Traitors", [Role.FAITHFUL]),
        ("Deception and Defense Tactics", [Role.TRAITOR, Role.FAITHFUL]),
        ("Tactics potentially used by Traitors", [Role.TRAITOR]),
        ("General Tactics", [Role.TRAITOR, Role.FAITHFUL]),
    ]

    for section_name, applicable_roles in strategy_sections:
        # Find the section
        pattern = rf'{section_name}.*?(?=\n\*\*[A-Z]|\n##|\Z)'
        matches = re.findall(pattern, synthesis_text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            # Extract bullet points
            bullets = re.findall(r'\*\s+\*\*([^*]+)\*\*:?\s*([^*]+?)(?=\n\*|\Z)', match)

            for tactic_name, description in bullets:
                strat = StrategicPattern(
                    name=tactic_name.strip(),
                    description=description.strip(),
                    applicable_roles=applicable_roles,
                )

                # Try to match to a strategy type
                name_lower = tactic_name.lower()
                if 'puppet' in name_lower or 'manipulat' in name_lower:
                    strat.strategy_type = StrategyType.PUPPET_MASTER
                elif 'low profile' in name_lower or 'under the radar' in name_lower:
                    strat.strategy_type = StrategyType.LOW_PROFILE
                elif 'transparent' in name_lower or 'open book' in name_lower:
                    strat.strategy_type = StrategyType.TRANSPARENCY
                elif 'alliance' in name_lower or 'trust' in name_lower:
                    strat.strategy_type = StrategyType.ALLIANCE_BUILDER
                elif 'accus' in name_lower or 'question' in name_lower:
                    strat.strategy_type = StrategyType.DIRECT_ACCUSER
                elif 'observ' in name_lower or 'watch' in name_lower:
                    strat.strategy_type = StrategyType.QUIET_OBSERVER

                # Find players who used this strategy
                for player_name, player in players.items():
                    for behavior in player.observed_behaviors:
                        if any(word in behavior.lower() for word in tactic_name.lower().split()):
                            strat.used_by.append(player_name)
                            strat.times_used += 1

                patterns.append(strat)

    # Deduplicate by name
    seen_names = set()
    unique_patterns = []
    for p in patterns:
        if p.name not in seen_names:
            seen_names.add(p.name)
            unique_patterns.append(p)

    print(f"Extracted {len(unique_patterns)} strategic patterns")

    for pattern in unique_patterns[:10]:  # Show first 10
        roles_str = "/".join(r.value for r in pattern.applicable_roles)
        print(f"  [{roles_str}] {pattern.name}")
        if pattern.used_by:
            print(f"    Used by: {', '.join(pattern.used_by[:3])}")

    return unique_patterns


# =============================================================================
# PASS 3: DIALOGUE PATTERN EXTRACTION
# =============================================================================

def pass3_extract_dialogue(data_dir: Path, players: dict[str, PlayerProfile]) -> list[DialoguePattern]:
    """
    Pass 3: Extract dialogue patterns.

    Extracts:
    - Common phrases by context (accusation, defense, alliance)
    - Emotional markers in speech
    - Role-specific language patterns
    """
    print("\n" + "=" * 60)
    print("PASS 3: DIALOGUE PATTERN EXTRACTION")
    print("=" * 60)

    patterns: list[DialoguePattern] = []

    synthesis_path = data_dir / "SIMULATOR_SYNTHESIS.md"
    synthesis_text = load_markdown_data(synthesis_path)

    # Extract all quoted speech
    quotes = re.findall(r'"([^"]+)"', synthesis_text)

    # Categorize quotes by context
    accusation_keywords = ['traitor', 'liar', 'suspect', 'guilty', 'hiding', 'lying']
    defense_keywords = ['innocent', 'swear', 'promise', 'trust me', 'not a traitor', 'faithful']
    alliance_keywords = ['together', 'alliance', 'trust', 'team', 'friends', 'stick together']
    emotion_keywords = ['scared', 'worried', 'excited', 'nervous', 'happy', 'sad', 'angry']

    categories = {
        'accusation': DialoguePattern(context='accusation', phase=GamePhase.ROUNDTABLE),
        'defense': DialoguePattern(context='defense', phase=GamePhase.ROUNDTABLE),
        'alliance_building': DialoguePattern(context='alliance_building', phase=GamePhase.SOCIAL),
        'emotional_expression': DialoguePattern(context='emotional_expression', phase=GamePhase.ROUNDTABLE),
        'strategic_planning': DialoguePattern(context='strategic_planning', phase=GamePhase.SOCIAL),
    }

    for quote in quotes:
        quote_lower = quote.lower()

        # Categorize
        if any(kw in quote_lower for kw in accusation_keywords):
            categories['accusation'].phrases.append(quote)
        elif any(kw in quote_lower for kw in defense_keywords):
            categories['defense'].phrases.append(quote)
        elif any(kw in quote_lower for kw in alliance_keywords):
            categories['alliance_building'].phrases.append(quote)
        elif any(kw in quote_lower for kw in emotion_keywords):
            categories['emotional_expression'].phrases.append(quote)
        else:
            categories['strategic_planning'].phrases.append(quote)

    # Extract emotional markers
    emotional_markers = [
        'crying', 'tears', 'shaking', 'nervous', 'confident', 'scared',
        'angry', 'frustrated', 'relieved', 'excited', 'disappointed'
    ]

    for marker in emotional_markers:
        count = synthesis_text.lower().count(marker)
        if count > 0:
            for cat in categories.values():
                cat.emotional_markers.append(f"{marker} ({count}x)")

    patterns = list(categories.values())

    print(f"Extracted {len(patterns)} dialogue pattern categories")
    for pattern in patterns:
        print(f"  {pattern.context}: {len(pattern.phrases)} phrases")
        if pattern.phrases:
            print(f"    Example: \"{pattern.phrases[0][:60]}...\"")

    return patterns


# =============================================================================
# PASS 4: SOCIAL DYNAMICS EXTRACTION
# =============================================================================

def pass4_extract_social_dynamics(data_dir: Path, players: dict[str, PlayerProfile]) -> tuple[list[AllianceEvent], list[TrustUpdate]]:
    """
    Pass 4: Extract social dynamics.

    Extracts:
    - Alliance formation and dissolution events
    - Trust level changes over time
    - Betrayal patterns
    """
    print("\n" + "=" * 60)
    print("PASS 4: SOCIAL DYNAMICS EXTRACTION")
    print("=" * 60)

    alliances: list[AllianceEvent] = []
    trust_updates: list[TrustUpdate] = []

    synthesis_path = data_dir / "SIMULATOR_SYNTHESIS.md"
    synthesis_text = load_markdown_data(synthesis_path)

    # Find alliance mentions
    alliance_pattern = r'(?:alliance|ally|allies|allied|together|team(?:ed)? up|group)'
    alliance_matches = re.finditer(alliance_pattern, synthesis_text, re.IGNORECASE)

    player_names = list(players.keys())

    for match in alliance_matches:
        # Get context around the match
        start = max(0, match.start() - 300)
        end = min(len(synthesis_text), match.end() + 300)
        context = synthesis_text[start:end]

        # Find episode number
        episode_match = re.search(r'Episode\s+(\d+)', context)
        episode = int(episode_match.group(1)) if episode_match else 0

        # Find player names in context
        involved_players = [name for name in player_names if name in context]

        if len(involved_players) >= 2:
            event = AllianceEvent(
                episode=episode,
                phase=GamePhase.SOCIAL,
                event_type="formation",
                members=involved_players[:4],  # Limit to 4
                description=context.strip()[:200],
            )
            alliances.append(event)

    # Find trust/suspicion mentions
    trust_pattern = r'(?:trust(?:ed|ing)?|suspicio(?:us|n)|distrust|believe|doubt)'
    trust_matches = re.finditer(trust_pattern, synthesis_text, re.IGNORECASE)

    for match in trust_matches:
        start = max(0, match.start() - 200)
        end = min(len(synthesis_text), match.end() + 200)
        context = synthesis_text[start:end]

        # Find episode number
        episode_match = re.search(r'Episode\s+(\d+)', context)
        episode = int(episode_match.group(1)) if episode_match else 0

        # Find player names in context
        involved_players = [name for name in player_names if name in context]

        if len(involved_players) >= 2:
            # Determine if trust increased or decreased
            is_positive = 'trust' in match.group().lower() and 'distrust' not in context.lower()

            update = TrustUpdate(
                episode=episode,
                phase=GamePhase.ROUNDTABLE,
                from_player=involved_players[0],
                to_player=involved_players[1] if len(involved_players) > 1 else "",
                delta=0.2 if is_positive else -0.2,
                trigger=match.group(),
                evidence=context.strip()[:150],
            )
            trust_updates.append(update)

    # Deduplicate
    unique_alliances = []
    seen = set()
    for a in alliances:
        key = (a.episode, tuple(sorted(a.members)))
        if key not in seen:
            seen.add(key)
            unique_alliances.append(a)

    print(f"Extracted {len(unique_alliances)} alliance events")
    print(f"Extracted {len(trust_updates)} trust updates")

    # Show some examples
    if unique_alliances:
        print("\nExample alliances:")
        for a in unique_alliances[:3]:
            print(f"  Episode {a.episode}: {', '.join(a.members)}")

    return unique_alliances, trust_updates


# =============================================================================
# PASS 5: GAME FLOW EXTRACTION
# =============================================================================

def pass5_extract_game_flow(data_dir: Path) -> list[PhaseNorms]:
    """
    Pass 5: Extract game flow patterns.

    Extracts:
    - Phase-specific behavioral norms
    - Typical activities per phase
    - Role-specific expectations
    """
    print("\n" + "=" * 60)
    print("PASS 5: GAME FLOW PATTERN EXTRACTION")
    print("=" * 60)

    norms: list[PhaseNorms] = []

    synthesis_path = data_dir / "SIMULATOR_SYNTHESIS.md"
    synthesis_text = load_markdown_data(synthesis_path)

    # Define phases and their keywords
    phases = [
        (GamePhase.ARRIVAL, ['arrival', 'train', 'castle', 'first meeting', 'introduction']),
        (GamePhase.BREAKFAST, ['breakfast', 'morning', 'murder reveal', 'victim']),
        (GamePhase.MISSION, ['mission', 'challenge', 'task', 'prize pot', 'money']),
        (GamePhase.SOCIAL, ['social', 'conversation', 'alliance', 'private', 'chat']),
        (GamePhase.ROUNDTABLE, ['round table', 'roundtable', 'vote', 'banish', 'accus']),
        (GamePhase.MURDER, ['murder', 'night', 'traitors meet', 'kill', 'eliminate']),
    ]

    for phase, keywords in phases:
        phase_norm = PhaseNorms(phase=phase)

        # Find all mentions of this phase
        for keyword in keywords:
            pattern = rf'{keyword}[^.]*\.'
            matches = re.findall(pattern, synthesis_text, re.IGNORECASE)

            for match in matches[:5]:  # Limit per keyword
                if len(match) > 20:  # Skip very short matches
                    phase_norm.expected_behaviors.append(match.strip())

        # Look for role-specific behaviors
        traitor_pattern = rf'traitor.*?{"|".join(keywords)}[^.]*\.'
        faithful_pattern = rf'faithful.*?{"|".join(keywords)}[^.]*\.'

        traitor_matches = re.findall(traitor_pattern, synthesis_text, re.IGNORECASE)
        faithful_matches = re.findall(faithful_pattern, synthesis_text, re.IGNORECASE)

        phase_norm.traitor_specific = [m.strip() for m in traitor_matches[:3]]
        phase_norm.faithful_specific = [m.strip() for m in faithful_matches[:3]]

        norms.append(phase_norm)

    print(f"Extracted norms for {len(norms)} game phases")
    for norm in norms:
        print(f"  {norm.phase.value}: {len(norm.expected_behaviors)} behaviors")

    return norms


# =============================================================================
# PASS 6: OUTCOME ANALYSIS
# =============================================================================

def pass6_analyze_outcomes(data_dir: Path, players: dict[str, PlayerProfile]) -> dict:
    """
    Pass 6: Analyze outcomes.

    Extracts:
    - Who won (traitors or faithfuls)
    - Which strategies correlated with survival
    - Elimination patterns (who got murdered vs banished)
    """
    print("\n" + "=" * 60)
    print("PASS 6: OUTCOME ANALYSIS")
    print("=" * 60)

    outcomes = {
        'winner': None,  # 'traitors' or 'faithfuls'
        'final_players': [],
        'eliminations': [],
        'strategy_success': defaultdict(lambda: {'survived': 0, 'eliminated': 0}),
        'archetype_success': defaultdict(lambda: {'survived': 0, 'eliminated': 0}),
    }

    # Load the season summary for final outcome
    summary_path = data_dir / "SEASON_SUMMARY.md"
    summary_text = load_markdown_data(summary_path)

    # Find elimination events
    murder_pattern = r'(?:murder(?:ed)?|killed|eliminated at night)[^.]*?(\w+)'
    banish_pattern = r'(?:banish(?:ed)?|voted out|eliminated)[^.]*?(\w+)'

    murder_matches = re.findall(murder_pattern, summary_text, re.IGNORECASE)
    banish_matches = re.findall(banish_pattern, summary_text, re.IGNORECASE)

    player_names = set(players.keys())

    for name in murder_matches:
        if name in player_names:
            outcomes['eliminations'].append({
                'name': name,
                'type': 'murder',
                'role': players[name].role.value,
            })

    for name in banish_matches:
        if name in player_names:
            outcomes['eliminations'].append({
                'name': name,
                'type': 'banishment',
                'role': players[name].role.value,
            })

    # Analyze which strategies led to survival
    # (This would need more detailed data to be accurate)

    # Check for finale/winner mentions
    if 'faithful' in summary_text.lower() and 'win' in summary_text.lower():
        if 'traitor' in summary_text.lower() and 'all' in summary_text.lower():
            outcomes['winner'] = 'faithfuls'
    elif 'traitor' in summary_text.lower() and 'win' in summary_text.lower():
        outcomes['winner'] = 'traitors'

    print(f"Winner: {outcomes['winner'] or 'Unknown'}")
    print(f"Eliminations tracked: {len(outcomes['eliminations'])}")

    # Count by role
    murders_by_role = defaultdict(int)
    banishments_by_role = defaultdict(int)

    for elim in outcomes['eliminations']:
        if elim['type'] == 'murder':
            murders_by_role[elim['role']] += 1
        else:
            banishments_by_role[elim['role']] += 1

    print(f"  Murders: {dict(murders_by_role)}")
    print(f"  Banishments: {dict(banishments_by_role)}")

    return outcomes


# =============================================================================
# MAIN EXTRACTION PIPELINE
# =============================================================================

def run_extraction_pipeline(data_dir: Path, passes: list[int] = None) -> dict:
    """Run the full extraction pipeline."""

    if passes is None:
        passes = [1, 2, 3, 4, 5, 6]

    results = {
        'players': {},
        'strategies': [],
        'dialogue': [],
        'alliances': [],
        'trust_updates': [],
        'phase_norms': [],
        'outcomes': {},
    }

    # Pass 1: Player profiles (required for other passes)
    if 1 in passes or any(p > 1 for p in passes):
        results['players'] = pass1_extract_players(data_dir)

    # Pass 2: Strategic patterns
    if 2 in passes:
        results['strategies'] = pass2_extract_strategies(data_dir, results['players'])

    # Pass 3: Dialogue patterns
    if 3 in passes:
        results['dialogue'] = pass3_extract_dialogue(data_dir, results['players'])

    # Pass 4: Social dynamics
    if 4 in passes:
        results['alliances'], results['trust_updates'] = pass4_extract_social_dynamics(
            data_dir, results['players']
        )

    # Pass 5: Game flow norms
    if 5 in passes:
        results['phase_norms'] = pass5_extract_game_flow(data_dir)

    # Pass 6: Outcome analysis
    if 6 in passes:
        results['outcomes'] = pass6_analyze_outcomes(data_dir, results['players'])

    return results


def save_results(results: dict, output_dir: Path):
    """Save extraction results to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert dataclasses to dicts
    def serialize(obj):
        if hasattr(obj, '__dataclass_fields__'):
            d = asdict(obj)
            # Convert enums
            for k, v in d.items():
                if isinstance(v, Enum):
                    d[k] = v.value
                elif isinstance(v, list):
                    d[k] = [x.value if isinstance(x, Enum) else x for x in v]
            return d
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [serialize(x) for x in obj]
        return obj

    # Save each category
    for category, data in results.items():
        if not data:
            continue

        output_path = output_dir / f"extracted_{category}.json"

        serialized = serialize(data)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serialized, f, indent=2, ensure_ascii=False)

        print(f"Saved {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract training data from Traitors analysis")
    parser.add_argument('--data-dir', type=Path, default=Path('analysis'),
                       help='Directory containing analysis files')
    parser.add_argument('--output-dir', type=Path, default=Path('data/extracted'),
                       help='Directory for output files')
    parser.add_argument('--pass', dest='passes', type=int, nargs='+',
                       help='Specific passes to run (1-6)')
    parser.add_argument('--all', action='store_true',
                       help='Run all passes')

    args = parser.parse_args()

    passes = None
    if args.all:
        passes = [1, 2, 3, 4, 5, 6]
    elif args.passes:
        passes = args.passes
    else:
        passes = [1, 2, 3, 4, 5, 6]  # Default to all

    print("=" * 60)
    print("TRAITORS UK TRAINING DATA EXTRACTION PIPELINE")
    print("=" * 60)
    print(f"Data directory: {args.data_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Passes to run: {passes}")

    # Verify data exists
    if not args.data_dir.exists():
        print(f"Error: Data directory {args.data_dir} not found")
        return 1

    # Run extraction
    results = run_extraction_pipeline(args.data_dir, passes)

    # Save results
    save_results(results, args.output_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Players extracted: {len(results.get('players', {}))}")
    print(f"Strategic patterns: {len(results.get('strategies', []))}")
    print(f"Dialogue patterns: {len(results.get('dialogue', []))}")
    print(f"Alliance events: {len(results.get('alliances', []))}")
    print(f"Trust updates: {len(results.get('trust_updates', []))}")
    print(f"Phase norms: {len(results.get('phase_norms', []))}")

    return 0


if __name__ == '__main__':
    exit(main())
