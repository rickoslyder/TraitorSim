"""MCP server setup for TraitorSim game tools.

This module provides in-process MCP tools for Claude Agent SDK player agents.
Tools are registered with the SDK client to enable structured decision-making.
"""

from typing import Dict, Any, List
from .game_tools import TOOL_DEFINITIONS


class GameToolServer:
    """In-process MCP tool server for game actions.

    This server provides structured tools to Claude SDK agents, replacing
    fragile regex-based extraction with reliable tool calls.
    """

    def __init__(self):
        """Initialize the tool server with game tools."""
        self.tools = TOOL_DEFINITIONS

    def get_tools_for_sdk(self) -> List[Dict[str, Any]]:
        """Get tool definitions formatted for Claude Agent SDK.

        Returns:
            List of tool definitions with function, description, and parameters.
        """
        return [
            {
                "name": name,
                "function": tool_def["function"],
                "description": tool_def["description"],
                "input_schema": tool_def["parameters"]
            }
            for name, tool_def in self.tools.items()
        ]

    def get_tool_names(self) -> List[str]:
        """Get list of available tool names.

        Returns:
            List of tool names.
        """
        return list(self.tools.keys())

    def get_tool(self, name: str) -> Dict[str, Any]:
        """Get a specific tool definition.

        Args:
            name: Tool name to retrieve

        Returns:
            Tool definition dict

        Raises:
            KeyError: If tool name not found
        """
        return self.tools[name]

    def execute_tool(self, name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name.

        Args:
            name: Tool name to execute
            args: Tool arguments
            context: Game context (player_id, game_state, etc.)

        Returns:
            Tool result dict with content and optional isError flag

        Raises:
            KeyError: If tool name not found
        """
        if name not in self.tools:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: Unknown tool '{name}'"
                }],
                "isError": True
            }

        tool_function = self.tools[name]["function"]
        return tool_function(args, context)


def create_tool_server() -> GameToolServer:
    """Create and return a GameToolServer instance.

    Convenience function for initializing the MCP tool server.

    Returns:
        Initialized GameToolServer
    """
    return GameToolServer()


# Global server instance (can be shared across agents)
_tool_server = None


def get_tool_server() -> GameToolServer:
    """Get the global tool server instance (singleton pattern).

    Returns:
        Global GameToolServer instance
    """
    global _tool_server
    if _tool_server is None:
        _tool_server = create_tool_server()
    return _tool_server
