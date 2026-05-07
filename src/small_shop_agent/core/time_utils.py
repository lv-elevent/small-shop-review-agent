"""Timestamp helpers for the application."""
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def now_iso() -> str:
    """Return current local time as ISO 8601 string (for DB storage compatibility)."""
    return datetime.now().isoformat()
