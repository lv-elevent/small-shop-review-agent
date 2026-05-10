"""Report exporter — generates a structured Markdown report for Trace & Eval."""
from __future__ import annotations

from typing import Any

_STEP_NAME_CN: dict[str, str] = {
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

_STATUS_CN: dict[str, str] = {
    "passed": "通过",
    "warning": "警告",
    "failed": "失败",
    "pending": "进行中",
}

_SEVERITY_CN: dict[str, str] = {
    "high": "高", "medium": "中", "low": "低",
}

_TOPIC_CN: dict[str, str] = {
    "hygiene": "卫生", "waiting_time": "等待时间", "service": "服务",
    "product": "产品", "environment": "环境", "price": "价格", "other": "其他",
}


def _cn_topic(raw: str) -> str:
    for en, cn in _TOPIC_CN.items():
        raw = raw.replace(en, cn)
    return raw


def _format_time(ts: str | None) -> str:
    if not ts:
        return "—"
    try:
        return ts[:19].replace("T", " ")
    except Exception:
        return str(ts)


def generate_report(
    batch_id: str,
    batch_info: dict[str, Any] | None = None,
    top_issues: list[dict[str, Any]] | None = None,
    traces: list[dict[str, Any]] | None = None,
    eval_result: dict[str, Any] | None = None,
    drafts: list[dict[str, Any]] | None = None,
) -> str:
    """Generate a structured Markdown report with 5 sections.

    Returns a Markdown string suitable for saving as .md or .txt.
    """
    lines: list[str] = []
    info = batch_info or {}
    issues = top_issues or []
    trace_list = traces or []
    eval_res = eval_result or {}
    draft_list = drafts or []

    # ── Header ──────────────────────────────────────────────────────────
    lines.append("# 小店评论经营助手 · 分析报告")
    lines.append("")
    lines.append(f"**批次 ID**: `{batch_id}`")
    lines.append(f"**导出时间**: {_format_time(None) if False else ''}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ══════════════════════════════════════════════════════════════════════
    # Section 1: Batch Summary
    # ══════════════════════════════════════════════════════════════════════
    lines.append("## 1. 批次汇总 (Batch Summary)")
    lines.append("")
    lines.append(f"- **门店类型**: {info.get('store_type', '—')}")
    lines.append(f"- **总评论数**: {info.get('total_reviews', info.get('valid_review_count', '—'))}")
    lines.append(f"- **平均评分**: {info.get('avg_rating', '—')}")
    lines.append(f"- **差评数**: {info.get('negative_count', '—')}")
    lines.append(f"- **待审核回复**: {info.get('pending_count', '—')}")
    lines.append(f"- **分析时间**: {_format_time(info.get('created_at'))}")
    lines.append("")

    # ══════════════════════════════════════════════════════════════════════
    # Section 2: Top Issues
    # ══════════════════════════════════════════════════════════════════════
    lines.append("## 2. 核心问题 (Top Issues)")
    lines.append("")
    if issues:
        for issue in issues:
            rank = issue.get("rank", "—")
            name = _cn_topic(str(issue.get("issue_name", "—")))
            topic = issue.get("topic", "—")
            sev = issue.get("severity_level", "medium")
            sev_label = _SEVERITY_CN.get(sev, sev)
            mention = issue.get("mention_count", 0)
            ev_count = issue.get("evidence_count", 0)
            ev_status = issue.get("evidence_status", "—")
            action = issue.get("suggested_action", "—")
            ev_ids = issue.get("evidence_review_ids", [])

            lines.append(f"### 问题 #{rank}: {name}")
            lines.append("")
            lines.append(f"- **主题**: {_cn_topic(topic)}")
            lines.append(f"- **严重程度**: {sev_label}")
            lines.append(f"- **提及次数**: {mention}")
            lines.append(f"- **证据数量**: {ev_count} 条 ({ev_status})")
            lines.append(f"- **建议措施**: {action}")
            if ev_ids:
                lines.append(f"- **关联评论**: {', '.join(str(eid) for eid in ev_ids)}")
            lines.append("")
    else:
        lines.append("暂无问题洞察数据。")
        lines.append("")

    # ══════════════════════════════════════════════════════════════════════
    # Section 3: Safety Summary
    # ══════════════════════════════════════════════════════════════════════
    lines.append("## 3. 安全检测汇总 (Safety Summary)")
    lines.append("")
    safety_stats = {"pass": 0, "rewrite_required": 0, "blocked": 0}
    risk_breakdown: dict[str, int] = {}
    for d in draft_list:
        sts = d.get("safety_status", "pass")
        if sts in safety_stats:
            safety_stats[sts] += 1
        for risk in d.get("risk_types", []):
            risk_breakdown[risk] = risk_breakdown.get(risk, 0) + 1

    lines.append(f"- **通过**: {safety_stats['pass']} 条")
    lines.append(f"- **需重写**: {safety_stats['rewrite_required']} 条")
    lines.append(f"- **已拦截**: {safety_stats['blocked']} 条")
    lines.append(f"- **总草稿数**: {len(draft_list)} 条")
    if risk_breakdown:
        lines.append("")
        lines.append("### 风险类型分布")
        lines.append("")
        for risk_type, count in sorted(risk_breakdown.items(), key=lambda x: -x[1]):
            lines.append(f"- **{risk_type}**: {count} 次")
    lines.append("")

    # ══════════════════════════════════════════════════════════════════════
    # Section 4: Trace Steps
    # ══════════════════════════════════════════════════════════════════════
    lines.append("## 4. 追踪步骤 (Trace Steps)")
    lines.append("")
    if trace_list:
        workflow_order = [
            "input_validation", "data_cleaning", "classification",
            "sentiment_analysis", "issue_aggregation", "evidence_check",
            "reply_drafting", "safety_check",
        ]
        trace_map = {t["step_name"]: t for t in trace_list}
        step_num = 0
        for step_name in workflow_order:
            t = trace_map.get(step_name)
            if not t:
                continue
            step_num += 1
            sts = t.get("status", "—")
            sts_cn = _STATUS_CN.get(sts, sts)
            name_cn = _STEP_NAME_CN.get(step_name, step_name)
            inp = t.get("input_summary", "—")
            out = t.get("output_summary", "—")
            latency = t.get("latency_ms", 0)

            lines.append(f"### {step_num}. {name_cn} — {sts_cn}")
            lines.append("")
            lines.append(f"- **状态**: {sts_cn}")
            lines.append(f"- **输入**: {inp}")
            lines.append(f"- **输出**: {out}")
            if latency:
                lines.append(f"- **耗时**: {latency}ms")
            err = t.get("error_message")
            if err:
                lines.append(f"- **错误**: {err}")
            lines.append("")
    else:
        lines.append("暂无追踪记录。")
        lines.append("")

    # ══════════════════════════════════════════════════════════════════════
    # Section 5: Eval Summary
    # ══════════════════════════════════════════════════════════════════════
    lines.append("## 5. 评测汇总 (Eval Summary)")
    lines.append("")
    if eval_res:
        ta = eval_res.get("topic_accuracy", 0)
        sa = eval_res.get("sentiment_accuracy", 0)
        unsafe = eval_res.get("unsafe_reply_count", 0)
        schema_fail = eval_res.get("schema_failure_count", 0)
        total_cases = eval_res.get("total_eval_cases", 0)
        composite = round((ta + sa) / 2, 2)

        lines.append(f"- **分类准确率**: {ta:.1%}")
        lines.append(f"- **情绪准确率**: {sa:.1%}")
        lines.append(f"- **不安全回复数**: {unsafe}")
        lines.append(f"- **结构校验失败**: {schema_fail}")
        lines.append(f"- **评测样例数**: {total_cases}")
        lines.append(f"- **综合评分**: {composite:.0%}")
    else:
        lines.append("尚未运行评测。")
    lines.append("")

    # ── Footer ──────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("*报告由 Small Shop Review Response & Insight Agent 自动生成*")
    lines.append("")

    return "\n".join(lines)
