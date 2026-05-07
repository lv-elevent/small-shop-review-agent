CREATE TABLE IF NOT EXISTS approval_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    draft_id INTEGER NOT NULL,
    batch_id TEXT NOT NULL,
    review_id TEXT NOT NULL,

    action TEXT NOT NULL
        CHECK (action IN ('approve', 'edit', 'reject')),

    before_text TEXT,
    after_text TEXT,
    reject_reason TEXT,

    actor_type TEXT NOT NULL DEFAULT 'local_user',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (draft_id)
        REFERENCES reply_drafts(id)
        ON DELETE CASCADE,

    FOREIGN KEY (batch_id, review_id)
        REFERENCES reviews(batch_id, review_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approval_actions_draft_id
ON approval_actions(draft_id);

CREATE INDEX IF NOT EXISTS idx_approval_actions_batch_id
ON approval_actions(batch_id);

CREATE INDEX IF NOT EXISTS idx_approval_actions_action
ON approval_actions(action);