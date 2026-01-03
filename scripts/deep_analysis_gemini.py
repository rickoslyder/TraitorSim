#!/usr/bin/env python3
"""
Deep Analysis with Gemini

Uses Gemini to perform sophisticated analysis passes on the Traitors UK data:
- Accurate role extraction from complex text
- Nuanced OCEAN trait inference
- Strategic pattern recognition
- Relationship mapping
- Success/failure correlation

Usage:
    python scripts/deep_analysis_gemini.py --pass role_extraction
    python scripts/deep_analysis_gemini.py --pass all
"""

import json
import os
import re
import asyncio
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum

# Use the google.genai Interactions API
from google import genai


# =============================================================================
# CONFIGURATION
# =============================================================================

GEMINI_MODEL = "gemini-2.5-flash"  # Fast and capable

# Rate limiting
REQUESTS_PER_MINUTE = 10
REQUEST_DELAY = 60.0 / REQUESTS_PER_MINUTE


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class EnhancedPlayerProfile:
    """Enhanced player profile from Gemini analysis."""
    name: str
    age: Optional[int] = None
    occupation: Optional[str] = None
    role: str = "unknown"  # traitor, faithful, or unknown
    role_confidence: float = 0.0

    # OCEAN with detailed evidence
    openness: float = 0.5
    openness_rationale: str = ""
    conscientiousness: float = 0.5
    conscientiousness_rationale: str = ""
    extraversion: float = 0.5
    extraversion_rationale: str = ""
    agreeableness: float = 0.5
    agreeableness_rationale: str = ""
    neuroticism: float = 0.5
    neuroticism_rationale: str = ""

    # Archetype
    primary_archetype: str = ""
    secondary_archetype: str = ""
    archetype_rationale: str = ""

    # Game outcome
    survived: bool = False
    elimination_method: str = ""  # murdered, banished, winner
    elimination_episode: Optional[int] = None

    # Key relationships
    closest_ally: str = ""
    biggest_enemy: str = ""
    key_relationships: list = None

    # Strategic profile
    dominant_strategy: str = ""
    strategy_effectiveness: str = ""
    notable_moves: list = None

    def __post_init__(self):
        if self.key_relationships is None:
            self.key_relationships = []
        if self.notable_moves is None:
            self.notable_moves = []


@dataclass
class StrategicInsight:
    """Deep strategic insight from Gemini analysis."""
    strategy_name: str
    description: str
    effectiveness_rating: float  # 0-1
    risk_level: str  # low, medium, high
    best_used_by: str  # traitor, faithful, either
    best_phase: str  # arrival, breakfast, mission, social, roundtable, murder
    counter_strategies: list = None
    examples_from_show: list = None

    def __post_init__(self):
        if self.counter_strategies is None:
            self.counter_strategies = []
        if self.examples_from_show is None:
            self.examples_from_show = []


@dataclass
class SocialDynamicPattern:
    """Social dynamic pattern from Gemini analysis."""
    pattern_name: str
    description: str
    triggers: list = None
    typical_progression: str = ""
    outcome_distribution: dict = None  # {"positive": 0.6, "negative": 0.4}
    examples: list = None

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []
        if self.outcome_distribution is None:
            self.outcome_distribution = {}
        if self.examples is None:
            self.examples = []


# =============================================================================
# GEMINI CLIENT
# =============================================================================

class GeminiAnalyzer:
    """Gemini-based analyzer for deep extraction."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")

        self.client = genai.Client(api_key=self.api_key)
        self.interaction_id = None

    async def analyze(self, prompt: str, context: str = "") -> str:
        """Send analysis prompt to Gemini."""

        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n{prompt}"

        try:
            # Use Interactions API with chaining for context
            interaction = self.client.interactions.create(
                model=GEMINI_MODEL,
                input=full_prompt,
                previous_interaction_id=self.interaction_id,
            )

            # Save interaction ID for chaining
            self.interaction_id = interaction.id

            return interaction.outputs[-1].text.strip()

        except Exception as e:
            print(f"Gemini API error: {e}")
            return ""

    def reset_context(self):
        """Reset conversation context."""
        self.interaction_id = None


# =============================================================================
# PASS: ROLE EXTRACTION
# =============================================================================

async def extract_roles_with_gemini(
    analyzer: GeminiAnalyzer,
    synthesis_text: str,
) -> dict[str, dict]:
    """
    Use Gemini to accurately extract player roles from the analysis.
    """
    print("\n" + "=" * 60)
    print("DEEP ANALYSIS: ROLE EXTRACTION")
    print("=" * 60)

    prompt = """
