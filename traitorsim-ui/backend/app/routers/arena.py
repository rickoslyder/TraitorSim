"""Arena API router - public-facing API for external AI agents.

Provides endpoints for:
- Agent registration with callback URL verification
- Game browsing, joining, and leaving
- Agent leaderboard and profiles
- Protocol specification serving

All agent authentication uses Bearer tokens issued during registration.
"""

import hashlib
import logging
import secrets
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

import httpx

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# In-memory storage (replace with database in production)
# ---------------------------------------------------------------------------

# Registered agents: api_key_hash -> agent_data
_agents: Dict[str, Dict[str, Any]] = {}

# Agent lookup by agent_id
_agents_by_id: Dict[str, Dict[str, Any]] = {}

# Arena games: game_id -> game_data
_arena_games: Dict[str, Dict[str, Any]] = {}

# Game participants: game_id -> list of agent_ids
_game_participants: Dict[str, List[str]] = {}

# Pending decisions for polling mode: agent_id -> list of pending decisions
_pending_decisions: Dict[str, List[Dict[str, Any]]] = {}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def _hash_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def verify_agent(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Verify agent's Bearer token and return agent data."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ")
    key_hash = _hash_key(token)

    agent = _agents.get(key_hash)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Update last seen
    agent["last_seen"] = datetime.utcnow().isoformat()
    return agent


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class RegisterAgentRequest(BaseModel):
    """Request to register an agent with the arena."""
    name: str = Field(..., min_length=1, max_length=64)
    callback_url: str = Field(..., description="Base URL of agent's HTTP server")
    model_info: Optional[str] = Field(None, max_length=128)
    protocol_version: str = Field(default="1.0")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RegisterAgentResponse(BaseModel):
    """Response after successful registration."""
    agent_id: str
    api_key: str
    name: str
    protocol_version: str
    message: str


class JoinGameRequest(BaseModel):
    """Request to join an arena game."""
    preferred_persona: Optional[str] = Field(
        None, description="Preferred archetype (e.g., 'strategic_analyst')"
    )


class CreateArenaGameRequest(BaseModel):
    """Request to create an arena game."""
    name: str = Field(..., min_length=1, max_length=128)
    max_players: int = Field(default=22, ge=4, le=30)
    num_traitors: int = Field(default=3, ge=1, le=8)
    min_agents: int = Field(default=6, ge=4, le=30)
    rule_set: str = Field(default="uk")
    fill_with_ai: bool = Field(default=True)
    scheduled_start: Optional[str] = Field(None, description="ISO 8601 datetime")
    visibility: str = Field(default="public", pattern="^(public|private|invitational)$")
    max_wait_minutes: int = Field(default=30, ge=1, le=1440)


class ArenaGameResponse(BaseModel):
    """Arena game information."""
    game_id: str
    name: str
    status: str
    max_players: int
    num_traitors: int
    min_agents: int
    rule_set: str
    fill_with_ai: bool
    registered_count: int
    visibility: str
    created_at: str
    scheduled_start: Optional[str] = None


class AgentProfileResponse(BaseModel):
    """Public agent profile."""
    agent_id: str
    name: str
    model_info: Optional[str] = None
    games_played: int = 0
    wins: int = 0
    elo_rating: float = 1000.0
    registered_at: str
    last_seen: Optional[str] = None


class DecisionSubmission(BaseModel):
    """Submit a decision for polling mode."""
    decision_id: str
    response: Dict[str, Any]


# ---------------------------------------------------------------------------
# Agent Registration
# ---------------------------------------------------------------------------

@router.post("/register", response_model=RegisterAgentResponse)
async def register_agent(request: RegisterAgentRequest):
    """Register a new agent with the arena.

    The agent must have an accessible HTTP server at the callback_url.
    A health check is performed to verify connectivity.

    Returns:
        Agent ID and API key (Bearer token for all subsequent requests)
    """
    # Validate callback URL format
    callback_url = request.callback_url.rstrip("/")
    if not callback_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="callback_url must start with http:// or https://",
        )

    # Health check the agent (skip in dev/test via metadata.skip_health)
    skip_health = request.metadata.get("skip_health") is True
    if not skip_health:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{callback_url}/health")
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Agent health check failed: HTTP {response.status_code}",
                    )
                health_data = response.json()
                if health_data.get("status") != "ok":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Agent health check returned non-ok status: {health_data}",
                    )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot connect to agent at {callback_url}. Ensure your HTTP server is publicly accessible.",
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=400,
                detail=f"Agent at {callback_url} did not respond within 10 seconds.",
            )

    # Generate credentials
    agent_id = f"tsa_{secrets.token_hex(8)}"
    api_key = f"tsa_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(api_key)

    agent_data = {
        "agent_id": agent_id,
        "name": request.name,
        "callback_url": callback_url,
        "api_key_hash": key_hash,
        "model_info": request.model_info,
        "protocol_version": request.protocol_version,
        "metadata": request.metadata,
        "registered_at": datetime.utcnow().isoformat(),
        "last_seen": datetime.utcnow().isoformat(),
        "games_played": 0,
        "wins": 0,
        "elo_rating": 1000.0,
        "is_active": True,
    }

    _agents[key_hash] = agent_data
    _agents_by_id[agent_id] = agent_data

    logger.info(f"Registered agent '{request.name}' (ID: {agent_id}) at {callback_url}")

    return RegisterAgentResponse(
        agent_id=agent_id,
        api_key=api_key,
        name=request.name,
        protocol_version=request.protocol_version,
        message="Registration successful. Use the api_key as Bearer token for arena API calls.",
    )


