"""MCP tools for TraitorSim game actions.

These tools provide structured interfaces for player agents to interact with the game,
replacing fragile regex-based extraction with reliable tool calls.
"""

import json
from typing import Dict, Any


def get_game_state(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current game information (day, phase, alive players, prize pot).

    Tool for agents to query the current state of the game.

    Args:
        args: Empty dict (no parameters needed)
        context: Game context containing game_state

    Returns:
        Tool result with game state JSON
    """
    game_state = context.get("game_state")

    if not game_state:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Game state not available"
            }],
            "isError": True
        }

    state_info = {
        "day": game_state.day,
        "phase": game_state.phase.value if hasattr(game_state.phase, 'value') else str(game_state.phase),
        "alive_players": [
            {"id": p.id, "name": p.name}
            for p in game_state.alive_players
        ],
        "prize_pot": float(game_state.prize_pot),
        "last_murder_victim": game_state.last_murder_victim,
        "recent_banishments": game_state.banished_players[-3:] if game_state.banished_players else []
    }

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(state_info, indent=2)
        }]
    }


def get_my_suspicions(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read your current suspicion scores for all other players.

    Tool for agents to query their trust matrix scores.

    Args:
        args: Empty dict (no parameters needed)
        context: Game context containing player_id, game_state

    Returns:
        Tool result with suspicion scores JSON
    """
    player_id = context.get("player_id")
    game_state = context.get("game_state")

    if not player_id or not game_state:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Player ID or game state not available"
            }],
            "isError": True
        }

    suspicions = {}
    for other_player in game_state.alive_players:
        if other_player.id != player_id:
            score = game_state.trust_matrix.get_suspicion(player_id, other_player.id)
            suspicions[other_player.id] = {
                "name": other_player.name,
                "suspicion": float(score),
                "alive": other_player.alive
            }

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(suspicions, indent=2)
        }]
    }


def cast_vote(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit your vote to banish a player at Round Table.

    This is the primary decision-making tool for Round Table voting.

    Args:
        args: {
            "target_player_id": str - ID of player to vote for (e.g., 'player_03')
            "reasoning": str - Brief explanation of your vote (1-2 sentences)
        }
        context: Game context containing player_id, game_state

    Returns:
        Tool result confirming vote or error
    """
    target_id = args.get("target_player_id")
    reasoning = args.get("reasoning", "No reasoning provided")

    player_id = context.get("player_id")
    game_state = context.get("game_state")

    if not target_id:
        return {
            "content": [{
                "type": "text",
                "text": "Error: target_player_id is required"
            }],
            "isError": True
        }

    if not player_id or not game_state:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Player ID or game state not available"
            }],
            "isError": True
        }

    # Validate target
    valid_targets = [p.id for p in game_state.alive_players if p.id != player_id]

    if target_id not in valid_targets:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {target_id} is not a valid vote target. Must be one of: {valid_targets}"
            }],
            "isError": True
        }

    # Store vote in context (will be collected by game engine)
    context["vote_result"] = {
        "target": target_id,
        "reasoning": reasoning
    }

    target_player = game_state.get_player(target_id)
    target_name = target_player.name if target_player else target_id

    return {
        "content": [{
            "type": "text",
            "text": f"Vote recorded: {target_name} ({target_id}). Reasoning: {reasoning}"
        }]
    }


def choose_murder_victim(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Choose which Faithful to murder tonight (Traitors only).

    This tool is only available to Traitor players during the Turret phase.

    Args:
        args: {
            "victim_player_id": str - ID of Faithful player to murder
            "reasoning": str - Strategic reasoning for this choice
        }
        context: Game context containing player, game_state

    Returns:
        Tool result confirming murder choice or error
    """
    victim_id = args.get("victim_player_id")
    reasoning = args.get("reasoning", "No reasoning provided")

    player = context.get("player")
    game_state = context.get("game_state")

    if not victim_id:
        return {
            "content": [{
                "type": "text",
                "text": "Error: victim_player_id is required"
            }],
            "isError": True
        }

    if not player or not game_state:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Player or game state not available"
            }],
            "isError": True
        }

    # Verify caller is a traitor
    if player.role.value != "traitor":
        return {
            "content": [{
                "type": "text",
                "text": "Error: Only Traitors can use this tool."
            }],
            "isError": True
        }

    # Validate target is Faithful
    faithful_ids = [p.id for p in game_state.alive_faithful]

    if victim_id not in faithful_ids:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {victim_id} is not a valid murder target. Must be an alive Faithful: {faithful_ids}"
            }],
            "isError": True
        }

    # Store murder choice in context
    context["murder_choice"] = {
        "victim": victim_id,
        "reasoning": reasoning
    }

    victim_player = game_state.get_player(victim_id)
    victim_name = victim_player.name if victim_player else victim_id

    return {
        "content": [{
            "type": "text",
            "text": f"Murder target selected: {victim_name} ({victim_id}). Reasoning: {reasoning}"
        }]
    }