Analyze this text from The Traitors UK Season 1 analysis and extract ALL players with their roles.

For each player, provide:
1. Name
2. Role: "traitor", "faithful", or "unknown"
3. Confidence: 0.0-1.0 (how certain based on text evidence)
4. Evidence: Brief quote or summary supporting the role assignment

IMPORTANT: Look for explicit role revelations like:
- "Role: Traitor" or "Role: Faithful"
- "was revealed as a Traitor"
- "Alyssa, Wilfred, and Amanda are the Traitors"
- References to characters doing "Traitor things" like murder planning

Return as JSON array:
[
  {"name": "PlayerName", "role": "traitor", "confidence": 0.95, "evidence": "explicitly stated as Traitor"},
  ...
]

Analyze this text:
"""

    # Split text into chunks if too long
    chunk_size = 30000
    chunks = [synthesis_text[i:i+chunk_size] for i in range(0, len(synthesis_text), chunk_size)]

    all_players = {}

    for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 chunks
        print(f"  Analyzing chunk {i+1}/{min(len(chunks), 5)}...")

        response = await analyzer.analyze(prompt + chunk[:chunk_size])

        # Extract JSON from response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                players = json.loads(json_match.group())
                for player in players:
                    name = player.get('name', '')
                    if name and name not in ['Episode', 'Season', 'Traitor', 'Faithful']:
                        if name not in all_players or player.get('confidence', 0) > all_players[name].get('confidence', 0):
                            all_players[name] = player
            except json.JSONDecodeError:
                pass

        await asyncio.sleep(REQUEST_DELAY)

    print(f"\nExtracted roles for {len(all_players)} players")

    # Summary
    traitors = [n for n, p in all_players.items() if p.get('role') == 'traitor']
    faithfuls = [n for n, p in all_players.items() if p.get('role') == 'faithful']

    print(f"  Traitors ({len(traitors)}): {', '.join(traitors)}")
    print(f"  Faithfuls ({len(faithfuls)}): {', '.join(faithfuls[:10])}...")

    return all_players


# =============================================================================
# PASS: OCEAN TRAIT ANALYSIS
# =============================================================================

async def analyze_ocean_traits(
    analyzer: GeminiAnalyzer,
    player_name: str,
    player_context: str,
) -> dict:
    """
    Use Gemini to analyze OCEAN traits for a specific player.
    """
    prompt = f"""
Analyze the personality of {player_name} from The Traitors UK based on the following observations.

For each Big Five (OCEAN) trait, provide:
1. Score: 0.0 (very low) to 1.0 (very high)
2. Rationale: 2-3 sentence explanation with specific behavioral evidence

Traits to analyze:
- Openness: creativity, curiosity, willingness to try new approaches
- Conscientiousness: organization, reliability, goal-orientation
- Extraversion: sociability, assertiveness, energy level
- Agreeableness: cooperation, trust, empathy vs competition/manipulation
- Neuroticism: emotional stability, anxiety, stress response

Return as JSON:
{{
  "openness": {{"score": 0.7, "rationale": "..."}},
  "conscientiousness": {{"score": 0.6, "rationale": "..."}},
  "extraversion": {{"score": 0.8, "rationale": "..."}},
  "agreeableness": {{"score": 0.4, "rationale": "..."}},
  "neuroticism": {{"score": 0.5, "rationale": "..."}}
}}

Player observations:
{player_context}
"""

    response = await analyzer.analyze(prompt)

    # Extract JSON
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {}


# =============================================================================
# PASS: ARCHETYPE MAPPING
# =============================================================================

async def map_archetypes(
    analyzer: GeminiAnalyzer,
    player_name: str,
    player_context: str,
    ocean_traits: dict,
) -> dict:
    """
    Use Gemini to map player to TraitorSim archetypes.
    """
    prompt = f"""
Map {player_name} from The Traitors UK to one of these TraitorSim archetypes:

ARCHETYPES:
1. The Prodigy - Young, intelligent, ambitious, confident in abilities
2. The Sage - Wise, experienced, gives advice, calm authority
3. The Charming Sociopath - Manipulative but likeable, puppet master tendencies
4. The Paranoid - Suspicious of everyone, high anxiety, defensive
5. The Underdog - Underestimated, humble, plays low profile
6. The Alpha - Dominant leader, assertive, takes charge
7. The Social Butterfly - Extremely social, popular, builds many connections
8. The Analyst - Quiet observer, strategic thinker, data-driven decisions
9. The Wildcard - Unpredictable, emotional, chaotic energy
10. The Matriarch/Patriarch - Parental figure, protective, nurturing
11. The Entertainer - Performer, uses humor/charm, center of attention
12. The Truthseeker - Detective mindset, confrontational, seeks to expose liars

