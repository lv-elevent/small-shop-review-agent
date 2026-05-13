"""Sequential graph runner — executes nodes in order defined by edges.

Phase 1-A: linear pipeline.  No parallel execution, no checkpointing,
no async.  Each node is a plain function (state, **deps) -> state.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from small_shop_agent.agent_runtime.state import AgentState
from small_shop_agent.agent_runtime.graph.edges import END, route

# Import node implementations so the lookup table works.
from small_shop_agent.agent_runtime.graph.nodes import (  # noqa: F401
    classification_node,
    classification_retry_node,
    fallback_classification_node,
    sentiment_node,
    sentiment_retry_node,
    fallback_sentiment_node,
    consistency_node,
    merge_node,
    insight_node,
    evidence_node,
    regenerate_insight_node,
    mark_insight_insufficient_node,
    reply_node,
    safety_node,
    approval_node,
)


def run_agent_graph(
    state: AgentState,
    *,
    provider,
    trace_repo,
    analysis_repo,
    insight_repo,
    reply_repo,
) -> AgentState:
    """Execute all pipeline nodes sequentially against *state*.

    Parameters
    ----------
    state : AgentState
        Must already contain ``batch_id``, ``mode``, ``model_name``,
        and ``reviews``.
    provider : BaseLLMProvider
    trace_repo : TraceRepository
    analysis_repo : AnalysisRepository
    insight_repo : InsightRepository
    reply_repo : ReplyRepository

    Returns the mutated state after all nodes have been visited.
    """
    # ── Node lookup table ──────────────────────────────────────────────
    node_registry: dict[str, Any] = {
        "classification": classification_node,
        "classification_retry": classification_retry_node,
        "fallback_classification": fallback_classification_node,
        "sentiment": sentiment_node,
        "sentiment_retry": sentiment_retry_node,
        "fallback_sentiment": fallback_sentiment_node,
        "consistency": consistency_node,
        "merge": merge_node,
        "insight": insight_node,
        "evidence": evidence_node,
        "regenerate_insight": regenerate_insight_node,
        "mark_insight_insufficient": mark_insight_insufficient_node,
        "reply": reply_node,
        "safety": safety_node,
        "approval": approval_node,
    }

    # Determine starting point
    current = state.get("current_step", "init")
    if current in ("init", "__start__"):
        current = "classification"

    # Ensure first node is valid
    if current not in node_registry:
        current = "classification"

    while current != END:
        node_fn = node_registry.get(current)
        if node_fn is None:
            logger.warning(f"未知节点：{current!r}，停止。")
            state["errors"].append({
                "step": current,
                "message": f"未知节点名称：{current!r}",
            })
            break

        state["current_step"] = current
        logger.debug(f"智能体流程 — 进入节点：{current}")

        try:
            _dispatch(node_fn, state, provider, trace_repo,
                      analysis_repo, insight_repo, reply_repo)
        except Exception as exc:
            logger.error(f"节点 {current!r} 失败：{exc}")
            state["errors"].append({
                "step": current,
                "message": str(exc),
            })

        # Conditional routing — state-aware
        current = route(state)

    logger.success(
        f"智能体流程完成 batch={state['batch_id']}："
        f"当前步骤={state.get('current_step')}, "
        f"错误={len(state['errors'])}, "
        f"警告={len(state['warnings'])}"
    )
    return state


def _dispatch(
    node_fn,
    state: AgentState,
    provider,
    trace_repo,
    analysis_repo,
    insight_repo,
    reply_repo,
) -> AgentState:
    """Call *node_fn* with only the keyword arguments it accepts."""
    import inspect

    sig = inspect.signature(node_fn)
    kwargs: dict[str, Any] = {
        "provider": provider,
        "trace_repo": trace_repo,
        "analysis_repo": analysis_repo,
        "insight_repo": insight_repo,
        "reply_repo": reply_repo,
    }
    # Filter to only parameters the function declares (beyond *state*).
    accepted = {p for p in sig.parameters if p != "state"}
    filtered = {k: v for k, v in kwargs.items() if k in accepted}
    node_fn(state, **filtered)


# ═══════════════════════════════════════════════════════════════════════════
# Async graph runner
# ═══════════════════════════════════════════════════════════════════════════

import asyncio  # noqa: E402


async def run_agent_graph_async(
    state: AgentState,
    *,
    provider,
    trace_repo,
    analysis_repo,
    insight_repo,
    reply_repo,
) -> AgentState:
    """Async variant — runs classification + sentiment concurrently.

    After the concurrent phase, remaining nodes execute sequentially
    (same as sync mode).
    """
    from small_shop_agent.agent_runtime.graph.nodes import (
        classification_node,
        sentiment_node,
    )

    node_registry: dict[str, Any] = {
        "consistency": consistency_node,
        "merge": merge_node,
        "insight": insight_node,
        "evidence": evidence_node,
        "reply": reply_node,
        "safety": safety_node,
        "approval": approval_node,
    }

    deps = {
        "provider": provider,
        "trace_repo": trace_repo,
        "analysis_repo": analysis_repo,
        "insight_repo": insight_repo,
        "reply_repo": reply_repo,
    }

    # ── Phase A: Concurrent classification + sentiment ──────────────
    state["current_step"] = "classification"

    async def _run_classify():
        import time as _t
        t_start = _t.time()
        try:
            filtered = {k: v for k, v in deps.items() if k in ("provider", "trace_repo")}
            classification_node(state, **filtered)
        except Exception as exc:
            logger.error(f"分类任务失败：{exc}")
            state["errors"].append({"step": "classification", "message": str(exc)})
            state["fallback_used"] = True
            from small_shop_agent.agent_runtime.graph.nodes import fallback_classification_node
            fb_filtered = {k: v for k, v in deps.items() if k in ("trace_repo",)}
            fallback_classification_node(state, **fb_filtered)
        finally:
            state.setdefault("_async_latency_ms", {})["classification"] = int((_t.time() - t_start) * 1000)
        return None

    async def _run_sentiment():
        import time as _t
        t_start = _t.time()
        try:
            filtered = {k: v for k, v in deps.items() if k in ("provider", "trace_repo")}
            sentiment_node(state, **filtered)
        except Exception as exc:
            logger.error(f"情绪分析任务失败：{exc}")
            state["errors"].append({"step": "sentiment_analysis", "message": str(exc)})
            state["fallback_used"] = True
            from small_shop_agent.agent_runtime.graph.nodes import fallback_sentiment_node
            fb_filtered = {k: v for k, v in deps.items() if k in ("trace_repo",)}
            fallback_sentiment_node(state, **fb_filtered)
        finally:
            state.setdefault("_async_latency_ms", {})["sentiment"] = int((_t.time() - t_start) * 1000)
        return None

    await asyncio.gather(_run_classify(), _run_sentiment())

    # ═══ After gather, sequential nodes ═══

    # Phase B onwards: sequential
    sequential_order = [
        "consistency", "merge", "insight", "evidence",
        "reply", "safety", "approval",
    ]
    from small_shop_agent.agent_runtime.graph.edges import route, END

    current = "consistency"  # start sequential after concurrent phase
    while current != END:
        node_fn = node_registry.get(current)
        if node_fn is None:
            state["errors"].append({"step": current, "message": f"未知节点：{current!r}"})
            break

        state["current_step"] = current
        logger.debug(f"智能体流程(异步) — 进入节点：{current}")
        try:
            _dispatch(node_fn, state, provider, trace_repo,
                      analysis_repo, insight_repo, reply_repo)
        except Exception as exc:
            logger.error(f"节点 {current!r} 失败：{exc}")
            state["errors"].append({"step": current, "message": str(exc)})

        current = route(state)

    logger.success(
        f"智能体流程(异步)完成 batch={state['batch_id']}："
        f"当前步骤={state.get('current_step')}, "
        f"错误={len(state['errors'])}, "
        f"警告={len(state['warnings'])}"
    )
    return state
