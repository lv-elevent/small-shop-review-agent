"""Tests for OllamaProvider — mock HTTP, no real Ollama required."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from small_shop_agent.llm.ollama_provider import OllamaProvider


def _mock_ollama_response(content: str):
    """Build a mock requests.Response with Ollama chat format."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"message": {"role": "assistant", "content": content}}
    return resp


REVIEWS = [
    {"review_id": "R1", "rating": 1, "review_text": "太难吃了"},
    {"review_id": "R2", "rating": 5, "review_text": "很棒"},
]

DRAFTS = [
    {"review_id": "R1", "draft_text": "我们会改进的。"},
]


class TestOllamaProvider:
    def test_classify_reviews(self):
        provider = OllamaProvider()
        mock_resp = _mock_ollama_response(json.dumps([
            {"review_id": "R1", "topics": ["product"], "primary_topic": "product",
             "topic_confidence": 0.90, "needs_review": True},
            {"review_id": "R2", "topics": ["product"], "primary_topic": "product",
             "topic_confidence": 0.95, "needs_review": False},
        ]))
        with patch("requests.post", return_value=mock_resp):
            result = provider.classify_reviews(REVIEWS)
        assert len(result) == 2
        assert result[0]["review_id"] == "R1"
        assert result[0]["primary_topic"] == "product"

    def test_analyze_sentiment(self):
        provider = OllamaProvider()
        mock_resp = _mock_ollama_response(json.dumps([
            {"review_id": "R1", "sentiment": "negative", "severity": 5,
             "sentiment_confidence": 0.95, "is_negative_candidate": True,
             "analysis_reason": "顾客明确表达不满"},
        ]))
        with patch("requests.post", return_value=mock_resp):
            result = provider.analyze_sentiment(REVIEWS)
        assert len(result) >= 1
        assert result[0]["sentiment"] == "negative"

    def test_check_safety(self):
        provider = OllamaProvider()
        mock_resp = _mock_ollama_response(json.dumps([
            {"review_id": "R1", "safety_status": "pass",
             "risk_types": [], "safety_reason": "回复安全"},
        ]))
        with patch("requests.post", return_value=mock_resp):
            result = provider.check_safety(DRAFTS)
        assert len(result) >= 1
        assert result[0]["safety_status"] == "pass"

    def test_ollama_json_extraction_with_fence(self):
        provider = OllamaProvider()
        raw = '```json\n[{"review_id": "X", "sentiment": "neutral"}]\n```'
        result = provider._extract_json(raw)
        assert len(result) == 1
        assert result[0]["review_id"] == "X"

    def test_ollama_json_extraction_plain(self):
        provider = OllamaProvider()
        raw = '[{"review_id": "Y", "sentiment": "positive"}]'
        result = provider._extract_json(raw)
        assert result[0]["review_id"] == "Y"

    def test_ollama_json_extraction_empty_fails(self):
        provider = OllamaProvider()
        with pytest.raises(ValueError, match="空输出"):
            provider._extract_json("")

    def test_default_config(self):
        provider = OllamaProvider()
        assert provider._base_url == "http://localhost:11434"
        assert provider._model == "qwen2.5:7b"

    def test_custom_config(self):
        provider = OllamaProvider(
            base_url="http://my-ollama:9999",
            model="custom-model",
        )
        assert provider._base_url == "http://my-ollama:9999"
        assert provider._model == "custom-model"

    def test_http_error_raised(self):
        provider = OllamaProvider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(Exception, match="HTTP 500"):
                provider.classify_reviews(REVIEWS)
