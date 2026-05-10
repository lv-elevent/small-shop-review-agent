"""TypedDict definitions for Service layer return values.

These are pure type annotations — they do NOT change any runtime behavior or data structures.
"""
from __future__ import annotations

from typing import Any, TypedDict


# ── ReviewService ────────────────────────────────────────────────────────────

class CsvValidateResult(TypedDict):
    """Return type of ReviewService.validate_csv()."""
    success: bool
    batch_id: str | None
    validation: dict[str, Any]
    message: str


class BatchCreateResult(TypedDict):
    """Return type of ReviewService.create_batch()."""
    success: bool
    batch_id: str | None
    validation: dict[str, Any]
    message: str


# ── ReplyService ─────────────────────────────────────────────────────────────

class ApprovalResult(TypedDict):
    """Return type of ReplyService.approve_draft / edit_draft / reject_draft."""
    success: bool
    draft: dict[str, Any] | None
    error: str | None


class ExportResult(TypedDict):
    """Return type of ReplyService.export_approved_replies()."""
    batch_id: str
    drafts: list[dict[str, Any]]
    count: int
    csv_data: str


# ── WorkflowService ──────────────────────────────────────────────────────────

class WorkflowResult(TypedDict):
    """Return type of WorkflowService.run_analysis / run_demo_analysis."""
    success: bool
    batch_id: str
    mode: str
    summary: dict[str, Any]
    error: str | None


class WorkflowCounts(TypedDict):
    """Counts sub-dict inside WorkflowStatusResult."""
    reviews: int
    valid_reviews: int
    analysis: int
    insights: int
    drafts: int


class WorkflowStatusResult(TypedDict):
    """Return type of WorkflowService.get_workflow_status()."""
    success: bool
    batch_id: str
    batch: dict[str, Any] | None
    traces: list[dict[str, Any]]
    counts: dict[str, int]
    error: str | None


# ── EvalService ──────────────────────────────────────────────────────────────

class EvalReport(TypedDict):
    """The 'report' sub-dict inside EvalResult."""
    topic_accuracy: float
    sentiment_accuracy: float
    unsafe_reply_count: int
    schema_failure_count: int
    total_eval_cases: int
    topic_correct_count: int
    sentiment_correct_count: int
    details: dict[str, Any]


class EvalResult(TypedDict):
    """Return type of EvalService.run_eval()."""
    success: bool
    eval_run_id: str
    batch_id: str
    report: dict[str, Any]
    error: str | None


# ── ApprovalService ──────────────────────────────────────────────────────────

class ApprovalActionResult(TypedDict):
    """Return type of ApprovalService.record_approval_action()."""
    id: int
    draft_id: int
    batch_id: str
    review_id: str
    action: str
    before_text: str
    after_text: str
    reject_reason: str
    created_at: str
