"""CSV validator — schema check, rating validation, empty detection, duplicate detection."""
from __future__ import annotations

import pandas as pd

from small_shop_agent.harness.input.input_contracts import REQUIRED_COLUMNS, RATING_MIN, RATING_MAX
from small_shop_agent.harness.input.data_cleaner import clean_text


def validate_csv_schema(df: pd.DataFrame) -> dict:
    """Check that required columns exist. Returns error dict or empty dict."""
    columns_lower = {c.strip().lower().replace(" ", "_") for c in df.columns}
    missing = []
    for col in REQUIRED_COLUMNS:
        if col not in columns_lower:
            missing.append(col)
    if missing:
        return {
            "success": False,
            "validation": {"missing_fields": missing, "schema_error_count": len(missing)},
            "message": f"CSV missing required fields: {', '.join(missing)}",
        }
    return {}


def validate_and_clean(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Validate and clean a DataFrame in one pass. Returns (cleaned_df, stats).

    For each row:
      - rating must be int in [1,5], else mark invalid
      - review_text empty/whitespace → is_empty=1, is_valid=0
      - duplicate review_id or review_text → is_duplicate=1, is_valid=0
      - cleaned_text is stripped and whitespace-normalized
    """
    df = dataframe.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    total = len(df)

    # Rating validation
    df["rating_num"] = pd.to_numeric(df["rating"], errors="coerce")
    rating_ok = (
        df["rating_num"].notna()
        & (df["rating_num"] >= RATING_MIN)
        & (df["rating_num"] <= RATING_MAX)
    )
    invalid_rating_count = int((~rating_ok).sum())

    # Clean text
    df["cleaned_text"] = df["review_text"].apply(clean_text)

    # Empty detection
    df["is_empty"] = (
        df["cleaned_text"].isna() | (df["cleaned_text"].str.strip() == "")
    ).astype(int)
    empty_count = int(df["is_empty"].sum())

    # Duplicate detection: by review_id
    dup_id_mask = df["review_id"].duplicated(keep="first")
    # Duplicate detection: by review_text (cleaned), skip empty
    dup_text_mask = df["cleaned_text"].duplicated(keep="first") & (
        df["cleaned_text"].str.strip() != ""
    )
    df["is_duplicate"] = (dup_id_mask | dup_text_mask).astype(int)
    duplicate_count = int(df["is_duplicate"].sum())

    # is_valid: rating ok, not empty, not duplicate
    df["is_valid"] = (
        rating_ok & (df["is_empty"] == 0) & (df["is_duplicate"] == 0)
    ).astype(int)
    valid_count = int(df["is_valid"].sum())

    # Clean rating: valid→int 1-5, invalid→3 (neutral, satisfies DB CHECK 1-5)
    df["rating"] = df["rating_num"].where(rating_ok, 3).fillna(3).astype(int)
    df.drop(columns=["rating_num"], inplace=True)

    # Convert bool-like columns to int
    for col in ["is_empty", "is_duplicate", "is_valid"]:
        df[col] = df[col].astype(int)

    stats = {
        "total_rows": total,
        "valid_review_count": valid_count,
        "duplicate_count": duplicate_count,
        "empty_review_count": empty_count,
        "schema_error_count": 0,
        "invalid_rating_count": invalid_rating_count,
    }
    return df, stats
