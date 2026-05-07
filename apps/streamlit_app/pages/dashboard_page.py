"""
Dashboard Page — 数据看板：评论概览、三大问题、Harness 状态、审核队列
参照示例图布局：指标卡 → 左(三大问题) + 右(Harness + 审核队列纵向堆叠)
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

    /* ── Queue row (inside table-like HTML) ── */
    .q-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 3px 10px;
        border-bottom: 1px solid #F5F0E8;
        font-size: 0.76rem;
    }
    .q-item:last-child { border-bottom: none; }
    .q-id { font-weight: 600; color: #4A3728; min-width: 40px; }
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


# ═══════════════════════════════════════════════════════════════════════════
# Demo Data
# ═══════════════════════════════════════════════════════════════════════════

def _init_demo_data() -> None:
    if "dashboard_initialized" in st.session_state:
        return

    reviews = [
        {"review_id":"D001","review_text":"咖啡味道不错，环境也好","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D002","review_text":"等了快40分钟才上菜，太慢了","rating":1,"category":"出餐速度","sentiment":"negative","issue":"出餐速度慢","severity":"high","reply_draft":"非常抱歉让您久等了...","reviewed":False,"approved":False},
        {"review_id":"D003","review_text":"服务员态度冷淡，爱答不理","rating":2,"category":"服务","sentiment":"negative","issue":"服务态度差","severity":"high","reply_draft":"感谢您的反馈，我们会加强培训...","reviewed":False,"approved":False},
        {"review_id":"D004","review_text":"挺好的，会再来","rating":4,"category":"综合","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D005","review_text":"桌面油腻腻的，卫生堪忧","rating":1,"category":"环境","sentiment":"negative","issue":"环境卫生问题","severity":"medium","reply_draft":"非常抱歉，我们马上整改...","reviewed":False,"approved":False},
        {"review_id":"D006","review_text":"拿铁拉花很漂亮","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D007","review_text":"等了20分钟被告知卖完了","rating":1,"category":"出餐速度","sentiment":"negative","issue":"出餐速度慢","severity":"high","reply_draft":"非常抱歉给您带来不好体验...","reviewed":False,"approved":False},
        {"review_id":"D008","review_text":"价格实惠，性价比高","rating":4,"category":"价格","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D009","review_text":"服务员上错菜还不承认","rating":1,"category":"服务","sentiment":"negative","issue":"服务态度差","severity":"high","reply_draft":"感谢指出，我们已严肃处理...","reviewed":False,"approved":False},
        {"review_id":"D010","review_text":"甜品不错，适合下午茶","rating":4,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D011","review_text":"音乐太大声，影响聊天","rating":2,"category":"环境","sentiment":"negative","issue":"环境卫生问题","severity":"medium","reply_draft":"谢谢建议，我们会调整音量...","reviewed":False,"approved":False},
        {"review_id":"D012","review_text":"周末高峰期完全没人管排队","rating":1,"category":"出餐速度","sentiment":"negative","issue":"出餐速度慢","severity":"high","reply_draft":"非常抱歉，我们将优化排队管理...","reviewed":False,"approved":False},
        {"review_id":"D013","review_text":"红茶拿铁绝了！","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D014","review_text":"卫生间不太干净","rating":2,"category":"环境","sentiment":"negative","issue":"环境卫生问题","severity":"medium","reply_draft":"感谢提醒，已安排加强清洁...","reviewed":False,"approved":False},
        {"review_id":"D015","review_text":"旁边那桌孩子吵闹也没人管","rating":2,"category":"环境","sentiment":"negative","issue":"环境卫生问题","severity":"low","reply_draft":"感谢反馈，我们会注意用餐秩序...","reviewed":False,"approved":False},
        {"review_id":"D016","review_text":"面包新鲜出炉，太香了","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D017","review_text":"结账时多收了一杯咖啡的钱","rating":1,"category":"服务","sentiment":"negative","issue":"服务态度差","severity":"high","reply_draft":"非常抱歉，我们立即核查退款...","reviewed":False,"approved":False},
        {"review_id":"D018","review_text":"出餐等了25分钟，催了三次","rating":1,"category":"出餐速度","sentiment":"negative","issue":"出餐速度慢","severity":"high","reply_draft":"非常抱歉，我们正优化出餐流程...","reviewed":False,"approved":False},
        {"review_id":"D019","review_text":"很适合办公，WiFi很稳定","rating":4,"category":"环境","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D020","review_text":"收银员边玩手机边结账","rating":2,"category":"服务","sentiment":"negative","issue":"服务态度差","severity":"medium","reply_draft":"感谢反馈，已对员工进行批评教育...","reviewed":False,"approved":False},
        {"review_id":"D021","review_text":"桂花拿铁很好喝","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D022","review_text":"和朋友聊聊天感觉不错","rating":4,"category":"综合","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D023","review_text":"点单时态度特别不耐烦","rating":2,"category":"服务","sentiment":"negative","issue":"服务态度差","severity":"medium","reply_draft":"非常抱歉，我们已批评当事员工...","reviewed":False,"approved":False},
        {"review_id":"D024","review_text":"口味一如既往地好","rating":4,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D025","review_text":"高峰期只有一个人做咖啡","rating":1,"category":"出餐速度","sentiment":"negative","issue":"出餐速度慢","severity":"high","reply_draft":"感谢反馈，我们将调整排班...","reviewed":False,"approved":False},
        {"review_id":"D026","review_text":"舒芙蕾入口即化","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D027","review_text":"咖啡豆品质不错","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D028","review_text":"店里装修很有格调","rating":4,"category":"环境","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D029","review_text":"外卖打包得很用心","rating":4,"category":"服务","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D030","review_text":"位置好找，停车方便","rating":4,"category":"综合","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D031","review_text":"冰美式寡淡无味","rating":2,"category":"口味","sentiment":"negative","issue":"口味不稳定","severity":"medium","reply_draft":"感谢反馈，我们会检查出品标准...","reviewed":False,"approved":False},
        {"review_id":"D032","review_text":"提拉米苏太甜了","rating":3,"category":"口味","sentiment":"neutral","issue":"口味不稳定","severity":"low","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D033","review_text":"店员很热情，推荐了新品","rating":5,"category":"服务","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D034","review_text":"地板上有食物残渣没扫","rating":2,"category":"环境","sentiment":"negative","issue":"环境卫生问题","severity":"medium","reply_draft":"感谢提醒，已安排打扫...","reviewed":False,"approved":False},
        {"review_id":"D035","review_text":"每次都来这里，习惯了","rating":4,"category":"综合","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D036","review_text":"等了15分钟，咖啡还没上","rating":2,"category":"出餐速度","sentiment":"negative","issue":"出餐速度慢","severity":"high","reply_draft":"非常抱歉，我们会改善...","reviewed":False,"approved":False},
        {"review_id":"D037","review_text":"牛角包酥脆掉渣，好吃","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D038","review_text":"WiFi密码没贴出来，不方便","rating":3,"category":"服务","sentiment":"neutral","issue":"服务细节不足","severity":"low","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D039","review_text":"老板人很nice","rating":5,"category":"服务","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D040","review_text":"插座太少，充电不方便","rating":3,"category":"环境","sentiment":"neutral","issue":"设施不足","severity":"low","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D041","review_text":"整体不错，会推荐朋友来","rating":4,"category":"综合","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D042","review_text":"出餐号牌不显示，不知道好了没","rating":2,"category":"出餐速度","sentiment":"negative","issue":"出餐速度慢","severity":"medium","reply_draft":"感谢反馈，我们正在升级叫号系统...","reviewed":False,"approved":False},
        {"review_id":"D043","review_text":"抹茶千层层次分明","rating":5,"category":"口味","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D044","review_text":"态度不好，像是欠他钱","rating":1,"category":"服务","sentiment":"negative","issue":"服务态度差","severity":"high","reply_draft":"非常抱歉，我们会严肃处理...","reviewed":False,"approved":False},
        {"review_id":"D045","review_text":"音乐选品品味在线","rating":4,"category":"环境","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D046","review_text":"漏给了一杯饮品，沟通半天","rating":1,"category":"服务","sentiment":"negative","issue":"服务态度差","severity":"high","reply_draft":"非常抱歉出现遗漏，我们立即改进...","reviewed":False,"approved":False},
        {"review_id":"D047","review_text":"停车券没有主动给","rating":3,"category":"服务","sentiment":"neutral","issue":"服务细节不足","severity":"low","reply_draft":"","reviewed":False,"approved":False},
        {"review_id":"D048","review_text":"二楼靠窗位子很棒","rating":5,"category":"环境","sentiment":"positive","issue":"","severity":"","reply_draft":"","reviewed":False,"approved":False},
    ]

    top_issues = [
        {"id":1,"title":"出餐速度慢 — 高峰期备餐能力不足","mentions":9,"severity":"high","severity_label":"高",
         "evidence_ids":["D002","D007","D012","D018","D025","D036","D042"],
         "suggestion":"建议高峰时段增加 1 名备餐员，提前预配常用食材，优化订单排队算法"},
        {"id":2,"title":"服务态度差 — 员工沟通与情绪管理","mentions":7,"severity":"high","severity_label":"高",
         "evidence_ids":["D003","D009","D017","D020","D023","D044","D046"],
         "suggestion":"安排服务礼仪复训，建立差评关联绩效机制，每周例会复盘典型案例"},
        {"id":3,"title":"环境卫生问题 — 清洁频次与死角管理","mentions":5,"severity":"medium","severity_label":"中",
         "evidence_ids":["D005","D011","D014","D015","D034"],
         "suggestion":"制定每 2 小时巡检表，重点覆盖卫生间和用餐区，张贴清洁签到码"},
    ]

    harness_checks = [
        {"name":"输入校验","status":"passed","detail":"48/48 条通过"},
        {"name":"Schema 约束","status":"passed","detail":"所有字段合法"},
        {"name":"证据绑定","status":"passed","detail":"19 条证据已关联"},
        {"name":"安全检查","status":"passed","detail":"无违规内容"},
        {"name":"人工审批","status":"pending","detail":"12 条待审核"},
    ]

    negative_reviews = [r for r in reviews if r["sentiment"] == "negative"]

    st.session_state.demo_reviews = reviews
    st.session_state.demo_top_issues = top_issues
    st.session_state.demo_harness = harness_checks
    st.session_state.demo_neg_count = sum(1 for r in reviews if r["sentiment"] == "negative")
    st.session_state.demo_pending_count = sum(1 for r in reviews if r["sentiment"] == "negative" and not r["reviewed"])
    st.session_state.demo_avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
    st.session_state.demo_total = len(reviews)
    st.session_state.demo_reply_queue = negative_reviews
    st.session_state.dashboard_initialized = True


# ═══════════════════════════════════════════════════════════════════════════
# Pagination (compact, right-aligned)
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
        if st.button("◀", key="page_prev", disabled=(current == 0), use_container_width=True):
            st.session_state[page_key] = max(0, current - 1)
            st.rerun()
    with c3:
        if st.button("▶", key="page_next", disabled=(current >= total_pages - 1), use_container_width=True):
            st.session_state[page_key] = min(total_pages - 1, current + 1)
            st.rerun()
    return current


# ═══════════════════════════════════════════════════════════════════════════
# Component: Issue Card
# ═══════════════════════════════════════════════════════════════════════════

def _render_issue_card(issue: dict) -> None:
    sev_colors = {"high": "#C0392B", "medium": "#E67E22", "low": "#27AE60"}
    stripe_color = sev_colors.get(issue["severity"], "#8B7355")
    sev_color = sev_colors.get(issue["severity"], "#8B7355")

    evidence_html = " ".join(f"<code>{eid}</code>" for eid in issue["evidence_ids"])

    html = f"""<div class="issue-card">
