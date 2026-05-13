"""Core domain entities as dataclasses — mirror DB row structure for type safety."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BatchEntity:
    batch_id: str
    store_type: str = "coffee_shop"
    source_type: str = "demo_mode"
    file_name: str = ""
    total_rows: int = 0
    valid_review_count: int = 0
    duplicate_count: int = 0
    empty_review_count: int = 0
    schema_error_count: int = 0
    negative_review_count: int = 0
    pending_reply_count: int = 0
    status: str = "uploaded"
    error_message: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ReviewEntity:
    batch_id: str
    review_id: str
    rating: int = 3
    review_text: str = ""
    cleaned_text: str = ""
    date: str = ""
    platform: str = ""
    is_empty: bool = False
    is_duplicate: bool = False
    is_valid: bool = True
