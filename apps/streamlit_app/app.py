"""
Small Shop Review Response & Insight Agent
Streamlit 主入口 — 小店差评处理与问题洞察 Agent
"""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure project root is on path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from loguru import logger
import sys as _sys
logger.remove()
logger.add(_sys.stderr, level="INFO")

from small_shop_agent.utils.logger import ensure_logger_configured
ensure_logger_configured()

import streamlit as st

st.set_page_config(
    page_title="小店评论经营助手",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

from apps.streamlit_app.components.sidebar import render_sidebar

# Sidebar renders with unified dark coffee theme from render_sidebar()
st.markdown("""
<style>
    .stApp { background-color: #FAFBF7; }
</style>
""", unsafe_allow_html=True)

render_sidebar()

st.markdown("""
<div style="text-align: center; padding-top: 120px;">
    <div style="font-size: 3rem; margin-bottom: 12px;">☕</div>
    <h1 style="
        font-size: 1.8rem;
        font-weight: 700;
        color: #4A3728;
        margin-bottom: 12px;
        letter-spacing: 0.3px;
    ">
        小店评论经营助手
    </h1>
    <p style="
        font-size: 1rem;
        color: #8B7355;
        margin-bottom: 28px;
        line-height: 1.6;
    ">
        Small Shop Review Response & Insight Agent<br>
        差评处理 · 问题复盘 · 回复审核
    </p>
    <p style="font-size: 0.85rem; color: #A09080;">
        👈 请从左侧导航选择「上传评论」开始使用
    </p>
</div>
""", unsafe_allow_html=True)
