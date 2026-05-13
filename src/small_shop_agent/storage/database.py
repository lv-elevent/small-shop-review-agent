"""SQLite connection management and migration runner."""
import sqlite3
from pathlib import Path
from loguru import logger

from small_shop_agent.core.config import DB_PATH, MIGRATIONS_DIR


def ensure_data_dir() -> None:
    """Create the data directory if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with WAL mode, foreign keys, and row_factory."""
    ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def execute_script(script_path: Path) -> None:
    """Execute a single SQL file."""
    if not script_path.exists():
        logger.error(f"SQL 文件未找到：{script_path}")
        return
    with get_connection() as conn:
        script = script_path.read_text(encoding="utf-8")
        conn.executescript(script)
        logger.debug(f"Executed: {script_path.name}")


def execute_migrations(migrations_dir: Path | None = None) -> None:
    """Run all .sql migration files in sorted order. Idempotent via IF NOT EXISTS.

    Also ensures file logging is configured (idempotent global init).
    """
    from small_shop_agent.utils.logger import ensure_logger_configured
    ensure_logger_configured()

    folder = migrations_dir or MIGRATIONS_DIR
    if not folder.exists():
        logger.error(f"迁移文件夹未找到：{folder}")
        return
    sql_files = sorted(folder.glob("*.sql"))
    for f in sql_files:
        execute_script(f)
    logger.debug(f"Applied {len(sql_files)} migrations.")
