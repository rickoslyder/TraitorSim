#!/usr/bin/env python3
"""Batch convert all game logs to JSON reports for UI import.

Usage:
    python scripts/batch_convert_logs.py
"""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generate_html_report import LogParser, generate_html
from dataclasses import asdict
import json


def convert_log_to_reports(log_path: Path, output_dir: Path) -> bool:
    """Convert a single log file to HTML and JSON reports."""
    try:
        # Read log file
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_text = f.read()

        if not log_text.strip():
            print(f"  Skipping empty file: {log_path.name}")
            return False

        # Parse the log
        parser = LogParser()
        report = parser.parse(log_text)

        # Skip if no meaningful data
        if report.total_days == 0 and not report.winner:
            print(f"  Skipping incomplete game: {log_path.name}")
            return False

        # Generate output filenames
        base_name = log_path.stem
        html_path = output_dir / f"{base_name}.html"
        json_path = output_dir / f"{base_name}.json"

        # Generate HTML
        html = generate_html(report)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        # Generate JSON
        data = {
            'total_days': report.total_days,
            'prize_pot': report.prize_pot,
            'winner': report.winner,
            'traitors': report.traitors,
            'faithfuls': report.faithfuls,
            'players': {name: asdict(p) for name, p in report.players.items()},
            'events': [
                {
                    'day': e.day,
                    'phase': e.phase,
                    'type': e.event_type.value,
                    'content': e.content,
                    'players': e.players_involved,
                    'metadata': e.metadata
                }
                for e in report.events
            ]
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"  Converted: {log_path.name}")
        print(f"    Days: {report.total_days}, Winner: {report.winner or 'Unknown'}, Players: {len(report.players)}")
        return True

    except Exception as e:
        print(f"  Error converting {log_path.name}: {e}")
        return False


def main():
    # Paths
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / "data" / "games"
    output_dir = project_root / "reports"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all log files
    log_files = sorted(logs_dir.glob("game_*.log"))

    if not log_files:
        print(f"No log files found in {logs_dir}")
        return

    print(f"Found {len(log_files)} log files in {logs_dir}")
    print(f"Output directory: {output_dir}\n")

    # Convert each log
    converted = 0
    skipped = 0
    failed = 0

    for log_path in log_files:
        # Check if JSON already exists
        json_path = output_dir / f"{log_path.stem}.json"
        if json_path.exists():
            print(f"  Already exists: {log_path.name}")
            skipped += 1
            continue

        if convert_log_to_reports(log_path, output_dir):
            converted += 1
        else:
            failed += 1

    print(f"\nConversion complete:")
    print(f"  Converted: {converted}")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  Failed/Incomplete: {failed}")
    print(f"  Total: {len(log_files)}")


if __name__ == '__main__':
    main()
