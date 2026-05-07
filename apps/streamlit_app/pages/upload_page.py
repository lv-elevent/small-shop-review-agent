"""
Upload Page — CSV 上传、校验与 Demo Mode
接入 ReviewService + WorkflowService 真实后端
"""

from __future__ import annotations
import io
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from apps.streamlit_app.components.metric_card import metric_card
from apps.streamlit_app.components.sidebar import render_sidebar
from small_shop_agent.services.review_service import ReviewService
from small_shop_agent.services.workflow_service import WorkflowService
from small_shop_agent.storage.database import execute_migrations

execute_migrations()

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="小店评论经营助手 · 上传评论",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: #FAFBF7; }
section[data-testid="stFileUploader"] {
    border: 2px dashed #D4C4B0 !important;
    border-radius: 14px !important;
    background: #FFFCF8 !important;
    padding: 40px 20px !important;
    text-align: center !important;
    transition: border-color 0.25s, background 0.25s !important;
}
section[data-testid="stFileUploader"]:hover { border-color: #A08060 !important; background: #FFF9F0 !important; }
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6B4C3B 0%, #5C3D2E 100%) !important;
    border: none !important; border-radius: 10px !important; color: #FFF !important;
    font-weight: 600 !important; font-size: 1rem !important; padding: 12px 32px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #7D5A47 0%, #6B4C3B 100%) !important;
    box-shadow: 0 3px 10px rgba(74,55,40,0.25) !important; transform: translateY(-1px) !important;
}
div[data-testid="stTable"] th { background: #F5F0E8 !important; color: #4A3728 !important; font-weight: 600 !important; font-size: 0.8rem !important; }
div[data-testid="stTable"] td { font-size: 0.82rem !important; }
.right-card { background:#fff; border:1px solid #E8E0D5; border-radius:14px; padding:22px 20px; box-shadow:0 1px 4px rgba(0,0,0,0.04); margin-bottom:16px;}
.section-title { font-size:1rem; font-weight:700; color:#4A3728; margin-bottom:14px; letter-spacing:0.2px;}
hr.custom-hr { border:none; border-top:1px solid #E8E0D5; margin:22px 0; }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────
STORE_TYPES = ["咖啡店","餐厅","奶茶店","便利店","甜品店","面包店","小吃店","其他"]
DEMO_CSV_PATH = _PROJECT_ROOT / "src" / "small_shop_agent" / "demo" / "sample_reviews.csv"

# ── Helpers ──────────────────────────────────────────────────────────────

def _read_csv_preview(file_bytes: bytes) -> pd.DataFrame | None:
    """Parse CSV bytes for UI preview. Returns DataFrame or None."""
    for enc in ["utf-8","utf-8-sig","gbk","gb2312","gb18030","latin-1"]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
            return df
        except Exception:
            continue
    return None


def _render_validation_cards(stats: dict):
    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)
    st.markdown('<p class="section-title">📊 数据校验结果</p>', unsafe_allow_html=True)
    valid = stats.get("valid_review_count", 0)
    total = stats.get("total_rows", 0)
    dup = stats.get("duplicate_count", 0)
    empty = stats.get("empty_review_count", 0)
    schema_err = stats.get("schema_error_count", 0)
    invalid_rating = stats.get("invalid_rating_count", 0)

    cards = [
        {"label":"有效评论","value":valid,"icon":"✅","color":"#2E7D32","warn":False},
        {"label":"重复评论","value":dup,"icon":"🔄","color":"#E67E22","warn":dup>0},
        {"label":"空评论","value":empty,"icon":"📭","color":"#C0392B","warn":empty>0},
        {"label":"评分异常","value":invalid_rating,"icon":"⚠️","color":"#C0392B","warn":invalid_rating>0},
    ]
    cols = st.columns(4, gap="medium")
    for i, card in enumerate(cards):
        with cols[i]:
            metric_card(**card)

    if schema_err > 0:
        st.error(f"❌ CSV 缺少必填字段（{schema_err} 项结构错误），请检查列名。")
    elif valid == total and total > 0:
        st.success(f"✅ 全部 {total} 条评论校验通过，可开始分析。")
    elif valid > 0:
        parts = [f"{dup} 条重复" if dup else "",
                 f"{empty} 条空评论" if empty else "",
                 f"{invalid_rating} 条评分异常" if invalid_rating else ""]
        st.warning(f"⚠️ 共 {total} 条，{valid} 条有效。{'、'.join(filter(None, parts))}。分析时自动过滤。")
    else:
        st.error("❌ 未检测到有效评论数据，请检查 CSV 格式。")


def _render_right_panel(has_data: bool):
    st.markdown('<div class="right-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📋 CSV 格式说明</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.84rem; color:#6B5B4F; line-height:1.75;">
        <p style="font-weight:600;">必填列：</p>
        <ul><li><code>review_text</code> — 评论正文</li>
        <li><code>rating</code> — 评分 (1-5)</li>
        <li><code>review_time</code> — 评论时间</li></ul>
        <p style="font-weight:600;">可选列：</p>
        <ul><li><code>review_id</code> — 评论 ID</li>
        <li><code>customer_name</code> — 顾客昵称</li>
        <li><code>platform</code> — 来源平台</li></ul>
        <p style="font-size:0.78rem; color:#A09080;">支持 UTF-8 / GBK 编码</p>
    </div>""", unsafe_allow_html=True)
    # Download sample CSV button
    try:
        sample_bytes = DEMO_CSV_PATH.read_bytes()
        st.download_button(
            "⬇ 下载示例 CSV", data=sample_bytes,
            file_name="sample_reviews.csv", mime="text/csv",
            use_container_width=True,
        )
    except Exception:
        pass

    # Preview demo CSV
    try:
        sample_df = pd.read_csv(DEMO_CSV_PATH)
        st.markdown('<p style="font-weight:600; color:#4A3728; margin:8px 0 4px;">示例数据预览</p>', unsafe_allow_html=True)
        st.dataframe(sample_df, use_container_width=True, hide_index=True, height=180)
    except Exception:
        pass

    if has_data:
        df = st.session_state.uploaded_df
        st.markdown('<div class="right-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">📈 数据概况</p>', unsafe_allow_html=True)
        avg_rating = "-"
        if "rating" in df.columns and len(df) > 0:
            try:
                avg_rating = f"{pd.to_numeric(df['rating'], errors='coerce').dropna().mean():.1f}"
            except Exception:
                pass
        c1, c2 = st.columns(2)
        with c1:
            st.metric("总评论", len(df))
            st.metric("平台数", df["platform"].nunique() if "platform" in df.columns else "-")
        with c2:
            st.metric("平均评分", avg_rating)
            date_col = "date" if "date" in df.columns else ("review_time" if "review_time" in df.columns else None)
        st.metric("最早日期", str(df[date_col].iloc[0])[:10] if date_col and len(df) > 0 else "-")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="right-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">💡 使用提示</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.82rem; color:#6B5B4F; line-height:1.85;">
        <ol style="padding-left:18px; margin:0;">
            <li>上传 CSV 后系统自动校验数据完整性</li>
            <li>开启 <strong>Demo Mode</strong> 可离线体验全部流程</li>
            <li>分析完成后前往「数据看板」查看洞察</li>
            <li>所有 AI 回复需人工审批后发出</li>
            <li>在「追踪与评测」中查看 Trace 和 Eval</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Main Page ────────────────────────────────────────────────────────────
def main() -> None:
    st.session_state.nav_selection = "上传评论"
    render_sidebar()

    rs = ReviewService()
    ws = WorkflowService()

    st.markdown("""
    <div style="margin-bottom:6px;">
        <h1 style="font-size:1.55rem;font-weight:700;color:#3D2C20;margin:0 0 2px 0;">📤 上传评论数据</h1>
        <p style="font-size:0.86rem;color:#8B7355;margin:0;">上传顾客评论 CSV，系统将自动完成分类、情绪分析和回复草稿生成。</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)
    left, right = st.columns([5, 3], gap="large")

    with left:
        demo_mode = st.toggle(
            "🎭 Demo Mode — 使用内置演示数据，无需上传文件",
            value=st.session_state.get("demo_mode", False), key="demo_mode",
            help="开启后加载示例评论 CSV，可离线体验完整分析流程。",
        )

        if demo_mode:
            st.info("🎭 **Demo Mode 已开启** — 使用内置 15 条示例评论数据。")
            try:
                demo_df = pd.read_csv(DEMO_CSV_PATH)
                demo_df.columns = [c.strip().lower().replace(" ", "_") for c in demo_df.columns]
                st.session_state.uploaded_df = demo_df
                if "_uploaded_bytes" in st.session_state:
                    del st.session_state._uploaded_bytes
                if "_file_name" in st.session_state:
                    del st.session_state._file_name
            except Exception as e:
                st.error(f"无法加载示例数据：{e}")

        store_type = st.selectbox(
            "🏪 门店类型", options=STORE_TYPES, index=0,
            key="store_type", help="选择门店类型以匹配回复风格和分析维度。",
        )

        if not demo_mode:
            st.markdown("<p style='font-weight:600;color:#4A3728;margin:16px 0 2px 0;'>📁 上传 CSV 文件</p>", unsafe_allow_html=True)
            st.caption("拖拽 CSV 文件到此处或点击上传 · 最大 200MB")
            uploaded_file = st.file_uploader(
                "上传评论 CSV", type=["csv"], accept_multiple_files=False,
                key="csv_uploader", label_visibility="collapsed",
            )
            if uploaded_file is not None:
                file_bytes = uploaded_file.getvalue()
                df = _read_csv_preview(file_bytes)
                if df is None:
                    st.error("❌ 无法解析 CSV 文件。")
                    st.session_state.uploaded_df = None
                    st.session_state._uploaded_bytes = None
                elif len(df) == 0:
                    st.error("❌ CSV 文件为空。")
                    st.session_state.uploaded_df = None
                    st.session_state._uploaded_bytes = None
                else:
                    st.session_state.uploaded_df = df
                    st.session_state._uploaded_bytes = file_bytes
                    st.session_state._file_name = uploaded_file.name
                    st.toast(f"✅ 上传成功！{len(df)} 条记录。")
            else:
                if "uploaded_df" in st.session_state and not demo_mode:
                    st.session_state.uploaded_df = None
                    st.session_state._uploaded_bytes = None

        # Show preview if data loaded
        if st.session_state.get("uploaded_df") is not None:
            df = st.session_state.uploaded_df
            st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)
            st.markdown('<p class="section-title">📋 数据预览</p>', unsafe_allow_html=True)
            with st.expander(f"共 {len(df)} 条评论 — 点击展开", expanded=False):
                display_cols = [c for c in df.columns if c in (
                    "review_id", "review_text", "rating", "review_time", "customer_name", "platform"
                )] or list(df.columns)
                st.dataframe(df[display_cols].head(10), use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        has_data = st.session_state.get("uploaded_df") is not None and len(
            st.session_state.get("uploaded_df", pd.DataFrame())
        ) > 0

        start_clicked = st.button(
            "🚀 开始分析", type="primary", use_container_width=True,
            disabled=not has_data, key="start_analysis",
        )

        if start_clicked and has_data:
            # Step 1: Create batch (validate + persist)
            with st.spinner("正在校验并上传 CSV …"):
                if demo_mode:
                    result = rs.create_batch(
                        str(DEMO_CSV_PATH), store_type=store_type,
                        file_name="sample_reviews.csv",
                    )
                else:
                    result = rs.create_batch(
                        st.session_state.get("_uploaded_bytes", b""),
                        store_type=store_type,
                        file_name=st.session_state.get("_file_name", "upload.csv"),
                    )

            if not result["success"]:
                st.error(f"❌ 上传失败：{result.get('message', '未知错误')}")
            else:
                st.session_state.latest_validation_result = result["validation"]
                st.session_state.current_batch_id = result["batch_id"]
                _render_validation_cards(result["validation"])

                # Step 2: Run demo analysis
                with st.spinner("正在运行分析流水线（分类 → 情绪 → 问题聚合 → 回复草稿 → 安全检查）…"):
                    wf_result = ws.run_demo_analysis(result["batch_id"])

                st.session_state.latest_workflow_result = wf_result

                if wf_result["success"]:
                    s = wf_result["summary"]
                    st.success(
                        f"✅ 分析完成！"
                        f"{s['review_count']} 条评论 → "
                        f"{s['insight_count']} 个洞察 → "
                        f"{s['draft_count']} 条回复草稿"
                    )
                    if s.get("blocked_count", 0) > 0:
                        st.warning(f"⚠️ {s['blocked_count']} 条回复因安全原因被拦截，需人工处理。")
                    st.info("👉 请前往 **「数据看板」** 查看洞察结果，或前往 **「回复审核」** 审批回复草稿。")
                else:
                    st.error(f"❌ 分析失败：{wf_result.get('error', '未知错误')}")

        # Show last result if exists
        elif st.session_state.get("latest_workflow_result") is not None and not start_clicked:
            wf = st.session_state.latest_workflow_result
            if wf.get("success"):
                s = wf["summary"]
                st.success(
                    f"📌 最近分析：batch `{st.session_state.get('current_batch_id', '?')}` — "
                    f"{s.get('review_count', '?')} 条评论, "
                    f"{s.get('insight_count', '?')} 个洞察, "
                    f"{s.get('draft_count', '?')} 条草稿"
                )

    with right:
        _render_right_panel(st.session_state.get("uploaded_df") is not None and len(
            st.session_state.get("uploaded_df", pd.DataFrame())
        ) > 0)


if __name__ == "__main__":
    main()
