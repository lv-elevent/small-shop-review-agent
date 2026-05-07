"""Schema stability scorer — checks traces for failures and unexpected step names."""
from __future__ import annotations

from typing import Any

_EXPECTED_STEPS = {
    "input_validation",
    "data_cleaning",
    "classification",
    "sentiment_analysis",
    "issue_aggregation",
    "evidence_check",
    "reply_drafting",
    "safety_check",
    "human_approval",
    "eval_run",
}


def score_schema_stability(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Check traces for schema failures and unexpected step names.

    Returns:
        {total_steps, failed_count, schema_failure_count, unexpected_steps: [...]}
    """
    failed = 0
    unexpected: list[str] = []

    for t in traces:
        step = t.get("step_name", "")
        status = t.get("status", "")

        if status == "failed":
            failed += 1

        if step and step not in _EXPECTED_STEPS:
            unexpected.append(step)

    return {
        "total_steps": len(traces),
        "failed_count": failed,
        "schema_failure_count": failed + len(unexpected),
        "unexpected_steps": unexpected,
    }
