#!/usr/bin/env python3
"""Generate skeleton personas for Deep Research processing.

Creates 10-20 candidate personas with:
- Archetype assignment (ensure diversity)
- OCEAN traits (sampled from archetype ranges)
- Demographic templates
- No backstories yet (filled by Deep Research)

Usage:
    python scripts/generate_skeleton_personas.py --count 15
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traitorsim.core.archetypes import ARCHETYPE_REGISTRY, select_archetype_for_cast


def generate_skeleton_batch(
    count: int = 15,
    max_per_archetype: int = 2,
    output_dir: str = "data/personas/skeletons"
) -> list:
    """Generate skeleton personas.

    Args:
        count: Number of skeletons to generate
        max_per_archetype: Maximum instances of same archetype (for diversity)
        output_dir: Output directory for skeletons

    Returns:
        List of skeleton dicts ready for Deep Research
    """
    skeletons = []
    existing_archetypes = []

    print(f"Generating {count} skeleton personas...")
    print(f"Ensuring archetype diversity (max {max_per_archetype} per archetype)")
    print()

    for i in range(count):
        # Select archetype (ensure diversity)
        archetype = select_archetype_for_cast(
            existing_archetypes,
            max_per_archetype=max_per_archetype
        )

        existing_archetypes.append(archetype.id)

        # Sample OCEAN from archetype ranges
        personality = archetype.sample_ocean()

        # Sample stats from archetype ranges
        stats = archetype.sample_stats()

        # Sample demographics from templates
        demographics_template = archetype.sample_demographics()

        # Add gender (not in archetype template)
        import random
        gender_choices = ["male", "female", "non-binary"]
        demographics_template["gender"] = random.choice(gender_choices)

        # Create skeleton
        skeleton = {
            "skeleton_id": f"skeleton_{i:03d}",
            "archetype": archetype.id,
            "archetype_name": archetype.name,
            "personality": personality,
            "stats": stats,
            "demographics_template": demographics_template,
            "strategic_drive": archetype.strategic_drive,
            "gameplay_tendency": archetype.gameplay_tendency
        }

        skeletons.append(skeleton)

        print(f"  [{i+1:02d}/{count}] {archetype.name:30s} | {demographics_template['occupation']:25s} | Age {demographics_template['age']}")

    print()
    print("=== Archetype Distribution ===")
    archetype_counts = Counter(existing_archetypes)
    for archetype_id, count_val in sorted(archetype_counts.items(), key=lambda x: x[1], reverse=True):
        archetype = ARCHETYPE_REGISTRY[archetype_id]
        print(f"  {archetype.name:30s}: {count_val} personas")

    return skeletons


def save_skeletons(skeletons: list, output_dir: str, batch_name: str = "test_batch_001"):
    """Save skeletons to JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / f"{batch_name}.json"

    with open(output_file, "w") as f:
        json.dump(skeletons, f, indent=2)

    print()
    print(f"✓ Saved {len(skeletons)} skeletons to: {output_file}")
    print()
    print("Next step: Run Deep Research batch processor")
    print(f"  python scripts/batch_deep_research.py")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate skeleton personas for Deep Research")
    parser.add_argument("--count", type=int, default=15, help="Number of skeletons to generate (default: 15)")
    parser.add_argument("--max-per-archetype", type=int, default=2, help="Max instances per archetype (default: 2)")
    parser.add_argument("--output", type=str, default="data/personas/skeletons", help="Output directory")
    parser.add_argument("--batch-name", type=str, default="test_batch_001", help="Batch name")

    args = parser.parse_args()

    # Validate count
    if args.count < 1 or args.count > 200:
        print("Error: Count must be between 1 and 200")
        sys.exit(1)

    # Generate skeletons
    skeletons = generate_skeleton_batch(
        count=args.count,
        max_per_archetype=args.max_per_archetype,
        output_dir=args.output
    )

    # Save to file
    save_skeletons(skeletons, args.output, args.batch_name)

    print("=== Generation Complete ===")
    print(f"Generated {len(skeletons)} personas across {len(set([s['archetype'] for s in skeletons]))} archetypes")


if __name__ == "__main__":
    main()
