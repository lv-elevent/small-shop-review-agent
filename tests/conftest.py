"""Shared test fixtures — temp DB with migrations, no pollution of demo DB."""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """Create temp SQLite DB, run all migrations, patch database module.

    All service / repository code flows through
    ``small_shop_agent.storage.database.get_connection()`` which reads
    ``database.DB_PATH`` at call time.  Patching the module-level
    ``DB_PATH`` redirects everything to the temp file.
    """
    db_path = tmp_path / "test_small_shop.db"

    monkeypatch.setattr(
        "small_shop_agent.storage.database.DB_PATH",
        db_path,
    )
    monkeypatch.setattr(
        "small_shop_agent.core.config.DB_PATH",
        db_path,
    )

    from small_shop_agent.storage.database import execute_migrations

    execute_migrations()

    return str(db_path)
