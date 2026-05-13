"""Dual-engine safety guard — Rule (keyword) + LLM Semantic Judge.

Rule runs first.  Blocked-by-rule always wins.  Semantic judge is called
for borderline / rewrite-required cases.  Disagreements escalate to human.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from small_shop_agent.harness.safety.safety_guardrails import check_reply_safety
from small_shop_agent.schemas.review_schema import SemanticSafetyResult
from small_shop_agent.utils.logger import log_step


# ── Result dataclass ────────────────────────────────────────────────────

@dataclass
class DualEngineResult:
    """Merged safety result for a single reply draft."""
    reply_id: str
    rule_status: str = "pass"            # pass | rewrite_required | blocked
    semantic_status: str | None = None   # None = semantic judge not invoked
    final_safety_status: str = "pass"    # pass | rewrite_required | blocked | human_escalation
    risk_types: list[str] = field(default_factory=list)
    reason: str = ""
    escalation_reason: str | None = None
    semantic_confidence: float | None = None


# ── Merge helpers ───────────────────────────────────────────────────────

_RULE_PRIORITY = "规则引擎判定 blocked，LLM 语义判定不覆盖。"
_ESCALATE_DISAGREE = "规则与语义判定不一致，提升至人工。"
_ESCALATE_SEMANTIC_BLOCKED = "LLM 语义判定 blocked，规则未拦截，提升至人工。"
_BOTH_PASS = "规则与语义判定均通过。"
_SEMANTIC_SKIPPED_BLOCKED = "规则已拦截，跳过语义判定。"
_SEMANTIC_AGREE_REWRITE = "规则与语义一致判定需改写。"


def _merge(
    reply_id: str,
    rule_status: str,
    semantic: SemanticSafetyResult | None,
) -> DualEngineResult:
    """Merge rule and semantic results into a final decision."""
    if semantic is None:
        # Rule blocked — no semantic call needed
        if rule_status == "blocked":
            return DualEngineResult(
                reply_id=reply_id,
                rule_status=rule_status,
                final_safety_status="blocked",
                reason=_SEMANTIC_SKIPPED_BLOCKED,
            )
        return DualEngineResult(
            reply_id=reply_id,
            rule_status=rule_status,
            final_safety_status=rule_status,
            reason="仅规则引擎运行（语义判定未启用）。",
        )

    s_status = semantic.semantic_status

    # Rule blocked always wins
    if rule_status == "blocked":
        return DualEngineResult(
            reply_id=reply_id,
            rule_status=rule_status,
            semantic_status=s_status,
            final_safety_status="blocked",
            risk_types=semantic.risk_types,
            reason=_RULE_PRIORITY,
            escalation_reason=None,
            semantic_confidence=semantic.confidence,
        )

    # Both agree on pass
    if rule_status == "pass" and s_status == "pass":
        return DualEngineResult(
            reply_id=reply_id,
            rule_status=rule_status,
            semantic_status=s_status,
            final_safety_status="pass",
            risk_types=[],
            reason=_BOTH_PASS,
            semantic_confidence=semantic.confidence,
        )

    # Both agree on rewrite
    if rule_status == "rewrite_required" and s_status == "rewrite_required":
        return DualEngineResult(
            reply_id=reply_id,
            rule_status=rule_status,
            semantic_status=s_status,
            final_safety_status="rewrite_required",
            risk_types=semantic.risk_types,
            reason=_SEMANTIC_AGREE_REWRITE,
            semantic_confidence=semantic.confidence,
        )

    # Semantic says blocked but rule didn't → escalate
    if s_status == "blocked" and rule_status != "blocked":
        return DualEngineResult(
            reply_id=reply_id,
            rule_status=rule_status,
            semantic_status=s_status,
            final_safety_status="human_escalation",
            risk_types=semantic.risk_types,
            reason=semantic.reason,
            escalation_reason=_ESCALATE_SEMANTIC_BLOCKED,
            semantic_confidence=semantic.confidence,
        )

    # Any other disagreement → escalate
    return DualEngineResult(
        reply_id=reply_id,
        rule_status=rule_status,
        semantic_status=s_status,
        final_safety_status="human_escalation",
        risk_types=semantic.risk_types,
        reason=semantic.reason,
        escalation_reason=_ESCALATE_DISAGREE,
        semantic_confidence=semantic.confidence,
    )


# ── Main entry point ────────────────────────────────────────────────────

def dual_engine_safety_check(
    drafts: list[dict[str, Any]],
    provider=None,
    *,
    batch_id: str = "",
    enable_semantic: bool = True,
    trace_repo=None,
) -> list[dict[str, Any]]:
    """Run dual-engine safety check on a list of reply drafts.

    Parameters
    ----------
    drafts : list[dict]
        Each must have ``review_id`` and ``draft_text``.
    provider : optional
        LLM provider with ``judge_semantic_safety()`` method.
        If None or missing the method, semantic judge is skipped.
    batch_id : str
    enable_semantic : bool
        If False, only the rule guard runs (same as existing behaviour).
    trace_repo : optional TraceRepository

    Returns
    -------
    list[dict]
        Each draft dict enriched with: rule_status, semantic_status,
        final_safety_status, escalation_reason, risk_types, reason.
        Backward-compatible: ``safety_status`` = final_safety_status,
        ``approval_status`` set to "blocked" when final=blocked.
    """
    t0 = time.time()
    has_semantic = (
        enable_semantic
        and provider is not None
        and hasattr(provider, "judge_semantic_safety")
    )

    results: list[dict[str, Any]] = []
    rule_blocked = 0
    semantic_called = 0
    escalated = 0

    for d in drafts:
        entry = dict(d)
        rid = entry.get("review_id", "")
        draft_text = str(entry.get("draft_text", ""))

        # ── Step 1: Rule check (always) ───────────────────────────────
        rule_result = check_reply_safety(draft_text)
        entry["rule_status"] = rule_result.status
        entry["rule_risk_types"] = rule_result.risk_flags

        semantic: SemanticSafetyResult | None = None

        # ── Step 2: Decide whether to call semantic judge ──────────────
        if has_semantic and rule_result.status != "blocked":
            try:
                semantic_list = provider.judge_semantic_safety([entry])
                if semantic_list and len(semantic_list) > 0:
                    raw = semantic_list[0]
                    semantic = SemanticSafetyResult(
                        reply_id=rid,
                        semantic_status=raw.get("semantic_status", "pass"),
                        risk_types=raw.get("risk_types", []),
                        reason=raw.get("reason", ""),
                        confidence=raw.get("confidence", 0.80),
                    )
                    semantic_called += 1
            except Exception as exc:
                logger.warning(f"语义安全判定失败 {rid}：{exc}，回退至仅规则。")
                log_step("semantic_safety_error", batch_id or "unknown",
                         review_id=rid, error=str(exc))

        # ── Step 3: Merge ─────────────────────────────────────────────
        merged = _merge(rid, rule_result.status, semantic)

        entry["semantic_status"] = merged.semantic_status
        entry["final_safety_status"] = merged.final_safety_status
        entry["risk_types"] = merged.risk_types
        entry["reason"] = merged.reason
        entry["escalation_reason"] = merged.escalation_reason
        entry["semantic_confidence"] = merged.semantic_confidence

        # Backward-compatible safety_status
        entry["safety_status"] = merged.final_safety_status
        if merged.final_safety_status == "blocked":
            entry["approval_status"] = "blocked"
            rule_blocked += 1
        elif merged.final_safety_status == "human_escalation":
            escalated += 1

        log_step("dual_safety_check", batch_id or "unknown",
                 review_id=rid,
                 rule_status=merged.rule_status,
                 semantic_status=merged.semantic_status,
                 final_status=merged.final_safety_status)

        results.append(entry)

    # ── Trace ──────────────────────────────────────────────────────────
    if trace_repo is not None:
        latency = int((time.time() - t0) * 1000)
        trace_repo.log_step(
            trace_id=f"trace-{batch_id}" if batch_id else "dual-engine",
            batch_id=batch_id or "unknown",
            step_name="safety_check",
            status="warning" if escalated else ("warning" if rule_blocked > 0 else "passed"),
            input_summary=f"{len(drafts)} 条草稿",
            output_summary=(
                f"规则拦截={rule_blocked}, "
                f"语义调用={semantic_called}, "
                f"人工升级={escalated}"
            ),
            latency_ms=latency,
            model_name="dual_engine",
        )

    return results
