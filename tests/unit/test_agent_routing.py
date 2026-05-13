"""Tests for agent_runtime/graph/edges.py — conditional routing logic."""
from __future__ import annotations

from copy import deepcopy

from small_shop_agent.agent_runtime.graph.edges import (
    route,
    END,
    route_after_classification,
    route_after_classification_retry,
    route_after_fallback_classification,
    route_after_sentiment,
    route_after_sentiment_retry,
    route_after_fallback_sentiment,
    route_after_consistency,
    route_after_evidence,
    route_after_regenerate_insight,
    route_after_mark_insufficient,
    route_after_safety,
    route_after_approval,
)


def _base_state(**overrides):
    s = {
        "batch_id": "b1", "mode": "demo", "model_name": "demo",
        "reviews": [],
        "classifications": [],
        "sentiments": [],
        "analysis_rows": [],
        "insights": [],
        "reply_drafts": [],
        "safety_results": [],
        "warnings": [],
        "errors": [],
        "fallback_used": False,
        "need_human_review": False,
        "current_step": "init",
        "_retry_counts": {},
        "_evidence_count": 0,
        "_blocked_count": 0,
    }
    s.update(overrides)
    return s


class TestClassificationRoutes:
    def test_empty_results_goes_to_retry(self):
        state = _base_state(current_step="classification", classifications=[])
        assert route_after_classification(state) == "classification_retry"

    def test_has_results_goes_to_sentiment(self):
        state = _base_state(current_step="classification",
                           classifications=[{"review_id": "A"}])
        assert route_after_classification(state) == "sentiment"

    def test_retry_exhausted_goes_to_fallback(self):
        state = _base_state(current_step="classification",
                           classifications=[],
                           _retry_counts={"classification": 1})
        assert route_after_classification(state) == "fallback_classification"

    def test_retry_failed_goes_to_fallback(self):
        state = _base_state(current_step="classification_retry",
                           classifications=[])
        assert route_after_classification_retry(state) == "fallback_classification"

    def test_retry_succeeded_goes_to_sentiment(self):
        state = _base_state(current_step="classification_retry",
                           classifications=[{"review_id": "A"}])
        assert route_after_classification_retry(state) == "sentiment"

    def test_fallback_classification_goes_to_sentiment(self):
        state = _base_state(current_step="fallback_classification")
        assert route_after_fallback_classification(state) == "sentiment"


class TestSentimentRoutes:
    def test_empty_goes_to_retry(self):
        state = _base_state(current_step="sentiment", sentiments=[])
        assert route_after_sentiment(state) == "sentiment_retry"

    def test_has_results_goes_to_consistency(self):
        state = _base_state(current_step="sentiment",
                           sentiments=[{"review_id": "A"}])
        assert route_after_sentiment(state) == "consistency"

    def test_retry_exhausted_goes_to_fallback(self):
        state = _base_state(current_step="sentiment",
                           sentiments=[],
                           _retry_counts={"sentiment": 1})
        assert route_after_sentiment(state) == "fallback_sentiment"

    def test_retry_failed_goes_to_fallback(self):
        state = _base_state(current_step="sentiment_retry", sentiments=[])
        assert route_after_sentiment_retry(state) == "fallback_sentiment"

    def test_retry_succeeded_goes_to_consistency(self):
        state = _base_state(current_step="sentiment_retry",
                           sentiments=[{"review_id": "A"}])
        assert route_after_sentiment_retry(state) == "consistency"

    def test_fallback_sentiment_goes_to_consistency(self):
        state = _base_state(current_step="fallback_sentiment")
        assert route_after_fallback_sentiment(state) == "consistency"


class TestConsistencyRoute:
    def test_goes_to_merge(self):
        state = _base_state(current_step="consistency")
        assert route_after_consistency(state) == "merge"


class TestEvidenceRoutes:
    def test_no_evidence_goes_to_regenerate(self):
        state = _base_state(current_step="evidence", _evidence_count=0)
        assert route_after_evidence(state) == "regenerate_insight"

    def test_has_evidence_goes_to_reply(self):
        state = _base_state(current_step="evidence", _evidence_count=3)
        assert route_after_evidence(state) == "reply"

    def test_retry_exhausted_goes_to_mark_insufficient(self):
        state = _base_state(current_step="evidence",
                           _evidence_count=0,
                           _retry_counts={"evidence": 1})
        assert route_after_evidence(state) == "mark_insight_insufficient"

    def test_regenerate_still_zero_goes_to_mark(self):
        state = _base_state(current_step="regenerate_insight",
                           _evidence_count=0)
        assert route_after_regenerate_insight(state) == "mark_insight_insufficient"

    def test_regenerate_succeeded_goes_to_reply(self):
        state = _base_state(current_step="regenerate_insight",
                           _evidence_count=2)
        assert route_after_regenerate_insight(state) == "reply"

    def test_mark_insufficient_goes_to_reply(self):
        state = _base_state(current_step="mark_insight_insufficient")
        assert route_after_mark_insufficient(state) == "reply"


class TestSafetyRoutes:
    def test_blocked_goes_to_approval_with_human_review(self):
        state = _base_state(current_step="safety", _blocked_count=1,
                           need_human_review=False)
        result = route_after_safety(state)
        assert result == "approval"
        assert state["need_human_review"] is True

    def test_all_pass_goes_to_approval(self):
        state = _base_state(current_step="safety", _blocked_count=0,
                           need_human_review=False)
        result = route_after_safety(state)
        assert result == "approval"
        assert state["need_human_review"] is False


class TestApprovalRoute:
    def test_goes_to_end(self):
        state = _base_state(current_step="approval")
        assert route_after_approval(state) == END


class TestTopLevelRoute:
    def test_route_dispatches_classification(self):
        state = _base_state(current_step="classification",
                           classifications=[{"review_id": "A"}])
        assert route(state) == "sentiment"

    def test_route_dispatches_empty_classification(self):
        state = _base_state(current_step="classification", classifications=[])
        assert route(state) == "classification_retry"

    def test_route_dispatches_approval_to_end(self):
        state = _base_state(current_step="approval")
        assert route(state) == END

    def test_route_unknown_step_returns_end(self):
        state = _base_state(current_step="nonexistent_node")
        assert route(state) == END
