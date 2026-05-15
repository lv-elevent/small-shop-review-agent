"""
Dashboard Page — 数据看板：老板视角经营总览

设计目标：
- 面向小店老板/店长：少用技术词，多展示“问题、影响、建议、待确认回复”。
- 保持真实数据链路：InsightService / ReplyService / TraceService / EvalService。
- 页面结构：顶部经营指标 -> 左侧重点问题 -> 右侧处理进度 + 待确认回复。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from apps.streamlit_app.components.sidebar import render_sidebar
from apps.streamlit_app.components.ui_helpers import safe_html, translate_trace_detail
from small_shop_agent.domain.business_rules import TOPIC_CN_MAP
from small_shop_agent.services.insight_service import InsightService
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.services.trace_service import TraceService
from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.storage.database import execute_migrations, get_connection
from small_shop_agent.utils.logger import ensure_logger_configured

execute_migrations()
ensure_logger_configured()

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="小店评论经营助手 · 数据看板",
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
            background: var(--card) !important;
            border: 1px solid var(--coffee-100) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045) !important;
        }

        .dashboard-top {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 18px;
            border-bottom: 1px solid var(--coffee-100);
            padding-bottom: 16px;
            margin-bottom: 18px;
        }

        .dashboard-title-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .dashboard-title-icon {
            width: 42px;
            height: 42px;
            border-radius: 14px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: var(--coffee-50);
            border: 1px solid var(--coffee-100);
            font-size: 1.35rem;
        }

        .dashboard-title {
            margin: 0;
            color: var(--coffee-800);
            font-size: 1.58rem;
            font-weight: 950;
            letter-spacing: -0.4px;
            line-height: 1.1;
        }

        .dashboard-subtitle {
            margin-top: 7px;
            color: var(--coffee-400);
            font-size: .84rem;
            line-height: 1.5;
        }

        .dashboard-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            flex-wrap: wrap;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 11px !important;
            font-weight: 900 !important;
            min-height: 40px !important;
            border: 1px solid var(--coffee-100) !important;
            box-shadow: 0 1px 4px rgba(0,0,0,.035) !important;
        }

        .owner-metric {
            display: flex;
            align-items: center;
            gap: 14px;
            min-height: 116px;
            padding: 18px 20px;
            border: 1px solid var(--coffee-100);
            border-radius: 16px;
            background: #fff;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045);
        }

        .owner-metric-icon {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            font-size: 1.25rem;
        }

        .owner-metric-label {
            color: var(--coffee-400);
            font-size: .76rem;
            font-weight: 850;
            margin-bottom: 5px;
        }

        .owner-metric-value {
            color: var(--coffee-800);
            font-size: 1.75rem;
            font-weight: 950;
            line-height: 1.05;
            margin-bottom: 6px;
            letter-spacing: -.5px;
        }

        .owner-metric-hint {
            color: var(--coffee-300);
            font-size: .70rem;
            line-height: 1.35;
        }

        .owner-metric-hint.good { color: var(--success); font-weight: 800; }
        .owner-metric-hint.warn { color: var(--warning); font-weight: 800; }
        .owner-metric-hint.danger { color: var(--danger); font-weight: 800; }

        .section-card {
            background: #FFFFFF;
            border: 1px solid var(--coffee-100);
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045);
        }

        .section-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
        }

        .section-title {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--coffee-700);
            font-size: 1rem;
            font-weight: 950;
            margin: 0;
        }

        .section-subtitle {
            color: var(--coffee-300);
            font-size: .72rem;
            margin-top: 4px;
            line-height: 1.45;
        }

        .section-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 6px 11px;
            background: var(--cream);
            border: 1px solid var(--coffee-100);
            color: var(--coffee-500);
            font-size: .72rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .issue-card {
            position: relative;
            overflow: hidden;
            background: #FFFFFF;
            border: 1px solid var(--coffee-100);
            border-radius: 15px;
            padding: 16px 18px 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.025);
        }

        .issue-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            width: 4px;
            background: var(--issue-color, var(--warning));
        }

        .issue-topline {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 8px;
        }

        .issue-title-wrap {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }

        .issue-rank {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            background: var(--issue-bg, var(--warning-bg));
            color: var(--issue-color, var(--warning));
            font-size: .82rem;
            font-weight: 950;
        }

        .issue-title {
            color: var(--coffee-800);
            font-size: .98rem;
            font-weight: 950;
            line-height: 1.28;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .issue-severity {
            border-radius: 999px;
            padding: 3px 8px;
            background: var(--issue-bg, var(--warning-bg));
            color: var(--issue-color, var(--warning));
            font-size: .68rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .issue-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
        }

        .issue-chip {
            display: inline-flex;
            align-items: center;
            border-radius: 8px;
            padding: 4px 8px;
            background: var(--coffee-50);
            color: var(--coffee-500);
            font-size: .70rem;
            font-weight: 850;
        }

        .quote-box {
            border-radius: 12px;
            background: linear-gradient(180deg,#FFFCF8 0%,#F8F3EC 100%);
            border: 1px solid #EFE7DC;
            padding: 10px 12px;
            margin: 10px 0;
            color: var(--coffee-600);
            font-size: .76rem;
            line-height: 1.58;
        }

        .quote-box b {
            color: var(--coffee-500);
            margin-right: 4px;
        }

        .action-box {
            border-radius: 12px;
            background: #fff;
            border: 1px solid var(--coffee-100);
            padding: 10px 12px;
            color: var(--coffee-700);
            font-size: .76rem;
            line-height: 1.58;
            font-weight: 700;
        }

        .chart-card {
            border: 1px solid var(--coffee-100);
            border-radius: 14px;
            background: #fff;
            padding: 14px 14px 12px;
        }

        .bar-row {
            display: grid;
            grid-template-columns: 82px 1fr 28px;
            gap: 8px;
            align-items: center;
            margin: 10px 0;
        }

        .bar-label {
            color: var(--coffee-500);
            font-size: .70rem;
            font-weight: 850;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .bar-track {
            height: 10px;
            border-radius: 999px;
            background: var(--coffee-50);
            overflow: hidden;
        }

        .bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg,#D64545,#E8A13C);
        }

        .bar-value {
            color: var(--coffee-700);
            font-size: .72rem;
            font-weight: 950;
            text-align: right;
        }

        .progress-list {
            display: flex;
            flex-direction: column;
            gap: 0;
        }

        .progress-row {
            display: grid;
            grid-template-columns: 30px 1fr auto;
            gap: 10px;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--coffee-50);
        }

        .progress-row:last-child { border-bottom: none; }

        .progress-icon {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: .82rem;
        }

        .progress-name {
            color: var(--coffee-700);
            font-size: .78rem;
            font-weight: 900;
        }

        .progress-detail {
            color: var(--coffee-300);
            font-size: .70rem;
            line-height: 1.35;
            margin-top: 2px;
        }

        .progress-badge {
            border-radius: 999px;
            padding: 4px 9px;
            font-size: .68rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .queue-headline {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .queue-count {
            border-radius: 999px;
            padding: 5px 10px;
            background: var(--warning-bg);
            color: var(--warning);
            font-size: .70rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .queue-table-head,
        .queue-row {
            display: grid;
            grid-template-columns: 64px 1fr 84px 76px;
            gap: 8px;
            align-items: center;
        }

        .queue-table-head {
            border-radius: 10px;
            background: var(--coffee-50);
            color: var(--coffee-500);
            font-size: .70rem;
            font-weight: 950;
            padding: 9px 10px;
        }

        .queue-row {
            padding: 9px 10px;
            border-bottom: 1px solid var(--coffee-50);
            color: var(--coffee-700);
            font-size: .74rem;
        }

        .queue-row:last-child { border-bottom: none; }

        .queue-id {
            font-weight: 950;
            color: var(--coffee-700);
        }

        .queue-text {
            color: var(--coffee-500);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .safe-badge {
            display: inline-flex;
            justify-content: center;
            border-radius: 999px;
            padding: 4px 8px;
            font-size: .68rem;
            font-weight: 950;
        }

        .owner-empty {
            border: 1px dashed var(--coffee-200);
            border-radius: 14px;
            background: var(--cream);
            padding: 18px;
            color: var(--coffee-400);
            font-size: .80rem;
            line-height: 1.65;
        }

        .footer-note {
            display: flex;
            gap: 14px;
            align-items: center;
            color: var(--coffee-300);
            font-size: .76rem;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--coffee-100);
        }

        div[data-testid="stDataFrame"] th {
            background: var(--coffee-50) !important;
            color: var(--coffee-700) !important;
            font-weight: 900 !important;
            font-size: .72rem !important;
        }

        div[data-testid="stDataFrame"] td {
            font-size: .74rem !important;
            color: var(--coffee-700) !important;
        }

        @media (max-width: 1260px) {
            .stMain .block-container {
                padding-left: 1.6rem !important;
                padding-right: 1.6rem !important;
            }
            .dashboard-top {
                align-items: flex-start;
                flex-direction: column;
            }
            .dashboard-actions {
                justify-content: flex-start;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


_EVIDENCE_STATUS_CN: dict[str, str] = {
    "sufficient": "证据充分",
    "insufficient": "证据不足",
    "weak": "证据较弱",
}


def _cn_topic(raw: str) -> str:
    """Convert a raw issue_name to Chinese if it contains English topic keys."""
    result = raw or "未命名问题"
    for en, cn in TOPIC_CN_MAP.items():
        result = result.replace(en, cn)
    return result


def _truncate(text: str | None, max_len: int = 54) -> str:
    value = (text or "").strip()
    if len(value) <= max_len:
        return value or "暂无内容"
    return value[:max_len] + "…"


def _status_style(status: str) -> tuple[str, str, str]:
    """Return (fg, bg, label) for process status."""
    if status == "passed":
        return "#27AE60", "#E8F8F0", "已完成"
    if status == "failed":
        return "#C0392B", "#FDEDEC", "需处理"
    if status == "warning":
        return "#E67E22", "#FEF5E7", "注意"
    return "#E67E22", "#FEF5E7", "进行中"


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════════
def _load_dashboard_data(batch_id: str) -> dict:
    """Load all dashboard data from real services for a given batch."""
    insight_svc = InsightService()
    reply_svc = ReplyService()
    trace_svc = TraceService()
    eval_svc = EvalService()

    top_issues = insight_svc.get_top_issues(batch_id)

    all_evidence_ids = set()
    for issue in top_issues:
        evidence_rows = insight_svc.get_issue_evidence(issue["id"])
        issue["evidence_review_ids"] = [e["review_id"] for e in evidence_rows]
        all_evidence_ids.update(issue["evidence_review_ids"])

    evidence_text_map: dict[str, str] = {}
    if all_evidence_ids:
        with get_connection() as conn:
            placeholders = ",".join(["?" for _ in all_evidence_ids])
            rows = conn.execute(
                f"SELECT review_id, review_text FROM reviews WHERE review_id IN ({placeholders})",
                list(all_evidence_ids),
            ).fetchall()
            evidence_text_map = {r["review_id"]: (r["review_text"] or "")[:140] for r in rows}

    for issue in top_issues:
        issue["evidence_review_texts"] = [
            {"review_id": rid, "text": evidence_text_map.get(rid, "")}
            for rid in issue["evidence_review_ids"]
        ]

    pending_drafts = reply_svc.get_pending_drafts(batch_id)
    traces = trace_svc.get_trace(batch_id)
    latest_eval = eval_svc.get_latest_eval()

    with get_connection() as conn:
        valid_reviews = conn.execute(
            "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ? AND is_valid = 1",
            (batch_id,),
        ).fetchone()
        total_valid = valid_reviews["cnt"] if valid_reviews else 0

        avg_row = conn.execute(
            "SELECT AVG(CAST(rating AS REAL)) as avg_r FROM reviews WHERE batch_id = ? AND is_valid = 1",
            (batch_id,),
        ).fetchone()
        avg_rating = round(avg_row["avg_r"], 1) if avg_row and avg_row["avg_r"] else 0

        neg_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ? AND is_negative_candidate = 1",
            (batch_id,),
        ).fetchone()
        negative_count = neg_row["cnt"] if neg_row else 0

        analysis_exists = conn.execute(
            "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()["cnt"]

    return {
        "top_issues": top_issues,
        "pending_drafts": pending_drafts,
        "traces": traces,
        "latest_eval": latest_eval,
        "total_valid": total_valid,
        "avg_rating": avg_rating,
        "negative_count": negative_count,
        "pending_count": len(pending_drafts),
        "has_analysis": analysis_exists > 0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Components
# ═══════════════════════════════════════════════════════════════════════════
def _render_page_header(batch_id: str | None) -> None:
    """Render top title and action buttons."""
    st.markdown(
        """
        <div class="dashboard-top">
            <div>
                <div class="dashboard-title-row">
                    <div class="dashboard-title-icon">📊</div>
                    <div>
                        <h1 class="dashboard-title">数据看板</h1>
                        <div class="dashboard-subtitle">看清顾客最关心的问题，优先处理需要回复的差评。</div>
                    </div>
                </div>
            </div>
            <div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Buttons rendered by Streamlit for real interactions.
    b1, b2, b3, spacer = st.columns([1.05, 1.05, 1.05, 5], gap="small")
    with b1:
        if batch_id:
            try:
                reply_svc = ReplyService()
                export_data = reply_svc.export_approved_replies(batch_id)
                if export_data.get("drafts") and export_data.get("csv_data"):
                    st.download_button(
                        label="📥 导出回复",
                        data=export_data["csv_data"],
                        file_name=f"approved_replies_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        width="stretch",
                        key="export_approved",
                    )
                else:
                    st.button("📥 导出回复", width="stretch", disabled=True, key="export_disabled_dash")
            except Exception:
                st.button("📥 导出回复", width="stretch", disabled=True, key="export_error_dash")
        else:
            st.button("📥 导出回复", width="stretch", disabled=True, key="export_no_batch")
    with b2:
        if st.button("🧾 检查记录", key="run_eval_dash", width="stretch"):
            st.switch_page("pages/trace_eval_page.py")
    with b3:
        if st.button("🔍 处理记录", key="view_trace_dash", width="stretch"):
            st.switch_page("pages/trace_eval_page.py")

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)


