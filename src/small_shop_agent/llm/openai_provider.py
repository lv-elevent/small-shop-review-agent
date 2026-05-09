"""OpenAI Provider — Live LLM via OpenAI-compatible API. Contract-only, no harness logic."""
from __future__ import annotations

import json as _json
import os
import re
from typing import Any

from small_shop_agent.llm.base import BaseLLMProvider

_MD_FENCE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by an OpenAI-compatible chat completion API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "").strip()
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._timeout = timeout_seconds

        timeout_env = os.environ.get("OPENAI_TIMEOUT_SECONDS")
        if timeout_env is not None:
            try:
                self._timeout = int(timeout_env)
            except ValueError:
                pass

    # ── BaseLLMProvider implementation ──────────────────────────────────

    def classify_reviews(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = self._build_classification_prompt(reviews)
        return self._call_json_model(
            system_prompt=_CLASSIFY_SYSTEM,
            user_prompt=prompt,
            step_name="classification",
        )

    def analyze_sentiment(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = self._build_sentiment_prompt(reviews)
        return self._call_json_model(
            system_prompt=_SENTIMENT_SYSTEM,
            user_prompt=prompt,
            step_name="sentiment_analysis",
        )

    def generate_insights(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        prompt = self._build_insights_prompt(reviews, analysis)
        return self._call_json_model(
            system_prompt=_INSIGHTS_SYSTEM,
            user_prompt=prompt,
            step_name="insight_generation",
        )

    def draft_replies(
        self, reviews: list[dict[str, Any]], analysis: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        prompt = self._build_replies_prompt(reviews, analysis)
        return self._call_json_model(
            system_prompt=_REPLIES_SYSTEM,
            user_prompt=prompt,
            step_name="reply_drafting",
        )

    def check_safety(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = self._build_safety_prompt(drafts)
        return self._call_json_model(
            system_prompt=_SAFETY_SYSTEM,
            user_prompt=prompt,
            step_name="safety_check",
        )

    # ── JSON extraction ─────────────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> Any:
        """Parse JSON from LLM output. Handles raw JSON and ```json fences."""
        stripped = text.strip()
        if not stripped:
            raise ValueError("LLM returned empty output, expected JSON.")

        # Try raw parse first
        try:
            return _json.loads(stripped)
        except _json.JSONDecodeError:
            pass

        # Try extracting from ```json / ``` fence
        m = _MD_FENCE.search(stripped)
        if m:
            inner = m.group(1).strip()
            try:
                return _json.loads(inner)
            except _json.JSONDecodeError as exc:
                raise ValueError(
                    f"Failed to parse JSON content inside code fence: {exc}"
                ) from exc

        raise ValueError(
            f"LLM output is not valid JSON. "
            f"First 200 chars: {stripped[:200]!r}"
        )

    # ── Internal API call ───────────────────────────────────────────────

    def _call_json_model(
        self, *, system_prompt: str, user_prompt: str, step_name: str
    ) -> Any:
        """Send chat completion, extract and return parsed JSON."""
        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Set it via environment variable or pass api_key= to OpenAIProvider()."
            )

        # Lazy import — only when actually called
        from openai import OpenAI  # type: ignore[import]

        client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=float(self._timeout),
        )
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        return self._extract_json(content)

    # ── Prompt builders ─────────────────────────────────────────────────

    def _build_classification_prompt(self, reviews: list[dict[str, Any]]) -> str:
        lines = [
            "Classify each of the following customer reviews. Return ONLY a JSON array.",
            "Each object must have: review_id (str), topics (list[str]), primary_topic (str),",
            "topic_confidence (float 0-1), needs_review (bool).",
            "Valid topics: hygiene, waiting_time, service, product, environment, price, other.",
            "",
            "Reviews:",
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
            "Analyze sentiment for each review. Return ONLY a JSON array.",
            "Each object: review_id (str), sentiment (positive|neutral|negative),",
            "severity (int 1-5), sentiment_confidence (float 0-1),",
            "is_negative_candidate (bool), analysis_reason (str, brief).",
            "",
            "Reviews:",
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
            "Aggregate the top 3 issues from negative reviews. Return ONLY a JSON array (length 3).",
            "Each object: rank (int 1-3), issue_name (str), issue_summary (str),",
            "topic (str), mention_count (int), severity_level (high|medium|low),",
            "priority_score (float 0-1), suggested_action (str),",
            "evidence_count (int), evidence_status (sufficient|insufficient),",
            'evidence (list of {review_id: str, evidence_text: str, evidence_reason: str}).',
            "Each piece of evidence MUST reference a real review_id from the data below.",
            "",
            f"Negative reviews ({len(neg)}):",
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
            "Draft replies for negative reviews. Return ONLY a JSON array.",
            "Each object: review_id (str), original_review (str),",
            "draft_text (str), approval_status (str = 'pending').",
            "Guidelines: sincere, restrained, no blame-shifting, no false promises, no fabricated facts.",
            "",
            f"Negative reviews ({len(neg)}):",
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
            "Check each reply draft for safety. Return ONLY a JSON array.",
            "Each object: review_id (str), safety_status (pass|rewrite_required|blocked),",
            "risk_types (list[str]), safety_reason (str).",
            "Rules: block if attacking customer, disclosing privacy, claiming employee punishment,",
            "or fabricating facts. Require rewrite for unfounded compensation, over-marketing,",
            "or defensive/blame-shifting language.",
            "",
            "Drafts:",
        ]
        for d in drafts:
            lines.append(
                f"  review_id={d.get('review_id')} | "
                f"draft_text={d.get('draft_text', '')!r}"
            )
        lines.append("")
        lines.append("JSON only — no markdown, no explanation:")
        return "\n".join(lines)


# ── System prompts ─────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = (
    "You are a review classification engine. "
    "Classify customer reviews into topics. "
    "Return ONLY a JSON array — no markdown, no explanation, no code fences."
)

_SENTIMENT_SYSTEM = (
    "You are a sentiment analysis engine. "
    "Analyze review sentiment, severity, and flag negative candidates. "
    "Return ONLY a JSON array — no markdown, no explanation, no code fences."
)

_INSIGHTS_SYSTEM = (
    "You are an issue aggregation engine. "
    "Identify the top 3 problems from negative reviews with evidence binding. "
    "Every evidence item MUST cite a real review_id from the input. "
    "Return ONLY a JSON array of 3 objects — no markdown, no explanation, no code fences."
)

_REPLIES_SYSTEM = (
    "You are a customer reply drafting engine. "
    "Write sincere, restrained replies for negative reviews. "
    "No blame-shifting, no false promises, no fabricated facts, no claiming employee punishment. "
    "Return ONLY a JSON array — no markdown, no explanation, no code fences."
)

_SAFETY_SYSTEM = (
    "You are a reply safety checker. "
    "Flag replies that contain attacks, privacy leaks, fabricated facts, "
    "unfounded compensation, over-marketing, or defensive language. "
    "Return ONLY a JSON array — no markdown, no explanation, no code fences."
)

