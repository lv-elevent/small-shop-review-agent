"""Text cleaning utilities for review data."""
from __future__ import annotations

import math
import re

_MULTI_SPACE = re.compile(r"\s+")


def clean_text(text: str | float | None) -> str:
    """Strip whitespace, collapse multiple spaces/newlines into single space."""
    if text is None:
        return ""
    if isinstance(text, float) and math.isnan(text):
        return ""
    if not isinstance(text, str):
        text = str(text)
    return _MULTI_SPACE.sub(" ", text).strip()
