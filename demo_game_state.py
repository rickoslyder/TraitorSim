#!/usr/bin/env python3
"""Demo script to show how to access game state using the get_game_state tool.

This demonstrates the MCP tool interface for "The Traitors" game simulation.
"""

import json
from src.traitorsim.core.game_state import GameState, Player, TrustMatrix
from src.traitorsim.core.enums import GamePhase, Role
from src.traitorsim.mcp.game_tools import (
    get_game_state,
    get_my_suspicions,
    get_player_info,
)
from src.traitorsim.mcp.server import GameToolServer


def create_demo_game_state():
    """Create a demo game state based on the recent game log."""
    game_state = GameState()

    # Create players based on the log (10 players, 3 traitors)
    player_names = [
        "Player1", "Player2", "Player3", "Player4", "Player5",
        "Player6", "Player7", "Player8", "Player9", "Player10"
    ]

    # Traitors are Player4, Player5, Player8 (indices 3, 4, 7)
    traitor_indices = [3, 4, 7]

    for i, name in enumerate(player_names):
        player = Player(
            id=f"player_{i:02d}",
            name=name,
            role=Role.TRAITOR if i in traitor_indices else Role.FAITHFUL,
            personality={
                "openness": 0.6,
                "conscientiousness": 0.5,
                "extraversion": 0.7,
                "agreeableness": 0.5,
                "neuroticism": 0.4,
            },
            stats={
                "intellect": 0.7,
                "dexterity": 0.6,
                "social_influence": 0.8,
            },
        )
        game_state.players.append(player)

    # Set game state from the log
    game_state.day = 3
    game_state.phase = GamePhase.SOCIAL
    game_state.prize_pot = 1750.0

    # Player9 (index 8) was murdered
    game_state.players[8].alive = False
    game_state.last_murder_victim = "Player9"
    game_state.murdered_players.append("Player9")

    # Player2 (index 1) was banished
    game_state.players[1].alive = False
    game_state.banished_players.append("Player2")

    # Initialize trust matrix for alive players
    player_ids = [f"player_{i:02d}" for i in range(10)]
    game_state.trust_matrix = TrustMatrix(player_ids)

    # Add some sample suspicions
    game_state.trust_matrix.update_suspicion("player_00", "player_03", 0.3)  # Player1 suspects Player4
    game_state.trust_matrix.update_suspicion("player_00", "player_04", 0.4)  # Player1 suspects Player5
    game_state.trust_matrix.update_suspicion("player_00", "player_07", 0.2)  # Player1 suspects Player8

    return game_state


def main():
    """Demonstrate accessing game state via MCP tools."""

    print("="*70)
    print("THE TRAITORS - GAME STATE DEMO")
    print("="*70)
    print()

    # Create demo game state
    game_state = create_demo_game_state()

    # Create tool context for Player1
    context = {
        "player_id": "player_00",
        "player": game_state.players[0],
        "game_state": game_state,
    }

    # 1. Get overall game state
    print("1. GET_GAME_STATE Tool")
    print("-" * 70)
    result = get_game_state({}, context)
    state_data = json.loads(result["content"][0]["text"])
    print(json.dumps(state_data, indent=2))
    print()

    # 2. Get Player1's suspicions
    print("2. GET_MY_SUSPICIONS Tool (for Player1)")
    print("-" * 70)
    result = get_my_suspicions({}, context)
    suspicions_data = json.loads(result["content"][0]["text"])
    print(json.dumps(suspicions_data, indent=2))
    print()

    # 3. Get info about specific players
    print("3. GET_PLAYER_INFO Tool Examples")
    print("-" * 70)

    # Get info about an alive player (role hidden)
    print("Info about Player4 (alive, actually a Traitor):")
    result = get_player_info({"player_id": "player_03"}, context)
    player_info = json.loads(result["content"][0]["text"])
    print(json.dumps(player_info, indent=2))
    print()

    # Get info about a dead player (role revealed)
    print("Info about Player2 (banished, was a Faithful):")
    result = get_player_info({"player_id": "player_01"}, context)
    player_info = json.loads(result["content"][0]["text"])
    print(json.dumps(player_info, indent=2))
    print()

    # 4. Use GameToolServer
    print("4. Using GameToolServer")
    print("-" * 70)
    server = GameToolServer()
    print(f"Available tools: {server.get_tool_names()}")
    print()

    # Execute tool through server
    result = server.execute_tool("get_game_state", {}, context)
    print("Game state via server:")
    print(result["content"][0]["text"])
    print()

    # Summary
    print("="*70)
    print("GAME STATE SUMMARY")
    print("="*70)
    print(f"Day: {game_state.day}")
    print(f"Phase: {game_state.phase.value}")
    print(f"Prize Pot: ${game_state.prize_pot:,.0f}")
    print(f"Alive Players: {len(game_state.alive_players)}/10")
    print(f"Alive Faithful: {len(game_state.alive_faithful)}")
    print(f"Alive Traitors: {len(game_state.alive_traitors)}")
    print(f"Last Murder Victim: {game_state.last_murder_victim}")
    print(f"Banished Players: {', '.join(game_state.banished_players)}")
    print()

    print("Alive Players:")
    for player in game_state.alive_players:
        print(f"  - {player.name} ({player.id}) - Role: {'TRAITOR' if player.role == Role.TRAITOR else 'FAITHFUL'}")
    print()

    print("Dead Players:")
    for player in game_state.players:
        if not player.alive:
            status = "Murdered" if player.name in game_state.murdered_players else "Banished"
            print(f"  - {player.name} ({player.id}) - Role: {player.role.value.upper()} - Status: {status}")
    print()

    print("="*70)
    print("Tool demonstration complete!")
    print("="*70)


if __name__ == "__main__":
    main()
