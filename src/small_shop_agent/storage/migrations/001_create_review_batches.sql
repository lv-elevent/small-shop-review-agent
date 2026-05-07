CREATE TABLE IF NOT EXISTS review_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    batch_id TEXT NOT NULL UNIQUE,
    store_type TEXT NOT NULL DEFAULT 'coffee_shop',
    source_type TEXT NOT NULL CHECK (source_type IN ('csv_upload', 'demo_mode')),

    file_name TEXT,
    file_hash TEXT,

    date_start TEXT,
    date_end TEXT,

    total_rows INTEGER NOT NULL DEFAULT 0,
    valid_review_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    empty_review_count INTEGER NOT NULL DEFAULT 0,
    schema_error_count INTEGER NOT NULL DEFAULT 0,
    negative_review_count INTEGER NOT NULL DEFAULT 0,
    pending_reply_count INTEGER NOT NULL DEFAULT 0,

    status TEXT NOT NULL DEFAULT 'uploaded'
        CHECK (status IN ('uploaded', 'validated', 'analyzing', 'analyzed', 'failed')),

    error_message TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_review_batches_batch_id
ON review_batches(batch_id);

CREATE INDEX IF NOT EXISTS idx_review_batches_status
ON review_batches(status);