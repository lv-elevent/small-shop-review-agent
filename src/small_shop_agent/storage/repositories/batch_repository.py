"""Repository for review_batches table."""
from __future__ import annotations

from small_shop_agent.storage.sqlite_session import get_session


class BatchRepository:
    """CRUD for review_batches."""

    def create_batch(
        self,
        *,
        batch_id: str,
        store_type: str = "coffee_shop",
        source_type: str = "demo_mode",
        file_name: str | None = None,
        total_rows: int = 0,
        valid_review_count: int = 0,
        duplicate_count: int = 0,
        empty_review_count: int = 0,
        schema_error_count: int = 0,
        status: str = "uploaded",
    ) -> dict:
        with get_session() as conn:
            conn.execute(
                """INSERT INTO review_batches
                   (batch_id, store_type, source_type, file_name,
                    total_rows, valid_review_count, duplicate_count,
                    empty_review_count, schema_error_count, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (batch_id, store_type, source_type, file_name,
                 total_rows, valid_review_count, duplicate_count,
                 empty_review_count, schema_error_count, status),
            )
        # Called outside the with block so the INSERT is committed first
        return self.get_batch(batch_id)  # type: ignore[return-value]

    def get_batch(self, batch_id: str) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM review_batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_status(self, batch_id: str, status: str, **extra: object) -> dict | None:
        sets = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params: list[object] = [status]
        for col, val in extra.items():
            sets.append(f"{col} = ?")
            params.append(val)
        params.append(batch_id)
        with get_session() as conn:
            conn.execute(
                f"UPDATE review_batches SET {', '.join(sets)} WHERE batch_id = ?",
                params,
            )
        return self.get_batch(batch_id)

    def get_latest_batch(self) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM review_batches ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def list_batches(self) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                "SELECT * FROM review_batches ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]
