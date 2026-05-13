"""Tests for agent_runtime/memory_retriever.py"""
from __future__ import annotations

import pytest

from small_shop_agent.agent_runtime.memory_retriever import MemoryRetriever
from small_shop_agent.storage.repositories.memory_repository import MemoryRepository

STORE = "coffee_shop"


@pytest.fixture
def _seed_memories(temp_db):
    repo = MemoryRepository()
    repo.insert_source(source_id="src-1", batch_id="b1", review_id="R1")
    repo.insert_source(source_id="src-2", batch_id="b2", review_id="R2")
    repo.insert_source(source_id="src-3", batch_id="b3", review_id="R3")
    repo.insert_source(source_id="src-4", batch_id="b4", review_id="R4")

    repo.insert_memory(
        memory_id="m1", store_type=STORE, memory_type="approved_reply",
        content="感谢您的反馈，我们会改进咖啡品质。",
        source_id="src-1",
    )
    repo.insert_memory(
        memory_id="m2", store_type=STORE, memory_type="approved_reply",
        content="非常抱歉服务不周，已加强员工培训。",
        source_id="src-2",
    )
    repo.insert_memory(
        memory_id="m3", store_type=STORE, memory_type="rejected_reply",
        content="驳回原因：回复不够具体，需要针对问题说明改进措施。原文：我们会改进的。",
        source_id="src-3",
    )
    repo.insert_memory(
        memory_id="m4", store_type=STORE, memory_type="safety_case",
        content="修改前：已开除员工。修改后：我们会加强管理。",
        source_id="src-4",
    )
    repo.insert_memory(
        memory_id="m5", store_type=STORE, memory_type="approved_reply",
        content="感谢光临，您反馈的卫生问题我们已彻底整改。",
        source_id="src-1",
    )
    repo.insert_memory(
        memory_id="m6", store_type=STORE, memory_type="rejected_reply",
        content="驳回原因：推卸责任。原文：是你自己的问题。",
        source_id="src-2",
    )


class TestMemoryRetriever:
    def test_retrieve_returns_all_types(self, temp_db, _seed_memories):
        r = MemoryRetriever()
        result = r.retrieve(store_type=STORE)
        assert "approved" in result
        assert "rejected" in result
        assert "safety" in result

    def test_retrieve_with_keyword(self, temp_db, _seed_memories):
        r = MemoryRetriever()
        result = r.retrieve(store_type=STORE, keywords=["咖啡", "服务"])
        approved = result["approved"]
        assert len(approved) >= 1
        assert any("咖啡" in m["content"] for m in approved)

    def test_retrieve_respects_limit(self, temp_db, _seed_memories):
        r = MemoryRetriever()
        result = r.retrieve(store_type=STORE, keywords=[""], limit_per_type=2)
        assert len(result["approved"]) <= 2

    def test_no_keywords_returns_all_capped(self, temp_db, _seed_memories):
        r = MemoryRetriever()
        result = r.retrieve(store_type=STORE, keywords=[])
        assert len(result["approved"]) <= 3

    def test_empty_store_no_error(self, temp_db):
        r = MemoryRetriever()
        result = r.retrieve(store_type="nonexistent")
        assert result["approved"] == []
        assert result["rejected"] == []
        assert result["safety"] == []

    def test_rejected_not_in_approved(self, temp_db, _seed_memories):
        r = MemoryRetriever()
        result = r.retrieve(store_type=STORE)
        approved_ids = {m["memory_id"] for m in result["approved"]}
        rejected_ids = {m["memory_id"] for m in result["rejected"]}
        assert "m3" not in approved_ids
        assert "m6" not in approved_ids
        assert "m3" in rejected_ids
        assert "m6" in rejected_ids
