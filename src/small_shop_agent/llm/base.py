"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Interface that all LLM providers must implement."""

    @abstractmethod
    def classify_reviews(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Classify each review into topics."""

    @abstractmethod
    def analyze_sentiment(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Analyze sentiment and severity for each review."""

    @abstractmethod
    def generate_insights(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate top issues with evidence from review analysis."""

    @abstractmethod
    def draft_replies(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Draft replies for negative candidate reviews."""

    @abstractmethod
    def check_safety(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Check safety of reply drafts and set safety_status/risk_types."""

    def judge_semantic_safety(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Semantic safety judge — optional, default no-op (passes all).

        Subclasses override to provide LLM-based semantic safety analysis.
        Each returned dict should contain: reply_id, semantic_status,
        risk_types, reason, confidence.
        """
        return [{
            "reply_id": d.get("review_id", ""),
            "semantic_status": "pass",
            "risk_types": [],
            "reason": "语义判定未启用（provider 未实现）。",
            "confidence": 0.80,
        } for d in drafts]
