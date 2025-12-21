#!/bin/bash
# Master script for offline persona generation pipeline
#
# This script orchestrates the complete Deep Research pipeline:
# 1. Generate skeleton personas
# 2. Submit Deep Research jobs
# 3. Poll for completion
# 4. Synthesize backstories
# 5. Validate library
#
# Usage:
#   ./scripts/generate_persona_library.sh
#   ./scripts/generate_persona_library.sh --count 20

set -e  # Exit on error

# Load .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Default parameters
COUNT=15
BATCH_NAME="test_batch_001"
MAX_PER_ARCHETYPE=2

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --count)
            COUNT="$2"
            shift 2
            ;;
        --batch-name)
            BATCH_NAME="$2"
            shift 2
            ;;
        --max-per-archetype)
            MAX_PER_ARCHETYPE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--count N] [--batch-name NAME] [--max-per-archetype N]"
            exit 1
            ;;
    esac
done

echo "==========================================="
echo "TraitorSim Persona Library Generation"
echo "==========================================="
echo ""
echo "Parameters:"
echo "  Count: $COUNT personas"
echo "  Batch: $BATCH_NAME"
echo "  Max per archetype: $MAX_PER_ARCHETYPE"
echo ""
echo "Estimated time: 30-60 minutes"
echo "Estimated cost: \$6-10 for $COUNT personas (Deep Research + Claude)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi
echo ""

# Check environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY environment variable not set"
    echo "Set GEMINI_API_KEY in .env file"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo "Error: Neither ANTHROPIC_API_KEY nor CLAUDE_CODE_OAUTH_TOKEN set"
    echo "Set one of these in .env file for Claude API access"
    exit 1
fi

if [ ! -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo "✅ Using Claude subscription via CLAUDE_CODE_OAUTH_TOKEN"
else
    echo "✅ Using Claude API via ANTHROPIC_API_KEY"
fi

# Check World Bible exists
if [ ! -f "WORLD_BIBLE.md" ]; then
    echo "Error: WORLD_BIBLE.md not found in project root"
    exit 1
fi

echo "==========================================="
echo "[1/5] Generating skeleton personas..."
echo "==========================================="
python3 scripts/generate_skeleton_personas.py \
    --count $COUNT \
    --max-per-archetype $MAX_PER_ARCHETYPE \
    --batch-name $BATCH_NAME

if [ $? -ne 0 ]; then
    echo "Error: Skeleton generation failed"
    exit 1
fi

echo ""
echo "==========================================="
echo "[2/5] Submitting Deep Research jobs..."
echo "==========================================="
echo "This will take a few minutes to submit all jobs."
echo ""
python3 scripts/batch_deep_research.py \
    --input "data/personas/skeletons/${BATCH_NAME}.json" \
    --batch-name $BATCH_NAME

if [ $? -ne 0 ]; then
    echo "Error: Deep Research submission failed"
    exit 1
fi

echo ""
echo "==========================================="
echo "[3/5] Polling for job completion..."
echo "==========================================="
echo "This will take 10-20 minutes. Polling every 30 seconds."
echo ""
python3 scripts/poll_research_jobs.py \
    --input "data/personas/jobs/${BATCH_NAME}_jobs.json" \
    --batch-name $BATCH_NAME \
    --timeout 30

if [ $? -ne 0 ]; then
    echo "Error: Polling failed or timed out"
    exit 1
fi

echo ""
echo "==========================================="
echo "[4/5] Synthesizing backstories with Claude..."
echo "==========================================="
python3 scripts/synthesize_backstories.py \
    --reports "data/personas/reports/${BATCH_NAME}_reports.json" \
    --batch-name $BATCH_NAME

if [ $? -ne 0 ]; then
    echo "Error: Backstory synthesis failed"
    exit 1
fi

echo ""
echo "==========================================="
echo "[5/5] Validating persona library..."
echo "==========================================="
python3 scripts/validate_personas.py \
    --input "data/personas/library/${BATCH_NAME}_personas.json"

if [ $? -ne 0 ]; then
    echo "Error: Validation failed"
    exit 1
fi

echo ""
echo "==========================================="
echo "✓ Generation Complete!"
echo "==========================================="
echo ""
echo "Persona library ready at:"
echo "  data/personas/library/${BATCH_NAME}_personas.json"
echo ""
echo "Generated:"
echo "  - $COUNT personas"
echo "  - $(ls -lh data/personas/library/${BATCH_NAME}_personas.json | awk '{print $5}') persona library"
echo ""
echo "To use in game:"
echo "  1. Set config.personality_generation = 'archetype'"
echo "  2. Set config.persona_library_path = 'data/personas/library'"
echo "  3. Run game normally"
echo ""
echo "To generate more personas:"
echo "  ./scripts/generate_persona_library.sh --count 50 --batch-name batch_002"
echo "==========================================="
