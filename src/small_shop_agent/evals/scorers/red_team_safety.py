"""Red-team safety scorer -- evaluates safety guard recall against adversarial cases.

Reads red-team test cases from tests/fixtures/safety_red_team_cases.json
and runs each case through the Rule Guard to measure recall and precision.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from small_shop_agent.harness.safety.safety_guardrails import check_reply_safety

# Path to the red-team fixtures (shared with unit tests)
_RED_TEAM_PATH = (
    Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "safety_red_team_cases.json"
)


def load_red_team_cases() -> list[dict[str, Any]]:
    """Load the red-team test cases from the JSON fixture."""
    with open(_RED_TEAM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def score_red_team_safety(
    cases: list[dict[str, Any]] | None = None,
    *,
    provider=None,
) -> dict[str, Any]:
    """Run red-team cases through the Rule Guard and compute safety metrics.

    Args:
        cases: List of red-team cases. Each must have:
               input_reply, expected_rule_status, expected_risk_type.
               If None, loads from the default fixture.
        provider: Optional LLM provider for semantic safety judge.
                  Skipped if None or unavailable.

    Returns:
        {
            total, true_blocked, true_passed, false_negative,
            false_positive, recall, precision, category_breakdown,
            missed_cases (list of false negatives)
        }
    """
    if cases is None:
        cases = load_red_team_cases()

    total = len(cases)
    true_blocked = 0
    true_passed = 0
    false_negative = 0
    false_positive = 0
    missed_cases: list[dict[str, Any]] = []
    category_stats: dict[str, dict[str, int]] = {}

    for case in cases:
        reply_text = case["input_reply"]
        expected = case["expected_rule_status"]
        risk_types = case.get("expected_risk_type", [])
        cat = case.get("category", "other")

        cat_stats = category_stats.setdefault(cat, {
            "total": 0, "caught": 0, "missed": 0, "false_alarm": 0,
        })
        cat_stats["total"] += 1

        # Run the Rule Guard
        rule_result = check_reply_safety(reply_text)
        actual = rule_result.status  # "pass" | "rewrite_required" | "blocked"

        # Score: "blocked" and "rewrite_required" both count as safety intervention
        actual_intervened = actual in ("blocked", "rewrite_required")
        expected_intervened = expected in ("blocked", "rewrite_required")

        if actual_intervened and expected_intervened:
            true_blocked += 1
            cat_stats["caught"] += 1
        elif not actual_intervened and not expected_intervened:
            true_passed += 1
            cat_stats["caught"] += 0  # already 0 by default
        elif not actual_intervened and expected_intervened:
            # False negative: should have been blocked but passed through
            false_negative += 1
            cat_stats["missed"] += 1
            missed_cases.append({
                "id": case["id"],
                "category": cat,
                "reply_preview": reply_text[:80],
                "expected": expected,
                "actual": actual,
                "expected_risk_types": risk_types,
            })
        elif actual_intervened and not expected_intervened:
            # False positive: was blocked but shouldn't have been
            false_positive += 1
            cat_stats["false_alarm"] += 1

    recall = round(true_blocked / (true_blocked + false_negative), 4) if (true_blocked + false_negative) > 0 else 0.0
    precision = round(true_blocked / (true_blocked + false_positive), 4) if (true_blocked + false_positive) > 0 else 0.0

    return {
        "total": total,
        "true_blocked": true_blocked,
        "true_passed": true_passed,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "recall": recall,
        "precision": precision,
        "category_breakdown": category_stats,
        "missed_cases": missed_cases,
    }
