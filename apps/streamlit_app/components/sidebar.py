"""
Reusable sidebar navigation — dark coffee-shop theme with functional page switching
"""

from __future__ import annotations
import streamlit as st


_PAGE_MAP: dict[str, str] = {
    "上传评论": "pages/upload_page.py",
    "数据看板": "pages/dashboard_page.py",
    "回复审核": "pages/reply_review_page.py",
    "追踪与评测": "pages/trace_eval_page.py",
}


def render_sidebar() -> str:
    st.markdown("""
    <style>
        /* Hide default Streamlit page navigation */
        div[data-testid="stSidebarNav"] { display: none !important; }

        section[data-testid="stSidebar"] {
            background: #2C221B;
        }
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] .stMarkdown * {
            color: #D4C4B0 !important;
        }

        /* Nav buttons */
        section[data-testid="stSidebar"] button {
            background: transparent !important;
            border: none !important;
            border-left: 3px solid transparent !important;
            text-align: left !important;
            font-size: 0.94rem !important;
            font-weight: 500 !important;
            color: #C4B8A8 !important;
            padding: 10px 14px !important;
            border-radius: 0 10px 10px 0 !important;
            width: 100% !important;
            margin: 2px 0 !important;
            transition: all 0.18s;
        }
        section[data-testid="stSidebar"] button:hover {
            background: rgba(255,255,255,0.06) !important;
            color: #FFF !important;
            border-left-color: rgba(255,255,255,0.25) !important;
        }
        section[data-testid="stSidebar"] button[kind="primary"] {
            background: rgba(255,255,255,0.10) !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border-left: 3px solid #C8A882 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("""
        <div style="padding: 14px 8px 16px 8px; text-align: center;">
            <div style="font-size: 1.08rem; font-weight: 700; color: #FFFFFF; letter-spacing: 0.3px;">
                ☕ 小店点评经营助手
            </div>
            <div style="font-size: 0.68rem; color: #A09080; margin-top: 2px;">
                Review Response &amp; Insight Agent
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='margin:0; border-color:#3D342E;'>", unsafe_allow_html=True)

        if "nav_selection" not in st.session_state:
            st.session_state.nav_selection = "上传评论"

        nav_items = [
            ("📤  上传评论", "上传评论"),
            ("📊  数据看板", "数据看板"),
            ("💌  回复审核", "回复审核"),
            ("🔍  追踪评测", "追踪与评测"),
            ("⚙️  设置", "设置"),
        ]

        for label, key in nav_items:
            active = st.session_state.nav_selection == key
            clicked = st.button(
                label,
                key=f"nav_{key}",
                width='stretch',
                type="primary" if active else "secondary",
            )
            if clicked:
                st.session_state.nav_selection = key
                if key in _PAGE_MAP:
                    st.switch_page(_PAGE_MAP[key])

        st.markdown("<hr style='margin:8px 0 0 0; border-color:#3D342E;'>", unsafe_allow_html=True)

        st.markdown("""
        <div style="padding: 10px 8px; font-size: 0.72rem; color: #A09080;">
            <div style="display:flex; align-items:center; gap:7px;">
                <span style="
                    width:7px; height:7px; background:#4CAF50;
                    border-radius:50%; display:inline-block;
                "></span>
                系统就绪
            </div>
        </div>
        """, unsafe_allow_html=True)

    return st.session_state.nav_selection
