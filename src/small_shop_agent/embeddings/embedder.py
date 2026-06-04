"""Embedding provider - online uses OpenAI API, offline returns empty list.

text-embedding-3-small: 512-dim, $0.02/1M tokens.
When OPENAI_API_KEY is unset, all methods return empty lists and callers
fall back to keyword-only matching.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

_EMBEDDING_MODEL = "text-embedding-3-small"
_EMBEDDING_DIM = 512


class EmbeddingProvider:
    """Thin wrapper around OpenAI embeddings API.

    When the OPENAI_API_KEY env var is empty or missing, ``available`` is
    False and all embed methods return empty lists, signalling callers to
    degrade to keyword-only retrieval.
    """

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if api_key:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url=os.environ.get("OPENAI_BASE_URL", None),
            )

    @property
    def available(self) -> bool:
        return self._client is not None

    def embed_single(self, text: str) -> list[float]:
        """Return a 512-dim embedding vector, or empty list if unavailable."""
        if not self._client:
            return []
        resp = self._client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=[text[:8000]],
            dimensions=_EMBEDDING_DIM,
        )
        return resp.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return multiple embedding vectors via a single API call."""
        if not self._client:
            return [[] for _ in texts]
        resp = self._client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=[t[:8000] for t in texts],
            dimensions=_EMBEDDING_DIM,
        )
        return [r.embedding for r in resp.data]


# Singleton
_embedder: EmbeddingProvider | None = None


def get_embedder() -> EmbeddingProvider:
    """Return the process-wide EmbeddingProvider singleton."""
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingProvider()
    return _embedder