# ---------------------------------------------------------------------------
# Game Management
# ---------------------------------------------------------------------------

@router.post("/games", response_model=ArenaGameResponse)
async def create_arena_game(
    request: CreateArenaGameRequest,
    agent: Dict = Depends(verify_agent),
):
    """Create a new arena game.

    Only registered agents can create games. The creator is automatically
    added as the first participant.
    """
    game_id = f"arena_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"

    game_data = {
        "game_id": game_id,
        "name": request.name,
        "status": "open",
        "max_players": request.max_players,
        "num_traitors": request.num_traitors,
        "min_agents": request.min_agents,
        "rule_set": request.rule_set,
        "fill_with_ai": request.fill_with_ai,
        "visibility": request.visibility,
        "max_wait_minutes": request.max_wait_minutes,
        "scheduled_start": request.scheduled_start,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": agent["agent_id"],
    }

    _arena_games[game_id] = game_data
    _game_participants[game_id] = [agent["agent_id"]]

    logger.info(f"Arena game '{request.name}' created (ID: {game_id}) by {agent['name']}")

    return ArenaGameResponse(
        game_id=game_id,
        name=request.name,
        status="open",
        max_players=request.max_players,
        num_traitors=request.num_traitors,
        min_agents=request.min_agents,
        rule_set=request.rule_set,
        fill_with_ai=request.fill_with_ai,
        registered_count=1,
        visibility=request.visibility,
        created_at=game_data["created_at"],
        scheduled_start=request.scheduled_start,
    )


@router.get("/games", response_model=List[ArenaGameResponse])
async def list_arena_games(
    status: Optional[str] = Query(None, description="Filter by status"),
    visibility: str = Query("public", description="Filter by visibility"),
):
    """List open arena games.

    Public endpoint - no authentication required for browsing.
    """
    games = []
    for gid, game in _arena_games.items():
        if status and game["status"] != status:
            continue
        if game["visibility"] != visibility and visibility != "all":
            continue

        games.append(ArenaGameResponse(
            game_id=gid,
            name=game["name"],
            status=game["status"],
            max_players=game["max_players"],
            num_traitors=game["num_traitors"],
            min_agents=game["min_agents"],
            rule_set=game["rule_set"],
            fill_with_ai=game["fill_with_ai"],
            registered_count=len(_game_participants.get(gid, [])),
            visibility=game["visibility"],
            created_at=game["created_at"],
            scheduled_start=game.get("scheduled_start"),
        ))

    return games


@router.get("/games/{game_id}", response_model=ArenaGameResponse)
async def get_arena_game(game_id: str):
    """Get details of a specific arena game."""
    game = _arena_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return ArenaGameResponse(
        game_id=game_id,
        name=game["name"],
        status=game["status"],
        max_players=game["max_players"],
        num_traitors=game["num_traitors"],
        min_agents=game["min_agents"],
        rule_set=game["rule_set"],
        fill_with_ai=game["fill_with_ai"],
        registered_count=len(_game_participants.get(game_id, [])),
        visibility=game["visibility"],
        created_at=game["created_at"],
        scheduled_start=game.get("scheduled_start"),
    )


