#!/usr/bin/env python3
"""Submit Deep Research jobs for persona backstory generation.

Uses Gemini Interactions API with:
- File Search grounding (World Bible)
- Background jobs (5-15 min per persona)
- Batch processing with rate limiting
- API key rotation to maximize throughput

Usage:
    python scripts/batch_deep_research.py
    python scripts/batch_deep_research.py --input data/personas/skeletons/batch_85.json
    python scripts/batch_deep_research.py --input skeletons.json --rotate-keys
"""

import argparse
import json
import os
import sys
import asyncio
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from google import genai
except ImportError:
    print("Error: google-genai package not installed")
    print("Install with: pip install google-genai")
    sys.exit(1)


@dataclass
class APIKeyManager:
    """Manages rotation of multiple Gemini API keys for Deep Research.

    Uses keys 2, 3, 4 for research (preserving main key for game/sim).
    Tracks usage per key and implements basic quota management.
    """
    keys: List[str] = field(default_factory=list)
    usage_counts: dict = field(default_factory=dict)
    current_index: int = 0
    jobs_per_key_limit: int = 12  # Conservative limit per key per batch

    @classmethod
    def from_env(cls, use_rotation: bool = True) -> 'APIKeyManager':
        """Load API keys from environment.

        Args:
            use_rotation: If True, use keys 2,3,4. If False, use main key only.
        """
        if use_rotation:
            # Use keys 2-6 for research (preserve main key for game/sim)
            keys = []
            for key_num in [2, 3, 4, 5, 6]:
                key = os.getenv(f"GEMINI_API_KEY_{key_num}")
                if key:
                    keys.append(key)
                    print(f"✓ Loaded GEMINI_API_KEY_{key_num}")

            if not keys:
                print("Warning: No rotation keys found, falling back to main key")
                main_key = os.getenv("GEMINI_API_KEY")
                if main_key:
                    keys = [main_key]
        else:
            main_key = os.getenv("GEMINI_API_KEY")
            keys = [main_key] if main_key else []

        if not keys:
            print("Error: No Gemini API keys found in environment")
            sys.exit(1)

        usage_counts = {k: 0 for k in keys}
        return cls(keys=keys, usage_counts=usage_counts)

    def get_next_key(self) -> str:
        """Get next API key using round-robin rotation."""
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key

    def get_key_with_capacity(self) -> Optional[str]:
        """Get a key that hasn't exceeded its limit."""
        for _ in range(len(self.keys)):
            key = self.get_next_key()
            if self.usage_counts[key] < self.jobs_per_key_limit:
                return key
        return None  # All keys at capacity

    def record_usage(self, key: str):
        """Record that a job was submitted with this key."""
        self.usage_counts[key] = self.usage_counts.get(key, 0) + 1

    def get_client(self, key: str) -> genai.Client:
        """Create a Gemini client for the given key."""
        return genai.Client(api_key=key)

    def get_capacity_remaining(self) -> int:
        """Get total remaining capacity across all keys."""
        return sum(
            max(0, self.jobs_per_key_limit - count)
            for count in self.usage_counts.values()
        )

    def get_status(self) -> str:
        """Get human-readable status of key usage."""
        lines = ["API Key Usage:"]
        for i, key in enumerate(self.keys):
            count = self.usage_counts[key]
            remaining = self.jobs_per_key_limit - count
            key_id = f"KEY_{i+2}" if len(self.keys) > 1 else "MAIN"
            lines.append(f"  {key_id}: {count}/{self.jobs_per_key_limit} used, {remaining} remaining")
        return "\n".join(lines)


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
    rate_limit_delay: int = 6,
    use_key_rotation: bool = True,
    max_jobs: int = 0  # 0 = no limit
):
    """Process skeleton batch with rate limiting and key rotation.

    Args:
        skeleton_file: Path to skeleton JSON file
        world_bible_path: Path to WORLD_BIBLE.md
        output_dir: Output directory for job tracker
        batch_name: Batch identifier
        rate_limit_delay: Seconds between job submissions (default: 6 = 10/min)
        use_key_rotation: Use keys 2,3,4 for rotation (preserve main key)
        max_jobs: Maximum jobs to submit (0 = all)
    """
    # Initialize API Key Manager
    print("=" * 70)
    print("TraitorSim Deep Research Batch Processor")
    print("=" * 70)
    print()

    key_manager = APIKeyManager.from_env(use_rotation=use_key_rotation)
    print(f"Loaded {len(key_manager.keys)} API key(s) for rotation")
    print(f"Capacity per batch: ~{key_manager.jobs_per_key_limit * len(key_manager.keys)} jobs")
    print()

    # Load skeletons
    print(f"Loading skeletons from: {skeleton_file}")
    with open(skeleton_file) as f:
        skeletons = json.load(f)

    total_available = len(skeletons)
    print(f"Loaded {total_available} skeletons")

    # Apply max_jobs limit
    if max_jobs > 0 and max_jobs < total_available:
        skeletons = skeletons[:max_jobs]
        print(f"Limiting to first {max_jobs} skeletons (--max-jobs)")

    total = len(skeletons)

    # Check capacity
    capacity = key_manager.get_capacity_remaining()
    if total > capacity:
        print(f"\n⚠️  Warning: {total} jobs requested but only {capacity} capacity available")
        print(f"   Will submit first {capacity} jobs. Re-run later for remaining.")
        skeletons = skeletons[:capacity]
        total = len(skeletons)

    print()
    print(f"Submitting {total} Deep Research jobs...")
    print(f"Rate limit: {rate_limit_delay}s delay between submissions")
    print("API keys will rotate to distribute load")
    print()

    # Submit jobs with rate limiting and key rotation
    job_records = []
    start_time = time.time()

    for i, skeleton in enumerate(skeletons, 1):
        # Get next key with capacity
        api_key = key_manager.get_key_with_capacity()
        if not api_key:
            print(f"\n⚠️  All API keys at capacity limit. Stopping at {i-1} jobs.")
            break

        client = key_manager.get_client(api_key)
        key_index = key_manager.keys.index(api_key) + 2  # Keys are 2, 3, 4

        print(f"[{i:02d}/{total}] KEY_{key_index} | {skeleton['archetype_name']:25s} | {skeleton['demographics_template']['occupation'][:20]:20s}...", end=" ")

        try:
            job_id = await submit_deep_research_job(
                client,
                skeleton
            )

            key_manager.record_usage(api_key)

            job_records.append({
                "skeleton_id": skeleton["skeleton_id"],
                "archetype": skeleton["archetype"],
                "archetype_name": skeleton["archetype_name"],
                "demographics": skeleton["demographics_template"],
                "interaction_id": job_id,
                "api_key_index": key_index,
                "submitted_at": time.time()
            })

            print(f"✓ {job_id[:30]}...")

        except Exception as e:
            error_msg = str(e)
            print(f"✗ FAILED: {error_msg[:50]}")

            # Check for quota errors
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                print(f"   → Quota limit hit on KEY_{key_index}, will skip this key")
                key_manager.usage_counts[api_key] = key_manager.jobs_per_key_limit  # Mark as exhausted

            job_records.append({
                "skeleton_id": skeleton["skeleton_id"],
                "archetype": skeleton["archetype"],
                "error": error_msg,
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

    # Summary
    successful = len([j for j in job_records if j.get('interaction_id')])
    failed = len([j for j in job_records if not j.get('interaction_id')])

    print()
    print("=" * 70)
    print("BATCH SUBMISSION COMPLETE")
    print("=" * 70)
    print()
    print(key_manager.get_status())
    print()
    print(f"Results:")
    print(f"  ✓ Submitted: {successful} jobs")
    if failed > 0:
        print(f"  ✗ Failed: {failed} jobs")
    print(f"  ⏱  Elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  📁 Job tracker: {output_file}")
    print()
    print("Estimated completion time: 10-20 minutes per job")
    print()
    print("Next step: Poll jobs for completion")
    print(f"  python scripts/poll_research_jobs.py --input {output_file}")
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Submit Deep Research batch jobs with API key rotation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Submit all skeletons with key rotation (default)
  python scripts/batch_deep_research.py --input data/personas/skeletons/batch_85.json

  # Submit only first 36 jobs (one wave)
  python scripts/batch_deep_research.py --input skeletons.json --max-jobs 36

  # Use only main key (no rotation)
  python scripts/batch_deep_research.py --input skeletons.json --no-rotate
        """
    )
    parser.add_argument("--input", type=str, default="data/personas/skeletons/batch_85.json", help="Skeleton JSON file")
    parser.add_argument("--world-bible", type=str, default="WORLD_BIBLE.md", help="World Bible path")
    parser.add_argument("--output", type=str, default="data/personas/jobs", help="Output directory for job tracker")
    parser.add_argument("--batch-name", type=str, default="batch_85", help="Batch name")
    parser.add_argument("--rate-limit", type=int, default=6, help="Seconds between submissions (default: 6)")
    parser.add_argument("--rotate-keys", action="store_true", default=True, help="Use API keys 2,3,4 for rotation (default)")
    parser.add_argument("--no-rotate", action="store_true", help="Use only main API key (no rotation)")
    parser.add_argument("--max-jobs", type=int, default=0, help="Maximum jobs to submit (0 = all)")

    args = parser.parse_args()

    # Validate input
    if not Path(args.input).exists():
        print(f"Error: Skeleton file not found: {args.input}")
        sys.exit(1)

    if not Path(args.world_bible).exists():
        print(f"Error: World Bible not found: {args.world_bible}")
        sys.exit(1)

    # Determine rotation mode
    use_rotation = not args.no_rotate

    # Run batch processor
    asyncio.run(batch_process_skeletons(
        skeleton_file=args.input,
        world_bible_path=args.world_bible,
        output_dir=args.output,
        batch_name=args.batch_name,
        rate_limit_delay=args.rate_limit,
        use_key_rotation=use_rotation,
        max_jobs=args.max_jobs
    ))


if __name__ == "__main__":
    main()
