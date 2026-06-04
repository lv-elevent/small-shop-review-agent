"""MemoryRetriever -- hybrid keyword + embedding retrieval for reply drafting.

Online mode: uses text-embedding-3-small to generate query vectors and
ranks memories by cosine similarity weighted with keyword hits.
Offline/demo mode: falls back to keyword-only LIKE matching.
"""
from __future__ import annotations

import json
from typing import Any

from small_shop_agent.core.config import HYBRID_VECTOR_WEIGHT, HYBRID_KEYWORD_WEIGHT, HYBRID_MIN_SCORE
from small_shop_agent.storage.repositories.memory_repository import MemoryRepository


class MemoryRetriever:
    """Retrieve relevant agent memories for reply generation context.

    Hybrid retrieval: vector similarity (when embedding is available) +
    keyword matching, with configurable weights and score threshold.
    """

    def __init__(self) -> None:
        self._repo = MemoryRepository()

    def retrieve(
        self,
        store_type: str = "coffee_shop",
        keywords: list[str] | None = None,
        limit_per_type: int = 3,
        query_text: str = "",
    ) -> dict[str, list[dict[str, Any]]]:
        """Search memories by store_type, using hybrid ranking.

        Args:
            store_type: Memory store identifier.
            keywords: Keyword list for keyword-matching (always used).
            limit_per_type: Max results per memory type.
            query_text: Full review text to generate embedding query vector.
                        When embedder is unavailable, this is ignored and
                        keyword-only matching is used.

        Returns:
            {approved: [...], rejected: [...], safety: [...]}
        """
        keywords = keywords or []
        lower_kw = [k.lower() for k in keywords if k.strip()]

        # Resolve query vector (empty list when unavailable)
        query_vec = self._get_query_vec(query_text) if query_text else []

        approved = self._rank(query_vec, "approved_reply", store_type, lower_kw, limit_per_type)
        rejected = self._rank(query_vec, "rejected_reply", store_type, lower_kw, limit_per_type)
        safety = self._rank(query_vec, "safety_case", store_type, lower_kw, limit_per_type)

        return {
            "approved": approved,
            "rejected": rejected,
            "safety": safety,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_query_vec(self, query_text: str) -> list[float]:
        """Generate embedding vector for the query text."""
        try:
            from small_shop_agent.embeddings.embedder import get_embedder
            embedder = get_embedder()
            if embedder.available:
                return embedder.embed_single(query_text)
        except Exception:
            pass
        return []

    def _rank(
        self,
        query_vec: list[float],
        memory_type: str,
        store_type: str,
        keywords: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch memories and rank by hybrid scoring or keyword-only."""
        all_memos = self._repo.list_memories(
            store_type=store_type,
            memory_type=memory_type,
            limit=100,
        )

        if not query_vec:
            # Degrade to keyword-only matching
            return self._keyword_match(all_memos, keywords, limit)

        # Hybrid: vector + keyword (pure-Python dot product = cosine sim on normalized vectors)
        scored: list[tuple[float, dict]] = []
        for m in all_memos:
            vec_score = self._cosine_sim(query_vec, m)
            kw_score = self._keyword_score(m, keywords)
            final = HYBRID_VECTOR_WEIGHT * vec_score + HYBRID_KEYWORD_WEIGHT * kw_score
            if final >= HYBRID_MIN_SCORE:
                scored.append((final, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    # ------------------------------------------------------------------
    # Scoring functions
    # ------------------------------------------------------------------

    @staticmethod
    def _dot(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def _cosine_sim(query_vec: list[float], memory: dict) -> float:
        """Compute cosine similarity between query and memory embedding.

        Embeddings stored as JSON array; vectors are normalized by the
        API so dot-product equals cosine similarity.
        """
        raw = memory.get("embedding")
        if not raw:
            return 0.0
        try:
            emb = json.loads(raw) if isinstance(raw, str) else raw
            if not emb:
                return 0.0
            return _dot(query_vec, emb)
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _keyword_score(memory: dict, keywords: list[str]) -> float:
        """Return normalized keyword hit score (0.0 to 1.0)."""
        if not keywords:
            return 0.0
        content_lower = memory.get("content", "").lower()
        hits = sum(1 for kw in keywords if kw in content_lower)
        return min(hits / len(keywords), 1.0)

    @staticmethod
    def _keyword_match(
        memories: list[dict],
        keywords: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Original keyword-only retrieval (degraded path)."""
        if not keywords:
            return memories[:limit]

        scored: list[tuple[int, dict]] = []
        for m in memories:
            content_lower = m.get("content", "").lower()
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]
