CREATE TABLE IF NOT EXISTS agent_memories (
    memory_id TEXT PRIMARY KEY,

    store_type TEXT NOT NULL DEFAULT '',

    memory_type TEXT NOT NULL
        CHECK (memory_type IN (
            'issue_trend',
            'approved_reply',
            'rejected_reply',
            'safety_case'
        )),

    content TEXT NOT NULL DEFAULT '',

    metadata_json TEXT NOT NULL DEFAULT '{}',

    source_id TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_memories_store_type
ON agent_memories(store_type);

CREATE INDEX IF NOT EXISTS idx_agent_memories_type
ON agent_memories(memory_type);

CREATE INDEX IF NOT EXISTS idx_agent_memories_source_id
ON agent_memories(source_id);

CREATE INDEX IF NOT EXISTS idx_agent_memories_created_at
ON agent_memories(created_at);
