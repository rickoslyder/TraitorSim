"""Analysis router - Optimized endpoints for game analysis queries.

These endpoints use normalized database tables for efficient queries
without loading the entire game JSON.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List

from ..db import database as db
from ..cache import cache

router = APIRouter()


@router.get("/{game_id}/trust-matrix")
async def get_trust_matrix(
    game_id: str,
    day: Optional[int] = Query(None, description="Day number to get trust matrix for"),
    phase: Optional[str] = Query(None, description="Phase to get trust matrix for")
) -> Dict[str, Any]:
    """Get the trust matrix at a specific point in the game.

    Uses normalized trust_snapshots table for efficient querying.
    If day is not specified, returns the latest snapshot.
    """
    # Check cache
    cache_key = f"trust:{game_id}:{day}:{phase}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    matrix = await db.get_trust_matrix(game_id, day, phase)

    if not matrix:
        # Return empty matrix if not found
        return {"day": day, "phase": phase, "matrix": {}, "alive_count": 0}

    cache.set(cache_key, matrix)
    return matrix


@router.get("/{game_id}/events")
async def get_events(
    game_id: str,
    day: Optional[int] = Query(None, description="Filter by day"),
    phase: Optional[str] = Query(None, description="Filter by phase"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    player_id: Optional[str] = Query(None, description="Filter by player involved"),
    limit: int = Query(100, description="Max events to return"),
    offset: int = Query(0, description="Pagination offset")
) -> Dict[str, Any]:
    """Get filtered events from a game.

    Supports filtering by day, phase, event type, and player involvement.
    Uses indexed queries on the events table.
    """
    # For type-specific queries, use optimized path
    if event_type and not player_id:
        events = await db.get_events_by_type(game_id, event_type, day)
        return {"events": events, "total": len(events)}

    # Otherwise load game and filter
    game = await db.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    events = game.get("events", [])

    # Apply filters
    if day is not None:
        events = [e for e in events if e.get("day") == day]

    if phase is not None:
        events = [e for e in events if e.get("phase") == phase]

    if event_type is not None:
        events = [e for e in events if e.get("type") == event_type]

    if player_id is not None:
        events = [
            e for e in events
            if e.get("actor") == player_id
            or e.get("target") == player_id
            or player_id in (e.get("data", {}).get("participants", []))
        ]

    # Apply pagination
    total = len(events)
    events = events[offset:offset + limit]

    return {"events": events, "total": total, "limit": limit, "offset": offset}


@router.get("/{game_id}/players/{player_id}/timeline")
async def get_player_timeline(game_id: str, player_id: str) -> Dict[str, Any]:
    """Get all events involving a specific player.

    Returns the player's full event timeline ordered chronologically.
    """
    # Get player info
    player = await db.get_player(game_id, player_id)
    if not player:
        raise HTTPException(
            status_code=404,
            detail=f"Player {player_id} not found in game {game_id}"
        )

    # Get game events and filter
    game = await db.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    events = game.get("events", [])

    # Filter events involving this player
    player_events = [
        e for e in events
        if e.get("actor") == player_id
        or e.get("target") == player_id
        or player_id in (e.get("data", {}).get("participants", []))
        or player_id in (e.get("data", {}).get("votes", {}).keys())
        or player_id in (e.get("data", {}).get("votes", {}).values())
    ]

    return {
        "player": player,
        "events": player_events,
        "total": len(player_events)
    }


@router.get("/{game_id}/voting-patterns")
async def get_voting_patterns(game_id: str) -> Dict[str, Any]:
    """Analyze voting patterns in the game.

    Returns a matrix showing how many times each player voted for each target,
    plus aggregated statistics.
    """
    # Check cache
    cache_key = f"voting:{game_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    game = await db.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    events = game.get("events", [])
    players = game.get("players", {})

    # Build voting matrix from VOTE_TALLY events (more complete data)
    vote_tallies = [e for e in events if e.get("type") == "VOTE_TALLY"]
    vote_counts: Dict[str, Dict[str, int]] = {}  # {voter: {target: count}}
    votes_received: Dict[str, int] = {}  # {target: total votes received}
    banishments: List[Dict[str, Any]] = []

    for tally in vote_tallies:
        data = tally.get("data", {})
        votes = data.get("votes", {})
        eliminated = data.get("eliminated")
        eliminated_name = data.get("eliminated_name")
        eliminated_role = data.get("eliminated_role")

        if eliminated:
            banishments.append({
                "day": tally.get("day"),
                "player_id": eliminated,
                "player_name": eliminated_name,
                "role": eliminated_role,
            })

        for voter, target in votes.items():
            if voter not in vote_counts:
                vote_counts[voter] = {}
            vote_counts[voter][target] = vote_counts[voter].get(target, 0) + 1

            votes_received[target] = votes_received.get(target, 0) + 1

    # Fallback to individual VOTE events if no tallies
    if not vote_tallies:
        vote_events = [e for e in events if e.get("type") == "VOTE"]
        for event in vote_events:
            voter = event.get("actor")
            target = event.get("target")
            if voter and target:
                if voter not in vote_counts:
                    vote_counts[voter] = {}
                vote_counts[voter][target] = vote_counts[voter].get(target, 0) + 1
                votes_received[target] = votes_received.get(target, 0) + 1

    # Calculate who voted most consistently for traitors
    traitor_ids = [pid for pid, p in players.items() if p.get("role") == "TRAITOR"]
    traitor_voters: Dict[str, int] = {}  # {voter: times_voted_for_traitor}

    for voter, targets in vote_counts.items():
        traitor_votes = sum(count for target, count in targets.items() if target in traitor_ids)
        if traitor_votes > 0:
            traitor_voters[voter] = traitor_votes

    result = {
        "vote_matrix": vote_counts,
        "votes_received": votes_received,
        "total_voting_rounds": len(vote_tallies) if vote_tallies else len(set(e.get("day") for e in events if e.get("type") == "VOTE")),
        "banishments": banishments,
        "traitor_voters": traitor_voters,
    }

    cache.set(cache_key, result)
    return result


@router.get("/{game_id}/trust-evolution")
async def get_trust_evolution(
    game_id: str,
    observer_id: Optional[str] = Query(None, description="Filter by observer"),
    target_id: Optional[str] = Query(None, description="Filter by target")
) -> Dict[str, Any]:
    """Get how trust evolved over the course of the game.

    Returns trust values at each snapshot for the specified observer/target pair,
    or all pairs if not specified.
    """
    game = await db.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    snapshots = game.get("trust_snapshots", [])

    if not snapshots:
        return {"evolution": [], "total_snapshots": 0}

    # If specific pair requested
    if observer_id and target_id:
        evolution = []
        for snapshot in snapshots:
            matrix = snapshot.get("matrix", {})
            suspicion = matrix.get(observer_id, {}).get(target_id)
            if suspicion is not None:
                evolution.append({
                    "day": snapshot.get("day"),
                    "phase": snapshot.get("phase"),
                    "suspicion": suspicion,
                })

        return {
            "observer_id": observer_id,
            "target_id": target_id,
            "evolution": evolution,
            "total_snapshots": len(evolution)
        }

    # Otherwise return summary per player
    target_suspicion: Dict[str, List[Dict[str, Any]]] = {}

    for snapshot in snapshots:
        matrix = snapshot.get("matrix", {})
        for observer, targets in matrix.items():
            if observer_id and observer != observer_id:
                continue

            for target, suspicion in targets.items():
                if target_id and target != target_id:
                    continue

                if target not in target_suspicion:
                    target_suspicion[target] = []

                target_suspicion[target].append({
                    "day": snapshot.get("day"),
                    "phase": snapshot.get("phase"),
                    "observer": observer,
                    "suspicion": suspicion,
                })

    # Calculate average suspicion per target over time
    avg_suspicion_timeline: Dict[str, List[Dict[str, Any]]] = {}

    for target, data_points in target_suspicion.items():
        # Group by day/phase
        by_snapshot: Dict[str, List[float]] = {}
        for point in data_points:
            key = f"{point['day']}-{point['phase']}"
            if key not in by_snapshot:
                by_snapshot[key] = []
            by_snapshot[key].append(point['suspicion'])

        # Calculate average
        timeline = []
        for key, values in by_snapshot.items():
            day, phase = key.split('-')
            timeline.append({
                "day": int(day),
                "phase": phase,
                "avg_suspicion": sum(values) / len(values),
                "num_observers": len(values),
            })

        timeline.sort(key=lambda x: (x['day'], x['phase']))
        avg_suspicion_timeline[target] = timeline

    return {
        "target_evolution": avg_suspicion_timeline,
        "total_snapshots": len(snapshots)
    }


@router.get("/{game_id}/mission-performance")
async def get_mission_performance(game_id: str) -> Dict[str, Any]:
    """Get mission performance data for all players.

    Aggregates mission performance scores across all missions.
    """
    mission_events = await db.get_events_by_type(game_id, "MISSION_COMPLETE")

    if not mission_events:
        return {"missions": [], "player_scores": {}, "total_missions": 0}

    player_scores: Dict[str, List[float]] = {}
    mission_summaries = []

    for event in mission_events:
        data = event.get("data", {})
        scores = data.get("performance_scores", {})

        mission_summaries.append({
            "day": event.get("day"),
            "mission_name": data.get("mission_name"),
            "success": data.get("success"),
            "success_rate": data.get("success_rate"),
            "earnings": data.get("earnings"),
            "top_performers": sorted(
                scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3] if scores else [],
        })

        for player_id, score in scores.items():
            if player_id not in player_scores:
                player_scores[player_id] = []
            player_scores[player_id].append(score)

    # Calculate averages
    avg_scores = {
        pid: sum(scores) / len(scores)
        for pid, scores in player_scores.items()
    }

    return {
        "missions": mission_summaries,
        "player_avg_scores": avg_scores,
        "total_missions": len(mission_events)
    }


@router.get("/{game_id}/breakfast-analysis")
async def get_breakfast_analysis(game_id: str) -> Dict[str, Any]:
    """Analyze breakfast entry order patterns.

    The 'last to arrive' tell is a key indicator in The Traitors.
    This endpoint analyzes arrival patterns.
    """
    breakfast_events = await db.get_events_by_type(game_id, "BREAKFAST_ORDER")

    if not breakfast_events:
        return {"days": [], "last_arrivals": {}, "patterns": []}

    last_arrivals: Dict[str, int] = {}  # {player_id: times_arrived_last}
    days_data = []

    for event in breakfast_events:
        data = event.get("data", {})
        order = data.get("order", [])
        last = data.get("last_to_arrive")
        victim = data.get("victim_revealed")

        days_data.append({
            "day": event.get("day"),
            "entry_order": order,
            "last_to_arrive": last,
            "victim_revealed": victim,
        })

        if last:
            last_arrivals[last] = last_arrivals.get(last, 0) + 1

    # Identify suspicious patterns (arrived last multiple times but never murdered)
    game = await db.get_game(game_id)
    if game:
        murdered = game.get("murdered_players", [])
        players = game.get("players", {})

        suspicious_late_arrivers = []
        for player_id, count in last_arrivals.items():
            player = players.get(player_id, {})
            player_name = player.get("name", player_id)
            player_alive = player.get("alive", True)
            was_murdered = player_name in murdered or not player_alive and player.get("elimination_type") == "MURDERED"

            if count >= 2 and not was_murdered:
                suspicious_late_arrivers.append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "times_last": count,
                    "role": player.get("role"),
                })

    return {
        "days": days_data,
        "last_arrivals": last_arrivals,
        "suspicious_patterns": suspicious_late_arrivers,
        "total_days": len(days_data)
    }
