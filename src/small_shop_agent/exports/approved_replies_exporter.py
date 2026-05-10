"""Approved replies CSV exporter — fixed 6-column format with review JOIN."""
from __future__ import annotations

import csv
import io

from small_shop_agent.storage.database import get_connection

_CSV_COLUMNS = [
    "review_id",
    "platform",
    "rating",
    "original_review",
    "approved_reply",
    "approved_at",
]


def export_approved_replies_csv(batch_id: str) -> str:
    """Export approved/edited replies as CSV with review JOIN for platform/rating.

    Returns a CSV string (UTF-8 BOM) with exactly 6 columns:
    review_id, platform, rating, original_review, approved_reply, approved_at
    """
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT
                   d.review_id,
                   COALESCE(r.platform, '') AS platform,
                   r.rating,
                   d.original_review,
                   COALESCE(NULLIF(d.final_text, ''), d.draft_text) AS approved_reply,
                   d.approved_at
               FROM reply_drafts d
               LEFT JOIN reviews r
                 ON r.batch_id = d.batch_id AND r.review_id = d.review_id
               WHERE d.batch_id = ?
                 AND d.approval_status IN ('approved', 'edited')
               ORDER BY d.approved_at DESC""",
            (batch_id,),
        ).fetchall()

    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM for Excel
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    for row in rows:
        writer.writerow([
            row["review_id"],
            row["platform"],
            row["rating"],
            row["original_review"],
            row["approved_reply"],
            row["approved_at"] or "",
        ])
    return buf.getvalue()
