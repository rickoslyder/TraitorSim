#!/bin/bash
# Run TraitorSim using Docker-in-Docker orchestrator
# This isolates all agent containers inside a single orchestrator container

set -e

echo "==========================================="
echo "TraitorSim - Docker-in-Docker Mode"
echo "==========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Create .env with CLAUDE_CODE_OAUTH_TOKEN and GEMINI_API_KEY"
    echo ""
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker and try again"
    exit 1
fi

echo "📦 Building orchestrator container..."
docker compose -f docker-compose.orchestrator.yml build

echo ""
echo "🚀 Starting orchestrator (this will run the entire game inside)..."
echo "   - Orchestrator will start Docker daemon"
echo "   - Build 10 agent containers internally"
echo "   - Run the game engine"
echo "   - Clean up when done"
echo ""
echo "==========================================="
echo ""

# Run orchestrator (will stream logs)
docker compose -f docker-compose.orchestrator.yml up --abort-on-container-exit

# Capture exit code
EXIT_CODE=$?

echo ""
echo "🧹 Removing orchestrator container..."
docker compose -f docker-compose.orchestrator.yml down -v

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Complete! Check data/games/ for game logs."
else
    echo "❌ Orchestrator exited with error code: $EXIT_CODE"
fi

exit $EXIT_CODE
