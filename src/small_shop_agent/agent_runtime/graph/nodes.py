"""Graph nodes — thin adapters that call pipeline_steps functions.

Each node reads from / writes to an AgentState dict and returns it.
"""
from __future__ import annotations

from typing import Any

from small_shop_agent.agent_runtime.state import AgentState
from small_shop_agent.harness.verification.fallback_rules import (
    classify_many_by_keywords,
    fallback_sentiment_from_rating,
    fallback_insights,
    fallback_reply_for_reviews,
)
from small_shop_agent.services.pipeline_steps import (
    run_classification,
    run_sentiment,
    run_consistency_check,
    merge_classification_sentiment,
    write_analysis_to_db,
    run_insights,
    run_evidence_check,
    run_reply_drafting,
    run_safety_check,
    write_drafts_to_db,
)
from small_shop_agent.core.config import MIN_EVIDENCE_COUNT


def _trace_id(state: AgentState) -> str:
    return f"agent-{state['batch_id']}"


# ── Step nodes ──────────────────────────────────────────────────────────

def classification_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
) -> AgentState:
    state["current_step"] = "classification"
    results = run_classification(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        review_dicts=state["reviews"],
        provider=provider,
        fallback_classify_fn=classify_many_by_keywords,
        trace_repo=trace_repo,
    )
    state["classifications"] = results
    return state


def sentiment_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
) -> AgentState:
    state["current_step"] = "sentiment_analysis"
    results = run_sentiment(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        review_dicts=state["reviews"],
        provider=provider,
        fallback_sentiment_fn=fallback_sentiment_from_rating,
        trace_repo=trace_repo,
    )
    state["sentiments"] = results
    return state


def consistency_node(
    state: AgentState,
    *,
    trace_repo,
) -> AgentState:
    state["current_step"] = "consistency_check"
    run_consistency_check(
        classifications=state["classifications"],
        sentiments=state["sentiments"],
        review_dicts=state["reviews"],
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        trace_repo=trace_repo,
    )
    return state


def merge_node(
    state: AgentState,
    *,
    analysis_repo,
) -> AgentState:
    state["current_step"] = "merge_analysis"
    rows = merge_classification_sentiment(
        state["classifications"],
        state["sentiments"],
    )
    write_analysis_to_db(
        state["batch_id"], state["mode"], rows, analysis_repo,
    )
    state["analysis_rows"] = rows
    return state


def insight_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
    insight_repo,
) -> AgentState:
    state["current_step"] = "insights"

    # ── Phase 1: Enrich analysis_rows with tool-gathered context ──────
    from mcps.reviews.mcp_client import get_mcp_client
    mcp = get_mcp_client()

    batch_id = state["batch_id"]
    # Collect topic counts for negative-candidate topics
    neg_topics: set[str] = set()
    for a in state["analysis_rows"]:
        if a.get("is_negative_candidate"):
            neg_topics.add(a.get("primary_topic", "other"))

    topic_counts: dict[str, int] = {}
    for topic in neg_topics:
        tr = mcp.call("count_by_topic", {"topic": topic, "batch_id": batch_id})
        topic_counts[topic] = tr.get("count", 0) if tr.get("success") else 0

    enriched_rows: list[dict[str, Any]] = []
    for a in state["analysis_rows"]:
        row = dict(a)
        row["_tool_topic_count"] = topic_counts.get(
            row.get("primary_topic", "other"), 0,
        )
        enriched_rows.append(row)

    # ── Phase 2: Generate insights via existing pipeline ───────────────
    insights_list, insight_count, negative_count = run_insights(
        batch_id=batch_id,
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        review_dicts=state["reviews"],
        analysis_rows=enriched_rows,
        provider=provider,
        fallback_insights_fn=fallback_insights,
        trace_repo=trace_repo,
        insight_repo=insight_repo,
    )

    # ── Phase 3: Validate evidence_review_ids ──────────────────────────
    valid_ids = {str(r.get("review_id")) for r in state["reviews"]}
    for ins in insights_list:
        evidence = ins.get("evidence", [])
        eids: list[str] = [e["review_id"] for e in evidence if "review_id" in e]
        quotes: list[str] = [e.get("evidence_text", "") for e in evidence
                            if e.get("evidence_text")]

        ins["evidence_review_ids"] = eids
        ins["evidence_quotes"] = quotes

        valid_eids = [rid for rid in eids if rid in valid_ids]
        invalid_count = len(eids) - len(valid_eids)

        if invalid_count > 0:
            ins["evidence_review_ids"] = valid_eids
            state["warnings"].append({
                "step": "insights",
                "message": (
                    f"洞察 '{ins.get('issue_name', '?')}' 有 "
                    f"{invalid_count} 个无效的 evidence_review_ids 已移除"
                ),
            })

        if len(valid_eids) < 2:
            ins["evidence_status"] = "evidence_insufficient"
            ins["evidence_count"] = len(valid_eids)

    state["insights"] = insights_list
    state["_insight_count"] = insight_count
    state["_negative_count"] = negative_count
    return state


