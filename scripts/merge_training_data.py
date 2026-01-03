#!/usr/bin/env python3
"""
Merge all extracted training data into unified datasets for TraitorSim.

Creates:
1. player_training_data.json - Complete player profiles with OCEAN, archetypes, strategies
2. strategy_playbook.json - Strategic patterns organized by role and phase
3. relationship_patterns.json - Social dynamics templates
4. dialogue_templates.json - Speech patterns by context
"""

import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional


def load_json(path: Path) -> dict | list:
    """Load JSON file, return empty dict/list if not found."""
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def merge_player_data(extracted_dir: Path) -> list[dict]:
    """Merge player data from all sources."""
    print("\nMerging player data...")

    # Load from different sources
    basic_players = load_json(extracted_dir / "extracted_players.json")
    deep_roles = load_json(extracted_dir / "deep_roles.json")
    deep_strategies = load_json(extracted_dir / "deep_strategies.json")
    relationships = load_json(extracted_dir / "deep_relationships.json")

    # Build relationship map
    player_relationships = defaultdict(list)
    for rel in relationships:
        p1, p2 = rel.get('player1', ''), rel.get('player2', '')
        rel_type = rel.get('type', '')
        strength = rel.get('strength', 0.5)

        if p1:
            player_relationships[p1].append({
                'partner': p2,
                'type': rel_type,
                'strength': strength,
            })
        if p2:
            player_relationships[p2].append({
                'partner': p1,
                'type': rel_type,
                'strength': strength,
            })

    # Build strategy map per player
    player_strategies = defaultdict(list)
    for strategy in deep_strategies:
        for example in strategy.get('examples_from_show', []):
            # Extract player names mentioned
            for player_name in basic_players.keys():
                if player_name in example:
                    player_strategies[player_name].append({
                        'strategy': strategy.get('strategy_name', ''),
                        'effectiveness': strategy.get('effectiveness_rating', 0.5),
                    })

    # Merge into unified profiles
    merged_players = []

    for name, basic in basic_players.items():
        role_info = deep_roles.get(name, {})

        profile = {
            'name': name,
            'age': basic.get('age'),
            'occupation': basic.get('occupation'),

            # Role
            'role': role_info.get('role', basic.get('role', 'unknown')),
            'role_confidence': role_info.get('confidence', 0.0),
            'role_evidence': role_info.get('evidence', ''),

            # OCEAN traits
            'ocean': {
                'openness': basic.get('ocean_traits', {}).get('openness', 0.5),
                'conscientiousness': basic.get('ocean_traits', {}).get('conscientiousness', 0.5),
                'extraversion': basic.get('ocean_traits', {}).get('extraversion', 0.5),
                'agreeableness': basic.get('ocean_traits', {}).get('agreeableness', 0.5),
                'neuroticism': basic.get('ocean_traits', {}).get('neuroticism', 0.5),
            },

            # Archetype
            'archetype': basic.get('archetype', ''),
            'archetype_confidence': basic.get('archetype_confidence', 0.0),

            # Behavioral observations
            'self_descriptions': basic.get('self_descriptions', [])[:5],
            'observed_behaviors': basic.get('observed_behaviors', []),

            # Relationships
            'relationships': player_relationships.get(name, []),

            # Strategies used
            'strategies_used': player_strategies.get(name, []),
        }

        merged_players.append(profile)

    # Sort by role then name
    merged_players.sort(key=lambda p: (
        0 if p['role'] == 'traitor' else 1 if p['role'] == 'faithful' else 2,
        p['name']
    ))

    print(f"  Merged {len(merged_players)} players")
    traitors = sum(1 for p in merged_players if p['role'] == 'traitor')
    faithfuls = sum(1 for p in merged_players if p['role'] == 'faithful')
    print(f"  Traitors: {traitors}, Faithfuls: {faithfuls}")

    return merged_players


def create_strategy_playbook(extracted_dir: Path) -> dict:
    """Create organized strategy playbook."""
    print("\nCreating strategy playbook...")

    basic_strategies = load_json(extracted_dir / "extracted_strategies.json")
    deep_strategies = load_json(extracted_dir / "deep_strategies.json")

    playbook = {
        'traitor_strategies': [],
        'faithful_strategies': [],
        'universal_strategies': [],
        'phase_strategies': defaultdict(list),
        'counter_strategies': {},
    }

    # Process deep strategies (richer data)
    for strat in deep_strategies:
        entry = {
            'name': strat.get('strategy_name', ''),
            'description': strat.get('description', ''),
            'effectiveness': strat.get('effectiveness_rating', 0.5),
            'risk_level': strat.get('risk_level', 'medium'),
            'best_phase': strat.get('best_phase', 'roundtable'),
            'counter_strategies': strat.get('counter_strategies', []),
            'examples': strat.get('examples_from_show', []),
        }

        best_used_by = strat.get('best_used_by', 'either')
        if best_used_by == 'traitor':
            playbook['traitor_strategies'].append(entry)
        elif best_used_by == 'faithful':
            playbook['faithful_strategies'].append(entry)
        else:
            playbook['universal_strategies'].append(entry)

        # Also organize by phase
        phase = strat.get('best_phase', 'roundtable')
        playbook['phase_strategies'][phase].append(entry['name'])

        # Build counter-strategy index
        for counter in entry['counter_strategies']:
            if counter not in playbook['counter_strategies']:
                playbook['counter_strategies'][counter] = []
            playbook['counter_strategies'][counter].append(entry['name'])

    # Add basic strategies if not already covered
    covered_names = {s.get('strategy_name', s.get('name', '')) for s in deep_strategies}

    for strat in basic_strategies:
        if strat.get('name', '') not in covered_names:
            entry = {
                'name': strat.get('name', ''),
                'description': strat.get('description', ''),
                'effectiveness': 0.5,  # Unknown
                'risk_level': 'medium',
            }

            roles = strat.get('applicable_roles', [])
            if 'traitor' in roles and 'faithful' not in roles:
                playbook['traitor_strategies'].append(entry)
            elif 'faithful' in roles and 'traitor' not in roles:
                playbook['faithful_strategies'].append(entry)
            else:
                playbook['universal_strategies'].append(entry)

    # Convert defaultdict for JSON serialization
    playbook['phase_strategies'] = dict(playbook['phase_strategies'])

    print(f"  Traitor strategies: {len(playbook['traitor_strategies'])}")
    print(f"  Faithful strategies: {len(playbook['faithful_strategies'])}")
    print(f"  Universal strategies: {len(playbook['universal_strategies'])}")

    return playbook


