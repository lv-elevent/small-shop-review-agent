"""Repository for traces table."""
from __future__ import annotations

from small_shop_agent.storage.sqlite_session import get_session


class TraceRepository:
    """CRUD for traces."""

    def log_step(
        self,
        *,
        trace_id: str,
        batch_id: str,
        step_name: str,
        status: str,
        input_summary: str = "",
        output_summary: str = "",
        error_message: str = "",
        latency_ms: int = 0,
        model_name: str = "",
    ) -> dict:
        with get_session() as conn:
            cur = conn.execute(
                """INSERT INTO traces
                   (trace_id, batch_id, step_name, status,
                    input_summary, output_summary, error_message,
                    latency_ms, model_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trace_id, batch_id, step_name, status,
                 input_summary, output_summary, error_message,
                 latency_ms, model_name),
            )
            row = conn.execute(
                "SELECT * FROM traces WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return dict(row) if row else {}

    def get_traces(self, batch_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT * FROM traces
                   WHERE batch_id = ? ORDER BY id ASC""",
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_latest_trace(self) -> list[dict]:
        """Get traces for the most recent batch."""
        with get_session() as conn:
            # Find the latest batch_id with traces
            latest = conn.execute(
                """SELECT DISTINCT batch_id FROM traces
                   ORDER BY id DESC LIMIT 1"""
            ).fetchone()
            if not latest:
                return []
            return self.get_traces(latest["batch_id"])

    def get_trace_by_id(self, trace_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT * FROM traces
                   WHERE trace_id = ? ORDER BY id ASC""",
                (trace_id,),
            ).fetchall()
            return [dict(r) for r in rows]
