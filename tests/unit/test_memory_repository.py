"""Tests for storage/repositories/memory_repository.py"""
from __future__ import annotations

import pytest

from small_shop_agent.storage.repositories.memory_repository import MemoryRepository


@pytest.fixture
def repo(temp_db):
    return MemoryRepository()


class TestMemorySource:
    def test_insert_and_get_source(self, repo):
        result = repo.insert_source(
            source_id="src-test-001",
            batch_id="batch-1",
            review_id="R1",
            reply_id="1",
            approval_action_id=42,
        )
        assert result["source_id"] == "src-test-001"
        assert result["batch_id"] == "batch-1"
        assert result["review_id"] == "R1"

    def test_get_nonexistent_source(self, repo):
        assert repo.get_source("no-such-source") is None

    def test_auto_generate_source_id(self, repo):
        result = repo.insert_source(batch_id="batch-2")
        assert result["source_id"].startswith("src-")
        assert len(result["source_id"]) > 4


class TestAgentMemory:
    def _ensure_source(self, repo, source_id="src-test-001"):
        if repo.get_source(source_id) is None:
            repo.insert_source(source_id=source_id, batch_id="batch-1")

    def test_insert_and_get_memory(self, repo):
        self._ensure_source(repo)
        result = repo.insert_memory(
            memory_id="mem-001",
            store_type="coffee_shop",
            memory_type="safety_case",
            content="RT-010: 回复声称处罚员工被拦截。",
            metadata={"risk_type": "claim_employee_punished", "severity": "high"},
            source_id="src-test-001",
        )
        assert result["memory_id"] == "mem-001"
        assert result["store_type"] == "coffee_shop"
        assert result["memory_type"] == "safety_case"
        assert "处罚员工" in result["content"]
        meta = result["metadata"]
        assert meta["risk_type"] == "claim_employee_punished"

    def test_auto_generate_memory_id(self, repo):
        result = repo.insert_memory(
            store_type="coffee_shop",
            memory_type="approved_reply",
            content="Approved reply template.",
        )
        assert result["memory_id"].startswith("mem-")

    def test_list_memories_filtered(self, repo):
        # Insert 3 memories of different types
        repo.insert_memory(memory_id="m1", store_type="coffee_shop", memory_type="safety_case", content="c1")
        repo.insert_memory(memory_id="m2", store_type="coffee_shop", memory_type="approved_reply", content="c2")
        repo.insert_memory(memory_id="m3", store_type="tea_house", memory_type="safety_case", content="c3")

        # Filter by store_type
        coffee = repo.list_memories(store_type="coffee_shop")
        assert len(coffee) == 2

        # Filter by type
        safety = repo.list_memories(memory_type="safety_case")
        assert len(safety) == 2

        # Combined filter
        tea_safety = repo.list_memories(store_type="tea_house", memory_type="safety_case")
        assert len(tea_safety) == 1
        assert tea_safety[0]["memory_id"] == "m3"

    def test_count_memories(self, repo):
        repo.insert_memory(memory_id="c1", store_type="coffee_shop", memory_type="safety_case", content="x")
        repo.insert_memory(memory_id="c2", store_type="coffee_shop", memory_type="approved_reply", content="y")
        repo.insert_memory(memory_id="c3", store_type="coffee_shop", memory_type="safety_case", content="z")

        total = repo.count_memories(store_type="coffee_shop")
        assert total == 3
        safety = repo.count_memories(store_type="coffee_shop", memory_type="safety_case")
        assert safety == 2

    def test_list_memories_respects_limit(self, repo):
        for i in range(5):
            repo.insert_memory(memory_id=f"ml{i}", store_type="coffee_shop", memory_type="issue_trend", content=f"x{i}")
        results = repo.list_memories(store_type="coffee_shop", limit=3)
        assert len(results) == 3

    def test_get_nonexistent_memory(self, repo):
        assert repo.get_memory("no-such-memory") is None
