"""
Upload Page — CSV Upload & Validation

生产版上传页
- 面向小店老板/店长：减少英文和专业术语，强调“上传评论表 -> 检查 -> 分析 -> 生成回复草稿”。
- 去除开发阶段 Demo 入口：页面只保留真实上传链路。
- 保持核心业务链路不变：CSV -> ReviewService.create_batch() -> WorkflowService/AgentRuntime。
"""

from __future__ import annotations

import io
import os
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from apps.streamlit_app.components import (
    inject_global_styles,
    render_page_header,
    render_metric_card,
    render_section_title,
    render_empty_state,
    render_small_table,
    render_two_column_layout,
    render_card_container,
    render_sidebar,
)
from small_shop_agent.services.review_service import ReviewService
from small_shop_agent.services.workflow_service import WorkflowService
from small_shop_agent.storage.database import execute_migrations
from small_shop_agent.utils.logger import ensure_logger_configured

execute_migrations()
ensure_logger_configured()

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="小店评论经营助手 · 上传评论",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ────────────────────────────────────────────────────────────
STORE_TYPES = ["咖啡店", "餐厅", "奶茶店", "便利店", "甜品店", "面包店", "小吃店", "其他"]
DEMO_CSV_PATH = _PROJECT_ROOT / "src" / "small_shop_agent" / "demo" / "sample_reviews.csv"

REQUIRED_COLUMNS = ["review_text", "rating"]
DATE_COLUMNS = ["date", "review_date", "review_time", "created_at"]
OPTIONAL_COLUMNS = ["review_id", "customer_name", "platform", "store_id", "order_id"]

COLUMN_LABELS = {
    "review_id": "评论编号",
    "rating": "评分",
    "review_text": "评论内容",
    "date": "评论日期",
    "review_date": "评论日期",
    "review_time": "评论时间",
    "created_at": "评论时间",
    "customer_name": "顾客昵称",
    "platform": "来源平台",
    "store_id": "门店编号",
    "order_id": "订单编号",
}


