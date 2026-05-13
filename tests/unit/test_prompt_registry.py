"""Tests for prompts/prompt_registry.py"""
from __future__ import annotations

import pytest

from small_shop_agent.prompts.prompt_registry import get_prompt


VALID_KEYS = [
    "classify_reviews",
    "analyze_sentiment",
    "generate_insights",
    "draft_replies",
    "check_safety",
]


class TestGetPrompt:
    @pytest.mark.parametrize("key", VALID_KEYS)
    def test_get_prompt_returns_non_empty_string(self, key: str):
        result = get_prompt(key)
        assert isinstance(result, str)
        assert len(result) > 0, f"Prompt for {key!r} is empty"

    def test_get_prompt_unknown_key_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown prompt key"):
            get_prompt("unknown_key")

    def test_unknown_key_message_includes_valid_keys(self):
        with pytest.raises(KeyError, match="classify_reviews") as exc_info:
            get_prompt("nonexistent")
        msg = str(exc_info.value)
        for key in VALID_KEYS:
            assert key in msg, f"Missing {key!r} in error message: {msg!r}"