<div class="severity-stripe" style="background:{stripe_color};"></div>
<div class="issue-header">
<span class="issue-num">问题 #{issue['id']}</span>
<span class="sev-dot" style="color:{sev_color};">● {issue['severity_label']}严重</span>
</div>
<div class="issue-title">{issue['title']}</div>
<div class="issue-stats">
<span>提及 <b>{issue['mentions']}</b> 次</span>
<span>证据 <b>{len(issue['evidence_ids'])}</b> 条</span>
</div>
<div class="evidence-list">关联评论：{evidence_html}</div>
<span class="btn-suggestion">💡 {issue['suggestion']}</span>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Component: Harness Status
# ═══════════════════════════════════════════════════════════════════════════

def _render_harness_status(checks: list[dict]) -> None:
    status_icon = {"passed": "✓", "pending": "◷", "failed": "✗"}
    status_color = {"passed": "#27AE60", "pending": "#E67E22", "failed": "#C0392B"}
    status_badge = {
        "passed": ("#27AE60", "#E8F8F0", "✓ 通过"),
        "pending": ("#E67E22", "#FEF5E7", "◷ 进行中"),
        "failed": ("#C0392B", "#FDEDEC", "✗ 未通过"),
    }

    html_parts = ['<div class="section-card">',
                  '<p class="section-title">AI 工作流可靠性检查</p>',
                  '<p style="font-size:0.74rem;color:#A09080;margin:-8px 0 10px 0;">Harness Engine 实时状态</p>']

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
# Component: Reply Queue — HTML rows, compact
# ═══════════════════════════════════════════════════════════════════════════

