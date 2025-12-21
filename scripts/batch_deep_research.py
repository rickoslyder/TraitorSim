#!/usr/bin/env python3
"""Submit Deep Research jobs for persona backstory generation.

Uses Gemini Interactions API with:
- File Search grounding (World Bible)
- Background jobs (5-15 min per persona)
- Batch processing with rate limiting

Usage:
    python scripts/batch_deep_research.py
    python scripts/batch_deep_research.py --input data/personas/skeletons/test_batch_001.json
"""

import argparse
import json
import os
import sys
import asyncio
import time
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("Error: google-genai package not installed")
    print("Install with: pip install google-genai")
    sys.exit(1)


async def upload_world_bible(client: genai.Client, world_bible_path: str):
    """Upload World Bible for file_search grounding.

    Args:
        client: Gemini client
        world_bible_path: Path to WORLD_BIBLE.md

    Returns:
        File upload response with file_id
    """
    print(f"Uploading World Bible from: {world_bible_path}")

    if not Path(world_bible_path).exists():
        raise FileNotFoundError(f"World Bible not found: {world_bible_path}")

    # Upload file
    file_response = client.files.upload(file=world_bible_path)

    print(f"✓ World Bible uploaded: {file_response.name} (ID: {file_response.name})")
    print()

    return file_response


async def submit_deep_research_job(
    client: genai.Client,
    skeleton: dict
) -> str:
    """Submit Deep Research job for one skeleton.

    Args:
        client: Gemini client
        skeleton: Skeleton persona dict

    Returns:
        interaction_id for later retrieval
    """
    # Build Deep Research prompt (includes instructions since system_instruction not supported)
    prompt = f"""You are a demographic researcher creating authentic life context for reality TV contestants. Focus on grounded, realistic details with citations from credible sources.

Research the typical life context for the following demographic profile in the UK:

**Demographics:**
- Age: {skeleton['demographics_template']['age']}
- Gender: {skeleton['demographics_template']['gender']}
- Location: {skeleton['demographics_template']['location']}
- Occupation: {skeleton['demographics_template']['occupation']}
- Socioeconomic class: {skeleton['demographics_template']['socioeconomic']}

**Personality Archetype:** {skeleton['archetype_name']}
- Strategic drive: {skeleton['strategic_drive']}
- Gameplay tendency: {skeleton['gameplay_tendency']}

**Research Requirements:**
Provide a comprehensive, well-cited report on the typical life context for this demographic profile. Include:

1. **Daily Life & Work Routines**: Typical work schedule, commute, daily activities for this occupation in {skeleton['demographics_template']['location']}

2. **Financial Situation**: Average salary range for this occupation, typical monthly expenses, economic stressors (rent, debt, savings)

3. **Family Background & Living Arrangements**: Common family structures, typical housing situation (renting vs owning, flatmates vs solo), relationship patterns

4. **Hobbies & Social Life**: Common leisure activities, social circles, weekend patterns, entertainment preferences

5. **Language & Cultural References**: Regional dialect, slang, speaking style for {skeleton['demographics_template']['location']}, pop culture references

6. **Political Leanings & Attitudes**: Typical voting patterns for this demographic, social attitudes, community involvement

7. **Neighborhood Context**: Specific areas/suburbs in {skeleton['demographics_template']['location']} where this demographic typically lives, local amenities, transport links

**Critical Constraints:**
- This is for a reality TV show simulation set in "The Traitors" universe defined in the World Bible
- Use in-universe brands from World Bible: Highland Spring Co. (water), Cairngorm Coffee Roasters (coffee), ScotNet (internet), CastleVision (production company)
- Reference Ardross Castle, Scottish Highlands setting where appropriate
- Avoid real-world social media platforms (use "ScotNet" instead of Facebook/Twitter/Instagram)
- Maintain cultural authenticity to UK context, especially {skeleton['demographics_template']['location']}
- Cite all sources for demographic claims
- Provide NON-STEREOTYPICAL details - focus on realistic variance within demographic

**Output Format:**
Structured report with clear sections, citations, and specific examples. Focus on authentic, grounded details that could inform an AI agent's behavior in a social deduction game."""

    # Create interaction with Deep Research agent
    try:
        interaction = client.interactions.create(
            agent="deep-research-pro-preview-12-2025",  # Correct Deep Research agent ID
            input=prompt,
            background=True,  # Required for Deep Research (exceeds timeout limits)
            store=True,  # Required for background jobs
            # Note: system_instruction not supported for Deep Research - instructions included in prompt
        )

        return interaction.id

    except Exception as e:
        print(f"Error submitting job for {skeleton['skeleton_id']}: {e}")
        raise


