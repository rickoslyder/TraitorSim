#!/usr/bin/env python3
"""Poll Deep Research jobs and retrieve completed reports.

Polls Gemini Interactions API every 30 seconds until all jobs complete.

Usage:
    python scripts/poll_research_jobs.py
    python scripts/poll_research_jobs.py --input data/personas/jobs/test_batch_001_jobs.json
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


async def poll_job_status(
    client: genai.Client,
    interaction_id: str
) -> tuple[str, str]:
    """Poll job status and return report if complete.

    Args:
        client: Gemini client
        interaction_id: Interaction ID from job submission

    Returns:
        Tuple of (status, report_text or None)
        status: "completed", "processing", "failed"
    """
    try:
        interaction = client.interactions.get(interaction_id)

        if hasattr(interaction, 'status'):
            status = interaction.status

            if status == "completed":
                # Extract research report from outputs
                if interaction.outputs and len(interaction.outputs) > 0:
                    report_text = interaction.outputs[-1].text
                    return ("completed", report_text)
                else:
                    return ("completed", None)  # Completed but no output

            elif status in ["processing", "pending", "in_progress"]:
                return ("processing", None)

            else:
                return ("failed", None)
        else:
            # Older API - try to extract text directly
            if hasattr(interaction, 'outputs') and interaction.outputs:
                return ("completed", interaction.outputs[-1].text)
            return ("processing", None)

    except Exception as e:
        return ("failed", f"Error: {e}")


def get_client_for_key_index(key_index: int) -> genai.Client:
    """Get Gemini client for a specific API key index.

    Args:
        key_index: Key index (2-6 for rotation keys, None for main)

    Returns:
        Gemini client configured with the appropriate key
    """
    if key_index and key_index >= 2:
        key = os.getenv(f"GEMINI_API_KEY_{key_index}")
    else:
        key = os.getenv("GEMINI_API_KEY")

    if not key:
        raise ValueError(f"API key not found for index {key_index}")

    return genai.Client(api_key=key)


async def poll_batch(
    job_file: str,
    output_dir: str,
    batch_name: str,
    poll_interval: int = 30,
    timeout_minutes: int = 30
):
    """Poll all jobs in batch until complete.

    Args:
        job_file: Path to job tracker JSON
        output_dir: Output directory for reports
        batch_name: Batch identifier
        poll_interval: Seconds between polling (default: 30)
        timeout_minutes: Maximum wait time (default: 30)
    """
    # Build client cache for each API key used
    clients = {}

    def get_client(key_index):
        if key_index not in clients:
            clients[key_index] = get_client_for_key_index(key_index)
        return clients[key_index]

    # Verify at least main key exists
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    # Default client for jobs without key_index
    default_client = genai.Client(api_key=api_key)

    # Load jobs
    print(f"Loading jobs from: {job_file}")
    with open(job_file) as f:
        jobs = json.load(f)

    # Filter out failed submissions
    valid_jobs = [j for j in jobs if j.get('interaction_id')]
    total = len(valid_jobs)

    if total == 0:
        print("Error: No valid jobs to poll")
        sys.exit(1)

    print(f"Polling {total} jobs...")
    print(f"Poll interval: {poll_interval}s")
    print(f"Timeout: {timeout_minutes} minutes")
    print()

    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    completed = 0
    failed = 0
    processing = total

    while completed < total:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print()
            print(f"⏱  Timeout reached ({timeout_minutes} min)")
            print(f"   Completed: {completed}/{total}")
            print(f"   Still processing: {processing}")
            break

        # Poll all incomplete jobs
        print(f"[{int(elapsed//60):02d}:{int(elapsed%60):02d}] Polling... ", end="")

        newly_completed = 0
        newly_failed = 0

        for job in valid_jobs:
            # Skip if already has report or error
            if "report" in job or "poll_error" in job:
                continue

            interaction_id = job["interaction_id"]

            # Use the same API key that submitted this job
            key_index = job.get("api_key_index")
            try:
                client = get_client(key_index) if key_index else default_client
            except ValueError:
                client = default_client

            status, report = await poll_job_status(client, interaction_id)

            if status == "completed":
                if report:
                    job["report"] = report
                    job["completed_at"] = time.time()
                    newly_completed += 1
                else:
                    job["poll_error"] = "Completed but no output"
                    newly_failed += 1

            elif status == "failed":
                job["poll_error"] = report or "Job failed"
                newly_failed += 1

        completed += newly_completed
        failed += newly_failed
        processing = total - completed - failed

        print(f"Completed: {completed:2d}/{total} | Processing: {processing:2d} | Failed: {failed:2d}")

        # Save progress
        with open(job_file, "w") as f:
            json.dump(jobs, f, indent=2)

        if completed + failed >= total:
            break

        # Wait before next poll
        await asyncio.sleep(poll_interval)

    elapsed = time.time() - start_time

    # Extract reports and save
    print()
    print("=" * 70)
    print("Polling complete!")
    print(f"  Elapsed time: {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f"  Completed: {completed}/{total}")
    if failed > 0:
        print(f"  Failed: {failed}")
    print()

    # Save reports to separate file
    reports = []
    for job in valid_jobs:
        if "report" in job:
            reports.append({
                "skeleton_id": job["skeleton_id"],
                "archetype": job["archetype"],
                "archetype_name": job["archetype_name"],
                "demographics": job["demographics"],
                "report": job["report"]
            })

    if reports:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        output_file = output_path / f"{batch_name}_reports.json"

        with open(output_file, "w") as f:
            json.dump(reports, f, indent=2)

        print(f"✓ Saved {len(reports)} reports to: {output_file}")
        print()
        print("Next step: Synthesize backstories")
        print(f"  python scripts/synthesize_backstories.py --reports {output_file}")
    else:
        print("✗ No completed reports to save")

    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Poll Deep Research jobs")
    parser.add_argument("--input", type=str, default="data/personas/jobs/test_batch_001_jobs.json", help="Job tracker JSON file")
    parser.add_argument("--output", type=str, default="data/personas/reports", help="Output directory for reports")
    parser.add_argument("--batch-name", type=str, default="test_batch_001", help="Batch name")
    parser.add_argument("--poll-interval", type=int, default=30, help="Seconds between polls (default: 30)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in minutes (default: 30)")

    args = parser.parse_args()

    # Validate input
    if not Path(args.input).exists():
        print(f"Error: Job file not found: {args.input}")
        sys.exit(1)

    # Run poller
    asyncio.run(poll_batch(
        job_file=args.input,
        output_dir=args.output,
        batch_name=args.batch_name,
        poll_interval=args.poll_interval,
        timeout_minutes=args.timeout
    ))


if __name__ == "__main__":
    main()
