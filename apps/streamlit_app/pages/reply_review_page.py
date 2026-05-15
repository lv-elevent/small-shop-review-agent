"""
Reply Review Page — 回复确认：左侧待办队列 + 右侧回复详情

设计目标：
- 面向小店老板/店长：将“审核 AI 回复”改成“确认顾客回复”。
- 减少技术词：不展示 AI、risk_types、approval_status 等内部概念。
- 保持真实业务链路：ReplyService.approve_draft / edit_draft / reject_draft。
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from apps.streamlit_app.components.sidebar import render_sidebar
from apps.streamlit_app.components.ui_helpers import safe_html
from small_shop_agent.domain.business_rules import TOPIC_CN_MAP
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.database import execute_migrations, get_connection
from small_shop_agent.utils.logger import ensure_logger_configured

execute_migrations()
ensure_logger_configured()

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="小店评论经营助手 · 回复确认",
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

        /* Hide Streamlit production-irrelevant chrome */
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
            background: #FFFFFF !important;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045) !important;
        }

        .review-top {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 18px;
            border-bottom: 1px solid var(--coffee-100);
            padding-bottom: 16px;
            margin-bottom: 18px;
        }

        .review-title-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .review-title-icon {
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

        .review-title {
            margin: 0;
            color: var(--coffee-800);
            font-size: 1.58rem;
            font-weight: 950;
            letter-spacing: -0.4px;
            line-height: 1.1;
        }

        .review-subtitle {
            margin-top: 7px;
            color: var(--coffee-400);
            font-size: .84rem;
            line-height: 1.5;
        }

        .pending-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 6px 12px;
            background: var(--warning-bg);
            color: var(--warning);
            font-size: .76rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .filter-row {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 18px;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 11px !important;
            font-weight: 900 !important;
            min-height: 40px !important;
            border: 1px solid var(--coffee-100) !important;
            box-shadow: 0 1px 4px rgba(0,0,0,.035) !important;
        }

        button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg,var(--coffee-600),var(--coffee-800)) !important;
            border-color: var(--coffee-700) !important;
            color: #FFFFFF !important;
            font-weight: 950 !important;
        }

        button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background: var(--coffee-800) !important;
            border-color: var(--coffee-800) !important;
        }

        .queue-section-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            gap: 10px;
        }

        .queue-title {
            color: var(--coffee-700);
            font-size: .94rem;
            font-weight: 950;
            margin: 0;
        }

        .queue-count {
            border-radius: 999px;
            padding: 4px 9px;
            background: var(--coffee-50);
            color: var(--coffee-500);
            font-size: .70rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .qi-row {
            display: grid;
            grid-template-columns: 54px 1fr auto 22px;
            align-items: center;
            gap: 10px;
            min-height: 58px;
            padding: 10px 12px;
            border: 1px solid var(--coffee-100);
            border-radius: 12px;
            background: #FFFFFF;
            transition: all 0.16s ease;
            box-shadow: 0 1px 4px rgba(0,0,0,.025);
            position: relative;
            overflow: hidden;
        }

        .qi-row.selected {
            border-color: #D1B996;
            background: linear-gradient(90deg,#FFF8EE 0%,#FFFFFF 80%);
            box-shadow: 0 8px 18px rgba(107,76,59,.075);
        }

        .qi-row.selected::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--coffee-600);
        }

        .qi-id {
            font-weight: 950;
            font-size: .78rem;
            color: var(--coffee-700);
            padding-left: 2px;
        }

        .qi-text {
            min-width: 0;
            font-size: .80rem;
            color: var(--coffee-600);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .qi-priority {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: .72rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .qi-arrow {
            color: var(--coffee-300);
            font-size: 1rem;
            font-weight: 900;
            text-align: right;
        }

        .detail-card {
            background: #FFFFFF;
            border: 1px solid var(--coffee-100);
            border-radius: 16px;
            padding: 20px 20px 18px;
            box-shadow: 0 8px 22px rgba(61,44,32,0.045);
        }

        .detail-head {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 14px;
        }

        .detail-title {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--coffee-700);
            font-size: .98rem;
            font-weight: 950;
            margin: 0;
        }

        .detail-subtitle {
            color: var(--coffee-300);
            font-size: .72rem;
            margin-top: 4px;
        }

        .detail-page {
            color: var(--coffee-300);
            font-size: .72rem;
            font-weight: 850;
            white-space: nowrap;
        }

        .suggested-reply {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 12px;
            align-items: center;
            border-radius: 13px;
            background: linear-gradient(180deg,#F8FAFF 0%,#F5F8FC 100%);
            border: 1px solid #E8EDF7;
            padding: 14px 14px;
            margin-bottom: 14px;
        }

        .reply-text {
            color: var(--coffee-700);
            font-size: .84rem;
            line-height: 1.7;
            font-weight: 650;
        }

        .label-line {
            display: flex;
            align-items: center;
            gap: 7px;
            color: var(--coffee-700);
            font-size: .82rem;
            font-weight: 950;
            margin: 14px 0 8px;
        }

        .original-review-box {
            background: linear-gradient(180deg,#FFFCF8 0%,#F8F3EC 100%);
            border: 1px solid #EFE7DC;
            border-radius: 12px;
            padding: 13px 14px;
            color: var(--coffee-700);
            font-size: .84rem;
            line-height: 1.7;
        }

        .review-meta-row {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin: 10px 0 12px;
            color: var(--coffee-400);
            font-size: .76rem;
            font-weight: 850;
        }

        .status-badge,
        .safety-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            padding: 6px 11px;
            font-size: .72rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .check-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 12px;
        }

        .check-card {
            border: 1px solid var(--coffee-100);
            border-radius: 12px;
            background: #FFFFFF;
            padding: 10px;
            min-height: 72px;
        }

        .check-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 6px;
        }

        .check-name {
            color: var(--coffee-700);
            font-size: .74rem;
            font-weight: 950;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .check-pill {
            border-radius: 999px;
            padding: 3px 7px;
            font-size: .66rem;
            font-weight: 950;
            white-space: nowrap;
        }

        .check-desc {
            color: var(--coffee-300);
            font-size: .68rem;
            line-height: 1.45;
        }

        .risk-note {
            border-radius: 12px;
            background: var(--warning-bg);
            color: var(--warning);
            border: 1px solid #F4D8B8;
            padding: 10px 12px;
            font-size: .76rem;
            line-height: 1.6;
            margin-bottom: 12px;
            font-weight: 750;
        }

        .final-state {
            border-radius: 12px;
            padding: 12px 14px;
            margin-top: 14px;
            font-size: .84rem;
            line-height: 1.65;
            font-weight: 850;
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

        .pgn-wrap {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 4px;
            margin: 8px 0 4px;
        }

        .pgn-item,
        .pgn-arrow {
            display: inline-block;
            min-width: 28px;
            height: 28px;
            line-height: 27px;
            text-align: center;
            border-radius: 7px;
            font-size: .74rem;
            font-weight: 850;
            border: 1px solid #E0D5C5;
            background: #FFFCF8;
            color: var(--coffee-400);
            padding: 0 6px;
        }

        .pgn-item.active {
            background: var(--coffee-800);
            color: #FAFBF7;
            border-color: var(--coffee-800);
            font-weight: 950;
        }

        .pgn-arrow.disabled {
            opacity: .35;
        }

        .pgn-ellipsis {
            padding: 0 2px;
            color: #C0B0A0;
            font-size: .78rem;
        }

        textarea {
            border-radius: 12px !important;
        }

        @media (max-width: 1260px) {
            .stMain .block-container {
                padding-left: 1.6rem !important;
                padding-right: 1.6rem !important;
            }
            .check-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════════
def _load_reply_review_data(batch_id: str) -> dict:
    """Load all drafts + review metadata for the Reply Review page."""
    rpr = ReplyRepository()
    drafts = rpr.list_drafts(batch_id)

    if not drafts:
        return {"drafts": [], "pending_count": 0, "blocked_count": 0, "rewrite_count": 0}

    review_ids = list({d["review_id"] for d in drafts})

    with get_connection() as conn:
        placeholders = ",".join(["?" for _ in review_ids])
        reviews = conn.execute(
            f"SELECT review_id, rating, platform, review_text, date, review_date, review_time, created_at "
            f"FROM reviews WHERE batch_id = ? AND review_id IN ({placeholders})",
            [batch_id] + review_ids,
        ).fetchall()
        review_map = {r["review_id"]: dict(r) for r in reviews}

        analysis_rows = conn.execute(
            f"SELECT review_id, severity, primary_topic FROM review_analysis "
            f"WHERE batch_id = ? AND review_id IN ({placeholders})",
            [batch_id] + review_ids,
        ).fetchall()
        analysis_map = {a["review_id"]: dict(a) for a in analysis_rows}

    for d in drafts:
        rm = review_map.get(d["review_id"], {})
        am = analysis_map.get(d["review_id"], {})
        d["rating"] = rm.get("rating", "")
        d["platform"] = rm.get("platform", "—")
        d["review_date"] = (
            rm.get("date")
            or rm.get("review_date")
            or rm.get("review_time")
            or rm.get("created_at")
            or "—"
        )
        if not d.get("original_review"):
            d["original_review"] = rm.get("review_text", "")

        sev_num = am.get("severity", 2)
        if sev_num >= 4:
            d["severity"] = "high"
        elif sev_num >= 3:
            d["severity"] = "medium"
        else:
            d["severity"] = "low"
        d["issue"] = TOPIC_CN_MAP.get(am.get("primary_topic", ""), am.get("primary_topic", "—"))

        if isinstance(d.get("risk_types"), str):
            import json

            try:
                d["risk_types"] = json.loads(d["risk_types"])
            except Exception:
                d["risk_types"] = []
        if d.get("risk_types") is None:
            d["risk_types"] = []

    pending_count = sum(1 for d in drafts if d["approval_status"] == "pending")
    blocked_count = sum(
        1 for d in drafts if d["safety_status"] == "blocked" and d["approval_status"] == "pending"
    )
    rewrite_count = sum(
        1
        for d in drafts
        if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending"
    )

    return {
        "drafts": drafts,
        "pending_count": pending_count,
        "blocked_count": blocked_count,
        "rewrite_count": rewrite_count,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
def _truncate(text: str | None, max_len: int = 44) -> str:
    value = (text or "").strip()
    if not value:
        return "暂无内容"
    if len(value) <= max_len:
        return value
    return value[:max_len] + "…"


def _sev_color(severity: str) -> str:
    return {"high": "#C0392B", "medium": "#E67E22", "low": "#27AE60"}.get(severity, "#8B7355")


def _sev_label(severity: str) -> str:
    return {"high": "高优先", "medium": "建议处理", "low": "可稍后"}.get(severity, "待处理")


def _safety_display(status: str) -> tuple[str, str, str, str]:
    cfg = {
        "pass": ("#27AE60", "#E8F8F0", "可以发布", "🛡️"),
        "rewrite_required": ("#E67E22", "#FEF5E7", "建议修改", "⚠️"),
        "blocked": ("#C0392B", "#FDEDEC", "不建议发布", "🚫"),
    }
    return cfg.get(status, ("#8B7355", "#F5F0E8", status or "待确认", "•"))


def _approval_display(status: str) -> tuple[str, str, str]:
    cfg = {
        "pending": ("#E67E22", "#FEF5E7", "待确认"),
        "approved": ("#27AE60", "#E8F8F0", "已发布"),
        "edited": ("#3498DB", "#EBF5FB", "已修改"),
        "rejected": ("#C0392B", "#FDEDEC", "未采用"),
    }
    return cfg.get(status, ("#8B7355", "#F5F0E8", status or "未知"))


def _status_badge_html(status: str) -> str:
    fg, bg, label = _approval_display(status)
    return f'<span class="status-badge" style="color:{fg};background:{bg};">{safe_html(label)}</span>'


def _safety_badge_html(status: str) -> str:
    fg, bg, label, icon = _safety_display(status)
    return f'<span class="safety-badge" style="color:{fg};background:{bg};">{icon} {safe_html(label)}</span>'


# ═══════════════════════════════════════════════════════════════════════════
# Filter
# ═══════════════════════════════════════════════════════════════════════════
def _apply_filter(drafts: list[dict], filter_key: str) -> list[dict]:
    if filter_key == "pending":
        return [d for d in drafts if d["approval_status"] == "pending"]
    if filter_key == "rewrite":
        return [
            d
            for d in drafts
            if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending"
        ]
    if filter_key == "blocked":
        return [d for d in drafts if d["safety_status"] == "blocked" and d["approval_status"] == "pending"]
    if filter_key == "processed":
        return [d for d in drafts if d["approval_status"] != "pending"]

    priority = {"pending": 0, "rewrite_required": 1, "blocked": 2, "processed": 3}
    return sorted(
        drafts,
        key=lambda d: priority.get(
            "pending"
            if d["approval_status"] == "pending" and d["safety_status"] not in ("rewrite_required", "blocked")
            else "rewrite_required"
            if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending"
            else "blocked"
            if d["safety_status"] == "blocked" and d["approval_status"] == "pending"
            else "processed",
            99,
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Components
# ═══════════════════════════════════════════════════════════════════════════
def _render_page_header(pending_count: int) -> None:
    st.markdown(
        f"""
        <div class="review-top">
            <div>
                <div class="review-title-row">
                    <div class="review-title-icon">💌</div>
                    <div>
                        <h1 class="review-title">回复确认</h1>
                        <div class="review-subtitle">确认系统生成的顾客回复，必要时修改后再发布。</div>
                    </div>
                </div>
            </div>
            <div class="pending-pill">{pending_count} 条待确认</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _filter_count(drafts: list[dict], key: str) -> int:
    return len(_apply_filter(drafts, key))


