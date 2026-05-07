"""TraceService — read/write access for workflow traces."""
from __future__ import annotations

from typing import Any

from small_shop_agent.storage.repositories.trace_repository import TraceRepository


class TraceService:
    """Provides trace logging and retrieval for the workflow pipeline."""

    def __init__(self) -> None:
        self._repo = TraceRepository()

    def log_step(self, trace_event: dict[str, Any]) -> dict[str, Any]:
        """Log a single trace step. trace_event must contain keys matching
        TraceRepository.log_step parameters."""
        return self._repo.log_step(**trace_event)

    def get_trace(self, batch_id: str) -> list[dict[str, Any]]:
        """Return all traces for a batch, ordered by id."""
        return self._repo.get_traces(batch_id)

    def get_latest_trace(self) -> list[dict[str, Any]]:
        """Return traces for the most recently traced batch."""
        return self._repo.get_latest_trace()
