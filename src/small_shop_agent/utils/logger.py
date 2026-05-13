"""Structured JSON-style step logger for workflow tracing."""
from __future__ import annotations

import json
from typing import Any

from loguru import logger

_logger_configured = False


def log_step(
    step_name: str,
    batch_id: str,
    review_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Emit a JSON-structured log entry for a workflow step.

    Args:
        step_name: e.g. "classification", "sentiment_analysis"
        batch_id:  batch identifier
        review_id: review identifier (optional, for per-review logs)
        **kwargs:  extra fields (fallback_used, attempt_num, status, latency_ms, etc.)
    """
    entry: dict[str, Any] = {"step": step_name, "batch_id": batch_id}
    if review_id:
        entry["review_id"] = review_id
    entry.update(kwargs)
    logger.debug(json.dumps(entry, ensure_ascii=False, default=str))


def ensure_logger_configured() -> None:
    """Idempotent: add file sink to loguru if not already done.

    Call once at module load time in each Streamlit entry point.
    Writes DEBUG-level logs to data/app.log with rotation.
    """
    global _logger_configured
    if _logger_configured:
        return
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[3] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        data_dir / "app.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )
    _logger_configured = True
