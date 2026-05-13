"""CSV input contracts: required columns, rating range, validation structures."""
from __future__ import annotations

REQUIRED_COLUMNS = [
    "review_text",
    "rating",
    "date",
]

OPTIONAL_COLUMNS = [
    "review_id",
    "platform",
]

RATING_MIN = 1
RATING_MAX = 5
