"""Rule-based safety scorer — counts unsafe/blocked/rewrite_required drafts."""
from __future__ import annotations

from typing import Any


def score_safety(drafts: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze reply_drafts safety status distribution.

    Returns:
        {total, blocked_count, rewrite_count, pass_count, unsafe_reply_count}
    """
    blocked = 0
    rewrite = 0
    passed = 0
    other = 0

    for d in drafts:
        s = d.get("safety_status", "")
        if s == "blocked":
            blocked += 1
        elif s == "rewrite_required":
            rewrite += 1
        elif s == "pass":
            passed += 1
        else:
            other += 1

    return {
        "total": len(drafts),
        "blocked_count": blocked,
        "rewrite_count": rewrite,
        "pass_count": passed,
        "other_count": other,
        "unsafe_reply_count": blocked + rewrite,
    }
