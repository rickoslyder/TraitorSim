"""Game runner API endpoints - Start and monitor games via WebSocket.

This module provides:
- POST /run - Start a new game simulation
- GET /run/status - Get status of running game
- POST /run/stop - Stop a running game
- WebSocket /run/ws - Real-time log streaming
"""

import asyncio
import json
import logging
import os
import subprocess
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class GameRun:
    """Represents a running game session."""
    id: str
    status: str  # 'starting', 'running', 'completed', 'failed', 'stopped'
    started_at: str
    ended_at: Optional[str] = None
    current_day: int = 0
    current_phase: str = ""
    alive_players: int = 0
    prize_pot: int = 0
    winner: Optional[str] = None
    error: Optional[str] = None
    log_lines: list = field(default_factory=list)


# Global state for current game run
_current_run: Optional[GameRun] = None
_process: Optional[subprocess.Popen] = None
_connected_websockets: list[WebSocket] = []


class RunGameRequest(BaseModel):
    """Request body for starting a new game."""
    num_players: int = 22
    num_traitors: int = 3
    rule_variant: str = "uk"


class RunStatusResponse(BaseModel):
    """Response for game run status."""
    running: bool
    game_id: Optional[str] = None
    status: Optional[str] = None
    current_day: int = 0
    current_phase: str = ""
    alive_players: int = 0
    prize_pot: int = 0
    winner: Optional[str] = None
    started_at: Optional[str] = None
    log_line_count: int = 0


@router.post("/run")
async def start_game(request: RunGameRequest):
    """Start a new game simulation.

    The game runs in the background. Use WebSocket /run/ws to stream logs
    or GET /run/status to poll for status.
    """
    global _current_run, _process

    # Check if a game is already running
    if _current_run and _current_run.status in ('starting', 'running'):
        raise HTTPException(
            status_code=409,
            detail="A game is already running. Stop it first or wait for completion."
        )

    # Create new game run
    game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    _current_run = GameRun(
        id=game_id,
        status="starting",
        started_at=datetime.now().isoformat()
    )

    # Start game in background
    asyncio.create_task(_run_game_async(request))

    logger.info(f"Starting game: {game_id}")

    return {
        "game_id": game_id,
        "status": "starting",
        "message": "Game starting. Connect to WebSocket /api/games/run/ws for live updates."
    }


@router.get("/run/status", response_model=RunStatusResponse)
async def get_run_status():
    """Get the status of the current or last game run."""
    if not _current_run:
        return RunStatusResponse(running=False)

    return RunStatusResponse(
        running=_current_run.status in ('starting', 'running'),
        game_id=_current_run.id,
        status=_current_run.status,
        current_day=_current_run.current_day,
        current_phase=_current_run.current_phase,
        alive_players=_current_run.alive_players,
        prize_pot=_current_run.prize_pot,
        winner=_current_run.winner,
        started_at=_current_run.started_at,
        log_line_count=len(_current_run.log_lines)
    )


@router.post("/run/stop")
async def stop_game():
    """Stop the currently running game."""
    global _current_run, _process

    if not _current_run or _current_run.status not in ('starting', 'running'):
        raise HTTPException(status_code=400, detail="No game is currently running")

    if _process:
        try:
            # Send SIGTERM to process group
            os.killpg(os.getpgid(_process.pid), signal.SIGTERM)
            _process = None
        except Exception as e:
            logger.error(f"Error stopping game: {e}")

    _current_run.status = "stopped"
    _current_run.ended_at = datetime.now().isoformat()

    await _broadcast_status()

    return {"status": "stopped", "game_id": _current_run.id}


