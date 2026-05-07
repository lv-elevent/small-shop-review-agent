"""Repository for eval_results table."""
from __future__ import annotations

from small_shop_agent.storage.sqlite_session import get_session


class EvalRepository:
    """CRUD for eval_results."""

    def save_eval_result(
        self,
        *,
        eval_run_id: str,
        batch_id: str | None = None,
        topic_accuracy: float = 0.0,
        sentiment_accuracy: float = 0.0,
        unsafe_reply_count: int = 0,
        schema_failure_count: int = 0,
        total_eval_cases: int = 0,
        topic_correct_count: int = 0,
        sentiment_correct_count: int = 0,
        baseline_topic_accuracy: float | None = None,
        baseline_sentiment_accuracy: float | None = None,
        notes: str = "",
        report_json: str = "",
    ) -> dict:
        with get_session() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO eval_results
                   (eval_run_id, batch_id, topic_accuracy, sentiment_accuracy,
                    unsafe_reply_count, schema_failure_count,
                    total_eval_cases, topic_correct_count, sentiment_correct_count,
                    baseline_topic_accuracy, baseline_sentiment_accuracy,
                    notes, report_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (eval_run_id, batch_id, topic_accuracy, sentiment_accuracy,
                 unsafe_reply_count, schema_failure_count,
                 total_eval_cases, topic_correct_count, sentiment_correct_count,
                 baseline_topic_accuracy, baseline_sentiment_accuracy,
                 notes, report_json),
            )
        return self.get_eval_result(eval_run_id)  # type: ignore[return-value]

    def get_eval_result(self, eval_run_id: str) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM eval_results WHERE eval_run_id = ?", (eval_run_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_latest_eval(self) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM eval_results ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def list_eval_runs(self, limit: int = 20) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                "SELECT * FROM eval_results ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
