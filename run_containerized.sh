#!/bin/bash
# Helper script to run TraitorSim with containerized agents

set -e

echo "=========================================="
echo "TraitorSim - Containerized Architecture"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Create .env with CLAUDE_CODE_OAUTH_TOKEN and GEMINI_API_KEY"
    echo ""
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker and try again"
    exit 1
fi

echo "📦 Building agent containers..."
docker-compose build

echo ""
echo "🚀 Starting 10 agent containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for agents to become healthy..."
sleep 10

# Check agent health
echo ""
echo "🏥 Health check:"
for i in {0..9}; do
    port=$((8000 + i))
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "  ✅ Agent $i (port $port): healthy"
    else
        echo "  ❌ Agent $i (port $port): not ready"
    fi
done

echo ""
echo "🎮 Starting game engine..."
echo "=========================================="
echo ""

# Run the containerized game engine
python3 -m src.traitorsim.__main_containerized__

echo ""
echo "🧹 Cleaning up containers..."
docker-compose down

echo ""
echo "✅ Done!"
