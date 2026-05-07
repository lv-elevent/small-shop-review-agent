"""Repository for review_analysis table."""
from __future__ import annotations

import json

from small_shop_agent.storage.sqlite_session import get_session


class AnalysisRepository:
    """CRUD for review_analysis."""

    def bulk_insert_analysis(self, batch_id: str, analyses: list[dict]) -> int:
        """Insert analysis results. Returns count inserted."""
        with get_session() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO review_analysis
                   (batch_id, review_id, topics, primary_topic, sentiment,
                    severity, topic_confidence, sentiment_confidence,
                    is_negative_candidate, needs_review)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(batch_id, a["review_id"],
                  json.dumps(a["topics"], ensure_ascii=False),
                  a["primary_topic"], a["sentiment"], a["severity"],
                  a.get("topic_confidence", 0.85),
                  a.get("sentiment_confidence", 0.85),
                  int(a.get("is_negative_candidate", False)),
                  int(a.get("needs_review", False)))
                 for a in analyses],
            )
        return len(analyses)

    def list_analysis(self, batch_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                "SELECT * FROM review_analysis WHERE batch_id = ? ORDER BY id",
                (batch_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["topics"] = json.loads(d["topics"]) if d["topics"] else []
                result.append(d)
            return result

    def get_negative_candidates(self, batch_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT * FROM review_analysis
                   WHERE batch_id = ? AND is_negative_candidate = 1
                   ORDER BY severity DESC""",
                (batch_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["topics"] = json.loads(d["topics"]) if d["topics"] else []
                result.append(d)
            return result

    def count_by_sentiment(self, batch_id: str) -> dict[str, int]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT sentiment, COUNT(*) as cnt
                   FROM review_analysis WHERE batch_id = ?
                   GROUP BY sentiment""",
                (batch_id,),
            ).fetchall()
            counts = {"positive": 0, "neutral": 0, "negative": 0}
            for r in rows:
                counts[r["sentiment"]] = r["cnt"]
            return counts
