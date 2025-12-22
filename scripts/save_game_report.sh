#!/bin/bash
# Generate HTML report from the latest TraitorSim game
#
# Usage:
#   ./scripts/save_game_report.sh              # Auto-names based on timestamp
#   ./scripts/save_game_report.sh my_game      # Custom name -> reports/my_game.html
#   ./scripts/save_game_report.sh --json       # Also generate JSON data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$PROJECT_DIR/reports"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Parse arguments
REPORT_NAME=""
JSON_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_FLAG="--json"
            shift
            ;;
        *)
            REPORT_NAME="$1"
            shift
            ;;
    esac
done

# Generate default name if not provided
if [ -z "$REPORT_NAME" ]; then
    REPORT_NAME="game_$(date +%Y%m%d_%H%M%S)"
fi

OUTPUT_FILE="$REPORTS_DIR/${REPORT_NAME}.html"

echo "Generating TraitorSim report..."
echo "Output: $OUTPUT_FILE"

# Check if orchestrator container exists
if ! docker ps -a --format "{{.Names}}" | grep -q "traitorsim-orchestrator"; then
    echo "Error: traitorsim-orchestrator container not found"
    echo "Run a game first with: ./run.sh"
    exit 1
fi

# Generate report from Docker logs
docker logs traitorsim-orchestrator 2>&1 | python3 "$SCRIPT_DIR/generate_html_report.py" \
    --output "$OUTPUT_FILE" $JSON_FLAG

echo ""
echo "Report saved!"
echo "Open in browser: file://$OUTPUT_FILE"

# If on a server, suggest a way to view
if [ -n "$SSH_CONNECTION" ]; then
    echo ""
    echo "On remote server? Copy to local machine with:"
    echo "  scp $(hostname):$OUTPUT_FILE ."
fi
