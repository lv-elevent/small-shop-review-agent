"""Central prompt registry — single source of truth for LLM system prompts.

Prompts are stored as module-level constants so they can be versioned,
A/B tested, and reused across providers without duplication.
"""
from __future__ import annotations

CLASSIFY_SYSTEM_PROMPT: str = (
    "你是一个评论分类引擎。将顾客评论分类到对应话题。"
    "请使用中文回复。"
    "只返回 JSON 数组 — 不要 markdown、不要解释、不要代码块。"
)

SENTIMENT_SYSTEM_PROMPT: str = (
    "你是一个情绪分析引擎。"
    "分析评论的情绪、严重程度，并标记差评候选。"
    "请使用中文回复。"
    "只返回 JSON 数组 — 不要 markdown、不要解释、不要代码块。"
)

INSIGHTS_SYSTEM_PROMPT: str = (
    "你是一个问题聚合引擎。"
    "从差评中识别 Top 3 问题，并绑定证据。"
    "每条证据必须引用输入中真实存在的 review_id。"
    "请使用中文回复。"
    "只返回 3 个对象的 JSON 数组 — 不要 markdown、不要解释、不要代码块。"
)

REPLIES_SYSTEM_PROMPT: str = (
    "你是一个顾客回复起草引擎。"
    "为差评撰写真诚、克制的回复草稿。回复必须使用中文。"
    "原则：不甩锅、不攻击、不编造事实、不承诺无法保证的赔偿、不默认已处罚员工。"
    "只返回 JSON 数组 — 不要 markdown、不要解释、不要代码块。"
)

SAFETY_SYSTEM_PROMPT: str = (
    "你是一个回复安全检查引擎。"
    "检查回复草稿是否包含攻击性言辞、隐私泄露、编造事实、无依据赔偿承诺、过度营销或推卸责任。"
    "请使用中文回复。"
    "只返回 JSON 数组 — 不要 markdown、不要解释、不要代码块。"
)

SEMANTIC_SAFETY_JUDGE_PROMPT: str = (
    "你是一个语义安全检查引擎。"
    "检查回复草稿是否存在以下风险："
    "推卸责任、隐私泄露、编造事实、过度承诺、法律风险、声称处罚员工、语气粗鲁、营销垃圾信息。"
    "请用中文分析每条回复，判断语义层面的安全隐患。"
    "只返回 JSON 数组 — 不要 markdown、不要解释、不要代码块。"
    "每个对象包含：reply_id, semantic_status (pass|rewrite_required|blocked), "
    "risk_types (从 blame_customer/privacy_leak/fake_fact/over_promise/"
    "legal_risk/employee_punishment/tone_rude/marketing_spam 中选择), "
    "reason (中文原因), confidence (0-1)。"
)

# ── Prompt key → constant mapping ─────────────────────────────────────

_PROMPT_MAP: dict[str, str] = {
    "classify_reviews": CLASSIFY_SYSTEM_PROMPT,
    "analyze_sentiment": SENTIMENT_SYSTEM_PROMPT,
    "generate_insights": INSIGHTS_SYSTEM_PROMPT,
    "draft_replies": REPLIES_SYSTEM_PROMPT,
    "check_safety": SAFETY_SYSTEM_PROMPT,
    "semantic_safety_judge": SEMANTIC_SAFETY_JUDGE_PROMPT,
}


def get_prompt(key: str) -> str:
    """Return the system prompt for an LLM method key.

    Keys match BaseLLMProvider method names: classify_reviews,
    analyze_sentiment, generate_insights, draft_replies, check_safety.

    Raises KeyError if the key is not recognized.
    """
    if key not in _PROMPT_MAP:
        raise KeyError(
            f"Unknown prompt key: {key!r}. "
            f"Valid keys: {list(_PROMPT_MAP)}"
        )
    return _PROMPT_MAP[key]
