"""MCP Tool Registry — in-process tool discovery and invocation.

Implements the MCP semantic (list_tools + call_tool) inside a single
Python process.  No JSON-RPC, no stdio pipes — direct function calls
with zero network overhead.  Callers that import this module get the
full MCP-style interface with no external dependencies.
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

_registry: dict[str, dict[str, Any]] = {}


def mcp_tool(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    *,
    read_only: bool = True,
    require_batch_id: bool = False,
) -> Callable:
    """Decorator that registers a function as an MCP tool on module import."""
    def deco(fn: Callable) -> Callable:
        _registry[name] = {
            "fn": fn,
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "read_only": read_only,
            "require_batch_id": require_batch_id,
        }

        @wraps(fn)
        def wrapper(**kwargs: Any) -> Any:
            return fn(**kwargs)

        return wrapper

    return deco


def list_tools() -> list[dict[str, Any]]:
    """Return all registered tools in MCP-compatible format."""
    return [
        {
            "name": v["name"],
            "description": v["description"],
            "inputSchema": v["input_schema"],
        }
        for v in _registry.values()
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Invoke a registered tool by name.  Always returns {success, ...}."""
    entry = _registry.get(name)
    if entry is None:
        return {"success": False, "error": f"Unknown tool: {name!r}"}

    if entry["require_batch_id"] and not arguments.get("batch_id"):
        return {"success": False, "error": f"Tool {name!r} requires batch_id"}

    try:
        result = entry["fn"](**arguments)
        if isinstance(result, dict) and "success" not in result:
            result["success"] = True
        return result
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def reset_registry() -> None:
    """Clear the tool registry (for testing)."""
    _registry.clear()
