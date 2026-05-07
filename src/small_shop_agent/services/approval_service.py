"""ApprovalService — records human approval actions for audit trail."""
from __future__ import annotations

from typing import Any

from small_shop_agent.storage.repositories.reply_repository import ReplyRepository


class ApprovalService:
    """Thin wrapper around ReplyRepository.insert_approval_action for audit logging."""

    def __init__(self) -> None:
        self._repo = ReplyRepository()

    def record_approval_action(
        self,
        *,
        draft_id: int,
        batch_id: str,
        review_id: str,
        action: str,
        before_text: str = "",
        after_text: str = "",
        reject_reason: str = "",
    ) -> dict[str, Any]:
        """Record a single approval action (approve/edit/reject)."""
        return self._repo.insert_approval_action(
            draft_id=draft_id,
            batch_id=batch_id,
            review_id=review_id,
            action=action,
            before_text=before_text,
            after_text=after_text,
            reject_reason=reject_reason,
        )
