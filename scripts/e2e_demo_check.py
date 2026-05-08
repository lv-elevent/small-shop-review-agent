"""
End-to-end demo check — runs the full MVP demo flow from zero DB to verified results.
Simulates: init → upload → analyze → approve → eval → verify all 9 tables.
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from loguru import logger

from small_shop_agent.storage.database import execute_migrations, get_connection

logger.info("=== Step 0: Init database ===")
execute_migrations()

from small_shop_agent.services.review_service import ReviewService
from small_shop_agent.services.workflow_service import WorkflowService
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository

rs = ReviewService()
ws = WorkflowService()
reply_svc = ReplyService()
eval_svc = EvalService()
rpr = ReplyRepository()

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
# Step 1: Upload CSV (create_batch)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Step 1: Create batch (upload CSV) ===")
csv_path = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
result = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create_batch success", result["success"] is True, str(result))
batch_id = result["batch_id"]
check("batch_id returned", bool(batch_id))
check("total_rows=15", result["validation"]["total_rows"] == 15)
check("valid_review_count=13", result["validation"]["valid_review_count"] == 13)
check("duplicate_count=1", result["validation"]["duplicate_count"] == 1)
check("empty_review_count=1", result["validation"]["empty_review_count"] == 1)

# Verify review_batches table
with get_connection() as conn:
    batch = conn.execute(
        "SELECT * FROM review_batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()
    check("review_batches has record", batch is not None)
    check("batch status=analyzed", batch["status"] == "analyzed")

# Verify reviews table
with get_connection() as conn:
    review_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("reviews table: 15 rows", review_count == 15, f"count={review_count}")
    valid_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ? AND is_valid = 1",
        (batch_id,),
    ).fetchone()["cnt"]
    check("reviews table: 13 valid", valid_count == 13)

# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Run demo analysis
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Step 2: Run demo analysis ===")
wf = ws.run_demo_analysis(batch_id)
check("workflow success", wf["success"] is True, str(wf))
check("review_count=13", wf["summary"]["review_count"] == 13)
check("insight_count=3", wf["summary"]["insight_count"] == 3)
check("draft_count=5", wf["summary"]["draft_count"] == 5)
check("blocked_count=1", wf["summary"]["blocked_count"] == 1)
check("evidence_count=5", wf["summary"]["evidence_count"] == 5)

# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Verify Dashboard-required data
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Step 3: Verify Dashboard data ===")
with get_connection() as conn:
    # review_analysis
    analysis_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("review_analysis: 13 rows", analysis_cnt == 13, f"count={analysis_cnt}")

    # insights
    insights = conn.execute(
        "SELECT * FROM insights WHERE batch_id = ? ORDER BY rank", (batch_id,)
    ).fetchall()
    check("insights: 3 rows", len(insights) == 3)
    check("rank1=hygiene", insights[0]["topic"] == "hygiene")
    check("insights have issue_summary", all(bool(i["issue_summary"]) for i in insights))

    # insight_evidence
    evidence_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM insight_evidence WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("insight_evidence: 5 rows", evidence_cnt == 5)

    # reply_drafts
    drafts = conn.execute(
        "SELECT * FROM reply_drafts WHERE batch_id = ?", (batch_id,)
    ).fetchall()
    check("reply_drafts: 5 rows", len(drafts) == 5)
    safety_set = {d["safety_status"] for d in drafts}
    check("drafts: has pass", "pass" in safety_set)
    check("drafts: has rewrite_required", "rewrite_required" in safety_set)
    check("drafts: has blocked", "blocked" in safety_set)

    # traces (8 workflow steps)
    trace_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM traces WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("traces: 8 steps", trace_cnt == 8, f"count={trace_cnt}")

    # Negative count (for metric card)
    neg_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ? AND is_negative_candidate = 1",
        (batch_id,),
    ).fetchone()["cnt"]
    check("negative candidates: 5", neg_cnt == 5, f"count={neg_cnt}")

    # Pending count
    pending_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM reply_drafts WHERE batch_id = ? AND approval_status = 'pending'",
        (batch_id,),
    ).fetchone()["cnt"]
    check("pending drafts: 4", pending_cnt == 4, f"count={pending_cnt}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Approve one draft (COFF04)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Step 4: Approve COFF04 ===")
coff04 = rpr.get_draft_by_review(batch_id, "COFF04")
check("COFF04 draft exists", coff04 is not None)
apr = reply_svc.approve_draft(coff04["id"])
check("approve success", apr["success"] is True)
check("approve status=approved", apr["draft"]["approval_status"] == "approved")

# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Run eval
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Step 5: Run eval ===")
eval_result = eval_svc.run_eval({"batch_id": batch_id})
check("run_eval success", eval_result["success"] is True, str(eval_result))
check("eval has eval_run_id", bool(eval_result.get("eval_run_id")))
check("topic_accuracy >= 0", eval_result["report"]["topic_accuracy"] >= 0)
check("sentiment_accuracy >= 0", eval_result["report"]["sentiment_accuracy"] >= 0)
check("unsafe_reply_count > 0", eval_result["report"]["unsafe_reply_count"] > 0)
check("total_eval_cases > 0", eval_result["report"]["total_eval_cases"] > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Step 6: Final verification — all 9 tables
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Step 6: Final 9-table verification ===")

# De-duplicate: only count rows for this batch
with get_connection() as conn:
    tables = {
        "review_batches": "SELECT COUNT(*) as cnt FROM review_batches WHERE batch_id = ?",
        "reviews": "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ?",
        "review_analysis": "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?",
        "insights": "SELECT COUNT(*) as cnt FROM insights WHERE batch_id = ?",
        "insight_evidence": "SELECT COUNT(*) as cnt FROM insight_evidence WHERE batch_id = ?",
        "reply_drafts": "SELECT COUNT(*) as cnt FROM reply_drafts WHERE batch_id = ?",
        "approval_actions": "SELECT COUNT(*) as cnt FROM approval_actions WHERE batch_id = ?",
        "traces": "SELECT COUNT(*) as cnt FROM traces WHERE batch_id = ?",
        "eval_results": "SELECT COUNT(*) as cnt FROM eval_results WHERE batch_id = ?",
    }
    expected = {
        "review_batches": 1, "reviews": 15, "review_analysis": 13,
        "insights": 3, "insight_evidence": 5, "reply_drafts": 5,
        "approval_actions": 1, "traces": 10, "eval_results": 1,
    }
    for table, query in tables.items():
        cnt = conn.execute(query, (batch_id,)).fetchone()["cnt"]
        exp = expected[table]
        check(f"Table '{table}': {cnt} rows (expected {exp})",
              cnt == exp, f"got {cnt}, expected {exp}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 7: Cleanup
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Step 7: Cleanup ===")
with get_connection() as conn:
    for tbl in ["approval_actions", "insight_evidence", "reply_drafts",
                "review_analysis", "insights", "traces", "eval_results",
                "reviews", "review_batches"]:
        conn.execute(f"DELETE FROM {tbl} WHERE batch_id = ?", (batch_id,))
    conn.commit()
logger.success("Cleanup done")

# ═══════════════════════════════════════════════════════════════════════════
logger.info(f"\n{'='*50}")
logger.info(f"E2E DEMO CHECK: {passed} passed, {failed} failed")
if failed == 0:
    logger.success("E2E DEMO CHECK PASSED — MVP ready for demo")
else:
    logger.error(f"E2E DEMO CHECK FAILED — {failed} test(s) failed")
