"""Tests for harness/verification/ consistency_check and self_check integration."""
from __future__ import annotations

from unittest.mock import MagicMock


def _make_trace_repo():
    """Minimal mock trace_repo that records log_step calls."""
    repo = MagicMock()
    return repo


# ── Unit: detection functions ──────────────────────────────────────────

class TestDetectionFunctions:
    def test_detect_sentiment_rating_conflict_low_rating_positive(self):
        from small_shop_agent.harness.verification.self_check import (
            detect_sentiment_rating_conflict,
        )
        sentiments = [
            {"review_id": "R1", "sentiment": "positive"},
            {"review_id": "R2", "sentiment": "negative"},
        ]
        reviews = [
            {"review_id": "R1", "rating": 1},  # low rating + positive → conflict
            {"review_id": "R2", "rating": 2},  # low rating + negative → ok
        ]
        conflicts = detect_sentiment_rating_conflict(sentiments, reviews)
        assert len(conflicts) == 1
        assert conflicts[0]["review_id"] == "R1"
        assert "Low rating but positive sentiment" in conflicts[0]["issue"]

    def test_detect_sentiment_rating_conflict_high_rating_negative(self):
        from small_shop_agent.harness.verification.self_check import (
            detect_sentiment_rating_conflict,
        )
        sentiments = [
            {"review_id": "R1", "sentiment": "negative"},
            {"review_id": "R2", "sentiment": "positive"},
        ]
        reviews = [
            {"review_id": "R1", "rating": 5},  # high rating + negative → conflict
            {"review_id": "R2", "rating": 4},  # high rating + positive → ok
        ]
        conflicts = detect_sentiment_rating_conflict(sentiments, reviews)
        assert len(conflicts) == 1
        assert conflicts[0]["review_id"] == "R1"

    def test_detect_sentiment_rating_conflict_no_conflict(self):
        from small_shop_agent.harness.verification.self_check import (
            detect_sentiment_rating_conflict,
        )
        sentiments = [
            {"review_id": "R1", "sentiment": "negative"},
            {"review_id": "R2", "sentiment": "positive"},
            {"review_id": "R3", "sentiment": "neutral"},
        ]
        reviews = [
            {"review_id": "R1", "rating": 1},  # low + negative → ok
            {"review_id": "R2", "rating": 5},  # high + positive → ok
            {"review_id": "R3", "rating": 3},  # mid + neutral → ok
        ]
        conflicts = detect_sentiment_rating_conflict(sentiments, reviews)
        assert len(conflicts) == 0


class TestAlignmentCheck:
    def test_classification_sentiment_mismatch(self):
        from small_shop_agent.harness.verification.consistency_check import (
            check_classification_sentiment_alignment,
        )
        classifications = [
            {"review_id": "A"}, {"review_id": "B"}, {"review_id": "C"},
        ]
        sentiments = [
            {"review_id": "A"}, {"review_id": "C"},
        ]
        mismatches = check_classification_sentiment_alignment(classifications, sentiments)
        assert len(mismatches) == 1
        assert mismatches[0]["review_id"] == "B"
        assert "classified but not analyzed" in mismatches[0]["issue"]

    def test_sentiment_without_classification(self):
        from small_shop_agent.harness.verification.consistency_check import (
            check_classification_sentiment_alignment,
        )
        classifications = [
            {"review_id": "A"},
        ]
        sentiments = [
            {"review_id": "A"}, {"review_id": "D"},
        ]
        mismatches = check_classification_sentiment_alignment(classifications, sentiments)
        assert len(mismatches) == 1
        assert mismatches[0]["review_id"] == "D"
        assert "sentiment analyzed but not classified" in mismatches[0]["issue"]

    def test_no_mismatch(self):
        from small_shop_agent.harness.verification.consistency_check import (
            check_classification_sentiment_alignment,
        )
        classifications = [{"review_id": "A"}, {"review_id": "B"}]
        sentiments = [{"review_id": "A"}, {"review_id": "B"}]
        mismatches = check_classification_sentiment_alignment(classifications, sentiments)
        assert len(mismatches) == 0


# ── Integration: pipeline step ─────────────────────────────────────────

