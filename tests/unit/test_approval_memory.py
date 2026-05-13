"""Tests: approval actions persist to agent_memories."""
from __future__ import annotations

import pytest

from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.memory_repository import MemoryRepository

BATCH_ID = "test-batch-memo"
REVIEW_ID = "R99"


@pytest.fixture
def _setup_memo_db(temp_db):
    BatchRepository().create_batch(batch_id=BATCH_ID, total_rows=1, valid_review_count=1)
    ReviewRepository().bulk_insert_reviews(BATCH_ID, [{
        "review_id": REVIEW_ID, "rating": 2, "review_text": "服务不好。",
    }])


@pytest.fixture
def _draft_pass(_setup_memo_db):
    ReplyRepository().bulk_insert_drafts(BATCH_ID, [{
        "review_id": REVIEW_ID, "original_review": "服务不好。",
        "draft_text": "抱歉，我们会改进。",
        "safety_status": "pass", "risk_types": [],
        "approval_status": "pending", "model_name": "test",
    }])


@pytest.fixture
def _draft_blocked(_setup_memo_db):
    ReplyRepository().bulk_insert_drafts(BATCH_ID, [{
        "review_id": REVIEW_ID, "original_review": "服务不好。",
        "draft_text": "已经开除了那名员工。",
        "safety_status": "blocked", "risk_types": ["claim_employee_punished"],
        "approval_status": "pending", "model_name": "test",
    }])


class TestApproveMemory:
    def test_approve_creates_approved_reply_memory(self, temp_db, _draft_pass):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        result = svc.approve_draft(drafts[0]["id"])
        assert result["success"] is True

        memos = MemoryRepository().list_memories(memory_type="approved_reply")
        assert len(memos) >= 1
        m = memos[0]
        assert "抱歉，我们会改进" in m["content"]
        assert m["metadata"]["approval_action"] == "approve"


class TestEditMemory:
    def test_edit_creates_both_memories(self, temp_db, _draft_pass):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        result = svc.edit_draft(drafts[0]["id"], "我们会针对性改进服务流程。")
        assert result["success"] is True

        # approved_reply memory (after text)
        approved = MemoryRepository().list_memories(memory_type="approved_reply")
        assert len(approved) >= 1
        assert "针对性改进" in approved[0]["content"]

        # safety_case memory (before text)
        safety = MemoryRepository().list_memories(memory_type="safety_case")
        assert len(safety) >= 1
        before_entry = [m for m in safety if "修改前" in m["content"]]
        assert len(before_entry) >= 1
        assert "抱歉，我们会改进" in before_entry[0]["content"]


class TestRejectMemory:
    def test_reject_pass_creates_rejected_reply(self, temp_db, _draft_pass):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        result = svc.reject_draft(drafts[0]["id"], "回复不够具体。")
        assert result["success"] is True

        memos = MemoryRepository().list_memories(memory_type="rejected_reply")
        assert len(memos) >= 1
        assert "驳回原因" in memos[0]["content"]
        assert memos[0]["metadata"]["reject_reason"] == "回复不够具体。"

    def test_reject_blocked_creates_safety_case(self, temp_db, _draft_blocked):
        svc = ReplyService()
        drafts = ReplyRepository().list_drafts(BATCH_ID)
        result = svc.reject_draft(drafts[0]["id"], "违反安全规则。")
        assert result["success"] is True

        memos = MemoryRepository().list_memories(memory_type="safety_case")
        blocked_memos = [m for m in memos if "已经开除了" in m["content"]]
        assert len(blocked_memos) >= 1
