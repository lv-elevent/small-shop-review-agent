"""
Trace & Eval Page — 追踪与评测：左追踪日志右评测摘要
接入 TraceService + EvalService 真实数据
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
from small_shop_agent.services.trace_service import TraceService
from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.services.insight_service import InsightService
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.storage.database import execute_migrations, get_connection
from small_shop_agent.exports.report_exporter import generate_report

execute_migrations()

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
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

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


def _step_cn(name: str) -> str:
    return _STEP_NAME_CN.get(name, name)


def _translate_detail(raw: str) -> str:
    """Translate common English trace output_summary fragments to Chinese."""
    import re
    s = raw
    s = re.sub(r"(\d+) valid reviews?", r"\1 条有效评论", s)
    s = re.sub(r"(\d+) raw reviews?", r"\1 条原始评论", s)
    s = re.sub(r"(\d+) pass, (\d+) rewrite_required, (\d+) blocked",
               r"通过 \1 条，需重写 \2 条，拦截 \3 条", s)
    s = re.sub(r"(\d+) evidence; (\d+) valid, (\d+) rejected/insufficient",
               r"共 \1 条证据；\2 条有效，\3 条不足", s)
    s = re.sub(r"(\d+) evidence records across (\d+) issues",
               r"\1 条证据记录（\2 个问题）", s)
    s = re.sub(r"(\d+) reviews", r"\1 条评论", s)
    s = re.sub(r"(\d+) classified", r"\1 条已分类", s)
    s = re.sub(r"(\d+) analyzed", r"\1 条已分析", s)
    s = re.sub(r"(\d+) drafts", r"\1 条草稿", s)
    s = re.sub(r"(\d+) insights", r"\1 个洞察", s)
    s = re.sub(r"(\d+) evidence", r"\1 条证据", s)
    s = re.sub(r"(\d+) negative candidates", r"\1 条差评", s)
    s = re.sub(r"(\d+) drafts generated", r"\1 条草稿已生成", s)
    return s


def _status_dot_color(status: str) -> str:
    return {
        "passed": "#27AE60", "warning": "#E67E22",
        "failed": "#C0392B", "pending": "#8B7355",
    }.get(status, "#8B7355")


def _status_badge(status: str) -> str:
    cfg = {
        "passed": ("#27AE60", "#E8F8F0", "✓ 通过"),
        "warning": ("#E67E22", "#FEF5E7", "⚠ 警告"),
        "failed": ("#C0392B", "#FDEDEC", "✗ 失败"),
        "pending": ("#8B7355", "#F5F0E8", "◷ 进行中"),
    }
    c, bg, label = cfg.get(status, ("#8B7355", "#F5F0E8", status))
    return f'<span class="sb" style="color:{c};background:{bg};">{label}</span>'


def _fmt_time(ts: str) -> str:
    """Extract HH:MM:SS from ISO timestamp."""
    try:
        return ts[11:19] if "T" in ts else ts[:8] if len(ts) >= 8 else ts
    except Exception:
        return ts or "—"


# ═══════════════════════════════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.session_state.nav_selection = "追踪与评测"
    render_sidebar()

    trace_svc = TraceService()
    eval_svc = EvalService()
    batch_id = st.session_state.get("current_batch_id")
    if not batch_id:
        qp_bid = st.query_params.get("batch_id")
        if qp_bid:
            st.session_state.current_batch_id = qp_bid
            batch_id = qp_bid

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

    # ── No batch ──
    if not batch_id:
        st.info("👈 请先在 **「上传评论」** 页面中上传 CSV 或开启 Demo Mode 并运行分析。")
        return

    # ── Load traces ──
    try:
        traces = trace_svc.get_trace(batch_id)
    except Exception:
        traces = []

    # ── No analysis ──
    if not traces:
        st.warning("该批次尚无工作流追踪记录。请前往 **「上传评论」** 页面运行分析。")
        return

    # ── Load eval data ──
    try:
        latest_eval = eval_svc.get_latest_eval()
        eval_runs = eval_svc.list_eval_runs(limit=10)
    except Exception:
        latest_eval = None
        eval_runs = []

    # ═══════════════════════════════════════════════════════
    # Main two-column layout
    # ═══════════════════════════════════════════════════════
    left, right = st.columns([11, 9], gap="medium")

    # ═══════ LEFT: Trace Log ═══════
    with left:
        # Build ordered step list: workflow trace steps + approval + eval
        workflow_order = [
            "input_validation", "data_cleaning", "classification",
            "sentiment_analysis", "issue_aggregation", "evidence_check",
            "reply_drafting", "safety_check",
        ]
        trace_map: dict[str, dict] = {t["step_name"]: t for t in traces}
        ordered_steps: list[dict] = []
        for step_name in workflow_order:
            t = trace_map.get(step_name)
            if t:
                ordered_steps.append(t)

        # Check for approval actions
        approval_exists = False
        approval_count = 0
        try:
            from small_shop_agent.storage.database import get_connection
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

        # Check for eval results
        eval_exists = latest_eval is not None

        st.markdown(
            '<div class="section-card">'
            '<p class="section-title-sm">📋 追踪日志</p>'
            '<p style="font-size:0.78rem;color:#A09080;margin:-8px 0 14px 0;">'
            f'工作流执行记录 · 共 {len(ordered_steps)} 个步骤</p>',
            unsafe_allow_html=True,
        )

        # ── Step cards ──
        step_num = 0
        for t in ordered_steps:
            step_num += 1
            sts = t["status"]
            dot_c = _status_dot_color(sts)
            time_str = _fmt_time(t.get("created_at", ""))
            detail_parts = [_translate_detail(t.get("input_summary", "")),
                          _translate_detail(t.get("output_summary", ""))]
            latency = t.get("latency_ms", 0)
            if latency:
                detail_parts.append(f"耗时 {latency}ms")
            detail = " → ".join(p for p in detail_parts if p)

            st.markdown(f"""<div class="tr-row has-left-bar" style="border-left-color:{dot_c};">
