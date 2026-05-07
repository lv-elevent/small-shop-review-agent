CREATE TABLE IF NOT EXISTS insight_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    insight_id INTEGER NOT NULL,
    batch_id TEXT NOT NULL,
    review_id TEXT NOT NULL,

    evidence_text TEXT NOT NULL,
    evidence_reason TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insight_id)
        REFERENCES insights(id)
        ON DELETE CASCADE,

    FOREIGN KEY (batch_id, review_id)
        REFERENCES reviews(batch_id, review_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_insight_evidence_insight_id
ON insight_evidence(insight_id);

CREATE INDEX IF NOT EXISTS idx_insight_evidence_batch_id
ON insight_evidence(batch_id);

CREATE INDEX IF NOT EXISTS idx_insight_evidence_review_id
ON insight_evidence(review_id);