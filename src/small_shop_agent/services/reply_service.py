"""ReplyService — draft management, human approval workflow, and reply export."""
from __future__ import annotations

from typing import Any

from loguru import logger

from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.storage.repositories.memory_repository import MemoryRepository
from small_shop_agent.services.types import ApprovalResult, ExportResult

_MEMO_STORE = "coffee_shop"


def _json_loads_list(val: object) -> list:
    import json as _json
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return _json.loads(val)
        except Exception:
            return []
    return []


class ReplyService:
    """Manages reply drafts: listing, approving, editing, rejecting, and exporting."""

    def __init__(self) -> None:
        self._reply_repo = ReplyRepository()
        self._trace_repo = TraceRepository()
        self._memory_repo = MemoryRepository()

    # ── Read ────────────────────────────────────────────────────────────────

    def get_pending_drafts(self, batch_id: str) -> list[dict[str, Any]]:
        """Return drafts with approval_status='pending', ordered by risk priority."""
        return self._reply_repo.get_pending_drafts(batch_id)

    def get_draft_detail(self, draft_id: int) -> dict[str, Any] | None:
        """Return a single draft by its id."""
        return self._reply_repo.get_draft_detail(draft_id)

    # ── Approval Actions ────────────────────────────────────────────────────

    def approve_draft(self, draft_id: int) -> ApprovalResult:
        """
        Approve a draft for publishing.
        Only allowed when safety_status is 'pass'.
        """
        draft = self._reply_repo.get_draft_detail(draft_id)
        if draft is None:
            return {"success": False, "error": f"Draft not found: {draft_id}"}

        if draft["safety_status"] != "pass":
            return {
                "success": False,
                "error": (
                    f"Cannot approve draft with safety_status='{draft['safety_status']}'. "
                    "Only 'pass' drafts can be approved."
                ),
            }

        updated = self._reply_repo.update_approval_status(
            draft_id, "approved", final_text=draft["draft_text"]
        )
        if updated is None:
            return {"success": False, "error": "Failed to update approval status."}

        approval_action = self._reply_repo.insert_approval_action(
            draft_id=draft_id,
            batch_id=draft["batch_id"],
            review_id=draft["review_id"],
            action="approve",
            before_text=draft["draft_text"],
            after_text=draft["draft_text"],
        )

        self._trace_repo.log_step(
            trace_id=f"trace-{draft['batch_id']}",
            batch_id=draft["batch_id"],
            step_name="human_approval",
            status="passed",
            input_summary=f"approve draft {draft_id} ({draft['review_id']})",
            output_summary="approved",
            latency_ms=0,
            model_name="human",
        )

        logger.success(f"草稿 {draft_id} ({draft['review_id']}) 审批通过")
        self._write_memory(draft, approval_action, "approved_reply", draft["draft_text"])
        return {"success": True, "draft": updated, "error": None}

    def edit_draft(self, draft_id: int, edited_text: str) -> ApprovalResult:
        """
        Edit a draft's text and mark as 'edited'.
        edited_text must not be empty.
        """
        if not edited_text or not edited_text.strip():
            return {"success": False, "error": "edited_text cannot be empty."}

        draft = self._reply_repo.get_draft_detail(draft_id)
        if draft is None:
            return {"success": False, "error": f"Draft not found: {draft_id}"}

        updated = self._reply_repo.update_approval_status(
            draft_id, "edited", edited_text=edited_text, final_text=edited_text
        )
        if updated is None:
            return {"success": False, "error": "Failed to update approval status."}

        approval_action = self._reply_repo.insert_approval_action(
            draft_id=draft_id,
            batch_id=draft["batch_id"],
            review_id=draft["review_id"],
            action="edit",
            before_text=draft["draft_text"],
            after_text=edited_text,
        )

        self._trace_repo.log_step(
            trace_id=f"trace-{draft['batch_id']}",
            batch_id=draft["batch_id"],
            step_name="human_approval",
            status="passed",
            input_summary=f"edit draft {draft_id} ({draft['review_id']})",
            output_summary=f"edited ({len(edited_text)} chars)",
            latency_ms=0,
            model_name="human",
        )

        logger.success(f"草稿 {draft_id} ({draft['review_id']}) 已编辑")
        self._write_memory(
            draft, approval_action, "safety_case",
            f"修改前：{draft['draft_text']}",
            metadata_extra={"edit_reason": "人工修改优化"},
        )
        self._write_memory(draft, approval_action, "approved_reply", edited_text)
        return {"success": True, "draft": updated, "error": None}

    def reject_draft(self, draft_id: int, reason: str = "") -> ApprovalResult:
        """Reject a draft so it will not be published."""
        draft = self._reply_repo.get_draft_detail(draft_id)
        if draft is None:
            return {"success": False, "error": f"Draft not found: {draft_id}"}

        updated = self._reply_repo.update_approval_status(
            draft_id, "rejected", edited_text="", final_text=""
        )
        if updated is None:
            return {"success": False, "error": "Failed to update approval status."}

        approval_action = self._reply_repo.insert_approval_action(
            draft_id=draft_id,
            batch_id=draft["batch_id"],
            review_id=draft["review_id"],
            action="reject",
            before_text=draft["draft_text"],
            after_text="",
            reject_reason=reason,
        )

        self._trace_repo.log_step(
            trace_id=f"trace-{draft['batch_id']}",
            batch_id=draft["batch_id"],
            step_name="human_approval",
            status="passed",
            input_summary=f"reject draft {draft_id} ({draft['review_id']})",
            output_summary=f"rejected: {reason[:80]}" if reason else "rejected",
            latency_ms=0,
            model_name="human",
        )

        logger.success(f"草稿 {draft_id} ({draft['review_id']}) 已驳回")
        mem_type = "safety_case" if draft.get("safety_status") == "blocked" else "rejected_reply"
        self._write_memory(
            draft, approval_action, mem_type,
            f"驳回原因：{reason}\n原文：{draft['draft_text']}",
            metadata_extra={"reject_reason": reason},
        )
        return {"success": True, "draft": updated, "error": None}

    # ── Memory ─────────────────────────────────────────────────────────────

    def _write_memory(
        self,
        draft: dict[str, Any],
        approval_action: dict[str, Any],
        memory_type: str,
        content: str,
        *,
        metadata_extra: dict[str, Any] | None = None,
    ) -> None:
        """Persist an approval action as an agent memory entry."""
        try:
            source = self._memory_repo.insert_source(
                batch_id=draft.get("batch_id", ""),
                review_id=draft.get("review_id", ""),
                reply_id=str(draft.get("id", "")),
                approval_action_id=approval_action.get("id"),
            )
            meta: dict[str, Any] = {
                "risk_types": _json_loads_list(draft.get("risk_types", [])),
                "topic": draft.get("primary_topic", ""),
                "sentiment": draft.get("sentiment", ""),
                "approval_action": approval_action.get("action", ""),
            }
            if metadata_extra:
                meta.update(metadata_extra)
            embedding = self._embed_content(content)
            self._memory_repo.insert_memory(
                store_type=_MEMO_STORE,
                memory_type=memory_type,
                content=content,
                metadata=meta,
                source_id=source.get("source_id", ""),
                embedding=embedding,
            )
        except Exception as exc:
            logger.warning(f"写入记忆失败：{exc}")

    @staticmethod
    def _embed_content(content: str):
        """Generate embedding vector for content. Returns None when unavailable."""
        try:
            from small_shop_agent.embeddings.embedder import get_embedder
            embedder = get_embedder()
            if embedder.available:
                return embedder.embed_single(content)
        except Exception:
            pass
        return None

    # ── Export ──────────────────────────────────────────────────────────────

    def export_approved_replies(self, batch_id: str) -> ExportResult:
        """Return all approved/edited drafts ready for publishing, with CSV data."""
        from small_shop_agent.exports.approved_replies_exporter import (
            export_approved_replies_csv,
        )
        all_drafts = self._reply_repo.list_drafts(batch_id)
        approved = [d for d in all_drafts if d["approval_status"] in ("approved", "edited")]
        return {
            "batch_id": batch_id,
            "drafts": approved,
            "count": len(approved),
            "csv_data": export_approved_replies_csv(batch_id),
        }
