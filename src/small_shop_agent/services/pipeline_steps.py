"""Pipeline step functions — each takes a context dict, returns it (possibly mutated).

Extracted from WorkflowService to keep individual methods small and testable.
Demo and Live paths share these steps; branching happens inside each step via ctx["mode"].

Also houses the Pydantic schema models shared between WorkflowService and step functions.
"""
from __future__ import annotations

import time
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from small_shop_agent.core.config import LLM_MAX_RETRIES, MIN_EVIDENCE_COUNT, CONSISTENCY_CONFIDENCE_FACTOR
from small_shop_agent.harness.output.structured_retry import run_with_schema_retry, StructuredRetryResult
from small_shop_agent.harness.evidence.evidence_guard import validate_insight_evidence
from small_shop_agent.harness.safety.safety_guardrails import check_many_replies
from small_shop_agent.harness.verification.consistency_check import check_classification_sentiment_alignment
from small_shop_agent.harness.verification.self_check import detect_sentiment_rating_conflict
from small_shop_agent.utils.logger import log_step


# ── Private Pydantic models for schema validation (shared between steps and service) ──

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


# ── Helper: normalize evidence_status for DB CHECK constraint ───────────

def _norm_evidence_status(raw: str) -> str:
    """Map LLM-generated evidence_status values to DB-accepted 'sufficient' or 'insufficient'."""
    return "insufficient" if "insufficient" in raw else "sufficient"


# ── Step 0: Batch Validation (shared between demo and live) ─────────────

def run_batch_validation(
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    batch_repo,
    review_repo,
    trace_repo,
) -> dict[str, Any] | None:
    """Validate batch exists and has valid reviews.

    Returns None on success (caller proceeds).
    Returns error WorkflowResult dict on failure (caller returns immediately).
    """
    batch = batch_repo.get_batch(batch_id)
    if batch is None:
        log_step("validate_batch", batch_id, status="failed", error="Batch not found", mode=mode)
        return {
            "success": False, "batch_id": batch_id, "mode": mode,
            "summary": {}, "error": f"Batch not found: {batch_id}",
        }

    reviews = review_repo.list_reviews(batch_id, is_valid=True)
    if not reviews:
        batch_repo.update_status(batch_id, "failed", error_message="No valid reviews to analyze.")
        trace_repo.log_step(
            trace_id=trace_id, batch_id=batch_id,
            step_name="classification", status="failed",
            input_summary="0 valid reviews", output_summary="",
            error_message="No valid reviews found for analysis.",
            latency_ms=0, model_name=model_name,
        )
        return {
            "success": False, "batch_id": batch_id, "mode": mode,
            "summary": {"review_count": 0}, "error": "No valid reviews to analyze.",
        }

    batch_repo.update_status(batch_id, "analyzing")
    return None


# ── Step 1: Classification ──────────────────────────────────────────────

def run_classification(
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    review_dicts: list[dict[str, Any]],
    provider,
    fallback_classify_fn,
    trace_repo,
) -> list[dict[str, Any]]:
    """Classify reviews. Returns list of classification dicts."""
    t0 = time.time()

    if mode in ("demo", "mock"):
        classifications = provider.classify_reviews(review_dicts)
        latency_ms = int((time.time() - t0) * 1000)
        trace_repo.log_step(
            trace_id=trace_id, batch_id=batch_id,
            step_name="classification", status="passed",
            input_summary=f"{len(review_dicts)} reviews",
            output_summary=(
                f"{len(classifications)} classified | "
                f"provider={model_name} | attempts=1 | "
                f"used_fallback=False | schema_ok=True | "
                f"schema_errors_count=0"
            ),
            latency_ms=latency_ms, model_name=model_name,
        )
        return classifications

    # Live / OpenAI path
    log_step("classification_start", batch_id, review_count=len(review_dicts), mode=mode, model=model_name)
    cls_retry: StructuredRetryResult = run_with_schema_retry(
        call_fn=lambda attempt: provider.classify_reviews(review_dicts),
        schema_cls=_ClassificationItem,
        many=True, max_retries=LLM_MAX_RETRIES,
        fallback_fn=lambda: fallback_classify_fn(review_dicts),
        batch_id=batch_id,
    )
    classifications: list[dict[str, Any]] = []
    if isinstance(cls_retry.data, list):
        classifications = [_model_to_dict(m) for m in cls_retry.data]
    latency_ms = int((time.time() - t0) * 1000)
    log_step("classification_done", batch_id,
            classified_count=len(classifications),
            attempts=cls_retry.attempts,
            fallback_used=cls_retry.used_fallback,
            schema_errors=cls_retry.errors,
            latency_ms=latency_ms, mode=mode)
    trace_repo.log_step(
        trace_id=trace_id, batch_id=batch_id,
        step_name="classification",
        status="warning" if cls_retry.used_fallback else "passed",
        input_summary=f"{len(review_dicts)} reviews",
        output_summary=(
            f"{len(classifications)} classified | "
            f"provider={model_name} | "
            f"attempts={cls_retry.attempts} | "
            f"used_fallback={cls_retry.used_fallback} | "
            f"schema_ok={cls_retry.ok} | "
            f"schema_errors_count={_count_schema_errors(cls_retry.errors)}"
        ),
        latency_ms=latency_ms, model_name=model_name,
        error_message="; ".join(cls_retry.errors) if cls_retry.errors else None,
    )
    return classifications


