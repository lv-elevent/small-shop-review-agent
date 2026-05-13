"""Cross-step consistency checks — catch mismatches between pipeline steps."""
from __future__ import annotations

from typing import Any


def check_classification_sentiment_alignment(
    classifications: list[dict[str, Any]],
    sentiments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Verify every classification has a matching sentiment record and vice versa.

    Returns list of mismatches with {review_id, issue}.
    """
    cls_ids = {c["review_id"] for c in classifications}
    sent_ids = {s["review_id"] for s in sentiments}

    mismatches: list[dict[str, Any]] = []
    for rid in cls_ids - sent_ids:
        mismatches.append({"review_id": rid, "issue": "classified but not analyzed for sentiment"})
    for rid in sent_ids - cls_ids:
        mismatches.append({"review_id": rid, "issue": "sentiment analyzed but not classified"})
    return mismatches
