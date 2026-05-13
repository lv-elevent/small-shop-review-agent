"""AgentState — plain dict-based state shared across graph nodes.

Fields
------
batch_id : str
mode : str  ("demo" | "live")
model_name : str
reviews : list[dict]
classifications : list[dict]
sentiments : list[dict]
analysis_rows : list[dict]
insights : list[dict]
reply_drafts : list[dict]
safety_results : list[dict]
warnings : list[dict]
errors : list[dict]
fallback_used : bool
need_human_review : bool
current_step : str
"""
from __future__ import annotations

from typing import Any

# Public alias so callers can annotate with this type.
AgentState = dict[str, Any]


def create_initial_state(
    *,
    batch_id: str,
    mode: str = "demo",
    model_name: str = "demo",
    reviews: list[dict[str, Any]] | None = None,
) -> AgentState:
    """Return a fresh AgentState with defaults for all graph-managed fields."""
    return {
        "batch_id": batch_id,
        "mode": mode,
        "model_name": model_name,
        "reviews": reviews or [],
        "classifications": [],
        "sentiments": [],
        "analysis_rows": [],
        "insights": [],
        "reply_drafts": [],
        "safety_results": [],
        "warnings": [],
        "errors": [],
        "fallback_used": False,
        "need_human_review": False,
        "current_step": "init",
        "_retry_counts": {},
    }
