"""Initialize the SQLite database by running all migrations. Idempotent."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from loguru import logger
from small_shop_agent.storage.database import execute_migrations, DB_PATH


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Initializing database at: {DB_PATH}")
    execute_migrations()
    logger.success(f"Database ready: {DB_PATH}")


if __name__ == "__main__":
    init_db()