Their OCEAN traits: {json.dumps(ocean_traits)}

Based on their behaviors and personality, provide:
1. Primary archetype (best match)
2. Secondary archetype (if applicable)
3. Rationale explaining why they fit these archetypes

Return as JSON:
{{
  "primary_archetype": "The Charming Sociopath",
  "secondary_archetype": "The Alpha",
  "rationale": "..."
}}

Player context:
{player_context}
"""

    response = await analyzer.analyze(prompt)

    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {}


# =============================================================================
# PASS: STRATEGIC PATTERN EXTRACTION
# =============================================================================

async def extract_strategic_patterns(
    analyzer: GeminiAnalyzer,
    synthesis_text: str,
) -> list[StrategicInsight]:
    """
    Use Gemini to extract and analyze strategic patterns.
    """
    print("\n" + "=" * 60)
    print("DEEP ANALYSIS: STRATEGIC PATTERNS")
    print("=" * 60)

    prompt = """
Analyze The Traitors UK gameplay and extract the most effective strategies used.

For each strategy, provide:
1. Name: Clear, descriptive name
2. Description: How the strategy works (2-3 sentences)
3. Effectiveness: 0.0-1.0 rating based on observed outcomes
4. Risk Level: "low", "medium", or "high"
5. Best Used By: "traitor", "faithful", or "either"
6. Best Phase: "arrival", "breakfast", "mission", "social", "roundtable", or "murder"
7. Counter-strategies: How to defend against this strategy
8. Examples: Specific instances from the show

Return as JSON array of 10-15 key strategies:
[
  {
    "strategy_name": "The Puppet Master",
    "description": "Form alliances then manipulate allies to vote for your targets...",
    "effectiveness_rating": 0.8,
    "risk_level": "medium",
    "best_used_by": "traitor",
    "best_phase": "roundtable",
    "counter_strategies": ["Track voting patterns", "Share information widely"],
    "examples_from_show": ["Wilfred used this to control votes through Episode 6"]
  },
  ...
]

Text to analyze:
"""

    # Use a representative chunk
    chunk = synthesis_text[:50000]

    response = await analyzer.analyze(prompt + chunk)

    strategies = []
    json_match = re.search(r'\[[\s\S]*\]', response)
    if json_match:
        try:
            raw_strategies = json.loads(json_match.group())
            for s in raw_strategies:
                strategies.append(StrategicInsight(
                    strategy_name=s.get('strategy_name', ''),
                    description=s.get('description', ''),
                    effectiveness_rating=s.get('effectiveness_rating', 0.5),
                    risk_level=s.get('risk_level', 'medium'),
                    best_used_by=s.get('best_used_by', 'either'),
                    best_phase=s.get('best_phase', 'roundtable'),
                    counter_strategies=s.get('counter_strategies', []),
                    examples_from_show=s.get('examples_from_show', []),
                ))
        except json.JSONDecodeError:
            pass

    print(f"Extracted {len(strategies)} strategic patterns")
    for s in strategies[:5]:
        print(f"  [{s.best_used_by}] {s.strategy_name} (effectiveness: {s.effectiveness_rating})")

    return strategies


# =============================================================================
# PASS: DIALOGUE PATTERN EXTRACTION
# =============================================================================

async def extract_dialogue_patterns(
    analyzer: GeminiAnalyzer,
    synthesis_text: str,
) -> dict:
    """
    Use Gemini to extract dialogue patterns by context.
    """
    print("\n" + "=" * 60)
    print("DEEP ANALYSIS: DIALOGUE PATTERNS")
    print("=" * 60)

    prompt = """
Analyze dialogue from The Traitors UK and extract speech patterns for different contexts.

For each context, provide:
1. Common phrases and their variations
2. Emotional markers (crying, laughing, nervous ticks)
3. Rhetorical devices used
4. Success rate (did this type of speech achieve its goal?)

Contexts to analyze:
- ACCUSATION: Language used when accusing someone of being a Traitor
- DEFENSE: Language used when defending against accusations
- ALLIANCE_BUILDING: Language used to form alliances
- BETRAYAL: Language used when betraying an ally
- GRIEF: Language when mourning a murdered player
- VICTORY: Language when successfully banishing a Traitor
- MISDIRECTION: Language used by Traitors to deflect

