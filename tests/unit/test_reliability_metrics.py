"""Tests for observability/metrics.py — reliability calculator."""
from __future__ import annotations

import pytest

from small_shop_agent.observability.metrics import compute_metrics, ReliabilityMetrics
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.storage.repositories.memory_repository import MemoryRepository

BID = "test-batch-metrics"


@pytest.fixture
def _seed_metrics_db(temp_db):
    BatchRepository().create_batch(batch_id=BID, total_rows=2, valid_review_count=2)
    ReviewRepository().bulk_insert_reviews(BID, [
        {"review_id": "R1", "rating": 1, "review_text": "bad"},
        {"review_id": "R2", "rating": 3, "review_text": "ok"},
    ])
    ReplyRepository().bulk_insert_drafts(BID, [
        {"review_id": "R1", "original_review": "bad", "draft_text": "We will improve.",
         "safety_status": "pass", "risk_types": [], "approval_status": "pending", "model_name": "t"},
        {"review_id": "R2", "original_review": "ok", "draft_text": "Thanks.",
         "safety_status": "blocked", "risk_types": ["fake_fact"], "approval_status": "pending", "model_name": "t"},
    ])
    tr = TraceRepository()
    tr.log_step(trace_id="t1", batch_id=BID, step_name="classification",
                status="passed", input_summary="2 reviews", output_summary="2 classified",
                latency_ms=50, model_name="test")
    tr.log_step(trace_id="t2", batch_id=BID, step_name="sentiment_analysis",
                status="passed", input_summary="2 reviews",
                output_summary="used_fallback=True | schema_errors_count=1",
                latency_ms=30, model_name="test")
    tr.log_step(trace_id="t3", batch_id=BID, step_name="reply_drafting_prep",
                status="passed", input_summary="1 candidates",
                output_summary="memory_hits=2, blocked_rules=1",
                latency_ms=0, model_name="test")


class TestReliabilityMetrics:
    def test_empty_batch_returns_zeros(self, temp_db):
        m = compute_metrics("nonexistent-batch")
        assert m.trace_count == 0
        assert m.total_latency_ms == 0
        assert m.fallback_rate == 0.0

    def test_latency_sums_correctly(self, temp_db, _seed_metrics_db):
        m = compute_metrics(BID)
        assert m.trace_count == 3
        assert m.total_latency_ms == 80

    def test_fallback_detected(self, temp_db, _seed_metrics_db):
        m = compute_metrics(BID)
        assert m.fallback_count >= 1
        assert m.fallback_rate > 0

    def test_schema_retry_detected(self, temp_db, _seed_metrics_db):
        m = compute_metrics(BID)
        assert m.schema_retry_count >= 1

    def test_safety_block_rate(self, temp_db, _seed_metrics_db):
        m = compute_metrics(BID)
        assert m.safety_block_count == 1
        assert m.safety_block_rate == 0.5

    def test_memory_hit_detected(self, temp_db, _seed_metrics_db):
        m = compute_metrics(BID)
        assert m.memory_hit_count == 2

    def test_rate_fields_in_range(self, temp_db, _seed_metrics_db):
        m = compute_metrics(BID)
        assert 0.0 <= m.fallback_rate <= 1.0
        assert 0.0 <= m.safety_block_rate <= 1.0
        assert 0.0 <= m.human_edit_rate <= 1.0
        assert 0.0 <= m.memory_hit_rate <= 1.0