class TestRunConsistencyCheck:
    def test_no_conflict_passes_and_no_mutation(self):
        from small_shop_agent.services.pipeline_steps import run_consistency_check

        classifications = [
            {"review_id": "A", "primary_topic": "service", "topic_confidence": 0.90, "needs_review": False},
        ]
        sentiments = [
            {"review_id": "A", "sentiment": "negative", "sentiment_confidence": 0.95},
        ]
        review_dicts = [
            {"review_id": "A", "rating": 1, "review_text": "bad"},
        ]
        trace_repo = _make_trace_repo()

        run_consistency_check(
            classifications, sentiments, review_dicts,
            batch_id="b1", trace_id="t1", mode="test",
            model_name="test", trace_repo=trace_repo,
        )

        # Trace should be logged
        assert trace_repo.log_step.call_count == 1
        call_kwargs = trace_repo.log_step.call_args.kwargs
        assert call_kwargs["step_name"] == "consistency_check"
        assert call_kwargs["status"] == "passed"

        # No mutations on clean data
        assert classifications[0]["topic_confidence"] == 0.90
        assert classifications[0]["needs_review"] is False
        assert sentiments[0]["sentiment_confidence"] == 0.95

    def test_rating_sentiment_conflict_downgrades_confidence(self):
        from small_shop_agent.services.pipeline_steps import run_consistency_check

        classifications = [
            {"review_id": "R1", "primary_topic": "service", "topic_confidence": 0.90, "needs_review": False},
        ]
        sentiments = [
            {"review_id": "R1", "sentiment": "positive", "sentiment_confidence": 0.95},
        ]
        review_dicts = [
            {"review_id": "R1", "rating": 1, "review_text": "terrible"},  # rating=1 + positive → conflict
        ]
        trace_repo = _make_trace_repo()

        run_consistency_check(
            classifications, sentiments, review_dicts,
            batch_id="b1", trace_id="t1", mode="test",
            model_name="test", trace_repo=trace_repo,
        )

        # Trace writes warning
        call_kwargs = trace_repo.log_step.call_args.kwargs
        assert call_kwargs["status"] == "warning"
        assert "1 rating/sentiment conflicts" in call_kwargs["output_summary"]

        # Confidence downgraded
        assert classifications[0]["needs_review"] is True
        assert classifications[0]["topic_confidence"] < 0.90
        assert sentiments[0]["sentiment_confidence"] < 0.95

    def test_mismatch_only_writes_warning_no_confidence_change(self):
        from small_shop_agent.services.pipeline_steps import run_consistency_check

        classifications = [
            {"review_id": "A", "primary_topic": "service", "topic_confidence": 0.85, "needs_review": False},
            {"review_id": "B", "primary_topic": "price", "topic_confidence": 0.80, "needs_review": False},
        ]
        sentiments = [
            {"review_id": "A", "sentiment": "negative", "sentiment_confidence": 0.90},
            # B missing from sentiment
        ]
        review_dicts = [
            {"review_id": "A", "rating": 2, "review_text": "not good"},
            {"review_id": "B", "rating": 3, "review_text": "ok"},
        ]
        trace_repo = _make_trace_repo()

        run_consistency_check(
            classifications, sentiments, review_dicts,
            batch_id="b1", trace_id="t1", mode="test",
            model_name="test", trace_repo=trace_repo,
        )

        call_kwargs = trace_repo.log_step.call_args.kwargs
        assert call_kwargs["status"] == "warning"
        assert "1 review_id mismatches" in call_kwargs["output_summary"]

        # Confidence NOT changed for mismatches (only for conflicts)
        assert classifications[0]["topic_confidence"] == 0.85
        assert classifications[1]["topic_confidence"] == 0.80

    def test_both_conflict_and_mismatch(self):
        from small_shop_agent.services.pipeline_steps import run_consistency_check

        classifications = [
            {"review_id": "R1", "primary_topic": "service", "topic_confidence": 0.90, "needs_review": False},
            {"review_id": "R2", "primary_topic": "price", "topic_confidence": 0.85, "needs_review": False},
        ]
        sentiments = [
            {"review_id": "R1", "sentiment": "positive", "sentiment_confidence": 0.95},
            # R2 is in classification but not sentiment → mismatch
        ]
        review_dicts = [
            {"review_id": "R1", "rating": 1, "review_text": "worst"},  # conflict: low rating + positive
            {"review_id": "R2", "rating": 3, "review_text": "ok"},
        ]
        trace_repo = _make_trace_repo()

        run_consistency_check(
            classifications, sentiments, review_dicts,
            batch_id="b1", trace_id="t1", mode="test",
            model_name="test", trace_repo=trace_repo,
        )

        call_kwargs = trace_repo.log_step.call_args.kwargs
        assert call_kwargs["status"] == "warning"
        assert "1 rating/sentiment conflicts" in call_kwargs["output_summary"]
        assert "1 review_id mismatches" in call_kwargs["output_summary"]

        # R1: conflict → downgrade
        assert classifications[0]["needs_review"] is True

        # R2: mismatch only → no downgrade
        assert classifications[1]["needs_review"] is False