def create_relationship_patterns(extracted_dir: Path) -> dict:
    """Create relationship pattern templates."""
    print("\nCreating relationship patterns...")

    relationships = load_json(extracted_dir / "deep_relationships.json")
    alliances = load_json(extracted_dir / "extracted_alliances.json")

    # Categorize relationships by type
    patterns = {
        'alliance': [],
        'rivalry': [],
        'romantic': [],
        'suspicious': [],
        'trust': [],
        'mentor': [],
    }

    for rel in relationships:
        rel_type = rel.get('type', 'alliance')
        if rel_type in patterns:
            patterns[rel_type].append({
                'players': [rel.get('player1', ''), rel.get('player2', '')],
                'strength': rel.get('strength', 0.5),
                'evolution': rel.get('evolution', ''),
                'key_moments': rel.get('key_moments', []),
            })

    # Add alliance formation patterns
    alliance_triggers = defaultdict(int)
    for alliance in alliances:
        desc = alliance.get('description', '').lower()
        if 'train' in desc:
            alliance_triggers['shared_travel'] += 1
        if 'mission' in desc or 'challenge' in desc:
            alliance_triggers['mission_cooperation'] += 1
        if 'defend' in desc or 'support' in desc:
            alliance_triggers['mutual_defense'] += 1
        if 'vote' in desc:
            alliance_triggers['voting_alignment'] += 1

    patterns['alliance_triggers'] = dict(alliance_triggers)

    print(f"  Alliance patterns: {len(patterns['alliance'])}")
    print(f"  Rivalry patterns: {len(patterns['rivalry'])}")

    return patterns


def create_dialogue_templates(extracted_dir: Path) -> dict:
    """Create dialogue templates by context."""
    print("\nCreating dialogue templates...")

    basic_dialogue = load_json(extracted_dir / "extracted_dialogue.json")
    deep_dialogue = load_json(extracted_dir / "deep_dialogue.json")

    # Use basic dialogue as fallback since deep_dialogue may be empty
    templates = {}

    for pattern in basic_dialogue:
        context = pattern.get('context', 'general')
        templates[context] = {
            'phrases': pattern.get('phrases', [])[:20],  # Limit to 20
            'emotional_markers': pattern.get('emotional_markers', []),
            'phase': pattern.get('phase', 'roundtable'),
        }

    # Add deep dialogue if available
    if deep_dialogue:
        for context, data in deep_dialogue.items():
            if context not in templates:
                templates[context] = data
            else:
                # Merge
                if 'phrases' in data:
                    templates[context]['phrases'].extend(data['phrases'])
                if 'emotional_markers' in data:
                    templates[context]['emotional_markers'].extend(data['emotional_markers'])

    print(f"  Dialogue contexts: {len(templates)}")
    for context, data in templates.items():
        print(f"    {context}: {len(data.get('phrases', []))} phrases")

    return templates


def create_phase_norms(extracted_dir: Path) -> dict:
    """Create phase-specific behavioral norms."""
    print("\nCreating phase norms...")

    norms = load_json(extracted_dir / "extracted_phase_norms.json")

    phase_guide = {}

    for norm in norms:
        phase = norm.get('phase', 'unknown')
        phase_guide[phase] = {
            'expected_behaviors': norm.get('expected_behaviors', [])[:10],
            'traitor_specific': norm.get('traitor_specific', []),
            'faithful_specific': norm.get('faithful_specific', []),
        }

    print(f"  Phases documented: {len(phase_guide)}")

    return phase_guide


def main():
    extracted_dir = Path('data/extracted')
    output_dir = Path('data/training')
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("MERGING TRAINING DATA")
    print("=" * 60)

    # Create merged datasets
    players = merge_player_data(extracted_dir)
    playbook = create_strategy_playbook(extracted_dir)
    relationships = create_relationship_patterns(extracted_dir)
    dialogue = create_dialogue_templates(extracted_dir)
    phases = create_phase_norms(extracted_dir)

    # Save outputs
    datasets = {
        'player_profiles.json': players,
        'strategy_playbook.json': playbook,
        'relationship_patterns.json': relationships,
        'dialogue_templates.json': dialogue,
        'phase_norms.json': phases,
    }

    for filename, data in datasets.items():
        output_path = output_dir / filename
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved: {output_path}")

    # Create summary
    summary = {
        'generated_from': 'The Traitors UK Season 1 Analysis',
        'players_count': len(players),
        'traitors': [p['name'] for p in players if p['role'] == 'traitor'],
        'faithfuls': [p['name'] for p in players if p['role'] == 'faithful'],
        'strategies_count': (
            len(playbook['traitor_strategies']) +
            len(playbook['faithful_strategies']) +
            len(playbook['universal_strategies'])
        ),
        'relationship_patterns': len(relationships.get('alliance', [])),
        'dialogue_contexts': list(dialogue.keys()),
        'game_phases': list(phases.keys()),
    }

    summary_path = output_dir / 'training_data_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {summary_path}")

    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    main()
