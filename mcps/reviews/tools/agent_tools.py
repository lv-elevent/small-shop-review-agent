"""MCP-registered agent tools grouping all read-only business operations.

Importing this module automatically registers every decorated tool into
the global MCP registry (mcps.reviews.mcp_server._registry).
"""
from __future__ import annotations

import time
from typing import Any

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

from mcps.reviews.mcp_server import mcp_tool

# ------------------------------------------------------------------
# Internal helpers (unchanged from original tools.py)
# ------------------------------------------------------------------

def _record_tool_call(tool_name: str, input_summary: str, output_summary: str, latency_ms: int) -> None:
    logger.bind(
        tool_name=tool_name, input_summary=input_summary,
        output_summary=output_summary, latency_ms=latency_ms,
    ).debug("tool_call")

def _trace(tool_name: str, input_summary: str, output_summary: str, t0: float) -> None:
    _record_tool_call(tool_name, input_summary, output_summary, int((time.time() - t0) * 1000))

# ------------------------------------------------------------------
# 5 Agent tools
# ------------------------------------------------------------------

@mcp_tool(
    name="lookup_review",
    description="Query a single review by batch_id and review_id",
    input_schema={
        "type": "object",
        "properties": {
            "review_id": {"type": "string", "description": "The review unique identifier"},
            "batch_id": {"type": "string", "description": "The batch identifier"},
        },
        "required": ["review_id", "batch_id"],
    },
    require_batch_id=True,
)
def lookup_review(*, review_id: str, batch_id: str, trace: bool = True) -> dict[str, Any]:
    t0 = time.time()
    try:
        repo = ReviewRepository()
        row = repo.get_review(batch_id, review_id)
        result = {"success": True, "found": row is not None, "review": dict(row) if row else None, "error": None}
    except Exception as exc:
        result = {"success": False, "found": False, "review": None, "error": str(exc)}
    if trace:
        _trace("lookup_review", f"review_id={review_id}, batch_id={batch_id}", f"found={result['found']}", t0)
    return result


@mcp_tool(
    name="search_reviews",
    description="Search reviews whose review_text contains the keyword (SQL LIKE)",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "Search keyword or phrase"},
            "batch_id": {"type": "string", "description": "The batch identifier"},
            "limit": {"type": "integer", "description": "Maximum number of results", "default": 10},
        },
        "required": ["keyword", "batch_id"],
    },
    require_batch_id=True,
)
def search_reviews(*, keyword: str, batch_id: str, limit: int = 10, trace: bool = True) -> dict[str, Any]:
    t0 = time.time()
    try:
        with get_session() as conn:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE batch_id = ? AND review_text LIKE ? ORDER BY id LIMIT ?",
                (batch_id, "%" + keyword + "%", limit),
            ).fetchall()
        matches = [dict(r) for r in rows]
        result = {"success": True, "matches": matches, "count": len(matches), "keyword": keyword, "error": None}
    except Exception as exc:
        result = {"success": False, "matches": [], "count": 0, "keyword": keyword, "error": str(exc)}
    if trace:
        _trace("search_reviews", f"keyword={keyword!r}, batch_id={batch_id}, limit={limit}", f"found={result['count']}", t0)
    return result


@mcp_tool(
    name="count_by_topic",
    description="Count review_analysis rows where primary_topic matches the given topic",
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic name to count"},
            "batch_id": {"type": "string", "description": "The batch identifier"},
        },
        "required": ["topic", "batch_id"],
    },
    require_batch_id=True,
)
def count_by_topic(*, topic: str, batch_id: str, trace: bool = True) -> dict[str, Any]:
    t0 = time.time()
    try:
        with get_session() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ? AND primary_topic = ?",
                (batch_id, topic),
            ).fetchone()
        count = row["cnt"] if row else 0
        result = {"success": True, "topic": topic, "count": count, "error": None}
    except Exception as exc:
        result = {"success": False, "topic": topic, "count": 0, "error": str(exc)}
    if trace:
        _trace("count_by_topic", f"topic={topic!r}, batch_id={batch_id}", f"count={result['count']}", t0)
    return result


