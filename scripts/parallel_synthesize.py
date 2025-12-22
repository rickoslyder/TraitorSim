#!/usr/bin/env python3
"""Parallel backstory synthesis using subprocess workers.

Splits reports into chunks and runs synthesis in parallel subprocesses
to work around Claude Agent SDK's async limitations.

Usage:
    python scripts/parallel_synthesize.py --reports data/personas/reports/batch_85_wave2_reports.json --workers 4
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


def run_synthesis_worker(args_tuple):
    """Run synthesis for a single chunk in subprocess."""
    chunk_idx, chunk_file, output_file, model, oauth_token = args_tuple

    env = os.environ.copy()
    env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token

    cmd = [
        sys.executable,
        "scripts/synthesize_backstories.py",
        "--reports", chunk_file,
        "--output", str(Path(output_file).parent),
        "--batch-name", f"chunk_{chunk_idx:02d}",
        "--model", model
    ]

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    return {
        "chunk_idx": chunk_idx,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output_file": output_file
    }


def main():
    parser = argparse.ArgumentParser(description="Parallel backstory synthesis")
    parser.add_argument("--reports", type=str, required=True, help="Reports JSON file")
    parser.add_argument("--output", type=str, default="data/personas/library", help="Output directory")
    parser.add_argument("--batch-name", type=str, default="parallel_batch", help="Batch name")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--chunk-size", type=int, default=6, help="Personas per chunk")
    parser.add_argument("--model", type=str, default="claude-opus-4-5-20251101", help="Claude model")

    args = parser.parse_args()

    # Verify OAuth token
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if not oauth_token:
        print("Error: CLAUDE_CODE_OAUTH_TOKEN not set")
        sys.exit(1)

    # Load reports
    print(f"Loading reports from: {args.reports}")
    with open(args.reports) as f:
        reports = json.load(f)

    total = len(reports)
    num_chunks = (total + args.chunk_size - 1) // args.chunk_size

    print(f"Loaded {total} reports")
    print(f"Splitting into {num_chunks} chunks of ~{args.chunk_size} each")
    print(f"Running with {args.workers} parallel workers")
    print()

    # Create temp directory for chunks
    temp_dir = tempfile.mkdtemp(prefix="synthesis_")
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Split into chunk files
    chunk_args = []
    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * args.chunk_size
        end_idx = min(start_idx + args.chunk_size, total)
        chunk_reports = reports[start_idx:end_idx]

        chunk_file = f"{temp_dir}/chunk_{chunk_idx:02d}.json"
        with open(chunk_file, "w") as f:
            json.dump(chunk_reports, f)

        output_file = output_dir / f"chunk_{chunk_idx:02d}_personas.json"

        print(f"  Chunk {chunk_idx + 1}: {len(chunk_reports)} personas -> {output_file.name}")

        chunk_args.append((chunk_idx, chunk_file, str(output_file), args.model, oauth_token))

    print()
    print(f"Launching {min(args.workers, num_chunks)} parallel workers...")
    print()

    # Run in parallel
    all_personas = []
    failed_chunks = []

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_synthesis_worker, arg): arg[0] for arg in chunk_args}

        for future in as_completed(futures):
            chunk_idx = futures[future]
            try:
                result = future.result()

                if result["returncode"] == 0:
                    # Load generated personas
                    output_file = result["output_file"]
                    if Path(output_file).exists():
                        with open(output_file) as f:
                            personas = json.load(f)
                        all_personas.extend(personas)
                        print(f"  ✓ Chunk {chunk_idx + 1} complete: {len(personas)} personas")
                    else:
                        print(f"  ✗ Chunk {chunk_idx + 1}: output file not found")
                        failed_chunks.append(chunk_idx)
                else:
                    print(f"  ✗ Chunk {chunk_idx + 1} failed (exit {result['returncode']})")
                    if result["stderr"]:
                        print(f"    {result['stderr'][:200]}")
                    failed_chunks.append(chunk_idx)

            except Exception as e:
                print(f"  ✗ Chunk {chunk_idx + 1} exception: {e}")
                failed_chunks.append(chunk_idx)

    print()
    print("=" * 70)
    print(f"✓ Synthesized {len(all_personas)}/{total} personas")
    if failed_chunks:
        print(f"✗ Failed chunks: {failed_chunks}")
    print()

    # Save combined output
    if all_personas:
        combined_file = output_dir / f"{args.batch_name}_personas.json"
        with open(combined_file, "w") as f:
            json.dump(all_personas, f, indent=2)
        print(f"✓ Saved {len(all_personas)} personas to: {combined_file}")

    # Cleanup temp files
    for arg in chunk_args:
        Path(arg[1]).unlink(missing_ok=True)
    Path(temp_dir).rmdir()

    print("=" * 70)


if __name__ == "__main__":
    main()
