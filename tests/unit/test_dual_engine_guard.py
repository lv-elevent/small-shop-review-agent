"""Tests for harness/safety/dual_engine_guard.py — merge logic."""
from __future__ import annotations

from unittest.mock import MagicMock

from small_shop_agent.harness.safety.dual_engine_guard import (
    dual_engine_safety_check,
    _merge,
    DualEngineResult,
)
from small_shop_agent.schemas.review_schema import SemanticSafetyResult


class TestMergeLogic:
    def test_rule_blocked_no_semantic(self):
        """Rule blocked → final blocked, no semantic call needed."""
        result = _merge("R1", "blocked", None)
        assert result.rule_status == "blocked"
        assert result.semantic_status is None
        assert result.final_safety_status == "blocked"
        assert "规则已拦截" in result.reason

    def test_rule_blocked_wins_over_semantic_blocked(self):
        """Rule blocked → final blocked, even if semantic also says blocked."""
        semantic = SemanticSafetyResult(
            reply_id="R2",
            semantic_status="blocked",
            risk_types=["tone_rude"],
            reason="语义检测到粗鲁语气。",
        )
        result = _merge("R2", "blocked", semantic)
        assert result.final_safety_status == "blocked"
        assert "规则引擎判定 blocked" in result.reason
        assert result.escalation_reason is None

    def test_both_pass(self):
        semantic = SemanticSafetyResult(
            reply_id="R3",
            semantic_status="pass",
            risk_types=[],
        )
        result = _merge("R3", "pass", semantic)
        assert result.final_safety_status == "pass"
        assert "均通过" in result.reason

    def test_both_rewrite_agree(self):
        semantic = SemanticSafetyResult(
            reply_id="R4",
            semantic_status="rewrite_required",
            risk_types=["over_promise"],
        )
        result = _merge("R4", "rewrite_required", semantic)
        assert result.final_safety_status == "rewrite_required"

    def test_semantic_blocked_escalates_when_rule_pass(self):
        """Semantic says blocked but rule says pass → escalate."""
        semantic = SemanticSafetyResult(
            reply_id="R5",
            semantic_status="blocked",
            risk_types=["privacy_leak"],
            reason="语义检测到隐私泄露。",
            confidence=0.88,
        )
        result = _merge("R5", "pass", semantic)
        assert result.final_safety_status == "human_escalation"
        assert result.escalation_reason is not None
        assert "LLM 语义判定 blocked" in result.escalation_reason

    def test_rule_rewrite_semantic_blocked_escalates(self):
        """Rule=rewrite, semantic=blocked → escalate."""
        semantic = SemanticSafetyResult(
            reply_id="R6",
            semantic_status="blocked",
            risk_types=["legal_risk"],
            reason="可能涉及法律风险。",
        )
        result = _merge("R6", "rewrite_required", semantic)
        assert result.final_safety_status == "human_escalation"

    def test_disagree_escalates(self):
        """Rule=pass, semantic=rewrite_required → escalate."""
        semantic = SemanticSafetyResult(
            reply_id="R7",
            semantic_status="rewrite_required",
            risk_types=["marketing_spam"],
        )
        result = _merge("R7", "pass", semantic)
        assert result.final_safety_status == "human_escalation"
        assert "不一致" in result.escalation_reason


class TestDualEngineIntegration:
    def test_rule_blocked_skips_semantic(self):
        """Integration: rule blocked → no LLM call, result blocked."""
        drafts = [{
            "review_id": "R1",
            "draft_text": "我们已经开除了那个服务员。你满意了吧？",
        }]
        # provider without judge_semantic_safety → semantic skipped
        provider = MagicMock()
        del provider.judge_semantic_safety
        results = dual_engine_safety_check(
            drafts, provider=None, batch_id="test", enable_semantic=True,
        )
        r = results[0]
        assert r["rule_status"] == "blocked"
        assert r["final_safety_status"] == "blocked"

    def test_rule_pass_no_semantic_provider(self):
        """No semantic provider → just rule result."""
        drafts = [{
            "review_id": "R2",
            "draft_text": "感谢您的反馈，我们会持续改进。",
        }]
        results = dual_engine_safety_check(
            drafts, provider=None, batch_id="test", enable_semantic=False,
        )
        r = results[0]
        assert r["rule_status"] == "pass"
        assert r["final_safety_status"] == "pass"

    def test_semantic_disabled(self):
        """enable_semantic=False → no semantic call, only rule."""
        drafts = [{
            "review_id": "R3",
            "draft_text": "我们会给您全额退款。",
        }]
        results = dual_engine_safety_check(
            drafts, provider=None, batch_id="test", enable_semantic=False,
        )
        r = results[0]
        assert r["rule_status"] == "rewrite_required"
        assert r["semantic_status"] is None

    def test_disagree_escalation_integration(self):
        """Rule=pass, semantic=blocked → human_escalation."""
        mock = MagicMock()
        mock.judge_semantic_safety.return_value = [{
            "reply_id": "R4",
            "semantic_status": "blocked",
            "risk_types": ["tone_rude"],
            "reason": "语义分析：语气粗鲁。",
            "confidence": 0.85,
        }]
        drafts = [{
            "review_id": "R4",
            "draft_text": "感谢反馈。",
        }]
        results = dual_engine_safety_check(
            drafts, provider=mock, batch_id="test", enable_semantic=True,
        )
        r = results[0]
        assert r["rule_status"] == "pass"
        assert r["semantic_status"] == "blocked"
        assert r["final_safety_status"] == "human_escalation"
        assert r["escalation_reason"] is not None
