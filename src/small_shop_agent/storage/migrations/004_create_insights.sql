CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    batch_id TEXT NOT NULL,

    rank INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 3),

    issue_name TEXT NOT NULL,
    issue_summary TEXT,

    topic TEXT NOT NULL
        CHECK (topic IN (
            'waiting_time',
            'service',
            'product',
            'price',
            'environment',
            'hygiene',
            'location',
            'other'
        )),

    mention_count INTEGER NOT NULL DEFAULT 0,

    severity_level TEXT NOT NULL
        CHECK (severity_level IN ('low', 'medium', 'high')),

    priority_score REAL NOT NULL DEFAULT 0,

    suggested_action TEXT NOT NULL,

    evidence_count INTEGER NOT NULL DEFAULT 0,
    evidence_status TEXT NOT NULL DEFAULT 'insufficient'
        CHECK (evidence_status IN ('sufficient', 'insufficient')),

    model_name TEXT,
    raw_model_output TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (batch_id)
        REFERENCES review_batches(batch_id)
        ON DELETE CASCADE,

    UNIQUE (batch_id, rank)
);

CREATE INDEX IF NOT EXISTS idx_insights_batch_id
ON insights(batch_id);

CREATE INDEX IF NOT EXISTS idx_insights_rank
ON insights(rank);

CREATE INDEX IF NOT EXISTS idx_insights_topic
ON insights(topic);

CREATE INDEX IF NOT EXISTS idx_insights_severity_level
ON insights(severity_level);