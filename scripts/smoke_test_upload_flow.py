"""
Phase 6 smoke test — simulates Upload page backend flow:
  create_batch → run_demo_analysis → verify DB data
"""
import io
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from loguru import logger

from small_shop_agent.storage.database import execute_migrations, get_connection
execute_migrations()

from small_shop_agent.services.review_service import ReviewService
from small_shop_agent.services.workflow_service import WorkflowService

rs = ReviewService()
ws = WorkflowService()

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
# Setup
# ═══════════════════════════════════════════════════════════════════════════
csv_path = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
csv_bytes = csv_path.read_bytes()

# ═══════════════════════════════════════════════════════════════════════════
# Test 1: create_batch (happy path — file path)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: create_batch via file path ===")
result = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create_batch success", result["success"] is True, str(result))
batch_id = result["batch_id"]
check("batch_id returned", bool(batch_id) and batch_id.startswith("batch-"))
check("validation has total_rows", result["validation"]["total_rows"] == 15)
check("validation valid_review_count=13", result["validation"]["valid_review_count"] == 13,
      f"count={result['validation']['valid_review_count']}")
check("validation duplicate_count=1", result["validation"]["duplicate_count"] == 1)
check("validation empty_review_count=1", result["validation"]["empty_review_count"] == 1)
check("validation schema_error_count=0", result["validation"]["schema_error_count"] == 0)

