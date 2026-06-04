"""MCP Client -- in-process tool discovery for the Agent Runtime.

Loads the tool registry (importing mcps.reviews.tools.agent_tools triggers
@mcp_tool registration) and exposes call() + list_tools() as the single
entry point for the Agent Graph to interact with tools.
"""
from __future__ import annotations

from typing import Any

from mcps.reviews.mcp_server import list_tools, call_tool


class MCPClient:
    """Thin wrapper that loads the MCP tool registry on construction."""

    def __init__(self) -> None:
        # Trigger @mcp_tool decorators
        import mcps.reviews.tools.agent_tools  # noqa: F401

    def list_tools(self) -> list[dict[str, Any]]:
        return list_tools()

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return call_tool(tool_name, arguments)

    def get_tool_schemas_for_llm(self) -> list[dict[str, Any]]:
        """Return tool descriptions in a format suitable for LLM tool-use prompts."""
        tools = self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["inputSchema"],
                },
            }
            for t in tools
        ]


# Convenience singleton lazy-created on first access.
_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient()
    return _client
