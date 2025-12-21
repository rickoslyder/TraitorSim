#!/usr/bin/env python3
"""Quick script to call get_game_state and display current game information.

This is a minimal example showing how to use the get_game_state MCP tool.
"""

import json
from src.traitorsim.mcp.game_tools import get_game_state
from src.traitorsim.core.game_state import GameState, Player, TrustMatrix
from src.traitorsim.core.enums import GamePhase, Role


def quick_game_state_example():
    """Simple example of calling get_game_state."""

    # Create a minimal game state
    game_state = GameState()
    game_state.day = 3
    game_state.phase = GamePhase.SOCIAL
    game_state.prize_pot = 1750.0
    game_state.last_murder_victim = "Player9"
    game_state.banished_players = ["Player2"]

    # Add some players
    for i in range(1, 11):
        player = Player(
            id=f"player_{i-1:02d}",
            name=f"Player{i}",
            role=Role.TRAITOR if i in [4, 5, 8] else Role.FAITHFUL
        )
        # Player2 and Player9 are dead
        if i in [2, 9]:
            player.alive = False
        game_state.players.append(player)

    # Create context for the tool
    context = {
        "game_state": game_state
    }

    # Call get_game_state tool
    print("Calling get_game_state()...")
    print("="*70)
    result = get_game_state({}, context)

    # Parse and display the result
    if "isError" in result and result["isError"]:
        print("ERROR:", result["content"][0]["text"])
    else:
        state_data = json.loads(result["content"][0]["text"])
        print(json.dumps(state_data, indent=2))

    print("\n" + "="*70)
    print(f"Summary: Day {game_state.day}, {len(game_state.alive_players)} alive, ${game_state.prize_pot:,.0f} prize")


if __name__ == "__main__":
    quick_game_state_example()
