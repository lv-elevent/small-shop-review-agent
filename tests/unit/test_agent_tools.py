"""Tests for agent_runtime/tools.py — read-only business tools."""
from __future__ import annotations

import pytest

from small_shop_agent.agent_runtime.tools import (
    lookup_review,
    search_reviews,
    count_by_topic,
    get_batch_stats,
    get_safety_policy_snippet,
)
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository

BATCH_ID = "test-batch-tools"


@pytest.fixture
def _setup_tools_db(temp_db):
    """Insert one batch, three reviews, and three analysis rows."""
    BatchRepository().create_batch(
        batch_id=BATCH_ID, total_rows=3, valid_review_count=3,
    )
    ReviewRepository().bulk_insert_reviews(BATCH_ID, [
        {"review_id": "R1", "rating": 1, "review_text": "咖啡太难喝了"},
        {"review_id": "R2", "rating": 2, "review_text": "等待时间太长"},
        {"review_id": "R3", "rating": 5, "review_text": "咖啡很赞，服务好"},
    ])
    AnalysisRepository().bulk_insert_analysis(BATCH_ID, [
        {"review_id": "R1", "topics": ["product"], "primary_topic": "product",
         "topic_confidence": 0.90, "needs_review": True,
         "sentiment": "negative", "severity": 5, "sentiment_confidence": 0.95,
         "is_negative_candidate": True},
        {"review_id": "R2", "topics": ["waiting_time"], "primary_topic": "waiting_time",
         "topic_confidence": 0.85, "needs_review": True,
         "sentiment": "negative", "severity": 4, "sentiment_confidence": 0.90,
         "is_negative_candidate": True},
        {"review_id": "R3", "topics": ["product"], "primary_topic": "product",
         "topic_confidence": 0.95, "needs_review": False,
         "sentiment": "positive", "severity": 1, "sentiment_confidence": 0.97,
         "is_negative_candidate": False},
    ])


class TestLookupReview:
    def test_found(self, temp_db, _setup_tools_db):
        result = lookup_review(review_id="R1", batch_id=BATCH_ID, trace=False)
        assert result["success"] is True
        assert result["found"] is True
        assert result["review"]["review_id"] == "R1"
        assert result["review"]["rating"] == 1
        assert "咖啡太难喝" in result["review"]["review_text"]

    def test_not_found(self, temp_db, _setup_tools_db):
        result = lookup_review(review_id="NONE", batch_id=BATCH_ID, trace=False)
        assert result["success"] is True
        assert result["found"] is False
        assert result["review"] is None


class TestSearchReviews:
    def test_matches(self, temp_db, _setup_tools_db):
        result = search_reviews(keyword="咖啡", batch_id=BATCH_ID, trace=False)
        assert result["success"] is True
        assert result["count"] >= 2  # R1 and R3 both have 咖啡
        matched_ids = {m["review_id"] for m in result["matches"]}
        assert "R1" in matched_ids
        assert "R3" in matched_ids

    def test_no_match(self, temp_db, _setup_tools_db):
        result = search_reviews(keyword="ZZZNOTEXIST", batch_id=BATCH_ID, trace=False)
        assert result["success"] is True
        assert result["count"] == 0
        assert result["matches"] == []

    def test_respects_limit(self, temp_db, _setup_tools_db):
        result = search_reviews(keyword="咖啡", batch_id=BATCH_ID, limit=1, trace=False)
        assert result["count"] == 1
        assert len(result["matches"]) == 1


class TestCountByTopic:
    def test_has_count(self, temp_db, _setup_tools_db):
        result = count_by_topic(topic="product", batch_id=BATCH_ID, trace=False)
        assert result["success"] is True
        assert result["count"] == 2

    def test_zero(self, temp_db, _setup_tools_db):
        result = count_by_topic(topic="hygiene", batch_id=BATCH_ID, trace=False)
        assert result["success"] is True
        assert result["count"] == 0

    def test_waiting_time(self, temp_db, _setup_tools_db):
        result = count_by_topic(topic="waiting_time", batch_id=BATCH_ID, trace=False)
        assert result["count"] == 1


class TestBatchStats:
    def test_aggregates(self, temp_db, _setup_tools_db):
        result = get_batch_stats(batch_id=BATCH_ID, trace=False)
        assert result["success"] is True
        s = result["stats"]
        assert s["total_reviews"] == 3
        assert s["valid_reviews"] == 3
        assert s["negative_count"] == 2
        assert s["positive_count"] == 1

    def test_nonexistent_batch(self, temp_db):
        result = get_batch_stats(batch_id="no-such-batch", trace=False)
        assert result["success"] is False
        assert "not found" in str(result["error"]).lower()


class TestSafetyPolicySnippet:
    def test_blocked(self):
        result = get_safety_policy_snippet(policy_type="blocked", trace=False)
        assert result["success"] is True
        assert "attack_customer" in result["patterns"]
        assert "fabricated_fact" in result["patterns"]
        assert "attack_customer" in result["reasons"]

    def test_rewrite(self):
        result = get_safety_policy_snippet(policy_type="rewrite", trace=False)
        assert result["success"] is True
        assert "over_marketing" in result["patterns"]
        assert "unfounded_compensation" in result["patterns"]
        assert "defensive_or_blame_shift" in result["patterns"]

    def test_all(self):
        result = get_safety_policy_snippet(policy_type="all", trace=False)
        assert result["success"] is True
        # "all" includes both blocked and rewrite
        assert "attack_customer" in result["patterns"]
        assert "over_marketing" in result["patterns"]

    def test_unknown_type(self):
        result = get_safety_policy_snippet(policy_type="invalid", trace=False)
        assert result["success"] is False
        assert "Unknown policy_type" in result["error"]
