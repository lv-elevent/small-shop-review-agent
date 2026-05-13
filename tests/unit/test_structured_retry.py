"""Tests for harness/output/structured_retry.py"""
from __future__ import annotations

from pydantic import BaseModel

from small_shop_agent.harness.output.structured_retry import run_with_schema_retry


class _Item(BaseModel):
    name: str
    value: int


class TestRunWithSchemaRetry:
    def test_first_attempt_succeeds(self):
        def call_fn(attempt: int) -> list[dict]:
            return [{"name": "a", "value": 1}]

        result = run_with_schema_retry(
            call_fn=call_fn, schema_cls=_Item, many=True, max_retries=1,
        )
        assert result.ok is True
        assert result.attempts == 1
        assert result.used_fallback is False
        assert result.schema_name == "_Item"

    def test_first_fails_second_succeeds(self):
        call_count = [0]

        def call_fn(attempt: int) -> list[dict]:
            call_count[0] += 1
            if call_count[0] == 1:
                return [{"name": "a"}]  # missing 'value'
            return [{"name": "a", "value": 1}]

        result = run_with_schema_retry(
            call_fn=call_fn, schema_cls=_Item, many=True, max_retries=1,
        )
        assert result.ok is True
        assert result.attempts == 2
        assert result.used_fallback is False

    def test_all_retries_fail_triggers_fallback(self):
        def call_fn(attempt: int) -> list[dict]:
            return [{"name": "a"}]  # always invalid

        def fallback_fn() -> list[dict]:
            return [{"name": "fallback", "value": 99}]

        result = run_with_schema_retry(
            call_fn=call_fn, schema_cls=_Item, many=True, max_retries=1,
            fallback_fn=fallback_fn,
        )
        assert result.ok is True
        assert result.used_fallback is True
        assert result.attempts == 2  # 1 original + 1 retry + fallback counted as extra

    def test_call_fn_and_fallback_both_fail(self):
        def call_fn(attempt: int) -> list[dict]:
            return [{"name": "a"}]

        def fallback_fn() -> list[dict]:
            return [{"name": "bad"}]  # also missing 'value'

        result = run_with_schema_retry(
            call_fn=call_fn, schema_cls=_Item, many=True, max_retries=1,
            fallback_fn=fallback_fn,
        )
        assert result.ok is False
        assert result.used_fallback is True

    def test_call_fn_raises_exception(self):
        def call_fn(attempt: int) -> list[dict]:
            raise RuntimeError("LLM unavailable")

        result = run_with_schema_retry(
            call_fn=call_fn, schema_cls=_Item, many=True, max_retries=1,
        )
        assert result.ok is False
        assert "RuntimeError" in str(result.errors)

    def test_schema_name_preserved(self):
        def call_fn(attempt: int) -> list[dict]:
            return [{"name": "x", "value": 1}]

        result = run_with_schema_retry(
            call_fn=call_fn, schema_cls=_Item, many=True, max_retries=0,
        )
        assert result.schema_name == "_Item"
