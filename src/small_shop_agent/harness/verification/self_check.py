"""Self-check utilities — detect internal contradictions in LLM outputs."""
from __future__ import annotations

from typing import Any


def detect_sentiment_rating_conflict(
    sentiments: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flag reviews where sentiment contradicts the rating score.

    e.g. rating=5 but sentiment='negative' → likely LLM error.
    """
    review_ratings = {r["review_id"]: int(r.get("rating", 3)) for r in reviews}
    conflicts: list[dict[str, Any]] = []
    for s in sentiments:
        rid = s["review_id"]
        rating = review_ratings.get(rid, 3)
        sentiment = s.get("sentiment", "neutral")
        if rating >= 4 and sentiment == "negative":
            conflicts.append({
                "review_id": rid, "rating": rating, "sentiment": sentiment,
                "issue": "High rating but negative sentiment — possible misclassification.",
            })
        elif rating <= 2 and sentiment == "positive":
            conflicts.append({
                "review_id": rid, "rating": rating, "sentiment": sentiment,
                "issue": "Low rating but positive sentiment — possible misclassification.",
            })
    return conflicts