Return as JSON:
{
  "accusation": {
    "phrases": ["I think you're a Traitor because...", "Your behavior has been suspicious..."],
    "emotional_markers": ["pointing", "raised voice", "direct eye contact"],
    "rhetorical_devices": ["citing specific evidence", "appealing to group consensus"],
    "success_indicators": ["getting votes", "changing minds"]
  },
  ...
}

Text to analyze:
"""

    chunk = synthesis_text[:40000]
    response = await analyzer.analyze(prompt + chunk)

    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            patterns = json.loads(json_match.group())
            print(f"Extracted patterns for {len(patterns)} dialogue contexts")
            return patterns
        except json.JSONDecodeError:
            pass

    return {}


# =============================================================================
# PASS: RELATIONSHIP NETWORK EXTRACTION
# =============================================================================

async def extract_relationships(
    analyzer: GeminiAnalyzer,
    synthesis_text: str,
) -> list[dict]:
    """
    Use Gemini to extract the relationship network.
    """
    print("\n" + "=" * 60)
    print("DEEP ANALYSIS: RELATIONSHIP NETWORK")
    print("=" * 60)

    prompt = """
Analyze The Traitors UK and map the key relationships between players.

For each significant relationship, provide:
1. Player1: First player name
2. Player2: Second player name
3. Relationship type: "alliance", "rivalry", "mentor", "romantic", "suspicious", "trust"
4. Strength: 0.0-1.0
5. Evolution: How did this relationship change over the season?
6. Key moments: Specific events that defined the relationship

Return as JSON array of 20-30 most important relationships:
[
  {
    "player1": "Wilfred",
    "player2": "Amanda",
    "type": "alliance",
    "strength": 0.9,
    "evolution": "Fellow Traitors who maintained strong partnership throughout",
    "key_moments": ["First murder selection together", "Defended each other at Round Table"]
  },
  ...
]

Text to analyze:
"""

    chunk = synthesis_text[:50000]
    response = await analyzer.analyze(prompt + chunk)

    relationships = []
    json_match = re.search(r'\[[\s\S]*\]', response)
    if json_match:
        try:
            relationships = json.loads(json_match.group())
            print(f"Extracted {len(relationships)} key relationships")
        except json.JSONDecodeError:
            pass

    return relationships


# =============================================================================
# PASS: ELIMINATION PATTERN ANALYSIS
# =============================================================================

async def analyze_eliminations(
    analyzer: GeminiAnalyzer,
    synthesis_text: str,
) -> dict:
    """
    Use Gemini to analyze elimination patterns.
    """
    print("\n" + "=" * 60)
    print("DEEP ANALYSIS: ELIMINATION PATTERNS")
    print("=" * 60)

    prompt = """
Analyze all eliminations in The Traitors UK Season 1.

Provide:
1. Complete elimination order with details
2. Murder patterns (who did Traitors tend to target and why?)
3. Banishment accuracy (how often did Faithfuls correctly identify Traitors?)
4. Key turning points (banishments that changed the game)

Return as JSON:
{
  "elimination_order": [
    {"episode": 1, "name": "Player", "method": "murder/banishment", "role": "traitor/faithful", "reason": "..."},
    ...
  ],
  "murder_patterns": {
    "target_selection_criteria": ["Loud players", "Alliance leaders", "Those close to discovering truth"],
    "timing_patterns": "Traitors often killed potential accusers before Round Table"
  },
  "banishment_accuracy": {
    "correct_banishments": 3,
    "incorrect_banishments": 5,
    "accuracy_rate": 0.375,
    "common_mistakes": ["Voting out loud players", "Bandwagon voting"]
  },
  "turning_points": [
    {"episode": 6, "event": "Banishment of Wilfred", "impact": "First Traitor caught, shifted momentum to Faithfuls"}
  ]
}

