"""Reliability metrics calculator — reads traces, drafts, memories, evals."""
from __future__ import annotations

from dataclasses import dataclass, field

from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.memory_repository import MemoryRepository
from small_shop_agent.storage.repositories.eval_repository import EvalRepository


@dataclass
class ReliabilityMetrics:
    batch_id: str = ""
    total_latency_ms: int = 0
    llm_latency_ms: int = 0
    trace_count: int = 0
    tool_call_count: int = 0
    schema_retry_count: int = 0
    fallback_count: int = 0
    fallback_rate: float = 0.0
    safety_block_count: int = 0
    safety_block_rate: float = 0.0
    human_edit_count: int = 0
    human_edit_rate: float = 0.0
    memory_hit_count: int = 0
    memory_hit_rate: float = 0.0
    unsafe_escape_count: int = 0
    errors: list[str] = field(default_factory=list)


def compute_metrics(batch_id: str) -> ReliabilityMetrics:
    """Aggregate reliability metrics for a batch from all available sources."""
    m = ReliabilityMetrics(batch_id=batch_id)
    trace_repo = TraceRepository()
    reply_repo = ReplyRepository()
    memo_repo = MemoryRepository()
    eval_repo = EvalRepository()

    try:
        # ── Traces: latency, fallback, schema retries ───────────────
        traces = trace_repo.get_traces(batch_id)
        m.trace_count = len(traces)
        for t in traces:
            m.total_latency_ms += t.get("latency_ms", 0) or 0
            out = t.get("output_summary", "")
            if out and isinstance(out, str):
                if "fallback" in out.lower() or "used_fallback=True" in out:
                    m.fallback_count += 1
                if "retry" in out.lower() or "schema_errors" in out:
                    m.schema_retry_count += 1

        llm_traces = [t for t in traces if "llm_call" in t.get("step_name", "").lower()]
        m.llm_latency_ms = sum(t.get("latency_ms", 0) or 0 for t in llm_traces)
        if m.trace_count > 0:
            m.fallback_rate = m.fallback_count / m.trace_count

        # ── Drafts: safety block rate, human edit rate ──────────────
        drafts = reply_repo.list_drafts(batch_id)
        draft_total = len(drafts)
        if draft_total > 0:
            m.safety_block_count = sum(1 for d in drafts if d.get("safety_status") == "blocked")
            m.safety_block_rate = m.safety_block_count / draft_total
            m.human_edit_count = sum(1 for d in drafts if d.get("approval_status") == "edited")
            m.human_edit_rate = m.human_edit_count / draft_total

        # ── Memory: hit rate (from reply_drafting_prep trace) ──────
        for t in traces:
            out = t.get("output_summary", "")
            if isinstance(out, str) and "memory_hits=" in out:
                try:
                    hits_str = out.split("memory_hits=")[-1].split(",")[0].strip()
                    m.memory_hit_count = int(hits_str)
                except ValueError:
                    pass
        neg_count = sum(1 for d in drafts if d.get("safety_status") is not None)
        if neg_count > 0:
            m.memory_hit_rate = min(m.memory_hit_count / (neg_count * 3), 1.0)

        # ── Eval: unsafe escape count ──────────────────────────────
        latest = eval_repo.get_latest_eval()
        if latest:
            m.unsafe_escape_count = latest.get("unsafe_reply_count", 0) or 0

    except Exception as exc:
        m.errors.append(str(exc))

    return m
