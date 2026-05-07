CREATE TABLE IF NOT EXISTS review_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    batch_id TEXT NOT NULL,
    review_id TEXT NOT NULL,

    topics TEXT NOT NULL,
    primary_topic TEXT NOT NULL
        CHECK (primary_topic IN (
            'waiting_time',
            'service',
            'product',
            'price',
            'environment',
            'hygiene',
            'location',
            'other'
        )),

    sentiment TEXT NOT NULL
        CHECK (sentiment IN ('positive', 'neutral', 'negative')),

    severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),

    topic_confidence REAL,
    sentiment_confidence REAL,

    is_negative_candidate INTEGER NOT NULL DEFAULT 0 CHECK (is_negative_candidate IN (0, 1)),
    needs_review INTEGER NOT NULL DEFAULT 0 CHECK (needs_review IN (0, 1)),

    analysis_reason TEXT,
    model_name TEXT,
    raw_model_output TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (batch_id, review_id)
        REFERENCES reviews(batch_id, review_id)
        ON DELETE CASCADE,

    UNIQUE (batch_id, review_id)
);

CREATE INDEX IF NOT EXISTS idx_review_analysis_batch_id
ON review_analysis(batch_id);

CREATE INDEX IF NOT EXISTS idx_review_analysis_review_id
ON review_analysis(review_id);

CREATE INDEX IF NOT EXISTS idx_review_analysis_primary_topic
ON review_analysis(primary_topic);

CREATE INDEX IF NOT EXISTS idx_review_analysis_sentiment
ON review_analysis(sentiment);

CREATE INDEX IF NOT EXISTS idx_review_analysis_negative
ON review_analysis(is_negative_candidate);

CREATE INDEX IF NOT EXISTS idx_review_analysis_severity
ON review_analysis(severity);