"""Context manager for SQLite sessions with auto-commit/rollback."""
from contextlib import contextmanager
from collections.abc import Generator
from sqlite3 import Connection

from .database import get_connection


@contextmanager
def get_session() -> Generator[Connection, None, None]:
    """Yield a connection; commit on success, rollback on exception, close always."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
