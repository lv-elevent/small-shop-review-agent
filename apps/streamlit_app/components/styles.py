"""
Global Styles Injection —— 小店评论经营助手 UI 规范

提供全局CSS样式注入和颜色变量定义。
"""

from __future__ import annotations

import streamlit as st


# ═══════════════════════════════════════════════════════════════════════════
# Color Palette —— 颜色规范
# ═══════════════════════════════════════════════════════════════════════════

COLOR_PALETTE = {
    # 咖啡色系 - 主色调
    "coffee": {
        900: "#2C221B",  # Sidebar 背景
        800: "#3D2C20",  # 最深标题
        700: "#4A3728",  # 正文主色
        600: "#5C3D2E",  # 强调文字
        500: "#6B4C3B",  # Primary按钮、图标
        400: "#8B7355",  # Secondary文字
        300: "#A09080",  # 弱化文字、占位符
        200: "#D4C4B0",  # 边框、分割线
        100: "#E8E0D5",  # 浅边框、分隔线
        50: "#F5F0E8",   # Hover背景
    },
    # 功能色
    "success": {
        "main": "#27AE60",
        "light": "#E8F8F0",
        "border": "#A9DFBF",
    },
    "warning": {
        "main": "#E67E22",
        "light": "#FEF5E7",
        "border": "#F5CBA7",
    },
    "danger": {
        "main": "#C0392B",
        "light": "#FDEDEC",
        "border": "#F5B7B1",
    },
    "info": {
        "main": "#3498DB",
        "light": "#EBF5FB",
        "border": "#AED6F1",
    },
    # 中性色
    "text": {
        "primary": "#3D2C20",
        "secondary": "#6B5B4F",
        "tertiary": "#8B7355",
        "muted": "#A09080",
    },
    "border": {
        "default": "#E8E0D5",
        "light": "#F5F0E8",
        "dashed": "#D4C4B0",
    },
    "background": {
        "page": "#FAFBF7",
        "card": "#FFFFFF",
        "hover": "#F5F0E8",
        "cream": "#FFFCF8",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Status Style Mapping —— 状态样式映射
# ═══════════════════════════════════════════════════════════════════════════

STATUS_STYLES = {
    # 成功类状态
    "passed": {"color": "#27AE60", "bg": "#E8F8F0", "icon": "✓", "label": "通过"},
    "pass": {"color": "#27AE60", "bg": "#E8F8F0", "icon": "✓", "label": "安全"},
    "safe": {"color": "#27AE60", "bg": "#E8F8F0", "icon": "✓", "label": "安全"},
    "approved": {"color": "#27AE60", "bg": "#E8F8F0", "icon": "✓", "label": "已批准"},
    "success": {"color": "#27AE60", "bg": "#E8F8F0", "icon": "✓", "label": "成功"},
    "edited": {"color": "#3498DB", "bg": "#EBF5FB", "icon": "📝", "label": "已编辑"},

    # 警告类状态
    "pending": {"color": "#E67E22", "bg": "#FEF5E7", "icon": "◷", "label": "进行中"},
    "warning": {"color": "#E67E22", "bg": "#FEF5E7", "icon": "⚠", "label": "警告"},
    "rewrite_required": {"color": "#E67E22", "bg": "#FEF5E7", "icon": "⚠", "label": "需修改"},
    "human_escalation": {"color": "#E67E22", "bg": "#FEF5E7", "icon": "👤", "label": "人工介入"},

    # 危险类状态
    "blocked": {"color": "#C0392B", "bg": "#FDEDEC", "icon": "✗", "label": "已拦截"},
    "failed": {"color": "#C0392B", "bg": "#FDEDEC", "icon": "✗", "label": "失败"},
    "rejected": {"color": "#C0392B", "bg": "#FDEDEC", "icon": "✗", "label": "已驳回"},
    "danger": {"color": "#C0392B", "bg": "#FDEDEC", "icon": "✗", "label": "危险"},
    "error": {"color": "#C0392B", "bg": "#FDEDEC", "icon": "✗", "label": "错误"},

    # 信息类状态
    "info": {"color": "#3498DB", "bg": "#EBF5FB", "icon": "ℹ", "label": "信息"},
    "neutral": {"color": "#8B7355", "bg": "#F5F0E8", "icon": "●", "label": "中性"},
    "default": {"color": "#8B7355", "bg": "#F5F0E8", "icon": "●", "label": "待处理"},
}


# ═══════════════════════════════════════════════════════════════════════════
# Severity Colors —— 严重度颜色
# ═══════════════════════════════════════════════════════════════════════════

SEVERITY_STYLES = {
    "high": {"color": "#C0392B", "label": "高", "stripe": "#C0392B"},
    "medium": {"color": "#E67E22", "label": "中", "stripe": "#E67E22"},
    "low": {"color": "#27AE60", "label": "低", "stripe": "#27AE60"},
}


# ═══════════════════════════════════════════════════════════════════════════
# Global CSS Styles
# ═══════════════════════════════════════════════════════════════════════════

GLOBAL_STYLES = """
<style>
    /* ═══════════════════════════════════════════════════════════════
       Page Base
       ═══════════════════════════════════════════════════════════════ */
    .stApp {
        background: #FAFBF7;
    }

    /* ═══════════════════════════════════════════════════════════════
       Typography
       ═══════════════════════════════════════════════════════════════ */
    h1, h2, h3 {
        color: #3D2C20;
        font-weight: 700;
    }

    /* ═══════════════════════════════════════════════════════════════
       Card Container (st.container with border)
       ═══════════════════════════════════════════════════════════════ */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border: 1px solid #E8E0D5 !important;
        border-radius: 14px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Buttons (scoped to .stMain to avoid polluting sidebar)
       ═══════════════════════════════════════════════════════════════ */
    .stMain div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #6B4C3B 0%, #5C3D2E 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        transition: all 0.2s ease !important;
    }

    .stMain div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #7D5A47 0%, #6B4C3B 100%) !important;
        box-shadow: 0 3px 10px rgba(74,55,40,0.25) !important;
        transform: translateY(-1px) !important;
    }

    .stMain div[data-testid="stButton"] > button[kind="secondary"] {
        background: #FFFFFF !important;
        border: 1px solid #6B4C3B !important;
        border-radius: 10px !important;
        color: #6B4C3B !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    .stMain div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: #F5F0E8 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       File Uploader
       ═══════════════════════════════════════════════════════════════ */
    section[data-testid="stFileUploader"] {
        border: 2px dashed #D4C4B0 !important;
        border-radius: 12px !important;
        background: #FFFCF8 !important;
        padding: 28px 16px !important;
        text-align: center !important;
        transition: all 0.25s ease !important;
    }

    section[data-testid="stFileUploader"]:hover {
        border-color: #A08060 !important;
        background: #FFF9F0 !important;
    }

    section[data-testid="stFileUploader"] > div > div > div > div {
        color: #6B4C3B !important;
        font-weight: 500 !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       DataFrame / Table
       ═══════════════════════════════════════════════════════════════ */
    div[data-testid="stDataFrame"] th {
        background: #F5F0E8 !important;
        color: #4A3728 !important;
        font-weight: 700 !important;
        font-size: 0.72rem !important;
        border-bottom: 1px solid #E8E0D5 !important;
    }

    div[data-testid="stDataFrame"] td {
        font-size: 0.76rem !important;
        color: #4A3728 !important;
        border-bottom: 1px solid #F5F0E8 !important;
    }

    div[data-testid="stDataFrame"] tr:hover td {
        background: #FAFAFA !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Tabs
       ═══════════════════════════════════════════════════════════════ */
    button[data-baseweb="tab"] {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #8B7355 !important;
        padding: 12px 20px !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #4A3728 !important;
        border-bottom-color: #6B4C3B !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Expander
       ═══════════════════════════════════════════════════════════════ */
    details[data-testid="stExpander"] {
        border: 1px solid #E8E0D5 !important;
        border-radius: 10px !important;
        background: #FFFFFF !important;
    }

    details[data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: #4A3728 !important;
        padding: 12px 16px !important;
    }

    details[data-testid="stExpander"] summary:hover {
        background: #F5F0E8 !important;
        border-radius: 10px !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Metric
       ═══════════════════════════════════════════════════════════════ */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }

    div[data-testid="stMetric"] label {
        color: #8B7355 !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #4A3728 !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        font-size: 0.7rem !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Select / Input
       ═══════════════════════════════════════════════════════════════ */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        border-color: #E8E0D5 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="input"] > div:focus-within {
        border-color: #6B4C3B !important;
        box-shadow: 0 0 0 2px rgba(107,76,59,0.1) !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Toggle
       ═══════════════════════════════════════════════════════════════ */
    div[data-testid="stToggle"] > div > div {
        background-color: #E8E0D5 !important;
    }

    div[data-testid="stToggle"] > div > div[data-checked="true"] {
        background-color: #6B4C3B !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Popover / Dialog
       ═══════════════════════════════════════════════════════════════ */
    div[data-testid="stPopover"] > div > div {
        border: 1px solid #E8E0D5 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Text Area
       ═══════════════════════════════════════════════════════════════ */
    textarea[data-testid="stTextArea"] {
        border-color: #E8E0D5 !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
    }

    textarea[data-testid="stTextArea"]:focus {
        border-color: #6B4C3B !important;
        box-shadow: 0 0 0 2px rgba(107,76,59,0.1) !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Progress Bar
       ═══════════════════════════════════════════════════════════════ */
    div[data-testid="stProgress"] > div > div {
        background-color: #E8E0D5 !important;
        border-radius: 4px !important;
    }

    div[data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, #6B4C3B, #8B7355) !important;
        border-radius: 4px !important;
    }

    /* ═══════════════════════════════════════════════════════════════
       Toast / Alert
       ═══════════════════════════════════════════════════════════════ */
    div[data-testid="stToast"] {
        border-radius: 10px !important;
    }

</style>
"""


# ═══════════════════════════════════════════════════════════════════════════
# Functions
# ═══════════════════════════════════════════════════════════════════════════

def inject_global_styles() -> None:
    """Inject global CSS styles into the Streamlit app.

    Call this at the beginning of each page.
    """
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)


def _build_flat_palette() -> dict:
    """Derive a flat colour dictionary from the nested COLOR_PALETTE."""
    flat: dict = {}
    coffee = COLOR_PALETTE["coffee"]
    for shade in (900, 800, 700, 600, 500, 400, 300, 200, 100, 50):
        flat[f"coffee_{shade}"] = coffee[shade]
    flat["cream"] = COLOR_PALETTE["background"]["cream"]
    for group in ("success", "warning", "danger", "info"):
        for key, mapped in (("main", "main"), ("light", "light"), ("border", "border")):
            flat[f"{group}_{mapped}"] = COLOR_PALETTE[group][key]
    flat["bg_page"] = COLOR_PALETTE["background"]["page"]
    flat["bg_card"] = COLOR_PALETTE["background"]["card"]
    flat["border_default"] = COLOR_PALETTE["border"]["default"]
    flat["text_primary"] = COLOR_PALETTE["text"]["primary"]
    flat["text_secondary"] = COLOR_PALETTE["text"]["secondary"]
    flat["text_muted"] = COLOR_PALETTE["text"]["muted"]
    return flat


_FLAT_PALETTE: dict | None = None


def get_color_palette() -> dict:
    """Return the flat color palette dictionary.

    Keys: coffee_900 .. coffee_50, cream,
    success_main / success_light / success_border,
    warning_main / warning_light / warning_border,
    danger_main  / danger_light  / danger_border,
    info_main    / info_light    / info_border,
    bg_page, bg_card, border_default,
    text_primary, text_secondary, text_muted.
    """
    global _FLAT_PALETTE
    if _FLAT_PALETTE is None:
        _FLAT_PALETTE = _build_flat_palette()
    return _FLAT_PALETTE


def get_status_style(status: str) -> dict:
    """Get the style configuration for a given status.

    Args:
        status: Status string (e.g., 'passed', 'pending', 'blocked')

    Returns:
        dict: Dictionary with 'color', 'bg', 'icon', 'label' keys
    """
    return STATUS_STYLES.get(status, STATUS_STYLES["default"])


def get_severity_style(severity: str) -> dict:
    """Get the style configuration for a given severity level.

    Args:
        severity: Severity string ('high', 'medium', 'low')

    Returns:
        dict: Dictionary with 'color', 'label', 'stripe' keys
    """
    return SEVERITY_STYLES.get(severity, SEVERITY_STYLES["medium"])


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert hex color to rgba string.

    Args:
        hex_color: Hex color string (e.g., '#FF5733')
        alpha: Alpha value between 0 and 1

    Returns:
        str: RGBA color string
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
