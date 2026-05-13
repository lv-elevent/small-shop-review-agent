"""Convenience entry point — creates state, resolves provider, runs the graph."""
from __future__ import annotations

from typing import Any

from loguru import logger

from small_shop_agent.agent_runtime.state import AgentState, create_initial_state
from small_shop_agent.agent_runtime.graph.review_workflow import (
    run_agent_graph,
    run_agent_graph_async,
)
from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.repositories.insight_repository import InsightRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.demo.demo_loader import DemoLoader
from small_shop_agent.llm.mock_provider import MockProvider


def run_with_agent_runtime(
    batch_id: str,
    mode: str = "demo",
) -> AgentState:
    """Run the full agent graph against *batch_id*, returning final state.

    *mode* can be ``"demo"`` (uses MockProvider) or ``"live"``
    (resolves an OpenAI-compatible provider).
    """
    # ── Repos ─────────────────────────────────────────────────────────
    batch_repo = BatchRepository()
    review_repo = ReviewRepository()
    analysis_repo = AnalysisRepository()
    insight_repo = InsightRepository()
    reply_repo = ReplyRepository()
    trace_repo = TraceRepository()

    # ── Validate batch ────────────────────────────────────────────────
    batch = batch_repo.get_batch(batch_id)
    if batch is None:
        return {
            **create_initial_state(batch_id=batch_id, mode=mode),
            "errors": [{"step": "init", "message": f"Batch not found: {batch_id}"}],
        }

    reviews = review_repo.list_reviews(batch_id, is_valid=True)
    review_dicts: list[dict[str, Any]] = [dict(r) for r in reviews]

    # ── Provider ──────────────────────────────────────────────────────
    if mode in ("demo", "mock"):
        provider = MockProvider(DemoLoader())
        model_name = "demo"
    else:
        try:
            from small_shop_agent.llm.llm_router import get_llm_provider
            provider = get_llm_provider(mode)
            model_name = getattr(provider, "_model", mode)
            provider._batch_id = batch_id  # type: ignore[attr-defined]
        except Exception as exc:
            state = create_initial_state(
                batch_id=batch_id, mode=mode,
                model_name=mode, reviews=review_dicts,
            )
            state["errors"].append({
                "step": "init",
                "message": f"Failed to resolve provider for mode={mode!r}: {exc}",
            })
            return state

    # ── Initial state ─────────────────────────────────────────────────
    state = create_initial_state(
        batch_id=batch_id,
        mode=mode,
        model_name=model_name,
        reviews=review_dicts,
    )

    batch_repo.update_status(batch_id, "analyzing")

    # ── Run graph ─────────────────────────────────────────────────────
    from small_shop_agent.core.config import AGENT_ASYNC_ENABLED

    if AGENT_ASYNC_ENABLED:
        import asyncio
        runner_fn = run_agent_graph_async
        final_state = asyncio.run(runner_fn(
            state=state,
            provider=provider,
            trace_repo=trace_repo,
            analysis_repo=analysis_repo,
            insight_repo=insight_repo,
            reply_repo=reply_repo,
        ))
    else:
        final_state = run_agent_graph(
            state=state,
            provider=provider,
            trace_repo=trace_repo,
            analysis_repo=analysis_repo,
            insight_repo=insight_repo,
            reply_repo=reply_repo,
        )

    # ── Finalize batch status ─────────────────────────────────────────
    error_count = len(final_state["errors"])
    batch_repo.update_status(
        batch_id,
        "analyzed" if error_count == 0 else "failed",
        negative_review_count=final_state.get("_negative_count", 0),
        pending_reply_count=len([
            d for d in final_state.get("safety_results", [])
            if d.get("approval_status") == "pending"
        ]),
    )

    logger.success(
        f"智能体运行结束 batch={batch_id}："
        f"错误={error_count}, 警告={len(final_state['warnings'])}"
    )
    return final_state
