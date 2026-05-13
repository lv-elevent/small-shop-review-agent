"""MockProvider — deterministic demo LLM provider backed by DemoLoader JSON data."""
from __future__ import annotations

from typing import Any

from small_shop_agent.demo.demo_loader import DemoLoader
from small_shop_agent.harness.verification.fallback_rules import classify_by_keywords
from small_shop_agent.llm.base import BaseLLMProvider


class MockProvider(BaseLLMProvider):
    """Deterministic LLM provider that returns pre-computed demo data."""

    def __init__(self, demo_loader: DemoLoader | None = None) -> None:
        self._loader = demo_loader or DemoLoader()

        # Build lookup dicts at init for O(1) access
        self._class_map: dict[str, dict[str, Any]] = {
            e["review_id"]: e for e in self._loader.load_mock_classification()
        }
        self._sentiment_map: dict[str, dict[str, Any]] = {
            e["review_id"]: e for e in self._loader.load_mock_sentiment()
        }
        self._reply_map: dict[str, dict[str, Any]] = {
            e["review_id"]: e for e in self._loader.load_mock_replies()
        }
        self._insights: list[dict[str, Any]] = self._loader.load_mock_insights()

        # Safety mapping: review_id → (safety_status, risk_types, safety_reason)
        self._safety_map: dict[str, tuple[str, list[str], str]] = {
            "COFF04": ("pass", [], "回复语气克制，没有攻击、虚假承诺或编造事实。"),
            "COFF06": (
                "rewrite_required",
                ["over_marketing"],
                "回复语气尚可但未充分回应服务质量问题，建议增强具体改进措施的描述。",
            ),
            "COFF08": (
                "blocked",
                ["fabricated_fact"],
                "无法确认异物具体来源，回复不宜在未调查清楚前作出任何关于调查结果的承诺。",
            ),
            "COFF12": ("pass", [], "回复真诚致歉并给出改进承诺，语气克制。"),
            "COFF13": ("pass", [], "回复具体承认了卫生问题并给出了整改措施，语气得当。"),
        }

        # Semantic safety mapping: review_id → (semantic_status, risk_types, reason, confidence)
        self._semantic_safety_map: dict[str, tuple[str, list[str], str, float]] = {
            "COFF04": ("pass", [], "语义分析：回复真诚，语气克制，无安全风险。", 0.95),
            "COFF06": (
                "rewrite_required",
                ["over_promise"],
                "语义分析：回复中承诺加强培训，但措辞略显过度，建议更聚焦问题本身。",
                0.82,
            ),
            "COFF08": (
                "blocked",
                ["fake_fact"],
                "语义分析：回复暗示已进行调查并确认了问题来源，存在编造事实的风险。",
                0.91,
            ),
            "COFF12": ("pass", [], "语义分析：回复真诚致歉且未发现安全风险。", 0.93),
            "COFF13": ("pass", [], "语义分析：回复具体且克制，无安全问题。", 0.94),
        }

    # ── Public Methods ─────────────────────────────────────────────────

    def classify_reviews(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return mock classification for each valid, non-duplicate review."""
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for r in reviews:
            rid = str(r.get("review_id", ""))
            text = str(r.get("review_text", "")).strip()
            rating = int(r.get("rating", 3))

            if not text:
                continue
            if rid in seen:
                continue
            seen.add(rid)

            if rid in self._class_map:
                results.append(dict(self._class_map[rid]))
            else:
                results.append(self._fallback_classify(rid, rating))
        return results

    def analyze_sentiment(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return mock sentiment analysis for each valid, non-duplicate review."""
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for r in reviews:
            rid = str(r.get("review_id", ""))
            text = str(r.get("review_text", "")).strip()
            rating = int(r.get("rating", 3))

            if not text:
                continue
            if rid in seen:
                continue
            seen.add(rid)

            if rid in self._sentiment_map:
                results.append(dict(self._sentiment_map[rid]))
            else:
                results.append(self._fallback_sentiment(rid, rating))
        return results

    def generate_insights(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return pre-defined top 3 insights with evidence."""
        return [dict(i) for i in self._insights]

    def draft_replies(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate drafts only for negative candidate reviews."""
        neg_ids = {
            a["review_id"] for a in analysis if a.get("is_negative_candidate")
        }
        results: list[dict[str, Any]] = []
        for rid in sorted(neg_ids):
            if rid in self._reply_map:
                entry = dict(self._reply_map[rid])
                entry.setdefault("safety_status", "pass")
                entry.setdefault("risk_types", [])
                entry.setdefault("safety_reason", "")
                results.append(entry)
            else:
                original = self._find_review_text(reviews, rid)
                results.append({
                    "review_id": rid,
                    "original_review": original,
                    "draft_text": "感谢您的反馈，我们会认真改进。",
                    "safety_status": "pass",
                    "risk_types": [],
                    "safety_reason": "",
                    "approval_status": "pending",
                })
        return results

    def check_safety(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply pre-defined safety statuses to each draft."""
        results: list[dict[str, Any]] = []
        for d in drafts:
            rid = d.get("review_id", "")
            entry = dict(d)
            if rid in self._safety_map:
                status, risks, reason = self._safety_map[rid]
                entry["safety_status"] = status
                entry["risk_types"] = risks
                entry["safety_reason"] = reason
                if status == "blocked":
                    entry["approval_status"] = "blocked"
            else:
                entry["safety_status"] = "pass"
                entry["risk_types"] = []
                entry["safety_reason"] = "Mock — 未匹配到特定安全检查规则，默认通过。"
            results.append(entry)
        return results

    def judge_semantic_safety(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return pre-defined semantic safety results for known review IDs."""
        results: list[dict[str, Any]] = []
        for d in drafts:
            rid = d.get("review_id", "")
            if rid in self._semantic_safety_map:
                status, risks, reason, conf = self._semantic_safety_map[rid]
            else:
                status, risks, reason, conf = ("pass", [], "Mock — 语义判定未匹配，默认通过。", 0.80)
            results.append({
                "reply_id": rid,
                "semantic_status": status,
                "risk_types": list(risks),
                "reason": reason,
                "confidence": conf,
            })
        return results

    # ── Deterministic Fallbacks ────────────────────────────────────────

    @staticmethod
    def _fallback_classify(review_id: str, rating: int) -> dict[str, Any]:
        topic = classify_by_keywords("", rating)
        return {
            "review_id": review_id,
            "topics": [topic],
            "primary_topic": topic,
            "topic_confidence": 0.80,
            "needs_review": rating <= 2,
        }

    @staticmethod
    def _fallback_sentiment(review_id: str, rating: int) -> dict[str, Any]:
        if rating >= 4:
            sent, sev = "positive", 1
        elif rating == 3:
            sent, sev = "neutral", 2
        else:
            sent, sev = "negative", 4
        return {
            "review_id": review_id,
            "sentiment": sent,
            "severity": sev,
            "sentiment_confidence": 0.80,
            "is_negative_candidate": sent == "negative",
            "analysis_reason": f"Mock fallback — 基于评分 {rating} 推断。",
        }

    @staticmethod
    def _find_review_text(reviews: list[dict[str, Any]], review_id: str) -> str:
        for r in reviews:
            if str(r.get("review_id")) == review_id:
                return str(r.get("review_text", ""))
        return ""