# ── Styling ──────────────────────────────────────────────────────────────
def _inject_upload_page_styles() -> None:
    """Inject upload-page-specific CSS after global styles."""
    st.markdown(
        """
        <style>
            :root {
                --coffee-950:#1E1510;
                --coffee-900:#2C221B;
                --coffee-800:#3D2C20;
                --coffee-700:#4A3728;
                --coffee-600:#5C3D2E;
                --coffee-500:#6B4C3B;
                --coffee-400:#8B7355;
                --coffee-300:#A09080;
                --coffee-200:#D4C4B0;
                --coffee-100:#E8E0D5;
                --coffee-50:#F5F0E8;
                --cream:#FFFCF8;
                --page-bg:#FAFBF7;
                --card:#FFFFFF;
                --success:#27AE60;
                --success-bg:#E8F8F0;
                --warning:#E67E22;
                --warning-bg:#FEF5E7;
                --danger:#C0392B;
                --danger-bg:#FDEDEC;
                --info:#3498DB;
                --info-bg:#EBF5FB;
            }

            html, body, [data-testid="stAppViewContainer"] {
                background: var(--page-bg) !important;
            }

            /* Hide Streamlit production-irrelevant chrome */
            #MainMenu, header[data-testid="stHeader"], footer {
                visibility: hidden !important;
                height: 0 !important;
            }

            .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"] {
                display: none !important;
            }

            section[data-testid="stSidebar"] {
                min-width: 238px !important;
                max-width: 238px !important;
                background: linear-gradient(180deg,#271D17 0%,#1B130F 100%) !important;
            }

            .stMain .block-container {
                padding-top: 1.35rem !important;
                padding-bottom: 2rem !important;
                padding-left: 2.55rem !important;
                padding-right: 2.55rem !important;
                max-width: 1440px !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 14px !important;
                border-color: var(--coffee-100) !important;
                box-shadow: 0 1px 4px rgba(0,0,0,.035) !important;
                background: var(--card) !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 1rem !important;
            }

            label, .stSelectbox label {
                font-weight: 850 !important;
                color: var(--coffee-700) !important;
                font-size: .82rem !important;
            }

            .stCaptionContainer, .stMarkdown p {
                color: var(--coffee-400);
            }

            .stButton > button,
            .stDownloadButton > button {
                border-radius: 11px !important;
                font-weight: 900 !important;
                min-height: 41px !important;
            }

            .stButton > button[kind="primary"],
            .stButton > button[data-testid="baseButton-primary"] {
                background: linear-gradient(135deg,var(--coffee-600),var(--coffee-800)) !important;
                border: 0 !important;
                box-shadow: 0 2px 8px rgba(74,55,40,.17) !important;
            }

            .stDownloadButton > button,
            .stButton > button[kind="secondary"],
            .stButton > button[data-testid="baseButton-secondary"] {
                border: 1px solid #BCA58A !important;
                color: var(--coffee-600) !important;
                background: #fff !important;
            }

            div[data-baseweb="select"] > div,
            div[data-testid="stSelectbox"] div[role="button"] {
                border-radius: 9px !important;
                border-color: var(--coffee-100) !important;
                background: #F7F8FA !important;
            }

            section[data-testid="stFileUploader"] {
                padding: 0 !important;
                border: none !important;
                background: transparent !important;
            }

            section[data-testid="stFileUploader"] label {
                display: none !important;
            }

            section[data-testid="stFileUploader"] div[data-testid="stFileUploaderDropzone"] {
                border: 2px dashed #D7C6B0 !important;
                border-radius: 14px !important;
                background: linear-gradient(180deg, #FFFCF8 0%, #FFF9F2 100%) !important;
                min-height: 168px !important;
                padding: 34px 18px 22px !important;
                align-items: center !important;
                justify-content: center !important;
                transition: all .22s ease !important;
            }

            section[data-testid="stFileUploader"] div[data-testid="stFileUploaderDropzone"]:hover {
                border-color: #9E7658 !important;
                box-shadow: 0 10px 24px rgba(107,76,59,.08) !important;
                transform: translateY(-1px);
            }

            section[data-testid="stFileUploader"] button {
                border-radius: 11px !important;
                background: linear-gradient(135deg,var(--coffee-600),var(--coffee-800)) !important;
                color: #fff !important;
                border: 0 !important;
                font-weight: 900 !important;
                padding: 0 25px !important;
                min-height: 41px !important;
                box-shadow: 0 2px 8px rgba(74,55,40,.17) !important;
            }

            section[data-testid="stFileUploader"] small,
            section[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
                color: var(--coffee-300) !important;
                font-size: .74rem !important;
            }

            section[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
                border-radius: 12px !important;
                border: 1px solid var(--coffee-100) !important;
                background: #F7F8FA !important;
            }

            section[data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"] {
                color: var(--coffee-700) !important;
                font-weight: 850 !important;
            }

            div[data-testid="stDataFrame"] {
                border-radius: 10px !important;
                overflow: hidden !important;
            }

            div[data-testid="stDataFrame"] th {
                background: var(--coffee-50) !important;
                color: var(--coffee-700) !important;
                font-size: .72rem !important;
                font-weight: 900 !important;
                padding: 8px 9px !important;
            }

            div[data-testid="stDataFrame"] td {
                font-size: .73rem !important;
                padding: 8px 9px !important;
                color: var(--coffee-700) !important;
            }

            details[data-testid="stExpander"] {
                border: 1px solid var(--coffee-100) !important;
                border-radius: 9px !important;
                background: #fff !important;
            }

            details[data-testid="stExpander"] summary {
                font-size: .77rem !important;
                font-weight: 850 !important;
                color: var(--coffee-700) !important;
                padding: 10px 13px !important;
            }

            .owner-flow-banner {
                display: grid;
                grid-template-columns: 1.2fr repeat(4, minmax(0, 1fr));
                gap: 8px;
                border: 1px solid var(--coffee-100);
                border-radius: 14px;
                background:
                    radial-gradient(circle at 98% 12%, rgba(201,168,121,.18), transparent 30%),
                    linear-gradient(135deg,#fff 0%,#FFFCF8 62%,#F6F0E8 100%);
                padding: 12px;
                margin-bottom: 16px;
                box-shadow: 0 1px 4px rgba(0,0,0,.025);
            }

            .owner-flow-intro {
                padding: 8px 10px;
            }

            .owner-flow-title {
                font-size: .94rem;
                font-weight: 950;
                color: var(--coffee-800);
                margin-bottom: 4px;
            }

            .owner-flow-desc {
                font-size: .72rem;
                color: var(--coffee-400);
                line-height: 1.55;
            }

            .owner-flow-step {
                border: 1px solid var(--coffee-100);
                border-radius: 12px;
                background: rgba(255,255,255,.72);
                padding: 10px 8px;
                min-height: 62px;
            }

            .owner-flow-step b {
                display: block;
                font-size: .78rem;
                color: var(--coffee-700);
                margin-bottom: 4px;
            }

            .owner-flow-step span {
                display: block;
                font-size: .68rem;
                color: var(--coffee-300);
                line-height: 1.35;
            }

            .source-card {
                border: 1px solid var(--coffee-100);
                border-radius: 14px;
                background: linear-gradient(180deg, #FFFCF8 0%, #FFFFFF 100%);
                padding: 14px;
                margin-bottom: 12px;
            }

            .source-card-head {
                display: flex;
                gap: 12px;
                align-items: flex-start;
            }

            .source-icon {
                width: 42px;
                height: 42px;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: #fff;
                color: var(--coffee-500);
                border: 1px solid var(--coffee-100);
                font-size: 1.25rem;
                flex: 0 0 auto;
                line-height: 1;
            }

            .source-title {
                font-size: .95rem;
                font-weight: 950;
                color: var(--coffee-700);
                margin: 1px 0 3px;
            }

            .source-desc {
                font-size: .74rem;
                color: var(--coffee-400);
                line-height: 1.58;
            }

            .hero-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 7px;
                margin-top: 10px;
            }

            .hero-chip,
            .stat-chip {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                border-radius: 999px;
                padding: 4px 9px;
                font-size: .68rem;
                font-weight: 850;
                border: 1px solid var(--coffee-100);
                background: rgba(255,255,255,.78);
                color: var(--coffee-500);
                white-space: nowrap;
            }

            .quick-action-box {
                border: 1px solid var(--coffee-100);
                border-radius: 12px;
                background: var(--cream);
                padding: 13px;
                font-size: .74rem;
                color: var(--coffee-500);
                line-height: 1.65;
                margin-top: 10px;
            }

            .pipeline-row {
                display: grid;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                gap: 6px;
                margin-top: 9px;
            }

            .pipeline-step {
                border: 1px solid var(--coffee-100);
                border-radius: 10px;
                background: #FFFFFF;
                padding: 8px 5px;
                text-align: center;
                font-size: .66rem;
                font-weight: 850;
                color: var(--coffee-500);
            }

            .check-list {
                display: flex;
                flex-direction: column;
                gap: 0;
            }

            .check-row {
                display: grid;
                grid-template-columns: 31px 1fr auto;
                align-items: center;
                gap: 8px;
                padding: 10px 0;
                border-bottom: 1px solid var(--coffee-50);
            }

            .check-row:last-child { border-bottom: none; }

            .check-icon {
                width: 28px;
                height: 28px;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 13px;
            }

            .check-label {
                font-size: .74rem;
                color: var(--coffee-400);
                font-weight: 850;
            }

            .check-value {
                font-size: 1.05rem;
                font-weight: 950;
                color: var(--coffee-700);
                white-space: nowrap;
            }

            .schema-list {
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin: 8px 0 12px 0;
            }

            .schema-row {
                display: grid;
                grid-template-columns: 88px 1fr;
                gap: 10px;
                align-items: start;
                padding: 10px;
                border-radius: 12px;
                background: var(--cream);
                border: 1px solid var(--coffee-100);
            }

            .schema-label {
                font-size: .72rem;
                font-weight: 950;
                color: var(--coffee-600);
            }

            .schema-content {
                font-size: .72rem;
                color: var(--coffee-500);
                line-height: 1.6;
            }

            .soft-note {
                border-radius: 12px;
                border: 1px solid var(--coffee-100);
                background: var(--cream);
                padding: 10px 12px;
                color: var(--coffee-500);
                font-size: .73rem;
                line-height: 1.6;
            }

            .preview-head-line {
                display:flex;
                justify-content:space-between;
                align-items:center;
                gap:12px;
                margin-bottom:10px;
            }

            .preview-count {
                color: var(--coffee-400);
                font-size: .73rem;
                white-space: nowrap;
                font-weight: 800;
            }

            .owner-empty-help {
                border: 1px dashed var(--coffee-200);
                border-radius: 13px;
                background: var(--cream);
                padding: 16px;
                color: var(--coffee-400);
                font-size: .76rem;
                line-height: 1.65;
            }

            .overview-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
                width: 100%;
            }

            .overview-card {
                min-width: 0;
                border: 1px solid var(--coffee-100);
                border-radius: 13px;
                background: #fff;
                padding: 12px 10px;
            }

            .overview-label {
                color: var(--coffee-400);
                font-size: .68rem;
                font-weight: 850;
                margin-bottom: 6px;
            }

            .overview-value {
                color: var(--coffee-800);
                font-size: 1.22rem;
                font-weight: 950;
                line-height: 1.1;
                overflow-wrap: anywhere;
            }

            .overview-date {
                font-size: .86rem;
                letter-spacing: -.3px;
            }

            .owner-plain-table-note {
                color: var(--coffee-300);
                font-size: .68rem;
                line-height: 1.45;
                margin-top: 8px;
            }

            @media (max-width: 1260px) {
                .stMain .block-container {
                    padding-left: 1.6rem !important;
                    padding-right: 1.6rem !important;
                }

                .owner-flow-banner {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                .owner-flow-intro {
                    grid-column: 1 / -1;
                }
            }

            @media (max-width: 980px) {
                .pipeline-row,
                .overview-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Data helpers ─────────────────────────────────────────────────────────
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _humanize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known technical columns to owner-friendly Chinese labels for display only."""
    return df.rename(columns={col: COLUMN_LABELS.get(col, col) for col in df.columns})


def _read_csv_preview(file_bytes: bytes) -> pd.DataFrame | None:
    """Parse CSV bytes for UI preview. Returns DataFrame or None."""
    for enc in ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]:
        try:
            return _normalize_columns(pd.read_csv(io.BytesIO(file_bytes), encoding=enc))
        except Exception:
            continue
    return None


