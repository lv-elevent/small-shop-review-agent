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
