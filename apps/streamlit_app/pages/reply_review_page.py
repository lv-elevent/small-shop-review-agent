"""
Reply Review Page — 回复审核：左队列右详情，参照 UI mockup (Reply Review页.png)
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

    /* ── Action button overrides ──
       Green: approve button, selected filter, selected queue item
       Red: blocked items (via safety bar + badge, not buttons) */
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
# Demo Data
# ═══════════════════════════════════════════════════════════════════════════

def _init_demo_data() -> None:
    if "reply_review_init" in st.session_state:
        return

    drafts = [
        {"draft_id":"DR001","review_id":"D002","review_text":"等了快40分钟才上菜，太慢了","rating":1,
         "customer_name":"用户A","platform":"美团","issue":"出餐速度慢","severity":"high",
         "reply_draft":"亲爱的顾客，非常抱歉让您久等了。我们深知等餐时间过长会严重影响用餐体验。我们已经注意到高峰期出餐速度的问题，正在优化厨房流程和增加备餐人手。希望您能再给我们一次机会，下次来店我们将为您优先服务。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR002","review_id":"D003","review_text":"服务员态度冷淡，爱答不理","rating":2,
         "customer_name":"用户B","platform":"大众点评","issue":"服务态度差","severity":"high",
         "reply_draft":"感谢您的反馈，我们非常重视您的意见。关于服务员态度的问题，我们已经进行了内部调查和批评教育。我们将加强员工服务培训，确保每位顾客都能感受到温暖和尊重。再次为不佳的体验向您道歉。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR003","review_id":"D005","review_text":"桌面油腻腻的，卫生堪忧","rating":1,
         "customer_name":"用户C","platform":"美团","issue":"环境卫生问题","severity":"medium",
         "reply_draft":"非常抱歉给您带来不好的体验。我们已经立即安排了对用餐区域的深度清洁，并制定了每2小时的巡检制度。卫生是我们最基本的责任，感谢您的监督。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR004","review_id":"D007","review_text":"等了20分钟被告知卖完了","rating":1,
         "customer_name":"用户D","platform":"小红书","issue":"出餐速度慢","severity":"high",
         "reply_draft":"非常抱歉给您带来不好的体验！我们已经改进了库存管理和菜单提示系统，确保不会再出现类似情况。您下次光临时，我们愿意为您免费提供一份甜品作为补偿。",
         "safety_status":"rewrite_required","safety_issues":["避免承诺免费补偿 — 建议改为'我们将为您准备一份小惊喜'"],
         "approval_status":"pending","edit_text":""},
        {"draft_id":"DR005","review_id":"D009","review_text":"服务员上错菜还不承认","rating":1,
         "customer_name":"用户E","platform":"大众点评","issue":"服务态度差","severity":"high",
         "reply_draft":"感谢指出问题，我们已经对当事员工进行了严肃批评并处以罚款。我们会加强员工责任心培训，杜绝此类事件再次发生。欢迎您再次光临监督。",
         "safety_status":"blocked",
         "safety_issues":["禁止公开声明处罚员工 — 违规透露内部人事信息","建议改为'我们已内部严肃处理，将加强员工培训'"],
         "approval_status":"pending","edit_text":""},
        {"draft_id":"DR006","review_id":"D011","review_text":"音乐太大声，影响聊天","rating":2,
         "customer_name":"用户F","platform":"美团","issue":"环境卫生问题","severity":"medium",
         "reply_draft":"谢谢您的建议！我们已经调整了店内背景音乐的音量，并在不同时段设置了不同的音量标准。希望下次您来的时候能享受到更舒适的氛围。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR007","review_id":"D012","review_text":"周末高峰期完全没人管排队","rating":1,
         "customer_name":"用户G","platform":"小红书","issue":"出餐速度慢","severity":"high",
         "reply_draft":"非常抱歉！我们已经意识到周末高峰期的排队管理问题，正在引入取号系统和等位区优化方案。预计下周末前完成改进。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR008","review_id":"D014","review_text":"卫生间不太干净","rating":2,
         "customer_name":"用户H","platform":"美团","issue":"环境卫生问题","severity":"medium",
         "reply_draft":"感谢您的提醒，我们已经立即安排保洁人员对卫生间进行了彻底清洁，并增加了清洁频次。卫生问题我们绝不姑息，欢迎您随时监督。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR009","review_id":"D017","review_text":"结账时多收了一杯咖啡的钱","rating":1,
         "customer_name":"用户I","platform":"大众点评","issue":"服务态度差","severity":"high",
         "reply_draft":"非常抱歉出现这样的错误！我们已经核查了当天的账单并进行了退款处理。针对收银流程，我们增加了双人复核制度。感谢您的理解。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR010","review_id":"D020","review_text":"收银员边玩手机边结账","rating":2,
         "customer_name":"用户J","platform":"美团","issue":"服务态度差","severity":"medium",
         "reply_draft":"感谢您的反馈。我们已对当事员工进行了批评教育，并重申了工作期间禁止使用手机的规定。我们将通过定期巡查确保服务规范。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR011","review_id":"D025","review_text":"高峰期只有一个人做咖啡","rating":1,
         "customer_name":"用户K","platform":"小红书","issue":"出餐速度慢","severity":"high",
         "reply_draft":"感谢您的反馈，我们已经调整了员工排班方案，确保高峰期至少有2名咖啡师在岗。同时我们也在优化出餐流程以提高效率。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
        {"draft_id":"DR012","review_id":"D031","review_text":"冰美式寡淡无味","rating":2,
         "customer_name":"用户L","platform":"美团","issue":"口味不稳定","severity":"medium",
         "reply_draft":"感谢您的反馈，我们已经检查了咖啡机的萃取参数和咖啡豆的新鲜度。如果方便的话，下次来店时请告知我们的咖啡师您的口味偏好，我们很乐意为您调整浓度。",
         "safety_status":"pass","safety_issues":[],"approval_status":"pending","edit_text":""},
    ]

    for d in drafts:
        d["edit_text"] = d["reply_draft"]

    st.session_state.reply_drafts = drafts
    st.session_state.reply_selected_idx = 0
    st.session_state.reply_review_init = True


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
    priority = {"pending": 0, "rewrite_required": 1, "blocked": 2}
    return sorted(drafts, key=lambda d: (
        priority.get(
            "pending" if d["approval_status"] == "pending" and d["safety_status"] not in ("rewrite_required","blocked")
            else "rewrite_required" if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending"
            else "blocked" if d["safety_status"] == "blocked"
            else "processed", 99
        )
    ))


# ═══════════════════════════════════════════════════════════════════════════
# Pagination — compact, right-aligned, bottom only
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

    # Visual pagination HTML
    parts: list[str] = []

    # Prev arrow
    prev_cls = "pgn-arrow disabled" if cur == 0 else "pgn-arrow"
    parts.append(f'<span class="{prev_cls}">‹</span>')

    # Page numbers
    if total_pages <= 7:
        for p in range(total_pages):
            cls = "pgn-item active" if p == cur else "pgn-item"
            parts.append(f'<span class="{cls}">{p + 1}</span>')
    else:
        # First page
        cls = "pgn-item active" if cur == 0 else "pgn-item"
        parts.append(f'<span class="{cls}">1</span>')

        if cur > 2:
            parts.append('<span class="pgn-ellipsis">…</span>')

        # Pages around current
        for p in range(max(1, cur - 1), min(total_pages - 1, cur + 2)):
            cls = "pgn-item active" if p == cur else "pgn-item"
            parts.append(f'<span class="{cls}">{p + 1}</span>')

        if cur < total_pages - 3:
            parts.append('<span class="pgn-ellipsis">…</span>')

        # Last page
        cls = "pgn-item active" if cur == total_pages - 1 else "pgn-item"
        parts.append(f'<span class="{cls}">{total_pages}</span>')

    # Next arrow
    next_cls = "pgn-arrow disabled" if cur >= total_pages - 1 else "pgn-arrow"
    parts.append(f'<span class="{next_cls}">›</span>')

    html = '<div class="pgn-wrap">' + "".join(parts) + "</div>"
    st.markdown(html, unsafe_allow_html=True)

    # Functional prev/next buttons (compact, right-aligned)
    bc_empty, bc_prev, bc_info, bc_next = st.columns([3, 1, 2, 1])
    with bc_prev:
        if st.button("◀", key=f"{page_key}_prev", disabled=(cur == 0),
                     use_container_width=True):
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
                     use_container_width=True):
            st.session_state[page_key] = cur + 1
            st.session_state.reply_selected_idx = 0
            st.rerun()

    return cur


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    _init_demo_data()
    st.session_state.nav_selection = "回复审核"
    render_sidebar()

    drafts: list[dict] = st.session_state.reply_drafts

    if "reply_selected_idx" not in st.session_state:
        st.session_state.reply_selected_idx = 0

    # ── Stats ──
    pending_n = sum(1 for d in drafts if d["approval_status"] == "pending")
    blocked_n = sum(1 for d in drafts if d["safety_status"] == "blocked" and d["approval_status"] == "pending")
    rewrite_n = sum(1 for d in drafts if d["safety_status"] == "rewrite_required" and d["approval_status"] == "pending")

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
            if st.button(label, key=f"filter_{key}", use_container_width=True,
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
    # Main two-column layout
    # ═══════════════════════════════════════════════════════
    left, right = st.columns([5, 7], gap="medium")

    # ══════════════ LEFT: 待处理队列 ══════════════
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
                snippet = d["review_text"][:30] + ("…" if len(d["review_text"]) > 30 else "")

                # Row: display (90%) + compact select button (10%)
                rc1, rc2 = st.columns([9, 1], gap="small")
                with rc1:
                    qi_md = f"""<div class="{row_class}">
