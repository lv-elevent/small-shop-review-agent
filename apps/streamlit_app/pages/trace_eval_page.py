"""
Trace & Eval Page — 处理记录与质量检查

目标：
- 尽量贴近目标图的布局与质感：左侧纵向步骤时间线，右侧质量检查 / 运行情况 / 检查记录。
- 面向老板/运营：少用 Trace、Schema、LLM、Fallback 等技术词。
- 保持真实能力：TraceService / EvalService / compute_metrics / generate_report。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from apps.streamlit_app.components.sidebar import render_sidebar
from apps.streamlit_app.components.ui_helpers import safe_html
from small_shop_agent.services.trace_service import TraceService
from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.services.insight_service import InsightService
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.storage.database import execute_migrations, get_connection
from small_shop_agent.utils.logger import ensure_logger_configured
from small_shop_agent.exports.report_exporter import generate_report

execute_migrations()
ensure_logger_configured()

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="小店评论经营助手 · 处理记录",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <style>
        :root {
            --coffee-950:#1E1510;
            --coffee-900:#2C221B;
            --coffee-800:#3D2C20;
            --coffee-700:#4A3728;
            --coffee-600:#5C3D2E;
            --coffee-500:#6B4C3B;
            --coffee-400:#8B7355;
            --coffee-300:#A09080;
            --coffee-200:#D4C4B0;
            --coffee-100:#E8E0D5;
            --coffee-50:#F5F0E8;
            --cream:#FFFCF8;
            --page-bg:#FAFBF7;
            --card:#FFFFFF;
            --success:#27AE60;
            --success-bg:#E8F8F0;
            --warning:#E67E22;
            --warning-bg:#FEF5E7;
            --danger:#C0392B;
            --danger-bg:#FDEDEC;
            --info:#3498DB;
            --info-bg:#EBF5FB;
            --blue:#3498DB;
            --purple:#7C5CE6;
            --teal:#20B8B8;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: var(--page-bg) !important;
        }

        #MainMenu, header[data-testid="stHeader"], footer,
        .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"] {
            visibility: hidden !important;
            display: none !important;
            height: 0 !important;
        }

        .stMain .block-container {
            padding-top: 1.35rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2.55rem !important;
            padding-right: 2.55rem !important;
            max-width: 1440px !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--coffee-100) !important;
            border-radius: 16px !important;
            background: var(--card) !important;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045) !important;
        }

        .page-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 16px;
            margin-bottom: 16px;
        }

        .title-wrap {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .title-icon {
            width: 42px;
            height: 42px;
            border-radius: 14px;
            background: var(--coffee-50);
            border: 1px solid var(--coffee-100);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 1.35rem;
        }

        .page-title {
            margin: 0;
            color: var(--coffee-800);
            font-size: 1.58rem;
            font-weight: 950;
            letter-spacing: -0.4px;
            line-height: 1.1;
        }

        .page-subtitle {
            margin-top: 7px;
            color: var(--coffee-400);
            font-size: .84rem;
            line-height: 1.5;
        }

        .top-controls {
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
        }

        .fake-select {
            height: 36px;
            min-width: 142px;
            border-radius: 9px;
            border: 1px solid var(--coffee-100);
            background: #fff;
            color: var(--coffee-500);
            font-size: .76rem;
            font-weight: 850;
            display: inline-flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 0 11px;
            box-shadow: 0 1px 4px rgba(0,0,0,.03);
        }

        .section-card {
            background: #FFFFFF;
            border: 1px solid var(--coffee-100);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045);
            margin-bottom: 12px;
        }

        .section-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
        }

        .section-title {
            margin: 0;
            color: var(--coffee-700);
            font-size: .98rem;
            font-weight: 950;
        }

        .section-subtitle {
            color: var(--coffee-300);
            font-size: .72rem;
            margin-top: 4px;
            line-height: 1.45;
        }

        .done-pill {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            border-radius: 999px;
            padding: 5px 11px;
            color: var(--success);
            background: var(--success-bg);
            font-size: .70rem;
            font-weight: 950;
            white-space: nowrap;
        }

        /* Timeline */
        .timeline {
            position: relative;
            padding-left: 38px;
        }

        .timeline::before {
            content: "";
            position: absolute;
            left: 15px;
            top: 16px;
            bottom: 20px;
            width: 2px;
            background: linear-gradient(180deg,#28B463 0%,#A6E3BF 100%);
        }

        .timeline-row {
            position: relative;
            display: grid;
            grid-template-columns: 24px 1fr auto auto;
            gap: 10px;
            align-items: center;
            min-height: 62px;
            margin-bottom: 9px;
            border: 1px solid var(--coffee-100);
            border-radius: 13px;
            background: #fff;
            padding: 10px 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,.025);
        }

        .timeline-dot {
            position: absolute;
            left: -34px;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: var(--success);
            color: #fff;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: .72rem;
            font-weight: 950;
            box-shadow: 0 0 0 3px #E8F8F0;
        }

        .step-num {
            color: var(--coffee-300);
            font-size: .74rem;
            font-weight: 950;
            text-align: center;
        }

        .step-icon {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: .86rem;
            font-weight: 950;
            flex-shrink: 0;
        }

        .step-main {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }

        .step-title {
            color: var(--coffee-700);
            font-size: .82rem;
            font-weight: 950;
            margin-bottom: 3px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .step-detail {
            color: var(--coffee-300);
            font-size: .70rem;
            line-height: 1.35;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 460px;
        }

        .step-time {
            color: var(--coffee-300);
            font-size: .70rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: .68rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .trace-footer {
            display: flex;
            flex-wrap: wrap;
            gap: 26px;
            border: 1px solid var(--coffee-100);
            border-radius: 10px;
            background: #fff;
            padding: 10px 14px;
            color: var(--coffee-300);
            font-size: .70rem;
            font-weight: 850;
        }

        /* Tabs mimic */
        .tabs-shell {
            background: #fff;
            border: 1px solid var(--coffee-100);
            border-radius: 16px;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045);
            margin-bottom: 12px;
            overflow: hidden;
        }

        .tabs-head {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            border-bottom: 1px solid var(--coffee-100);
        }

        .tab-item {
            text-align: center;
            padding: 13px 8px 12px;
            color: var(--coffee-400);
            font-size: .82rem;
            font-weight: 950;
            border-bottom: 2px solid transparent;
        }

        .tab-item.active {
            color: var(--coffee-800);
            border-bottom-color: var(--coffee-600);
        }

        .tabs-body {
            padding: 18px;
        }

        .pass-line {
            text-align: right;
            color: var(--success);
            font-size: .82rem;
            font-weight: 950;
            margin-bottom: 14px;
        }

        .quality-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
        }

        .quality-card {
            border: 1px solid var(--coffee-100);
            border-radius: 12px;
            background: #fff;
            padding: 16px 12px 12px;
            text-align: center;
            min-height: 124px;
            box-shadow: 0 1px 4px rgba(0,0,0,.025);
        }

        .quality-label {
            color: var(--coffee-500);
            font-size: .74rem;
            font-weight: 950;
            margin-bottom: 10px;
        }

        .quality-value {
            color: var(--coffee-800);
            font-size: 1.55rem;
            font-weight: 950;
            line-height: 1.1;
            margin-bottom: 8px;
        }

        .quality-sub {
            color: var(--coffee-300);
            font-size: .68rem;
            line-height: 1.35;
        }

        .progress-track {
            height: 4px;
            border-radius: 999px;
            background: var(--coffee-50);
            overflow: hidden;
            margin-top: 12px;
        }

        .progress-fill {
            height: 100%;
            border-radius: 999px;
        }

        .run-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
        }

        .run-card {
            border: 1px solid var(--coffee-100);
            border-radius: 12px;
            background: #fff;
            padding: 14px 14px;
            min-height: 78px;
            display: grid;
            grid-template-columns: 34px 1fr;
            gap: 10px;
            align-items: center;
        }

        .run-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            font-weight: 950;
        }

        .run-label {
            color: var(--coffee-400);
            font-size: .70rem;
            font-weight: 850;
            margin-bottom: 3px;
        }

        .run-value {
            color: var(--coffee-800);
            font-size: 1.18rem;
            font-weight: 950;
            line-height: 1.1;
        }

        .records-table {
            border: 1px solid var(--coffee-100);
            border-radius: 12px;
            overflow: hidden;
            background: #fff;
        }

        .record-head,
        .record-row {
            display: grid;
            grid-template-columns: 1.2fr 1fr 1fr 1fr .8fr;
            gap: 10px;
            align-items: center;
            padding: 11px 12px;
        }

        .record-head {
            background: var(--coffee-50);
            color: var(--coffee-500);
            font-size: .70rem;
            font-weight: 950;
        }

        .record-row {
            border-top: 1px solid var(--coffee-50);
            color: var(--coffee-700);
            font-size: .74rem;
            font-weight: 750;
        }

        .record-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }

        .action-row {
            display: grid;
            grid-template-columns: 1.2fr 1fr 1fr;
            gap: 12px;
            margin-top: 12px;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 11px !important;
            font-weight: 950 !important;
            min-height: 42px !important;
            border: 1px solid var(--coffee-100) !important;
            box-shadow: 0 1px 4px rgba(0,0,0,.035) !important;
        }

        button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg,#FF4E50,#E53935) !important;
            border-color: #E53935 !important;
            color: #FFFFFF !important;
        }

        button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background: #D93833 !important;
            border-color: #D93833 !important;
        }

        .owner-empty {
            border: 1px dashed var(--coffee-200);
            border-radius: 14px;
            background: var(--cream);
            padding: 24px;
            color: var(--coffee-400);
            font-size: .86rem;
            line-height: 1.7;
            text-align: center;
        }

        @media (max-width: 1260px) {
            .stMain .block-container {
                padding-left: 1.6rem !important;
                padding-right: 1.6rem !important;
            }
            .page-top {
                align-items: flex-start;
                flex-direction: column;
            }
            .quality-grid,
            .run-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
_OWNER_STEP_CN: dict[str, tuple[str, str, str]] = {
    "input_validation": ("检查评论表", "🧾", "#27AE60"),
    "data_cleaning": ("整理评论数据", "🗃️", "#3498DB"),
    "classification": ("按问题分类", "🧩", "#7C5CE6"),
    "sentiment_analysis": ("判断好评差评", "🏠", "#F39C12"),
    "issue_aggregation": ("汇总高频问题", "🔗", "#35B779"),
    "evidence_check": ("关联原始评论", "📎", "#4A90E2"),
    "reply_drafting": ("生成回复草稿", "💬", "#8E63E7"),
    "safety_check": ("检查回复风险", "🛡️", "#F5A623"),
    "human_approval": ("等待人工确认", "👤", "#6B5B4F"),
    "eval_run": ("质量检查", "⭐", "#F5A623"),
}

_STATUS_LABELS = {
    "passed": ("#27AE60", "#E8F8F0", "通过"),
    "warning": ("#E67E22", "#FEF5E7", "注意"),
    "failed": ("#C0392B", "#FDEDEC", "未通过"),
    "pending": ("#E67E22", "#FEF5E7", "进行中"),
}


def _step_info(name: str) -> tuple[str, str, str]:
    return _OWNER_STEP_CN.get(name, (name, "•", "#8B7355"))


def _status_badge(status: str) -> str:
    c, bg, label = _STATUS_LABELS.get(status, ("#8B7355", "#F5F0E8", status or "未知"))
    icon = "✓" if status == "passed" else "!" if status == "failed" else "◷"
    return f'<span class="status-badge" style="color:{c};background:{bg};">{icon} {safe_html(label)}</span>'


def _fmt_time(ts: str) -> str:
    """Extract HH:MM:SS from ISO timestamp."""
    try:
        return ts[11:19] if "T" in ts else ts[:8] if len(ts) >= 8 else ts
    except Exception:
        return ts or "—"


# ── Lambda helpers for conditional _owner_trace_summary patterns ──────────

def _fmt_validation_output(m: re.Match) -> str:
    v, ir, se = int(m.group(1)), int(m.group(2)), int(m.group(3))
    parts = [f"{v} 条可分析评论"]
    if ir == 0 and se == 0:
        parts.append("评分格式正常，表格格式正常")
    else:
        if ir > 0:
            parts.append(f"评分异常 {ir} 条")
        if se > 0:
            parts.append(f"格式问题 {se} 条")
    return "，".join(parts)


def _fmt_cleaning_output(m: re.Match) -> str:
    v, e, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    parts = [f"{v} 条可分析"]
    if e > 0:
        parts.append(f"{e} 条空评论")
    if d > 0:
        parts.append(f"{d} 条重复评论")
    return "，".join(parts)


def _fmt_evidence_output(m: re.Match) -> str:
    ev, vi, ri, ei = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    parts = [f"关联 {ev} 条原始评论"]
    parts.append(f"{vi} 个问题证据充足")
    if ri > 0:
        parts.append(f"{ri} 个问题已剔除")
    if ei > 0:
        parts.append(f"{ei} 个问题证据不足")
    return "，".join(parts)


def _fmt_eval_output(m: re.Match) -> str:
    ta = m.group(1)
    sa = m.group(2)
    u = int(m.group(3))
    result = f"分类准确率 {ta}，好差评准确率 {sa}"
    if u > 0:
        result += f"，不安全回复 {u} 条"
    return result


def _owner_trace_summary(text: str | None) -> str:
    """将原始 Trace 摘要文本翻译为老板易读的中文描述。"""
    MAX_LEN = 72
    value = (text or "").strip()
    if not value:
        return "—"

    # Phase 1: Multi-field key=value patterns (most specific)
    value = re.sub(
        r"valid=(\d+),\s*invalid_rating=(\d+),\s*schema_errors=(\d+)",
        _fmt_validation_output, value,
    )
    value = re.sub(
        r"valid=(\d+),\s*empty=(\d+),\s*duplicate=(\d+)",
        _fmt_cleaning_output, value,
    )
    value = re.sub(
        r"(\d+)\s*evidence\s*\|\s*valid_issues_count=(\d+)\s*\|\s*rejected_issues_count=(\d+)\s*\|\s*evidence_insufficient_count=(\d+).*",
        _fmt_evidence_output, value,
    )
    value = re.sub(
        r"(\d+)\s*pass,\s*(\d+)\s*rewrite_required,\s*(\d+)\s*blocked\s*\|.*",
        r"\1 条通过检查，\2 条需重写，\3 条已拦截", value,
    )
    value = re.sub(
        r"topic_acc=([\d.]+%?),\s*sent_acc=([\d.]+%?),\s*unsafe=(\d+).*",
        _fmt_eval_output, value,
    )
    value = re.sub(
        r"规则拦截=(\d+),\s*语义调用=(\d+),\s*人工升级=(\d+).*",
        r"规则拦截 \1 条，语义检查 \2 次，人工升级 \3 条", value,
    )

    # Phase 2: Semi-specific patterns (count + keyword + trailing detail)
    value = re.sub(r"(\d+)\s*classified\b.*", r"\1 条评论已完成分类", value)
    value = re.sub(r"(\d+)\s*analyzed\b.*", r"\1 条评论已完成好差评判断", value)
    value = re.sub(r"(\d+)\s*insights?,\s*(\d+)\s*evidence\b.*", r"发现 \1 个经营问题，关联 \2 条证据", value)
    value = re.sub(r"(\d+)\s*insights?\b.*", r"发现 \1 个经营问题", value)
    value = re.sub(r"(\d+)\s*drafts?\s*generated\b.*", r"生成 \1 条回复草稿", value)
    value = re.sub(r"(\d+)\s*drafts?\s*\(.*", r"生成 \1 条回复草稿", value)

    # Phase 3: Generic single-keyword patterns
    value = re.sub(r".*\.csv\s*/\s*(\d+)\s*rows?\b.*", r"导入 \1 条评论", value)
    value = re.sub(r"(\d+)\s*negative\s*candidates?\b.*", r"\1 条差评", value)
    value = re.sub(r"(\d+)\s*reviews\b.*", r"\1 条评论", value)
    value = re.sub(r"(\d+)\s*analyses\b.*", r"\1 条分析结果", value)
    value = re.sub(r"(\d+)\s*evidence\b.*", r"\1 条证据", value)
    value = re.sub(r"(\d+)\s*drafts?\b.*", r"\1 条回复草稿", value)
    value = re.sub(r"(\d+)\s*cases?\b.*", r"\1 条样例", value)
    value = re.sub(r"(\d+)\s*rows?\b.*", r"\1 条评论", value)

    # Phase 4: Cleanup residual technical artifacts
    value = re.sub(r"\b(?:provider|model|model_name)=[^\s,;|]+", "", value)
    value = re.sub(r"\bused_fallback\s*=\s*(?:False|True)\b", "", value)
    value = re.sub(r"\bfallback\s*=\s*(?:False|True)\b", "", value)
    value = re.sub(r"\bschema_ok\s*=\s*(?:True|False)\b", "", value)
    value = re.sub(r"\bschema_errors_count\s*=\s*\d+\b", "", value)
    value = re.sub(r"\battempts\s*=\s*\d+\b", "", value)
    value = re.sub(r"\bretries\s*=\s*\d+\b", "", value)
    value = re.sub(r"\b(?:simulated|Qwen|DeepSeek|rule_based|mock)\b", "", value)
    value = re.sub(r"\s*\|\s*", "，", value)
    value = " ".join(value.split())
    value = re.sub(r"[，,]\s*[，,]", "，", value)
    value = value.strip("，。 ")

    # Phase 5: Length control
    if len(value) > MAX_LEN:
        return value[:MAX_LEN] + "…"
    return value or "—"


def _step_detail(t: dict) -> str:
    input_summary = _owner_trace_summary(t.get("input_summary", ""))
    output_summary = _owner_trace_summary(t.get("output_summary", ""))
    if input_summary != "—" and output_summary != "—":
        return f"{input_summary} → {output_summary}"
    return output_summary if output_summary != "—" else input_summary


def _quality_color(value: float, good: float = 0.8, warn: float = 0.7) -> str:
    if value >= good:
        return "#27AE60"
    if value >= warn:
        return "#E67E22"
    return "#C0392B"


def _pct(value: float) -> str:
    try:
        return f"{value:.0%}"
    except Exception:
        return "0%"


# ═══════════════════════════════════════════════════════════════════════════
# Render helpers
# ═══════════════════════════════════════════════════════════════════════════
def _render_header() -> None:
    st.markdown(
        """
        <div class="page-top">
            <div class="title-wrap">
                <div class="title-icon">🔍</div>
                <div>
                    <h1 class="page-title">处理记录</h1>
                    <div class="page-subtitle">查看本次评论分析是否顺利完成，以及回复内容是否适合发布。</div>
                </div>
            </div>
            <div class="top-controls">
                <div class="fake-select">📅 最近一次 <span>⌄</span></div>
                <div class="fake-select">全部步骤 <span>⌄</span></div>
                <div class="fake-select" style="background:#F6EFE5;color:#8B7355;min-width:110px;">↻ 最新结果 <span>⌄</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_ordered_steps(traces: list[dict], latest_eval: dict | None, batch_id: str) -> list[dict]:
    workflow_order = [
        "input_validation",
        "data_cleaning",
        "classification",
        "sentiment_analysis",
        "issue_aggregation",
        "evidence_check",
        "reply_drafting",
        "safety_check",
    ]
    trace_map: dict[str, dict] = {t["step_name"]: t for t in traces}
    ordered_steps: list[dict] = []
    for step_name in workflow_order:
        t = trace_map.get(step_name)
        if t:
            ordered_steps.append(t)

    approval_exists = False
    approval_count = 0
    try:
        with get_connection() as conn:
            ac = conn.execute(
                "SELECT COUNT(*) as cnt FROM approval_actions WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if ac and ac["cnt"] > 0:
                approval_exists = True
                approval_count = ac["cnt"]
    except Exception:
        pass

    ordered_steps.append(
        {
            "step_name": "human_approval",
            "status": "passed" if approval_exists else "pending",
            "input_summary": "回复草稿",
            "output_summary": f"已确认 {approval_count} 条" if approval_exists else "暂无确认记录",
            "latency_ms": 0,
            "created_at": "",
        }
    )

    if latest_eval:
        ta = latest_eval.get("topic_accuracy", 0)
        sa = latest_eval.get("sentiment_accuracy", 0)
        eval_output = f"问题分类准确率 {_pct(ta)}，好差评判断准确率 {_pct(sa)}"
        eval_status = "passed"
    else:
        eval_output = "尚未进行质量检查"
        eval_status = "pending"
    ordered_steps.append(
        {
            "step_name": "eval_run",
            "status": eval_status,
            "input_summary": "质量检查",
            "output_summary": eval_output,
            "latency_ms": latest_eval.get("latency_ms", 0) if latest_eval else 0,
            "created_at": latest_eval.get("created_at", "") if latest_eval else "",
        }
    )
    return ordered_steps


def _render_timeline(steps: list[dict], batch_id: str, latest_eval: dict | None) -> None:
    done_count = sum(1 for s in steps if s.get("status") == "passed")
    overall_done = done_count == len(steps)
    first_time = next((s.get("created_at", "") for s in steps if s.get("created_at")), "—")
    total_latency = sum(int(s.get("latency_ms") or 0) for s in steps)
    total_time = f"{total_latency / 1000:.2f}s" if total_latency else "—"

    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-head">
                <div>
                    <p class="section-title">执行步骤（共 {len(steps)} 步）</p>
                    <div class="section-subtitle">从上传评论表到生成回复草稿的完整处理过程。</div>
                </div>
                <div class="done-pill">{'已完成' if overall_done else '进行中'}</div>
            </div>
            <div class="timeline">
        """,
        unsafe_allow_html=True,
    )

    rows = []
    for i, t in enumerate(steps, start=1):
        name, icon, color = _step_info(t.get("step_name", ""))
        status = t.get("status", "pending")
        dot_label = "✓" if status == "passed" else str(i)
        detail = _step_detail(t)
        latency = t.get("latency_ms", 0)
        latency_label = f"{latency}ms" if latency and latency < 1000 else f"{latency / 1000:.2f}s" if latency else "—"
        if t.get("step_name") == "eval_run" and latest_eval:
            # Keep target-like final runtime if possible.
            latency_label = f"{latency / 1000:.2f}s" if latency else "—"
        rows.append(
            f"""
            <div class="timeline-row">
                <div class="timeline-dot">{safe_html(dot_label)}</div>
                <div class="step-num">{i}</div>
                <div class="step-main">
                    <div class="step-icon" style="background:{color};">{icon}</div>
                    <div style="min-width:0;">
                        <div class="step-title">{safe_html(name)}</div>
                        <div class="step-detail">{safe_html(detail)}</div>
                    </div>
                </div>
                <div class="step-time">{safe_html(latency_label)}</div>
                <div>{_status_badge(status)}</div>
            </div>
            """
        )

    st.markdown("".join(rows) + "</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
            <div class="trace-footer">
                <span>记录编号：{safe_html(str(latest_eval.get('eval_run_id', batch_id) if latest_eval else batch_id))}</span>
                <span>开始时间：{safe_html(str(first_time or '—'))}</span>
                <span>总耗时：{safe_html(total_time)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quality_tab(latest_eval: dict | None) -> tuple[float, float, float, int, int, int]:
    """Render quality check tab content. Returns (ta, sa, composite, total_cases, unsafe, schema_fail)."""
    if latest_eval is None:
        st.info("暂无质量检查结果，点击下方「重新检查质量」后会显示结果。")
        return 0, 0, 0, 0, 0, 0

    ta = latest_eval.get("topic_accuracy", 0) or 0
    sa = latest_eval.get("sentiment_accuracy", 0) or 0
    unsafe = latest_eval.get("unsafe_reply_count", 0) or 0
    schema_fail = latest_eval.get("schema_failure_count", 0) or 0
    total_cases = latest_eval.get("total_eval_cases", 0) or 0
    composite = round((ta + sa) / 2, 2)

    if total_cases == 0:
        st.info("暂无可匹配样例，准确率暂时无法计算。当前评论与评测基准不一致。")
        return ta, sa, composite, total_cases, unsafe, schema_fail

    pass_label = "评测通过" if composite >= 0.7 else "建议复查"
    st.markdown(
        f'<span style="color:#27AE60;font-weight:950;font-size:0.82rem;">✓ {safe_html(pass_label)}</span>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4, gap="small")
    items = [
        (c1, "问题分类准确率", _pct(ta), "目标 ≥ 70%", _quality_color(ta, 0.7, 0.6), ta),
        (c2, "好差评判断准确率", _pct(sa), "目标 ≥ 80%", _quality_color(sa, 0.8, 0.7), sa),
        (c3, "整体质量", f"{int(composite * 100)}/100", "越高越可靠", _quality_color(composite, 0.8, 0.7), composite),
        (c4, "检查样例数", str(total_cases), "用于质量检查", "#3498DB", 1),
    ]
    for col, label, value, sub, *_rest in items:
        with col:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"## {value}")
                st.caption(sub)

    return ta, sa, composite, total_cases, unsafe, schema_fail


def _render_run_metrics(batch_id: str, unsafe: int, schema_fail: int) -> None:
    from small_shop_agent.observability.metrics import compute_metrics

    rm = compute_metrics(batch_id)
    total_time = f"{rm.total_latency_ms / 1000:.2f}s" if rm.total_latency_ms else "—"

    def run_card(icon: str, label: str, value: str, color: str, bg: str) -> str:
        return f"""
        <div class="run-card">
            <div class="run-icon" style="color:{color};background:{bg};">{icon}</div>
            <div>
                <div class="run-label">{safe_html(label)}</div>
                <div class="run-value">{safe_html(value)}</div>
            </div>
        </div>
        """

    cards = [
        run_card("⏱", "总耗时", total_time, "#3498DB", "#EBF5FB"),
        run_card("A", "格式重试", f"{rm.schema_retry_count} 次", "#7C5CE6", "#F0EBFF"),
        run_card("↩", "备用方案", _pct(rm.fallback_rate), "#E67E22", "#FEF5E7"),
        run_card("🛡", "回复拦截", _pct(rm.safety_block_rate), "#C0392B", "#FDEDEC"),
        run_card("▱", "格式异常", f"{schema_fail} 次", "#20B8B8", "#E9FAFA"),
        run_card("✎", "人工修改", f"{rm.human_edit_count} 次", "#3498DB", "#EBF5FB"),
        run_card("🔒", "风险遗漏", f"{rm.unsafe_escape_count} 条", "#E67E22", "#FEF5E7"),
        run_card("☰", "不建议发布", f"{unsafe} 条", "#C0392B" if unsafe else "#27AE60", "#FDEDEC" if unsafe else "#E8F8F0"),
    ]

    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-head">
                <div>
                    <p class="section-title">运行情况</p>
                    <div class="section-subtitle">本次分析的耗时、重试和风险处理情况。</div>
                </div>
            </div>
            <div class="run-grid">{''.join(cards)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_eval_records(eval_runs: list[dict]) -> None:
    """Render eval run history as a Streamlit dataframe with Chinese headers."""
    import pandas as pd

    if not eval_runs:
        with st.container(border=True):
            st.markdown("**检查记录**")
            st.caption("最近几次质量检查结果。")
            st.info("暂无质量检查记录。点击下方按钮可以重新检查质量。")
        return

    table_rows = []
    for run in eval_runs[:10]:
        ta = run.get("topic_accuracy", 0) or 0
        sa = run.get("sentiment_accuracy", 0) or 0
        score = round((ta + sa) / 2, 2)
        status = "通过" if score >= 0.7 else "需复查"
        time_str = run.get("created_at", "") or "—"
        if "T" in time_str:
            time_str = time_str.replace("T", " ")[:19]
        table_rows.append({
            "时间": time_str,
            "样例数": run.get("total_eval_cases", 0) or 0,
            "问题分类": _pct(ta),
            "好差评判断": _pct(sa),
            "整体质量": f"{int(score * 100)}/100",
            "状态": status,
        })

    df = pd.DataFrame(table_rows)
    with st.container(border=True):
        st.markdown(
            f'<span style="font-weight:700;color:#4A3728;font-size:0.95rem;">检查记录</span>'
            f'<span style="font-size:0.74rem;color:#A09080;margin-left:10px;">'
            f'最近几次质量检查结果 · 共 {len(eval_runs)} 条</span>',
            unsafe_allow_html=True,
        )
        st.dataframe(df, use_container_width=True, hide_index=True)


def _trace_text(traces: list[dict]) -> str:
    status_text = {"passed": "通过", "warning": "注意", "failed": "未通过", "pending": "进行中"}
    lines = []
    for t in traces:
        step_name, _icon, _color = _step_info(t.get("step_name", ""))
        lines.append(
            f"[{status_text.get(t.get('status'), t.get('status', ''))}] {step_name} | "
            f"输入: {_owner_trace_summary(t.get('input_summary', '-'))} | "
            f"输出: {_owner_trace_summary(t.get('output_summary', '-'))} | "
            f"耗时: {t.get('latency_ms', 0)}ms"
        )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    st.session_state.nav_selection = "追踪评测"
    render_sidebar()

    trace_svc = TraceService()
    eval_svc = EvalService()
    batch_id = st.session_state.get("current_batch_id")
    if not batch_id:
        qp_bid = st.query_params.get("batch_id")
        if qp_bid:
            st.session_state.current_batch_id = qp_bid
            batch_id = qp_bid

    _render_header()

    if not batch_id:
        st.markdown(
            """
            <div class="owner-empty">
                👈 请先到「上传评论」页面上传评论表，并点击「开始分析」。分析完成后，这里会显示处理步骤和质量检查结果。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    try:
        traces = trace_svc.get_trace(batch_id)
    except Exception:
        traces = []

    if not traces:
        st.markdown(
            """
            <div class="owner-empty">
                这份评论表还没有处理记录。请回到「上传评论」页面点击「开始分析」。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    try:
        latest_eval = eval_svc.get_latest_eval_by_batch(batch_id)
        eval_runs = eval_svc.list_eval_runs_by_batch(batch_id, limit=10)
    except Exception:
        latest_eval = None
        eval_runs = []

    # Extract unsafe / schema_fail from latest_eval for run_metrics
    if latest_eval:
        unsafe = latest_eval.get("unsafe_reply_count", 0) or 0
        schema_fail = latest_eval.get("schema_failure_count", 0) or 0
    else:
        unsafe = schema_fail = 0

    steps = _build_ordered_steps(traces, latest_eval, batch_id)

    left, right = st.columns([11, 9], gap="medium")

    with left:
        _render_timeline(steps, batch_id, latest_eval)

    with right:
        tab_q, tab_m, tab_r = st.tabs(["📊 质量检查", "⏳ 运行情况", "🧾 检查记录"])
        with tab_q:
            _render_quality_tab(latest_eval)
        with tab_m:
            _render_run_metrics(batch_id, unsafe, schema_fail)
        with tab_r:
            _render_eval_records(eval_runs)

        bc1, bc2, bc3 = st.columns([2, 2, 2], gap="medium")
        with bc1:
            if st.button("▶ 重新检查质量", key="run_eval_btn", width="stretch", type="primary"):
                with st.spinner("正在重新检查质量…"):
                    result = eval_svc.run_eval({"batch_id": batch_id})
                if result["success"]:
                    st.toast("✅ 质量检查完成", icon="✅")
                    st.rerun()
                else:
                    st.toast(f"❌ 检查失败：{result.get('error', '')}", icon="❌")
        with bc2:
            if traces:
                try:
                    insight_svc = InsightService()
                    reply_svc = ReplyService()
                    top_issues = insight_svc.get_top_issues(batch_id)
                    batch_info: dict = {}
                    with get_connection() as conn:
                        b = conn.execute(
                            "SELECT * FROM review_batches WHERE batch_id = ?",
                            (batch_id,),
                        ).fetchone()
                        if b:
                            batch_info = dict(b)
                        avg_row = conn.execute(
                            "SELECT AVG(CAST(rating AS REAL)) as avg_r FROM reviews WHERE batch_id = ? AND is_valid = 1",
                            (batch_id,),
                        ).fetchone()
                        batch_info["avg_rating"] = round(avg_row["avg_r"], 1) if avg_row and avg_row["avg_r"] else 0
                        neg_row = conn.execute(
                            "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ? AND is_negative_candidate = 1",
                            (batch_id,),
                        ).fetchone()
                        batch_info["negative_count"] = neg_row["cnt"] if neg_row else 0
                        pending_row = conn.execute(
                            "SELECT COUNT(*) as cnt FROM reply_drafts WHERE batch_id = ? AND approval_status = 'pending'",
                            (batch_id,),
                        ).fetchone()
                        batch_info["pending_count"] = pending_row["cnt"] if pending_row else 0
                    drafts = reply_svc._reply_repo.list_drafts(batch_id)
                    report_text = generate_report(
                        batch_id=batch_id,
                        batch_info=batch_info,
                        top_issues=top_issues,
                        traces=traces,
                        eval_result=latest_eval,
                        drafts=drafts,
                    )
                    st.download_button(
                        "⬇ 导出报告",
                        data=report_text,
                        file_name=f"处理记录报告_{batch_id}.md",
                        mime="text/markdown",
                        width="stretch",
                        type="secondary",
                        key="export_eval_btn",
                    )
                except Exception:
                    st.button("⬇ 导出报告", key="export_eval", width="stretch", type="secondary", disabled=True, help="导出报告生成失败")
            else:
                st.button("⬇ 导出报告", key="export_eval", width="stretch", type="secondary", disabled=True, help="请先运行分析后再导出")
        with bc3:
            with st.popover("📋 复制处理记录", width="stretch"):
                text = _trace_text(traces)
                if text:
                    st.code(text, language=None)
                    st.caption("选中上方文本即可复制")
                else:
                    st.info("暂无处理记录")


if __name__ == "__main__":
    main()
