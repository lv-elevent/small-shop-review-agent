"""Tests for services/eval_service.py — eval pipeline with temp DB."""
from __future__ import annotations

import pytest

from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository

BATCH_ID = "test-batch-eval"


@pytest.fixture
def _setup_eval_batch(temp_db):
    """Set up full batch with reviews, analysis, drafts, traces."""
    BatchRepository().create_batch(
        batch_id=BATCH_ID, total_rows=3, valid_review_count=3,
    )
    ReviewRepository().bulk_insert_reviews(BATCH_ID, [
        {"review_id": "EV1", "rating": 1, "review_text": "卫生太差了"},
        {"review_id": "EV2", "rating": 2, "review_text": "等太久"},
        {"review_id": "EV3", "rating": 5, "review_text": "咖啡很赞"},
    ])
    AnalysisRepository().bulk_insert_analysis(BATCH_ID, [
        {"review_id": "EV1", "topics": ["hygiene"], "primary_topic": "hygiene",
         "topic_confidence": 0.90, "needs_review": True,
         "sentiment": "negative", "severity": 5, "sentiment_confidence": 0.95,
         "is_negative_candidate": True},
        {"review_id": "EV2", "topics": ["waiting_time"], "primary_topic": "waiting_time",
         "topic_confidence": 0.85, "needs_review": True,
         "sentiment": "negative", "severity": 4, "sentiment_confidence": 0.90,
         "is_negative_candidate": True},
        {"review_id": "EV3", "topics": ["product"], "primary_topic": "product",
         "topic_confidence": 0.95, "needs_review": False,
         "sentiment": "positive", "severity": 1, "sentiment_confidence": 0.97,
         "is_negative_candidate": False},
    ])
    ReplyRepository().bulk_insert_drafts(BATCH_ID, [
        {"review_id": "EV1", "original_review": "卫生太差了",
         "draft_text": "我们会改进卫生。", "safety_status": "pass",
         "risk_types": [], "approval_status": "pending", "model_name": "test"},
        {"review_id": "EV2", "original_review": "等太久",
         "draft_text": "我们开除了员工。", "safety_status": "blocked",
         "risk_types": ["claim_employee_punished"],
         "approval_status": "pending", "model_name": "test"},
    ])
    TraceRepository().log_step(
        trace_id=f"trace-{BATCH_ID}", batch_id=BATCH_ID,
        step_name="classification", status="passed",
        input_summary="3 reviews", output_summary="3 classified",
        latency_ms=10, model_name="test",
    )


class TestEvalService:
    def test_run_eval_success(self, temp_db, _setup_eval_batch):
        svc = EvalService()
        result = svc.run_eval({"batch_id": BATCH_ID})
        assert result["success"] is True
        assert result["batch_id"] == BATCH_ID
        assert bool(result["eval_run_id"])
        report = result["report"]
        assert report["total_eval_cases"] > 0
        assert 0.0 <= report["topic_accuracy"] <= 1.0
        assert 0.0 <= report["sentiment_accuracy"] <= 1.0
        assert report["unsafe_reply_count"] >= 0

    def test_eval_results_persisted(self, temp_db, _setup_eval_batch):
        svc = EvalService()
        result = svc.run_eval({"batch_id": BATCH_ID})

        from small_shop_agent.storage.sqlite_session import get_session
        with get_session() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM eval_results WHERE batch_id = ?",
                (BATCH_ID,),
            ).fetchone()
        assert row["cnt"] == 1

    def test_run_eval_no_batch_fails(self, temp_db):
        svc = EvalService()
        result = svc.run_eval({"batch_id": "nonexistent-batch"})
        assert result["success"] is False
        assert result.get("error") is not None
