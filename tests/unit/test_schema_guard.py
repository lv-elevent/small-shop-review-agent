"""Tests for harness/output/schema_guard.py"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from small_shop_agent.harness.output.schema_guard import validate_output


class _Item(BaseModel):
    name: str
    value: int


class TestValidateOutput:
    def test_all_valid_many(self):
        data = [{"name": "a", "value": 1}, {"name": "b", "value": 2}]
        result = validate_output(data, _Item, many=True)
        assert result.ok is True
        assert result.total_valid == 2
        assert result.total_invalid == 0
        assert len(result.validated) == 2

    def test_partial_invalid_still_returns_valids(self):
        data = [{"name": "a", "value": 1}, {"name": "b"}]
        result = validate_output(data, _Item, many=True)
        assert result.ok is False
        assert result.total_valid == 1
        assert result.total_invalid == 1
        assert len(result.validated) == 1

    def test_single_item_many_false(self):
        result = validate_output({"name": "a", "value": 1}, _Item, many=False)
        assert result.ok is True
        assert result.total_valid == 1

    def test_single_item_invalid_many_false(self):
        result = validate_output({"name": "a"}, _Item, many=False)
        assert result.ok is False
        assert result.total_invalid == 1

    def test_empty_list_not_ok(self):
        result = validate_output([], _Item, many=True)
        assert result.ok is False
        assert result.total_valid == 0

    def test_extra_fields_ignored(self):
        """Pydantic ignores extra fields by default (v2) — test that schema guard accepts."""
        data = [{"name": "a", "value": 1, "extra": "should_be_ok"}]
        result = validate_output(data, _Item, many=True)
        assert result.ok is True

    def test_type_error_readable(self):
        data = [{"name": "a", "value": "not_an_int"}]
        result = validate_output(data, _Item, many=True)
        assert result.ok is False
        assert len(result.errors) == 1
        assert "index" in result.errors[0]
