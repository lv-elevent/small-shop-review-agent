"""Read-only business tools for the agent runtime.

Every tool returns a plain dict conforming to a TypedDict schema.
Tools never INSERT/UPDATE/DELETE — they only SELECT or read in-memory data.
"""
from __future__ import annotations

import time
from typing import Any, TypedDict

from loguru import logger

from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.sqlite_session import get_session
from small_shop_agent.harness.safety.safety_policy import (
    BLOCKED_PATTERNS,
    REWRITE_PATTERNS,
    REASON_MAP,
)

# ── Result TypedDicts ────────────────────────────────────────────────────

class LookupReviewResult(TypedDict):
    success: bool
    found: bool
    review: dict[str, Any] | None
    error: str | None


class SearchReviewsResult(TypedDict):
    success: bool
    matches: list[dict[str, Any]]
    count: int
    keyword: str
    error: str | None


class CountByTopicResult(TypedDict):
    success: bool
    topic: str
    count: int
    error: str | None


class BatchStatsResult(TypedDict):
    success: bool
    batch_id: str
    stats: dict[str, Any]
    error: str | None


class SafetyPolicyResult(TypedDict):
    success: bool
    policy_type: str
    patterns: dict[str, list[str]]
    reasons: dict[str, str]
    error: str | None


# ── Internal helpers ─────────────────────────────────────────────────────

def _record_tool_call(
    tool_name: str,
    input_summary: str,
    output_summary: str,
    latency_ms: int,
) -> None:
    """Write a structured log entry for tool-call tracing."""
    logger.bind(
        tool_name=tool_name,
        input_summary=input_summary,
        output_summary=output_summary,
        latency_ms=latency_ms,
    ).debug("tool_call")