async def batch_process_skeletons(
    skeleton_file: str,
    world_bible_path: str,
    output_dir: str,
    batch_name: str,
    rate_limit_delay: int = 6
):
    """Process skeleton batch with rate limiting.

    Args:
        skeleton_file: Path to skeleton JSON file
        world_bible_path: Path to WORLD_BIBLE.md
        output_dir: Output directory for job tracker
        batch_name: Batch identifier
        rate_limit_delay: Seconds between job submissions (default: 6 = 10/min)
    """
    # Initialize Gemini client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Load skeletons
    print(f"Loading skeletons from: {skeleton_file}")
    with open(skeleton_file) as f:
        skeletons = json.load(f)

    print(f"Loaded {len(skeletons)} skeletons")
    print()

    # Submit jobs with rate limiting
    job_records = []
    total = len(skeletons)

    print(f"Submitting {total} Deep Research jobs...")
    print(f"Rate limit: {rate_limit_delay}s delay between submissions (10 jobs/min)")
    print("Note: World Bible constraints will be applied during synthesis phase with Claude")
    print()

    start_time = time.time()

    for i, skeleton in enumerate(skeletons, 1):
        print(f"[{i:02d}/{total}] {skeleton['archetype_name']:30s} | {skeleton['demographics_template']['occupation']:25s}...", end=" ")

        try:
            job_id = await submit_deep_research_job(
                client,
                skeleton
            )

            job_records.append({
                "skeleton_id": skeleton["skeleton_id"],
                "archetype": skeleton["archetype"],
                "archetype_name": skeleton["archetype_name"],
                "demographics": skeleton["demographics_template"],
                "interaction_id": job_id,
                "submitted_at": time.time()
            })

            print(f"✓ Job ID: {job_id}")

        except Exception as e:
            print(f"✗ FAILED: {e}")
            job_records.append({
                "skeleton_id": skeleton["skeleton_id"],
                "error": str(e),
                "interaction_id": None
            })

        # Rate limiting
        if i < total:
            await asyncio.sleep(rate_limit_delay)

    elapsed = time.time() - start_time

    # Save job tracker
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / f"{batch_name}_jobs.json"

    with open(output_file, "w") as f:
        json.dump(job_records, f, indent=2)

    print()
    print("=" * 70)
    print(f"✓ Submitted {len([j for j in job_records if j.get('interaction_id')])} jobs successfully")
    failed = len([j for j in job_records if not j.get('interaction_id')])
    if failed > 0:
        print(f"✗ {failed} jobs failed")
    print(f"  Elapsed time: {elapsed:.1f}s")
    print(f"  Job tracker saved to: {output_file}")
    print()
    print("Estimated completion time: 10-20 minutes")
    print()
    print("Next step: Poll jobs for completion")
    print(f"  python scripts/poll_research_jobs.py --input {output_file}")
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Submit Deep Research batch jobs")
    parser.add_argument("--input", type=str, default="data/personas/skeletons/test_batch_001.json", help="Skeleton JSON file")
    parser.add_argument("--world-bible", type=str, default="WORLD_BIBLE.md", help="World Bible path")
    parser.add_argument("--output", type=str, default="data/personas/jobs", help="Output directory for job tracker")
    parser.add_argument("--batch-name", type=str, default="test_batch_001", help="Batch name")
    parser.add_argument("--rate-limit", type=int, default=6, help="Seconds between submissions (default: 6)")

    args = parser.parse_args()

    # Validate input
    if not Path(args.input).exists():
        print(f"Error: Skeleton file not found: {args.input}")
        sys.exit(1)

    if not Path(args.world_bible).exists():
        print(f"Error: World Bible not found: {args.world_bible}")
        sys.exit(1)

    # Run batch processor
    asyncio.run(batch_process_skeletons(
        skeleton_file=args.input,
        world_bible_path=args.world_bible,
        output_dir=args.output,
        batch_name=args.batch_name,
        rate_limit_delay=args.rate_limit
    ))


if __name__ == "__main__":
    main()
