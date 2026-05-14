"""
Reusable metric card component — legacy wrapper.

Delegates to ``ui_components.render_metric_card()`` for rendering.
Kept for backward compatibility with existing page imports.
"""

from __future__ import annotations
import streamlit as st

from apps.streamlit_app.components.ui_components import render_metric_card


def metric_card(
    label: str,
    value,
    icon: str = "",
    color: str = "#4A3728",
    bg_color: str = "#FFF8F5",
    warn: bool = False,
) -> None:
    """Render a metric card (legacy wrapper).

    Delegates to ``render_metric_card()``.
    """
    status = "warning" if warn else "neutral"
    render_metric_card(
        label=label,
        value=value,
        icon=icon,
        status=status,
        color=color,
        bg_color=bg_color,
    )
