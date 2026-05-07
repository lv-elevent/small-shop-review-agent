"""Repository for insights and insight_evidence tables."""
from __future__ import annotations

from small_shop_agent.storage.sqlite_session import get_session


class InsightRepository:
    """CRUD for insights + insight_evidence."""

    # ── Insights ────────────────────────────────────────────────────────────

    def bulk_insert_insights(self, batch_id: str, insights: list[dict]) -> int:
        """Insert insight rows. Returns count inserted."""
        with get_session() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO insights
                   (batch_id, rank, issue_name, topic, mention_count,
                    severity_level, priority_score, suggested_action,
                    evidence_count, evidence_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(batch_id, i["rank"], i["issue_name"], i["topic"],
                  i["mention_count"], i["severity_level"], i["priority_score"],
                  i["suggested_action"], i.get("evidence_count", 0),
                  i.get("evidence_status", "sufficient"))
                 for i in insights],
            )
        return len(insights)

    def get_top_issues(self, batch_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                "SELECT * FROM insights WHERE batch_id = ? ORDER BY rank ASC",
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Insight Evidence ────────────────────────────────────────────────────

    def bulk_insert_evidence(self, batch_id: str, evidence_list: list[dict]) -> int:
        """Insert evidence rows linking insights to review_ids. Returns count inserted."""
        with get_session() as conn:
            conn.executemany(
                """INSERT INTO insight_evidence
                   (insight_id, batch_id, review_id, evidence_text, evidence_reason)
                   VALUES (?, ?, ?, ?, ?)""",
                [(e["insight_id"], batch_id, e["review_id"],
                  e["evidence_text"], e.get("evidence_reason", ""))
                 for e in evidence_list],
            )
        return len(evidence_list)

    def get_issue_evidence(self, insight_id: int) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT * FROM insight_evidence
                   WHERE insight_id = ? ORDER BY id""",
                (insight_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_evidence_by_batch(self, batch_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT ev.*, i.issue_name, i.rank
                   FROM insight_evidence ev
                   JOIN insights i ON ev.insight_id = i.id
                   WHERE ev.batch_id = ?
                   ORDER BY i.rank, ev.id""",
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]
