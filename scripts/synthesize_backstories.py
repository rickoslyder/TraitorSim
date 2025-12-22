#!/usr/bin/env python3
"""Synthesize final persona cards from skeletons + Deep Research reports.

Uses Claude to generate:
- Narrative backstory (first-person, 200-300 words)
- Specific key relationships
- Formative trauma/challenge
- Strategic motivations

Usage:
    python scripts/synthesize_backstories.py
    python scripts/synthesize_backstories.py --reports data/personas/reports/test_batch_001_reports.json
"""

import argparse
import json
import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traitorsim.utils.world_flavor import (
    IN_UNIVERSE_BRANDS,
    FORBIDDEN_BRANDS,
    detect_forbidden_brands
)

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, AssistantMessage
    from claude_agent_sdk.types import TextBlock
except ImportError:
    print("Error: claude_agent_sdk package not installed")
    print("Install with: pip install claude-agent-sdk")
    sys.exit(1)


async def synthesize_batch_single_query(
    reports: list,
    model: str = "claude-opus-4-5-20251101"
) -> list:
    """Generate all personas in a single Claude query.

    Args:
        reports: List of report dicts with skeleton data
        model: Claude model to use

    Returns:
        List of complete persona cards
    """
    # Build a single batch prompt for all personas
    personas_context = []
    for i, report_data in enumerate(reports, 1):
        personas_context.append(f"""
## PERSONA {i}: {report_data['skeleton_id']}

**Skeleton Profile:**
- Archetype: {report_data['archetype_name']}
- Age: {report_data['demographics']['age']}
- Occupation: {report_data['demographics']['occupation']}
- Location: {report_data['demographics']['location']}
- Gender: {report_data['demographics']['gender']}
- Socioeconomic: {report_data['demographics']['socioeconomic']}

**Deep Research Context (first 2000 chars):**
```
{report_data['report'][:2000]}...
```
""")

    batch_prompt = f"""You are creating persona cards for AI agents playing "The Traitors" reality TV show. You will create {len(reports)} distinct personas.

{chr(10).join(personas_context)}

**Your Task:**
Generate {len(reports)} complete persona cards. Output ONLY a JSON array where each element has these exact keys:

[
  {{
    "skeleton_id": "skeleton_XXX",
    "name": "Realistic UK name appropriate for age/ethnicity",
    "backstory": "First-person narrative (200-300 words) covering childhood, family, education, career, current life, why they need the prize money, personality quirks, speaking style",
    "key_relationships": ["Specific person 1 (relationship, emotional stakes)", "Specific person 2", "Specific person 3"],
    "formative_challenge": "One major past experience that shaped them (related to trust/betrayal themes)",
    "political_philosophical_beliefs": "Specific positions and how they affect gameplay (not just 'left-wing' or 'right-wing')",
    "hobbies": ["Specific hobby 1 (not generic 'travel')", "Specific hobby 2", "Specific hobby 3"],
    "strategic_approach": "How their personality translates to gameplay tactics in The Traitors"
  }},
  ...
]

**Critical Constraints:**
1. **In-Universe Brands ONLY** (World Bible compliance):
   - Water: Highland Spring Co., Coffee: Cairngorm Coffee, Internet: ScotNet
   - Streaming: Highland Play, Production: CastleVision, News: The Highland Herald

2. **FORBIDDEN - Never mention these real-world brands:**
   - Facebook, Twitter, Instagram, TikTok, Snapchat, Starbucks, Costa, McDonald's
   - Tesco, Sainsbury's, Asda, Waitrose, Google, Amazon, Netflix, Uber

3. Reflect Deep Research findings - don't contradict the context
4. Each persona must be unique and three-dimensional
5. Cultural authenticity to UK context (especially their specific location)
6. Specific details - "plays 5-a-side football at Victoria Park" not "enjoys sports"
7. Backstories in FIRST PERSON ("I grew up in...")
8. Reference real UK places/neighborhoods from their location

**Tone:** Authentic, grounded, human. These people should feel real, not like character sketches."""

    # Call Claude via SDK (single query for all personas)
    try:
        options = ClaudeAgentOptions(
            model=model
        )

        # Query Claude and collect response
        response_text = ""
        async for message in query(prompt=batch_prompt, options=options):
            if isinstance(message, AssistantMessage):
                # Extract text from content blocks
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
            elif isinstance(message, ResultMessage):
                break

        # Find JSON in response (may have markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text.strip()

        personas_data = json.loads(json_text)

        # Merge with skeleton data
        persona_cards = []
        for persona_data in personas_data:
            # Find matching report
            skeleton_id = persona_data["skeleton_id"]
            report_data = next(r for r in reports if r["skeleton_id"] == skeleton_id)

            persona_card = {
                "skeleton_id": skeleton_id,
                "archetype": report_data["archetype"],
                "archetype_name": report_data["archetype_name"],
                "personality": report_data.get("personality", {}),
                "stats": report_data.get("stats", {}),
                "demographics": report_data["demographics"],
                "name": persona_data["name"],
                "backstory": persona_data["backstory"],
                "key_relationships": persona_data["key_relationships"],
                "formative_challenge": persona_data["formative_challenge"],
                "political_beliefs": persona_data["political_philosophical_beliefs"],
                "hobbies": persona_data["hobbies"],
                "strategic_approach": persona_data["strategic_approach"],
                "research_report_snippet": report_data["report"][:500]
            }
            persona_cards.append(persona_card)

        return persona_cards

    except json.JSONDecodeError as e:
        print(f"    ✗ JSON parsing error: {e}")
        print(f"    Response preview: {response_text[:500]}")
        raise
    except Exception as e:
        print(f"    ✗ Error in batch synthesis: {e}")
        raise