def _trace(tool_name: str, input_summary: str, output_summary: str, t0: float) -> None:
    _record_tool_call(
        tool_name,
        input_summary,
        output_summary,
        latency_ms=int((time.time() - t0) * 1000),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Public tools
# ═══════════════════════════════════════════════════════════════════════════

def lookup_review(
    *,
    review_id: str,
    batch_id: str,
    trace: bool = True,
) -> LookupReviewResult:
    """Return a single review by batch_id + review_id.

    Returns ``{success, found, review, error}``.
    """
    t0 = time.time()
    try:
        repo = ReviewRepository()
        row = repo.get_review(batch_id, review_id)
        result: LookupReviewResult = {
            "success": True,
            "found": row is not None,
            "review": dict(row) if row else None,
            "error": None,
        }
    except Exception as exc:
        result = {"success": False, "found": False, "review": None, "error": str(exc)}

    if trace:
        _trace("lookup_review",
               f"review_id={review_id}, batch_id={batch_id}",
               f"found={result['found']}", t0)
    return result


def search_reviews(
    *,
    keyword: str,
    batch_id: str,
    limit: int = 10,
    trace: bool = True,
) -> SearchReviewsResult:
    """Search reviews whose ``review_text`` contains *keyword* (LIKE).

    Returns ``{success, matches, count, keyword, error}``.
    """
    t0 = time.time()
    try:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT * FROM reviews
                   WHERE batch_id = ? AND review_text LIKE ?
                   ORDER BY id LIMIT ?""",
                (batch_id, f"%{keyword}%", limit),
            ).fetchall()
        matches = [dict(r) for r in rows]
        result: SearchReviewsResult = {
            "success": True,
            "matches": matches,
            "count": len(matches),
            "keyword": keyword,
            "error": None,
        }
    except Exception as exc:
        result = {"success": False, "matches": [], "count": 0, "keyword": keyword, "error": str(exc)}

    if trace:
        _trace("search_reviews",
               f"keyword={keyword!r}, batch_id={batch_id}, limit={limit}",
               f"found={result['count']}", t0)
    return result


def count_by_topic(
    *,
    topic: str,
    batch_id: str,
    trace: bool = True,
) -> CountByTopicResult:
    """Count ``review_analysis`` rows where ``primary_topic`` equals *topic*.

    Returns ``{success, topic, count, error}``.
    """
    t0 = time.time()
    try:
        with get_session() as conn:
            row = conn.execute(
                """SELECT COUNT(*) as cnt FROM review_analysis
                   WHERE batch_id = ? AND primary_topic = ?""",
                (batch_id, topic),
            ).fetchone()
        count = row["cnt"] if row else 0
        result: CountByTopicResult = {
            "success": True,
            "topic": topic,
            "count": count,
            "error": None,
        }
    except Exception as exc:
        result = {"success": False, "topic": topic, "count": 0, "error": str(exc)}

    if trace:
        _trace("count_by_topic",
               f"topic={topic!r}, batch_id={batch_id}",
               f"count={result['count']}", t0)
    return result


def get_batch_stats(
    *,
    batch_id: str,
    trace: bool = True,
) -> BatchStatsResult:
    """Aggregate batch-level statistics using existing repositories.

    Returns ``{success, batch_id, stats, error}`` with keys:
    total_reviews, valid_reviews, negative_count, neutral_count,
    positive_count, status.
    """
    t0 = time.time()
    try:
        batch_repo = BatchRepository()
        review_repo = ReviewRepository()
        analysis_repo = AnalysisRepository()

        batch = batch_repo.get_batch(batch_id)
        if batch is None:
            return {"success": False, "batch_id": batch_id, "stats": {},
                    "error": f"Batch not found: {batch_id}"}

        total = review_repo.count_reviews(batch_id)
        valid = review_repo.count_reviews(batch_id, is_valid=True)
        sentiment_counts = analysis_repo.count_by_sentiment(batch_id)

        stats = {
            "total_reviews": total,
            "valid_reviews": valid,
            "negative_count": sentiment_counts.get("negative", 0),
            "neutral_count": sentiment_counts.get("neutral", 0),
            "positive_count": sentiment_counts.get("positive", 0),
            "status": batch.get("status", "unknown"),
            "store_type": batch.get("store_type", ""),
            "file_name": batch.get("file_name", ""),
        }
        result: BatchStatsResult = {
            "success": True,
            "batch_id": batch_id,
            "stats": stats,
            "error": None,
        }
    except Exception as exc:
        result = {"success": False, "batch_id": batch_id, "stats": {}, "error": str(exc)}

    if trace:
        _trace("get_batch_stats",
               f"batch_id={batch_id}",
               f"total={result['stats'].get('total_reviews', 0)}", t0)
    return result


def get_safety_policy_snippet(
    *,
    policy_type: str,
    trace: bool = True,
) -> SafetyPolicyResult:
    """Return safety policy patterns and reasons from the in-memory policy module.

    *policy_type* must be one of ``"blocked"``, ``"rewrite"``, or ``"all"``.

    Returns ``{success, policy_type, patterns, reasons, error}``.
    """
    t0 = time.time()
    valid_types = ("blocked", "rewrite", "all")
    if policy_type not in valid_types:
        return {
            "success": False,
            "policy_type": policy_type,
            "patterns": {},
            "reasons": {},
            "error": f"Unknown policy_type: {policy_type!r}. Valid: {valid_types}",
        }

    patterns: dict[str, list[str]] = {}
    if policy_type in ("blocked", "all"):
        patterns.update(BLOCKED_PATTERNS)
    if policy_type in ("rewrite", "all"):
        patterns.update(REWRITE_PATTERNS)

    reasons = {k: REASON_MAP.get(k, "") for k in patterns}

    result: SafetyPolicyResult = {
        "success": True,
        "policy_type": policy_type,
        "patterns": patterns,
        "reasons": reasons,
        "error": None,
    }

    if trace:
        _trace("get_safety_policy_snippet",
               f"policy_type={policy_type!r}",
               f"category_count={len(patterns)}", t0)
    return result
