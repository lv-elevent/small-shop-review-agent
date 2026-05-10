"""Schema stability scorer — checks traces for failures, unexpected step names, and schema errors."""
from __future__ import annotations

import re
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
    Check traces for schema failures, unexpected step names, and
    classification schema_errors_count.

    Returns:
        {total_steps, failed_count, schema_failure_count, unexpected_steps: [...]}
    """
    failed = 0
    unexpected: list[str] = []
    schema_errors_total = 0

    for t in traces:
        step = t.get("step_name", "")
        status = t.get("status", "")

        if status == "failed":
            failed += 1

        if step and step not in _EXPECTED_STEPS:
            unexpected.append(step)

        if step == "classification":
            output = t.get("output_summary", "")
            m = re.search(r"schema_errors_count=(\d+)", output)
            if m:
                schema_errors_total += int(m.group(1))

    return {
        "total_steps": len(traces),
        "failed_count": failed,
        "schema_failure_count": failed + len(unexpected) + schema_errors_total,
        "unexpected_steps": unexpected,
    }
