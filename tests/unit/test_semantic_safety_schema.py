"""Tests for SemanticSafetyResult schema and SEMANTIC_RISK_TYPES."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from small_shop_agent.schemas.review_schema import (
    SemanticSafetyResult,
    SEMANTIC_RISK_TYPES,
    SEMANTIC_STATUS_VALUES,
)


class TestSemanticRiskTypes:
    def test_has_eight_types(self):
        assert len(SEMANTIC_RISK_TYPES) == 8

    def test_all_expected_keys_present(self):
        expected = {
            "blame_customer", "privacy_leak", "fake_fact", "over_promise",
            "legal_risk", "employee_punishment", "tone_rude", "marketing_spam",
        }
        assert set(SEMANTIC_RISK_TYPES) == expected

    def test_status_values(self):
        assert set(SEMANTIC_STATUS_VALUES) == {"pass", "rewrite_required", "blocked"}


class TestSemanticSafetyResult:
    def test_pass_result_valid(self):
        result = SemanticSafetyResult(
            reply_id="R1",
            semantic_status="pass",
            risk_types=[],
            reason="回复安全，无风险。",
            confidence=0.95,
        )
        assert result.reply_id == "R1"
        assert result.semantic_status == "pass"

    def test_blocked_result_with_risks_valid(self):
        result = SemanticSafetyResult(
            reply_id="R2",
            semantic_status="blocked",
            risk_types=["blame_customer", "tone_rude"],
            reason="回复推卸责任且语气粗鲁。",
            confidence=0.92,
        )
        assert result.semantic_status == "blocked"
        assert len(result.risk_types) == 2

    def test_rewrite_required_valid(self):
        result = SemanticSafetyResult(
            reply_id="R3",
            semantic_status="rewrite_required",
            risk_types=["over_promise"],
            reason="回复承诺全额退款。",
            confidence=0.85,
        )
        assert result.semantic_status == "rewrite_required"

    def test_invalid_semantic_status_rejected(self):
        with pytest.raises(ValidationError):
            SemanticSafetyResult(
                reply_id="R4",
                semantic_status="invalid_status",  # type: ignore
            )

    def test_invalid_risk_type_rejected(self):
        with pytest.raises(ValidationError, match="未知风险类型"):
            SemanticSafetyResult(
                reply_id="R5",
                semantic_status="blocked",
                risk_types=["nonexistent_risk"],
            )

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            SemanticSafetyResult(
                reply_id="R6",
                semantic_status="pass",
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            SemanticSafetyResult(
                reply_id="R7",
                semantic_status="pass",
                confidence=-0.1,
            )

    def test_defaults(self):
        result = SemanticSafetyResult(
            reply_id="R8",
            semantic_status="pass",
        )
        assert result.risk_types == []
        assert result.reason == ""
        assert result.confidence == 0.80

    def test_all_eight_risk_types_accepted(self):
        result = SemanticSafetyResult(
            reply_id="R9",
            semantic_status="blocked",
            risk_types=SEMANTIC_RISK_TYPES,
            reason="所有风险类型测试。",
        )
        assert len(result.risk_types) == 8