Text to analyze:
"""

    chunk = synthesis_text[:60000]
    response = await analyzer.analyze(prompt + chunk)

    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            analysis = json.loads(json_match.group())
            print(f"Analyzed {len(analysis.get('elimination_order', []))} eliminations")
            accuracy = analysis.get('banishment_accuracy', {}).get('accuracy_rate', 0)
            print(f"Banishment accuracy: {accuracy:.1%}")
            return analysis
        except json.JSONDecodeError:
            pass

    return {}


# =============================================================================
# MAIN PIPELINE
# =============================================================================

async def run_deep_analysis(data_dir: Path, output_dir: Path, passes: list[str]):
    """Run deep analysis with Gemini."""

    print("=" * 60)
    print("GEMINI DEEP ANALYSIS PIPELINE")
    print("=" * 60)

    # Load source data
    synthesis_path = data_dir / "SIMULATOR_SYNTHESIS.md"
    with open(synthesis_path, 'r') as f:
        synthesis_text = f.read()

    print(f"Loaded {len(synthesis_text):,} characters of analysis data")

    # Initialize analyzer
    analyzer = GeminiAnalyzer()

    results = {}

    # Run requested passes
    if 'roles' in passes or 'all' in passes:
        results['roles'] = await extract_roles_with_gemini(analyzer, synthesis_text)
        await asyncio.sleep(REQUEST_DELAY)

    if 'strategies' in passes or 'all' in passes:
        analyzer.reset_context()
        results['strategies'] = await extract_strategic_patterns(analyzer, synthesis_text)
        await asyncio.sleep(REQUEST_DELAY)

    if 'dialogue' in passes or 'all' in passes:
        analyzer.reset_context()
        results['dialogue'] = await extract_dialogue_patterns(analyzer, synthesis_text)
        await asyncio.sleep(REQUEST_DELAY)

    if 'relationships' in passes or 'all' in passes:
        analyzer.reset_context()
        results['relationships'] = await extract_relationships(analyzer, synthesis_text)
        await asyncio.sleep(REQUEST_DELAY)

    if 'eliminations' in passes or 'all' in passes:
        analyzer.reset_context()
        results['eliminations'] = await analyze_eliminations(analyzer, synthesis_text)

    # Deep player analysis (uses multiple API calls per player)
    if 'players_deep' in passes:
        print("\n" + "=" * 60)
        print("DEEP ANALYSIS: INDIVIDUAL PLAYERS")
        print("=" * 60)

        # Get roles first if not already done
        if 'roles' not in results:
            results['roles'] = await extract_roles_with_gemini(analyzer, synthesis_text)

        enhanced_players = []
        player_names = list(results['roles'].keys())[:15]  # Limit to 15 players

        for i, name in enumerate(player_names):
            print(f"\nAnalyzing {name} ({i+1}/{len(player_names)})...")

            # Find player context
            pattern = rf'\*\*{name}\*\*.*?(?=\*\*[A-Z]|\n##|\Z)'
            matches = re.findall(pattern, synthesis_text, re.DOTALL)
            context = "\n".join(matches[:5])[:3000]

            if not context:
                continue

            # OCEAN analysis
            analyzer.reset_context()
            ocean = await analyze_ocean_traits(analyzer, name, context)
            await asyncio.sleep(REQUEST_DELAY)

            # Archetype mapping
            archetype = await map_archetypes(analyzer, name, context, ocean)
            await asyncio.sleep(REQUEST_DELAY)

            # Build profile
            role_info = results['roles'].get(name, {})
            profile = EnhancedPlayerProfile(
                name=name,
                role=role_info.get('role', 'unknown'),
                role_confidence=role_info.get('confidence', 0.0),
            )

            # Add OCEAN
            for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
                if trait in ocean:
                    setattr(profile, trait, ocean[trait].get('score', 0.5))
                    setattr(profile, f"{trait}_rationale", ocean[trait].get('rationale', ''))

            # Add archetype
            profile.primary_archetype = archetype.get('primary_archetype', '')
            profile.secondary_archetype = archetype.get('secondary_archetype', '')
            profile.archetype_rationale = archetype.get('rationale', '')

            enhanced_players.append(asdict(profile))
            print(f"  → {profile.primary_archetype}, {profile.role}")

        results['enhanced_players'] = enhanced_players

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, data in results.items():
        output_path = output_dir / f"deep_{key}.json"

        # Handle dataclass serialization
        if isinstance(data, list) and data and hasattr(data[0], '__dataclass_fields__'):
            data = [asdict(item) for item in data]

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSaved: {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Deep analysis with Gemini")
    parser.add_argument('--data-dir', type=Path, default=Path('analysis'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/extracted'))
    parser.add_argument('--pass', dest='passes', nargs='+',
                       choices=['all', 'roles', 'strategies', 'dialogue',
                               'relationships', 'eliminations', 'players_deep'],
                       default=['all'])

    args = parser.parse_args()

    asyncio.run(run_deep_analysis(args.data_dir, args.output_dir, args.passes))


if __name__ == '__main__':
    main()