@st.cache_data(show_spinner=False)
def _load_sample_dataframe() -> pd.DataFrame | None:
    """Load sample CSV for the downloadable template preview only."""
    try:
        return _normalize_columns(pd.read_csv(DEMO_CSV_PATH))
    except Exception:
        return None


def _safe_pop_state(*keys: str) -> None:
    """Remove session_state keys when present."""
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def _date_column(df: pd.DataFrame) -> str | None:
    """Return a known date-like column name."""
    for col in DATE_COLUMNS:
        if col in df.columns:
            return col
    return None


def _compute_preview_stats(df: pd.DataFrame | None) -> dict:
    """Compute lightweight UI-only validation stats from preview data."""
    if df is None or len(df) == 0:
        return {
            "total_rows": 0,
            "valid_review_count": 0,
            "empty_review_count": 0,
            "duplicate_count": 0,
            "invalid_rating_count": 0,
            "missing_required_columns": REQUIRED_COLUMNS.copy(),
            "missing_date_column": True,
            "avg_rating": "-",
            "platform_count": "-",
            "earliest_date": "-",
            "latest_date": "-",
            "low_rating_count": 0,
            "low_rating_rate": "-",
        }

    total = len(df)
    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    missing_date_column = _date_column(df) is None

    if "review_text" in df.columns:
        text_series = df["review_text"].fillna("").astype(str).str.strip()
        empty_review_count = int((text_series == "").sum())
        duplicate_count = int(text_series[text_series != ""].duplicated().sum())
    else:
        empty_review_count = total
        duplicate_count = 0

    invalid_rating_count = 0
    avg_rating: str | float = "-"
    low_rating_count = 0
    low_rating_rate = "-"

    if "rating" in df.columns:
        rating = pd.to_numeric(df["rating"], errors="coerce")
        invalid_rating_count = int((rating.isna() | (rating < 1) | (rating > 5)).sum())
        valid_rating = rating.dropna()
        valid_rating = valid_rating[(valid_rating >= 1) & (valid_rating <= 5)]
        if len(valid_rating) > 0:
            avg_rating = f"{valid_rating.mean():.1f}"
            low_rating_count = int((valid_rating <= 2).sum())
            low_rating_rate = f"{low_rating_count / max(len(valid_rating), 1) * 100:.0f}%"
    else:
        invalid_rating_count = total

    issue_count = empty_review_count + invalid_rating_count + duplicate_count
    valid_review_count = 0 if missing_required else max(total - issue_count, 0)

    platform_count = "-"
    if "platform" in df.columns:
        try:
            platform_count = str(
                df["platform"]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )
        except Exception:
            platform_count = "-"

    earliest_date = "-"
    latest_date = "-"
    date_col = _date_column(df)
    if date_col:
        parsed = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(parsed) > 0:
            earliest_date = parsed.min().strftime("%Y-%m-%d")
            latest_date = parsed.max().strftime("%Y-%m-%d")

    return {
        "total_rows": total,
        "valid_review_count": valid_review_count,
        "empty_review_count": empty_review_count,
        "duplicate_count": duplicate_count,
        "invalid_rating_count": invalid_rating_count,
        "missing_required_columns": missing_required,
        "missing_date_column": missing_date_column,
        "avg_rating": avg_rating,
        "platform_count": platform_count,
        "earliest_date": earliest_date,
        "latest_date": latest_date,
        "low_rating_count": low_rating_count,
        "low_rating_rate": low_rating_rate,
    }


