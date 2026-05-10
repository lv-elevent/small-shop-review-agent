"""WorkflowService — orchestrates the end-to-end review analysis pipeline."""
from __future__ import annotations

import time
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.repositories.insight_repository import InsightRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.demo.demo_loader import DemoLoader
from small_shop_agent.llm.mock_provider import MockProvider
from small_shop_agent.llm.base import BaseLLMProvider
from small_shop_agent.harness.output.schema_guard import validate_output
from small_shop_agent.harness.output.structured_retry import run_with_schema_retry
from small_shop_agent.harness.evidence.evidence_guard import validate_insight_evidence
from small_shop_agent.harness.safety.safety_guardrails import check_many_replies
from small_shop_agent.utils.logger import log_step
from small_shop_agent.services.types import WorkflowResult, WorkflowStatusResult


# ── Private Pydantic models for schema validation (do NOT modify schemas/) ──

class _ClassificationItem(BaseModel):
    review_id: str
    topics: list[str]
    primary_topic: str
    topic_confidence: float
    needs_review: bool = False


class _SentimentItem(BaseModel):
    review_id: str
    sentiment: str
    severity: int = Field(ge=1, le=5)
    sentiment_confidence: float
    is_negative_candidate: bool = False
    analysis_reason: str = ""


class _InsightItem(BaseModel):
    rank: int
    issue_name: str
    topic: str
    issue_summary: str = ""
    mention_count: int = 0
    severity_level: str = "medium"
    priority_score: float = 0.0
    suggested_action: str = ""
    evidence_count: int = 0
    evidence_status: str = "sufficient"
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class _ReplyItem(BaseModel):
    review_id: str
    draft_text: str
    original_review: str = ""
    approval_status: str = "pending"


def _model_to_dict(model: Any) -> dict[str, Any]:
    """Convert a Pydantic model instance to a plain dict."""
    if hasattr(model, "model_dump"):
        return model.model_dump()  # pydantic v2
    return model.dict()  # pydantic v1