<span class="qi-id">{d['review_id']}</span>
<span class="qi-text">{snippet}</span>
<span style="font-weight:600;font-size:0.76rem;color:{sev_c};">● {sev_l}</span>
<span class="qi-badge" style="color:{sb_c};background:{sb_bg};">{sb_label}</span>
</div>"""
                    st.markdown(qi_md, unsafe_allow_html=True)
                with rc2:
                    if is_selected:
                        st.button("✓", key=f"sel_{d['draft_id']}",
                                  use_container_width=True, type="primary")
                    else:
                        if st.button("›", key=f"sel_{d['draft_id']}",
                                    use_container_width=True, type="secondary"):
                            st.session_state.reply_selected_idx = i
                            st.rerun()

            # Pagination at bottom of queue
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            _render_pagination(len(filtered), page_size, queue_key)

    # ══════════════ RIGHT: AI 回复草稿 ══════════════
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
            key_prefix = f"draft_{d['draft_id']}"

            # ── Render the fixed right panel ──
            sc_cfg = {
                "pass": ("#27AE60", "#E8F8F0", "🛡️ 安全检查通过"),
                "rewrite_required": ("#E67E22", "#FEF5E7", "🛡️ 安全检查：建议修改"),
                "blocked": ("#C0392B", "#FDEDEC", "🛡️ 安全检查：已拦截"),
            }
            sc_c, sc_bg, sc_label = sc_cfg.get(safety, ("#8B7355", "#F5F0E8", safety))

            # Build safety issues HTML inline
            issues_html = ""
            for issue in d.get("safety_issues", []):
                issues_html += f'<div class="rp-safety-issue">· {issue}</div>'

            # Panel header + review + safety (single markdown call to keep DOM intact)
            st.markdown(f"""<div class="rp-box">
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
<div>
<span style="font-weight:700;font-size:0.95rem;color:#4A3728;">💬 AI 回复草稿</span>
<span style="font-size:0.78rem;color:#A09080;margin-left:6px;">← {d['review_id']}</span>
</div>
<div style="display:flex;gap:8px;">
{_safety_badge(safety)}
{_status_badge(status)}
</div>
</div>
<div class="rp-label">📝 原始评论</div>
<div class="rp-review-box">{d['review_text']}</div>
<div style="margin-top:6px;">
<span class="rp-meta">👤 {d['customer_name']}</span>
<span class="rp-meta" style="margin-left:12px;">📱 {d['platform']}</span>
<span class="rp-meta" style="margin-left:12px;">⭐ {d['rating']}/5</span>
<span class="rp-meta" style="margin-left:12px;">🏷 {d['issue']}</span>
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
                edited = st.text_area(
                    "编辑回复",
                    value=d["edit_text"],
                    height=120,
                    key=f"{key_prefix}_editor",
                    label_visibility="collapsed",
                )
                if edited != d["edit_text"]:
                    d["edit_text"] = edited
            else:
                st.markdown(
                    f'<div style="background:#F8F5F0;border-radius:8px;padding:14px;'
                    f'font-size:0.86rem;color:#4A3728;line-height:1.7;margin-top:14px;">'
                    f'{d["reply_draft"]}</div>',
                    unsafe_allow_html=True,
                )

            # ── Action buttons ──
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            if is_pending:
                blocked_safety = safety == "blocked"
                rewrite_safety = safety == "rewrite_required"

                bc1, bc2, bc3, bc4 = st.columns([2, 2, 2, 3])

                with bc1:
                    approve_clicked = st.button(
                        "✅ 批准发布",
                        key=f"{key_prefix}_approve",
                        use_container_width=True,
                        type="primary",
                        disabled=blocked_safety,
                    )
                    if approve_clicked:
                        d["approval_status"] = "approved"
                        d["reply_draft"] = d["edit_text"]
                        st.toast("✅ 已批准", icon="✅")
                        st.rerun()

                with bc2:
                    save_clicked = st.button(
                        "📝 保存修改",
                        key=f"{key_prefix}_save",
                        use_container_width=True,
                    )
                    if save_clicked:
                        d["approval_status"] = "edited"
                        d["reply_draft"] = d["edit_text"]
                        st.toast("📝 已保存", icon="📝")
                        st.rerun()

                with bc3:
                    with st.popover("✗ 驳回", use_container_width=True):
                        reason = st.text_area(
                            "驳回原因", placeholder="请输入驳回原因…",
                            key=f"{key_prefix}_reason",
                        )
                        if st.button("确认驳回", key=f"{key_prefix}_reject_confirm",
                                    disabled=not reason.strip()):
                            d["approval_status"] = "rejected"
                            d["reject_reason"] = reason.strip()
                            st.toast("✗ 已驳回", icon="✗")
                            st.rerun()

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
