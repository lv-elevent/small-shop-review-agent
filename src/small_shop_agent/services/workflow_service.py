"""WorkflowService — orchestrates the end-to-end review analysis pipeline."""
from __future__ import annotations

import time
from typing import Any

from loguru import logger

from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.repositories.insight_repository import InsightRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.demo.demo_loader import DemoLoader
from small_shop_agent.llm.mock_provider import MockProvider


class WorkflowService:
    """Orchestrates the full analysis pipeline: classify → sentiment → insights → replies → safety."""

    def __init__(self) -> None:
        self._batch_repo = BatchRepository()
        self._review_repo = ReviewRepository()
        self._analysis_repo = AnalysisRepository()
        self._insight_repo = InsightRepository()
        self._reply_repo = ReplyRepository()
        self._trace_repo = TraceRepository()
        self._demo_loader = DemoLoader()
        self._mock = MockProvider(self._demo_loader)

    # ── Public API ──────────────────────────────────────────────────────────

    def run_analysis(self, batch_id: str, mode: str = "demo") -> dict[str, Any]:
        """Run the analysis pipeline. Currently only 'demo' mode is supported."""
        if mode == "demo":
            return self.run_demo_analysis(batch_id)
        return {
            "success": False,
            "batch_id": batch_id,
            "mode": mode,
            "summary": {},
            "error": f"Unsupported mode: {mode}",
        }

    def run_demo_analysis(self, batch_id: str) -> dict[str, Any]:
        """
        Execute the full demo analysis pipeline:

        1. Validate batch exists and has valid reviews
        2. Classify reviews
        3. Analyze sentiment
        4. Aggregate top 3 issues with evidence
        5. Draft replies for negative candidates
        6. Safety check all drafts
        7. Write all results + traces to DB
        """
        t_start = time.time()
        trace_id = f"trace-{batch_id}"

        # ── Step 0: Validate batch ──────────────────────────────────────
        batch = self._batch_repo.get_batch(batch_id)
        if batch is None:
            return {
                "success": False,
                "batch_id": batch_id,
                "mode": "demo",
                "summary": {},
                "error": f"Batch not found: {batch_id}",
            }

        reviews = self._review_repo.list_reviews(batch_id, is_valid=True)
        if not reviews:
            self._batch_repo.update_status(batch_id, "failed",
                                           error_message="No valid reviews to analyze.")
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="classification", status="failed",
                input_summary="0 valid reviews",
                output_summary="",
                error_message="No valid reviews found for analysis.",
                latency_ms=0, model_name="demo",
            )
            return {
                "success": False,
                "batch_id": batch_id,
                "mode": "demo",
                "summary": {"review_count": 0},
                "error": "No valid reviews to analyze.",
            }

        review_count = len(reviews)
        self._batch_repo.update_status(batch_id, "analyzing")

        # Convert sqlite3.Row to plain dicts for MockProvider
        review_dicts: list[dict[str, Any]] = [dict(r) for r in reviews]

        try:
            # ── Step 1: Classification ──────────────────────────────────
            t1 = time.time()
            classifications = self._mock.classify_reviews(review_dicts)
            cls_latency = int((time.time() - t1) * 1000)
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="classification", status="passed",
                input_summary=f"{review_count} reviews",
                output_summary=f"{len(classifications)} classified",
                latency_ms=cls_latency, model_name="demo",
            )

            # ── Step 2: Sentiment Analysis ──────────────────────────────
            t2 = time.time()
            sentiments = self._mock.analyze_sentiment(review_dicts)
            sent_latency = int((time.time() - t2) * 1000)
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="sentiment_analysis", status="passed",
                input_summary=f"{review_count} reviews",
                output_summary=f"{len(sentiments)} analyzed",
                latency_ms=sent_latency, model_name="demo",
            )

            # ── Merge classification + sentiment → review_analysis ─────
            sent_map = {s["review_id"]: s for s in sentiments}
            analysis_rows: list[dict[str, Any]] = []
            for c in classifications:
                rid = c["review_id"]
                s = sent_map.get(rid, {})
                analysis_rows.append({
                    "review_id": rid,
                    "topics": c.get("topics", []),
                    "primary_topic": c.get("primary_topic", "other"),
                    "topic_confidence": c.get("topic_confidence", 0.80),
                    "needs_review": c.get("needs_review", False),
                    "sentiment": s.get("sentiment", "neutral"),
                    "severity": s.get("severity", 2),
                    "sentiment_confidence": s.get("sentiment_confidence", 0.80),
                    "is_negative_candidate": s.get("is_negative_candidate", False),
                })
            self._analysis_repo.bulk_insert_analysis(batch_id, analysis_rows)

            # ── Step 3: Issue Aggregation (insights + evidence) ────────
            t3 = time.time()
            insights = self._mock.generate_insights(review_dicts, analysis_rows)
            insight_count = len(insights)
            negative_count = sum(1 for a in analysis_rows if a.get("is_negative_candidate"))

            # Write insight rows (without nested evidence)
            insight_rows: list[dict[str, Any]] = []
            for ins in insights:
                insight_rows.append({
                    "rank": ins["rank"],
                    "issue_name": ins["issue_name"],
                    "issue_summary": ins.get("issue_summary", ""),
                    "topic": ins["topic"],
                    "mention_count": ins["mention_count"],
                    "severity_level": ins["severity_level"],
                    "priority_score": ins["priority_score"],
                    "suggested_action": ins["suggested_action"],
                    "evidence_count": ins.get("evidence_count", 0),
                    "evidence_status": ins.get("evidence_status", "sufficient"),
                })
            self._insight_repo.bulk_insert_insights(batch_id, insight_rows)
            ins_latency = int((time.time() - t3) * 1000)

            # Write evidence rows — resolve insight IDs from DB
            inserted_insights = self._insight_repo.get_top_issues(batch_id)
            rank_to_id: dict[int, int] = {i["rank"]: i["id"] for i in inserted_insights}

            evidence_rows: list[dict[str, Any]] = []
            for ins in insights:
                iid = rank_to_id.get(ins["rank"])
                if iid is None:
                    continue
                for ev in ins.get("evidence", []):
                    evidence_rows.append({
                        "insight_id": iid,
                        "review_id": ev["review_id"],
                        "evidence_text": ev["evidence_text"],
                        "evidence_reason": ev.get("evidence_reason", ""),
                    })
            evidence_count = len(evidence_rows)
            if evidence_rows:
                self._insight_repo.bulk_insert_evidence(batch_id, evidence_rows)

            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="issue_aggregation", status="passed",
                input_summary=f"{len(analysis_rows)} analyses",
                output_summary=f"{insight_count} insights, {evidence_count} evidence",
                latency_ms=ins_latency, model_name="demo",
            )

            # ── Step 4: Evidence Check ──────────────────────────────────
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="evidence_check", status="passed",
                input_summary=f"{insight_count} insights",
                output_summary=f"{evidence_count} evidence records across {insight_count} issues",
                latency_ms=0, model_name="demo",
            )

            # ── Step 5: Reply Drafting ──────────────────────────────────
            t5 = time.time()
            drafts = self._mock.draft_replies(review_dicts, analysis_rows)

            # Apply safety check
            safe_drafts = self._mock.check_safety(drafts)
            draft_latency = int((time.time() - t5) * 1000)

            draft_count = len(safe_drafts)
            blocked_count = sum(1 for d in safe_drafts if d.get("safety_status") == "blocked")
            rewrite_count = sum(1 for d in safe_drafts if d.get("safety_status") == "rewrite_required")
            pass_count = sum(1 for d in safe_drafts if d.get("safety_status") == "pass")

            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="reply_drafting", status="passed",
                input_summary=f"{negative_count} negative candidates",
                output_summary=f"{draft_count} drafts generated",
                latency_ms=draft_latency, model_name="demo",
            )

            # ── Step 6: Safety Check ────────────────────────────────────
            safety_status = "warning" if blocked_count > 0 else "passed"
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="safety_check", status=safety_status,
                input_summary=f"{draft_count} drafts",
                output_summary=f"{pass_count} pass, {rewrite_count} rewrite_required, {blocked_count} blocked",
                latency_ms=0, model_name="demo",
            )

            # ── Write reply_drafts to DB ────────────────────────────────
            if safe_drafts:
                draft_rows: list[dict[str, Any]] = []
                for d in safe_drafts:
                    draft_rows.append({
                        "review_id": d["review_id"],
                        "original_review": d.get("original_review", ""),
                        "draft_text": d.get("draft_text", ""),
                        "safety_status": d.get("safety_status", "pass"),
                        "risk_types": d.get("risk_types", []),
                        "approval_status": d.get("approval_status", "pending"),
                        "model_name": "demo",
                    })
                self._reply_repo.bulk_insert_drafts(batch_id, draft_rows)

            # ── Final: Update batch status ──────────────────────────────
            pending_count = sum(1 for d in safe_drafts if d.get("approval_status") == "pending")
            self._batch_repo.update_status(
                batch_id, "analyzed",
                negative_review_count=negative_count,
                pending_reply_count=pending_count,
            )

            total_latency = int((time.time() - t_start) * 1000)
            logger.success(
                f"Demo analysis complete for {batch_id}: "
                f"{review_count} reviews, {insight_count} insights, {draft_count} drafts, "
                f"{total_latency}ms"
            )

            return {
                "success": True,
                "batch_id": batch_id,
                "mode": "demo",
                "summary": {
                    "review_count": review_count,
                    "negative_count": negative_count,
                    "insight_count": insight_count,
                    "draft_count": draft_count,
                    "blocked_count": blocked_count,
                    "rewrite_count": rewrite_count,
                    "pass_count": pass_count,
                    "evidence_count": evidence_count,
                    "trace_count": 6,
                },
                "error": None,
            }

        except Exception as exc:
            logger.error(f"Demo analysis failed for {batch_id}: {exc}")
            error_msg = str(exc)
            self._batch_repo.update_status(batch_id, "failed", error_message=error_msg)
            return {
                "success": False,
                "batch_id": batch_id,
                "mode": "demo",
                "summary": {},
                "error": error_msg,
            }

    def get_workflow_status(self, batch_id: str) -> dict[str, Any]:
        """Return batch status, trace summary, and data counts."""
        batch = self._batch_repo.get_batch(batch_id)
        if batch is None:
            return {
                "success": False,
                "batch_id": batch_id,
                "batch": None,
                "traces": [],
                "counts": {},
                "error": f"Batch not found: {batch_id}",
            }

        traces = self._trace_repo.get_traces(batch_id)
        analysis_list = self._analysis_repo.list_analysis(batch_id)
        insights_list = self._insight_repo.get_top_issues(batch_id)
        drafts_list = self._reply_repo.list_drafts(batch_id)

        return {
            "success": True,
            "batch_id": batch_id,
            "batch": dict(batch),
            "traces": [dict(t) for t in traces],
            "counts": {
                "reviews": self._review_repo.count_reviews(batch_id),
                "valid_reviews": self._review_repo.count_reviews(batch_id, is_valid=True),
                "analysis": len(analysis_list),
                "insights": len(insights_list),
                "drafts": len(drafts_list),
            },
            "error": None,
        }
