"""Games router - Serves game data from normalized SQLite database.

This router provides:
- List games with pagination
- Get full game data by ID
- Import games from JSON files
- Sync from reports directory
- Delete games
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import logging

from ..db import database as db
from ..cache import cache, invalidate_game

logger = logging.getLogger(__name__)

router = APIRouter()

# Reports directory - mounted from host
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "/app/reports"))


# =============================================================================
# Response Models
# =============================================================================

class GameSummary(BaseModel):
    """Summary of a game for list views."""
    id: str
    name: str
    created_at: str
    total_days: int
    prize_pot: float  # Engine stores as float
    winner: str
    rule_variant: str
    config_total_players: Optional[int] = None
    config_num_traitors: Optional[int] = None


class GameListResponse(BaseModel):
    """Response for listing games."""
    games: List[GameSummary]
    total: int
    reports_dir: str


class SyncResponse(BaseModel):
    """Response for sync operation."""
    imported: List[str]
    count: int
    reports_dir: str


class ImportResponse(BaseModel):
    """Response for import operation."""
    id: str
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=GameListResponse)
async def list_all_games(limit: int = 50, offset: int = 0):
    """List all games from database with pagination.

    Games are sorted by created_at descending (newest first).
    """
    # Try cache first for total count
    cache_key = f"games:list:{limit}:{offset}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    games = await db.list_games(limit=limit, offset=offset)
    total = await db.count_games()

    # Convert to response model
    summaries = []
    for g in games:
        summaries.append(GameSummary(
            id=g["id"],
            name=g["name"],
            created_at=g["created_at"] or "",
            total_days=g["total_days"] or 0,
            prize_pot=g["prize_pot"] or 0,
            winner=g["winner"] or "UNKNOWN",
            rule_variant=g["rule_variant"] or "uk",
            config_total_players=g.get("config_total_players"),
            config_num_traitors=g.get("config_num_traitors"),
        ))

    response = GameListResponse(
        games=summaries,
        total=total,
        reports_dir=str(REPORTS_DIR)
    )

    # Cache for 30 seconds (shorter TTL for list)
    cache.set(cache_key, response)

    return response


@router.get("/{game_id}")
async def get_game_by_id(game_id: str) -> Dict[str, Any]:
    """Get full game data by ID.

    Returns complete game data including players, events, and trust snapshots,
    reconstructed from normalized database tables.
    """
    # Try cache first
    cache_key = f"game:{game_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Try database
    game = await db.get_game(game_id)

    if game:
        cache.set(cache_key, game)
        return game

    # Try partial match in database (for backwards compatibility)
    all_games = await db.list_games(limit=100, offset=0)
    for g in all_games:
        if game_id in g["id"]:
            full_game = await db.get_game(g["id"])
            if full_game:
                cache.set(cache_key, full_game)
                return full_game

    # Fallback: Try to import from filesystem
    file_path = REPORTS_DIR / f"{game_id}.json"
    if file_path.exists():
        try:
            await db.migrate_json_to_db(file_path)
            game = await db.get_game(game_id)
            if game:
                cache.set(cache_key, game)
                return game
        except Exception as e:
            logger.error(f"Failed to import game {game_id}: {e}")

    # Try partial match on filesystem
    matches = list(REPORTS_DIR.glob(f"*{game_id}*.json"))
    if matches:
        try:
            await db.migrate_json_to_db(matches[0])
            imported_id = matches[0].stem
            game = await db.get_game(imported_id)
            if game:
                cache.set(f"game:{imported_id}", game)
                return game
        except Exception as e:
            logger.error(f"Failed to import matched game: {e}")

    raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")


@router.post("/sync", response_model=SyncResponse)
async def sync_from_filesystem():
    """Scan reports directory and import any new games into database.

    This endpoint scans the configured REPORTS_DIR for JSON files
    and imports any that aren't already in the database.
    """
    imported = await db.sync_from_filesystem(REPORTS_DIR)

    # Invalidate list cache if we imported anything
    if imported:
        cache.invalidate("games:list")

    return SyncResponse(
        imported=imported,
        count=len(imported),
        reports_dir=str(REPORTS_DIR)
    )


@router.post("/import", response_model=ImportResponse)
async def import_game(file: UploadFile = File(...)):
    """Import a game JSON file into database.

    Upload a JSON game file to import it into the database.
    The file will be temporarily saved and then imported.
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    # Save to temp file
    temp_path = Path(f"/tmp/{file.filename}")
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Import to database
        game_id = await db.migrate_json_to_db(temp_path)

        # Invalidate list cache
        cache.invalidate("games:list")

        return ImportResponse(
            id=game_id,
            message="Game imported successfully"
        )
    except Exception as e:
        logger.error(f"Failed to import uploaded game: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()


@router.post("/refresh")
async def refresh_games():
    """Force refresh: sync from filesystem and clear cache.

    This combines sync and cache invalidation for a complete refresh.
    """
    # Clear all game caches
    cache.invalidate()

    # Sync from filesystem
    imported = await db.sync_from_filesystem(REPORTS_DIR)

    # Get fresh count
    total = await db.count_games()

    return {
        "message": "Games refreshed",
        "imported": imported,
        "imported_count": len(imported),
        "total_games": total,
        "reports_dir": str(REPORTS_DIR)
    }


@router.delete("/{game_id}")
async def delete_game(game_id: str):
    """Delete a game and all its related data.

    This permanently removes the game from the database.
    The original JSON file (if any) is not deleted.
    """
    deleted = await db.delete_game(game_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    # Invalidate caches
    invalidate_game(game_id)
    cache.invalidate("games:list")

    return {"message": f"Game {game_id} deleted successfully"}


@router.get("/{game_id}/trust-matrix")
async def get_trust_matrix(
    game_id: str,
    day: Optional[int] = None,
    phase: Optional[str] = None
):
    """Get trust matrix for a specific day/phase.

    If day is not specified, returns the latest snapshot.
    If phase is not specified, defaults to 'roundtable'.

    This is more efficient than loading the full game when you only
    need the trust matrix for visualization.
    """
    cache_key = f"trust:{game_id}:{day}:{phase}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    matrix = await db.get_trust_matrix(game_id, day, phase)

    if not matrix:
        raise HTTPException(
            status_code=404,
            detail=f"Trust matrix not found for game {game_id} day {day} phase {phase}"
        )

    cache.set(cache_key, matrix)
    return matrix


@router.get("/{game_id}/events")
async def get_game_events(
    game_id: str,
    event_type: Optional[str] = None,
    day: Optional[int] = None
):
    """Get events for a game, optionally filtered by type and day.

    Event types include: VOTE_TALLY, MISSION_COMPLETE, MURDER, RECRUITMENT,
    BREAKFAST_ORDER, etc.
    """
    if event_type:
        events = await db.get_events_by_type(game_id, event_type, day)
    else:
        # Get all events for the game
        game = await db.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
        events = game.get("events", [])

        # Filter by day if specified
        if day is not None:
            events = [e for e in events if e.get("day") == day]

    return {"events": events, "count": len(events)}


@router.get("/{game_id}/players/{player_id}")
async def get_player(game_id: str, player_id: str):
    """Get a specific player's data from a game.

    Returns full player data including personality, stats, and demographics.
    """
    player = await db.get_player(game_id, player_id)

    if not player:
        raise HTTPException(
            status_code=404,
            detail=f"Player {player_id} not found in game {game_id}"
        )

    return player
