"""Ollama Provider — local LLM via Ollama HTTP API (chat endpoint)."""
from __future__ import annotations

import json as _json
import os
import re
from typing import Any

import requests

from small_shop_agent.llm.base import BaseLLMProvider
from small_shop_agent.core.config import LLM_TEMPERATURE, LLM_TIMEOUT_SECONDS
from small_shop_agent.prompts.prompt_registry import get_prompt
from small_shop_agent.utils.logger import log_step

_MD_FENCE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


class OllamaProvider(BaseLLMProvider):
    """LLM provider backed by a local Ollama server."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = LLM_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        self._timeout = timeout_seconds

    # ── BaseLLMProvider implementation ──────────────────────────────────

    def classify_reviews(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = self._build_classification_prompt(reviews)
        return self._call_json_model(
            system_prompt=get_prompt("classify_reviews"),
            user_prompt=prompt,
            step_name="classification",
        )

    def analyze_sentiment(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = self._build_sentiment_prompt(reviews)
        return self._call_json_model(
            system_prompt=get_prompt("analyze_sentiment"),
            user_prompt=prompt,
            step_name="sentiment_analysis",
        )

    def generate_insights(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        prompt = self._build_insights_prompt(reviews, analysis)
        return self._call_json_model(
            system_prompt=get_prompt("generate_insights"),
            user_prompt=prompt,
            step_name="insight_generation",
        )

    def draft_replies(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        prompt = self._build_replies_prompt(reviews, analysis)
        return self._call_json_model(
            system_prompt=get_prompt("draft_replies"),
            user_prompt=prompt,
            step_name="reply_drafting",
        )

    def check_safety(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = self._build_safety_prompt(drafts)
        return self._call_json_model(
            system_prompt=get_prompt("check_safety"),
            user_prompt=prompt,
            step_name="safety_check",
        )

    def judge_semantic_safety(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = self._build_safety_prompt(drafts)
        return self._call_json_model(
            system_prompt=get_prompt("semantic_safety_judge"),
            user_prompt=prompt,
            step_name="semantic_safety",
        )

    # ── JSON extraction ────────────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> Any:
        stripped = text.strip()
        if not stripped:
            raise ValueError("LLM 返回空输出，预期 JSON。")
        try:
            return _json.loads(stripped)
        except _json.JSONDecodeError:
            pass
        m = _MD_FENCE.search(stripped)
        if m:
            inner = m.group(1).strip()
            try:
                return _json.loads(inner)
            except _json.JSONDecodeError as exc:
                raise ValueError(f"解析 JSON 失败：{exc}") from exc
        raise ValueError(f"LLM 输出不是合法 JSON。前 200 字：{stripped[:200]!r}")

    # ── Internal HTTP call ─────────────────────────────────────────────

    _REVIEW_ID_RE = re.compile(r"review_id=(\w+)")

    def _call_json_model(
        self, *, system_prompt: str, user_prompt: str, step_name: str
    ) -> Any:
        batch_id: str = getattr(self, "_batch_id", "")
        review_ids: list[str] = self._REVIEW_ID_RE.findall(user_prompt)

        log_step(
            f"{step_name}_ollama_call_start", batch_id or "unknown",
            model=self._model, step=step_name,
            review_count=len(review_ids),
            prompt_len=len(user_prompt),
        )

        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": LLM_TEMPERATURE},
                },
                timeout=float(self._timeout),
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            result = self._extract_json(content)

            log_step(
                f"{step_name}_ollama_call_done", batch_id or "unknown",
                model=self._model, step=step_name,
                response_ok=True,
                output_len=len(content),
            )
            return result

        except Exception as exc:
            log_step(
                f"{step_name}_ollama_call_error", batch_id or "unknown",
                model=self._model, step=step_name,
                response_ok=False,
                error=str(exc),
            )
            raise

    # ── Prompt builders ─────────────────────────────────────────────────

    def _build_classification_prompt(self, reviews: list[dict[str, Any]]) -> str:
        lines = [
            "请用中文对以下顾客评论进行分类。只返回 JSON 数组。",
            "每个对象包含：review_id (str), topics (list[str]), primary_topic (str),",
            "topic_confidence (float 0-1), needs_review (bool)。",
            "有效话题：卫生(hygiene), 等待时间(waiting_time), 服务(service), 产品(product), 环境(environment), 价格(price), 其他(other)。",
            "primary_topic 请使用英文键名（如 hygiene, waiting_time 等）。",
            "",
            "评论列表：",
        ]
        for r in reviews:
            lines.append(
                f"  review_id={r.get('review_id')} | "
                f"rating={r.get('rating')} | "
                f"text={r.get('review_text', r.get('cleaned_text', ''))!r}"
            )
        lines.append("")
        lines.append("JSON only — no markdown, no explanation:")
        return "\n".join(lines)

    def _build_sentiment_prompt(self, reviews: list[dict[str, Any]]) -> str:
        lines = [
            "请用中文分析以下评论的情绪。只返回 JSON 数组。",
            "每个对象：review_id (str), sentiment (positive|neutral|negative),",
            "severity (int 1-5), sentiment_confidence (float 0-1),",
            "is_negative_candidate (bool), analysis_reason (str, 用中文简述)。",
            "",
            "评论列表：",
        ]
        for r in reviews:
            lines.append(
                f"  review_id={r.get('review_id')} | "
                f"rating={r.get('rating')} | "
                f"text={r.get('review_text', r.get('cleaned_text', ''))!r}"
            )
        lines.append("")
        lines.append("JSON only — no markdown, no explanation:")
        return "\n".join(lines)

    def _build_insights_prompt(
        self, reviews: list[dict[str, Any]], analyses: list[dict[str, Any]]
    ) -> str:
        neg = [a for a in analyses if a.get("is_negative_candidate")]
        lines = [
            "请用中文从差评中聚合 Top 3 问题。只返回 JSON 数组（长度 3）。",
            "每个对象：rank (int 1-3), issue_name (str 中文标题), issue_summary (str 中文总结),",
            "topic (str 英文键名), mention_count (int), severity_level (high|medium|low),",
            "priority_score (float 0-1), suggested_action (str 中文建议),",
            "evidence_count (int), evidence_status (sufficient|insufficient),",
            'evidence (list of {review_id: str, evidence_text: str, evidence_reason: str 中文}).',
            "每条证据必须引用下面数据中真实存在的 review_id。",
            "",
            f"差评列表 ({len(neg)} 条)：",
        ]
        for a in neg:
            rid = a.get("review_id", "")
            text = ""
            for r in reviews:
                if r.get("review_id") == rid:
                    text = r.get("review_text", r.get("cleaned_text", ""))
                    break
            lines.append(f"  review_id={rid} | topic={a.get('primary_topic')} | text={text!r}")
        lines.append("")
        lines.append("JSON only — no markdown, no explanation:")
        return "\n".join(lines)

    def _build_replies_prompt(
        self, reviews: list[dict[str, Any]], analyses: list[dict[str, Any]]
    ) -> str:
        neg = [a for a in analyses if a.get("is_negative_candidate")]
        lines = [
            "请用中文为差评撰写回复草稿。只返回 JSON 数组。",
            "每个对象：review_id (str), original_review (str),",
            "draft_text (str 中文回复), approval_status (str = 'pending')。",
            "原则：真诚、克制、不甩锅、不攻击顾客、不编造事实、不承诺无法保证的赔偿、不默认已处罚员工。",
            "",
            f"差评列表 ({len(neg)} 条)：",
        ]
        for a in neg:
            rid = a.get("review_id", "")
            text = ""
            for r in reviews:
                if r.get("review_id") == rid:
                    text = r.get("review_text", r.get("cleaned_text", ""))
                    break
            lines.append(f"  review_id={rid} | topic={a.get('primary_topic')} | text={text!r}")
        lines.append("")
        lines.append("JSON only — no markdown, no explanation:")
        return "\n".join(lines)

    def _build_safety_prompt(self, drafts: list[dict[str, Any]]) -> str:
        lines = [
            "请用中文检查以下回复草稿的安全性。只返回 JSON 数组。",
            "每个对象：review_id (str), safety_status (pass|rewrite_required|blocked),",
            "risk_types (list[str]), safety_reason (str 中文)。",
            "规则：攻击顾客、泄露隐私、声称已处罚员工、编造事实 → blocked；",
            "无依据赔偿承诺、过度营销、推卸责任式语言 → rewrite_required。",
            "",
            "草稿列表：",
        ]
        for d in drafts:
            lines.append(
                f"  review_id={d.get('review_id')} | "
                f"draft_text={d.get('draft_text', '')!r}"
            )
        lines.append("")
        lines.append("JSON only — no markdown, no explanation:")
        return "\n".join(lines)
