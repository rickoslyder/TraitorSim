#!/usr/bin/env python3
"""Validate persona library for completeness and quality.

Checks:
- Required fields present
- OCEAN/stats in valid ranges
- Real-world brand leakage detection
- Backstory length
- Archetype distribution

Usage:
    python scripts/validate_personas.py
    python scripts/validate_personas.py --input data/personas/library/test_batch_001_personas.json
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traitorsim.utils.world_flavor import FORBIDDEN_BRANDS, detect_forbidden_brands


def validate_persona_card(persona: dict) -> list[str]:
    """Validate single persona card.

    Args:
        persona: Persona dict to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required top-level fields
    required_fields = [
        "name", "archetype", "archetype_name", "demographics",
        "backstory", "strategic_approach"
    ]

    for field in required_fields:
        if field not in persona or not persona[field]:
            errors.append(f"Missing or empty required field: {field}")

    # Check demographics subfields
    if "demographics" in persona and isinstance(persona["demographics"], dict):
        demographics_required = ["age", "location", "occupation"]
        for field in demographics_required:
            if field not in persona["demographics"]:
                errors.append(f"Missing demographics field: {field}")

    # Check OCEAN traits (if present)
    if "personality" in persona and isinstance(persona["personality"], dict):
        for trait, value in persona["personality"].items():
            if not isinstance(value, (int, float)):
                errors.append(f"Invalid personality value for {trait}: {value}")
            elif not 0.0 <= value <= 1.0:
                errors.append(f"Personality {trait} out of range [0, 1]: {value}")

    # Check stats (if present)
    if "stats" in persona and isinstance(persona["stats"], dict):
        for stat, value in persona["stats"].items():
            if not isinstance(value, (int, float)):
                errors.append(f"Invalid stat value for {stat}: {value}")
            elif not 0.0 <= value <= 1.0:
                errors.append(f"Stat {stat} out of range [0, 1]: {value}")

    # Check backstory length (200-300 words ≈ 1200-1800 chars, allow up to 1600)
    if "backstory" in persona:
        backstory = persona["backstory"]
        if len(backstory) < 200:
            errors.append(f"Backstory too short ({len(backstory)} chars, min 200)")
        if len(backstory) > 1600:
            errors.append(f"Backstory too long ({len(backstory)} chars, max 1600)")

    # Check for real-world brand leakage
    if "backstory" in persona:
        detected_brands = detect_forbidden_brands(persona["backstory"])
        for brand in detected_brands:
            errors.append(f"Real-world brand leak detected: '{brand}'")

    # Check key_relationships (if present)
    if "key_relationships" in persona:
        if not isinstance(persona["key_relationships"], list):
            errors.append("key_relationships must be a list")
        elif len(persona["key_relationships"]) < 2:
            errors.append(f"Need at least 2 key relationships, found {len(persona['key_relationships'])}")

    # Check hobbies (if present)
    if "hobbies" in persona:
        if not isinstance(persona["hobbies"], list):
            errors.append("hobbies must be a list")
        elif len(persona["hobbies"]) < 2:
            errors.append(f"Need at least 2 hobbies, found {len(persona['hobbies'])}")
        else:
            # Check for generic hobbies
            generic_hobbies = ["travel", "reading", "fitness", "music", "movies"]
            hobbies_lower = [h.lower() for h in persona["hobbies"]]
            generic_found = [h for h in generic_hobbies if h in " ".join(hobbies_lower)]
            if len(generic_found) >= 2:
                errors.append(f"Too many generic hobbies: {generic_found}")

    return errors


def validate_library(library_path: str, fail_fast: bool = True) -> bool:
    """Validate entire persona library.

    Args:
        library_path: Path to persona JSON file or directory
        fail_fast: Exit with error if validation fails

    Returns:
        True if all personas valid, False otherwise
    """
    library_path_obj = Path(library_path)

    # Load all personas
    all_personas = []

    if library_path_obj.is_file():
        with open(library_path_obj) as f:
            personas = json.load(f)
            if isinstance(personas, list):
                all_personas.extend(personas)
            else:
                all_personas.append(personas)
    elif library_path_obj.is_dir():
        for file in library_path_obj.glob("*.json"):
            with open(file) as f:
                personas = json.load(f)
                if isinstance(personas, list):
                    all_personas.extend(personas)
                else:
                    all_personas.append(personas)
    else:
        print(f"Error: Path not found: {library_path}")
        return False

    if not all_personas:
        print("Error: No personas found")
        return False

    print(f"Validating {len(all_personas)} personas...")
    print()

    # Validate each persona
    total_errors = 0
    personas_with_errors = 0

    for persona in all_personas:
        errors = validate_persona_card(persona)

        if errors:
            personas_with_errors += 1
            total_errors += len(errors)

            print(f"✗ {persona.get('name', 'Unknown')} ({persona.get('archetype_name', 'Unknown')})")
            for error in errors:
                print(f"    - {error}")
            print()

    # Check archetype distribution
    print("=" * 70)
    print("Archetype Distribution:")
    archetype_counts = Counter([p.get('archetype_name', 'Unknown') for p in all_personas])
    for archetype, count in sorted(archetype_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {archetype:30s}: {count}")
    print()

    # Summary
    if total_errors == 0:
        print("✓ All personas valid!")
        print(f"  {len(all_personas)} personas passed validation")
        return True
    else:
        print(f"✗ Found {total_errors} errors across {personas_with_errors}/{len(all_personas)} personas")

        if fail_fast:
            sys.exit(1)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate persona library")
    parser.add_argument("--input", type=str, default="data/personas/library", help="Persona JSON file or directory")
    parser.add_argument("--no-fail-fast", action="store_true", help="Don't exit with error on validation failure")

    args = parser.parse_args()

    # Validate
    is_valid = validate_library(args.input, fail_fast=not args.no_fail_fast)

    if is_valid:
        print()
        print("=" * 70)
        print("Validation complete! Persona library ready to use.")
        print()
        print("To use in game:")
        print("  1. Ensure persona library is in data/personas/library/")
        print("  2. Set config.personality_generation = 'archetype'")
        print("  3. Run game normally - personas will be loaded automatically")
        print("=" * 70)
    else:
        if not args.no_fail_fast:
            sys.exit(1)


if __name__ == "__main__":
    main()