def _render_filters(drafts: list[dict]) -> None:
    if "rr_filter" not in st.session_state:
        st.session_state.rr_filter = "pending"

    filters = [
        ("all", "全部", len(drafts)),
        ("pending", "待确认", _filter_count(drafts, "pending")),
        ("rewrite", "建议修改", _filter_count(drafts, "rewrite")),
        ("blocked", "不建议发布", _filter_count(drafts, "blocked")),
        ("processed", "已完成", _filter_count(drafts, "processed")),
    ]

    fc = st.columns(len(filters), gap="small")
    for i, (key, label, count) in enumerate(filters):
        with fc[i]:
            active = st.session_state.rr_filter == key
            button_label = f"{label}  {count}"
            if st.button(button_label, key=f"filter_{key}", width="stretch", type="primary" if active else "secondary"):
                st.session_state.rr_filter = key
                st.session_state.rr_queue_page = 0
                st.session_state.reply_selected_idx = 0
                st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


def _render_pagination(total: int, page_size: int, page_key: str) -> int:
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    cur = st.session_state[page_key]
    if cur >= total_pages:
        st.session_state[page_key] = 0
        cur = 0

    if total_pages <= 1:
        return 0

    parts: list[str] = []
    prev_cls = "pgn-arrow disabled" if cur == 0 else "pgn-arrow"
    parts.append(f'<span class="{prev_cls}">‹</span>')

    if total_pages <= 7:
        for p in range(total_pages):
            cls = "pgn-item active" if p == cur else "pgn-item"
            parts.append(f'<span class="{cls}">{p + 1}</span>')
    else:
        cls = "pgn-item active" if cur == 0 else "pgn-item"
        parts.append(f'<span class="{cls}">1</span>')
        if cur > 2:
            parts.append('<span class="pgn-ellipsis">…</span>')
        for p in range(max(1, cur - 1), min(total_pages - 1, cur + 2)):
            cls = "pgn-item active" if p == cur else "pgn-item"
            parts.append(f'<span class="{cls}">{p + 1}</span>')
        if cur < total_pages - 3:
            parts.append('<span class="pgn-ellipsis">…</span>')
        cls = "pgn-item active" if cur == total_pages - 1 else "pgn-item"
        parts.append(f'<span class="{cls}">{total_pages}</span>')

    next_cls = "pgn-arrow disabled" if cur >= total_pages - 1 else "pgn-arrow"
    parts.append(f'<span class="{next_cls}">›</span>')
    st.markdown('<div class="pgn-wrap">' + "".join(parts) + "</div>", unsafe_allow_html=True)

    bc_empty, bc_prev, bc_info, bc_next = st.columns([3, 1, 2, 1])
    with bc_prev:
        if st.button("上一页", key=f"{page_key}_prev", disabled=(cur == 0), width="stretch"):
            st.session_state[page_key] = cur - 1
            st.session_state.reply_selected_idx = 0
            st.rerun()
    with bc_info:
        st.markdown(
            f'<div style="text-align:center;font-size:0.78rem;color:#8B7355;padding-top:7px;">'
            f'{cur + 1} / {total_pages}</div>',
            unsafe_allow_html=True,
        )
    with bc_next:
        if st.button("下一页", key=f"{page_key}_next", disabled=(cur >= total_pages - 1), width="stretch"):
            st.session_state[page_key] = cur + 1
            st.session_state.reply_selected_idx = 0
            st.rerun()

    return cur


