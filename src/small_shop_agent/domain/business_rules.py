"""Shared business constants — single source of truth for topic/severity/safety/step mappings."""
from __future__ import annotations

# ── Topic → Chinese label ───────────────────────────────────────────────
TOPIC_CN_MAP: dict[str, str] = {
    "hygiene": "卫生",
    "waiting_time": "等待时间",
    "service": "服务",
    "product": "产品",
    "environment": "环境",
    "price": "价格",
    "other": "其他",
}

# ── Severity colors & labels ────────────────────────────────────────────
SEVERITY_COLOR_MAP: dict[str, str] = {"high": "#C0392B", "medium": "#E67E22", "low": "#27AE60"}
SEVERITY_LABEL_MAP: dict[str, str] = {"high": "高", "medium": "中", "low": "低"}

# ── Safety badge configs ────────────────────────────────────────────────
SAFETY_STATUS_BADGE_MAP: dict[str, tuple[str, str, str]] = {
    "pass": ("#27AE60", "#E8F8F0", "✓ 安全"),
    "rewrite_required": ("#E67E22", "#FEF5E7", "⚠ 需修改"),
    "blocked": ("#C0392B", "#FDEDEC", "✗ 已拦截"),
}

APPROVAL_STATUS_BADGE_MAP: dict[str, tuple[str, str, str]] = {
    "pending": ("#E67E22", "#FEF5E7", "⏳ 待审核"),
    "approved": ("#27AE60", "#E8F8F0", "✓ 已批准"),
    "edited": ("#3498DB", "#EBF5FB", "📝 已编辑"),
    "rejected": ("#C0392B", "#FDEDEC", "✗ 已驳回"),
}

TRACE_STATUS_BADGE_MAP: dict[str, tuple[str, str, str]] = {
    "passed": ("#27AE60", "#E8F8F0", "✓ 通过"),
    "warning": ("#E67E22", "#FEF5E7", "⚠ 警告"),
    "failed": ("#C0392B", "#FDEDEC", "✗ 失败"),
    "pending": ("#8B7355", "#F5F0E8", "◷ 进行中"),
}

TRACE_STATUS_COLOR_MAP: dict[str, str] = {
    "passed": "#27AE60", "warning": "#E67E22", "failed": "#C0392B", "pending": "#8B7355",
}

# ── Step name → Chinese label ─────────────────────────────────────────
STEP_NAME_CN_MAP: dict[str, str] = {
    "input_validation": "输入校验",
    "data_cleaning": "数据清洗",
    "classification": "评论分类",
    "sentiment_analysis": "情绪分析",
    "issue_aggregation": "问题聚合",
    "evidence_check": "证据绑定",
    "reply_drafting": "回复草稿",
    "safety_check": "安全检查",
    "human_approval": "人工审批",
    "eval_run": "评测运行",
}

# ── Evidence status → Chinese label ───────────────────────────────────
EVIDENCE_STATUS_CN_MAP: dict[str, str] = {
    "sufficient": "证据充分",
    "insufficient": "证据不足",
    "weak": "证据较弱",
}

# ── Store types ────────────────────────────────────────────────────────
STORE_TYPES: list[str] = [
    "咖啡店", "餐厅", "奶茶店", "便利店", "甜品店", "面包店", "小吃店", "其他",
]