def evidence_node(
    state: AgentState,
    *,
    trace_repo,
    insight_repo,
) -> AgentState:
    state["current_step"] = "evidence_check"
    valid_ids = {str(r.get("review_id")) for r in state["reviews"]}
    evidence_count, ev_valid, ev_rejected, ev_insufficient = run_evidence_check(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        insights=state["insights"],
        review_dicts=state["reviews"],
        valid_review_ids=valid_ids,
        trace_repo=trace_repo,
        insight_repo=insight_repo,
    )
    state["_evidence_count"] = evidence_count
    if ev_rejected > 0 or ev_insufficient > 0:
        state["warnings"].append({
            "step": "evidence_check",
            "message": f"证据被拒绝={ev_rejected}, 证据不足={ev_insufficient}",
        })
    return state


def reply_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
) -> AgentState:
    state["current_step"] = "reply_drafting"

    # ── Phase 1: Gather tool context ──────────────────────────────────
    from mcps.reviews.mcp_client import get_mcp_client
    mcp = get_mcp_client()

    safety = mcp.call("get_safety_policy_snippet", {"policy_type": "all"})
    safety_reasons = safety.get("reasons", {}) if safety["success"] else {}
    safety_blocked = [k for k, v in safety.get("patterns", {}).items()
                      if k in ("attack_customer", "disclose_privacy",
                               "claim_employee_punished", "fabricated_fact")]
    safety_rewrite = [k for k, v in safety.get("patterns", {}).items()
                      if k in ("unfounded_compensation", "over_marketing",
                               "defensive_or_blame_shift")]

    # ── Phase 1b: Memory retrieval ────────────────────────────────────
    from small_shop_agent.agent_runtime.memory_retriever import MemoryRetriever

    neg_rids = {a["review_id"] for a in state["analysis_rows"]
                if a.get("is_negative_candidate")}

    # Extract keywords from negative-candidate review texts
    neg_review_texts = [
        str(r.get("review_text", ""))
        for r in state["reviews"]
        if r.get("review_id") in neg_rids
    ]
    all_text = " ".join(neg_review_texts)
    simple_keywords = list({w for w in all_text.split() if len(w) >= 2})[:20]

    retriever = MemoryRetriever()
    memory_results = retriever.retrieve(
        store_type="coffee_shop",
        keywords=simple_keywords,
        limit_per_type=3,
    )
    approved_memos = memory_results["approved"]
    rejected_memos = memory_results["rejected"]
    safety_memos = memory_results["safety"]
    memory_hit = len(approved_memos) + len(rejected_memos) + len(safety_memos)
    state["_memory_hit_count"] = memory_hit

    # Enrich each review dict with safety policy context
    enriched_reviews: list[dict[str, Any]] = []

    for r in state["reviews"]:
        row = dict(r)
        rid = row.get("review_id", "")
        if rid in neg_rids:
            row["_tool_safety_rules"] = safety_reasons
            row["_tool_safety_blocked_keywords"] = safety_blocked
            row["_tool_safety_rewrite_keywords"] = safety_rewrite
            row["_tool_memory_approved"] = [
                m["content"] for m in approved_memos
            ]
            row["_tool_memory_rejected"] = [
                f"REJECTED: {m['content']}" for m in rejected_memos
            ]
            row["_tool_memory_safety"] = [
                f"SAFETY: {m['content']}" for m in safety_memos
            ]
        enriched_reviews.append(row)

    trace_repo.log_step(
        trace_id=_trace_id(state),
        batch_id=state["batch_id"],
        step_name="reply_drafting_prep",
        status="passed",
        input_summary=f"{len(neg_rids)} negative candidates",
        output_summary=(
            f"tool_context: safety_categories={len(safety_reasons)}, "
            f"blocked_rules={len(safety_blocked)}, "
            f"rewrite_rules={len(safety_rewrite)}, "
            f"memory_hits={memory_hit}"
        ),
        latency_ms=0,
        model_name=state["model_name"],
    )

    # ── Phase 2: Generate drafts ──────────────────────────────────────
    drafts, draft_count = run_reply_drafting(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        review_dicts=enriched_reviews,
        analysis_rows=state["analysis_rows"],
        provider=provider,
        fallback_reply_fn=fallback_reply_for_reviews,
        trace_repo=trace_repo,
    )

    state["reply_drafts"] = drafts
    state["_draft_count"] = draft_count
    return state


