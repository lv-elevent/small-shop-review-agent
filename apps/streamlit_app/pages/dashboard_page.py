"""
Dashboard Page — 数据看板：评论概览、三大问题、Harness 状态、审核队列
接入 InsightService / ReplyService / TraceService / EvalService 真实数据
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

from apps.streamlit_app.components.metric_card import metric_card
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
st.markdown("""
<style>
    .stApp { background: #FAFBF7; }

    hr.custom-hr {
        border: none;
        border-top: 1px solid #E8E0D5;
        margin: 18px 0;
    }

    /* ── Issue card ── */
    .issue-card {
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        position: relative;
        overflow: hidden;
    }
    .issue-card .severity-stripe {
        position: absolute;
        left: 0; top: 0; bottom: 0;
        width: 4px;
        border-radius: 14px 0 0 14px;
    }
    .issue-card .issue-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    .issue-card .issue-num {
        font-size: 0.72rem;
        font-weight: 700;
        color: #8B7355;
        background: #F5F0E8;
        padding: 2px 8px;
        border-radius: 5px;
    }
    .issue-card .issue-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #3D2C20;
        margin-bottom: 6px;
    }
    .issue-card .issue-stats {
        display: flex;
        gap: 16px;
        margin-bottom: 4px;
        font-size: 0.80rem;
        color: #6B5B4F;
    }
    .issue-card .evidence-list {
        font-size: 0.76rem;
        color: #8B7355;
        margin-bottom: 8px;
        line-height: 1.7;
    }
    .issue-card .evidence-list code {
        background: #F5F0E8;
        color: #6B4C3B;
        padding: 1px 6px;
        border-radius: 3px;
        font-size: 0.73rem;
        margin: 0 1px;
    }
    .issue-card .btn-suggestion {
        display: inline-block;
        background: #F5F0E8;
        color: #5C3D2E;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 7px 16px;
        border-radius: 8px;
        border: 1px solid #E8E0D5;
    }

    /* ── Severity dot ── */
    .sev-dot {
        font-weight: 700;
        font-size: 0.80rem;
    }

    /* ── Section card ── */
    .section-card {
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .section-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #4A3728;
        margin-bottom: 12px;
    }

    /* ── Harness row ── */
    .hw-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 11px 0;
        border-bottom: 1px solid #F5F0E8;
        font-size: 0.82rem;
    }
    .hw-row:last-child { border-bottom: none; }
    .hw-icon { font-size: 1rem; min-width: 20px; text-align: center; }
    .hw-badge {
        display: inline-block; font-size: 0.68rem; font-weight: 600;
        padding: 2px 10px; border-radius: 10px; white-space: nowrap;
    }

    /* ── Queue row ── */
    .q-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 3px 10px;
        border-bottom: 1px solid #F5F0E8;
        font-size: 0.76rem;
    }
    .q-item:last-child { border-bottom: none; }
    .q-id { font-weight: 600; color: #4A3728; min-width: 48px; }
    .q-text { flex: 1; color: #6B5B4F; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .q-badge {
        font-size: 0.68rem; font-weight: 600; padding: 2px 8px; border-radius: 10px;
        white-space: nowrap;
    }

    /* ── Dataframe overrides ── */
    div[data-testid="stDataFrame"] th {
        background: #F5F0E8 !important;
        color: #4A3728 !important;
        font-weight: 700 !important;
        font-size: 0.76rem !important;
    }
    div[data-testid="stDataFrame"] td {
        font-size: 0.80rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border: 1px solid #E8E0D5 !important;
        border-radius: 14px !important;
        padding: 18px 20px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    }
</style>
""", unsafe_allow_html=True)


_EVIDENCE_STATUS_CN: dict[str, str] = {
    "sufficient": "证据充分",
    "insufficient": "证据不足",
    "weak": "证据较弱",
}

def _cn_topic(raw: str) -> str:
    """Convert a raw issue_name to Chinese if it contains English topic keys."""
    result = raw
    for en, cn in TOPIC_CN_MAP.items():
        result = result.replace(en, cn)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════════

def _load_dashboard_data(batch_id: str) -> dict:
    """Load all dashboard data from real services for a given batch."""
    insight_svc = InsightService()
    reply_svc = ReplyService()
    trace_svc = TraceService()
    eval_svc = EvalService()

    # Top issues
    top_issues = insight_svc.get_top_issues(batch_id)

    # Attach evidence review_ids to each issue
    for issue in top_issues:
        evidence_rows = insight_svc.get_issue_evidence(issue["id"])
        issue["evidence_review_ids"] = [e["review_id"] for e in evidence_rows]

    # Pending drafts
    pending_drafts = reply_svc.get_pending_drafts(batch_id)

    # Traces
    traces = trace_svc.get_trace(batch_id)

    # Eval
    latest_eval = eval_svc.get_latest_eval()

    # Counts from DB
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
            "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?", (batch_id,),
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
# Pagination
# ═══════════════════════════════════════════════════════════════════════════

def _render_pagination(total_items: int, page_size: int = 5) -> int:
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
            f'<div style="text-align:right;padding-top:4px;font-size:0.78rem;color:#8B7355;">'
            f'{current + 1} / {total_pages} · 共 {total_items} 条</div>',
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("◀", key="page_prev", disabled=(current == 0), width='stretch'):
            st.session_state[page_key] = max(0, current - 1)
            st.rerun()
    with c3:
        if st.button("▶", key="page_next", disabled=(current >= total_pages - 1), width='stretch'):
            st.session_state[page_key] = min(total_pages - 1, current + 1)
            st.rerun()
    return current


# ═══════════════════════════════════════════════════════════════════════════
# Component: Issue Card (real data shape)
# ═══════════════════════════════════════════════════════════════════════════

def _render_issue_card(issue: dict) -> None:
    sev = issue.get("severity_level", "medium")
    sev_colors = {"high": "#C0392B", "medium": "#E67E22", "low": "#27AE60"}
    stripe_color = sev_colors.get(sev, "#8B7355")
    sev_color = sev_colors.get(sev, "#8B7355")
    sev_label = {"high": "高", "medium": "中", "low": "低"}.get(sev, sev)

    evidence_ids = issue.get("evidence_review_ids", [])
    evidence_html = " ".join(f"<code>{safe_html(eid)}</code>" for eid in evidence_ids) if evidence_ids else "暂无关联评论"

    html = f"""<div class="issue-card">
<div class="severity-stripe" style="background:{stripe_color};"></div>
<div class="issue-header">
<span class="issue-num">问题 #{issue['rank']}</span>
<span class="sev-dot" style="color:{sev_color};">● {sev_label}严重</span>
</div>
<div class="issue-title">{safe_html(_cn_topic(issue['issue_name']))}</div>
<div class="issue-stats">
<span>提及 <b>{issue['mention_count']}</b> 次</span>
<span>证据 <b>{issue['evidence_count']}</b> 条 · {_EVIDENCE_STATUS_CN.get(issue.get('evidence_status', ''), issue.get('evidence_status', '—'))}</span>
</div>
<div class="evidence-list">关联评论：{evidence_html}</div>
<span class="btn-suggestion">💡 {safe_html(issue.get('suggested_action', '暂无建议'))}</span>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Component: Harness Status (derived from traces)
# ═══════════════════════════════════════════════════════════════════════════


def _render_harness_status(traces: list[dict], pending_count: int) -> None:
    trace_map = {t["step_name"]: t for t in traces}

    checks = [
        {
            "name": "输入校验",
            "status": trace_map.get("input_validation", {}).get("status", "pending"),
            "detail": translate_trace_detail(trace_map.get("input_validation", {}).get("output_summary", "—")),
        },
        {
            "name": "Schema 约束",
            "status": "passed" if all(
                t.get("status") != "failed" for t in traces
            ) else "failed",
            "detail": f"{len(traces)} 个步骤，无结构校验异常",
        },
        {
            "name": "证据绑定",
            "status": trace_map.get("evidence_check", {}).get("status", "pending"),
            "detail": translate_trace_detail(trace_map.get("evidence_check", {}).get("output_summary", "—")),
        },
        {
            "name": "安全检查",
            "status": trace_map.get("safety_check", {}).get("status", "pending"),
            "detail": translate_trace_detail(trace_map.get("safety_check", {}).get("output_summary", "—")),
        },
        {
            "name": "人工审批",
            "status": "passed" if pending_count == 0 else "pending",
            "detail": f"{pending_count} 条待审核" if pending_count > 0 else "全部审核完成",
        },
    ]

    status_icon = {"passed": "✓", "pending": "◷", "failed": "✗", "warning": "⚠"}
    status_color = {"passed": "#27AE60", "pending": "#E67E22", "failed": "#C0392B", "warning": "#E67E22"}
    status_badge = {
        "passed": ("#27AE60", "#E8F8F0", "✓ 通过"),
        "pending": ("#E67E22", "#FEF5E7", "◷ 进行中"),
        "failed": ("#C0392B", "#FDEDEC", "✗ 未通过"),
        "warning": ("#E67E22", "#FEF5E7", "⚠ 警告"),
    }

    html_parts = ['<div class="section-card">',
                  '<p class="section-title">AI 工作流可靠性检查</p>',
                  '<p style="font-size:0.74rem;color:#A09080;margin:-8px 0 10px 0;">防护引擎实时状态</p>']

    for check in checks:
        sts = check["status"]
        icon = status_icon.get(sts, "?")
        dot_c = status_color.get(sts, "#8B7355")
        badge_c, badge_bg, badge_label = status_badge.get(
            sts, ("#8B7355", "#F5F0E8", sts),
        )

        html_parts.append(f"""<div class="hw-row">
<span class="hw-icon" style="color:{dot_c};">{icon}</span>
<span style="font-weight:600;color:#4A3728;min-width:80px;">{check['name']}</span>
<span style="color:#A09080;flex:1;font-size:0.80rem;">{check['detail']}</span>
<span class="hw-badge" style="color:{badge_c};background:{badge_bg};">{badge_label}</span>
</div>""")

    html_parts.append('</div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Component: Reply Queue (real draft data)
# ═══════════════════════════════════════════════════════════════════════════

def _render_reply_queue(drafts: list[dict], page: int, page_size: int = 4) -> None:
    start = page * page_size
    page_items = drafts[start:start + page_size]

    if not drafts:
        st.info("所有差评回复已处理完毕")
        return

    if not page_items:
        st.info("当前页无数据")
        return

    safety_colors = {
        "pass": ("#27AE60", "✓ 安全"),
        "rewrite_required": ("#E67E22", "⚠ 需重写"),
        "blocked": ("#C0392B", "✗ 已拦截"),
    }

    with st.container(border=True):
        st.markdown(
            '<p class="section-title" style="margin-bottom:8px;">差评回复审核队列</p>',
            unsafe_allow_html=True,
        )

        for item in page_items:
            safety = item.get("safety_status", "pass")
            dot_c, dot_label = safety_colors.get(safety, ("#8B7355", safety))
            draft_snippet = (item.get("draft_text", "") or "")[:36]
            snippet = draft_snippet + ("…" if len(item.get("draft_text", "") or "") > 36 else "")

            r1, r2 = st.columns([20, 5], gap="small")
            with r1:
                st.markdown(f"""<div class="q-item">
<span class="q-id">{item['review_id']}</span>
<span class="q-text">{snippet}</span>
<span style="font-weight:600;font-size:0.76rem;color:{dot_c};">● {dot_label}</span>
</div>""", unsafe_allow_html=True)
            with r2:
                if st.button("审核", key=f"q_review_{item['review_id']}", type="secondary", width='stretch'):
                    st.switch_page("pages/reply_review_page.py")


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.session_state.nav_selection = "数据看板"
    render_sidebar()

    batch_id = st.session_state.get("current_batch_id")
    # Restore batch_id from URL query params on browser refresh
    if not batch_id:
        qp_bid = st.query_params.get("batch_id")
        if qp_bid:
            st.session_state.current_batch_id = qp_bid
            batch_id = qp_bid

    # ── Top bar ──
    left_top, right_top = st.columns([3, 2])
    with left_top:
        st.markdown("""
        <div style="margin-bottom:6px;">
            <h1 style="font-size:1.55rem;font-weight:700;color:#3D2C20;margin:0 0 2px 0;">📊 数据看板</h1>
            <p style="font-size:0.86rem;color:#8B7355;margin:0;">评论概览 · 三大问题洞察 · 回复审核队列 · Harness 状态</p>
        </div>
        """, unsafe_allow_html=True)

    with right_top:
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        bc1, bc2, bc3 = st.columns(3, gap="small")
        with bc1:
            if batch_id:
                try:
                    reply_svc = ReplyService()
                    export_data = reply_svc.export_approved_replies(batch_id)
                    if export_data.get("drafts") and export_data.get("csv_data"):
                        st.download_button(
                            label="📥 导出", data=export_data["csv_data"],
                            file_name=f"approved_replies_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv", width='stretch', key="export_approved",
                        )
                    else:
                        st.button("📥 导出", width='stretch', disabled=True, key="export_disabled_dash")
                except Exception:
                    st.button("📥 导出", width='stretch', disabled=True, key="export_error_dash")
            else:
                st.button("📥 导出", width='stretch', disabled=True, key="export_no_batch")
        with bc2:
            if st.button("🧪 评测", key="run_eval_dash", width='stretch'):
                st.switch_page("pages/trace_eval_page.py")
        with bc3:
            if st.button("🔍 追踪", key="view_trace_dash", width='stretch'):
                st.switch_page("pages/trace_eval_page.py")

    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)

    # ── No batch selected ──
    if not batch_id:
        st.info("👈 请先在 **「上传评论」** 页面中上传 CSV 文件（或开启 Demo Mode），点击「开始分析」后再来查看数据看板。")
        return

    # ── Load data ──
    try:
        data = _load_dashboard_data(batch_id)
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        return

    # ── No analysis ──
    if not data["has_analysis"]:
        st.warning("该批次尚未完成分析。请前往 **「上传评论」** 页面运行分析。")
        return

    # ── Metric cards ──
    mc1, mc2, mc3, mc4 = st.columns(4, gap="medium")
    with mc1:
        metric_card(label="总评论数", value=data["total_valid"], icon="📝",
                    color="#4A3728", bg_color="#FFFCF8", warn=False)
    with mc2:
        metric_card(label="平均评分", value=data["avg_rating"], icon="⭐",
                    color="#4A3728", bg_color="#FFFCF8", warn=False)
    with mc3:
        metric_card(label="差评数", value=data["negative_count"], icon="⚠️",
                    color="#C0392B", bg_color="#FFFCF8", warn=data["negative_count"] > 0)
    with mc4:
        pending = data["pending_count"]
        metric_card(label="待审核回复", value=pending, icon="✏️",
                    color="#E67E22" if pending > 0 else "#27AE60",
                    bg_color="#FFFCF8", warn=pending > 0)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Two-column layout ──
    left_col, right_col = st.columns([5, 5], gap="medium")

    with left_col:
        st.markdown(
            '<p class="section-title" style="margin-top:0;">三大问题洞察</p>',
            unsafe_allow_html=True,
        )
        if data["top_issues"]:
            for issue in data["top_issues"]:
                _render_issue_card(issue)
        else:
            st.info("暂无问题洞察数据")

    with right_col:
        _render_harness_status(data["traces"], data["pending_count"])

        # Reply queue
        queue = data["pending_drafts"]
        if "queue_page" not in st.session_state:
            st.session_state["queue_page"] = 0
        page = st.session_state["queue_page"]
        total_pages = max(1, (len(queue) + 4 - 1) // 4)
        if page >= total_pages:
            page = 0
            st.session_state["queue_page"] = 0
        _render_reply_queue(queue, page, page_size=4)

        _render_pagination(len(queue), page_size=4)


if __name__ == "__main__":
    main()