def _display_columns(df: pd.DataFrame) -> list[str]:
    """Pick compact columns for preview tables."""
    preferred = [
        "review_id",
        "rating",
        "review_text",
        "date",
        "review_date",
        "review_time",
        "customer_name",
        "platform",
    ]
    cols = [c for c in preferred if c in df.columns]
    return cols or list(df.columns)


def _quality_label(stats: dict) -> tuple[str, str]:
    """Return UI status key and Chinese label for current preview data."""
    total = stats.get("total_rows", 0)
    valid = stats.get("valid_review_count", 0)
    missing = stats.get("missing_required_columns", [])
    issue_count = (
        stats.get("empty_review_count", 0)
        + stats.get("duplicate_count", 0)
        + stats.get("invalid_rating_count", 0)
    )

    if not total:
        return "neutral", "等待上传"
    if missing:
        return "danger", "缺少字段"
    if valid == total:
        return "success", "可以分析"
    if valid > 0 and issue_count > 0:
        return "warning", "部分可用"
    return "danger", "需要调整"


# ── UI helpers ───────────────────────────────────────────────────────────
def _status_colors(status: str) -> tuple[str, str]:
    if status == "success":
        return "#E8F8F0", "#27AE60"
    if status == "warning":
        return "#FEF5E7", "#E67E22"
    if status == "danger":
        return "#FDEDEC", "#C0392B"
    if status == "info":
        return "#EBF5FB", "#3498DB"
    return "#F5F0E8", "#6B4C3B"


