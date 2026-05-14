from __future__ import annotations

import pytest

from apps.streamlit_app.components.styles import STATUS_STYLES, get_color_palette
from apps.streamlit_app.components.ui_components import (
    format_latency,
    get_status_style,
    render_status_badge,
)


# ═══════════════════════════════════════════════════════════════════════════
# get_status_style
# ═══════════════════════════════════════════════════════════════════════════

class TestGetStatusStyle:
    def test_passed_returns_green(self):
        result = get_status_style("passed")
        assert result["color"] == "#27AE60"
        assert result["bg"] == "#E8F8F0"
        assert result["icon"] == "✓"
        assert result["label"] == "通过"

    def test_warning_returns_orange(self):
        result = get_status_style("warning")
        assert result["color"] == "#E67E22"
        assert result["bg"] == "#FEF5E7"
        assert result["icon"] == "⚠"
        assert result["label"] == "警告"

    def test_blocked_returns_red(self):
        result = get_status_style("blocked")
        assert result["color"] == "#C0392B"
        assert result["bg"] == "#FDEDEC"
        assert result["icon"] == "✗"
        assert result["label"] == "已拦截"

    def test_pending_returns_orange(self):
        result = get_status_style("pending")
        assert result["color"] == "#E67E22"
        assert result["label"] == "进行中"

    def test_approved_returns_green(self):
        result = get_status_style("approved")
        assert result["color"] == "#27AE60"

    def test_rewrite_required_returns_orange(self):
        result = get_status_style("rewrite_required")
        assert result["color"] == "#E67E22"
        assert result["label"] == "需修改"

    def test_failed_returns_red(self):
        result = get_status_style("failed")
        assert result["color"] == "#C0392B"

    def test_rejected_returns_red(self):
        result = get_status_style("rejected")
        assert result["color"] == "#C0392B"

    def test_unknown_status_falls_back_to_default(self):
        result = get_status_style("nonexistent_status")
        assert result == STATUS_STYLES["default"]
        assert result["color"] == "#8B7355"


# ═══════════════════════════════════════════════════════════════════════════
# format_latency
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatLatency:
    def test_none_returns_emdash(self):
        assert format_latency(None) == "—"

    def test_zero_returns_sub_ms(self):
        assert format_latency(0) == "<1ms"

    def test_negative_returns_emdash(self):
        assert format_latency(-5) == "—"

    def test_sub_millisecond(self):
        assert format_latency(0.5) == "<1ms"

    def test_100ms(self):
        assert format_latency(100) == "100ms"

    def test_500ms(self):
        assert format_latency(500) == "500ms"

    def test_999ms(self):
        assert format_latency(999) == "999ms"

    def test_1500ms_returns_seconds(self):
        assert format_latency(1500) == "1.50s"

    def test_1000ms_boundary(self):
        assert format_latency(1000) == "1.00s"

    def test_float_input(self):
        assert format_latency(1234.5) == "1.23s"

    def test_large_ms(self):
        assert format_latency(59300) == "59.30s"

    def test_string_input(self):
        assert format_latency("invalid") == "—"


# ═══════════════════════════════════════════════════════════════════════════
# get_color_palette
# ═══════════════════════════════════════════════════════════════════════════

class TestColorPalette:
    def test_returns_flat_dict(self):
        palette = get_color_palette()
        assert isinstance(palette, dict)

    def test_coffee_shades_present(self):
        palette = get_color_palette()
        assert palette["coffee_900"] == "#2C221B"
        assert palette["coffee_700"] == "#4A3728"
        assert palette["coffee_500"] == "#6B4C3B"
        assert palette["coffee_100"] == "#E8E0D5"
        assert palette["coffee_50"] == "#F5F0E8"

    def test_cream_present(self):
        palette = get_color_palette()
        assert palette["cream"] == "#FFFCF8"

    def test_functional_colors_present(self):
        palette = get_color_palette()
        assert palette["success_main"] == "#27AE60"
        assert palette["success_light"] == "#E8F8F0"
        assert palette["success_border"] == "#A9DFBF"
        assert palette["warning_main"] == "#E67E22"
        assert palette["danger_main"] == "#C0392B"
        assert palette["info_main"] == "#3498DB"

    def test_background_and_text_keys(self):
        palette = get_color_palette()
        assert palette["bg_page"] == "#FAFBF7"
        assert palette["bg_card"] == "#FFFFFF"
        assert palette["border_default"] == "#E8E0D5"
        assert palette["text_primary"] == "#3D2C20"
        assert palette["text_secondary"] == "#6B5B4F"
        assert palette["text_muted"] == "#A09080"

    def test_not_nested(self):
        palette = get_color_palette()
        assert "coffee" not in palette
        assert "success" not in palette
        assert isinstance(palette["coffee_900"], str)


# ═══════════════════════════════════════════════════════════════════════════
# render_status_badge
# ═══════════════════════════════════════════════════════════════════════════

class TestRenderStatusBadge:
    def test_returns_html_string(self):
        html = render_status_badge("passed")
        assert isinstance(html, str)
        assert "<span" in html

    def test_passed_contains_green_color(self):
        html = render_status_badge("passed")
        assert "#27AE60" in html

    def test_blocked_contains_red_color(self):
        html = render_status_badge("blocked")
        assert "#C0392B" in html

    def test_custom_label_overrides_default(self):
        html = render_status_badge("passed", label="OK")
        assert "OK" in html

    def test_warning_contains_orange(self):
        html = render_status_badge("warning")
        assert "#E67E22" in html

    def test_unknown_status_does_not_crash(self):
        html = render_status_badge("nonexistent")
        assert isinstance(html, str)
        assert "<span" in html


# ═══════════════════════════════════════════════════════════════════════════
# Import checks
# ═══════════════════════════════════════════════════════════════════════════

class TestImports:
    def test_all_public_symbols_importable(self):
        from apps.streamlit_app.components import (
            inject_global_styles,
            get_color_palette,
            get_status_style,
            get_severity_style,
            hex_to_rgba,
            render_status_badge,
            render_page_header,
            render_metric_card,
            render_section_title,
            render_empty_state,
            render_progress_metric,
            render_small_table,
            format_latency,
            render_two_column_layout,
            render_card_container,
            metric_card,
            render_sidebar,
            safe_html,
            translate_trace_detail,
        )
        assert callable(inject_global_styles)
        assert callable(render_metric_card)
        assert callable(format_latency)
        assert callable(metric_card)

    def test_legacy_metric_card_import_still_works(self):
        from apps.streamlit_app.components.metric_card import metric_card
        assert callable(metric_card)

    def test_format_latency_importable(self):
        assert callable(format_latency)
