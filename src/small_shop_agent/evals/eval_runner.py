"""EvalRunner — orchestrates all scorers and produces a unified eval report."""
from __future__ import annotations

from typing import Any

from small_shop_agent.evals.scorers.topic_accuracy import score_topic_accuracy
from small_shop_agent.evals.scorers.sentiment_accuracy import score_sentiment_accuracy
from small_shop_agent.evals.scorers.safety_score import score_safety
from small_shop_agent.evals.scorers.schema_stability import score_schema_stability


def run_full_eval(
    analysis: list[dict[str, Any]],
    drafts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    topic_ground_truth: dict[str, str],
    sentiment_ground_truth: dict[str, str],
) -> dict[str, Any]:
    """Run all scorers and return a unified eval report."""
    topic = score_topic_accuracy(analysis, topic_ground_truth)
    sentiment = score_sentiment_accuracy(analysis, sentiment_ground_truth)
    safety = score_safety(drafts)
    stability = score_schema_stability(traces)

    return {
        "topic_accuracy": topic["accuracy"],
        "sentiment_accuracy": sentiment["accuracy"],
        "unsafe_reply_count": safety["unsafe_reply_count"],
        "schema_failure_count": stability["schema_failure_count"],
        "total_eval_cases": topic["total"],
        "topic_correct_count": topic["correct_count"],
        "sentiment_correct_count": sentiment["correct_count"],
        "details": {
            "topic": topic,
            "sentiment": sentiment,
            "safety": safety,
            "schema_stability": stability,
        },
    }