def _render_owner_metric(label: str, value: str | int | float, icon: str, hint: str, status: str = "neutral") -> None:
    bg_map = {
        "good": "#E8F8F0",
        "warn": "#FEF5E7",
        "danger": "#FDEDEC",
        "neutral": "#F5F0E8",
    }
    fg_map = {
        "good": "#27AE60",
        "warn": "#E67E22",
        "danger": "#C0392B",
        "neutral": "#6B4C3B",
    }
    hint_class = "good" if status == "good" else "warn" if status == "warn" else "danger" if status == "danger" else ""
    st.markdown(
        f"""
        <div class="owner-metric">
            <div class="owner-metric-icon" style="background:{bg_map.get(status, bg_map['neutral'])};color:{fg_map.get(status, fg_map['neutral'])};">{icon}</div>
            <div>
                <div class="owner-metric-label">{safe_html(label)}</div>
                <div class="owner-metric-value">{safe_html(str(value))}</div>
                <div class="owner-metric-hint {hint_class}">{safe_html(hint)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_metrics(data: dict) -> None:
    """Render top business metrics."""
    total = data["total_valid"]
    avg = data["avg_rating"]
    negative = data["negative_count"]
    pending = data["pending_count"]

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        _render_owner_metric("本次评论", total, "💬", f"共分析 {total} 条可用评论", "neutral")
    with c2:
        score_status = "good" if avg >= 4 else "warn" if avg >= 3 else "danger"
        score_hint = "评分较好，继续保持" if avg >= 4 else "评分偏低，建议查看原因" if avg < 3 else "仍有提升空间"
        _render_owner_metric("顾客评分", avg, "⭐", score_hint, score_status)
    with c3:
        neg_status = "danger" if negative > 0 else "good"
        neg_hint = "需要优先查看差评原因" if negative > 0 else "暂无明显差评问题"
        _render_owner_metric("需重点关注", negative, "⚠️", neg_hint, neg_status)
    with c4:
        pending_status = "warn" if pending > 0 else "good"
        pending_hint = "回复草稿等待确认" if pending > 0 else "回复都已处理完成"
        _render_owner_metric("待确认回复", pending, "✏️", pending_hint, pending_status)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)


def _render_issue_card(issue: dict) -> None:
    """Render one owner-friendly issue card."""
    sev = issue.get("severity_level", "medium")
    sev_config = {
        "high": ("#C0392B", "#FDEDEC", "严重"),
        "medium": ("#E67E22", "#FEF5E7", "中等"),
        "low": ("#27AE60", "#E8F8F0", "轻微"),
    }
    color, bg, sev_label = sev_config.get(sev, ("#8B7355", "#F5F0E8", "关注"))
    title = _cn_topic(issue.get("issue_name", "未命名问题"))
    rank = issue.get("rank", "-")
    mention_count = issue.get("mention_count", 0)
    evidence_count = issue.get("evidence_count", 0)
    evidence_status = _EVIDENCE_STATUS_CN.get(issue.get("evidence_status", ""), "已关联评论")

    evidence_texts = issue.get("evidence_review_texts", [])
    first_quote = ""
    if evidence_texts:
        first_quote = evidence_texts[0].get("text") or ""
    if not first_quote:
        first_quote = "暂无典型评论原文，可在详情中查看关联评论。"

    suggested = issue.get("suggested_action") or "建议结合门店实际情况，优先安排负责人跟进。"

    st.markdown(
        f"""
        <div class="issue-card" style="--issue-color:{color};--issue-bg:{bg};">
            <div class="issue-topline">
                <div class="issue-title-wrap">
                    <div class="issue-rank">{safe_html(str(rank))}</div>
                    <div class="issue-title">{safe_html(title)}</div>
                </div>
                <div class="issue-severity">{safe_html(sev_label)}</div>
            </div>
            <div class="issue-meta">
                <span class="issue-chip">{mention_count} 条评论提到</span>
                <span class="issue-chip">{evidence_count} 条原始评论</span>
                <span class="issue-chip">{safe_html(evidence_status)}</span>
            </div>
            <div class="quote-box"><b>顾客原话：</b>{safe_html(_truncate(first_quote, 86))}</div>
            <div class="action-box">💡 建议：{safe_html(suggested)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_issue_chart(issues: list[dict]) -> None:
    """Render issue mention counts as a leaderboard with progress bars."""
    if not issues:
        return

    max_count = max([int(i.get("mention_count", 0) or 0) for i in issues] + [1])
    with st.container(border=True):
        st.markdown("**问题提及次数**")
        for issue in issues[:5]:
            name = _truncate(_cn_topic(issue.get("issue_name", "问题")), 8)
            count = int(issue.get("mention_count", 0) or 0)
            c1, c2, c3 = st.columns([3, 1, 1], gap="small")
            with c1:
                st.caption(name)
                st.progress(count / max_count)
            with c2:
                st.markdown(f"**{count}**")
            with c3:
                pass
        st.caption("💡 排名靠前的问题，建议优先安排门店负责人跟进。")


def _render_top_issues(data: dict) -> None:
    issues = data["top_issues"]
    left, right = st.columns([1.65, 0.85], gap="medium")

    with left:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-head">
                    <div>
                        <p class="section-title">☰ 重点问题</p>
                        <div class="section-subtitle">系统从评论中整理出的高频问题，建议优先处理前几项。</div>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )
        if issues:
            for issue in issues[:3]:
                _render_issue_card(issue)
                evidence_texts = issue.get("evidence_review_texts", [])
                if evidence_texts:
                    with st.expander(f"查看相关评论原文（{len(evidence_texts)} 条）", expanded=False):
                        for et in evidence_texts:
                            st.caption(f"**{et.get('review_id', '')}** — {et.get('text', '')}")
        else:
            st.markdown(
                """
                <div class="owner-empty">
                    暂无明显高频问题。继续积累评论后，这里会显示顾客最常提到的问题。
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        _render_issue_chart(issues)


def _process_rows_from_traces(traces: list[dict], pending_count: int) -> list[dict]:
    trace_map = {t["step_name"]: t for t in traces}

    input_status = trace_map.get("input_validation", {}).get("status", "pending")
    classify_status = trace_map.get("classification", {}).get("status", "pending")
    insight_status = trace_map.get("insight_generation", {}).get("status", "pending")
    reply_status = trace_map.get("reply_generation", {}).get("status", "pending")
    safety_status = trace_map.get("safety_check", {}).get("status", "pending")

    return [
        {
            "name": "表格已检查",
            "status": input_status,
            "detail": translate_trace_detail(trace_map.get("input_validation", {}).get("output_summary", "评论表检查完成")),
        },
        {
            "name": "评论已分类",
            "status": classify_status,
            "detail": translate_trace_detail(trace_map.get("classification", {}).get("output_summary", "已按问题类型整理评论")),
        },
        {
            "name": "经营建议已生成",
            "status": insight_status,
            "detail": translate_trace_detail(trace_map.get("insight_generation", {}).get("output_summary", "已生成重点问题和建议")),
        },
        {
            "name": "回复草稿已生成",
            "status": reply_status,
            "detail": translate_trace_detail(trace_map.get("reply_generation", {}).get("output_summary", "已生成待确认回复")),
        },
        {
            "name": "回复风险已检查",
            "status": safety_status,
            "detail": translate_trace_detail(trace_map.get("safety_check", {}).get("output_summary", "已检查回复风险")),
        },
        {
            "name": "等待人工确认",
            "status": "passed" if pending_count == 0 else "pending",
            "detail": f"还有 {pending_count} 条回复需要确认" if pending_count > 0 else "所有回复都已处理完成",
        },
    ]


def _render_process_status(traces: list[dict], pending_count: int) -> None:
    rows = _process_rows_from_traces(traces, pending_count)
    done = sum(1 for r in rows if r["status"] == "passed")
    pass_rate = int(done / max(len(rows), 1) * 100)

    with st.container(border=True):
        st.markdown(f"**🛡️ 处理进度**  ·  完成 {pass_rate}%")
        st.caption("从上传到生成回复的关键步骤。")
        for row in rows:
            fg, bg, badge = _status_style(row["status"])
            c1, c2, c3 = st.columns([4, 6, 3], gap="small")
            with c1:
                st.markdown(f"**{safe_html(row['name'])}**")
            with c2:
                st.caption(safe_html(row['detail']))
            with c3:
                st.markdown(
                    f'<span style="color:{fg};background:{bg};padding:2px 10px;'
                    f'border-radius:10px;font-size:0.72rem;font-weight:600;">{safe_html(badge)}</span>',
                    unsafe_allow_html=True,
                )


def _render_reply_queue(drafts: list[dict], page: int, page_size: int = 4) -> None:
    start = page * page_size
    page_items = drafts[start:start + page_size]

    st.markdown(
        f"""
        <div class="section-card">
            <div class="queue-headline">
                <div>
                    <p class="section-title">💌 待确认回复</p>
                    <div class="section-subtitle">系统已生成草稿，确认后再用于回复顾客。</div>
                </div>
                <div class="queue-count">{len(drafts)} 条待确认</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    if not drafts:
        st.markdown(
            """
            <div class="owner-empty">
                目前没有待确认的回复。所有差评回复都已处理完成。
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if not page_items:
        st.markdown(
            """
            <div class="owner-empty">当前页暂无数据。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    safety_colors = {
        "pass": ("#27AE60", "#E8F8F0", "可确认"),
        "rewrite_required": ("#E67E22", "#FEF5E7", "需调整"),
        "blocked": ("#C0392B", "#FDEDEC", "需人工处理"),
    }

    st.markdown(
        """
        <div class="queue-table-head">
            <div>评论</div><div>回复草稿预览</div><div>状态</div><div>操作</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for item in page_items:
        safety = item.get("safety_status", "pass")
        fg, bg, label = safety_colors.get(safety, ("#8B7355", "#F5F0E8", "待确认"))
        draft_snippet = _truncate(item.get("draft_text", ""), 42)
        review_id = item.get("review_id", "—")

        r1, r2 = st.columns([12, 2.1], gap="small")
        with r1:
            st.markdown(
                f"""
                <div class="queue-row">
                    <div class="queue-id">{safe_html(str(review_id))}</div>
                    <div class="queue-text">{safe_html(draft_snippet)}</div>
                    <div><span class="safe-badge" style="background:{bg};color:{fg};">{safe_html(label)}</span></div>
                    <div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r2:
            if st.button("去确认", key=f"q_review_{review_id}", type="secondary", width="stretch"):
                st.session_state.reply_selected_id = item.get("review_id", "")
                st.session_state.reply_selected_draft_id = item.get("id", "")
                st.switch_page("pages/reply_review_page.py")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_pagination(total_items: int, page_size: int = 4) -> int:
    page_key = "queue_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    total_pages = max(1, (total_items + page_size - 1) // page_size)
    current = st.session_state[page_key]
    if current >= total_pages:
        current = 0
        st.session_state[page_key] = 0

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown(
            f'<div style="text-align:right;padding-top:7px;font-size:0.76rem;color:#8B7355;">'
            f'{current + 1} / {total_pages} · 共 {total_items} 条</div>',
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("上一页", key="page_prev", disabled=(current == 0), width="stretch"):
            st.session_state[page_key] = max(0, current - 1)
            st.rerun()
    with c3:
        if st.button("下一页", key="page_next", disabled=(current >= total_pages - 1), width="stretch"):
            st.session_state[page_key] = min(total_pages - 1, current + 1)
            st.rerun()
    return current


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    st.session_state.nav_selection = "数据看板"
    render_sidebar()

    batch_id = st.session_state.get("current_batch_id")
    if not batch_id:
        qp_bid = st.query_params.get("batch_id")
        if qp_bid:
            st.session_state.current_batch_id = qp_bid
            batch_id = qp_bid

    _render_page_header(batch_id)

    if not batch_id:
        st.markdown(
            """
            <div class="owner-empty">
                👈 请先到「上传评论」页面上传评论表，并点击「开始分析」。分析完成后，这里会显示顾客反馈、重点问题和待确认回复。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    try:
        data = _load_dashboard_data(batch_id)
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        return

    if not data["has_analysis"]:
        st.markdown(
            """
            <div class="owner-empty">
                这份评论表还没有完成分析。请回到「上传评论」页面点击「开始分析」。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    _render_metrics(data)

    left_col, right_col = st.columns([5.7, 4.3], gap="medium")

    with left_col:
        _render_top_issues(data)

    with right_col:
        _render_process_status(data["traces"], data["pending_count"])

        queue = data["pending_drafts"]
        if "queue_page" not in st.session_state:
            st.session_state["queue_page"] = 0
        page = st.session_state["queue_page"]
        total_pages = max(1, (len(queue) + 4 - 1) // 4)
        if page >= total_pages:
            page = 0
            st.session_state["queue_page"] = 0
        _render_reply_queue(queue, page, page_size=4)
        if queue:
            _render_pagination(len(queue), page_size=4)

    st.markdown(
        f"""
        <div class="footer-note">
            <span>🕒 数据最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
            <span>刷新页面可查看最新处理结果</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
