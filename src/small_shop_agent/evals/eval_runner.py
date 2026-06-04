"""EvalRunner -- orchestrates all scorers (incl. red-team) and produces a unified eval report with historical comparison."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from small_shop_agent.evals.scorers.topic_accuracy import score_topic_accuracy
from small_shop_agent.evals.scorers.sentiment_accuracy import score_sentiment_accuracy
from small_shop_agent.evals.scorers.safety_score import score_safety
from small_shop_agent.evals.scorers.schema_stability import score_schema_stability
from small_shop_agent.evals.scorers.red_team_safety import score_red_team_safety


def run_full_eval(
    analysis: list[dict[str, Any]],
    drafts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    topic_ground_truth: dict[str, str],
    sentiment_ground_truth: dict[str, str],
    red_team_cases: list[dict[str, Any]] | None = None,
    previous_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run all scorers and return a unified eval report with historical comparison."""
    topic = score_topic_accuracy(analysis, topic_ground_truth)
    sentiment = score_sentiment_accuracy(analysis, sentiment_ground_truth)
    safety = score_safety(drafts)
    stability = score_schema_stability(traces)
    red_team = score_red_team_safety(cases=red_team_cases)

    report: dict[str, Any] = {
        "topic_accuracy": topic["accuracy"],
        "sentiment_accuracy": sentiment["accuracy"],
        "unsafe_reply_count": safety["unsafe_reply_count"],
        "schema_failure_count": stability["schema_failure_count"],
        "total_eval_cases": topic["total"],
        "topic_correct_count": topic["correct_count"],
        "sentiment_correct_count": sentiment["correct_count"],
        "red_team_recall": red_team["recall"],
        "red_team_precision": red_team["precision"],
        "red_team_false_negative": red_team["false_negative"],
        "red_team_total": red_team["total"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {
            "topic": topic,
            "sentiment": sentiment,
            "safety": safety,
            "schema_stability": stability,
            "red_team": red_team,
        },
    }

    if previous_results:
        report["trend"] = _compute_trend(report, previous_results)

    return report


def _compute_trend(
    current: dict[str, Any],
    previous: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare current metrics against the previous run."""
    if not previous:
        return {"message": "no previous data for comparison"}
    prev = previous[0]

    def _delta(cur_key: str, prev_key: str | None = None) -> float | None:
        pv = prev.get(prev_key or cur_key)
        cv = current.get(cur_key)
        if pv is None or cv is None:
            return None
        try:
            return round(float(cv) - float(pv), 4)
        except (TypeError, ValueError):
            return None

    return {
        "previous_run_id": prev.get("eval_run_id", "unknown"),
        "previous_timestamp": prev.get("timestamp", ""),
        "deltas": {
            "topic_accuracy": _delta("topic_accuracy"),
            "sentiment_accuracy": _delta("sentiment_accuracy"),
            "unsafe_reply_count": _delta("unsafe_reply_count"),
            "schema_failure_count": _delta("schema_failure_count"),
            "red_team_recall": _delta("red_team_recall"),
            "red_team_precision": _delta("red_team_precision"),
        },
    }