def _count_schema_errors(errors: list[str]) -> int:
    """Count schema validation errors (format: 'index N: ...') from retry errors."""
    return sum(1 for e in errors if e.startswith("index "))


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

    def run_analysis(self, batch_id: str, mode: str = "demo") -> WorkflowResult:
        """Run the analysis pipeline. 'demo'/'mock' uses MockProvider; 'live'/'openai' uses OpenAI."""
        if mode in ("demo", "mock"):
            return self.run_demo_analysis(batch_id)
        try:
            from small_shop_agent.llm.llm_router import get_llm_provider
            provider = get_llm_provider(mode)
        except Exception as exc:
            return {
                "success": False, "batch_id": batch_id, "mode": mode, "summary": {},
                "error": f"Failed to resolve provider for mode={mode!r}: {exc}",
            }
        return self._run_provider_analysis(batch_id, provider, mode)

    def run_demo_analysis(self, batch_id: str) -> WorkflowResult:
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
            log_step("validate_batch", batch_id, status="failed", error="Batch not found")
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
        log_step("validate_batch", batch_id, status="ok", review_count=review_count, mode="demo")
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
                output_summary=(
                    f"{len(classifications)} classified | "
                    f"provider=demo | attempts=1 | "
                    f"used_fallback=False | schema_ok=True | "
                    f"schema_errors_count=0"
                ),
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
            log_step("write_analysis_to_db", batch_id, row_count=len(analysis_rows), mode="demo")

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
            for ins in insights:
                log_step("generate_insights", batch_id, rank=ins.get("rank"),
                        issue_name=ins.get("issue_name"), topic=ins.get("topic"),
                        evidence_count=ins.get("evidence_count"), mode="demo")
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
            log_step("evidence_check", batch_id, evidence_count=evidence_count,
                    insight_count=insight_count, mode="demo")

            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="issue_aggregation", status="passed",
                input_summary=f"{len(analysis_rows)} analyses",
                output_summary=f"{insight_count} insights, {evidence_count} evidence",
                latency_ms=ins_latency, model_name="demo",
            )

            # ── Step 4: Evidence Check ──────────────────────────────────
            ev_valid = sum(1 for ins in insights if ins.get("evidence_status", "sufficient") == "sufficient")
            ev_rejected = sum(1 for ins in insights if ins.get("evidence_status") == "invalid")
            ev_insufficient = sum(1 for ins in insights if ins.get("evidence_status") == "evidence_insufficient")
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="evidence_check", status="passed",
                input_summary=f"{insight_count} insights",
                output_summary=(
                    f"{evidence_count} evidence records across {insight_count} issues | "
                    f"valid_issues_count={ev_valid} | "
                    f"rejected_issues_count={ev_rejected} | "
                    f"evidence_insufficient_count={ev_insufficient}"
                ),
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
            for d in safe_drafts:
                log_step("safety_check", batch_id, review_id=d.get("review_id"),
                        safety_status=d.get("safety_status"),
                        risk_types=d.get("risk_types", []), mode="demo")
            safety_status = "warning" if blocked_count > 0 else "passed"
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="safety_check", status=safety_status,
                input_summary=f"{draft_count} drafts",
                output_summary=(
                    f"{pass_count} pass, {rewrite_count} rewrite_required, {blocked_count} blocked | "
                    f"pass_count={pass_count} | "
                    f"rewrite_required_count={rewrite_count} | "
                    f"blocked_count={blocked_count}"
                ),
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
            log_step("write_drafts_to_db", batch_id, draft_count=draft_count, mode="demo")

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
            log_step("demo_analysis_error", batch_id, status="failed", error=str(exc), mode="demo")
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

    # ── Live Provider Analysis ───────────────────────────────────────────────

    def _run_provider_analysis(
        self, batch_id: str, provider: BaseLLMProvider, mode: str
    ) -> WorkflowResult:
        """8-step analysis pipeline wired to Schema Guard + Structured Retry +
        Evidence Guard + Safety Guardrails. Never crashes — uses fallbacks."""
        t_start = time.time()
        trace_id = f"trace-{batch_id}"
        model_name = getattr(provider, "_model", mode)
        provider._batch_id = batch_id  # wire batch_id for structured logging

        # ── Step 0: Validate batch ──────────────────────────────────
        batch = self._batch_repo.get_batch(batch_id)
        if batch is None:
            log_step("validate_batch", batch_id, status="failed", error="Batch not found", mode=mode)
            return {"success": False, "batch_id": batch_id, "mode": mode,
                    "summary": {}, "error": f"Batch not found: {batch_id}"}

        reviews = self._review_repo.list_reviews(batch_id, is_valid=True)
        if not reviews:
            log_step("validate_batch", batch_id, status="failed", error="No valid reviews", review_count=0, mode=mode)
            self._batch_repo.update_status(batch_id, "failed",
                                           error_message="No valid reviews to analyze.")
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="input_validation", status="failed",
                input_summary="0 valid reviews", output_summary="",
                error_message="No valid reviews found.", latency_ms=0,
                model_name=model_name,
            )
            return {"success": False, "batch_id": batch_id, "mode": mode,
                    "summary": {"review_count": 0}, "error": "No valid reviews to analyze."}

        review_count = len(reviews)
        log_step("validate_batch", batch_id, status="ok", review_count=review_count, mode=mode)
        self._batch_repo.update_status(batch_id, "analyzing")
        review_dicts: list[dict[str, Any]] = [dict(r) for r in reviews]

        # ── Step 1: input_validation (already done by upload) ─────────
        self._trace_repo.log_step(
            trace_id=trace_id, batch_id=batch_id,
            step_name="input_validation", status="passed",
            input_summary=f"{batch.get('total_rows', review_count)} raw reviews",
            output_summary=f"{review_count} valid reviews",
            latency_ms=0, model_name=model_name,
        )

        # ── Step 2: data_cleaning ────────────────────────────────────
        valid_review_ids = {str(r.get("review_id")) for r in review_dicts if r.get("review_id")}
        batch_reviews_all = self._review_repo.list_reviews(batch_id, is_valid=None)
        dup_count = sum(1 for r in batch_reviews_all if int(getattr(r, "is_duplicate", 0) or 0))
        empty_count = sum(1 for r in batch_reviews_all if int(getattr(r, "is_empty", 0) or 0))
        self._trace_repo.log_step(
            trace_id=trace_id, batch_id=batch_id,
            step_name="data_cleaning", status="warning" if (dup_count or empty_count) else "passed",
            input_summary=f"{len(batch_reviews_all)} raw reviews",
            output_summary=f"{review_count} valid, {empty_count} empty, {dup_count} duplicate",
            latency_ms=0, model_name=model_name,
        )

        try:
            # ── Step 3: classification ───────────────────────────────
            log_step("classification_start", batch_id, review_count=review_count, mode=mode, model=model_name)
            t3 = time.time()
            cls_retry = run_with_schema_retry(
                call_fn=lambda attempt: provider.classify_reviews(review_dicts),
                schema_cls=_ClassificationItem,
                many=True, max_retries=1,
                fallback_fn=lambda: self._fallback_classify(review_dicts),
                batch_id=batch_id,
            )
            classifications: list[dict[str, Any]]
            if isinstance(cls_retry.data, list):
                classifications = [_model_to_dict(m) for m in cls_retry.data]
            else:
                classifications = []
            cls_latency = int((time.time() - t3) * 1000)
            log_step("classification_done", batch_id,
                    classified_count=len(classifications),
                    attempts=cls_retry.attempts,
                    fallback_used=cls_retry.used_fallback,
                    schema_errors=cls_retry.errors,
                    latency_ms=cls_latency, mode=mode)
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="classification", status="warning" if cls_retry.used_fallback else "passed",
                input_summary=f"{review_count} reviews",
                output_summary=(
                    f"{len(classifications)} classified | "
                    f"provider={model_name} | "
                    f"attempts={cls_retry.attempts} | "
                    f"used_fallback={cls_retry.used_fallback} | "
                    f"schema_ok={cls_retry.ok} | "
                    f"schema_errors_count={_count_schema_errors(cls_retry.errors)}"
                ),
                latency_ms=cls_latency, model_name=model_name,
                error_message="; ".join(cls_retry.errors) if cls_retry.errors else None,
            )

            # ── Step 4: sentiment_analysis ───────────────────────────
            t4 = time.time()
            sent_retry = run_with_schema_retry(
                call_fn=lambda attempt: provider.analyze_sentiment(review_dicts),
                schema_cls=_SentimentItem,
                many=True, max_retries=1,
                fallback_fn=lambda: self._fallback_sentiment(review_dicts),
                batch_id=batch_id,
            )
            sentiments: list[dict[str, Any]]
            if isinstance(sent_retry.data, list):
                sentiments = [_model_to_dict(m) for m in sent_retry.data]
            else:
                sentiments = []
            sent_latency = int((time.time() - t4) * 1000)
            log_step("sentiment_done", batch_id,
                    analyzed_count=len(sentiments),
                    attempts=sent_retry.attempts,
                    fallback_used=sent_retry.used_fallback,
                    schema_errors=sent_retry.errors,
                    latency_ms=sent_latency, mode=mode)
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="sentiment_analysis", status="warning" if sent_retry.used_fallback else "passed",
                input_summary=f"{review_count} reviews",
                output_summary=f"{len(sentiments)} analyzed (retries={sent_retry.attempts}, fallback={sent_retry.used_fallback})",
                latency_ms=sent_latency, model_name=model_name,
                error_message="; ".join(sent_retry.errors) if sent_retry.errors else None,
            )

            # Merge classification + sentiment → analysis_rows
            sent_map: dict[str, dict[str, Any]] = {}
            for s in sentiments:
                sid = s.get("review_id", "")
                if sid:
                    sent_map[sid] = s
            analysis_rows: list[dict[str, Any]] = []
            for c in classifications:
                rid = c.get("review_id", "")
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
            if analysis_rows:
                self._analysis_repo.bulk_insert_analysis(batch_id, analysis_rows)
            log_step("write_analysis_to_db", batch_id, row_count=len(analysis_rows), mode=mode)

            # ── Step 5: issue_aggregation ────────────────────────────
            t5 = time.time()
            ins_retry = run_with_schema_retry(
                call_fn=lambda attempt: provider.generate_insights(review_dicts, analysis_rows),
                schema_cls=_InsightItem,
                many=True, max_retries=1,
                fallback_fn=lambda: self._fallback_insights(review_dicts, analysis_rows),
                batch_id=batch_id,
            )
            insights: list[dict[str, Any]]
            if isinstance(ins_retry.data, list):
                insights = [_model_to_dict(m) for m in ins_retry.data]
            else:
                insights = []
            insight_count = len(insights)
            negative_count = sum(1 for a in analysis_rows if a.get("is_negative_candidate"))

            # Write insight rows (normalize evidence_status to DB constraint)
            def _norm_evidence_status(raw: str) -> str:
                return "insufficient" if "insufficient" in raw else "sufficient"

            insight_db_rows: list[dict[str, Any]] = []
            for ins in insights:
                insight_db_rows.append({
                    "rank": ins.get("rank", 1),
                    "issue_name": ins.get("issue_name", ""),
                    "issue_summary": ins.get("issue_summary", ""),
                    "topic": ins.get("topic", "other"),
                    "mention_count": ins.get("mention_count", 0),
                    "severity_level": ins.get("severity_level", "medium"),
                    "priority_score": ins.get("priority_score", 0.0),
                    "suggested_action": ins.get("suggested_action", ""),
                    "evidence_count": ins.get("evidence_count", 0),
                    "evidence_status": _norm_evidence_status(ins.get("evidence_status", "sufficient")),
                })
            self._insight_repo.bulk_insert_insights(batch_id, insight_db_rows)
            for ins in insights:
                log_step("generate_insights", batch_id, rank=ins.get("rank"),
                        issue_name=ins.get("issue_name"), topic=ins.get("topic"),
                        evidence_count=ins.get("evidence_count"),
                        fallback_used=ins_retry.used_fallback,
                        attempts=ins_retry.attempts, mode=mode)
            ins_latency = int((time.time() - t5) * 1000)

            # ══ Step 6: evidence_check ─══════════════════════════════
            log_step("evidence_check_start", batch_id, insight_count=insight_count, mode=mode)
            evidence_result = validate_insight_evidence(insights, review_dicts, min_evidence_count=2, batch_id=batch_id)
            ecount = sum(len(ir.evidence_review_ids) for ir in evidence_result.issues)
            log_step("evidence_check_done", batch_id,
                    total_evidence=ecount,
                    valid_issues=len(evidence_result.valid_issues),
                    rejected_issues=len(evidence_result.rejected_issues),
                    mode=mode)

            # Write evidence — resolve DB insight IDs from rank
            inserted_insights = self._insight_repo.get_top_issues(batch_id)
            rank_to_iid: dict[int, int] = {i["rank"]: i["id"] for i in inserted_insights}

            evidence_db_rows: list[dict[str, Any]] = []
            for ins in insights:
                iid = rank_to_iid.get(ins.get("rank", 0))
                if iid is None:
                    continue
                for ev in ins.get("evidence", []):
                    rid = ev.get("review_id", "")
                    if rid in valid_review_ids:
                        evidence_db_rows.append({
                            "insight_id": iid,
                            "review_id": rid,
                            "evidence_text": ev.get("evidence_text", ""),
                            "evidence_reason": ev.get("evidence_reason", ""),
                        })
            if evidence_db_rows:
                self._insight_repo.bulk_insert_evidence(batch_id, evidence_db_rows)
            log_step("write_evidence_to_db", batch_id, evidence_count=len(evidence_db_rows), mode=mode)

            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="issue_aggregation", status="warning" if ins_retry.used_fallback else "passed",
                input_summary=f"{len(analysis_rows)} analyses",
                output_summary=f"{insight_count} insights (retries={ins_retry.attempts}, fallback={ins_retry.used_fallback})",
                latency_ms=ins_latency, model_name=model_name,
                error_message="; ".join(ins_retry.errors) if ins_retry.errors else None,
            )
            e_valid = len(evidence_result.valid_issues)
            e_rejected = sum(1 for ir in evidence_result.issues if ir.status == "invalid")
            e_insufficient = sum(1 for ir in evidence_result.issues if ir.status == "evidence_insufficient")
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="evidence_check", status="warning" if (e_rejected or e_insufficient) else "passed",
                input_summary=f"{insight_count} insights",
                output_summary=(
                    f"{ecount} evidence | "
                    f"valid_issues_count={e_valid} | "
                    f"rejected_issues_count={e_rejected} | "
                    f"evidence_insufficient_count={e_insufficient}"
                ),
                latency_ms=0, model_name=model_name,
            )

            # ── Step 7: reply_drafting ───────────────────────────────
            t7 = time.time()
            neg_candidates = [a for a in analysis_rows if a.get("is_negative_candidate")]
            log_step("reply_drafting_start", batch_id, negative_count=len(neg_candidates), mode=mode)
            if not neg_candidates:
                neg_candidates = [a for a in analysis_rows if a.get("severity", 2) >= 3]
            neg_ids = {a["review_id"] for a in neg_candidates}

            neg_review_dicts = [r for r in review_dicts if r.get("review_id") in neg_ids]
            neg_analyses = [a for a in analysis_rows if a.get("review_id") in neg_ids]

            reply_retry = run_with_schema_retry(
                call_fn=lambda attempt: provider.draft_replies(neg_review_dicts, neg_analyses),
                schema_cls=_ReplyItem,
                many=True, max_retries=1,
                fallback_fn=lambda: self._fallback_reply(neg_review_dicts),
                batch_id=batch_id,
            )
            drafts: list[dict[str, Any]]
            if isinstance(reply_retry.data, list):
                drafts = [_model_to_dict(m) for m in reply_retry.data]
            else:
                drafts = []
            draft_latency = int((time.time() - t7) * 1000)

            # ══ Step 8: safety_check ─═══════════════════════════════
            safe_drafts = check_many_replies(drafts, batch_id=batch_id)
            blocked_count = sum(1 for d in safe_drafts if d.get("safety_status") == "blocked")
            rewrite_count = sum(1 for d in safe_drafts if d.get("safety_status") == "rewrite_required")
            pass_count = sum(1 for d in safe_drafts if d.get("safety_status") == "pass")
            for d in safe_drafts:
                log_step("safety_check", batch_id, review_id=d.get("review_id"),
                        safety_status=d.get("safety_status"),
                        risk_types=d.get("risk_types", []), mode=mode)

            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="reply_drafting", status="warning" if reply_retry.used_fallback else "passed",
                input_summary=f"{len(neg_candidates)} negative candidates",
                output_summary=f"{len(drafts)} drafts (retries={reply_retry.attempts}, fallback={reply_retry.used_fallback})",
                latency_ms=draft_latency, model_name=model_name,
                error_message="; ".join(reply_retry.errors) if reply_retry.errors else None,
            )
            safety_trace_status = "warning" if blocked_count > 0 else "passed"
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="safety_check", status=safety_trace_status,
                input_summary=f"{len(drafts)} drafts",
                output_summary=(
                    f"{pass_count} pass, {rewrite_count} rewrite_required, {blocked_count} blocked | "
                    f"pass_count={pass_count} | "
                    f"rewrite_required_count={rewrite_count} | "
                    f"blocked_count={blocked_count}"
                ),
                latency_ms=0, model_name=model_name,
            )

            # ── Write reply_drafts to DB ─────────────────────────────
            if safe_drafts:
                draft_db_rows: list[dict[str, Any]] = []
                for d in safe_drafts:
                    draft_db_rows.append({
                        "review_id": d.get("review_id", ""),
                        "original_review": d.get("original_review", ""),
                        "draft_text": d.get("draft_text", ""),
                        "safety_status": d.get("safety_status", "pass"),
                        "risk_types": d.get("risk_types", []),
                        "approval_status": d.get("approval_status", "pending"),
                        "model_name": model_name,
                    })
                self._reply_repo.bulk_insert_drafts(batch_id, draft_db_rows)
            log_step("write_drafts_to_db", batch_id, draft_count=len(safe_drafts), mode=mode)

            # ── Final: Update batch status ───────────────────────────
            pending_count = sum(1 for d in safe_drafts if d.get("approval_status") == "pending")
            self._batch_repo.update_status(
                batch_id, "analyzed",
                negative_review_count=len(neg_candidates),
                pending_reply_count=pending_count,
            )
            total_latency = int((time.time() - t_start) * 1000)
            logger.success(
                f"Provider analysis complete for {batch_id} ({mode}): "
                f"{review_count} reviews, {insight_count} insights, {len(drafts)} drafts, "
                f"{total_latency}ms"
            )
            return {
                "success": True, "batch_id": batch_id, "mode": mode,
                "summary": {
                    "review_count": review_count,
                    "negative_count": len(neg_candidates),
                    "insight_count": insight_count,
                    "draft_count": len(drafts),
                    "blocked_count": blocked_count,
                    "rewrite_count": rewrite_count,
                    "pass_count": pass_count,
                    "evidence_count": ecount,
                    "trace_count": 8,
                },
                "error": None,
            }

        except Exception as exc:
            log_step("provider_analysis_error", batch_id, status="failed", error=str(exc), mode=mode)
            logger.error(f"Provider analysis failed for {batch_id}: {exc}")
            self._batch_repo.update_status(batch_id, "failed", error_message=str(exc))
            return {"success": False, "batch_id": batch_id, "mode": mode,
                    "summary": {}, "error": str(exc)}

    # ── Fallback Rules ──────────────────────────────────────────────────────

    @staticmethod
    def _fallback_classify(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keyword-based classification fallback — never raises."""
        results: list[dict[str, Any]] = []
        for r in reviews:
            rid = r.get("review_id", "")
            rating = int(r.get("rating", 3))
            text = str(r.get("review_text", r.get("cleaned_text", ""))).lower()
            if any(kw in text for kw in ["卫生", "脏", "虫", "异味", "异物", "头发"]):
                topic = "hygiene"
            elif any(kw in text for kw in ["等", "排队", "太慢", "半小时", "20分钟", "太久"]):
                topic = "waiting_time"
            elif any(kw in text for kw in ["服务", "态度", "员工", "服务员", "店员"]):
                topic = "service"
            elif any(kw in text for kw in ["价格", "贵", "不值", "太贵"]):
                topic = "price"
            elif any(kw in text for kw in ["环境", "装修", "座位", "吵", "安静"]):
                topic = "environment"
            elif "咖啡" in text or "味道" in text or "口感" in text:
                topic = "product"
            elif rating <= 2:
                topic = "waiting_time"
            else:
                topic = "other"
            results.append({
                "review_id": rid, "topics": [topic], "primary_topic": topic,
                "topic_confidence": 0.60, "needs_review": rating <= 2,
            })
        return results

    @staticmethod
    def _fallback_sentiment(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rating-based sentiment fallback."""
        results: list[dict[str, Any]] = []
        for r in reviews:
            rid = r.get("review_id", "")
            rating = int(r.get("rating", 3))
            if rating <= 2:
                sentiment, severity = "negative", 4 if rating == 1 else 3
            elif rating == 3:
                sentiment, severity = "neutral", 2
            else:
                sentiment, severity = "positive", 1
            results.append({
                "review_id": rid, "sentiment": sentiment, "severity": severity,
                "sentiment_confidence": 0.60, "is_negative_candidate": sentiment == "negative",
                "analysis_reason": f"Fallback — rating={rating}",
            })
        return results

    @staticmethod
    def _fallback_insights(
        reviews: list[dict[str, Any]], analyses: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Topic-counting insight fallback — top 3 topics with up to 3 evidence each."""
        neg_analyses = [a for a in analyses if a.get("is_negative_candidate")]
        topic_counts: dict[str, list[str]] = {}
        for a in neg_analyses:
            topic = a.get("primary_topic", "other")
            topic_counts.setdefault(topic, []).append(a.get("review_id", ""))
        sorted_topics = sorted(topic_counts.items(), key=lambda x: len(x[1]), reverse=True)[:3]

        results: list[dict[str, Any]] = []
        for rank, (topic, review_ids) in enumerate(sorted_topics, 1):
            three_ids = review_ids[:3]
            evidence = []
            for rid in three_ids:
                text = ""
                for r in reviews:
                    if r.get("review_id") == rid:
                        text = str(r.get("review_text", ""))[:80]
                        break
                evidence.append({"review_id": rid, "evidence_text": text, "evidence_reason": "Fallback evidence."})
            _TOPIC_CN = {
                "hygiene": "卫生", "waiting_time": "等待时间", "service": "服务",
                "product": "产品", "environment": "环境", "price": "价格", "other": "其他",
            }
            topic_actions = {
                "hygiene": "建议排查清洁流程，重点检查异物来源和卫生死角，建立定时巡检制度。",
                "waiting_time": "建议优化出餐流程，高峰期增加人手或提前备料，等待超15分钟主动致歉。",
                "service": "建议安排服务礼仪培训，建立客诉反馈机制，每周例会复盘典型服务案例。",
                "price": "建议复盘定价策略，对比同商圈竞品价格，评估性价比优化空间。",
                "environment": "建议检查店内环境，评估噪音、座位舒适度等影响体验的因素。",
                "product": "建议复查产品制作流程，确保出餐品质稳定。",
            }
            topic_cn = _TOPIC_CN.get(topic, topic)
            action = topic_actions.get(topic, "请人工核实具体问题，结合评论内容判断优先级。")
            results.append({
                "rank": rank, "issue_name": f"{topic_cn}相关问题", "topic": topic,
                "issue_summary": f"共 {len(review_ids)} 条相关评论。",
                "mention_count": len(review_ids), "severity_level": "medium",
                "priority_score": 0.60, "suggested_action": action,
                "evidence_count": len(three_ids),
                "evidence_status": "sufficient" if len(three_ids) >= 2 else "evidence_insufficient",
                "evidence": evidence,
            })
        return results

    @staticmethod
    def _fallback_reply(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fixed-template reply fallback."""
        template = (
            "您好，非常抱歉这次体验没有达到您的期待。"
            "我们已经记录您反馈的问题，会认真复盘当天的服务流程。"
            "感谢您愿意指出问题，也欢迎您后续继续反馈。"
        )
        results: list[dict[str, Any]] = []
        for r in reviews:
            rid = r.get("review_id", "")
            original = str(r.get("review_text", r.get("cleaned_text", "")))
            results.append({
                "review_id": rid, "original_review": original,
                "draft_text": template, "approval_status": "pending",
            })
        return results

    # ── Public API (continued) ───────────────────────────────────────────────

    def get_workflow_status(self, batch_id: str) -> WorkflowStatusResult:
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
