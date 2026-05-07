"""
Upload Page — CSV 上传、校验与 Demo Mode
优化版：1:1 复刻示例图
"""

from __future__ import annotations
import io
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
import sys
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from apps.streamlit_app.components.metric_card import metric_card
from apps.streamlit_app.components.sidebar import render_sidebar

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="小店评论经营助手 · 上传评论",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS for upload page ───────────────────────────────────────────
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

# ── Constants & Demo Data ────────────────────────────────────────────────
STORE_TYPES = ["咖啡店","餐厅","奶茶店","便利店","甜品店","面包店","小吃店","其他"]
DEMO_REVIEWS = [
    {"review_id":f"D00{i+1}","review_text":"示例评论内容","rating":i%5+1,"review_time":"2025-01-01 08:00","customer_name":"用户"+str(i+1),"platform":"美团"}
    for i in range(10)
]
SAMPLE_CSV_DATA = pd.DataFrame(DEMO_REVIEWS)

# ── Helper Functions ─────────────────────────────────────────────────────
def validate_csv(df: pd.DataFrame) -> dict:
    total = len(df)
    empty_rows = df.isna().all(axis=1).sum()
    missing_text = df['review_text'].isna().sum() if 'review_text' in df.columns else 0
    duplicate_count = df.duplicated().sum()
    structure_errors = 0
    if 'rating' in df.columns:
        rating_num = pd.to_numeric(df['rating'], errors='coerce')
        structure_errors += rating_num.isna().sum() + ((rating_num<1)|(rating_num>5)).sum()
    valid = max(0,total-empty_rows-structure_errors)
    return {
        "total": total, "valid": valid,
        "missing_text": missing_text, "duplicate_count": duplicate_count,
        "structure_errors": structure_errors, "empty_rows": empty_rows
    }

def _parse_uploaded_file(uploaded_file):
    content = uploaded_file.read()
    for enc in ["utf-8","utf-8-sig","gbk","gb2312","gb18030","latin-1"]:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=enc)
            df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
            return df
        except: continue
    return None