@router.websocket("/run/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time game log streaming.

    Clients receive JSON messages with:
    - type: 'status' | 'log' | 'complete'
    - data: Relevant payload
    """
    await websocket.accept()
    _connected_websockets.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(_connected_websockets)}")

    try:
        # Send current status
        if _current_run:
            await websocket.send_json({
                "type": "status",
                "data": asdict(_current_run)
            })
            # Send existing log lines
            for line in _current_run.log_lines[-100:]:  # Last 100 lines
                await websocket.send_json({
                    "type": "log",
                    "data": {"line": line}
                })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in _connected_websockets:
            _connected_websockets.remove(websocket)


async def _run_game_async(request: RunGameRequest):
    """Run the game simulation in a subprocess."""
    global _current_run, _process

    try:
        # Build command - check for mounted project or local path
        project_root = None
        possible_paths = [
            Path("/app/traitorsim"),  # Docker mount
            Path("/home/rkb/projects/TraitorSim"),  # Local development
            Path.cwd().parent,  # Relative to UI
        ]

        for path in possible_paths:
            if (path / "src" / "traitorsim").exists():
                project_root = path
                break

        if not project_root:
            raise RuntimeError(
                "TraitorSim game engine not found. "
                "To run games, mount the TraitorSim project to /app/traitorsim or run locally."
            )

        logger.info(f"Using TraitorSim project root: {project_root}")

        # Build environment string for su command
        # Include API keys for Gemini and Claude
        env_vars = []
        for key in ["GEMINI_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"]:
            if os.environ.get(key):
                env_vars.append(f'{key}="{os.environ[key]}"')

        # Critical: Set up environment for Claude CLI
        # - PATH must include npm global bin for claude command
        # - HOME must be set for SDK to find config files
        # - PYTHONPATH for module imports
        env_vars.extend([
            'PATH="/usr/local/bin:/usr/bin:/bin"',
            'HOME="/home/gamerunner"',
            f'PYTHONPATH="{project_root}"',
            'PYTHONUNBUFFERED=1',
        ])
        env_str = " ".join(env_vars)

        # Run as non-root user (gamerunner) to satisfy Claude Agent SDK security requirements
        # The SDK's bypassPermissions mode cannot run as root
        game_cmd = f"cd {project_root} && {env_str} python3 -m src.traitorsim"
        cmd = ["su", "-c", game_cmd, "gamerunner"]

        # Set environment for the parent process
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Start process as gamerunner user
        _process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            preexec_fn=os.setsid  # Create new process group
        )

        _current_run.status = "running"
        await _broadcast_status()

        # Stream output
        while True:
            if _process.poll() is not None:
                break

            line = _process.stdout.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue

            line = line.strip()
            if not line:
                continue

            # Parse line for game state
            _parse_log_line(line)

            # Store and broadcast
            _current_run.log_lines.append(line)
            await _broadcast_log(line)

        # Game completed
        exit_code = _process.returncode
        _current_run.status = "completed" if exit_code == 0 else "failed"
        _current_run.ended_at = datetime.now().isoformat()

        if exit_code != 0:
            _current_run.error = f"Process exited with code {exit_code}"

        await _broadcast_status()
        logger.info(f"Game completed: {_current_run.id}, status: {_current_run.status}")

    except Exception as e:
        logger.error(f"Game run error: {e}")
        if _current_run:
            _current_run.status = "failed"
            _current_run.error = str(e)
            _current_run.ended_at = datetime.now().isoformat()
            await _broadcast_status()

    finally:
        _process = None


def _parse_log_line(line: str):
    """Parse a log line to extract game state information."""
    global _current_run

    if not _current_run:
        return

    # Day marker
    if "DAY " in line:
        import re
        match = re.search(r"DAY (\d+)", line)
        if match:
            _current_run.current_day = int(match.group(1))

    # Phase markers
    if "Breakfast Phase" in line:
        _current_run.current_phase = "breakfast"
    elif "Mission Phase" in line:
        _current_run.current_phase = "mission"
    elif "Social Phase" in line:
        _current_run.current_phase = "social"
    elif "Round Table" in line:
        _current_run.current_phase = "roundtable"
    elif "Turret Phase" in line:
        _current_run.current_phase = "turret"

    # Prize pot
    if "Prize pot:" in line:
        import re
        match = re.search(r"Prize pot: [£$]?([\d,]+)", line)
        if match:
            _current_run.prize_pot = int(match.group(1).replace(",", ""))

    # Winner
    if "WINNERS:" in line:
        if "TRAITOR" in line:
            _current_run.winner = "TRAITORS"
        elif "FAITHFUL" in line:
            _current_run.winner = "FAITHFUL"

    # Alive players
    if "players remaining" in line.lower() or "alive:" in line.lower():
        import re
        match = re.search(r"(\d+)\s*(?:players? remaining|alive)", line, re.IGNORECASE)
        if match:
            _current_run.alive_players = int(match.group(1))


async def _broadcast_status():
    """Broadcast current game status to all connected WebSocket clients."""
    if not _current_run:
        return

    message = {
        "type": "status",
        "data": asdict(_current_run)
    }
    # Don't include full log_lines in status broadcasts
    message["data"]["log_lines"] = []
    message["data"]["log_line_count"] = len(_current_run.log_lines)

    disconnected = []
    for ws in _connected_websockets:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        _connected_websockets.remove(ws)


async def _broadcast_log(line: str):
    """Broadcast a log line to all connected WebSocket clients."""
    message = {
        "type": "log",
        "data": {"line": line}
    }

    disconnected = []
    for ws in _connected_websockets:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        _connected_websockets.remove(ws)
