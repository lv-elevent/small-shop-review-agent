"""Repository for reply_drafts and approval_actions tables."""
from __future__ import annotations

import json

from small_shop_agent.storage.sqlite_session import get_session


class ReplyRepository:
    """CRUD for reply_drafts + approval_actions."""

    # ── Reply Drafts ────────────────────────────────────────────────────────

    def bulk_insert_drafts(self, batch_id: str, drafts: list[dict]) -> int:
        """Insert reply drafts. Returns count inserted."""
        with get_session() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO reply_drafts
                   (batch_id, review_id, original_review, draft_text,
                    safety_status, risk_types, approval_status, model_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(batch_id, d["review_id"], d["original_review"], d["draft_text"],
                  d.get("safety_status", "pass"),
                  json.dumps(d.get("risk_types", []), ensure_ascii=False),
                  d.get("approval_status", "pending"),
                  d.get("model_name", "demo"))
                 for d in drafts],
            )
        return len(drafts)

    def get_pending_drafts(self, batch_id: str) -> list[dict]:
        with get_session() as conn:
            rows = conn.execute(
                """SELECT * FROM reply_drafts
                   WHERE batch_id = ? AND approval_status = 'pending'
                   ORDER BY
                     CASE safety_status
                       WHEN 'blocked' THEN 1
                       WHEN 'rewrite_required' THEN 2
                       ELSE 3
                     END, id""",
                (batch_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["risk_types"] = json.loads(d["risk_types"]) if d["risk_types"] else []
                result.append(d)
            return result

    def get_draft_detail(self, draft_id: int) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM reply_drafts WHERE id = ?", (draft_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["risk_types"] = json.loads(d["risk_types"]) if d["risk_types"] else []
            return d

    def get_draft_by_review(self, batch_id: str, review_id: str) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM reply_drafts WHERE batch_id = ? AND review_id = ?",
                (batch_id, review_id),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["risk_types"] = json.loads(d["risk_types"]) if d["risk_types"] else []
            return d

    def list_drafts(self, batch_id: str,
                    approval_status: str | None = None,
                    safety_status: str | None = None) -> list[dict]:
        where = "WHERE batch_id = ?"
        params: list[object] = [batch_id]
        if approval_status:
            where += " AND approval_status = ?"
            params.append(approval_status)
        if safety_status:
            where += " AND safety_status = ?"
            params.append(safety_status)
        with get_session() as conn:
            rows = conn.execute(
                f"SELECT * FROM reply_drafts {where} ORDER BY id", params
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["risk_types"] = json.loads(d["risk_types"]) if d["risk_types"] else []
                result.append(d)
            return result

    def update_approval_status(self, draft_id: int, approval_status: str,
                                edited_text: str = "",
                                final_text: str = "") -> dict | None:
        with get_session() as conn:
            conn.execute(
                """UPDATE reply_drafts
                   SET approval_status = ?, edited_text = ?, final_text = ?,
                       updated_at = CURRENT_TIMESTAMP,
                       approved_at = CASE WHEN ? IN ('approved','edited')
                                          THEN CURRENT_TIMESTAMP ELSE approved_at END
                   WHERE id = ?""",
                (approval_status, edited_text, final_text, approval_status, draft_id),
            )
        return self.get_draft_detail(draft_id)

    # ── Approval Actions ────────────────────────────────────────────────────

    def insert_approval_action(
        self,
        *,
        draft_id: int,
        batch_id: str,
        review_id: str,
        action: str,
        before_text: str = "",
        after_text: str = "",
        reject_reason: str = "",
    ) -> dict:
        with get_session() as conn:
            cur = conn.execute(
                """INSERT INTO approval_actions
                   (draft_id, batch_id, review_id, action,
                    before_text, after_text, reject_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (draft_id, batch_id, review_id, action,
                 before_text, after_text, reject_reason),
            )
            row = conn.execute(
                "SELECT * FROM approval_actions WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return dict(row) if row else {}
