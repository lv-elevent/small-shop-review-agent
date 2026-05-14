from __future__ import annotations

import streamlit as st

from apps.streamlit_app.components.styles import get_status_style as _get_status_style


# ═══════════════════════════════════════════════════════════════════════════
# Status helpers
# ═══════════════════════════════════════════════════════════════════════════

def get_status_style(status: str) -> dict:
    """Get style config (color, bg, icon, label) for a status key.

    Delegates to ``styles.get_status_style()``.
    Unknown statuses fall back to the neutral default entry.
    """
    return _get_status_style(status)


def render_status_badge(status: str, label: str | None = None) -> str:
    """Return an HTML ``<span>`` status badge string.

    Does NOT call st.markdown — the caller injects the string.
    """
    cfg = _get_status_style(status)
    color = cfg["color"]
    bg = cfg["bg"]
    text = label if label is not None else cfg["label"]
    icon = cfg.get("icon", "")
    display = f"{icon} {text}".strip()

    return (
        f'<span style="display:inline-block;font-size:0.7rem;font-weight:600;'
        f'padding:2px 10px;border-radius:10px;color:{color};background:{bg};'
        f'white-space:nowrap;">{display}</span>'
    )


# ═══════════════════════════════════════════════════════════════════════════
# Layout components
# ═══════════════════════════════════════════════════════════════════════════

def render_page_header(
    title: str,
    subtitle: str = "",
    icon: str | None = None,
) -> None:
    """Render a page-level title with optional subtitle and divider."""
    icon_str = f"{icon} " if icon else ""
    subtitle_html = (
        f'<p style="font-size:0.86rem;color:#8B7355;margin:0 0 6px 0;">{subtitle}</p>'
        if subtitle
        else ""
    )
    html = (
        f'<div style="margin-bottom:6px;">'
        f'<h1 style="font-size:1.55rem;font-weight:700;color:#3D2C20;margin:0 0 2px 0;">'
        f'{icon_str}{title}</h1>'
        f'{subtitle_html}'
        f'</div>'
        f'<hr style="border:none;border-top:1px solid #E8E0D5;margin:0 0 18px 0;">'
    )
    st.markdown(html, unsafe_allow_html=True)


_METRIC_STATUS = {
    "neutral": {"color": "#4A3728", "bg": "#FFFFFF", "border": "#E8E0D5"},
    "success": {"color": "#27AE60", "bg": "#E8F8F0", "border": "#E8E0D5"},
    "warning": {"color": "#E67E22", "bg": "#FEF5E7", "border": "#E8E0D5"},
    "danger":  {"color": "#C0392B", "bg": "#FDEDEC", "border": "#E8E0D5"},
    "info":    {"color": "#3498DB", "bg": "#EBF5FB", "border": "#E8E0D5"},
}


def render_metric_card(
    label: str,
    value,
    icon: str = "",
    delta: str | None = None,
    status: str = "neutral",
    color: str | None = None,
    bg_color: str | None = None,
) -> None:
    """Render a metric card with optional delta line.

    When *color* / *bg_color* are omitted, colours are derived from *status*
    (one of ``neutral``, ``success``, ``warning``, ``danger``, ``info``).
    """
    s = _METRIC_STATUS.get(status, _METRIC_STATUS["neutral"])
    c = color if color is not None else s["color"]
    bg = bg_color if bg_color is not None else s["bg"]
    border = s["border"]

    delta_html = (
        f'<div style="font-size:0.78rem;color:#8B7355;margin-top:4px;">{delta}</div>'
        if delta
        else ""
    )

    html = (
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-radius:14px;padding:18px 16px;text-align:center;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.08);">'
        f'<div style="font-size:0.78rem;color:#8B7355;font-weight:500;'
        f'margin-bottom:6px;letter-spacing:0.3px;">{icon}  {label}</div>'
        f'<div style="font-size:1.85rem;font-weight:700;color:{c};line-height:1.2;">'
        f'{value}</div>'
        f'{delta_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_section_title(
    title: str,
    subtitle: str | None = None,
    icon: str | None = None,
) -> None:
    """Render a card-internal section title with optional subtitle."""
    icon_str = f"{icon} " if icon else ""
    sub = (
        f'<div style="font-size:0.78rem;color:#A09080;margin-top:2px;">{subtitle}</div>'
        if subtitle
        else ""
    )
    html = (
        f'<div style="font-size:1rem;font-weight:700;color:#4A3728;'
        f'margin-bottom:12px;letter-spacing:0.2px;">{icon_str}{title}</div>'
        f'{sub}'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_empty_state(
    title: str,
    description: str,
    icon: str = "📭",
) -> None:
    """Render a centered empty-state placeholder."""
    html = (
        f'<div style="padding:48px 20px;text-align:center;">'
        f'<div style="font-size:2.5rem;margin-bottom:12px;">{icon}</div>'
        f'<div style="font-size:1.1rem;font-weight:600;color:#4A3728;'
        f'margin-bottom:8px;">{title}</div>'
        f'<div style="font-size:0.85rem;color:#A09080;">{description}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_progress_metric(
    label: str,
    value,
    target: str | None = None,
    status: str | None = None,
) -> None:
    """Render a compact ratio/percentage metric card.

    *value* is displayed prominently. *target* appears as a secondary line.
    *status* affects the value colour (success green, warning orange, etc.).
    """
    s = _METRIC_STATUS.get(status or "neutral", _METRIC_STATUS["neutral"])
    target_html = (
        f'<div style="font-size:0.65rem;color:#A09080;margin-top:2px;">{target}</div>'
        if target
        else ""
    )
    html = (
        f'<div style="background:#FFFFFF;border:1px solid #E8E0D5;'
        f'border-radius:10px;padding:14px;text-align:center;">'
        f'<div style="font-size:1.25rem;font-weight:700;color:{s["color"]};'
        f'margin-bottom:2px;">{value}</div>'
        f'<div style="font-size:0.7rem;color:#8B7355;">{label}</div>'
        f'{target_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_small_table(df, height: int | None = None) -> None:
    """Render a unified st.dataframe. Falls back to empty state for empty data."""
    try:
        if df is None or len(df) == 0:
            render_empty_state("暂无数据", "当前没有可显示的记录")
            return
    except Exception:
        render_empty_state("暂无数据", "当前没有可显示的记录")
        return

    kwargs = {"use_container_width": True, "hide_index": True}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


def format_latency(ms: float | int | None) -> str:
    """Format a latency value in milliseconds to a human-readable string.

    * <1     → "<1ms"
    * <1000  → "xxxms"
    * >=1000 → "x.xxs"
    * None / negative → "—"
    """
    if ms is None:
        return "—"
    try:
        v = float(ms)
    except (TypeError, ValueError):
        return "—"
    if v < 0:
        return "—"
    if v < 1:
        return "<1ms"
    if v < 1000:
        return f"{int(v)}ms"
    return f"{v / 1000:.2f}s"
