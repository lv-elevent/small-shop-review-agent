"""Rule-based sentiment accuracy scorer — compares sentiment against mock ground truth."""
from __future__ import annotations

from typing import Any


def score_sentiment_accuracy(
    analysis: list[dict[str, Any]],
    ground_truth: dict[str, str],
) -> dict[str, Any]:
    """
    Compare each review_analysis row's sentiment against expected values.

    Args:
        analysis: list of review_analysis rows (each has review_id, sentiment)
        ground_truth: dict of review_id → expected sentiment

    Returns:
        {total, correct_count, accuracy, mismatches: [...]}
    """
    total = 0
    correct = 0
    mismatches: list[dict[str, Any]] = []

    for row in analysis:
        rid = row["review_id"]
        actual = row["sentiment"]
        expected = ground_truth.get(rid)
        if expected is None:
            continue
        total += 1
        if actual == expected:
            correct += 1
        else:
            mismatches.append({
                "review_id": rid,
                "expected": expected,
                "actual": actual,
            })

    accuracy = round(correct / total, 4) if total > 0 else 0.0
    return {
        "total": total,
        "correct_count": correct,
        "accuracy": accuracy,
        "mismatches": mismatches,
    }
