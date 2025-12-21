"""SDK-compatible MCP tool wrappers for Claude Agent SDK.

This module wraps the game tools with the @tool decorator to make them
compatible with the Claude Agent SDK's create_sdk_mcp_server() function.

The tools are created dynamically with game context injected via closures.
"""

from typing import Dict, Any, List
from claude_agent_sdk import tool, SdkMcpTool, create_sdk_mcp_server

from . import game_tools


def create_game_tools_for_player(context: Dict[str, Any]) -> List[SdkMcpTool]:
    """Create SDK-compatible tools with game context injected.

    Args:
        context: Game context containing player_id, game_state, etc.

    Returns:
        List of SdkMcpTool instances ready for use with create_sdk_mcp_server()
    """

    # Tool 1: Get game state
    @tool(
        "get_game_state",
        "Get current game information (day, phase, alive players, prize pot)",
        {},
    )
    async def get_game_state_sdk(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get game state (SDK-wrapped)."""
        return game_tools.get_game_state(args, context)

    # Tool 2: Get my suspicions
    @tool(
        "get_my_suspicions",
        "Read your current suspicion scores for all other players",
        {},
    )
    async def get_my_suspicions_sdk(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get suspicions (SDK-wrapped)."""
        return game_tools.get_my_suspicions(args, context)

    # Tool 3: Cast vote
    @tool(
        "cast_vote",
        "Submit your vote to banish a player at Round Table",
        {
            "target_player_id": {
                "type": "string",
                "description": "ID of player to vote for (e.g., 'player_03')",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of your vote (1-2 sentences)",
            },
        },
    )
    async def cast_vote_sdk(args: Dict[str, Any]) -> Dict[str, Any]:
        """Cast vote (SDK-wrapped)."""
        return game_tools.cast_vote(args, context)

    # Tool 4: Choose murder victim (Traitors only)
    @tool(
        "choose_murder_victim",
        "Choose which Faithful to murder tonight (Traitors only)",
        {
            "victim_player_id": {
                "type": "string",
                "description": "ID of Faithful player to murder",
            },
            "reasoning": {
                "type": "string",
                "description": "Strategic reasoning for this choice",
            },
        },
    )
    async def choose_murder_victim_sdk(args: Dict[str, Any]) -> Dict[str, Any]:
        """Choose murder victim (SDK-wrapped)."""
        return game_tools.choose_murder_victim(args, context)

    # Tool 5: Update suspicion
    @tool(
        "update_suspicion",
        "Update your suspicion score for another player",
        {
            "player_id": {
                "type": "string",
                "description": "ID of player to update suspicion for",
            },
            "new_score": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "New suspicion score (0.0=trust, 1.0=certain traitor)",
            },
            "reason": {
                "type": "string",
                "description": "Why you updated this score",
            },
        },
    )
    async def update_suspicion_sdk(args: Dict[str, Any]) -> Dict[str, Any]:
        """Update suspicion (SDK-wrapped)."""
        return game_tools.update_suspicion(args, context)

    # Tool 6: Get player info
    @tool(
        "get_player_info",
        "Query stats and publicly known information about a player",
        {
            "player_id": {
                "type": "string",
                "description": "ID of player to query",
            },
        },
    )
    async def get_player_info_sdk(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get player info (SDK-wrapped)."""
        return game_tools.get_player_info(args, context)

    # Return list of tools
    return [
        get_game_state_sdk,
        get_my_suspicions_sdk,
        cast_vote_sdk,
        choose_murder_victim_sdk,
        update_suspicion_sdk,
        get_player_info_sdk,
    ]


def create_game_mcp_server(player_id: str, game_state: Any, memory_manager: Any = None):
    """Create MCP server config for a specific player.

    Args:
        player_id: Player's ID
        game_state: Current game state
        memory_manager: Optional memory manager

    Returns:
        McpSdkServerConfig ready for ClaudeAgentOptions
    """
    # Build context
    player = game_state.get_player(player_id)
    context = {
        "player_id": player_id,
        "player": player,
        "game_state": game_state,
        "memory_manager": memory_manager,
    }

    # Create tools with context injected
    tools = create_game_tools_for_player(context)

    # Create and return MCP server config
    return create_sdk_mcp_server(
        name=f"traitorsim_game_{player_id}",
        version="1.0.0",
        tools=tools,
    )