<span style="font-weight:700;font-size:0.82rem;color:#4A3728;min-width:24px;">#{step_num}</span>
<span class="tr-status-dot" style="background:{dot_c};"></span>
<span class="tr-step">{_step_cn(t['step_name'])}</span>
<span class="tr-detail">{detail}</span>
<span>{_status_badge(sts)}</span>
</div>""", unsafe_allow_html=True)

        # ── Approval step card ──
        step_num += 1
        if approval_exists:
            ap_dot = "#27AE60"
            ap_status = "passed"
            ap_label = f"已审批 {approval_count} 条"
        else:
            ap_dot = "#8B7355"
            ap_status = "pending"
            ap_label = "暂无审批记录"
        st.markdown(f"""<div class="tr-row has-left-bar" style="border-left-color:{ap_dot};">
<span style="font-weight:700;font-size:0.82rem;color:#4A3728;min-width:24px;">#{step_num}</span>
<span class="tr-status-dot" style="background:{ap_dot};"></span>
<span class="tr-step">人工审批</span>
<span class="tr-detail">{ap_label}</span>
<span>{_status_badge(ap_status)}</span>
</div>""", unsafe_allow_html=True)

        # ── Eval step card ──
        step_num += 1
        if eval_exists:
            ev_dot = "#27AE60"
            ev_status = "passed"
            ta = latest_eval.get("topic_accuracy", 0)
            sa = latest_eval.get("sentiment_accuracy", 0)
            ev_label = f"分类准确率 {ta:.0%}，情绪准确率 {sa:.0%}"
        else:
            ev_dot = "#8B7355"
            ev_status = "pending"
            ev_label = "尚未运行评测"
        st.markdown(f"""<div class="tr-row has-left-bar" style="border-left-color:{ev_dot};">