# ── Step 2: Sentiment Analysis ──────────────────────────────────────────

def run_sentiment(
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    review_dicts: list[dict[str, Any]],
    provider,
    fallback_sentiment_fn,
    trace_repo,
) -> list[dict[str, Any]]:
    """Analyze sentiment. Returns list of sentiment dicts."""
    t0 = time.time()

    if mode in ("demo", "mock"):
        sentiments = provider.analyze_sentiment(review_dicts)
        latency_ms = int((time.time() - t0) * 1000)
        trace_repo.log_step(
            trace_id=trace_id, batch_id=batch_id,
            step_name="sentiment_analysis", status="passed",
            input_summary=f"{len(review_dicts)} reviews",
            output_summary=f"{len(sentiments)} analyzed",
            latency_ms=latency_ms, model_name=model_name,
        )
        return sentiments

    # Live / OpenAI path
    sent_retry: StructuredRetryResult = run_with_schema_retry(
        call_fn=lambda attempt: provider.analyze_sentiment(review_dicts),
        schema_cls=_SentimentItem,
        many=True, max_retries=LLM_MAX_RETRIES,
        fallback_fn=lambda: fallback_sentiment_fn(review_dicts),
        batch_id=batch_id,
    )
    sentiments: list[dict[str, Any]] = []
    if isinstance(sent_retry.data, list):
        sentiments = [_model_to_dict(m) for m in sent_retry.data]
    latency_ms = int((time.time() - t0) * 1000)
    log_step("sentiment_done", batch_id,
            analyzed_count=len(sentiments),
            attempts=sent_retry.attempts,
            fallback_used=sent_retry.used_fallback,
            schema_errors=sent_retry.errors,
            latency_ms=latency_ms, mode=mode)
    trace_repo.log_step(
        trace_id=trace_id, batch_id=batch_id,
        step_name="sentiment_analysis",
        status="warning" if sent_retry.used_fallback else "passed",
        input_summary=f"{len(review_dicts)} reviews",
        output_summary=f"{len(sentiments)} analyzed (retries={sent_retry.attempts}, fallback={sent_retry.used_fallback})",
        latency_ms=latency_ms, model_name=model_name,
        error_message="; ".join(sent_retry.errors) if sent_retry.errors else None,
    )
    return sentiments


# ── Step 2b: Consistency Check (classification ↔ sentiment alignment) ──

