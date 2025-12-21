#!/bin/bash
# Entrypoint for Docker-in-Docker orchestrator
# Starts Docker daemon, builds agent containers, and runs the game

set -e

echo "==========================================="
echo "TraitorSim Docker-in-Docker Orchestrator"
echo "==========================================="
echo ""

# Start Docker daemon in background
echo "🐳 Starting Docker daemon..."
dockerd-entrypoint.sh &
DOCKER_PID=$!

# Wait for Docker daemon to be ready
echo "⏳ Waiting for Docker daemon to be ready..."
timeout=30
while ! docker info >/dev/null 2>&1; do
    if [ $timeout -le 0 ]; then
        echo "❌ Docker daemon failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
    timeout=$((timeout - 1))
done

echo "✅ Docker daemon ready"
echo ""

# Build agent images inside the orchestrator
echo "🔨 Building agent container images..."
docker compose -f /app/docker-compose.yml build

echo ""
echo "🚀 Starting 24 agent containers (in batches to avoid resource spikes)..."

# Start in batches of 5 to avoid overwhelming the system
echo "  📦 Batch 1: Starting agents 0-4..."
docker compose -f /app/docker-compose.yml up -d agent-0 agent-1 agent-2 agent-3 agent-4
sleep 5

echo "  📦 Batch 2: Starting agents 5-9..."
docker compose -f /app/docker-compose.yml up -d agent-5 agent-6 agent-7 agent-8 agent-9
sleep 5

echo "  📦 Batch 3: Starting agents 10-14..."
docker compose -f /app/docker-compose.yml up -d agent-10 agent-11 agent-12 agent-13 agent-14
sleep 5

echo "  📦 Batch 4: Starting agents 15-19..."
docker compose -f /app/docker-compose.yml up -d agent-15 agent-16 agent-17 agent-18 agent-19
sleep 5

echo "  📦 Batch 5: Starting agents 20-23..."
docker compose -f /app/docker-compose.yml up -d agent-20 agent-21 agent-22 agent-23

echo ""
echo "⏳ Waiting for agents to become healthy..."
sleep 15

# Health check (using Docker service names)
echo ""
echo "🏥 Agent health check:"
for i in {0..23}; do
    agent_name="traitorsim-agent-$i"
    if curl -s http://$agent_name:5000/health >/dev/null 2>&1; then
        echo "  ✅ $agent_name: healthy"
    else
        echo "  ⚠️  $agent_name: not ready (will initialize during game)"
    fi
done

echo ""
echo "🎮 Starting TraitorSim game engine container..."
echo "==========================================="
echo ""

# Start game engine container (on same network as agents)
docker compose -f /app/docker-compose.yml up game-engine

# Capture exit code
GAME_EXIT_CODE=$?

echo ""
echo "🧹 Cleaning up agent containers..."
docker compose -f /app/docker-compose.yml down

echo ""
if [ $GAME_EXIT_CODE -eq 0 ]; then
    echo "✅ Game completed successfully!"
else
    echo "❌ Game exited with code: $GAME_EXIT_CODE"
fi

# Keep container alive if there was an error (for debugging)
if [ $GAME_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Container staying alive for debugging. Press Ctrl+C to exit."
    tail -f /dev/null
fi

exit $GAME_EXIT_CODE
