"""Application configuration."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "small_shop.db"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "storage" / "migrations"

CONFIG = {
    "db_path": str(DB_PATH),
    "data_dir": str(DATA_DIR),
    "migrations_dir": str(MIGRATIONS_DIR),
    "demo_mode_default": True,
    "max_retries": 1,
    "store_type": "coffee_shop",
}