@router.post("/games/{game_id}/join")
async def join_arena_game(
    game_id: str,
    request: Optional[JoinGameRequest] = None,
    agent: Dict = Depends(verify_agent),
):
    """Join an open arena game.

    Agents must be registered and authenticated. Each agent can only
    join a game once.
    """
    game = _arena_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game["status"] != "open":
        raise HTTPException(status_code=400, detail=f"Game is not open (status: {game['status']})")

    participants = _game_participants.get(game_id, [])
    if agent["agent_id"] in participants:
        raise HTTPException(status_code=400, detail="Already joined this game")

    if len(participants) >= game["max_players"]:
        raise HTTPException(status_code=400, detail="Game is full")

    participants.append(agent["agent_id"])
    _game_participants[game_id] = participants

    logger.info(f"Agent '{agent['name']}' joined game {game_id} ({len(participants)}/{game['max_players']})")

    return {
        "status": "joined",
        "game_id": game_id,
        "position": len(participants),
        "total_joined": len(participants),
        "max_players": game["max_players"],
    }


@router.post("/games/{game_id}/leave")
async def leave_arena_game(
    game_id: str,
    agent: Dict = Depends(verify_agent),
):
    """Leave an arena game before it starts."""
    game = _arena_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game["status"] != "open":
        raise HTTPException(status_code=400, detail="Cannot leave a game in progress")

    participants = _game_participants.get(game_id, [])
    if agent["agent_id"] not in participants:
        raise HTTPException(status_code=400, detail="Not in this game")

    participants.remove(agent["agent_id"])
    _game_participants[game_id] = participants

    logger.info(f"Agent '{agent['name']}' left game {game_id}")

    return {"status": "left", "game_id": game_id}


# ---------------------------------------------------------------------------
# Polling mode (for agents that can't run HTTP servers)
# ---------------------------------------------------------------------------

@router.get("/games/{game_id}/pending-decisions/{agent_id}")
async def get_pending_decisions(
    game_id: str,
    agent_id: str,
    agent: Dict = Depends(verify_agent),
):
    """Get pending decisions for an agent (polling mode).

    Used by agents that cannot run their own HTTP server.
    The game engine posts decisions here, and agents poll for them.
    """
    if agent["agent_id"] != agent_id:
        raise HTTPException(status_code=403, detail="Can only check your own pending decisions")

    pending = _pending_decisions.get(agent_id, [])
    game_pending = [d for d in pending if d.get("game_id") == game_id]

    return {"pending": game_pending, "count": len(game_pending)}


@router.post("/games/{game_id}/submit-decision")
async def submit_decision(
    game_id: str,
    submission: DecisionSubmission,
    agent: Dict = Depends(verify_agent),
):
    """Submit a decision response (polling mode).

    Used in conjunction with pending-decisions endpoint.
    """
    agent_id = agent["agent_id"]
    pending = _pending_decisions.get(agent_id, [])

    # Find and remove the matching pending decision
    matched = None
    for i, d in enumerate(pending):
        if d.get("decision_id") == submission.decision_id and d.get("game_id") == game_id:
            matched = pending.pop(i)
            break

    if not matched:
        raise HTTPException(status_code=404, detail="Decision not found or already submitted")

    # Store the response for the game engine to pick up
    matched["response"] = submission.response
    matched["submitted_at"] = datetime.utcnow().isoformat()

    logger.info(f"Agent {agent_id} submitted decision {submission.decision_id} for game {game_id}")

    return {"status": "accepted", "decision_id": submission.decision_id}


# ---------------------------------------------------------------------------
# Agent Leaderboard and Profiles
# ---------------------------------------------------------------------------

@router.get("/agents", response_model=List[AgentProfileResponse])
async def list_agents(
    sort_by: str = Query("elo_rating", description="Sort by: elo_rating, games_played, wins, name"),
    limit: int = Query(50, ge=1, le=100),
):
    """Get the agent leaderboard.

    Public endpoint - no authentication required.
    """
    agents = list(_agents_by_id.values())

    sort_key = {
        "elo_rating": lambda a: a.get("elo_rating", 1000.0),
        "games_played": lambda a: a.get("games_played", 0),
        "wins": lambda a: a.get("wins", 0),
        "name": lambda a: a.get("name", ""),
    }.get(sort_by, lambda a: a.get("elo_rating", 1000.0))

    agents.sort(key=sort_key, reverse=(sort_by != "name"))

    return [
        AgentProfileResponse(
            agent_id=a["agent_id"],
            name=a["name"],
            model_info=a.get("model_info"),
            games_played=a.get("games_played", 0),
            wins=a.get("wins", 0),
            elo_rating=a.get("elo_rating", 1000.0),
            registered_at=a["registered_at"],
            last_seen=a.get("last_seen"),
        )
        for a in agents[:limit]
    ]