# Verify reviews in DB
with get_connection() as conn:
    review_count = conn.execute(
        "SELECT count(*) as cnt FROM reviews WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("reviews table has 15 rows", review_count == 15, f"count={review_count}")
    valid_count = conn.execute(
        "SELECT count(*) as cnt FROM reviews WHERE batch_id = ? AND is_valid = 1", (batch_id,)
    ).fetchone()["cnt"]
    check("valid reviews = 13", valid_count == 13, f"count={valid_count}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: create_batch (happy path — bytes)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: create_batch via bytes ===")
result2 = rs.create_batch(csv_bytes, store_type="restaurant", file_name="uploaded.csv")
check("create_batch via bytes success", result2["success"] is True, str(result2))
batch_id2 = result2["batch_id"]
check("batch_id2 returned", bool(batch_id2))
check("bytes validation total_rows=15", result2["validation"]["total_rows"] == 15)

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: run_demo_analysis
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: run_demo_analysis ===")
wf_result = ws.run_demo_analysis(batch_id)
check("workflow success", wf_result["success"] is True, str(wf_result))
check("workflow mode=demo", wf_result["mode"] == "demo")
summary = wf_result["summary"]
check("summary review_count=13", summary["review_count"] == 13)
check("summary negative_count=5", summary["negative_count"] == 5)
check("summary insight_count=3", summary["insight_count"] == 3)
check("summary draft_count=5", summary["draft_count"] == 5)
check("summary blocked_count=1", summary["blocked_count"] == 1)
check("summary rewrite_count=1", summary["rewrite_count"] == 1)
check("summary pass_count=3", summary["pass_count"] == 3)
check("summary evidence_count=5", summary["evidence_count"] == 5)
check("summary trace_count=6", summary["trace_count"] == 6)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: Verify DB data after analysis (replicates Dashboard queries)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: Verify DB data (simulates Dashboard reads) ===")
with get_connection() as conn:
    # review_analysis
    analysis_count = conn.execute(
        "SELECT count(*) as cnt FROM review_analysis WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("review_analysis has 13 rows", analysis_count == 13, f"count={analysis_count}")

    # insights
    insights = conn.execute(
        "SELECT * FROM insights WHERE batch_id = ? ORDER BY rank", (batch_id,)
    ).fetchall()
    check("insights has 3 rows", len(insights) == 3)
    check("rank1 topic=hygiene", insights[0]["topic"] == "hygiene")
    check("rank1 issue_summary not null", bool(insights[0]["issue_summary"]))
    check("rank2 topic=waiting_time", insights[1]["topic"] == "waiting_time")
    check("rank3 topic=service", insights[2]["topic"] == "service")

    # insight_evidence
    evidence_count = conn.execute(
        "SELECT count(*) as cnt FROM insight_evidence WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("insight_evidence has 5 rows", evidence_count == 5)

    # reply_drafts
    drafts = conn.execute(
        "SELECT * FROM reply_drafts WHERE batch_id = ?", (batch_id,)
    ).fetchall()
    check("reply_drafts has 5 rows", len(drafts) == 5)
    safety_statuses = {d["safety_status"] for d in drafts}
    check("safety_statuses include blocked", "blocked" in safety_statuses)
    check("safety_statuses include rewrite_required", "rewrite_required" in safety_statuses)
    check("safety_statuses include pass", "pass" in safety_statuses)
    pending_count = sum(1 for d in drafts if d["approval_status"] == "pending")
    blocked_approval = sum(1 for d in drafts if d["approval_status"] == "blocked")
    check("4 pending + 1 blocked approval", pending_count == 4 and blocked_approval == 1,
          f"pending={pending_count}, blocked={blocked_approval}")

    # traces
    traces = conn.execute(
        "SELECT * FROM traces WHERE batch_id = ? ORDER BY id", (batch_id,)
    ).fetchall()
    check("traces has 8 rows", len(traces) == 8, f"count={len(traces)}")
    step_names = [t["step_name"] for t in traces]
    expected_steps = [
        "input_validation","data_cleaning","classification",
        "sentiment_analysis","issue_aggregation","evidence_check",
        "reply_drafting","safety_check",
    ]
    for step in expected_steps:
        check(f"trace step '{step}' exists", step in step_names)

    # review clean data
    valid_text_review = conn.execute(
        "SELECT review_text FROM reviews WHERE batch_id = ? AND is_valid = 1 LIMIT 1",
        (batch_id,),
    ).fetchone()
    check("valid review has text", valid_text_review is not None and bool(valid_text_review["review_text"]))

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: Run analysis on second batch
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: Second batch analysis ===")
wf2 = ws.run_demo_analysis(batch_id2)
check("second batch workflow success", wf2["success"] is True)
check("second batch insight_count=3", wf2["summary"]["insight_count"] == 3)

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: Edge cases — invalid CSV
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: Edge cases — invalid CSV ===")

# Missing required columns
bad_csv = b"col_a,col_b\n1,2\n3,4"
bad_result = rs.create_batch(bad_csv, store_type="coffee_shop", file_name="bad.csv")
check("missing columns fails", bad_result["success"] is False)
check("missing columns message", "missing" in bad_result.get("message", "").lower())

# Empty CSV
empty_csv = b""
empty_result = rs.create_batch(empty_csv, store_type="coffee_shop", file_name="empty.csv")
check("empty CSV fails", empty_result["success"] is False)

# Unparseable CSV
garbage = b"\xff\xfe\x00\x01\x02"
garbage_result = rs.create_batch(garbage, store_type="coffee_shop", file_name="bad.csv")
check("garbage CSV fails", garbage_result["success"] is False)

# Non-existent batch
nonexistent = ws.run_demo_analysis("batch-nonexistent")
check("nonexistent batch fails", nonexistent["success"] is False)

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: Validate CSV without persisting
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: validate_csv (no persist) ===")
val_result = rs.validate_csv(csv_bytes, file_name="sample_reviews.csv")
check("validate_csv success", val_result["success"] is True)
check("validate_csv batch_id is None", val_result["batch_id"] is None)
check("validate_csv has validation stats", bool(val_result["validation"]))
check("validate_csv total_rows=15", val_result["validation"]["total_rows"] == 15)

# ═══════════════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Cleanup ===")
with get_connection() as conn:
    for bid in (batch_id, batch_id2):
        conn.execute("DELETE FROM approval_actions WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM insight_evidence WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM reply_drafts WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM review_analysis WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM insights WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM traces WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM eval_results WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM reviews WHERE batch_id = ?", (bid,))
        conn.execute("DELETE FROM review_batches WHERE batch_id = ?", (bid,))
    conn.commit()
logger.success("Cleanup done")

# ═══════════════════════════════════════════════════════════════════════════
logger.info(f"\n{'='*50}")
logger.info(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    logger.success("ALL UPLOAD FLOW SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