@mcp_tool(
    name="get_batch_stats",
    description="Aggregate batch-level statistics: total, valid, negative/neutral/positive counts, status",
    input_schema={
        "type": "object",
        "properties": {
            "batch_id": {"type": "string", "description": "The batch identifier"},
        },
        "required": ["batch_id"],
    },
    require_batch_id=True,
)
def get_batch_stats(*, batch_id: str, trace: bool = True) -> dict[str, Any]:
    t0 = time.time()
    try:
        batch_repo = BatchRepository()
        review_repo = ReviewRepository()
        analysis_repo = AnalysisRepository()
        batch = batch_repo.get_batch(batch_id)
        if batch is None:
            return {"success": False, "batch_id": batch_id, "stats": {}, "error": f"Batch not found: {batch_id}"}
        total = review_repo.count_reviews(batch_id)
        valid = review_repo.count_reviews(batch_id, is_valid=True)
        sentiment_counts = analysis_repo.count_by_sentiment(batch_id)
        stats = {
            "total_reviews": total, "valid_reviews": valid,
            "negative_count": sentiment_counts.get("negative", 0),
            "neutral_count": sentiment_counts.get("neutral", 0),
            "positive_count": sentiment_counts.get("positive", 0),
            "status": batch.get("status", "unknown"),
            "store_type": batch.get("store_type", ""),
            "file_name": batch.get("file_name", ""),
        }
        result = {"success": True, "batch_id": batch_id, "stats": stats, "error": None}
    except Exception as exc:
        result = {"success": False, "batch_id": batch_id, "stats": {}, "error": str(exc)}
    if trace:
        _trace("get_batch_stats", f"batch_id={batch_id}", f"total={result['stats'].get('total_reviews', 0)}", t0)
    return result


@mcp_tool(
    name="get_safety_policy_snippet",
    description="Return safety policy patterns and reasons from in-memory policy module",
    input_schema={
        "type": "object",
        "properties": {
            "policy_type": {
                "type": "string",
                "description": "One of: blocked, rewrite, all",
                "enum": ["blocked", "rewrite", "all"],
            },
        },
        "required": ["policy_type"],
    },
)
def get_safety_policy_snippet(*, policy_type: str, trace: bool = True) -> dict[str, Any]:
    t0 = time.time()
    valid_types = ("blocked", "rewrite", "all")
    if policy_type not in valid_types:
        return {"success": False, "policy_type": policy_type, "patterns": {}, "reasons": {}, "error": f"Unknown policy_type: {policy_type!r}"}
    patterns: dict[str, list[str]] = {}
    if policy_type in ("blocked", "all"):
        patterns.update(BLOCKED_PATTERNS)
    if policy_type in ("rewrite", "all"):
        patterns.update(REWRITE_PATTERNS)
    reasons = {k: REASON_MAP.get(k, "") for k in patterns}
    result = {"success": True, "policy_type": policy_type, "patterns": patterns, "reasons": reasons, "error": None}
    if trace:
        _trace("get_safety_policy_snippet", f"policy_type={policy_type!r}", f"category_count={len(patterns)}", t0)
    return result


# ------------------------------------------------------------------
# Utility tool (from mcps/reviews/tools/csv_stats.py)
# ------------------------------------------------------------------

@mcp_tool(
    name="csv_stats",
    description="Return basic statistics for an uploaded CSV file",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the CSV file"},
        },
        "required": ["file_path"],
    },
)
def csv_stats(file_path: str) -> dict[str, Any]:
    import pandas as pd
    try:
        df = pd.read_csv(file_path)
        return {
            "success": True,
            "total_rows": len(df),
            "columns": list(df.columns),
            "null_counts": df.isna().sum().to_dict(),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
