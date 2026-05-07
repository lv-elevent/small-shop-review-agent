"""
Phase 2 smoke test — exercises ReviewService CSV ingestion pipeline.
Covers: valid CSV, missing fields, rating validation, empty reviews, duplicates, traces.
"""
import sys
import io
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import pandas as pd
from loguru import logger

from small_shop_agent.storage.database import execute_migrations
execute_migrations()

from small_shop_agent.services.review_service import ReviewService

svc = ReviewService()
passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        logger.success(f"  PASS: {label}")
    else:
        failed += 1
        logger.error(f"  FAIL: {label} — {detail}")


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: Valid CSV — full pipeline
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: Valid CSV ===")
valid_csv = pd.DataFrame({
    "review_id": ["R001", "R002", "R003", "R004", "R005"],
    "date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"],
    "platform": ["美团", "大众点评", "小红书", "美团", "大众点评"],
    "rating": [5, 1, 3, 4, 2],
    "review_text": [
        "咖啡很好喝，环境舒适",
        "等了40分钟才上菜",
        "一般般吧，没什么特别",
        "牛角包酥脆好吃",
        "高峰期太乱了",
    ],
})
csv_bytes = valid_csv.to_csv(index=False).encode("utf-8")
result = svc.create_batch(csv_bytes, store_type="coffee_shop", file_name="test.csv")

check("success=True", result["success"] is True, str(result))
check("has batch_id", result.get("batch_id", "").startswith("batch-"))
batch_id = result["batch_id"]

val = result["validation"]
check("total_rows=5", val.get("total_rows") == 5)
check("valid_review_count=5", val.get("valid_review_count") == 5)
check("duplicate_count=0", val.get("duplicate_count") == 0)
check("empty_review_count=0", val.get("empty_review_count") == 0)
check("invalid_rating_count=0", val.get("invalid_rating_count") == 0)

# Check batch in DB
batch = svc.get_batch_summary(batch_id)
check("batch in DB", batch is not None)
check("batch status=analyzed", batch["status"] == "analyzed")
check("batch total_rows=5", batch["total_rows"] == 5)

# Check reviews in DB
reviews = svc.list_reviews(batch_id)
check("reviews count=5", len(reviews) == 5)
check("all reviews valid", all(r["is_valid"] == 1 for r in reviews))
check("all cleaned_text non-empty", all(r["cleaned_text"] for r in reviews))

# Check specific review
r001 = svc.get_review(batch_id, "R001")
check("get_review R001 found", r001 is not None and r001["review_text"] == "咖啡很好喝，环境舒适")

# Check traces
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
tr = TraceRepository()
traces = tr.get_traces(batch_id)
check("traces count=2", len(traces) == 2)
check("has input_validation trace", any(t["step_name"] == "input_validation" for t in traces))
check("has data_cleaning trace", any(t["step_name"] == "data_cleaning" for t in traces))
val_trace = next(t for t in traces if t["step_name"] == "input_validation")
check("input_validation status=passed", val_trace["status"] == "passed")

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: validate_csv (without persisting)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: validate_csv ===")
vresult = svc.validate_csv(csv_bytes, file_name="test.csv")
check("validate success=True", vresult["success"] is True)
check("validate batch_id=None", vresult["batch_id"] is None)
check("validate has stats", vresult["validation"].get("total_rows") == 5)

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: Missing required fields
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: Missing required fields ===")
bad_csv = pd.DataFrame({
    "review_id": ["M001"],
    "date": ["2025-01-01"],
    "platform": ["美团"],
    # missing: rating, review_text
})
result3 = svc.create_batch(bad_csv.to_csv(index=False).encode("utf-8"), file_name="bad.csv")
check("missing fields success=False", result3["success"] is False)
check("has missing_fields", "missing_fields" in result3.get("validation", {}))
missing = result3.get("validation", {}).get("missing_fields", [])
check("rating in missing_fields", "rating" in missing)
check("review_text in missing_fields", "review_text" in missing)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: Rating out of range (should be invalid, but batch still created)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: Rating out of range ===")
rating_csv = pd.DataFrame({
    "review_id": ["RR001", "RR002", "RR003", "RR004"],
    "date": ["2025-01-01"] * 4,
    "platform": ["美团"] * 4,
    "rating": [0, 6, 3, "abc"],
    "review_text": ["text A", "text B", "text C", "text D"],
})
result4 = svc.create_batch(rating_csv.to_csv(index=False).encode("utf-8"), file_name="rating.csv")
check("rating batch success=True", result4["success"] is True)
val4 = result4["validation"]
check("invalid_rating_count=3", val4.get("invalid_rating_count") == 3)
check("valid_review_count=1", val4.get("valid_review_count") == 1)