def _render_queue(page_items: list[dict], selected_idx: int, total_count: int) -> None:
    st.markdown(
        f"""
        <div class="queue-section-title">
            <p class="queue-title">📋 待处理队列</p>
            <span class="queue-count">共 {total_count} 条</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not page_items:
        st.markdown(
            """
            <div class="owner-empty">
                暂无匹配的回复。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for i, d in enumerate(page_items):
        sev_c = _sev_color(d.get("severity", "low"))
        sev_l = _sev_label(d.get("severity", "low"))
        is_selected = i == selected_idx
        row_class = "qi-row selected" if is_selected else "qi-row"
        raw_review = d.get("original_review", "") or ""
        snippet = _truncate(raw_review, 36)
        review_id = safe_html(str(d.get("review_id", "—")))

        rc1, rc2 = st.columns([10, 1.2], gap="small")
        with rc1:
            st.markdown(
                f"""
                <div class="{row_class}">
                    <span class="qi-id">{review_id}</span>
                    <span class="qi-text">{safe_html(snippet)}</span>
                    <span class="qi-priority" style="color:{sev_c};">● {safe_html(sev_l)}</span>
                    <span class="qi-arrow">›</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with rc2:
            if is_selected:
                st.button("✓", key=f"sel_{d['id']}", width="stretch", type="primary")
            else:
                if st.button("选", key=f"sel_{d['id']}", width="stretch", type="secondary"):
                    st.session_state.reply_selected_idx = i
                    st.rerun()


def _render_publish_checks(safety_status: str, risk_types: list) -> None:
    fg, bg, label, _icon = _safety_display(safety_status)
    is_blocked = safety_status == "blocked"
    is_rewrite = safety_status == "rewrite_required"

    if is_blocked:
        tone_result = ("#C0392B", "#FDEDEC", "需修改")
        promise_result = ("#C0392B", "#FDEDEC", "需检查")
        sensitive_result = ("#C0392B", "#FDEDEC", "需处理")
        platform_result = ("#E67E22", "#FEF5E7", "建议检查")
    elif is_rewrite:
        tone_result = ("#E67E22", "#FEF5E7", "建议优化")
        promise_result = ("#27AE60", "#E8F8F0", "通过")
        sensitive_result = ("#27AE60", "#E8F8F0", "通过")
        platform_result = ("#27AE60", "#E8F8F0", "通过")
    else:
        tone_result = ("#27AE60", "#E8F8F0", "通过")
        promise_result = ("#27AE60", "#E8F8F0", "通过")
        sensitive_result = ("#27AE60", "#E8F8F0", "通过")
        platform_result = ("#27AE60", "#E8F8F0", "通过")

    checks = [
        ("语气礼貌", "适合公开回复", tone_result),
        ("没有过度承诺", "避免承诺无法兑现", promise_result),
        ("没有敏感信息", "不泄露隐私信息", sensitive_result),
        ("符合平台规范", "适合在平台展示", platform_result),
    ]

    st.markdown(
        f'**🛡️ 发布前检查** '
        f'<span style="color:{fg};background:{bg};padding:2px 10px;border-radius:10px;'
        f'font-size:0.72rem;font-weight:600;margin-left:8px;">{safe_html(label)}</span>',
        unsafe_allow_html=True,
    )

    for row_start in range(0, len(checks), 2):
        cols = st.columns(2, gap="small")
        for i, col in enumerate(cols):
            idx = row_start + i
            if idx >= len(checks):
                break
            name, desc, result = checks[idx]
            c, b, l = result
            with col:
                with st.container(border=True):
                    st.markdown(
                        f'**{safe_html(name)}**'
                        f' <span style="color:{c};background:{b};padding:1px 8px;'
                        f'border-radius:8px;font-size:0.68rem;font-weight:600;">{safe_html(l)}</span>',
                        unsafe_allow_html=True,
                    )
                    st.caption(desc)

    if risk_types:
        risk_text = "、".join(str(x) for x in risk_types if str(x).strip())
        if risk_text:
            st.markdown(
                f"""
                <div class="risk-note">
                    需要注意：{safe_html(risk_text)}。建议确认内容无误后再发布。
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_detail(d: dict, page_index: int, total_items: int, reply_svc: ReplyService) -> None:
    safety = d.get("safety_status", "pass")
    status = d.get("approval_status", "pending")
    is_pending = status == "pending"
    draft_id = d["id"]
    key_prefix = f"draft_{draft_id}"
    blocked_safety = safety == "blocked"
    rewrite_safety = safety == "rewrite_required"

    reply_text = d.get("edited_text") or d.get("draft_text", "") or "暂无回复内容"
    original_text = d.get("original_review", "") or "暂无原始评论"
    review_id = safe_html(str(d.get("review_id", "—")))
    platform = safe_html(str(d.get("platform", "—")))
    rating = safe_html(str(d.get("rating", "—")))
    issue = safe_html(str(d.get("issue", "—")))
    review_date = safe_html(str(d.get("review_date", "—")))

    st.markdown(
        f"""
        <div class="detail-card">
            <div class="detail-head">
                <div>
                    <p class="detail-title">💬 系统建议回复 <span style="color:#A09080;font-size:.76rem;">{review_id}</span></p>
                    <div class="detail-subtitle">请确认语气和内容，必要时修改后再发布。</div>
                </div>
                <div class="detail-page">当前：第 {page_index + 1} / {total_items} 条</div>
            </div>
            <div class="suggested-reply">
                <div class="reply-text">{safe_html(reply_text)}</div>
                <div>{_safety_badge_html(safety)}</div>
            </div>
            <div class="label-line">🧾 顾客原评论</div>
            <div class="original-review-box">{safe_html(original_text)}</div>
            <div class="review-meta-row">
                <span>来源：{platform}</span>
                <span>评分：{rating}/5</span>
                <span>问题：{issue}</span>
                <span>时间：{review_date}</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    _render_publish_checks(safety, d.get("risk_types", []))

    if is_pending:
        st.markdown(
            """
            <div class="label-line">✏️ 修改回复内容</div>
            """,
            unsafe_allow_html=True,
        )
        edited = st.text_area(
            "修改回复内容",
            value=reply_text,
            height=132,
            key=f"{key_prefix}_editor",
            label_visibility="collapsed",
            max_chars=500,
        )
        st.caption(f"{len(edited or '')} / 500")
    else:
        final_text = d.get("final_text") or d.get("edited_text") or d.get("draft_text", "")
        fg, bg, label = _approval_display(status)
        st.markdown(
            f"""
            <div class="final-state" style="color:{fg};background:{bg};border:1px solid {bg};">
                {_status_badge_html(status)}<br>
                {safe_html(final_text)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        edited = ""

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    if is_pending:
        bc1, bc2, bc3 = st.columns([2.1, 2.1, 2.1], gap="medium")

        with bc1:
            if st.button(
                "✅ 确认发布",
                key=f"{key_prefix}_approve",
                width="stretch",
                type="primary",
                disabled=blocked_safety,
            ):
                result = reply_svc.approve_draft(draft_id)
                if result["success"]:
                    st.toast("✅ 已确认发布", icon="✅")
                    st.rerun()
                else:
                    st.toast(f"❌ 操作失败：{result.get('error', '')}", icon="❌")

        with bc2:
            if st.button("💾 保存修改", key=f"{key_prefix}_save", width="stretch"):
                if not edited.strip():
                    st.toast("❌ 回复内容不能为空", icon="❌")
                else:
                    result = reply_svc.edit_draft(draft_id, edited.strip())
                    if result["success"]:
                        st.toast("💾 已保存修改", icon="💾")
                        st.rerun()
                    else:
                        st.toast(f"❌ 保存失败：{result.get('error', '')}", icon="❌")

        with bc3:
            with st.popover("❌ 不采用", width="stretch"):
                reason = st.text_area(
                    "不采用原因",
                    placeholder="例如：语气不合适、内容不准确、需要人工重新写…",
                    key=f"{key_prefix}_reason",
                )
                if st.button("确认不采用", key=f"{key_prefix}_reject_confirm"):
                    if not reason.strip():
                        st.toast("请填写不采用原因", icon="⚠️")
                    else:
                        result = reply_svc.reject_draft(draft_id, reason.strip())
                        if result["success"]:
                            st.toast("已标记为不采用", icon="❌")
                            st.rerun()
                        else:
                            st.toast(f"❌ 操作失败：{result.get('error', '')}", icon="❌")

        if blocked_safety:
            st.markdown(
                """
                <div class="risk-note" style="margin-top:12px;color:#C0392B;background:#FDEDEC;border-color:#F5C6C2;">
                    这条回复不建议直接发布。请先修改内容，保存后再确认。
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif rewrite_safety:
            st.markdown(
                """
                <div class="risk-note" style="margin-top:12px;">
                    建议先根据提示修改回复，再确认发布。
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        info_map = {
            "approved": ("#27AE60", "#E8F8F0", "这条回复已确认发布。"),
            "edited": ("#3498DB", "#EBF5FB", "这条回复已保存修改。"),
            "rejected": ("#C0392B", "#FDEDEC", f"这条回复已标记为不采用。原因：{d.get('reject_reason', '未填写')}")
        }
        fg, bg, msg = info_map.get(status, ("#8B7355", "#F5F0E8", "这条回复已处理。"))
        st.markdown(
            f"""
            <div class="final-state" style="color:{fg};background:{bg};">
                {safe_html(msg)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    st.session_state.nav_selection = "回复审核"
    render_sidebar()

    reply_svc = ReplyService()
    batch_id = st.session_state.get("current_batch_id")
    if not batch_id:
        qp_bid = st.query_params.get("batch_id")
        if qp_bid:
            st.session_state.current_batch_id = qp_bid
            batch_id = qp_bid

    if not batch_id:
        st.markdown(
            """
            <div class="owner-empty" style="margin-top:120px;">
                👈 请先到「上传评论」页面上传评论表，并点击「开始分析」。<br>
                分析完成后，系统生成的回复会在这里等待确认。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    try:
        data = _load_reply_review_data(batch_id)
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        return

    drafts: list[dict] = data["drafts"]

    if not drafts:
        _render_page_header(0)
        st.markdown(
            """
            <div class="owner-empty">
                📭 暂无回复草稿。<br>
                可能是这份评论表还没有完成分析，或所有回复都已经处理完了。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if "reply_selected_idx" not in st.session_state:
        st.session_state.reply_selected_idx = 0

    target_draft_id = st.session_state.pop("reply_selected_draft_id", None)
    target_review_id = st.session_state.pop("reply_selected_id", None)
    if target_draft_id or target_review_id:
        for i, d in enumerate(drafts):
            if target_draft_id and d.get("id") == target_draft_id:
                st.session_state.rr_filter = "all"
                st.session_state.rr_queue_page = i // 10
                st.session_state.reply_selected_idx = i % 10
                break
            if target_review_id and d.get("review_id") == target_review_id:
                st.session_state.rr_filter = "all"
                st.session_state.rr_queue_page = i // 10
                st.session_state.reply_selected_idx = i % 10
                break

    pending_n = data["pending_count"]
    _render_page_header(pending_n)
    _render_filters(drafts)

    filtered = _apply_filter(drafts, st.session_state.rr_filter)
    page_size = 10
    queue_key = "rr_queue_page"
    if queue_key not in st.session_state:
        st.session_state[queue_key] = 0

    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    cur_page = st.session_state[queue_key]
    if cur_page >= total_pages:
        st.session_state[queue_key] = 0
        cur_page = 0

    start = cur_page * page_size
    page_items = filtered[start:start + page_size]

    sel_idx = st.session_state.reply_selected_idx
    if sel_idx >= len(page_items):
        sel_idx = 0
        st.session_state.reply_selected_idx = 0

    left, right = st.columns([4.4, 7.6], gap="medium")

    with left:
        _render_queue(page_items, sel_idx, len(filtered))
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        _render_pagination(len(filtered), page_size, queue_key)

    with right:
        if not page_items:
            st.markdown(
                """
                <div class="detail-card">
                    <div class="owner-empty">
                        暂无匹配的回复，请切换上方筛选条件。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            _render_detail(page_items[sel_idx], start + sel_idx, len(filtered), reply_svc)


if __name__ == "__main__":
    main()
