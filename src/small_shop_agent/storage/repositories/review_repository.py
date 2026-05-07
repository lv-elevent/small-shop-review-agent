"""Repository for reviews table."""
from __future__ import annotations

from small_shop_agent.storage.sqlite_session import get_session


class ReviewRepository:
    """CRUD for reviews."""

    def bulk_insert_reviews(self, batch_id: str, reviews: list[dict]) -> int:
        """Insert a list of review dicts. Returns count inserted."""
        with get_session() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO reviews
                   (batch_id, review_id, date, platform, rating,
                    review_text, cleaned_text, is_empty, is_duplicate, is_valid)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(batch_id, r["review_id"], r.get("date", ""), r.get("platform", ""),
                  r["rating"], r["review_text"], r.get("cleaned_text", ""),
                  int(r.get("is_empty", False)), int(r.get("is_duplicate", False)),
                  int(r.get("is_valid", True)))
                 for r in reviews],
            )
        return len(reviews)

    def list_reviews(self, batch_id: str, *, is_valid: bool | None = None,
                     limit: int = 500, offset: int = 0) -> list[dict]:
        where = "WHERE batch_id = ?"
        params: list[object] = [batch_id]
        if is_valid is not None:
            where += " AND is_valid = ?"
            params.append(int(is_valid))
        with get_session() as conn:
            rows = conn.execute(
                f"SELECT * FROM reviews {where} ORDER BY id LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            return [dict(r) for r in rows]

    def get_review(self, batch_id: str, review_id: str) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE batch_id = ? AND review_id = ?",
                (batch_id, review_id),
            ).fetchone()
            return dict(row) if row else None

    def count_reviews(self, batch_id: str, *, is_valid: bool | None = None) -> int:
        where = "WHERE batch_id = ?"
        params: list[object] = [batch_id]
        if is_valid is not None:
            where += " AND is_valid = ?"
            params.append(int(is_valid))
        with get_session() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM reviews {where}", params
            ).fetchone()
            return row["cnt"] if row else 0

    def get_negative_reviews(self, batch_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT r.* FROM reviews r
                   JOIN review_analysis a ON r.batch_id = a.batch_id
                     AND r.review_id = a.review_id
                   WHERE r.batch_id = ? AND a.is_negative_candidate = 1
                   ORDER BY a.severity DESC""",
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]
