"""WorkflowService — orchestrates the end-to-end review analysis pipeline."""
from __future__ import annotations

import time
from typing import Any

from loguru import logger

from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.repositories.insight_repository import InsightRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.demo.demo_loader import DemoLoader
from small_shop_agent.llm.mock_provider import MockProvider
from small_shop_agent.llm.base import BaseLLMProvider
from small_shop_agent.utils.logger import log_step
from small_shop_agent.domain.business_rules import TOPIC_CN_MAP
from small_shop_agent.harness.verification.fallback_rules import classify_by_keywords
from small_shop_agent.services.pipeline_steps import (
    run_batch_validation,
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
    finalize_batch,
)
from small_shop_agent.services.types import WorkflowResult, WorkflowStatusResult


class WorkflowService:
    """Orchestrates the full analysis pipeline: classify → sentiment → insights → replies → safety."""

    def __init__(self) -> None:
        self._batch_repo = BatchRepository()
        self._review_repo = ReviewRepository()
        self._analysis_repo = AnalysisRepository()
        self._insight_repo = InsightRepository()
        self._reply_repo = ReplyRepository()
        self._trace_repo = TraceRepository()
        self._demo_loader = DemoLoader()
        self._mock = MockProvider(self._demo_loader)

    # ── Public API ──────────────────────────────────────────────────────────

    def run_analysis(self, batch_id: str, mode: str = "demo") -> WorkflowResult:
        """Run the analysis pipeline. 'demo'/'mock' uses MockProvider; 'live'/'openai' uses OpenAI."""
        if mode in ("demo", "mock"):
            return self.run_demo_analysis(batch_id)
        try:
            from small_shop_agent.llm.llm_router import get_llm_provider
            provider = get_llm_provider(mode)
        except Exception as exc:
            return {
                "success": False, "batch_id": batch_id, "mode": mode, "summary": {},
                "error": f"Failed to resolve provider for mode={mode!r}: {exc}",
            }
        return self._run_provider_analysis(batch_id, provider, mode)

    def run_demo_analysis(self, batch_id: str) -> WorkflowResult:
        """Execute the full demo analysis pipeline using MockProvider.

        Steps: validate → classify → sentiment → merge → insights → evidence
               → reply → safety → write DB → finalize.
        """
        return self._run_pipeline(
            batch_id=batch_id,
            mode="demo",
            provider=self._mock,
            model_name="demo",
            skip_live_extra_traces=True,
        )

    # ── Live Provider Analysis ───────────────────────────────────────────────

    def _run_provider_analysis(
        self, batch_id: str, provider: BaseLLMProvider, mode: str
    ) -> WorkflowResult:
        """Execute the full Live/OpenAI analysis pipeline.

        Same step sequence as demo, but each LLM call goes through
        Schema Guard + Structured Retry. Never crashes — uses fallbacks.
        """
        model_name = getattr(provider, "_model", mode)
        provider._batch_id = batch_id
        return self._run_pipeline(
            batch_id=batch_id,
            mode=mode,
            provider=provider,
            model_name=model_name,
            skip_live_extra_traces=False,
        )

    # ── Internal pipeline orchestrator ─────────────────────────────────────

    def _run_pipeline(
        self,
        batch_id: str,
        mode: str,
        provider,
        model_name: str,
        skip_live_extra_traces: bool,
    ) -> WorkflowResult:
        """Shared pipeline orchestrator for both demo and live modes."""
        t_start = time.time()
        trace_id = f"trace-{batch_id}"

        # Step 0: Validate batch
        err = run_batch_validation(
            batch_id=batch_id, trace_id=trace_id, mode=mode,
            model_name=model_name,
            batch_repo=self._batch_repo, review_repo=self._review_repo,
            trace_repo=self._trace_repo,
        )
        if err is not None:
            return err

        reviews = self._review_repo.list_reviews(batch_id, is_valid=True)
        review_count = len(reviews)
        log_step("validate_batch", batch_id, status="ok", review_count=review_count, mode=mode)
        review_dicts: list[dict[str, Any]] = [dict(r) for r in reviews]

        # Live-mode extra trace steps
        if not skip_live_extra_traces:
            batch = self._batch_repo.get_batch(batch_id)
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="input_validation", status="passed",
                input_summary=f"{batch.get('total_rows', review_count)} raw reviews",
                output_summary=f"{review_count} valid reviews",
                latency_ms=0, model_name=model_name,
            )
            valid_review_ids = {str(r.get("review_id")) for r in review_dicts if r.get("review_id")}
            batch_reviews_all = self._review_repo.list_reviews(batch_id, is_valid=None)
            dup_count = sum(1 for r in batch_reviews_all if int(getattr(r, "is_duplicate", 0) or 0))
            empty_count = sum(1 for r in batch_reviews_all if int(getattr(r, "is_empty", 0) or 0))
            self._trace_repo.log_step(
                trace_id=trace_id, batch_id=batch_id,
                step_name="data_cleaning", status="warning" if (dup_count or empty_count) else "passed",
                input_summary=f"{len(batch_reviews_all)} raw reviews",
                output_summary=f"{review_count} valid, {empty_count} empty, {dup_count} duplicate",
                latency_ms=0, model_name=model_name,
            )

        try:
            # Step 1: Classification
            classifications = run_classification(
                batch_id=batch_id, trace_id=trace_id, mode=mode,
                model_name=model_name, review_dicts=review_dicts,
                provider=provider,
                fallback_classify_fn=self._fallback_classify,
                trace_repo=self._trace_repo,
            )

            # Step 2: Sentiment
            sentiments = run_sentiment(
                batch_id=batch_id, trace_id=trace_id, mode=mode,
                model_name=model_name, review_dicts=review_dicts,
                provider=provider,
                fallback_sentiment_fn=self._fallback_sentiment,
                trace_repo=self._trace_repo,
            )

            # Step 2b: Consistency check (classification ↔ sentiment alignment)
            run_consistency_check(
                classifications=classifications,
                sentiments=sentiments,
                review_dicts=review_dicts,
                batch_id=batch_id,
                trace_id=trace_id,
                mode=mode,
                model_name=model_name,
                trace_repo=self._trace_repo,
            )

            # Step 3: Merge + write analysis
            analysis_rows = merge_classification_sentiment(classifications, sentiments)
            write_analysis_to_db(batch_id, mode, analysis_rows, self._analysis_repo)

            # Step 4: Insights + evidence
            insights, insight_count, negative_count = run_insights(
                batch_id=batch_id, trace_id=trace_id, mode=mode,
                model_name=model_name, review_dicts=review_dicts,
                analysis_rows=analysis_rows, provider=provider,
                fallback_insights_fn=self._fallback_insights,
                trace_repo=self._trace_repo, insight_repo=self._insight_repo,
            )

            # Step 5: Evidence check (live path uses valid_review_ids from live extra traces)
            vid_set = valid_review_ids if not skip_live_extra_traces else {str(r.get("review_id")) for r in review_dicts}
            evidence_count, _, _, _ = run_evidence_check(
                batch_id=batch_id, trace_id=trace_id, mode=mode,
                model_name=model_name, insights=insights,
                review_dicts=review_dicts, valid_review_ids=vid_set,
                trace_repo=self._trace_repo, insight_repo=self._insight_repo,
            )

            # Step 6: Reply drafting
            drafts, draft_count = run_reply_drafting(
                batch_id=batch_id, trace_id=trace_id, mode=mode,
                model_name=model_name, review_dicts=review_dicts,
                analysis_rows=analysis_rows, provider=provider,
                fallback_reply_fn=self._fallback_reply,
                trace_repo=self._trace_repo,
            )

            # Step 7: Safety check
            safe_drafts, pass_count, rewrite_count, blocked_count = run_safety_check(
                batch_id=batch_id, trace_id=trace_id, mode=mode,
                model_name=model_name, drafts=drafts,
                provider=provider,
                trace_repo=self._trace_repo,
            )

            # Step 8: Write drafts to DB
            write_drafts_to_db(batch_id, mode, model_name, safe_drafts, self._reply_repo)

            # Step 9: Finalize
            result = finalize_batch(
                batch_id=batch_id, mode=mode, review_count=review_count,
                negative_count=negative_count, insight_count=insight_count,
                draft_count=draft_count, blocked_count=blocked_count,
                rewrite_count=rewrite_count, pass_count=pass_count,
                evidence_count=evidence_count, trace_count=8,
                safe_drafts=safe_drafts, batch_repo=self._batch_repo,
            )

            total_latency = int((time.time() - t_start) * 1000)
            logger.success(
                f"{'演示' if mode == 'demo' else '在线'}分析完成 batch={batch_id}："
                f"评论={review_count}, 洞察={insight_count}, 草稿={draft_count}, "
                f"耗时={total_latency}ms"
            )
            return result

        except Exception as exc:
            log_step(f"{mode}_analysis_error", batch_id, status="failed", error=str(exc), mode=mode)
            logger.error(f"分析失败 batch={batch_id}：{exc}")
            self._batch_repo.update_status(batch_id, "failed", error_message=str(exc))
            return {"success": False, "batch_id": batch_id, "mode": mode,
                    "summary": {}, "error": str(exc)}

    # ── Fallback Rules ──────────────────────────────────────────────────────

    @staticmethod
    def _fallback_classify(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keyword-based classification fallback — never raises."""
        from small_shop_agent.harness.verification.fallback_rules import classify_many_by_keywords
        return classify_many_by_keywords(reviews)

    @staticmethod
    def _fallback_sentiment(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rating-based sentiment fallback."""
        results: list[dict[str, Any]] = []
        for r in reviews:
            rid = r.get("review_id", "")
            rating = int(r.get("rating", 3))
            if rating <= 2:
                sentiment, severity = "negative", 4 if rating == 1 else 3
            elif rating == 3:
                sentiment, severity = "neutral", 2
            else:
                sentiment, severity = "positive", 1
            results.append({
                "review_id": rid, "sentiment": sentiment, "severity": severity,
                "sentiment_confidence": 0.60, "is_negative_candidate": sentiment == "negative",
                "analysis_reason": f"Fallback — rating={rating}",
            })
        return results

    @staticmethod
    def _fallback_insights(
        reviews: list[dict[str, Any]], analyses: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Topic-counting insight fallback — top 3 topics with up to 3 evidence each."""
        neg_analyses = [a for a in analyses if a.get("is_negative_candidate")]
        topic_counts: dict[str, list[str]] = {}
        for a in neg_analyses:
            topic = a.get("primary_topic", "other")
            topic_counts.setdefault(topic, []).append(a.get("review_id", ""))
        sorted_topics = sorted(topic_counts.items(), key=lambda x: len(x[1]), reverse=True)[:3]

        results: list[dict[str, Any]] = []
        for rank, (topic, review_ids) in enumerate(sorted_topics, 1):
            three_ids = review_ids[:3]
            evidence = []
            for rid in three_ids:
                text = ""
                for r in reviews:
                    if r.get("review_id") == rid:
                        text = str(r.get("review_text", ""))[:80]
                        break
                evidence.append({"review_id": rid, "evidence_text": text, "evidence_reason": "Fallback evidence."})
            topic_actions = {
                "hygiene": "建议排查清洁流程，重点检查异物来源和卫生死角，建立定时巡检制度。",
                "waiting_time": "建议优化出餐流程，高峰期增加人手或提前备料，等待超15分钟主动致歉。",
                "service": "建议安排服务礼仪培训，建立客诉反馈机制，每周例会复盘典型服务案例。",
                "price": "建议复盘定价策略，对比同商圈竞品价格，评估性价比优化空间。",
                "environment": "建议检查店内环境，评估噪音、座位舒适度等影响体验的因素。",
                "product": "建议复查产品制作流程，确保出餐品质稳定。",
            }
            topic_cn = TOPIC_CN_MAP.get(topic, topic)
            action = topic_actions.get(topic, "请人工核实具体问题，结合评论内容判断优先级。")
            results.append({
                "rank": rank, "issue_name": f"{topic_cn}相关问题", "topic": topic,
                "issue_summary": f"共 {len(review_ids)} 条相关评论。",
                "mention_count": len(review_ids), "severity_level": "medium",
                "priority_score": 0.60, "suggested_action": action,
                "evidence_count": len(three_ids),
                "evidence_status": "sufficient" if len(three_ids) >= 2 else "evidence_insufficient",
                "evidence": evidence,
            })
        return results

    @staticmethod
    def _fallback_reply(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fixed-template reply fallback."""
        template = (
            "您好，非常抱歉这次体验没有达到您的期待。"
            "我们已经记录您反馈的问题，会认真复盘当天的服务流程。"
            "感谢您愿意指出问题，也欢迎您后续继续反馈。"
        )
        results: list[dict[str, Any]] = []
        for r in reviews:
            rid = r.get("review_id", "")
            original = str(r.get("review_text", r.get("cleaned_text", "")))
            results.append({
                "review_id": rid, "original_review": original,
                "draft_text": template, "approval_status": "pending",
            })
        return results

    # ── Public API (continued) ───────────────────────────────────────────────

    def get_workflow_status(self, batch_id: str) -> WorkflowStatusResult:
        """Return batch status, trace summary, and data counts."""
        batch = self._batch_repo.get_batch(batch_id)
        if batch is None:
            return {
                "success": False,
                "batch_id": batch_id,
                "batch": None,
                "traces": [],
                "counts": {},
                "error": f"Batch not found: {batch_id}",
            }

        traces = self._trace_repo.get_traces(batch_id)
        analysis_list = self._analysis_repo.list_analysis(batch_id)
        insights_list = self._insight_repo.get_top_issues(batch_id)
        drafts_list = self._reply_repo.list_drafts(batch_id)

        return {
            "success": True,
            "batch_id": batch_id,
            "batch": dict(batch),
            "traces": [dict(t) for t in traces],
            "counts": {
                "reviews": self._review_repo.count_reviews(batch_id),
                "valid_reviews": self._review_repo.count_reviews(batch_id, is_valid=True),
                "analysis": len(analysis_list),
                "insights": len(insights_list),
                "drafts": len(drafts_list),
            },
            "error": None,
        }
