from __future__ import annotations

from contextlib import contextmanager

import streamlit as st


def render_two_column_layout(
    left_ratio: int = 7,
    right_ratio: int = 5,
    gap: str = "medium",
) -> tuple:
    """Return a two-column layout ``(left, right)`` from st.columns."""
    return st.columns([left_ratio, right_ratio], gap=gap)


@contextmanager
def render_card_container(
    title: str | None = None,
    subtitle: str | None = None,
    icon: str | None = None,
):
    """Context manager wrapping ``st.container(border=True)``.

    Optionally renders a card header (icon + title + subtitle) at the top.
    Falls back to a plain container when ``border=True`` is not available
    (Streamlit < 1.34).
    """
    try:
        container = st.container(border=True)
    except TypeError:
        container = st.container()

    with container:
        if title:
            _render_card_header(title, subtitle, icon)
        yield


def _render_card_header(
    title: str,
    subtitle: str | None = None,
    icon: str | None = None,
) -> None:
    icon_str = f"{icon} " if icon else ""
    sub = (
        f'<p style="font-size:0.78rem;color:#A09080;margin:-10px 0 0 0;">{subtitle}</p>'
        if subtitle
        else ""
    )
    html = (
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">'
        f'<span style="font-size:1rem;font-weight:700;color:#4A3728;">'
        f'{icon_str}{title}</span>'
        f'</div>'
        f'{sub}'
    )
    st.markdown(html, unsafe_allow_html=True)
