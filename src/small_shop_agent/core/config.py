"""Application configuration — single source of truth for all tunable parameters."""
from __future__ import annotations
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "small_shop.db"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "storage" / "migrations"
LOG_FILE = DATA_DIR / "app.log"

# ── LLM ─────────────────────────────────────────────────────────
LLM_MAX_RETRIES: int = 1
LLM_TEMPERATURE: float = 0.3
LLM_TIMEOUT_SECONDS: int = 30

# ── Evidence ────────────────────────────────────────────────────
MIN_EVIDENCE_COUNT: int = 2

# ── Consistency Check ──────────────────────────────────────────
CONSISTENCY_CONFIDENCE_FACTOR: float = 0.5  # multiply confidence by this when conflict detected

# ── CSV ─────────────────────────────────────────────────────────
DEFAULT_RATING_WHEN_INVALID: int = 3
CSV_MAX_SIZE_MB: int = 10

# ── Demo ────────────────────────────────────────────────────────
DEMO_MODE_DEFAULT: bool = True
DEMO_STORE_TYPE: str = "coffee_shop"

# Weight of vector cosine-similarity score in hybrid ranking (0.0 to 1.0)
HYBRID_VECTOR_WEIGHT: float = 0.7
# Weight of keyword-match score in hybrid ranking (0.0 to 1.0)
HYBRID_KEYWORD_WEIGHT: float = 0.3
# Minimum combined score for a memory to be included in results
HYBRID_MIN_SCORE: float = 0.3
