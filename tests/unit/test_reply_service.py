"""Tests for services/reply_service.py — approve/edit/reject workflow."""
from __future__ import annotations

import pytest

from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository


BATCH_ID = "test-batch-reply"
REVIEW_ID = "R1"


@pytest.fixture
def _setup_batch_and_review(temp_db):
    """Create minimal batch + review row so FK constraints pass."""
    BatchRepository().create_batch(
        batch_id=BATCH_ID, total_rows=1, valid_review_count=1,
    )
    ReviewRepository().bulk_insert_reviews(BATCH_ID, [{
        "review_id": REVIEW_ID, "rating": 1,
        "review_text": "Terrible service.",
    }])


@pytest.fixture
def _draft_pass(_setup_batch_and_review):
    ReplyRepository().bulk_insert_drafts(BATCH_ID, [{
        "review_id": REVIEW_ID, "original_review": "Terrible service.",
        "draft_text": "Sorry for the experience.",
        "safety_status": "pass", "risk_types": [],
        "approval_status": "pending", "model_name": "test",
    }])


@pytest.fixture
def _draft_blocked(_setup_batch_and_review):
    ReplyRepository().bulk_insert_drafts(BATCH_ID, [{
        "review_id": REVIEW_ID, "original_review": "Terrible service.",
        "draft_text": "We fired the staff.",
        "safety_status": "blocked", "risk_types": ["claim_employee_punished"],
        "approval_status": "pending", "model_name": "test",
    }])


class TestApproveDraft:
    def test_approve_pass_draft_succeeds(self, temp_db, _draft_pass):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        assert len(drafts) == 1
        result = svc.approve_draft(drafts[0]["id"])
        assert result["success"] is True
        assert result["draft"]["approval_status"] == "approved"

    def test_approve_blocked_draft_fails(self, temp_db, _draft_blocked):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        result = svc.approve_draft(drafts[0]["id"])
        assert result["success"] is False
        assert "Cannot approve" in result["error"]

    def test_approve_nonexistent_draft_fails(self, temp_db, _setup_batch_and_review):
        svc = ReplyService()
        result = svc.approve_draft(9999)
        assert result["success"] is False
        assert "not found" in str(result["error"]).lower()


class TestEditDraft:
    def test_edit_draft_records_before_after(self, temp_db, _draft_pass):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        original_text = drafts[0]["draft_text"]
        new_text = "We are very sorry and will improve."

        result = svc.edit_draft(drafts[0]["id"], new_text)
        assert result["success"] is True
        assert result["draft"]["approval_status"] == "edited"

        # Verify approval_actions has the edit record
        from small_shop_agent.storage.sqlite_session import get_session
        with get_session() as conn:
            actions = conn.execute(
                "SELECT * FROM approval_actions WHERE batch_id = ? AND review_id = ?",
                (BATCH_ID, REVIEW_ID),
            ).fetchall()
        assert len(actions) >= 1
        edit_action = [a for a in actions if a["action"] == "edit"]
        assert len(edit_action) == 1
        assert edit_action[0]["before_text"] == original_text
        assert edit_action[0]["after_text"] == new_text

    def test_edit_draft_empty_text_fails(self, temp_db, _draft_pass):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        result = svc.edit_draft(drafts[0]["id"], "")
        assert result["success"] is False
        assert "cannot be empty" in result["error"].lower()

        result2 = svc.edit_draft(drafts[0]["id"], "   ")
        assert result2["success"] is False


class TestRejectDraft:
    def test_reject_draft_records_reason(self, temp_db, _draft_pass):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        reason = "Reply does not address the specific complaint."

        result = svc.reject_draft(drafts[0]["id"], reason)
        assert result["success"] is True
        assert result["draft"]["approval_status"] == "rejected"

        from small_shop_agent.storage.sqlite_session import get_session
        with get_session() as conn:
            actions = conn.execute(
                "SELECT * FROM approval_actions WHERE batch_id = ? AND review_id = ?",
                (BATCH_ID, REVIEW_ID),
            ).fetchall()
        reject_action = [a for a in actions if a["action"] == "reject"]
        assert len(reject_action) == 1
        assert reject_action[0]["reject_reason"] == reason
