"""EvalService — rule-based evaluation pipeline for workflow outputs."""
from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from small_shop_agent.storage.repositories.eval_repository import EvalRepository
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.evals.eval_runner import run_full_eval
from small_shop_agent.demo.demo_loader import DemoLoader
from small_shop_agent.harness.verification.fallback_rules import classify_by_keywords
from small_shop_agent.services.types import EvalResult


def _rule_topic(review: dict) -> str:
    """Keyword-based topic classification fallback for eval ground truth."""
    text = str(review.get("review_text", review.get("cleaned_text", "")))
    rating = int(review.get("rating", 3))
    return classify_by_keywords(text, rating)


def _rule_sentiment(review: dict) -> str:
    """Rating-based sentiment fallback for eval ground truth."""
    rating = int(review.get("rating", 3))
    if rating <= 2:
        return "negative"
    if rating == 3:
        return "neutral"
    return "positive"


class EvalService:
    """Runs rule-based evaluations against workflow outputs and persists results."""

    def __init__(self) -> None:
        self._eval_repo = EvalRepository()
        self._batch_repo = BatchRepository()
        self._analysis_repo = AnalysisRepository()
        self._reply_repo = ReplyRepository()
        self._trace_repo = TraceRepository()
        self._review_repo = ReviewRepository()
        self._demo_loader = DemoLoader()

    def run_eval(self, eval_config: dict[str, Any] | None = None) -> EvalResult:
        """
        Run rule-based evaluation against the latest analyzed batch.

        eval_config can optionally specify:
        - batch_id: target a specific batch
        - eval_run_id: custom eval run identifier
        """
        config = eval_config or {}
        batch_id = config.get("batch_id")

        # Resolve batch
        if batch_id:
            batch = self._batch_repo.get_batch(batch_id)
        else:
            batch = self._batch_repo.get_latest_batch()

        if batch is None:
            return {"success": False, "error": "No batch found for evaluation."}

        batch_id = batch["batch_id"]
        eval_run_id = config.get("eval_run_id", f"eval-{uuid.uuid4().hex[:8]}")

        # Gather data
        analysis = self._analysis_repo.list_analysis(batch_id)
        drafts = self._reply_repo.list_drafts(batch_id)
        traces = self._trace_repo.get_traces(batch_id)

        # Build ground truth — prefer demo mock data, fall back to rule-based
        mock_class = self._demo_loader.load_mock_classification()
        mock_sent = self._demo_loader.load_mock_sentiment()

        topic_gt: dict[str, str] = {
            e["review_id"]: e["primary_topic"] for e in mock_class
        }
        sentiment_gt: dict[str, str] = {
            e["review_id"]: e["sentiment"] for e in mock_sent
        }

        # Fill missing ground truth with rule-based defaults from review data
        reviews = self._review_repo.list_reviews(batch_id, is_valid=True)
        for r in reviews:
            rid = r["review_id"]
            if rid not in topic_gt:
                topic_gt[rid] = _rule_topic(r)
            if rid not in sentiment_gt:
                sentiment_gt[rid] = _rule_sentiment(r)

        # Run eval
        report = run_full_eval(analysis, drafts, traces, topic_gt, sentiment_gt)

        # No matching cases at all — shouldn't happen with rule-based fallback
        if report["total_eval_cases"] == 0:
            logger.warning(f"评测 {eval_run_id}：规则降级后评测案例为 0。")
            return {
                "success": False,
                "eval_run_id": eval_run_id,
                "batch_id": batch_id,
                "report": report,
                "error": "无法生成评测基准数据，请检查评论数据是否有效。",
            }

        # Persist to DB
        self._eval_repo.save_eval_result(
            eval_run_id=eval_run_id,
            batch_id=batch_id,
            topic_accuracy=report["topic_accuracy"],
            sentiment_accuracy=report["sentiment_accuracy"],
            unsafe_reply_count=report["unsafe_reply_count"],
            schema_failure_count=report["schema_failure_count"],
            total_eval_cases=report["total_eval_cases"],
            topic_correct_count=report["topic_correct_count"],
            sentiment_correct_count=report["sentiment_correct_count"],
        )

        # Write eval trace
        self._trace_repo.log_step(
            trace_id=f"trace-{batch_id}",
            batch_id=batch_id,
            step_name="eval_run",
            status="passed" if report["schema_failure_count"] == 0 else "warning",
            input_summary=f"{report['total_eval_cases']} cases",
            output_summary=(
                f"topic_acc={report['topic_accuracy']:.2%}, "
                f"sent_acc={report['sentiment_accuracy']:.2%}, "
                f"unsafe={report['unsafe_reply_count']}"
            ),
            latency_ms=0,
            model_name="rule_based",
        )

        logger.success(
            f"评测完成 ID={eval_run_id}："
            f"话题准确率={report['topic_accuracy']:.2%}, "
            f"情绪准确率={report['sentiment_accuracy']:.2%}"
        )

        return {
            "success": True,
            "eval_run_id": eval_run_id,
            "batch_id": batch_id,
            "report": report,
            "error": None,
        }

    def get_latest_eval(self) -> dict[str, Any] | None:
        """Return the most recent eval result."""
        return self._eval_repo.get_latest_eval()

    def list_eval_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent eval runs."""
        return self._eval_repo.list_eval_runs(limit=limit)
