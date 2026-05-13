"""MemoryRetriever — keyword-search agent_memories for reply drafting guidance."""
from __future__ import annotations

from typing import Any

from small_shop_agent.storage.repositories.memory_repository import MemoryRepository


class MemoryRetriever:
    """Retrieve relevant agent memories for reply generation context."""

    def __init__(self) -> None:
        self._repo = MemoryRepository()

    def retrieve(
        self,
        store_type: str = "coffee_shop",
        keywords: list[str] | None = None,
        limit_per_type: int = 3,
    ) -> dict[str, list[dict[str, Any]]]:
        """Search memories by store_type and keyword matching.

        Returns ``{approved: [...], rejected: [...], safety: [...]}``.
        Each list is capped at *limit_per_type*.
        """
        keywords = keywords or []
        lower_kw = [k.lower() for k in keywords if k.strip()]

        approved = self._search("approved_reply", store_type, lower_kw, limit_per_type)
        rejected = self._search("rejected_reply", store_type, lower_kw, limit_per_type)
        safety = self._search("safety_case", store_type, lower_kw, limit_per_type)

        return {
            "approved": approved,
            "rejected": rejected,
            "safety": safety,
        }

    def _search(
        self,
        memory_type: str,
        store_type: str,
        keywords: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch all memories of *memory_type*, filter by keyword, cap."""
        all_memos = self._repo.list_memories(
            store_type=store_type,
            memory_type=memory_type,
            limit=100,
        )
        if not keywords:
            return all_memos[:limit]

        scored: list[tuple[int, dict]] = []
        for m in all_memos:
            content_lower = m.get("content", "").lower()
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]
