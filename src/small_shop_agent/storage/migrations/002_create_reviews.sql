CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    batch_id TEXT NOT NULL,
    review_id TEXT NOT NULL,

    date TEXT,
    platform TEXT,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),

    review_text TEXT NOT NULL,
    cleaned_text TEXT,

    is_empty INTEGER NOT NULL DEFAULT 0 CHECK (is_empty IN (0, 1)),
    is_duplicate INTEGER NOT NULL DEFAULT 0 CHECK (is_duplicate IN (0, 1)),
    is_valid INTEGER NOT NULL DEFAULT 1 CHECK (is_valid IN (0, 1)),

    validation_message TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (batch_id)
        REFERENCES review_batches(batch_id)
        ON DELETE CASCADE,

    UNIQUE (batch_id, review_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_batch_id
ON reviews(batch_id);

CREATE INDEX IF NOT EXISTS idx_reviews_review_id
ON reviews(review_id);

CREATE INDEX IF NOT EXISTS idx_reviews_rating
ON reviews(rating);

CREATE INDEX IF NOT EXISTS idx_reviews_valid
ON reviews(is_valid);

CREATE INDEX IF NOT EXISTS idx_reviews_duplicate
ON reviews(is_duplicate);