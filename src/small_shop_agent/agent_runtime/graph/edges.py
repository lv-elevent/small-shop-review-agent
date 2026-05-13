"""Conditional routing — examines AgentState and decides the next graph node.

Phase 1-B: each node has at most 1 retry (2 total attempts).  Retry
counts are tracked in ``state["_retry_counts"]``.
No infinite loops — every path terminates at ``END``.
"""
from __future__ import annotations

from typing import Any

from small_shop_agent.agent_runtime.state import AgentState

# Sentinel that signals the runner to stop.
END = "__end__"

# ── Detail helpers (for trace / log) ──────────────────────────────────

def _retry_count(state: AgentState, key: str) -> int:
    return state.get("_retry_counts", {}).get(key, 0)


def _route_detail(reason: str, next_node: str) -> dict[str, Any]:
    return {"reason": reason, "next": next_node}


# ── Individual route functions ─────────────────────────────────────────

def route_after_classification(state: AgentState) -> str:
    count = len(state.get("classifications", []))
    if count == 0:
        if _retry_count(state, "classification") < 1:
            return "classification_retry"
        return "fallback_classification"
    state.setdefault("_route_details", []).append(
        _route_detail(f"classification ok ({count} results)", "sentiment"))
    return "sentiment"


def route_after_classification_retry(state: AgentState) -> str:
    count = len(state.get("classifications", []))
    if count == 0:
        state.setdefault("_route_details", []).append(
            _route_detail("retry failed (0 results)", "fallback_classification"))
        return "fallback_classification"
    state.setdefault("_route_details", []).append(
        _route_detail(f"retry ok ({count} results)", "sentiment"))
    return "sentiment"


def route_after_fallback_classification(state: AgentState) -> str:
    state.setdefault("_route_details", []).append(
        _route_detail("fallback classification used", "sentiment"))
    return "sentiment"


def route_after_sentiment(state: AgentState) -> str:
    count = len(state.get("sentiments", []))
    if count == 0:
        if _retry_count(state, "sentiment") < 1:
            return "sentiment_retry"
        return "fallback_sentiment"
    state.setdefault("_route_details", []).append(
        _route_detail(f"sentiment ok ({count} results)", "consistency"))
    return "consistency"


def route_after_sentiment_retry(state: AgentState) -> str:
    count = len(state.get("sentiments", []))
    if count == 0:
        state.setdefault("_route_details", []).append(
            _route_detail("retry failed (0 results)", "fallback_sentiment"))
        return "fallback_sentiment"
    state.setdefault("_route_details", []).append(
        _route_detail(f"retry ok ({count} results)", "consistency"))
    return "consistency"


def route_after_fallback_sentiment(state: AgentState) -> str:
    state.setdefault("_route_details", []).append(
        _route_detail("fallback sentiment used", "consistency"))
    return "consistency"


def route_after_consistency(state: AgentState) -> str:
    conflicts = 0
    mismatches = 0
    for w in state.get("warnings", []):
        if w.get("step") == "consistency_check":
            # Extract counts from warning message (best-effort)
            pass
    state.setdefault("_route_details", []).append(
        _route_detail("consistency completed", "merge"))
    return "merge"


def route_after_merge(_state: AgentState) -> str:
    return "insight"


def route_after_insight(_state: AgentState) -> str:
    return "evidence"


def route_after_evidence(state: AgentState) -> str:
    ec = state.get("_evidence_count", 0)
    if ec == 0:
        if _retry_count(state, "evidence") < 1:
            return "regenerate_insight"
        return "mark_insight_insufficient"
    state.setdefault("_route_details", []).append(
        _route_detail(f"evidence ok ({ec} items)", "reply"))
    return "reply"


def route_after_regenerate_insight(state: AgentState) -> str:
    ec = state.get("_evidence_count", 0)
    if ec == 0:
        return "mark_insight_insufficient"
    state.setdefault("_route_details", []).append(
        _route_detail(f"regenerated, evidence ok ({ec} items)", "reply"))
    return "reply"


def route_after_mark_insufficient(state: AgentState) -> str:
    state.setdefault("_route_details", []).append(
        _route_detail("insight evidence marked insufficient", "reply"))
    return "reply"


def route_after_reply(_state: AgentState) -> str:
    return "safety"


def route_after_safety(state: AgentState) -> str:
    blocked = state.get("_blocked_count", 0)
    if blocked > 0:
        state["need_human_review"] = True
        state.setdefault("_route_details", []).append(
            _route_detail(f"{blocked} blocked, needs human review", "approval"))
    else:
        state.setdefault("_route_details", []).append(
            _route_detail("all safety passed", "approval"))
    return "approval"


def route_after_approval(state: AgentState) -> str:
    state.setdefault("_route_details", []).append(
        _route_detail("pipeline complete", END))
    return END


# ── Route dispatch table ──────────────────────────────────────────────

_ROUTE_TABLE: dict[str, Any] = {
    "classification": route_after_classification,
    "classification_retry": route_after_classification_retry,
    "fallback_classification": route_after_fallback_classification,
    "sentiment_analysis": route_after_sentiment,
    "sentiment_retry": route_after_sentiment_retry,
    "fallback_sentiment": route_after_fallback_sentiment,
    "consistency_check": route_after_consistency,
    "merge_analysis": route_after_merge,
    "insights": route_after_insight,
    "evidence_check": route_after_evidence,
    "regenerate_insight": route_after_regenerate_insight,
    "mark_insight_insufficient": route_after_mark_insufficient,
    "reply_drafting": route_after_reply,
    "safety_check": route_after_safety,
    "human_approval": route_after_approval,
}


def route(state: AgentState) -> str:
    """Return the next node name given the full *state*.

    Looks up ``state["current_step"]`` in the route table and calls
    the corresponding handler.  Unknown steps fall through to ``END``.
    """
    current = state.get("current_step", "")
    handler = _ROUTE_TABLE.get(current)
    if handler is None:
        return END
    return handler(state)


# ── Backward-compatible linear helpers (kept for external callers) ─────

PIPELINE_NODE_NAMES: tuple[str, ...] = (
    "classification",
    "sentiment",
    "consistency",
    "merge",
    "insight",
    "evidence",
    "reply",
    "safety",
    "approval",
)


def next_node(current_step: str) -> str:
    """Simple linear successor (for backwards compat).  Prefer ``route(state)``."""
    try:
        idx = PIPELINE_NODE_NAMES.index(current_step)
    except ValueError:
        return END
    if idx + 1 < len(PIPELINE_NODE_NAMES):
        return PIPELINE_NODE_NAMES[idx + 1]
    return END


def is_terminal(step: str) -> bool:
    return step == END
