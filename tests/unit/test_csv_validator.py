"""Tests for harness/input/csv_validator.py"""
from __future__ import annotations

import pandas as pd
import pytest

from small_shop_agent.harness.input.csv_validator import validate_csv_schema, validate_and_clean


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestValidateCsvSchema:
    def test_all_required_columns_present(self):
        df = _make_df([{"review_id": "1", "date": "2024-01", "platform": "X",
                         "rating": 5, "review_text": "good"}])
        result = validate_csv_schema(df)
        assert result == {}

    def test_missing_review_text(self):
        df = _make_df([{"review_id": "1", "date": "2024-01", "platform": "X",
                         "rating": 5}])
        result = validate_csv_schema(df)
        assert result.get("success") is False
        assert "review_text" in result.get("validation", {}).get("missing_fields", [])

    def test_missing_rating(self):
        df = _make_df([{"review_id": "1", "date": "2024-01", "platform": "X",
                         "review_text": "good"}])
        result = validate_csv_schema(df)
        assert result.get("success") is False
        assert "rating" in result.get("validation", {}).get("missing_fields", [])


class TestValidateAndClean:
    def test_all_valid_reviews(self):
        df = _make_df([
            {"review_id": "A", "review_text": "Great coffee!", "rating": 5},
            {"review_id": "B", "review_text": "Too slow", "rating": 2},
        ])
        cleaned, stats = validate_and_clean(df)
        assert stats["total_rows"] == 2
        assert stats["valid_review_count"] == 2
        assert stats["duplicate_count"] == 0
        assert stats["empty_review_count"] == 0

    def test_rating_out_of_range_marked_invalid(self):
        df = _make_df([
            {"review_id": "A", "review_text": "ok", "rating": 0},
            {"review_id": "B", "review_text": "bad", "rating": 6},
        ])
        cleaned, stats = validate_and_clean(df)
        assert stats["valid_review_count"] == 0
        assert stats["invalid_rating_count"] == 2
        # Out-of-range ratings default to 3
        assert cleaned.iloc[0]["rating"] == 3

    def test_empty_review_text_marked_empty(self):
        df = _make_df([
            {"review_id": "A", "review_text": "", "rating": 3},
        ])
        cleaned, stats = validate_and_clean(df)
        assert stats["empty_review_count"] == 1
        assert stats["valid_review_count"] == 0

    def test_duplicate_review_id_marked_duplicate(self):
        df = _make_df([
            {"review_id": "A", "review_text": "good", "rating": 4},
            {"review_id": "A", "review_text": "good again", "rating": 5},
        ])
        cleaned, stats = validate_and_clean(df)
        assert stats["duplicate_count"] >= 1

    def test_duplicate_review_text_marked_duplicate(self):
        df = _make_df([
            {"review_id": "A", "review_text": "same text", "rating": 4},
            {"review_id": "B", "review_text": "same text", "rating": 4},
        ])
        cleaned, stats = validate_and_clean(df)
        assert stats["duplicate_count"] >= 1

    def test_mixed_scenario(self):
        df = _make_df([
            {"review_id": "A", "review_text": "good", "rating": 4},        # valid
            {"review_id": "B", "review_text": "", "rating": 3},            # empty
            {"review_id": "C", "review_text": "bad", "rating": 10},        # invalid rating
            {"review_id": "D", "review_text": "good", "rating": 5},        # duplicate text of A
        ])
        cleaned, stats = validate_and_clean(df)
        assert stats["total_rows"] == 4
        assert stats["valid_review_count"] == 1  # only A is valid
        assert stats["empty_review_count"] == 1
        assert stats["duplicate_count"] >= 1
        assert stats["invalid_rating_count"] == 1
