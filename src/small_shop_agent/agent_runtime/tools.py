"""Read-only business tools -- re-exports from MCP agent tools.

DEPRECATED: New code should import from mcps.reviews.mcp_client.
This module is kept for backward compatibility with existing tests.
"""
from __future__ import annotations

# Import triggers @mcp_tool registration
from mcps.reviews.tools.agent_tools import (  # noqa: F401
    lookup_review,
    search_reviews,
    count_by_topic,
    get_batch_stats,
    get_safety_policy_snippet,
    csv_stats,
)
