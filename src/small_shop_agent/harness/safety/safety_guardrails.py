"""Safety Guardrails — rule-based reply safety checker. No LLM calls."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Two-tier keyword patterns ──────────────────────────────────────────

BLOCKED_PATTERNS: dict[str, list[str]] = {
    "attack_customer": [
        "活该", "你自找的", "你这种人", "无理取闹", "脑子有",
        "你有病", "你傻", "蠢货", "垃圾顾客", "没素质",
        "idiot", "stupid", "you deserve it", "your problem",
    ],
    "disclose_privacy": [
        "你的电话是", "您的电话是", "你的地址是", "您的地址是",
        "你的身份证", "您的身份证", "你的手机号", "您的手机号",
        "你住在", "您住在", "你个人信息", "您个人信息", "你的微信号",
        "your phone number is", "your address is",
    ],
    "claim_employee_punished": [
        "已经开除", "已开除", "已被开除", "被开除",
        "已辞退", "已被辞退", "被辞退", "已经辞退",
        "已解雇", "已被解雇", "被解雇",
        "已经处罚", "已被处罚", "被处罚", "已处罚",
        "已罚款", "被罚款", "扣了工资", "扣发奖金",
        "已经处分", "已被处分", "已通报批评", "已停职",
        "fired the employee", "terminated the staff", "has been dismissed",
        "has been fired", "was fired", "got fired", "been terminated",
    ],
    "fabricated_fact": [
        "我们已经查明", "经调查确认", "监控录像显示", "调取监控发现",
        "经核查确认您", "我们调取了", "查看了监控发现",
        "we investigated and confirmed", "cctv footage shows",
    ],
}

REWRITE_PATTERNS: dict[str, list[str]] = {
    "unfounded_compensation": [
        "全额退款", "全额赔付", "免费赔偿", "双倍赔偿", "三倍赔偿",
        "赔您", "免单", "给您补偿金", "现金赔偿", "赔偿您",
        "full refund", "compensate you with cash",
    ],
    "over_marketing": [
        "新品上市", "限时优惠", "折扣活动", "会员专享", "买一送一",
        "充值送", "办卡优惠", "关注公众号", "扫码领",
        "下载APP", "加入会员", "转发朋友圈", "集赞",
        "new product launch", "limited time offer", "join our membership",
    ],
    "defensive_or_blame_shift": [
        "是您自己", "是您没有", "是客人自己", "是顾客自己",
        "您记错了", "您搞错了", "不是我们的问题", "跟我们无关",
        "您自己的原因", "您没看清楚", "是您的理解有误",
        "your fault", "you forgot", "you misremembered", "not our problem",
    ],
}


def _match_patterns(text: str, patterns: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """Return (matched_categories, matched_keywords) for the given patterns."""
    cats: list[str] = []
    hits: list[str] = []
    lower = text.lower()
    for category, keywords in patterns.items():
        for kw in keywords:
            if kw.lower() in lower:
                cats.append(category)
                hits.append(kw)
    return cats, hits


# ── Result dataclass ───────────────────────────────────────────────────

@dataclass
class SafetyCheckResult:
    """Result of a single reply safety check."""
    status: str = "pass"
    risk_flags: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    safe_reply: str | None = None
    original_reply: str | None = None


# ── Core functions ─────────────────────────────────────────────────────

def check_reply_safety(
    reply_text: str,
    review_context: dict[str, Any] | None = None,
) -> SafetyCheckResult:
    """Check a single reply draft against safety rules.

    Args:
        reply_text: The draft reply text.
        review_context: Optional original review dict (review_id, review_text, rating, etc.)

    Returns:
        SafetyCheckResult with status, risk_flags, and reasons.
    """
    stripped = (reply_text or "").strip()

    # Empty reply
    if not stripped:
        return SafetyCheckResult(
            status="blocked",
            risk_flags=["empty_reply"],
            reasons=["回复内容为空，不允许发布。"],
            original_reply=reply_text,
        )

    blocked_cats, blocked_hits = _match_patterns(stripped, BLOCKED_PATTERNS)
    if blocked_cats:
        return SafetyCheckResult(
            status="blocked",
            risk_flags=blocked_cats,
            reasons=[_reason_for(cat, kw) for cat, kw in zip(blocked_cats, blocked_hits)],
            original_reply=reply_text,
        )

    rewrite_cats, rewrite_hits = _match_patterns(stripped, REWRITE_PATTERNS)
    if rewrite_cats:
        return SafetyCheckResult(
            status="rewrite_required",
            risk_flags=rewrite_cats,
            reasons=[_reason_for(cat, kw) for cat, kw in zip(rewrite_cats, rewrite_hits)],
            original_reply=reply_text,
        )

    return SafetyCheckResult(
        status="pass",
        risk_flags=[],
        reasons=["回复真诚克制，未检测到安全风险。"],
        original_reply=reply_text,
    )


def check_many_replies(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Batch safety check. Preserves all original fields, appends safety fields.

    Args:
        drafts: List of dicts, each with at least 'draft_text' (and optionally
                'review_id', 'original_review', etc.).

    Returns:
        Same list with safety_status, risk_types, safety_reason added per draft.
        approval_status is set to "blocked" when blocked.
    """
    results: list[dict[str, Any]] = []
    for d in drafts:
        entry = dict(d)
        review_ctx = {k: d.get(k) for k in ("review_id", "review_text", "rating", "sentiment") if k in d}
        check = check_reply_safety(str(d.get("draft_text", "")), review_ctx)
        entry["safety_status"] = check.status
        entry["risk_types"] = check.risk_flags
        entry["safety_reason"] = "; ".join(check.reasons)
        if check.status == "blocked":
            entry["approval_status"] = "blocked"
        results.append(entry)
    return results


# ── Reason messages ────────────────────────────────────────────────────

_REASON_MAP: dict[str, str] = {
    "attack_customer": "回复包含攻击性或侮辱顾客的言辞。",
    "disclose_privacy": "回复包含疑似顾客个人信息，泄露隐私风险。",
    "claim_employee_punished": "回复声称已处罚或开除具体员工，不宜公开。",
    "fabricated_fact": "回复包含未经核实的调查结论或监控细节，存在编造事实风险。",
    "unfounded_compensation": "回复包含无依据的赔偿承诺，不宜在核实前做出。",
    "over_marketing": "回复包含过度营销或推销话术，差评回复应聚焦解决问题。",
    "defensive_or_blame_shift": "回复语气过度防御或有推卸责任倾向。",
}


def _reason_for(category: str, keyword: str) -> str:
    return _REASON_MAP.get(category, f"检测到安全风险关键词: {keyword}")