async def synthesize_batch(
    reports_file: str,
    output_dir: str,
    batch_name: str,
    model: str = "claude-opus-4-5-20251101",
    chunk_size: int = 6
):
    """Synthesize all personas in smaller batches.

    Args:
        reports_file: Path to Deep Research reports JSON
        output_dir: Output directory for persona library
        batch_name: Batch identifier
        model: Claude model to use
        chunk_size: Number of personas per batch query (default: 6)
    """
    # Verify environment variable for Claude Agent SDK
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if not oauth_token:
        print("Error: CLAUDE_CODE_OAUTH_TOKEN not set")
        print("Set this environment variable to use Claude Agent SDK")
        sys.exit(1)

    print("✅ Using Claude subscription via CLAUDE_CODE_OAUTH_TOKEN (Agent SDK)")

    # Load reports
    print(f"Loading reports from: {reports_file}")
    with open(reports_file) as f:
        reports = json.load(f)

    total = len(reports)
    print(f"Loaded {total} research reports")
    print()

    # Process in chunks to avoid response truncation
    num_chunks = (total + chunk_size - 1) // chunk_size
    print(f"Synthesizing {total} persona cards using {model}")
    print(f"Processing {num_chunks} batches of {chunk_size} personas (sequentially)...")
    print()

    all_personas = []
    failed = []

    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * chunk_size
        end_idx = min(start_idx + chunk_size, total)
        chunk_reports = reports[start_idx:end_idx]

        print(f"[Batch {chunk_idx + 1}/{num_chunks}] Processing {len(chunk_reports)} personas ({start_idx + 1}-{end_idx})...")

        try:
            personas = await synthesize_batch_single_query(chunk_reports, model=model)
            all_personas.extend(personas)

            for persona in personas:
                archetype = persona["archetype_name"]
                print(f"  ✓ {persona['name']:30s} | {archetype}")

            print()

        except Exception as e:
            print(f"  ✗ Batch {chunk_idx + 1} failed: {e}")
            for r in chunk_reports:
                failed.append({"skeleton_id": r["skeleton_id"], "error": str(e)})
            print()

    personas = all_personas

    print()
    print("=" * 70)
    print(f"✓ Synthesized {len(personas)}/{total} personas")
    if failed:
        print(f"✗ Failed: {len(failed)}")
        for f in failed:
            print(f"  - {f['skeleton_id']}: {f['error']}")
    print()

    # Save persona library
    if personas:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        output_file = output_path / f"{batch_name}_personas.json"

        with open(output_file, "w") as f:
            json.dump(personas, f, indent=2)

        print(f"✓ Saved {len(personas)} personas to: {output_file}")
        print()
        print("Next step: Validate persona library")
        print(f"  python scripts/validate_personas.py --input {output_file}")
        print("=" * 70)
    else:
        print("✗ No personas generated")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Synthesize backstories from research reports")
    parser.add_argument("--reports", type=str, default="data/personas/reports/test_batch_001_reports.json", help="Research reports JSON file")
    parser.add_argument("--output", type=str, default="data/personas/library", help="Output directory for persona library")
    parser.add_argument("--batch-name", type=str, default="test_batch_001", help="Batch name")
    parser.add_argument("--model", type=str, default="claude-opus-4-5-20251101", help="Claude model")

    args = parser.parse_args()

    # Validate input
    if not Path(args.reports).exists():
        print(f"Error: Reports file not found: {args.reports}")
        sys.exit(1)

    # Run synthesizer
    asyncio.run(synthesize_batch(
        reports_file=args.reports,
        output_dir=args.output,
        batch_name=args.batch_name,
        model=args.model
    ))


if __name__ == "__main__":
    main()
