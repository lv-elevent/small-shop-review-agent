"""Public UI components for the Small Shop Review Agent Streamlit app."""

from apps.streamlit_app.components.styles import (
    inject_global_styles,
    get_color_palette,
    get_severity_style,
    hex_to_rgba,
)
from apps.streamlit_app.components.ui_components import (
    get_status_style,
    render_status_badge,
    render_page_header,
    render_metric_card,
    render_section_title,
    render_empty_state,
    render_progress_metric,
    render_small_table,
    format_latency,
)
from apps.streamlit_app.components.layout import (
    render_two_column_layout,
    render_card_container,
)
from apps.streamlit_app.components.metric_card import metric_card
from apps.streamlit_app.components.sidebar import render_sidebar
from apps.streamlit_app.components.ui_helpers import safe_html, translate_trace_detail

__all__ = [
    # styles
    "inject_global_styles",
    "get_color_palette",
    "get_severity_style",
    "hex_to_rgba",
    # ui_components
    "get_status_style",
    "render_status_badge",
    "render_page_header",
    "render_metric_card",
    "render_section_title",
    "render_empty_state",
    "render_progress_metric",
    "render_small_table",
    "format_latency",
    # layout
    "render_two_column_layout",
    "render_card_container",
    # legacy compat
    "metric_card",
    "render_sidebar",
    "safe_html",
    "translate_trace_detail",
]