def _render_reply_queue(queue: list[dict], page: int, page_size: int = 4) -> None:
    start = page * page_size
    page_items = queue[start:start + page_size]

    if not page_items:
        st.info("所有差评已处理完毕")
        return

    sev_dot_map = {"high": ("#C0392B", "高"), "medium": ("#E67E22", "中"), "low": ("#27AE60", "低")}

    with st.container(border=True):
        st.markdown(
            '<p class="section-title" style="margin-bottom:8px;">差评回复审核队列</p>',
            unsafe_allow_html=True,
        )

        for item in page_items:
            sev = item.get("severity", "low")
            dot_c, dot_l = sev_dot_map.get(sev, ("#8B7355", sev))
            reviewed = item.get("reviewed", False)
            status_badge = (
                '<span style="font-size:0.64rem;color:#27AE60;background:#E8F8F0;'
                'padding:1px 7px;border-radius:9px;font-weight:600;">已审核</span>'
                if reviewed else
                '<span style="font-size:0.64rem;color:#E67E22;background:#FEF5E7;'
                'padding:1px 7px;border-radius:9px;font-weight:600;">待审核</span>'
            )
            snippet = item["review_text"][:32] + ("…" if len(item["review_text"]) > 32 else "")

            r1, r2 = st.columns([22, 3], gap="small")
            with r1:
                st.markdown(f"""<div class="q-item">
<span class="q-id">{item['review_id']}</span>
<span class="q-text">{snippet}</span>
<span style="font-weight:600;font-size:0.76rem;color:{dot_c};">● {dot_l}</span>
{status_badge}
</div>""", unsafe_allow_html=True)
            with r2:
                if reviewed:
                    st.button("✓", key=f"q_done_{item['review_id']}", disabled=True)
                else:
                    if st.button("审核", key=f"q_review_{item['review_id']}", type="secondary"):
                        for r in st.session_state.demo_reply_queue:
                            if r["review_id"] == item["review_id"]:
                                r["reviewed"] = True
                                break
                        for r in st.session_state.demo_reviews:
                            if r["review_id"] == item["review_id"]:
                                r["reviewed"] = True
                                break
                        st.session_state.demo_pending_count = sum(
                            1 for r in st.session_state.demo_reply_queue if not r["reviewed"]
                        )
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    _init_demo_data()
    st.session_state.nav_selection = "数据看板"
    render_sidebar()

    # ── Top bar: title (left) + action buttons (right) ──
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
            approved = [r for r in st.session_state.demo_reply_queue if r.get("reviewed")]
            if approved:
                export_df = pd.DataFrame(approved)[["review_id","review_text","issue","severity","reply_draft"]]
                st.download_button(
                    label="📥 导出", data=export_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"approved_replies_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv", use_container_width=True, key="export_approved",
                )
            else:
                st.button("📥 导出", use_container_width=True, disabled=True, key="export_disabled")
        with bc2:
            if st.button("🧪 评测", key="run_eval_dash", use_container_width=True):
                st.switch_page("pages/trace_eval_page.py")
        with bc3:
            if st.button("🔍 追踪", key="view_trace_dash", use_container_width=True):
                st.switch_page("pages/trace_eval_page.py")

    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)

    # ── Metric cards ──
    mc1, mc2, mc3, mc4 = st.columns(4, gap="medium")
    with mc1:
        metric_card(label="总评论数", value=st.session_state.demo_total, icon="📝",
                    color="#4A3728", bg_color="#FFFCF8", warn=False)
    with mc2:
        metric_card(label="平均评分", value=st.session_state.demo_avg_rating, icon="⭐",
                    color="#4A3728", bg_color="#FFFCF8", warn=False)
    with mc3:
        metric_card(label="差评数", value=st.session_state.demo_neg_count, icon="⚠️",
                    color="#C0392B", bg_color="#FFFCF8", warn=True)
    with mc4:
        pending = st.session_state.demo_pending_count
        metric_card(label="待审核回复", value=pending, icon="✏️",
                    color="#E67E22" if pending > 0 else "#27AE60",
                    bg_color="#FFFCF8", warn=pending > 0)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # Main two-column layout (left: issues, right: harness + queue)
    # ═══════════════════════════════════════════════════════
    left_col, right_col = st.columns([5, 5], gap="medium")

    with left_col:
        st.markdown(
            '<p class="section-title" style="margin-top:0;">三大问题洞察</p>',
            unsafe_allow_html=True,
        )
        for issue in st.session_state.demo_top_issues:
            _render_issue_card(issue)

    with right_col:
        # Harness status card
        _render_harness_status(st.session_state.demo_harness)

        # Reply queue card
        queue = st.session_state.demo_reply_queue
        if "queue_page" not in st.session_state:
            st.session_state["queue_page"] = 0
        page = st.session_state["queue_page"]
        total_pages = max(1, (len(queue) + 4 - 1) // 4)
        if page >= total_pages:
            page = 0
            st.session_state["queue_page"] = 0
        _render_reply_queue(queue, page, page_size=4)

        # Pagination below queue card
        _render_pagination(len(queue), page_size=4)


if __name__ == "__main__":
    main()
