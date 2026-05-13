"""Pydantic v2 schemas for CSV review row, batch summary, and semantic safety."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ReviewRow(BaseModel):
    """Schema for a single review row from CSV input."""
    review_id: str = ""
    date: str = ""
    platform: str = ""
    rating: int = Field(ge=1, le=5, default=3)
    review_text: str = ""


class BatchSummary(BaseModel):
    """Schema for batch-level summary after processing."""
    batch_id: str
    store_type: str = "coffee_shop"
    total_rows: int = 0
    valid_review_count: int = 0
    negative_review_count: int = 0
    pending_reply_count: int = 0


# ── Semantic Safety Judge ──────────────────────────────────────────────

SEMANTIC_RISK_TYPES: list[str] = [
    "blame_customer",       # 推卸责任
    "privacy_leak",         # 隐私泄露
    "fake_fact",            # 编造事实
    "over_promise",         # 过度承诺
    "legal_risk",           # 法律风险
    "employee_punishment",  # 声称处罚员工
    "tone_rude",            # 语气粗鲁
    "marketing_spam",       # 营销垃圾信息
]

SEMANTIC_STATUS_VALUES = ("pass", "rewrite_required", "blocked")


class SemanticSafetyResult(BaseModel):
    """LLM semantic safety check result for a single reply draft.

    Distinct from the keyword-based Safety Guard — this model captures
    nuanced, context-dependent risks that pattern matching cannot.
    """
    reply_id: str
    semantic_status: Literal["pass", "rewrite_required", "blocked"]
    risk_types: list[str] = Field(default_factory=list)
    reason: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.80)

    @field_validator("risk_types")
    @classmethod
    def _check_risk_types(cls, v: list[str]) -> list[str]:
        for rt in v:
            if rt not in SEMANTIC_RISK_TYPES:
                raise ValueError(
                    f"未知风险类型：{rt!r}。允许值：{SEMANTIC_RISK_TYPES}"
                )
        return v