def update_suspicion(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update your suspicion score for another player.

    Tool for agents to maintain their trust matrix with structured reasoning.

    Args:
        args: {
            "player_id": str - ID of player to update suspicion for
            "new_score": float - New suspicion score (0.0=trust, 1.0=certain traitor)
            "reason": str - Why you updated this score
        }
        context: Game context containing player_id (observer), game_state, memory_manager

    Returns:
        Tool result confirming update
    """
    suspect_id = args.get("player_id")
    new_score = args.get("new_score")
    reason = args.get("reason", "No reason provided")

    observer_id = context.get("player_id")
    game_state = context.get("game_state")
    memory_manager = context.get("memory_manager")

    if suspect_id is None or new_score is None:
        return {
            "content": [{
                "type": "text",
                "text": "Error: player_id and new_score are required"
            }],
            "isError": True
        }

    if not observer_id or not game_state:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Observer ID or game state not available"
            }],
            "isError": True
        }

    # Validate score range
    new_score = float(new_score)
    if not (0.0 <= new_score <= 1.0):
        return {
            "content": [{
                "type": "text",
                "text": "Error: new_score must be between 0.0 and 1.0"
            }],
            "isError": True
        }

    # Get current score
    old_score = game_state.trust_matrix.get_suspicion(observer_id, suspect_id)
    delta = new_score - old_score

    # Update trust matrix
    game_state.trust_matrix.update_suspicion(observer_id, suspect_id, delta)

    # Update memory file if available
    suspect = game_state.get_player(suspect_id)
    if memory_manager and suspect:
        memory_manager.update_suspicion(suspect_id, suspect.name, new_score, reason)

    suspect_name = suspect.name if suspect else suspect_id

    return {
        "content": [{
            "type": "text",
            "text": f"Updated suspicion of {suspect_name}: {old_score:.2f} → {new_score:.2f}. Reason: {reason}"
        }]
    }


def get_player_info(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query stats and publicly known information about a player.

    Tool for agents to learn about other players (role only revealed if dead).

    Args:
        args: {
            "player_id": str - ID of player to query
        }
        context: Game context containing game_state

    Returns:
        Tool result with player information JSON
    """
    target_id = args.get("player_id")
    game_state = context.get("game_state")

    if not target_id:
        return {
            "content": [{
                "type": "text",
                "text": "Error: player_id is required"
            }],
            "isError": True
        }

    if not game_state:
        return {
            "content": [{
                "type": "text",
                "text": "Error: Game state not available"
            }],
            "isError": True
        }

    player = game_state.get_player(target_id)

    if not player:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Player {target_id} not found."
            }],
            "isError": True
        }

    # Build info (don't reveal role unless dead)
    info = {
        "id": player.id,
        "name": player.name,
        "alive": player.alive,
        "stats": {
            "intellect": float(player.stats.get("intellect", 0.5)),
            "dexterity": float(player.stats.get("dexterity", 0.5)),
            "social_influence": float(player.stats.get("social_influence", 0.5))
        }
    }

    # Only show role if banished/murdered
    if not player.alive:
        info["role"] = player.role.value
    else:
        info["role"] = "Unknown (alive)"

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(info, indent=2)
        }]
    }


# Tool metadata for SDK registration
TOOL_DEFINITIONS = {
    "get_game_state": {
        "function": get_game_state,
        "description": "Get current game information (day, phase, alive players, prize pot)",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "get_my_suspicions": {
        "function": get_my_suspicions,
        "description": "Read your current suspicion scores for all other players",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "cast_vote": {
        "function": cast_vote,
        "description": "Submit your vote to banish a player at Round Table",
        "parameters": {
            "type": "object",
            "properties": {
                "target_player_id": {
                    "type": "string",
                    "description": "ID of player to vote for (e.g., 'player_03')"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of your vote (1-2 sentences)"
                }
            },
            "required": ["target_player_id", "reasoning"]
        }
    },
    "choose_murder_victim": {
        "function": choose_murder_victim,
        "description": "Choose which Faithful to murder tonight (Traitors only)",
        "parameters": {
            "type": "object",
            "properties": {
                "victim_player_id": {
                    "type": "string",
                    "description": "ID of Faithful player to murder"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Strategic reasoning for this choice"
                }
            },
            "required": ["victim_player_id", "reasoning"]
        }
    },
    "update_suspicion": {
        "function": update_suspicion,
        "description": "Update your suspicion score for another player",
        "parameters": {
            "type": "object",
            "properties": {
                "player_id": {
                    "type": "string",
                    "description": "ID of player to update suspicion for"
                },
                "new_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "New suspicion score (0.0=trust, 1.0=certain traitor)"
                },
                "reason": {
                    "type": "string",
                    "description": "Why you updated this score"
                }
            },
            "required": ["player_id", "new_score", "reason"]
        }
    },
    "get_player_info": {
        "function": get_player_info,
        "description": "Query stats and publicly known information about a player",
        "parameters": {
            "type": "object",
            "properties": {
                "player_id": {
                    "type": "string",
                    "description": "ID of player to query"
                }
            },
            "required": ["player_id"]
        }
    }
}
