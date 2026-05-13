"""Output contracts — Pydantic model references used by Schema Guard."""
from __future__ import annotations

from small_shop_agent.services.pipeline_steps import (
    _ClassificationItem,
    _SentimentItem,
    _InsightItem,
    _ReplyItem,
)

# Re-export for harness consumers
ClassificationContract = _ClassificationItem
SentimentContract = _SentimentItem
InsightContract = _InsightItem
ReplyContract = _ReplyItem

__all__ = [
    "ClassificationContract",
    "SentimentContract",
    "InsightContract",
    "ReplyContract",
]