def safety_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
    reply_repo,
) -> AgentState:
    state["current_step"] = "safety_check"
    safe_drafts, pass_count, rewrite_count, blocked_count = run_safety_check(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        drafts=state["reply_drafts"],
        provider=provider,
        trace_repo=trace_repo,
    )
    write_drafts_to_db(
        state["batch_id"], state["mode"], state["model_name"],
        safe_drafts, reply_repo,
    )
    state["safety_results"] = safe_drafts
    state["_pass_count"] = pass_count
    state["_blocked_count"] = blocked_count
    if blocked_count > 0:
        state["warnings"].append({
            "step": "safety_check",
            "message": f"{blocked_count} 条回复被拦截",
        })
    return state


# ── Retry / fallback nodes ──────────────────────────────────────────────

def classification_retry_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
) -> AgentState:
    state["current_step"] = "classification_retry"
    state.setdefault("_retry_counts", {})["classification"] = (
        state["_retry_counts"].get("classification", 0) + 1
    )
    results = run_classification(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        review_dicts=state["reviews"],
        provider=provider,
        fallback_classify_fn=classify_many_by_keywords,
        trace_repo=trace_repo,
    )
    state["classifications"] = results
    return state


def fallback_classification_node(
    state: AgentState,
    *,
    trace_repo,
) -> AgentState:
    state["current_step"] = "fallback_classification"
    state["fallback_used"] = True
    state["warnings"].append({
        "step": "classification",
        "message": "LLM 分类失败 — 使用关键词降级。",
    })
    results = classify_many_by_keywords(state["reviews"])
    state["classifications"] = results
    trace_repo.log_step(
        trace_id=_trace_id(state),
        batch_id=state["batch_id"],
        step_name="classification",
        status="warning",
        input_summary=f"{len(state['reviews'])} reviews",
        output_summary="降级分类（关键词规则）",
        latency_ms=0,
        model_name=state["model_name"],
    )
    return state


def sentiment_retry_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
) -> AgentState:
    state["current_step"] = "sentiment_retry"
    state.setdefault("_retry_counts", {})["sentiment"] = (
        state["_retry_counts"].get("sentiment", 0) + 1
    )
    results = run_sentiment(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        review_dicts=state["reviews"],
        provider=provider,
        fallback_sentiment_fn=fallback_sentiment_from_rating,
        trace_repo=trace_repo,
    )
    state["sentiments"] = results
    return state


def fallback_sentiment_node(
    state: AgentState,
    *,
    trace_repo,
) -> AgentState:
    state["current_step"] = "fallback_sentiment"
    state["fallback_used"] = True
    state["warnings"].append({
        "step": "sentiment_analysis",
        "message": "LLM 情绪分析失败 — 使用评分降级。",
    })
    results = fallback_sentiment_from_rating(state["reviews"])
    state["sentiments"] = results
    trace_repo.log_step(
        trace_id=_trace_id(state),
        batch_id=state["batch_id"],
        step_name="sentiment_analysis",
        status="warning",
        input_summary=f"{len(state['reviews'])} reviews",
        output_summary="降级情绪（评分规则）",
        latency_ms=0,
        model_name=state["model_name"],
    )
    return state


def regenerate_insight_node(
    state: AgentState,
    *,
    provider,
    trace_repo,
    insight_repo,
) -> AgentState:
    state["current_step"] = "regenerate_insight"
    state.setdefault("_retry_counts", {})["evidence"] = (
        state["_retry_counts"].get("evidence", 0) + 1
    )
    insights_list, insight_count, negative_count = run_insights(
        batch_id=state["batch_id"],
        trace_id=_trace_id(state),
        mode=state["mode"],
        model_name=state["model_name"],
        review_dicts=state["reviews"],
        analysis_rows=state["analysis_rows"],
        provider=provider,
        fallback_insights_fn=fallback_insights,
        trace_repo=trace_repo,
        insight_repo=insight_repo,
    )
    state["insights"] = insights_list
    state["_insight_count"] = insight_count
    return state


def mark_insight_insufficient_node(
    state: AgentState,
    *,
    insight_repo,
    trace_repo,
) -> AgentState:
    state["current_step"] = "mark_insight_insufficient"
    state["warnings"].append({
        "step": "evidence_check",
        "message": "重试后仍无有效证据 — 洞察已标记为证据不足。",
    })
    for ins in state.get("insights", []):
        ins["evidence_status"] = "insufficient"
        ins["evidence_count"] = 0
    trace_repo.log_step(
        trace_id=_trace_id(state),
        batch_id=state["batch_id"],
        step_name="evidence_check",
        status="warning",
        input_summary=f"{len(state.get('insights', []))} insights",
        output_summary="所有洞察已标记为证据不足",
        latency_ms=0,
        model_name=state["model_name"],
    )
    return state


def approval_node(state: AgentState) -> AgentState:
    state["current_step"] = "human_approval"
    pending = [d for d in state["safety_results"]
               if d.get("approval_status") == "pending"]
    if pending:
        state["need_human_review"] = True
        state["warnings"].append({
            "step": "human_approval",
            "message": f"{len(pending)} 条草稿待人工审批",
        })
    return state
