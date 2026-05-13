"""
Reply Review Page — 回复审核：左队列右详情
接入 ReplyService 真实审批（approve / edit / reject）
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
    page_title="小店评论经营助手 · 回复审核",
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
        margin: 16px 0;
    }

    /* ── Queue item row ── */
    .qi-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        border: 1px solid #E8E0D5;
        border-radius: 8px;
        background: #FFFFFF;
        transition: all 0.15s;
    }
    .qi-row.selected {
        border-left: 3px solid #6B4C3B;
        background: #F5F0E8;
    }
    .qi-id {
        font-weight: 700;
        font-size: 0.82rem;
        color: #4A3728;
        min-width: 44px;
    }
    .qi-text {
        flex: 1;
        font-size: 0.82rem;
        color: #6B5B4F;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .qi-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 10px;
        white-space: nowrap;
    }

    /* ── Right detail panel ── */
    .rp-box {
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 14px;
        padding: 24px 24px 20px 24px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .rp-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #8B7355;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .rp-review-box {
        background: #F8F5F0;
        border-radius: 8px;
        padding: 14px;
        font-size: 0.86rem;
        color: #4A3728;
        line-height: 1.7;
    }
    .rp-meta {
        font-size: 0.80rem;
        color: #8B7355;
    }
    .rp-safety-bar {
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 0.80rem;
        font-weight: 600;
    }
    .rp-safety-issue {
        font-size: 0.74rem;
        color: #8B7355;
        padding: 2px 0 2px 16px;
        line-height: 1.6;
    }

    /* ── Inline badge ── */
    .sb {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 12px;
    }

    /* ── Pagination ── */
    .pgn-wrap {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 2px;
    }
    .pgn-item, .pgn-arrow {
        display: inline-block;
        min-width: 28px;
        height: 28px;
        line-height: 27px;
        text-align: center;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 500;
        border: 1px solid #E0D5C5;
        background: #FFFCF8;
        color: #8B7355;
        padding: 0 6px;
    }
    .pgn-item.active {
        background: #3D2C20;
        color: #FAFBF7;
        border-color: #3D2C20;
        font-weight: 700;
    }
    .pgn-arrow.disabled {
        opacity: 0.35;
    }
    .pgn-ellipsis {
        padding: 0 2px;
        color: #C0B0A0;
        font-size: 0.78rem;
    }

    /* ── Action button overrides ── */
    button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background: #27AE60 !important;
        border-color: #27AE60 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background: #219A52 !important;
        border-color: #219A52 !important;
    }

    /* ── Container border ── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #E8E0D5 !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)


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

    # Batch-load review metadata
    with get_connection() as conn:
        placeholders = ",".join(["?" for _ in review_ids])
        reviews = conn.execute(
            f"SELECT review_id, rating, platform FROM reviews "
            f"WHERE batch_id = ? AND review_id IN ({placeholders})",
            [batch_id] + review_ids,
        ).fetchall()
        review_map = {r["review_id"]: dict(r) for r in reviews}

        analysis_rows = conn.execute(
            f"SELECT review_id, severity, primary_topic FROM review_analysis "
            f"WHERE batch_id = ? AND review_id IN ({placeholders})",
            [batch_id] + review_ids,
        ).fetchall()
        analysis_map = {a["review_id"]: dict(a) for a in analysis_rows}

    # Enrich drafts
    for d in drafts:
        rm = review_map.get(d["review_id"], {})
        am = analysis_map.get(d["review_id"], {})
        d["rating"] = rm.get("rating", "")
        d["platform"] = rm.get("platform", "—")
        sev_num = am.get("severity", 2)
        if sev_num >= 4:
            d["severity"] = "high"
        elif sev_num >= 3:
            d["severity"] = "medium"
        else:
            d["severity"] = "low"
        d["issue"] = TOPIC_CN_MAP.get(am.get("primary_topic", ""), am.get("primary_topic", "—"))
        # Ensure risk_types is a list
        if isinstance(d.get("risk_types"), str):
            import json
            try:
                d["risk_types"] = json.loads(d["risk_types"])
            except Exception:
                d["risk_types"] = []
        if d.get("risk_types") is None:
            d["risk_types"] = []

    pending_count = sum(1 for d in drafts if d["approval_status"] == "pending")
    blocked_count = sum(1 for d in drafts if d["safety_status"] == "blocked" and d["approval_status"] == "pending")
    rewrite_count = sum(1 for d in drafts if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending")

    return {
        "drafts": drafts,
        "pending_count": pending_count,
        "blocked_count": blocked_count,
        "rewrite_count": rewrite_count,
    }




# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _sev_color(severity: str) -> str:
    return {"high": "#C0392B", "medium": "#E67E22", "low": "#27AE60"}.get(severity, "#8B7355")

def _sev_label(severity: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(severity, severity)

def _safety_badge(status: str) -> str:
    cfg = {
        "pass": ("#27AE60", "#E8F8F0", "✓ 安全"),
        "rewrite_required": ("#E67E22", "#FEF5E7", "⚠ 需修改"),
        "blocked": ("#C0392B", "#FDEDEC", "✗ 已拦截"),
    }
    c, bg, label = cfg.get(status, ("#8B7355", "#F5F0E8", status))
    return f'<span class="sb" style="color:{c};background:{bg};">{label}</span>'

def _status_badge(status: str) -> str:
    cfg = {
        "pending": ("#E67E22", "#FEF5E7", "⏳ 待审核"),
        "approved": ("#27AE60", "#E8F8F0", "✓ 已批准"),
        "edited": ("#3498DB", "#EBF5FB", "📝 已编辑"),
        "rejected": ("#C0392B", "#FDEDEC", "✗ 已驳回"),
    }
    c, bg, label = cfg.get(status, ("#8B7355", "#F5F0E8", status))
    return f'<span class="sb" style="color:{c};background:{bg};">{label}</span>'


# ═══════════════════════════════════════════════════════════════════════════
# Filter
# ═══════════════════════════════════════════════════════════════════════════

def _apply_filter(drafts: list[dict], filter_key: str) -> list[dict]:
    if filter_key == "pending":
        return [d for d in drafts if d["approval_status"] == "pending"]
    elif filter_key == "rewrite":
        return [d for d in drafts if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending"]
    elif filter_key == "blocked":
        return [d for d in drafts if d["safety_status"] == "blocked" and d["approval_status"] == "pending"]
    elif filter_key == "processed":
        return [d for d in drafts if d["approval_status"] != "pending"]
    # "all" — sort by priority
    priority = {"pending": 0, "rewrite_required": 1, "blocked": 2}
    return sorted(drafts, key=lambda d: (
        priority.get(
            "pending" if d["approval_status"] == "pending" and d["safety_status"] not in ("rewrite_required", "blocked")
            else "rewrite_required" if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending"
            else "blocked" if d["safety_status"] == "blocked"
            else "processed", 99
        )
    ))


# ═══════════════════════════════════════════════════════════════════════════
# Pagination
# ═══════════════════════════════════════════════════════════════════════════

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

    html = '<div class="pgn-wrap">' + "".join(parts) + "</div>"
    st.markdown(html, unsafe_allow_html=True)

    bc_empty, bc_prev, bc_info, bc_next = st.columns([3, 1, 2, 1])
    with bc_prev:
        if st.button("◀", key=f"{page_key}_prev", disabled=(cur == 0),
                     width='stretch'):
            st.session_state[page_key] = cur - 1
            st.session_state.reply_selected_idx = 0
            st.rerun()
    with bc_info:
        st.markdown(
            f'<div style="text-align:center;font-size:0.78rem;color:#8B7355;padding-top:4px;">'
            f'{cur + 1} / {total_pages}</div>',
            unsafe_allow_html=True,
        )
    with bc_next:
        if st.button("▶", key=f"{page_key}_next", disabled=(cur >= total_pages - 1),
                     width='stretch'):
            st.session_state[page_key] = cur + 1
            st.session_state.reply_selected_idx = 0
            st.rerun()

    return cur


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

    # ── No batch ──
    if not batch_id:
        st.markdown("""
        <div style="text-align:center;padding-top:120px;color:#A09080;">
            <p style="font-size:1.1rem;">👈 请先在 <strong>「上传评论」</strong> 页面中上传 CSV 或开启 Demo Mode 并运行分析</p>
            <p style="font-size:0.82rem;">分析完成后，回复草稿将在此页面等待审核</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Load data ──
    try:
        data = _load_reply_review_data(batch_id)
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        return

    drafts: list[dict] = data["drafts"]

    # ── Empty state ──
    if not drafts:
        st.markdown("""
        <div style="text-align:center;padding-top:80px;color:#A09080;">
            <p style="font-size:1.1rem;">📭 暂无回复草稿</p>
            <p style="font-size:0.82rem;">该批次可能尚未完成分析，或所有草稿已处理完毕</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if "reply_selected_idx" not in st.session_state:
        st.session_state.reply_selected_idx = 0

    pending_n = data["pending_count"]
    blocked_n = data["blocked_count"]
    rewrite_n = data["rewrite_count"]

    # ── Title bar ──
    st.markdown(f"""<div style="margin-bottom:4px;">
<h1 style="font-size:1.55rem;font-weight:700;color:#3D2C20;margin:0 0 2px 0;">
✏️ 回复审核
<span style="display:inline-block;background:#FFF3EB;color:#C0392B;font-weight:700;
font-size:0.82rem;padding:2px 12px;border-radius:12px;margin-left:8px;">
{pending_n} 待审
</span>
</h1>
<p style="font-size:0.86rem;color:#8B7355;margin:0;">
审核 AI 生成的差评回复草稿 · 安全检查 · 批准 / 编辑 / 驳回
</p>
</div>""", unsafe_allow_html=True)

    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)

    # ── Filter pills ──
    if "rr_filter" not in st.session_state:
        st.session_state.rr_filter = "all"

    filters = [
        ("all", "全部"),
        ("pending", "⏳ 待审核"),
        ("rewrite", "⚠ 需修改"),
        ("blocked", "🚫 已拦截"),
        ("processed", "✅ 已处理"),
    ]
    fc = st.columns(len(filters), gap="small")
    for i, (key, label) in enumerate(filters):
        with fc[i]:
            active = st.session_state.rr_filter == key
            if st.button(label, key=f"filter_{key}", width='stretch',
                        type="primary" if active else "secondary"):
                st.session_state.rr_filter = key
                st.session_state.rr_queue_page = 0
                st.session_state.reply_selected_idx = 0
                st.rerun()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Filter + paginate ──
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

    # ═══════════════════════════════════════════════════════
    # Two-column layout
    # ═══════════════════════════════════════════════════════
    left, right = st.columns([5, 7], gap="medium")

    # ═══════ LEFT: queue ═══════
    with left:
        st.markdown(
            f'<p style="font-weight:700;color:#4A3728;font-size:0.95rem;margin:0 0 10px 0;">'
            f'📋 待处理队列 · {len(filtered)} 条</p>',
            unsafe_allow_html=True,
        )

        if not page_items:
            st.info("暂无匹配的草稿")
        else:
            for i, d in enumerate(page_items):
                sev_c = _sev_color(d.get("severity", "low"))
                sev_l = _sev_label(d.get("severity", "low"))
                safety = d.get("safety_status", "pass")

                sbadge_map = {
                    "pass": ("#27AE60", "#E8F8F0", "✓"),
                    "rewrite_required": ("#E67E22", "#FEF5E7", "⚠"),
                    "blocked": ("#C0392B", "#FDEDEC", "✗"),
                }
                sb_c, sb_bg, sb_label = sbadge_map.get(safety, ("#8B7355", "#F5F0E8", "?"))

                is_selected = i == sel_idx
                row_class = "qi-row selected" if is_selected else "qi-row"
                raw_review = d.get("original_review", "") or ""
                snippet = raw_review[:30] + ("…" if len(raw_review) > 30 else "")

                rc1, rc2 = st.columns([9, 1], gap="small")
                with rc1:
                    qi_md = f"""<div class="{row_class}">
<span class="qi-id">{safe_html(d['review_id'])}</span>
<span class="qi-text">{safe_html(snippet)}</span>
<span style="font-weight:600;font-size:0.76rem;color:{sev_c};">● {sev_l}</span>
<span class="qi-badge" style="color:{sb_c};background:{sb_bg};">{sb_label}</span>
</div>"""
                    st.markdown(qi_md, unsafe_allow_html=True)
                with rc2:
                    if is_selected:
                        st.button("✓", key=f"sel_{d['id']}",
                                  width='stretch', type="primary")
                    else:
                        if st.button("›", key=f"sel_{d['id']}",
                                    width='stretch', type="secondary"):
                            st.session_state.reply_selected_idx = i
                            st.rerun()

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            _render_pagination(len(filtered), page_size, queue_key)

    # ═══════ RIGHT: detail + actions ═══════
    with right:
        if not page_items:
            st.markdown("""
            <div class="rp-box" style="text-align:center;padding-top:80px;color:#A09080;">
                <p style="font-size:1.1rem;">👈 请从左侧队列选择一条评论</p>
                <p style="font-size:0.82rem;">选中后此处显示 AI 回复草稿与操作按钮</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            d = page_items[sel_idx]
            safety = d.get("safety_status", "pass")
            status = d.get("approval_status", "pending")
            is_pending = status == "pending"
            draft_id = d["id"]
            key_prefix = f"draft_{draft_id}"

            sc_cfg = {
                "pass": ("#27AE60", "#E8F8F0", "🛡️ 安全检查通过"),
                "rewrite_required": ("#E67E22", "#FEF5E7", "🛡️ 安全检查：建议修改"),
                "blocked": ("#C0392B", "#FDEDEC", "🛡️ 安全检查：已拦截"),
            }
            sc_c, sc_bg, sc_label = sc_cfg.get(safety, ("#8B7355", "#F5F0E8", safety))

            issues_html = ""
            for issue in d.get("risk_types", []):
                issues_html += f'<div class="rp-safety-issue">· {safe_html(issue)}</div>'

            original_text = safe_html(d.get("original_review", "") or "")

            st.markdown(f"""<div class="rp-box">
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
<div>
<span style="font-weight:700;font-size:0.95rem;color:#4A3728;">💬 AI 回复草稿</span>
<span style="font-size:0.78rem;color:#A09080;margin-left:6px;">← {safe_html(d['review_id'])}</span>
</div>
<div style="display:flex;gap:8px;">
{_safety_badge(safety)}
{_status_badge(status)}
</div>
</div>
<div class="rp-label">📝 原始评论</div>
<div class="rp-review-box">{original_text}</div>
<div style="margin-top:6px;">
<span class="rp-meta">📱 {safe_html(d.get('platform', '—'))}</span>
<span class="rp-meta" style="margin-left:12px;">⭐ {safe_html(d.get('rating', '—'))}/5</span>
<span class="rp-meta" style="margin-left:12px;">🏷 {safe_html(d.get('issue', '—'))}</span>
</div>
<div style="margin-top:14px;">
<div class="rp-safety-bar" style="background:{sc_bg};color:{sc_c};">{sc_label}</div>
</div>
{issues_html}
</div>""", unsafe_allow_html=True)

            # ── Editable reply ──
            if is_pending:
                st.markdown(
                    '<p style="font-weight:600;color:#4A3728;font-size:0.88rem;margin:14px 0 4px 0;">'
                    '✏️ 编辑回复内容</p>',
                    unsafe_allow_html=True,
                )
                current_text = d.get("edited_text") or d.get("draft_text", "")
                edited = st.text_area(
                    "编辑回复",
                    value=current_text,
                    height=120,
                    key=f"{key_prefix}_editor",
                    label_visibility="collapsed",
                )
            else:
                st.markdown(
                    f'<div style="background:#F8F5F0;border-radius:8px;padding:14px;'
                    f'font-size:0.86rem;color:#4A3728;line-height:1.7;margin-top:14px;">'
                    f'{d.get("final_text") or d.get("draft_text", "")}</div>',
                    unsafe_allow_html=True,
                )
                edited = ""

            # ── Action buttons ──
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            if is_pending:
                blocked_safety = safety == "blocked"
                rewrite_safety = safety == "rewrite_required"

                bc1, bc2, bc3, bc4 = st.columns([2, 2, 2, 3])

                with bc1:
                    if st.button(
                        "✅ 批准发布",
                        key=f"{key_prefix}_approve",
                        width='stretch',
                        type="primary",
                        disabled=blocked_safety,
                    ):
                        result = reply_svc.approve_draft(draft_id)
                        if result["success"]:
                            st.toast("✅ 已批准", icon="✅")
                            st.rerun()
                        else:
                            st.toast(f"❌ 批准失败：{result.get('error', '')}", icon="❌")

                with bc2:
                    if st.button(
                        "📝 保存修改",
                        key=f"{key_prefix}_save",
                        width='stretch',
                    ):
                        if not edited.strip():
                            st.toast("❌ 回复内容不能为空", icon="❌")
                        else:
                            result = reply_svc.edit_draft(draft_id, edited.strip())
                            if result["success"]:
                                st.toast("📝 已保存", icon="📝")
                                st.rerun()
                            else:
                                st.toast(f"❌ 保存失败：{result.get('error', '')}", icon="❌")

                with bc3:
                    with st.popover("❌ 驳回", width='stretch'):
                        reason = st.text_area(
                            "驳回原因", placeholder="请输入驳回原因…",
                            key=f"{key_prefix}_reason",
                        )
                        if st.button("确认驳回", key=f"{key_prefix}_reject_confirm"):
                            if not reason.strip():
                                st.toast("❌ 请输入驳回原因", icon="❌")
                            else:
                                result = reply_svc.reject_draft(draft_id, reason.strip())
                                if result["success"]:
                                    st.toast("❌ 已驳回", icon="❌")
                                    st.rerun()
                                else:
                                    st.toast(f"❌ 驳回失败：{result.get('error', '')}", icon="❌")

                with bc4:
                    if blocked_safety:
                        st.markdown(
                            '<span style="color:#C0392B;font-size:0.82rem;font-weight:600;">'
                            '🚫 内容已拦截，请修改后重新提交</span>',
                            unsafe_allow_html=True,
                        )
                    elif rewrite_safety:
                        st.markdown(
                            '<span style="color:#E67E22;font-size:0.82rem;font-weight:600;">'
                            '⚠️ 建议按安全检查意见修改后再批准</span>',
                            unsafe_allow_html=True,
                        )
            else:
                st_info = {
                    "approved": ("#27AE60", "✅ 此回复已批准发布"),
                    "edited": ("#3498DB", "📝 此回复已编辑保存"),
                    "rejected": ("#C0392B", f"✗ 已驳回 — {d.get('reject_reason', '未提供原因')}"),
                }
                c, msg = st_info.get(status, ("#8B7355", "状态未知"))
                st.markdown(
                    f'<div style="padding:8px 0;color:{c};font-weight:600;font-size:0.86rem;">{msg}</div>',
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
