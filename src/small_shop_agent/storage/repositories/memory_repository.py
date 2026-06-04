"""Repository for agent_memories and memory_sources tables."""
from __future__ import annotations

import json
import uuid
from typing import Any

from small_shop_agent.storage.sqlite_session import get_session


class MemoryRepository:
    """CRUD for agent_memories + memory_sources."""

    # ── Memory Sources ──────────────────────────────────────────────────

    def insert_source(
        self,
        *,
        source_id: str = "",
        batch_id: str = "",
        review_id: str = "",
        reply_id: str = "",
        approval_action_id: int | None = None,
    ) -> dict:
        """Insert a memory source record. Generates source_id if empty."""
        sid = source_id or f"src-{uuid.uuid4().hex[:12]}"
        with get_session() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO memory_sources
                   (source_id, batch_id, review_id, reply_id, approval_action_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (sid, batch_id, review_id, reply_id, approval_action_id),
            )
        return self.get_source(sid) or {}

    def get_source(self, source_id: str) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM memory_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            return dict(row) if row else None

    # ── Agent Memories ──────────────────────────────────────────────────

    def insert_memory(
        self,
        *,
        memory_id: str = "",
        store_type: str = "",
        memory_type: str = "safety_case",
        content: str = "",
        metadata: dict | None = None,
        source_id: str = "",
        embedding: list[float] | None = None,
    ) -> dict:
        """Insert an agent memory entry. Generates memory_id if empty."""
        mid = memory_id or f"mem-{uuid.uuid4().hex[:12]}"
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        emb_json = json.dumps(embedding) if embedding is not None else None
        with get_session() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO agent_memories
                   (memory_id, store_type, memory_type, content, metadata_json,
                    source_id, embedding)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (mid, store_type, memory_type, content, meta_json, source_id, emb_json),
            )
        return self.get_memory(mid) or {}

    def get_memory(self, memory_id: str) -> dict | None:
        with get_session() as conn:
            row = conn.execute(
                "SELECT * FROM agent_memories WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.get("metadata_json", "{}"))
            return d

    def list_memories(
        self,
        *,
        store_type: str | None = None,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List memories, optionally filtered by store_type and/or memory_type."""
        where = "WHERE 1=1"
        params: list[object] = []
        if store_type:
            where += " AND store_type = ?"
            params.append(store_type)
        if memory_type:
            where += " AND memory_type = ?"
            params.append(memory_type)
        with get_session() as conn:
            rows = conn.execute(
                f"SELECT * FROM agent_memories {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["metadata"] = json.loads(d.get("metadata_json", "{}"))
            result.append(d)
        return result

    def count_memories(
        self,
        store_type: str = "",
        memory_type: str | None = None,
    ) -> int:
        where = "WHERE store_type = ?"
        params: list[object] = [store_type]
        if memory_type:
            where += " AND memory_type = ?"
            params.append(memory_type)
        with get_session() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM agent_memories {where}", params
            ).fetchone()
            return row["cnt"] if row else 0
