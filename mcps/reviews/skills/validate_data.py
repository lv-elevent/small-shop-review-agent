"""
Skill: validate_data
功能：校验 CSV 数据的有效性和格式
"""

import pandas as pd

def validate_data(df: pd.DataFrame) -> dict:
    total = len(df)
    empty_rows = df.isna().all(axis=1).sum()
    duplicate_count = df.duplicated().sum()
    # 判断有没有 review_text/rating
    missing_text = int(df["review_text"].isna().sum()) if "review_text" in df.columns else total
    # rating 可转数字
    rating_num = pd.to_numeric(df["rating"], errors="coerce") if "rating" in df.columns else None
    structure_errors = int(rating_num.isna().sum()) if rating_num is not None else total
    valid = max(0, total - empty_rows - duplicate_count - structure_errors)
    return {
        "total": total,
        "valid": valid,
        "empty_rows": int(empty_rows),
        "duplicates": int(duplicate_count),
        "missing_text": missing_text,
        "structure_errors": structure_errors,
    }