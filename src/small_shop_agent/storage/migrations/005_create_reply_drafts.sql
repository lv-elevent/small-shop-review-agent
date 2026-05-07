CREATE TABLE IF NOT EXISTS reply_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    batch_id TEXT NOT NULL,
    review_id TEXT NOT NULL,

    original_review TEXT NOT NULL,

    draft_text TEXT NOT NULL,
    rewritten_text TEXT,
    edited_text TEXT,
    final_text TEXT,

    safety_status TEXT NOT NULL DEFAULT 'pass'
        CHECK (safety_status IN ('pass', 'rewrite_required', 'blocked')),

    risk_types TEXT,
    safety_reason TEXT,

    approval_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'edited', 'rejected', 'blocked')),

    model_name TEXT,
    raw_model_output TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TEXT,

    FOREIGN KEY (batch_id, review_id)
        REFERENCES reviews(batch_id, review_id)
        ON DELETE CASCADE,

    UNIQUE (batch_id, review_id)
);

CREATE INDEX IF NOT EXISTS idx_reply_drafts_batch_id
ON reply_drafts(batch_id);

CREATE INDEX IF NOT EXISTS idx_reply_drafts_review_id
ON reply_drafts(review_id);

CREATE INDEX IF NOT EXISTS idx_reply_drafts_safety_status
ON reply_drafts(safety_status);

CREATE INDEX IF NOT EXISTS idx_reply_drafts_approval_status
ON reply_drafts(approval_status);