@router.get("/agents/{agent_id}", response_model=AgentProfileResponse)
async def get_agent_profile(agent_id: str):
    """Get a specific agent's public profile."""
    agent = _agents_by_id.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentProfileResponse(
        agent_id=agent["agent_id"],
        name=agent["name"],
        model_info=agent.get("model_info"),
        games_played=agent.get("games_played", 0),
        wins=agent.get("wins", 0),
        elo_rating=agent.get("elo_rating", 1000.0),
        registered_at=agent["registered_at"],
        last_seen=agent.get("last_seen"),
    )


# ---------------------------------------------------------------------------
# Protocol specification
# ---------------------------------------------------------------------------

@router.get("/protocol")
async def get_protocol_spec():
    """Get the TraitorSim Agent Protocol specification.

    Returns the full protocol spec including required/optional endpoints,
    request/response schemas, and behavioral requirements.
    """
    return {
        "protocol": "TraitorSim Agent Protocol",
        "version": "1.0",
        "documentation": "https://traitorsim.rbnk.uk/docs/agent-protocol",
        "required_endpoints": [
            {"method": "GET", "path": "/health", "description": "Health check - return {status: 'ok'}"},
            {"method": "POST", "path": "/initialize", "description": "Receive player config, role, personality"},
            {"method": "POST", "path": "/vote", "description": "Cast Round Table banishment vote"},
            {"method": "POST", "path": "/reflect", "description": "Process game events, update internal state"},
            {"method": "GET", "path": "/get_suspicions", "description": "Return current trust matrix scores"},
        ],
        "optional_endpoints": [
            {"method": "POST", "path": "/choose_murder_victim", "condition": "Traitor role", "description": "Select murder target"},
            {"method": "POST", "path": "/choose_recruit_target", "condition": "Traitor role", "description": "Choose recruitment target"},
            {"method": "POST", "path": "/decide_recruitment", "condition": "Recruited by Traitors", "description": "Accept/refuse recruitment"},
            {"method": "POST", "path": "/vote_to_end", "condition": "Final N players", "description": "Vote END or BANISH"},
            {"method": "POST", "path": "/share_or_steal", "condition": "Australia variant", "description": "Traitor's Dilemma decision"},
            {"method": "POST", "path": "/choose_seer_target", "condition": "Has Seer power", "description": "Choose investigation target"},
            {"method": "POST", "path": "/seer_result", "condition": "After Seer use", "description": "Receive investigation result"},
            {"method": "POST", "path": "/create_death_list", "condition": "Traitor, Death List mechanic", "description": "Pre-select murder candidates"},
        ],
        "behavioral_requirements": [
            "Agents MUST NOT access other agents' private data",
            "Traitor agents MUST NOT leak role information in public reasoning",
            "Vote targets MUST be alive players (not self)",
            "Murder targets MUST be alive Faithful players",
            "Agents SHOULD maintain internal trust/suspicion tracking",
            "Agents SHOULD respect OCEAN personality traits in decision-making",
        ],
        "timeouts": {
            "decision": "60 seconds",
            "reflect": "30 seconds",
            "health_check": "10 seconds",
            "fallback": "Random valid action on timeout",
        },
        "rate_limits": {
            "registration": "1 per hour",
            "game_joins": "5 per hour",
            "api_calls": "100 per minute",
        },
    }


# ---------------------------------------------------------------------------
# Admin / internal endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def arena_status():
    """Get overall arena status (public)."""
    return {
        "total_agents": len(_agents_by_id),
        "active_games": len([g for g in _arena_games.values() if g["status"] == "in_progress"]),
        "open_games": len([g for g in _arena_games.values() if g["status"] == "open"]),
        "completed_games": len([g for g in _arena_games.values() if g["status"] == "completed"]),
    }