def _chip(label: str, status: str = "neutral") -> str:
    bg, fg = _status_colors(status)
    return f'<span class="stat-chip" style="background:{bg};color:{fg};">{label}</span>'


def _render_upload_hero() -> None:
    """Render compact owner-oriented flow banner."""
    st.markdown(
        """
        <div class="owner-flow-banner">
            <div class="owner-flow-intro">
                <div class="owner-flow-title">上传评论表，系统帮你整理顾客反馈</div>
                <div class="owner-flow-desc">把美团、大众点评、门店问卷等评论集中导入，快速看出顾客最不满意什么、哪些地方值得保持、哪些评论需要优先回复。</div>
            </div>
            <div class="owner-flow-step"><b>1. 上传表格</b><span>导入平台评论</span></div>
            <div class="owner-flow-step"><b>2. 自动检查</b><span>内容、评分、空行</span></div>
            <div class="owner-flow-step"><b>3. 找出问题</b><span>差评原因与高频主题</span></div>
            <div class="owner-flow-step"><b>4. 生成回复</b><span>草稿先审核再使用</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_source_card(
    *,
    icon: str,
    title: str,
    description: str,
    chips: list[tuple[str, str]] | None = None,
) -> None:
    chips_html = "".join(_chip(text, status) for text, status in (chips or []))
    chip_row = f'<div class="hero-chip-row">{chips_html}</div>' if chips_html else ""
    st.markdown(
        f"""
        <div class="source-card">
            <div class="source-card-head">
                <div class="source-icon">{icon}</div>
                <div>
                    <div class="source-title">{title}</div>
                    <div class="source-desc">{description}</div>
                    {chip_row}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_upload_source_card() -> None:
    """Render upload guidance above Streamlit file uploader."""
    _render_source_card(
        icon="📄",
        title="上传评论表",
        description="把平台导出的评论表拖到这里。表格里至少需要有评论内容和评分，最好也带上评论日期。",
        chips=[
            ("需要：评论内容", "neutral"),
            ("需要：评分", "neutral"),
            ("建议：评论日期", "neutral"),
            ("文件格式：CSV", "info"),
        ],
    )


def _render_pipeline_hint() -> None:
    st.markdown(
        """
        <div class="quick-action-box">
            <b>点击后系统会自动完成：</b>
            <div class="pipeline-row">
                <div class="pipeline-step">读评论</div>
                <div class="pipeline-step">分主题</div>
                <div class="pipeline-step">看情绪</div>
                <div class="pipeline-step">找问题</div>
                <div class="pipeline-step">写回复</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_check_rows(rows: list[tuple[str, str, str, str]]) -> None:
    """Render compact validation rows: (icon, label, value, status)."""
    row_html = '<div class="check-list">'
    for icon, label, value, status in rows:
        bg, fg = _status_colors(status)
        row_html += (
            f'<div class="check-row">'
            f'<div class="check-icon" style="background:{bg};color:{fg};">{icon}</div>'
            f'<div class="check-label">{label}</div>'
            f'<div class="check-value">{value}</div>'
            f'</div>'
        )
    row_html += "</div>"
    st.markdown(row_html, unsafe_allow_html=True)


def _render_validation_panel(stats: dict) -> None:
    """Render compact validation panel."""
    total = stats.get("total_rows", 0)
    valid = stats.get("valid_review_count", 0)
    duplicate = stats.get("duplicate_count", 0)
    empty = stats.get("empty_review_count", 0)
    invalid_rating = stats.get("invalid_rating_count", 0)
    missing_cols = stats.get("missing_required_columns", [])
    issue_count = duplicate + empty + invalid_rating

    valid_pct = f"({valid / total * 100:.0f}%)" if total else ""
    issue_pct = f"({issue_count / total * 100:.0f}%)" if total else ""
    quality_status, quality_text = _quality_label(stats)

    render_section_title("表格检查结果", subtitle="先帮你看看这份表能不能分析。", icon="🧩")
    _render_check_rows(
        rows=[
            ("📝", "总评论数", str(total), "neutral"),
            (
                "✅",
                "可分析评论",
                f"{valid} {valid_pct}".strip(),
                "success" if total and valid == total else "warning" if valid else "neutral",
            ),
            (
                "⚠️",
                "需要处理",
                f"{issue_count} {issue_pct}".strip(),
                "warning" if issue_count else "neutral",
            ),
            ("🧱", "表格状态", quality_text, quality_status),
        ]
    )

    with st.expander("查看检查详情"):
        if missing_cols:
            readable = [COLUMN_LABELS.get(col, col) for col in missing_cols]
            st.error(f"缺少必填内容：{', '.join(readable)}")
        if stats.get("missing_date_column"):
            st.warning("没有识别到评论日期。建议补上日期，方便后续查看趋势。")
        st.caption(
            f"总 {total} 条 · 可分析 {valid} 条 · 重复 {duplicate} 条 · 空评论 {empty} 条 · 评分异常 {invalid_rating} 条"
        )


def _render_service_validation_results(stats: dict) -> None:
    """Render authoritative validation result as compact rows."""
    valid = stats.get("valid_review_count", 0)
    total = stats.get("total_rows", 0)
    duplicate = stats.get("duplicate_count", 0)
    empty = stats.get("empty_review_count", 0)
    invalid_rating = stats.get("invalid_rating_count", 0)
    issue_count = empty + invalid_rating

    with render_card_container(title="📊 上传检查结果"):
        _render_check_rows(
            rows=[
                ("📝", "总评论数", str(total), "neutral"),
                (
                    "✅",
                    "进入分析",
                    str(valid),
                    "success" if valid == total and total > 0 else "warning" if valid > 0 else "danger",
                ),
                ("🔄", "重复评论", str(duplicate), "warning" if duplicate > 0 else "neutral"),
                ("⚠️", "需处理", str(issue_count), "danger" if issue_count > 0 else "neutral"),
            ]
        )

        if valid == total and total > 0:
            st.success(f"✅ 全部 {total} 条评论已通过检查，正在进入分析流程。")
        elif valid > 0:
            parts = []
            if duplicate:
                parts.append(f"{duplicate} 条重复")
            if empty:
                parts.append(f"{empty} 条空评论")
            if invalid_rating:
                parts.append(f"{invalid_rating} 条评分异常")
            st.warning(f"⚠️ 共 {total} 条，{valid} 条可分析。{', '.join(parts)}。系统会自动过滤问题数据。")
        else:
            st.error("❌ 没有识别到可分析的评论，请检查表格内容。")


def _render_data_overview(df: pd.DataFrame) -> None:
    """Render data overview. Uses one safe HTML block to avoid leaked raw HTML fragments."""
    stats = _compute_preview_stats(df)
    items = [
        ("总评论", stats["total_rows"], ""),
        ("平均评分", stats["avg_rating"], ""),
        ("低分评论", stats["low_rating_count"], ""),
        ("来源平台", stats["platform_count"], ""),
        ("最早评论", stats["earliest_date"], "overview-date"),
        ("低分占比", stats["low_rating_rate"], ""),
    ]
    cards = "".join(
        f"""
        <div class="overview-card">
            <div class="overview-label">{label}</div>
            <div class="overview-value {extra_class}">{value}</div>
        </div>
        """
        for label, value, extra_class in items
    )
    st.markdown(f'<div class="overview-grid">{cards}</div>', unsafe_allow_html=True)


def _render_data_preview(uploaded_df: pd.DataFrame | None) -> None:
    """Render uploaded dataframe preview."""
    has_data = isinstance(uploaded_df, pd.DataFrame) and len(uploaded_df) > 0

    if not has_data:
        with render_card_container(title="📋 表格预览"):
            st.markdown(
                """
                <div class="owner-empty-help">
                    暂无评论数据。请先上传评论表，上传后这里会显示前几条评论，方便你确认表格是否正确。
                </div>
                """,
                unsafe_allow_html=True,
            )
        return

    display_cols = _display_columns(uploaded_df)
    preview_df = _humanize_columns(uploaded_df[display_cols])

    with render_card_container(title="📋 表格预览"):
        stats = _compute_preview_stats(uploaded_df)
        quality_status, quality_text = _quality_label(stats)
        st.markdown(
            f"""
            <div class="preview-head-line">
                <div class="hero-chip-row" style="margin-top:0;">
                    {_chip(f"共 {len(uploaded_df)} 条", "neutral")}
                    {_chip(f"{quality_text}", quality_status)}
                    {_chip(f"平均评分 {stats['avg_rating']}", "info")}
                </div>
                <div class="preview-count">预览前 5 条</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_small_table(preview_df.head(5))
        st.caption("💡 这里只展示前 5 条；点击开始分析后会处理全部评论。")
        with st.expander("查看完整表格"):
            render_small_table(preview_df, height=360)


def _render_schema_guide() -> None:
    """Render CSV schema guide with owner-friendly wording."""
    st.markdown(
        """
        <div class="schema-list">
            <div class="schema-row">
                <div class="schema-label">必须有</div>
                <div class="schema-content">评论内容：顾客写的评价<br>评分：1 到 5 分</div>
            </div>
            <div class="schema-row">
                <div class="schema-label">建议有</div>
                <div class="schema-content">评论日期：用于查看不同时间段的反馈变化</div>
            </div>
            <div class="schema-row">
                <div class="schema-label">可选</div>
                <div class="schema-content">顾客昵称、来源平台、订单编号、门店编号等</div>
            </div>
        </div>
        <div class="soft-note">小提示：如果你的表格来自平台导出，通常只要包含“评论内容”和“评分”就可以先上传。系统会自动识别常见字段名。</div>
        """,
        unsafe_allow_html=True,
    )


# ── Business flow ────────────────────────────────────────────────────────
def _run_analysis(
    *,
    rs: ReviewService,
    ws: WorkflowService,
    store_type: str,
    llm_mode: str,
    workflow_runtime: str,
) -> None:
    """Create batch, run analysis and render result cards. Business flow unchanged."""
    with st.spinner("正在检查并上传评论表 …"):
        result = rs.create_batch(
            st.session_state.get("_uploaded_bytes", b""),
            store_type=store_type,
            file_name=st.session_state.get("_file_name", "upload.csv"),
        )

    if not result["success"]:
        st.error(f"❌ 上传失败：{result.get('message', '未知错误')}")
        return

    st.session_state.latest_validation_result = result["validation"]
    st.session_state.current_batch_id = result["batch_id"]
    st.query_params["batch_id"] = result["batch_id"]

    _render_service_validation_results(result["validation"])

    with st.spinner("正在分析顾客反馈，并生成经营建议和回复草稿 …"):
        if workflow_runtime == "agent_graph":
            from small_shop_agent.agent_runtime.runner import run_with_agent_runtime

            agent_state = run_with_agent_runtime(result["batch_id"], mode=llm_mode)
            errs = agent_state.get("errors", [])
            review_count = len(agent_state.get("reviews", []))
            wf_result = {
                "success": len(errs) == 0,
                "batch_id": result["batch_id"],
                "mode": llm_mode,
                "summary": {
                    "review_count": review_count,
                    "negative_count": agent_state.get("_negative_count", 0),
                    "insight_count": agent_state.get("_insight_count", 0),
                    "draft_count": agent_state.get("_draft_count", 0),
                    "blocked_count": agent_state.get("_blocked_count", 0),
                    "evidence_count": agent_state.get("_evidence_count", 0),
                    "pass_count": agent_state.get("_pass_count", 0),
                    "trace_count": 9,
                },
                "error": errs[0]["message"] if errs else None,
            }
        else:
            wf_result = ws.run_analysis(result["batch_id"], mode=llm_mode)

    st.session_state.latest_workflow_result = wf_result

    with render_card_container(title="✅ 分析完成"):
        if wf_result["success"]:
            summary = wf_result["summary"]
            result_cols = st.columns(4)
            with result_cols[0]:
                render_metric_card("评论数", summary.get("review_count", "-"), icon="📝", status="neutral")
            with result_cols[1]:
                render_metric_card("经营洞察", summary.get("insight_count", "-"), icon="💡", status="success")
            with result_cols[2]:
                render_metric_card("回复草稿", summary.get("draft_count", "-"), icon="✏️", status="success")
            with result_cols[3]:
                blocked = summary.get("blocked_count", 0)
                render_metric_card("需人工处理", blocked, icon="🛡️", status="danger" if blocked else "neutral")

            st.success(
                f"✅ 已分析 {summary.get('review_count', '?')} 条评论，"
                f"整理出 {summary.get('insight_count', '?')} 个经营洞察，"
                f"生成 {summary.get('draft_count', '?')} 条回复草稿。"
            )
            if summary.get("blocked_count", 0) > 0:
                st.warning(f"⚠️ {summary['blocked_count']} 条回复需要人工再确认。")
            st.info("👉 下一步：去「数据看板」查看问题和趋势，或去「回复审核」确认回复草稿。")
        else:
            st.error(f"❌ 分析失败：{wf_result.get('error', '未知错误')}")


def _render_recent_analysis() -> None:
    """Render latest successful workflow summary."""
    wf_result = st.session_state.get("latest_workflow_result")
    if not wf_result or not wf_result.get("success"):
        return

    summary = wf_result["summary"]
    with render_card_container(title="📌 最近一次分析"):
        st.success(
            f"已分析 {summary.get('review_count', '?')} 条评论，"
            f"发现 {summary.get('insight_count', '?')} 个经营洞察，"
            f"生成 {summary.get('draft_count', '?')} 条回复草稿。"
        )


# ── Main Page ────────────────────────────────────────────────────────────
def main() -> None:
    """Render upload page."""
    inject_global_styles()
    _inject_upload_page_styles()

    st.session_state.nav_selection = "上传评论"
    render_sidebar()

    rs = ReviewService()
    ws = WorkflowService()

    from small_shop_agent.core.config import WORKFLOW_RUNTIME

    workflow_runtime = WORKFLOW_RUNTIME
    # 生产页面不暴露模型/运行模式给老板；如需切换，请通过环境变量控制。
    llm_mode = os.environ.get("LLM_MODE", "live")

    render_page_header(
        title="上传评论数据",
        subtitle="上传顾客评论表，系统会自动找出问题、生成经营洞察和回复草稿。",
        icon="📤",
    )
    _render_upload_hero()

    left_col, right_col = render_two_column_layout(left_ratio=7, right_ratio=4, gap="medium")

    start_clicked = False

    with left_col:
        with render_card_container(title="⚙️ 基本信息"):
            cfg_store, cfg_note = st.columns([1, 1.6], gap="medium")
            with cfg_store:
                store_type = st.selectbox(
                    "🏪 店铺类型",
                    options=STORE_TYPES,
                    index=0,
                    key="store_type",
                    help="选择店铺类型后，系统会匹配更合适的分析维度和回复语气。",
                )
            with cfg_note:
                st.markdown(
                    """
                    <div class="owner-empty-help" style="padding:12px 14px;">
                        建议上传最近 1-3 个月的评论。评论越集中，越容易看出近期服务、口味、出餐和环境方面的问题。
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        op_left, op_right = st.columns([7, 2.25], gap="medium")

        with op_left:
            with render_card_container(title="📁 数据来源"):
                _render_upload_source_card()
                uploaded_file = st.file_uploader(
                    "上传评论表",
                    type=["csv"],
                    accept_multiple_files=False,
                    key="csv_uploader",
                    label_visibility="collapsed",
                )
                if uploaded_file is not None:
                    file_bytes = uploaded_file.getvalue()
                    df = _read_csv_preview(file_bytes)
                    if df is None:
                        st.error("❌ 无法读取这份表格。请确认是 CSV 文件，或换一种编码重新导出。")
                        st.session_state.uploaded_df = None
                        _safe_pop_state("_uploaded_bytes", "_file_name", "_data_source")
                    elif len(df) == 0:
                        st.error("❌ 这份表格是空的，请上传包含评论的数据。")
                        st.session_state.uploaded_df = None
                        _safe_pop_state("_uploaded_bytes", "_file_name", "_data_source")
                    else:
                        st.session_state.uploaded_df = df
                        st.session_state._uploaded_bytes = file_bytes
                        st.session_state._file_name = uploaded_file.name
                        st.session_state._data_source = "upload"
                        st.toast(f"✅ 上传成功！已读取 {len(df)} 条记录。")

            uploaded_df = st.session_state.get("uploaded_df")
            _render_data_preview(uploaded_df)

        with op_right:
            current_df = st.session_state.get("uploaded_df")
            has_current_data = isinstance(current_df, pd.DataFrame) and len(current_df) > 0

            with render_card_container(title="🚀 开始分析"):
                start_clicked = st.button(
                    "开始分析",
                    type="primary",
                    use_container_width=True,
                    disabled=not has_current_data,
                    key="start_analysis",
                )
                _render_pipeline_hint()

            with render_card_container():
                if has_current_data:
                    _render_validation_panel(_compute_preview_stats(current_df))
                else:
                    render_section_title("表格检查结果", subtitle="上传表格后会自动检查。", icon="🧩")
                    st.markdown(
                        """
                        <div class="owner-empty-help">
                            等待上传。上传后这里会显示总评论数、可分析评论和需要处理的数据。
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        current_df = st.session_state.get("uploaded_df")
        if start_clicked and isinstance(current_df, pd.DataFrame) and len(current_df) > 0:
            _run_analysis(
                rs=rs,
                ws=ws,
                store_type=store_type,
                llm_mode=llm_mode,
                workflow_runtime=workflow_runtime,
            )
        elif not start_clicked:
            _render_recent_analysis()

    with right_col:
        tab_format, tab_template, tab_overview = st.tabs(["表格要求", "示例格式", "当前概况"])

        with tab_format:
            with render_card_container():
                render_section_title("表格需要包含什么", subtitle="按下面内容准备，系统更容易识别。", icon="📋")
                _render_schema_guide()
                try:
                    sample_bytes = DEMO_CSV_PATH.read_bytes()
                    st.download_button(
                        "⬇ 下载表格模板",
                        data=sample_bytes,
                        file_name="评论表模板.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                except Exception:
                    st.info("模板暂时不可下载，请按上面的说明准备表格。")

        with tab_template:
            with render_card_container():
                render_section_title("示例格式", subtitle="只用于说明表格长什么样，不会自动参与分析。", icon="📄")
                sample_df = _load_sample_dataframe()
                if sample_df is not None:
                    sample_preview = _humanize_columns(sample_df[_display_columns(sample_df)].head(5))
                    render_small_table(sample_preview)
                    st.markdown(
                        """
                        <div class="owner-plain-table-note">
                            说明：你的实际表格不一定要和示例完全一样，只要能识别出评论内容和评分即可。
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    render_empty_state("无法加载示例格式", "请按“表格要求”准备评论表。", icon="📭")

        with tab_overview:
            with render_card_container():
                render_section_title("当前概况", subtitle="上传表格后实时统计。", icon="📈")
                current_df = st.session_state.get("uploaded_df")
                if isinstance(current_df, pd.DataFrame) and len(current_df) > 0:
                    _render_data_overview(current_df)
                else:
                    st.markdown(
                        """
                        <div class="owner-empty-help">
                            暂无数据。上传表格后，这里会显示总评论、平均评分、低分评论和来源平台数量。
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


if __name__ == "__main__":
    main()