<span style="font-weight:700;font-size:0.82rem;color:#4A3728;min-width:24px;">#{step_num}</span>
<span class="tr-status-dot" style="background:{ev_dot};"></span>
<span class="tr-step">评测运行</span>
<span class="tr-detail">{ev_label}</span>
<span>{_status_badge(ev_status)}</span>
</div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════ RIGHT: Eval Summary ═══════
    with right:
        st.markdown(
            '<div class="section-card" style="margin-bottom:12px;">'
            '<p class="section-title-sm">🧪 评测摘要</p>',
            unsafe_allow_html=True,
        )

        if latest_eval:
            ta = latest_eval.get("topic_accuracy", 0)
            sa = latest_eval.get("sentiment_accuracy", 0)
            unsafe = latest_eval.get("unsafe_reply_count", 0)
            schema_fail = latest_eval.get("schema_failure_count", 0)
            total_cases = latest_eval.get("total_eval_cases", 0)
            composite = round((ta + sa) / 2, 2)
            if total_cases == 0:
                st.warning("评测基准不匹配：当前批次评论ID与内置基准数据（示例CSV）不一致，无法计算准确率。请使用 Demo 模式运行示例数据后再评测。")
        else:
            ta = sa = composite = 0
            unsafe = schema_fail = total_cases = 0

        # 2x3 metric grid
        mr1, mr2, mr3 = st.columns(3, gap="small")
        with mr1:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#27AE60;">{ta:.0%}</div>'
                f'<div class="ev-label">分类准确率</div></div>',
                unsafe_allow_html=True,
            )
        with mr2:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#3498DB;">{sa:.0%}</div>'
                f'<div class="ev-label">情绪准确率</div></div>',
                unsafe_allow_html=True,
            )
        with mr3:
            uc = "#C0392B" if unsafe > 0 else "#27AE60"
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:{uc};">{unsafe}</div>'
                f'<div class="ev-label">不安全回复</div></div>',
                unsafe_allow_html=True,
            )

        mr4, mr5, mr6 = st.columns(3, gap="small")
        with mr4:
            sc = "#C0392B" if schema_fail > 0 else "#27AE60"
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:{sc};">{schema_fail}</div>'
                f'<div class="ev-label">结构校验失败</div></div>',
                unsafe_allow_html=True,
            )
        with mr5:
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:#4A3728;">{total_cases}</div>'
                f'<div class="ev-label">评测样例数</div></div>',
                unsafe_allow_html=True,
            )
        with mr6:
            comp_c = "#27AE60" if composite >= 0.85 else "#E67E22" if composite >= 0.70 else "#C0392B"
            st.markdown(
                f'<div class="ev-metric">'
                f'<div class="ev-value" style="color:{comp_c};">{composite:.0%}</div>'
                f'<div class="ev-label">综合评分</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Eval run history ──
        st.markdown(
            '<div class="section-card">'
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">'
            '<p class="section-title-sm" style="margin:0;">📜 评测记录</p>'
            '<span style="font-size:0.78rem;color:#A09080;">共 ' + str(len(eval_runs)) + ' 次</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        if eval_runs:
            for run in eval_runs:
                run_ta = run.get("topic_accuracy", 0)
                run_sa = run.get("sentiment_accuracy", 0)
                score = round((run_ta + run_sa) / 2, 2)
                sc_c = "#27AE60" if score >= 0.85 else "#E67E22" if score >= 0.70 else "#C0392B"
                time_str = _fmt_time(run.get("created_at", ""))
                rid = run.get("eval_run_id", "—")

                summary = (
                    f"分类 {run_ta:.0%} · 情绪 {run_sa:.0%} · "
                    f"不安全 {run.get('unsafe_reply_count', 0)} · "
                    f"Schema {run.get('schema_failure_count', 0)}"
                )

                st.markdown(f"""<div class="er-row">
<span class="er-dot" style="background:#27AE60;"></span>
<span style="font-size:0.74rem;color:#A09080;min-width:60px;">{time_str}</span>
<span style="font-weight:600;font-size:0.80rem;color:#4A3728;min-width:80px;">{rid}</span>
<span style="font-weight:700;font-size:0.84rem;color:{sc_c};min-width:42px;">{score:.0%}</span>
<span style="font-size:0.76rem;color:#6B5B4F;">{summary}</span>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="font-size:0.82rem;color:#A09080;text-align:center;padding:20px 0;">'
                '尚未运行评测，点击下方按钮开始</p>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Action buttons ──
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        bc1, bc2, bc3 = st.columns([2, 2, 2])
        with bc1:
            if st.button("🧪 运行评测", key="run_eval_btn", use_container_width=True, type="primary"):
                with st.spinner("正在运行评测…"):
                    result = eval_svc.run_eval({"batch_id": batch_id})
                if result["success"]:
                    st.toast("✅ 评测完成", icon="🧪")
                    st.rerun()
                else:
                    st.toast(f"❌ 评测失败：{result.get('error', '')}", icon="❌")
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
                        "📥 导出报告", data=report_text,
                        file_name=f"trace_eval_report_{batch_id}.md",
                        mime="text/markdown", use_container_width=True, type="secondary",
                        key="export_eval_btn",
                    )
                except Exception:
                    st.button("📥 导出报告", key="export_eval", use_container_width=True,
                              type="secondary", disabled=True,
                              help="导出报告生成失败")
            else:
                st.button("📥 导出报告", key="export_eval", use_container_width=True,
                          type="secondary", disabled=True,
                          help="请先运行分析后再导出")
        with bc3:
            _status_text = {"passed": "✓", "warning": "⚠", "failed": "✗", "pending": "◷"}
            trace_text_lines = []
            for t in traces:
                sts = t["status"]
                trace_text_lines.append(
                    f"[{_status_text.get(sts, sts)}] {_step_cn(t['step_name'])} | "
                    f"输入: {_translate_detail(t.get('input_summary', '-'))} | "
                    f"输出: {_translate_detail(t.get('output_summary', '-'))} | "
                    f"耗时: {t.get('latency_ms', 0)}ms"
                )
            trace_text = "\n".join(trace_text_lines)
            with st.popover("📋 复制 Trace", use_container_width=True):
                if trace_text:
                    st.code(trace_text, language=None)
                    st.caption("👆 选中上方文本即可复制")
                else:
                    st.info("暂无追踪数据")


if __name__ == "__main__":
    main()
