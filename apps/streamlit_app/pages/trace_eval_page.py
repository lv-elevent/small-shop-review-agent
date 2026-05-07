"""
Trace & Eval Page — 追踪与评测：左追踪日志右评测摘要，参照 UI mockup (Trace&Eval页.png)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from apps.streamlit_app.components.sidebar import render_sidebar

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="小店评论经营助手 · 追踪与评测",
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

    /* ── Trace event row ── */
    .tr-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 10px 14px;
        border: 1px solid #E8E0D5;
        border-radius: 8px;
        background: #FFFFFF;
        margin-bottom: 6px;
        transition: all 0.15s;
        position: relative;
        overflow: hidden;
    }
    .tr-row.has-left-bar {
        border-left: 3px solid #E8E0D5;
    }
    .tr-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-top: 5px;
        flex-shrink: 0;
    }
    .tr-time {
        font-size: 0.74rem;
        color: #A09080;
        min-width: 52px;
        white-space: nowrap;
        padding-top: 1px;
    }
    .tr-step {
        font-weight: 600;
        font-size: 0.84rem;
        color: #4A3728;
        min-width: 100px;
    }
    .tr-detail {
        flex: 1;
        font-size: 0.80rem;
        color: #6B5B4F;
        line-height: 1.5;
    }
    .tr-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 10px;
        white-space: nowrap;
        flex-shrink: 0;
    }

    /* ── Eval metric cards ── */
    .ev-metric {
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .ev-metric .ev-value {
        font-size: 1.5rem;
        font-weight: 700;
    }
    .ev-metric .ev-label {
        font-size: 0.72rem;
        color: #8B7355;
        font-weight: 500;
        margin-top: 2px;
    }

    /* ── Eval run row ── */
    .er-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        border: 1px solid #E8E0D5;
        border-radius: 8px;
        background: #FFFFFF;
        margin-bottom: 4px;
        font-size: 0.80rem;
    }
    .er-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    /* ── Section card ── */
    .section-card {
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 14px;
        padding: 20px 22px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .section-title-sm {
        font-weight: 700;
        font-size: 0.95rem;
        color: #4A3728;
        margin-bottom: 12px;
    }

    /* ── Status badges ── */
    .sb {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 12px;
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
    if "trace_eval_init" in st.session_state:
        return

    now = datetime.now()
    base = now - timedelta(minutes=15)

    # Trace events — follows the workflow: upload → classify → sentiment → insight → reply → safety → approval
    trace_events = [
        {"time": base.strftime("%H:%M:%S"),
         "step": "输入校验",
         "status": "passed",
         "detail": "48/48 条评论通过格式校验，0 条结构错误，编码自动识别为 UTF-8"},
        {"time": (base + timedelta(seconds=8)).strftime("%H:%M:%S"),
         "step": "Schema 约束",
         "status": "passed",
         "detail": "所有字段合法，review_id 唯一性检查通过，rating 范围 1-5 均合规"},
        {"time": (base + timedelta(seconds=15)).strftime("%H:%M:%S"),
         "step": "评论分类",
         "status": "passed",
         "detail": "48 条评论分类完成：口味 14 · 服务 12 · 出餐 9 · 环境 8 · 综合 5"},
        {"time": (base + timedelta(seconds=22)).strftime("%H:%M:%S"),
         "step": "情绪分析",
         "status": "passed",
         "detail": "正面 22 条 · 中性 7 条 · 负面 19 条，情绪置信度均值 0.87"},
        {"time": (base + timedelta(seconds=35)).strftime("%H:%M:%S"),
         "step": "三大问题聚合",
         "status": "passed",
         "detail": "识别 3 个主要问题：出餐速度慢 (9次) · 服务态度差 (7次) · 环境卫生 (5次)，证据链完整"},
        {"time": (base + timedelta(seconds=48)).strftime("%H:%M:%S"),
         "step": "回复草稿生成",
         "status": "passed",
         "detail": "19 条差评均已生成回复草稿，模板匹配率 94%，个性化调整率 73%"},
        {"time": (base + timedelta(seconds=58)).strftime("%H:%M:%S"),
         "step": "安全检查",
         "status": "warning",
         "detail": "17/19 条通过安全检查，1 条需修改 (承诺补偿)，1 条已拦截 (公开声明处罚员工)"},
        {"time": (base + timedelta(seconds=65)).strftime("%H:%M:%S"),
         "step": "证据绑定",
         "status": "passed",
         "detail": "19 条证据已关联至对应洞察，review_id → insight 映射完整"},
        {"time": (base + timedelta(seconds=72)).strftime("%H:%M:%S"),
         "step": "人工审批",
         "status": "pending",
         "detail": "12 条草稿待审核 · 5 条已批准 · 1 条已驳回 · 0 条自动发布"},
        {"time": (base + timedelta(seconds=80)).strftime("%H:%M:%S"),
         "step": "工作流完成",
         "status": "passed",
         "detail": "全流程耗时 95 秒，LLM 调用 52 次，重试 1 次 (安全检查)，fallback 0 次"},
    ]

    # Eval runs
    eval_runs = [
        {"id": "eval-004", "time": (now - timedelta(minutes=5)).strftime("%H:%M"), "score": 0.91, "status": "passed",
         "summary": "综合评分 91% · 准确率 94% · 安全通过率 95%"},
        {"id": "eval-003", "time": (now - timedelta(hours=2)).strftime("%H:%M"), "score": 0.88, "status": "passed",
         "summary": "综合评分 88% · 准确率 91% · 安全通过率 92%"},
        {"id": "eval-002", "time": (now - timedelta(days=1)).strftime("%m-%d %H:%M"), "score": 0.85, "status": "passed",
         "summary": "综合评分 85% · 准确率 88% · 安全通过率 90%"},
        {"id": "eval-001", "time": (now - timedelta(days=2)).strftime("%m-%d %H:%M"), "score": 0.72, "status": "warning",
         "summary": "综合评分 72% · 准确率 76% · 安全通过率 81%"},
    ]

    # Eval metrics summary
    eval_metrics = {
        "accuracy": 0.94,
        "response_quality": 0.89,
        "safety_pass_rate": 0.95,
        "avg_confidence": 0.87,
        "total_runs": 4,
        "latest_score": 0.91,
    }

    st.session_state.trace_events = trace_events
    st.session_state.eval_runs_list = eval_runs
    st.session_state.eval_metrics = eval_metrics
    st.session_state.eval_has_run = True
    st.session_state.trace_eval_init = True


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _status_dot_color(status: str) -> str:
    return {"passed": "#27AE60", "warning": "#E67E22", "failed": "#C0392B", "pending": "#8B7355"}.get(status, "#8B7355")

def _status_badge(status: str) -> str:
    cfg = {
        "passed": ("#27AE60", "#E8F8F0", "✓ 通过"),
        "warning": ("#E67E22", "#FEF5E7", "⚠ 警告"),
        "failed": ("#C0392B", "#FDEDEC", "✗ 失败"),
        "pending": ("#8B7355", "#F5F0E8", "◷ 进行中"),
    }
    c, bg, label = cfg.get(status, ("#8B7355", "#F5F0E8", status))
    return f'<span class="sb" style="color:{c};background:{bg};">{label}</span>'


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    _init_demo_data()
    st.session_state.nav_selection = "追踪与评测"
    render_sidebar()

    events = st.session_state.trace_events
    runs = st.session_state.eval_runs_list
    metrics = st.session_state.eval_metrics

    # ── Title ──
    st.markdown("""
    <div style="margin-bottom:4px;">
        <h1 style="font-size:1.55rem;font-weight:700;color:#3D2C20;margin:0 0 2px 0;">🔍 追踪与评测</h1>
        <p style="font-size:0.86rem;color:#8B7355;margin:0;">
            工作流 Trace 日志 · AI 输出质量评测 · 可靠性监控
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # Main two-column layout
    # ═══════════════════════════════════════════════════════
    left, right = st.columns([11, 9], gap="medium")

    # ══════════════ LEFT: 追踪日志 ══════════════
    with left:
        st.markdown(
            '<div class="section-card">'
            '<p class="section-title-sm">📋 追踪日志</p>'
            '<p style="font-size:0.78rem;color:#A09080;margin:-8px 0 12px 0;">'
            '最近一次工作流执行记录 · 共 ' + str(len(events)) + ' 个步骤</p>',
            unsafe_allow_html=True,
        )

        # ── Flow timeline visualization (compact) ──
        flow_steps = [e["step"] for e in events]
        flow_statuses = [e["status"] for e in events]
        flow_html = '<div style="display:flex;align-items:center;gap:0;flex-wrap:wrap;padding:6px 0 12px 0;">'
        for i, (step, sts) in enumerate(zip(flow_steps, flow_statuses)):
            dot_c = _status_dot_color(sts)
            flow_html += f'<span style="display:flex;align-items:center;gap:4px;font-size:0.72rem;color:#6B5B4F;white-space:nowrap;">'
            flow_html += f'<span style="width:7px;height:7px;border-radius:50%;background:{dot_c};display:inline-block;"></span>'
            flow_html += f'{step}</span>'
            if i < len(flow_steps) - 1:
                flow_html += '<span style="color:#D4C4B0;margin:0 6px;">→</span>'
        flow_html += '</div>'
        st.markdown(flow_html, unsafe_allow_html=True)

        # ── Trace event rows ──
        for e in events:
            sts = e["status"]
            dot_c = _status_dot_color(sts)

            st.markdown(f"""<div class="tr-row has-left-bar" style="border-left-color:{dot_c};">
<span class="tr-status-dot" style="background:{dot_c};"></span>
<span class="tr-time">{e['time']}</span>
<span class="tr-step">{e['step']}</span>
<span class="tr-detail">{e['detail']}</span>
<span>{_status_badge(sts)}</span>
</div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # close section-card

    # ══════════════ RIGHT: 评测摘要 ══════════════
    with right:
        # ── Eval metrics ──
        st.markdown(
            '<div class="section-card" style="margin-bottom:12px;">'
            '<p class="section-title-sm">🧪 评测摘要</p>',
            unsafe_allow_html=True,
        )

        # Metric cards in 2x3 grid
        mr1, mr2, mr3 = st.columns(3, gap="small")
        with mr1:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#27AE60;">{metrics["accuracy"]:.0%}</div>'
                f'<div class="ev-label">分类准确率</div></div>',
                unsafe_allow_html=True,
            )
        with mr2:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#3498DB;">{metrics["response_quality"]:.0%}</div>'
                f'<div class="ev-label">回复质量</div></div>',
                unsafe_allow_html=True,
            )
        with mr3:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#27AE60;">{metrics["safety_pass_rate"]:.0%}</div>'
                f'<div class="ev-label">安全通过率</div></div>',
                unsafe_allow_html=True,
            )

        mr4, mr5, mr6 = st.columns(3, gap="small")
        with mr4:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#4A3728;">{metrics["avg_confidence"]:.0%}</div>'
                f'<div class="ev-label">平均置信度</div></div>',
                unsafe_allow_html=True,
            )
        with mr5:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#4A3728;">{metrics["total_runs"]}</div>'
                f'<div class="ev-label">累计评测次数</div></div>',
                unsafe_allow_html=True,
            )
        with mr6:
            sc = metrics["latest_score"]
            sc_c = "#27AE60" if sc >= 0.85 else "#E67E22" if sc >= 0.70 else "#C0392B"
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:{sc_c};">{sc:.0%}</div>'
                f'<div class="ev-label">最新综合评分</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)  # close first section-card

        # ── Eval run history ──
        st.markdown(
            '<div class="section-card">'
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">'
            '<p class="section-title-sm" style="margin:0;">📜 评测记录</p>'
            '<span style="font-size:0.78rem;color:#A09080;">共 ' + str(len(runs)) + ' 次</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        for run in runs:
            dot_c = _status_dot_color(run["status"])
            sc = run["score"]
            sc_c = "#27AE60" if sc >= 0.85 else "#E67E22" if sc >= 0.70 else "#C0392B"

            st.markdown(f"""<div class="er-row">
<span class="er-dot" style="background:{dot_c};"></span>
<span style="font-size:0.74rem;color:#A09080;min-width:60px;">{run['time']}</span>
<span style="font-weight:600;font-size:0.80rem;color:#4A3728;min-width:65px;">{run['id']}</span>
<span style="font-weight:700;font-size:0.84rem;color:{sc_c};min-width:42px;">{sc:.0%}</span>
<span style="font-size:0.76rem;color:#6B5B4F;">{run['summary']}</span>
</div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # close section-card

        # ── Run Eval button ──
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        bc1, bc2, bc3 = st.columns([2, 2, 2])
        with bc1:
            if st.button("🧪 运行评测", key="run_eval_btn", use_container_width=True, type="primary"):
                with st.spinner("评测运行中…"):
                    import time
                    time.sleep(1.5)
                new_run = {
                    "id": f"eval-{len(runs) + 1:03d}",
                    "time": datetime.now().strftime("%H:%M"),
                    "score": 0.93,
                    "status": "passed",
                    "summary": f"综合评分 93% · 准确率 95% · 安全通过率 96%"
                }
                st.session_state.eval_runs_list.insert(0, new_run)
                st.session_state.eval_metrics["total_runs"] += 1
                st.session_state.eval_metrics["latest_score"] = 0.93
                st.toast("✅ 评测完成", icon="🧪")
                st.rerun()
        with bc2:
            st.button("📥 导出报告", key="export_eval", use_container_width=True, type="secondary")
        with bc3:
            st.button("📋 复制 Trace", key="copy_trace", use_container_width=True, type="secondary")


if __name__ == "__main__":
    main()
