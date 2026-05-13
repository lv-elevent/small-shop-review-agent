"""Tests for services/pipeline_steps.py step functions."""
from __future__ import annotations

from small_shop_agent.services.pipeline_steps import merge_classification_sentiment


class TestMergeClassificationSentiment:
    def test_both_lists_aligned(self):
        classifications = [
            {"review_id": "A", "topics": ["service"], "primary_topic": "service",
             "topic_confidence": 0.90, "needs_review": False},
        ]
        sentiments = [
            {"review_id": "A", "sentiment": "negative", "severity": 4,
             "sentiment_confidence": 0.95, "is_negative_candidate": True},
        ]
        rows = merge_classification_sentiment(classifications, sentiments)
        assert len(rows) == 1
        assert rows[0]["review_id"] == "A"
        assert rows[0]["primary_topic"] == "service"
        assert rows[0]["sentiment"] == "negative"
        assert rows[0]["is_negative_candidate"] is True
        assert rows[0]["needs_review"] is False

    def test_missing_sentiment_defaults_to_neutral(self):
        classifications = [
            {"review_id": "B", "topics": ["price"], "primary_topic": "price",
             "topic_confidence": 0.80, "needs_review": False},
        ]
        sentiments: list[dict] = []  # nothing for B
        rows = merge_classification_sentiment(classifications, sentiments)
        assert len(rows) == 1
        assert rows[0]["review_id"] == "B"
        assert rows[0]["sentiment"] == "neutral"
        assert rows[0]["severity"] == 2
        assert rows[0]["is_negative_candidate"] is False

    def test_propagates_needs_review_flag(self):
        classifications = [
            {"review_id": "C", "topics": ["hygiene"], "primary_topic": "hygiene",
             "topic_confidence": 0.70, "needs_review": True},
        ]
        sentiments = [
            {"review_id": "C", "sentiment": "negative", "severity": 5,
             "sentiment_confidence": 0.85, "is_negative_candidate": True},
        ]
        rows = merge_classification_sentiment(classifications, sentiments)
        assert rows[0]["needs_review"] is True
        assert rows[0]["is_negative_candidate"] is True

    def test_extra_sentiment_entry_ignored(self):
        """Sentiment without matching classification is silently skipped
        (merge is driven by classification list)."""
        classifications = [
            {"review_id": "D", "topics": ["product"], "primary_topic": "product",
             "topic_confidence": 0.85, "needs_review": False},
        ]
        sentiments = [
            {"review_id": "D", "sentiment": "positive", "severity": 1,
             "sentiment_confidence": 0.90, "is_negative_candidate": False},
            {"review_id": "EXTRA", "sentiment": "negative", "severity": 3,
             "sentiment_confidence": 0.80, "is_negative_candidate": True},
        ]
        rows = merge_classification_sentiment(classifications, sentiments)
        assert len(rows) == 1
        assert rows[0]["review_id"] == "D"
