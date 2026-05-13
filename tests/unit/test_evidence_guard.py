"""Tests for harness/evidence/evidence_guard.py"""
from __future__ import annotations

from small_shop_agent.harness.evidence.evidence_guard import (
    validate_insight_evidence,
    _extract_review_ids,
)


class TestExtractReviewIds:
    def test_direct_review_ids_list(self):
        insight = {"evidence_review_ids": ["A", "B", "C"]}
        assert _extract_review_ids(insight) == ["A", "B", "C"]

    def test_nested_evidence_dicts(self):
        insight = {"evidence": [
            {"review_id": "X", "evidence_text": "text1"},
            {"review_id": "Y", "evidence_text": "text2"},
        ]}
        result = _extract_review_ids(insight)
        assert result == ["X", "Y"]

    def test_empty_evidence(self):
        insight = {}
        assert _extract_review_ids(insight) == []

    def test_evidence_ids_field(self):
        insight = {"evidence_ids": ["ID1", "ID2"]}
        assert _extract_review_ids(insight) == ["ID1", "ID2"]


class TestValidateInsightEvidence:
    def test_sufficient_evidence(self):
        insights = [{"rank": 1, "topic": "hygiene", "evidence": [
            {"review_id": "A", "evidence_text": "有虫子"},
            {"review_id": "B", "evidence_text": "卫生差"},
        ]}]
        reviews = [{"review_id": "A"}, {"review_id": "B"}]
        result = validate_insight_evidence(insights, reviews, min_evidence_count=2)
        assert result.ok is True
        assert len(result.valid_issues) == 1
        assert result.issues[0].status == "sufficient"

    def test_insufficient_evidence(self):
        insights = [{"rank": 1, "topic": "hygiene", "evidence": [
            {"review_id": "A", "evidence_text": "有虫子"},
        ]}]
        reviews = [{"review_id": "A"}, {"review_id": "B"}]
        result = validate_insight_evidence(insights, reviews, min_evidence_count=2)
        assert result.ok is False
        assert result.issues[0].status == "evidence_insufficient"

    def test_no_evidence_invalid(self):
        insights = [{"rank": 1, "topic": "service", "issue_name": "服务差"}]
        reviews = [{"review_id": "A"}]
        result = validate_insight_evidence(insights, reviews)
        assert result.issues[0].status == "invalid"

    def test_missing_review_ids(self):
        insights = [{"rank": 1, "topic": "hygiene", "evidence": [
            {"review_id": "A", "evidence_text": "ok"},
            {"review_id": "GHOST", "evidence_text": "not found"},
        ]}]
        reviews = [{"review_id": "A"}, {"review_id": "B"}]
        result = validate_insight_evidence(insights, reviews, min_evidence_count=2)
        assert "GHOST" in result.issues[0].missing_review_ids

    def test_direct_review_ids_format(self):
        insights = [{"rank": 1, "topic": "price", "evidence_review_ids": ["A", "B"]}]
        reviews = [{"review_id": "A"}, {"review_id": "B"}]
        result = validate_insight_evidence(insights, reviews, min_evidence_count=2)
        assert result.ok is True
        assert result.issues[0].status == "sufficient"

    def test_multiple_issues_mixed_status(self):
        insights = [
            {"rank": 1, "topic": "hygiene", "evidence": [
                {"review_id": "A", "evidence_text": "t1"},
                {"review_id": "B", "evidence_text": "t2"},
            ]},
            {"rank": 2, "topic": "service", "evidence": []},
        ]
        reviews = [{"review_id": "A"}, {"review_id": "B"}]
        result = validate_insight_evidence(insights, reviews, min_evidence_count=2)
        assert result.ok is False
        assert len(result.valid_issues) == 1
        assert len(result.rejected_issues) == 1
