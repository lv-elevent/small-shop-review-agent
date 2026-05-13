"""Tests for harness/safety/safety_guardrails.py"""
from __future__ import annotations

import pytest
from small_shop_agent.harness.safety.safety_guardrails import (
    check_reply_safety,
    check_many_replies,
    SafetyCheckResult,
)


class TestCheckReplySafety:
    def test_attack_customer_blocked(self):
        result = check_reply_safety("你活该")
        assert result.status == "blocked"
        assert "attack_customer" in result.risk_flags

    def test_disclose_privacy_blocked(self):
        result = check_reply_safety("您的电话是138xxxx")
        assert result.status == "blocked"
        assert "disclose_privacy" in result.risk_flags

    def test_claim_employee_punished_blocked(self):
        result = check_reply_safety("该员工已经被开除")
        assert result.status == "blocked"
        assert "claim_employee_punished" in result.risk_flags

    def test_fabricated_fact_blocked(self):
        result = check_reply_safety("我们已经查明监控录像显示")
        assert result.status == "blocked"
        assert "fabricated_fact" in result.risk_flags

    def test_unfounded_compensation_rewrite_required(self):
        result = check_reply_safety("我们全额退款给您")
        assert result.status == "rewrite_required"
        assert "unfounded_compensation" in result.risk_flags

    def test_over_marketing_rewrite_required(self):
        result = check_reply_safety("新品上市限时优惠，会员专享")
        assert result.status == "rewrite_required"
        assert "over_marketing" in result.risk_flags

    def test_defensive_blame_shift_rewrite_required(self):
        result = check_reply_safety("是您自己没看清楚")
        assert result.status == "rewrite_required"
        assert "defensive_or_blame_shift" in result.risk_flags

    def test_safe_reply_passes(self):
        result = check_reply_safety("非常抱歉给您带来不便，我们会改进服务。")
        assert result.status == "pass"
        assert len(result.risk_flags) == 0

    def test_empty_reply_blocked(self):
        result = check_reply_safety("")
        assert result.status == "blocked"
        assert "empty_reply" in result.risk_flags

    def test_english_keyword_blocked(self):
        result = check_reply_safety("you deserve it")
        assert result.status == "blocked"
        assert "attack_customer" in result.risk_flags

    def test_none_reply_is_safe(self):
        """None input is treated as empty string -> blocked."""
        result = check_reply_safety(None)  # type: ignore[arg-type]
        assert result.status == "blocked"


class TestCheckManyReplies:
    def test_batch_preserves_all_drafts(self):
        drafts = [
            {"review_id": "A", "draft_text": "我们会改进。"},
            {"review_id": "B", "draft_text": "你活该"},
            {"review_id": "C", "draft_text": "新品上市限时优惠"},
        ]
        results = check_many_replies(drafts, batch_id="test-batch")
        assert len(results) == 3
        assert results[0]["safety_status"] == "pass"
        assert results[1]["safety_status"] == "blocked"
        assert results[2]["safety_status"] == "rewrite_required"

    def test_batch_preserves_original_fields(self):
        drafts = [{"review_id": "X", "draft_text": "谢谢反馈。", "custom": 42}]
        results = check_many_replies(drafts, batch_id="test-batch")
        assert results[0]["custom"] == 42
        assert results[0]["review_id"] == "X"

    def test_blocked_sets_approval_status(self):
        drafts = [{"review_id": "Z", "draft_text": "你活该"}]
        results = check_many_replies(drafts, batch_id="test-batch")
        assert results[0]["approval_status"] == "blocked"
