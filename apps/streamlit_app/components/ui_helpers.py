"""Shared UI helper utilities for Streamlit pages."""
from __future__ import annotations

import html as _html
import re


def safe_html(text: object) -> str:
    """Escape user-provided text for safe use in st.markdown(unsafe_allow_html=True)."""
    if not isinstance(text, str):
        text = str(text)
    return _html.escape(text)


def translate_trace_detail(raw: str) -> str:
    """Translate common English trace output_summary fragments to Chinese."""
    s = raw
    # Specific patterns first, generic patterns last (ordering matters)
    s = re.sub(r"(\d+) valid reviews?", r"\1 条有效评论", s)
    s = re.sub(r"(\d+) raw reviews?", r"\1 条原始评论", s)
    s = s.replace("verified; no duplicates detected", "已校验；未发现重复")
    s = re.sub(r"(\d+) pass, (\d+) rewrite_required, (\d+) blocked",
               r"通过 \1 条，需重写 \2 条，拦截 \3 条", s)
    s = re.sub(r"(\d+) evidence; (\d+) valid, (\d+) rejected/insufficient",
               r"共 \1 条证据；\2 条有效，\3 条不足", s)
    s = re.sub(r"(\d+) evidence records across (\d+) issues",
               r"\1 条证据记录（\2 个问题）", s)
    s = re.sub(r"(\d+) drafts generated", r"\1 条草稿已生成", s)
    s = re.sub(r"(\d+) negative candidates", r"\1 条差评", s)
    s = re.sub(r"(\d+) classified", r"\1 条已分类", s)
    s = re.sub(r"(\d+) analyzed", r"\1 条已分析", s)
    s = re.sub(r"(\d+) drafts", r"\1 条草稿", s)
    s = re.sub(r"(\d+) insights", r"\1 个洞察", s)
    s = re.sub(r"(\d+) evidence", r"\1 条证据", s)
    s = re.sub(r"(\d+) reviews", r"\1 条评论", s)
    return s