# Verify the valid one is the one with rating=3
reviews4 = svc.list_reviews(result4["batch_id"])
r4_valid = [r for r in reviews4 if r["is_valid"] == 1]
check("only rating=3 is valid", len(r4_valid) == 1 and r4_valid[0]["review_id"] == "RR003")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: Empty review_text → is_empty=1
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: Empty review_text ===")
empty_csv = pd.DataFrame({
    "review_id": ["E001", "E002", "E003", "E004"],
    "date": ["2025-01-01"] * 4,
    "platform": ["美团"] * 4,
    "rating": [4, 3, 2, 5],
    "review_text": ["正常评论内容", "", None, "   \t  "],
})
result5 = svc.create_batch(empty_csv.to_csv(index=False).encode("utf-8"), file_name="empty.csv")
check("empty batch success=True", result5["success"] is True)
val5 = result5["validation"]
check("empty_review_count=3", val5.get("empty_review_count") == 3)
check("valid_review_count=1", val5.get("valid_review_count") == 1)

reviews5 = svc.list_reviews(result5["batch_id"])
empty_reviews = [r for r in reviews5 if r["is_empty"] == 1]
check("3 reviews marked is_empty=1", len(empty_reviews) == 3)
# Verify the blank/whitespace text is now empty string
for er in empty_reviews:
    check(f"{er['review_id']} cleaned_text is empty", er["cleaned_text"] == "")

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: Duplicate review_id and review_text → is_duplicate=1
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: Duplicate review_id and review_text ===")
dup_csv = pd.DataFrame({
    "review_id": ["D001", "D001", "D003", "D004"],
    "date": ["2025-01-01"] * 4,
    "platform": ["美团"] * 4,
    "rating": [3, 3, 3, 3],
    "review_text": ["唯一评论A", "唯一评论A", "唯一评论B", "唯一评论B"],
})
result6 = svc.create_batch(dup_csv.to_csv(index=False).encode("utf-8"), file_name="dup.csv")
check("dup batch success=True", result6["success"] is True)
val6 = result6["validation"]
check("duplicate_count=2", val6.get("duplicate_count") == 2)
check("valid_review_count=2", val6.get("valid_review_count") == 2)

reviews6 = svc.list_reviews(result6["batch_id"])
valid_ones = [r for r in reviews6 if r["is_valid"] == 1]
dup_ones = [r for r in reviews6 if r["is_duplicate"] == 1]
check("2 valid (D001 + D003)", len(valid_ones) == 2 and {r["review_id"] for r in valid_ones} == {"D001", "D003"})
check("2 marked duplicate", len(dup_ones) == 2)

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: CSV with no required columns at all
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: No required columns ===")
junk_csv = pd.DataFrame({"col_a": [1], "col_b": [2]})
result7 = svc.create_batch(junk_csv.to_csv(index=False).encode("utf-8"), file_name="junk.csv")
check("junk csv success=False", result7["success"] is False)
all_missing = result7.get("validation", {}).get("missing_fields", [])
check("all 5 required columns missing", len(all_missing) == 5)

# ═══════════════════════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════════════════════
logger.info(f"\n{'='*50}")
logger.info(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    logger.success("ALL REVIEW SERVICE SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
