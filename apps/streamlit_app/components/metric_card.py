"""
Reusable metric card component — 完全复刻上传页示例图样式
"""

from __future__ import annotations
import streamlit as st

def metric_card(
    label: str,
    value,
    icon: str = "",
    color: str = "#4A3728",
    bg_color: str = "#FFF8F5",
    warn: bool = False,
) -> None:
    """Render a single metric card styled to match the mockup."""
    border = "#F0D0C0" if warn else "#E8E0D5"
    bg = "#FFF3EB" if warn else bg_color

    html = f"""
    <div style="
        background: {bg};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 18px 16px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    ">
        <div style="
            font-size: 0.78rem;
            color: #8B7355;
            font-weight: 500;
            margin-bottom: 6px;
            letter-spacing: 0.3px;
        ">{icon}  {label}</div>
        <div style="
            font-size: 1.85rem;
            font-weight: 700;
            color: {color};
            line-height: 1.2;
        ">{value}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)