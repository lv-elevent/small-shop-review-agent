CREATE TABLE IF NOT EXISTS eval_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    eval_run_id TEXT NOT NULL UNIQUE,
    batch_id TEXT,

    topic_accuracy REAL NOT NULL DEFAULT 0,
    sentiment_accuracy REAL NOT NULL DEFAULT 0,

    unsafe_reply_count INTEGER NOT NULL DEFAULT 0,
    schema_failure_count INTEGER NOT NULL DEFAULT 0,

    total_eval_cases INTEGER NOT NULL DEFAULT 0,
    topic_correct_count INTEGER NOT NULL DEFAULT 0,
    sentiment_correct_count INTEGER NOT NULL DEFAULT 0,

    baseline_topic_accuracy REAL,
    baseline_sentiment_accuracy REAL,

    notes TEXT,
    report_json TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (batch_id)
        REFERENCES review_batches(batch_id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_results_eval_run_id
ON eval_results(eval_run_id);

CREATE INDEX IF NOT EXISTS idx_eval_results_batch_id
ON eval_results(batch_id);

CREATE INDEX IF NOT EXISTS idx_eval_results_created_at
ON eval_results(created_at);