"""InsightService — read-side access for insights and evidence."""
from __future__ import annotations

from typing import Any

from small_shop_agent.storage.repositories.insight_repository import InsightRepository


class InsightService:
    """Provides read access to batch-level insights and per-issue evidence."""

    def __init__(self) -> None:
        self._repo = InsightRepository()

    def get_top_issues(self, batch_id: str) -> list[dict[str, Any]]:
        """Return top 3 issues for a batch, ordered by rank."""
        return self._repo.get_top_issues(batch_id)

    def get_issue_evidence(self, insight_id: int) -> list[dict[str, Any]]:
        """Return evidence rows linked to a specific insight."""
        return self._repo.get_issue_evidence(insight_id)
