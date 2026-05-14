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
    """Translate common English trace detail fragments to owner-readable Chinese."""
    s = raw
    # Remove provider/model/simulated prefixes
    s = re.sub(r"\bprovider=[^\s,;]+", "", s)
    s = re.sub(r"\bmodel=[^\s,;]+", "", s)
    s = re.sub(r"\bmodel_name=[^\s,;]+", "", s)
    s = re.sub(r"\bsimulated[^\s,;]*", "评论表", s)
    s = re.sub(r"\b\d+ rows?\b", lambda m: m.group().replace("rows", "条评论").replace("row", "条评论"), s)
    # Numeric patterns
    s = re.sub(r"\battempts=(\d+)", r"已自动处理 \1 次", s)
    s = re.sub(r"\bused_fallback\s*=\s*False\b", "", s)
    s = re.sub(r"\bused_fallback\s*=\s*True\b", "已使用备用方案", s)
    s = re.sub(r"\bfallback\s*=\s*False\b", "", s)
    s = re.sub(r"\bfallback\s*=\s*True\b", "已使用备用方案", s)
    s = re.sub(r"\bschema_errors?\s*=\s*0\b", "表格格式正常", s)
    s = re.sub(r"\bschema_errors?\s*=\s*(\d+)", r"格式问题 \1 条", s)
    s = re.sub(r"\bvalid\s*=\s*(\d+)", r"可分析 \1 条", s)
    s = re.sub(r"\binvalid_rating\s*=\s*(\d+)", r"评分异常 \1 条", s)
    s = re.sub(r"\bduplicate_count\s*=\s*(\d+)", r"重复 \1 条", s)
    s = re.sub(r"\bempty_review_count\s*=\s*(\d+)", r"空评论 \1 条", s)
    s = re.sub(r"\bnegative_count\s*=\s*(\d+)", r"差评 \1 条", s)
    s = re.sub(r"\bpass_count\s*=\s*(\d+)", r"通过 \1 条", s)
    s = re.sub(r"\bblocked_count\s*=\s*(\d+)", r"拦截 \1 条", s)
    s = re.sub(r"\brewrite_required_count\s*=\s*(\d+)", r"需重写 \1 条", s)
    s = re.sub(r"\binsight_count\s*=\s*(\d+)", r"经营洞察 \1 个", s)
    s = re.sub(r"\bdraft_count\s*=\s*(\d+)", r"回复草稿 \1 条", s)
    s = re.sub(r"\bevidence_count\s*=\s*(\d+)", r"证据 \1 条", s)
    s = re.sub(r"\breview_count\s*=\s*(\d+)", r"已分析 \1 条", s)
    s = re.sub(r"\brejected_issues_count\s*=\s*(\d+)", r"已剔除 \1 个问题", s)
    # Generic translations
    s = re.sub(r"(\d+) valid reviews?", r"\1 条可分析评论", s)
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
    s = re.sub(r"(\d+) analyses", r"\1 条分析结果", s)
    s = re.sub(r"(\d+) drafts", r"\1 条草稿", s)
    s = re.sub(r"(\d+) insights", r"\1 个洞察", s)
    s = re.sub(r"(\d+) evidence", r"\1 条证据", s)
    s = re.sub(r"(\d+) reviews", r"\1 条评论", s)
    # Collapse multi-space
    s = " ".join(s.split())
    return s
