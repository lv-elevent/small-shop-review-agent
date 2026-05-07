"""CSV input contracts: required columns, rating range, validation structures."""
from __future__ import annotations

REQUIRED_COLUMNS = [
    "review_id",
    "date",
    "platform",
    "rating",
    "review_text",
]

RATING_MIN = 1
RATING_MAX = 5