def run_consistency_check(
    classifications: list[dict[str, Any]],
    sentiments: list[dict[str, Any]],
    review_dicts: list[dict[str, Any]],
    *,
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    trace_repo,
) -> None:
    """Check classification↔sentiment consistency; mutate in place, write trace.

    Detects:
      - review_id mismatches between classification and sentiment results
      - rating/sentiment conflicts (e.g. rating≤2 but sentiment=positive)

    Does NOT raise or block — only writes warnings and downgrades confidence.
    """
    # 1. Review-id alignment check
    mismatches = check_classification_sentiment_alignment(classifications, sentiments)
    mismatch_count = len(mismatches)

    # 2. Rating ↔ sentiment conflict check
    conflicts = detect_sentiment_rating_conflict(sentiments, review_dicts)
    conflict_count = len(conflicts)

    # 3. Downgrade confidence for rating/sentiment conflicts
    cls_by_rid: dict[str, dict[str, Any]] = {c.get("review_id", ""): c for c in classifications}
    sent_by_rid: dict[str, dict[str, Any]] = {s.get("review_id", ""): s for s in sentiments}

    for c in conflicts:
        rid = c["review_id"]
        if rid in cls_by_rid:
            cls_entry = cls_by_rid[rid]
            cls_entry["needs_review"] = True
            cls_entry["topic_confidence"] = round(
                cls_entry.get("topic_confidence", 0.80) * CONSISTENCY_CONFIDENCE_FACTOR, 2
            )
        if rid in sent_by_rid:
            sent_entry = sent_by_rid[rid]
            sent_entry["sentiment_confidence"] = round(
                sent_entry.get("sentiment_confidence", 0.80) * CONSISTENCY_CONFIDENCE_FACTOR, 2
            )

    total_issues = mismatch_count + conflict_count
    status = "warning" if total_issues > 0 else "passed"

    trace_repo.log_step(
        trace_id=trace_id,
        batch_id=batch_id,
        step_name="consistency_check",
        status=status,
        input_summary=f"{len(classifications)} classifications, {len(sentiments)} sentiments",
        output_summary=(
            f"{conflict_count} rating/sentiment conflicts"
            f"{', ' if total_issues else ''}"
            f"{mismatch_count} review_id mismatches"
            f"{' — confidences downgraded' if conflict_count else ''}"
        ),
        latency_ms=0,
        model_name=model_name,
        error_message=None,
    )

    if total_issues > 0:
        log_step("consistency_check_warnings", batch_id,
                 conflict_count=conflict_count, mismatch_count=mismatch_count, mode=mode)


# ── Step 3: Merge classification + sentiment → analysis_rows ────────────

