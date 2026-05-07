CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trace_id TEXT NOT NULL,
    batch_id TEXT,

    step_name TEXT NOT NULL
        CHECK (step_name IN (
            'input_validation',
            'data_cleaning',
            'classification',
            'sentiment_analysis',
            'issue_aggregation',
            'evidence_check',
            'reply_drafting',
            'safety_check',
            'human_approval',
            'eval_run'
        )),

    input_summary TEXT,
    output_summary TEXT,

    status TEXT NOT NULL
        CHECK (status IN ('passed', 'warning', 'failed', 'pending')),

    error_message TEXT,

    latency_ms INTEGER,
    model_name TEXT,

    metadata TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (batch_id)
        REFERENCES review_batches(batch_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_traces_trace_id
ON traces(trace_id);

CREATE INDEX IF NOT EXISTS idx_traces_batch_id
ON traces(batch_id);

CREATE INDEX IF NOT EXISTS idx_traces_step_name
ON traces(step_name);

CREATE INDEX IF NOT EXISTS idx_traces_status
ON traces(status);

CREATE INDEX IF NOT EXISTS idx_traces_created_at
ON traces(created_at);