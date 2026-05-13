CREATE TABLE IF NOT EXISTS memory_sources (
    source_id TEXT PRIMARY KEY,

    batch_id TEXT,
    review_id TEXT,
    reply_id TEXT,
    approval_action_id INTEGER,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_sources_batch_id
ON memory_sources(batch_id);

CREATE INDEX IF NOT EXISTS idx_memory_sources_review_id
ON memory_sources(review_id);