def _render_validation_cards(results: dict):
    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)
    st.markdown('<p class="section-title">📊 数据校验结果</p>', unsafe_allow_html=True)
    cards = [
        {"label":"有效评论","value":results["valid"],"icon":"✅","color":"#2E7D32","warn":False},
        {"label":"重复评论","value":results["duplicate_count"],"icon":"🔄","color":"#E67E22","warn":results["duplicate_count"]>0},
        {"label":"空评论","value":results["missing_text"],"icon":"📭","color":"#C0392B","warn":results["missing_text"]>0},
        {"label":"结构错误","value":results["structure_errors"],"icon":"⚠️","color":"#C0392B","warn":results["structure_errors"]>0}
    ]
    cols = st.columns(4, gap="medium")
    for i,card in enumerate(cards):
        with cols[i]: metric_card(**card)
    if results["valid"]==results["total"] and results["total"]>0: st.success(f"✅ 全部 {results['total']} 条评论校验通过，可开始分析。")
    elif results["valid"]>0:
        parts = [f"{results['duplicate_count']} 条重复" if results['duplicate_count'] else "",
                 f"{results['missing_text']} 条空评论" if results['missing_text'] else "",
                 f"{results['structure_errors']} 条结构错误" if results['structure_errors'] else ""]
        st.warning(f"⚠️ 共 {results['total']} 条，{results['valid']} 条有效。{'、'.join(filter(None, parts))}。分析时自动过滤。")
    else: st.error("❌ 未检测到有效评论数据，请检查 CSV 格式。")

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
    st.download_button("⬇ 下载示例 CSV", data=SAMPLE_CSV_DATA.to_csv(index=False).encode("utf-8"), file_name="sample_reviews.csv", mime="text/csv", use_container_width=True)
    st.markdown('<p style="font-weight:600; color:#4A3728; margin:8px 0 4px;">示例数据预览</p>', unsafe_allow_html=True)
    st.dataframe(SAMPLE_CSV_DATA, use_container_width=True, hide_index=True, height=180)
    if has_data:
        df = st.session_state.uploaded_df
        st.markdown('<div class="right-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">📈 数据概况</p>', unsafe_allow_html=True)
        avg_rating = "-"
        if "rating" in df.columns and len(df)>0: avg_rating=f"{pd.to_numeric(df['rating'],errors='coerce').dropna().mean():.1f}"
        c1,c2 = st.columns(2)
        with c1: st.metric("总评论", len(df)); st.metric("平台数", df["platform"].nunique() if "platform" in df.columns else "-")
        with c2: st.metric("平均评分", avg_rating); st.metric("最早日期", df['review_time'].min()[:10] if "review_time" in df.columns else "-")
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
    st.markdown("""
    <div style="margin-bottom:6px;">
        <h1 style="font-size:1.55rem;font-weight:700;color:#3D2C20;margin:0 0 2px 0;">📤 上传评论数据</h1>
        <p style="font-size:0.86rem;color:#8B7355;margin:0;">上传顾客评论 CSV，系统将自动完成分类、情绪分析和回复草稿生成。</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr class='custom-hr'>", unsafe_allow_html=True)
    left,right = st.columns([5,3], gap="large")

    with left:
        demo_mode = st.toggle("🎭 Demo Mode — 使用内置演示数据，无需上传文件",
                              value=st.session_state.get("demo_mode",False), key="demo_mode",
                              help="开启后加载 10 条模拟评论，可离线体验完整分析流程。")
        if demo_mode:
            st.info("🎭 **Demo Mode 已开启** — 使用 10 条内置示例评论数据。")
            st.session_state.uploaded_df = pd.DataFrame(DEMO_REVIEWS)
            st.session_state.validation_results = validate_csv(st.session_state.uploaded_df)

        st.selectbox("🏪 门店类型", options=STORE_TYPES, index=0, key="store_type", help="选择门店类型以匹配回复风格和分析维度。")

        if not demo_mode:
            st.markdown("<p style='font-weight:600;color:#4A3728;margin:16px 0 2px 0;'>📁 上传 CSV 文件</p>", unsafe_allow_html=True)
            st.caption("拖拽 CSV 文件到此处或点击上传 · 最大 200MB")
            uploaded_file = st.file_uploader("上传评论 CSV", type=["csv"], accept_multiple_files=False, key="csv_uploader", label_visibility="collapsed")
            if uploaded_file is not None:
                with st.spinner("正在解析并校验 CSV …"):
                    df = _parse_uploaded_file(uploaded_file)
                    if df is None: st.error("❌ 无法解析 CSV 文件。"); st.session_state.uploaded_df = None; st.session_state.validation_results=None
                    elif len(df)==0: st.error("❌ CSV 文件为空。"); st.session_state.uploaded_df=None; st.session_state.validation_results=None
                    else: results=validate_csv(df); st.session_state.uploaded_df=df; st.session_state.validation_results=results; st.toast(f"✅ 上传成功！{results['total']} 条记录，{results['valid']} 条有效。")
            else:
                if "uploaded_df" in st.session_state and not demo_mode:
                    st.session_state.uploaded_df=None; st.session_state.validation_results=None

        if st.session_state.get("validation_results") is not None and st.session_state.get("uploaded_df") is not None:
            _render_validation_cards(st.session_state.validation_results)
            with st.expander(f"📋 数据预览（共 {len(st.session_state.uploaded_df)} 条）", expanded=False):
                display_cols = [c for c in st.session_state.uploaded_df.columns if c in ("review_id","review_text","rating","review_time","customer_name","platform")] or list(st.session_state.uploaded_df.columns)
                st.dataframe(st.session_state.uploaded_df[display_cols].head(10), use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        has_data = st.session_state.get("uploaded_df") is not None and len(st.session_state.get("uploaded_df",pd.DataFrame()))>0
        start_clicked = st.button("🚀 开始分析", type="primary", use_container_width=True, disabled=not has_data, key="start_analysis")
        if start_clicked:
            st.session_state.analysis_started=True; st.session_state.analysis_time=datetime.now().isoformat(); st.toast("🔬 分析流程已启动！", icon="🚀")
            progress=st.progress(0,text="初始化分析节点…")
            steps=[(0.1,"分类与情绪分析中…"),(0.3,"聚合三大问题…"),(0.6,"生成回复草稿…"),(0.85,"安全检查中…"),(1.0,"分析完成 ✅")]
            for pct,msg in steps: time.sleep(0.2); progress.progress(pct,text=msg)
            valid_n=st.session_state.validation_results.get("valid","N/A")
            st.success(f"✅ 分析完成！共处理 {valid_n} 条评论。请前往「数据看板」和「回复审核」查看结果。")

    with right: _render_right_panel(st.session_state.get("uploaded_df") is not None and len(st.session_state.get("uploaded_df",pd.DataFrame()))>0)

if __name__=="__main__": main()