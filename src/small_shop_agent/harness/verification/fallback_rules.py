"""Unified fallback rules — keyword → topic classification used by all fallback paths."""
from __future__ import annotations

from typing import Any

# Keyword groups → topic mapping (order matters: first match wins)
KEYWORD_TOPIC_RULES: list[tuple[list[str], str]] = [
    (["卫生", "脏", "虫", "异味", "异物", "头发"], "hygiene"),
    (["等", "排队", "太慢", "半小时", "20分钟", "30分钟", "太久"], "waiting_time"),
    (["服务", "态度", "员工", "服务员", "店员"], "service"),
    (["价格", "贵", "不值", "太贵", "性价比"], "price"),
    (["环境", "装修", "座位", "吵", "安静", "空调"], "environment"),
    (["咖啡", "味道", "口感", "难吃", "难喝"], "product"),
]


def classify_by_keywords(text: str, rating: int = 3) -> str:
    """Infer topic from review text keywords. Falls back to rating heuristic.

    Returns an English topic key (e.g. 'hygiene', 'waiting_time').
    """
    lower = text.lower()
    for keywords, topic in KEYWORD_TOPIC_RULES:
        if any(kw in lower for kw in keywords):
            return topic
    if rating <= 2:
        return "waiting_time"
    return "other"


def classify_many_by_keywords(
    reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build classification results for a list of reviews using keyword rules."""
    results: list[dict[str, Any]] = []
    for r in reviews:
        rid = r.get("review_id", "")
        rating = int(r.get("rating", 3))
        text = str(r.get("review_text", r.get("cleaned_text", "")))
        topic = classify_by_keywords(text, rating)
        results.append({
            "review_id": rid,
            "topics": [topic],
            "primary_topic": topic,
            "topic_confidence": 0.60,
            "needs_review": rating <= 2,
        })
    return results


def fallback_sentiment_from_rating(
    reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build sentiment analysis results from rating alone (no LLM needed)."""
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
            "review_id": rid,
            "sentiment": sentiment,
            "severity": severity,
            "sentiment_confidence": 0.60,
            "is_negative_candidate": sentiment == "negative",
            "analysis_reason": f"Fallback — rating={rating}",
        })
    return results


FALLBACK_REPLY_TEMPLATE: str = (
    "您好，非常抱歉这次体验没有达到您的期待。"
    "我们已经记录您反馈的问题，会认真复盘当天的服务流程。"
    "感谢您愿意指出问题，也欢迎您后续继续反馈。"
)


def fallback_insights(
    reviews: list[dict[str, Any]], analyses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Topic-counting insight fallback — top 3 topics with up to 3 evidence each."""
    from small_shop_agent.domain.business_rules import TOPIC_CN_MAP

    neg_analyses = [a for a in analyses if a.get("is_negative_candidate")]
    topic_counts: dict[str, list[str]] = {}
    for a in neg_analyses:
        topic = a.get("primary_topic", "other")
        topic_counts.setdefault(topic, []).append(a.get("review_id", ""))
    sorted_topics = sorted(topic_counts.items(), key=lambda x: len(x[1]), reverse=True)[:3]

    topic_actions = {
        "hygiene": "建议排查清洁流程，重点检查异物来源和卫生死角，建立定时巡检制度。",
        "waiting_time": "建议优化出餐流程，高峰期增加人手或提前备料，等待超15分钟主动致歉。",
        "service": "建议安排服务礼仪培训，建立客诉反馈机制，每周例会复盘典型服务案例。",
        "price": "建议复盘定价策略，对比同商圈竞品价格，评估性价比优化空间。",
        "environment": "建议检查店内环境，评估噪音、座位舒适度等影响体验的因素。",
        "product": "建议复查产品制作流程，确保出餐品质稳定。",
    }

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


def fallback_reply_for_reviews(
    reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate fixed-template reply drafts for a list of negative reviews."""
    results: list[dict[str, Any]] = []
    for r in reviews:
        rid = r.get("review_id", "")
        original = str(r.get("review_text", r.get("cleaned_text", "")))
        results.append({
            "review_id": rid,
            "original_review": original,
            "draft_text": FALLBACK_REPLY_TEMPLATE,
            "approval_status": "pending",
        })
    return results