def merge_classification_sentiment(
    classifications: list[dict[str, Any]],
    sentiments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine classification and sentiment results into analysis_rows."""
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
    return analysis_rows


def write_analysis_to_db(
    batch_id: str,
    mode: str,
    analysis_rows: list[dict[str, Any]],
    analysis_repo,
) -> None:
    """Persist analysis_rows to review_analysis table."""
    if analysis_rows:
        analysis_repo.bulk_insert_analysis(batch_id, analysis_rows)
    log_step("write_analysis_to_db", batch_id, row_count=len(analysis_rows), mode=mode)


# ── Step 4: Issue Aggregation + Evidence ────────────────────────────────

def run_insights(
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    review_dicts: list[dict[str, Any]],
    analysis_rows: list[dict[str, Any]],
    provider,
    fallback_insights_fn,
    trace_repo,
    insight_repo,
) -> tuple[list[dict[str, Any]], int, int]:
    """Generate insights and write to DB. Returns (insights, insight_count, negative_count)."""
    t0 = time.time()
    negative_count = sum(1 for a in analysis_rows if a.get("is_negative_candidate"))

    if mode in ("demo", "mock"):
        insights = provider.generate_insights(review_dicts, analysis_rows)
        insight_count = len(insights)

        # Write insight rows
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
        insight_repo.bulk_insert_insights(batch_id, insight_rows)
        for ins in insights:
            log_step("generate_insights", batch_id, rank=ins.get("rank"),
                    issue_name=ins.get("issue_name"), topic=ins.get("topic"),
                    evidence_count=ins.get("evidence_count"), mode="demo")
        latency_ms = int((time.time() - t0) * 1000)
        trace_repo.log_step(
            trace_id=trace_id, batch_id=batch_id,
            step_name="issue_aggregation", status="passed",
            input_summary=f"{len(analysis_rows)} analyses",
            output_summary=f"{insight_count} insights, {sum(ins.get('evidence_count', 0) for ins in insights)} evidence",
            latency_ms=latency_ms, model_name=model_name,
        )
        return insights, insight_count, negative_count

    # Live / OpenAI path
    ins_retry: StructuredRetryResult = run_with_schema_retry(
        call_fn=lambda attempt: provider.generate_insights(review_dicts, analysis_rows),
        schema_cls=_InsightItem,
        many=True, max_retries=LLM_MAX_RETRIES,
        fallback_fn=lambda: fallback_insights_fn(review_dicts, analysis_rows),
        batch_id=batch_id,
    )
    insights: list[dict[str, Any]] = []
    if isinstance(ins_retry.data, list):
        insights = [_model_to_dict(m) for m in ins_retry.data]
    insight_count = len(insights)

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
    insight_repo.bulk_insert_insights(batch_id, insight_db_rows)
    for ins in insights:
        log_step("generate_insights", batch_id, rank=ins.get("rank"),
                issue_name=ins.get("issue_name"), topic=ins.get("topic"),
                evidence_count=ins.get("evidence_count"),
                fallback_used=ins_retry.used_fallback,
                attempts=ins_retry.attempts, mode=mode)
    latency_ms = int((time.time() - t0) * 1000)
    trace_repo.log_step(
        trace_id=trace_id, batch_id=batch_id,
        step_name="issue_aggregation",
        status="warning" if ins_retry.used_fallback else "passed",
        input_summary=f"{len(analysis_rows)} analyses",
        output_summary=f"{insight_count} insights (retries={ins_retry.attempts}, fallback={ins_retry.used_fallback})",
        latency_ms=latency_ms, model_name=model_name,
        error_message="; ".join(ins_retry.errors) if ins_retry.errors else None,
    )
    return insights, insight_count, negative_count


# ── Step 5: Evidence Check & Write ──────────────────────────────────────

def run_evidence_check(
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    insights: list[dict[str, Any]],
    review_dicts: list[dict[str, Any]],
    valid_review_ids: set[str],
    trace_repo,
    insight_repo,
) -> tuple[int, int, int, int]:
    """Validate evidence and write to DB. Returns (evidence_count, ev_valid, ev_rejected, ev_insufficient)."""
    insight_count = len(insights)
    log_step("evidence_check_start", batch_id, insight_count=insight_count, mode=mode)
    evidence_result = validate_insight_evidence(insights, review_dicts, min_evidence_count=MIN_EVIDENCE_COUNT, batch_id=batch_id)
    ecount = sum(len(ir.evidence_review_ids) for ir in evidence_result.issues)
    log_step("evidence_check_done", batch_id,
            total_evidence=ecount,
            valid_issues=len(evidence_result.valid_issues),
            rejected_issues=len(evidence_result.rejected_issues),
            mode=mode)

    # Resolve DB insight IDs from rank
    inserted_insights = insight_repo.get_top_issues(batch_id)
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
        insight_repo.bulk_insert_evidence(batch_id, evidence_db_rows)
    log_step("write_evidence_to_db", batch_id, evidence_count=len(evidence_db_rows), mode=mode)

    e_valid = len(evidence_result.valid_issues)
    e_rejected = sum(1 for ir in evidence_result.issues if ir.status == "invalid")
    e_insufficient = sum(1 for ir in evidence_result.issues if ir.status == "evidence_insufficient")

    trace_repo.log_step(
        trace_id=trace_id, batch_id=batch_id,
        step_name="evidence_check",
        status="warning" if (e_rejected or e_insufficient) else "passed",
        input_summary=f"{insight_count} insights",
        output_summary=(
            f"{ecount} evidence | "
            f"valid_issues_count={e_valid} | "
            f"rejected_issues_count={e_rejected} | "
            f"evidence_insufficient_count={e_insufficient}"
        ),
        latency_ms=0, model_name=model_name,
    )
    return ecount, e_valid, e_rejected, e_insufficient


# ── Step 6: Reply Drafting ─────────────────────────────────────────────

def run_reply_drafting(
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    review_dicts: list[dict[str, Any]],
    analysis_rows: list[dict[str, Any]],
    provider,
    fallback_reply_fn,
    trace_repo,
) -> tuple[list[dict[str, Any]], int]:
    """Draft replies for negative candidates. Returns (drafts, draft_count)."""
    t0 = time.time()
    neg_candidates = [a for a in analysis_rows if a.get("is_negative_candidate")]
    log_step("reply_drafting_start", batch_id, negative_count=len(neg_candidates), mode=mode)
    if not neg_candidates:
        neg_candidates = [a for a in analysis_rows if a.get("severity", 2) >= 3]
    neg_ids = {a["review_id"] for a in neg_candidates}

    neg_review_dicts = [r for r in review_dicts if r.get("review_id") in neg_ids]
    neg_analyses = [a for a in analysis_rows if a.get("review_id") in neg_ids]

    if mode in ("demo", "mock"):
        drafts = provider.draft_replies(neg_review_dicts, neg_analyses)
        latency_ms = int((time.time() - t0) * 1000)
        trace_repo.log_step(
            trace_id=trace_id, batch_id=batch_id,
            step_name="reply_drafting", status="passed",
            input_summary=f"{len(neg_candidates)} negative candidates",
            output_summary=f"{len(drafts)} drafts generated",
            latency_ms=latency_ms, model_name=model_name,
        )
        return drafts, len(drafts)

    # Live / OpenAI path
    reply_retry: StructuredRetryResult = run_with_schema_retry(
        call_fn=lambda attempt: provider.draft_replies(neg_review_dicts, neg_analyses),
        schema_cls=_ReplyItem,
        many=True, max_retries=LLM_MAX_RETRIES,
        fallback_fn=lambda: fallback_reply_fn(neg_review_dicts),
        batch_id=batch_id,
    )
    drafts: list[dict[str, Any]] = []
    if isinstance(reply_retry.data, list):
        drafts = [_model_to_dict(m) for m in reply_retry.data]
    latency_ms = int((time.time() - t0) * 1000)
    trace_repo.log_step(
        trace_id=trace_id, batch_id=batch_id,
        step_name="reply_drafting",
        status="warning" if reply_retry.used_fallback else "passed",
        input_summary=f"{len(neg_candidates)} negative candidates",
        output_summary=f"{len(drafts)} drafts (retries={reply_retry.attempts}, fallback={reply_retry.used_fallback})",
        latency_ms=latency_ms, model_name=model_name,
        error_message="; ".join(reply_retry.errors) if reply_retry.errors else None,
    )
    return drafts, len(drafts)


# ── Step 7: Safety Check ────────────────────────────────────────────────

def run_safety_check(
    batch_id: str,
    trace_id: str,
    mode: str,
    model_name: str,
    drafts: list[dict[str, Any]],
    provider,
    trace_repo,
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Run safety checks on all drafts. Returns (safe_drafts, pass_count, rewrite_count, blocked_count).

    Demo mode delegates to provider.check_safety (pre-defined mock statuses).
    Live mode uses the keyword-based safety guardrails directly.
    """
    if mode in ("demo", "mock"):
        safe_drafts = provider.check_safety(drafts)
    else:
        safe_drafts = check_many_replies(drafts, batch_id=batch_id)

    blocked_count = sum(1 for d in safe_drafts if d.get("safety_status") == "blocked")
    rewrite_count = sum(1 for d in safe_drafts if d.get("safety_status") == "rewrite_required")
    pass_count = sum(1 for d in safe_drafts if d.get("safety_status") == "pass")
    draft_count = len(safe_drafts)

    for d in safe_drafts:
        log_step("safety_check", batch_id, review_id=d.get("review_id"),
                safety_status=d.get("safety_status"),
                risk_types=d.get("risk_types", []), mode=mode)

    safety_trace_status = "warning" if blocked_count > 0 else "passed"
    trace_repo.log_step(
        trace_id=trace_id, batch_id=batch_id,
        step_name="safety_check", status=safety_trace_status,
        input_summary=f"{draft_count} drafts",
        output_summary=(
            f"{pass_count} pass, {rewrite_count} rewrite_required, {blocked_count} blocked | "
            f"pass_count={pass_count} | "
            f"rewrite_required_count={rewrite_count} | "
            f"blocked_count={blocked_count}"
        ),
        latency_ms=0, model_name=model_name,
    )
    return safe_drafts, pass_count, rewrite_count, blocked_count


# ── Step 8: Write drafts to DB ──────────────────────────────────────────

def write_drafts_to_db(
    batch_id: str,
    mode: str,
    model_name: str,
    safe_drafts: list[dict[str, Any]],
    reply_repo,
) -> None:
    """Persist safe drafts to reply_drafts table."""
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
        reply_repo.bulk_insert_drafts(batch_id, draft_db_rows)
    log_step("write_drafts_to_db", batch_id, draft_count=len(safe_drafts), mode=mode)


# ── Step 9: Finalize batch ──────────────────────────────────────────────

def finalize_batch(
    batch_id: str,
    mode: str,
    review_count: int,
    negative_count: int,
    insight_count: int,
    draft_count: int,
    blocked_count: int,
    rewrite_count: int,
    pass_count: int,
    evidence_count: int,
    trace_count: int,
    safe_drafts: list[dict[str, Any]],
    batch_repo,
) -> dict[str, Any]:
    """Update batch status and return the WorkflowResult."""
    pending_count = sum(1 for d in safe_drafts if d.get("approval_status") == "pending")
    batch_repo.update_status(
        batch_id, "analyzed",
        negative_review_count=negative_count,
        pending_reply_count=pending_count,
    )
    return {
        "success": True,
        "batch_id": batch_id,
        "mode": mode,
        "summary": {
            "review_count": review_count,
            "negative_count": negative_count,
            "insight_count": insight_count,
            "draft_count": draft_count,
            "blocked_count": blocked_count,
            "rewrite_count": rewrite_count,
            "pass_count": pass_count,
            "evidence_count": evidence_count,
            "trace_count": trace_count,
        },
        "error": None,
    }
