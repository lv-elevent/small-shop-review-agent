"""
Phase 8 smoke test — simulates Reply Review page approval flow:
  approve / edit / reject drafts via ReplyService, verify DB writes
"""
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
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository

rs = ReviewService()
ws = WorkflowService()
reply_svc = ReplyService()
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
# Setup
# ═══════════════════════════════════════════════════════════════════════════
csv_path = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
result = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create_batch success", result["success"] is True)
batch_id = result["batch_id"]

wf_result = ws.run_demo_analysis(batch_id)
check("workflow success", wf_result["success"] is True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 1: Pending drafts
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: Pending drafts ===")
pending = reply_svc.get_pending_drafts(batch_id)
check("get_pending_drafts returns 4", len(pending) == 4, f"count={len(pending)}")
pending_ids = {d["review_id"] for d in pending}
check("COFF04 in pending", "COFF04" in pending_ids)
check("COFF06 in pending", "COFF06" in pending_ids)
check("COFF12 in pending", "COFF12" in pending_ids)
check("COFF13 in pending", "COFF13" in pending_ids)
check("COFF08 (blocked) NOT in pending", "COFF08" not in pending_ids)

# Get draft IDs
coff04 = rpr.get_draft_by_review(batch_id, "COFF04")
coff06 = rpr.get_draft_by_review(batch_id, "COFF06")
coff08 = rpr.get_draft_by_review(batch_id, "COFF08")
coff12 = rpr.get_draft_by_review(batch_id, "COFF12")
coff13 = rpr.get_draft_by_review(batch_id, "COFF13")
check("COFF04 draft exists", coff04 is not None)
check("COFF06 draft exists", coff06 is not None)
check("COFF08 draft exists", coff08 is not None)
check("COFF12 draft exists", coff12 is not None)
check("COFF13 draft exists", coff13 is not None)

coff04_id = coff04["id"]
coff06_id = coff06["id"]
coff08_id = coff08["id"]
coff12_id = coff12["id"]
coff13_id = coff13["id"]

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: Approve COFF04 (safety=pass)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: Approve COFF04 ===")
apr_result = reply_svc.approve_draft(coff04_id)
check("approve COFF04 success", apr_result["success"] is True, str(apr_result))
check("approve COFF04 status=approved",
      apr_result["draft"]["approval_status"] == "approved")
check("approve COFF04 final_text populated",
      bool(apr_result["draft"]["final_text"]))

# Verify in DB
coff04_check = rpr.get_draft_detail(coff04_id)
check("COFF04 DB: approval_status=approved",
      coff04_check["approval_status"] == "approved")
check("COFF04 DB: final_text = draft_text",
      coff04_check["final_text"] == coff04_check["draft_text"])

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: Edit COFF12
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: Edit COFF12 ===")
edited_text = "感谢您的反馈，我们已经优化了出餐流程，承诺等待时间已缩短至10分钟。"
edit_result = reply_svc.edit_draft(coff12_id, edited_text)
check("edit COFF12 success", edit_result["success"] is True, str(edit_result))
check("edit COFF12 status=edited",
      edit_result["draft"]["approval_status"] == "edited")
check("edit COFF12 edited_text matches",
      edit_result["draft"]["edited_text"] == edited_text)
check("edit COFF12 final_text matches",
      edit_result["draft"]["final_text"] == edited_text)

coff12_check = rpr.get_draft_detail(coff12_id)
check("COFF12 DB: approval_status=edited",
      coff12_check["approval_status"] == "edited")
check("COFF12 DB: final_text matches", coff12_check["final_text"] == edited_text)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: Reject COFF13
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: Reject COFF13 ===")
reject_reason = "回复不符合品牌调性，需要重新撰写"
reject_result = reply_svc.reject_draft(coff13_id, reject_reason)
check("reject COFF13 success", reject_result["success"] is True)
check("reject COFF13 status=rejected",
      reject_result["draft"]["approval_status"] == "rejected")
check("reject COFF13 final_text empty",
      reject_result["draft"]["final_text"] in ("", None))

coff13_check = rpr.get_draft_detail(coff13_id)
check("COFF13 DB: approval_status=rejected",
      coff13_check["approval_status"] == "rejected")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: Blocked draft (COFF08) cannot be approved
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: Blocked draft cannot approve ===")
blocked_result = reply_svc.approve_draft(coff08_id)
check("approve COFF08 (blocked) fails", blocked_result["success"] is False)
check("error mentions blocked/safety",
      "safety_status" in blocked_result.get("error", "").lower()
      or "blocked" in blocked_result.get("error", "").lower())

coff08_check = rpr.get_draft_detail(coff08_id)
check("COFF08 still blocked", coff08_check["approval_status"] == "blocked")

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: Rewrite_required draft (COFF06) cannot be approved
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: Rewrite_required draft cannot approve ===")
rewrite_result = reply_svc.approve_draft(coff06_id)
check("approve COFF06 (rewrite_required) fails", rewrite_result["success"] is False)

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: approval_actions table
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: approval_actions table ===")
with get_connection() as conn:
    actions = conn.execute(
        "SELECT * FROM approval_actions WHERE batch_id = ? ORDER BY id", (batch_id,)
    ).fetchall()
    check("approval_actions has 3 records", len(actions) == 3,
          f"count={len(actions)}")
    action_types = [a["action"] for a in actions]
    check("has approve action", "approve" in action_types)
    check("has edit action", "edit" in action_types)
    check("has reject action", "reject" in action_types)

    # Verify reject_reason stored
    reject_action = [a for a in actions if a["action"] == "reject"][0]
    check("reject action has reason",
          reject_action["reject_reason"] == reject_reason)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: human_approval traces
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 8: human_approval traces ===")
with get_connection() as conn:
    traces = conn.execute(
        "SELECT * FROM traces WHERE batch_id = ? AND step_name = 'human_approval' ORDER BY id",
        (batch_id,),
    ).fetchall()
    check("human_approval traces = 3", len(traces) == 3,
          f"count={len(traces)}")
    for t in traces:
        check(f"human_approval trace status=passed",
              t["status"] == "passed", f"status={t['status']}")
        check(f"human_approval has input_summary",
              bool(t["input_summary"]))

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: export_approved_replies
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 9: export_approved_replies ===")
export = reply_svc.export_approved_replies(batch_id)
check("export returns dict", isinstance(export, dict))
check("export count = 2 (COFF04 approved + COFF12 edited)",
      export["count"] == 2, f"count={export['count']}")
export_ids = {d["review_id"] for d in export["drafts"]}
check("export contains COFF04", "COFF04" in export_ids)
check("export contains COFF12", "COFF12" in export_ids)
check("export NOT contain COFF13 (rejected)", "COFF13" not in export_ids)
check("export NOT contain COFF08 (blocked)", "COFF08" not in export_ids)

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: Edge cases
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 10: Edge cases ===")
bad_approve = reply_svc.approve_draft(99999)
check("approve nonexistent fails", bad_approve["success"] is False)
bad_edit = reply_svc.edit_draft(99999, "text")
check("edit nonexistent fails", bad_edit["success"] is False)
bad_reject = reply_svc.reject_draft(99999)
check("reject nonexistent fails", bad_reject["success"] is False)
bad_detail = reply_svc.get_draft_detail(99999)
check("get_draft_detail nonexistent returns None", bad_detail is None)

# Edit with empty text
empty_edit = reply_svc.edit_draft(coff06_id, "")
check("edit with empty text fails", empty_edit["success"] is False)

# Already approved draft: UI hides approve button, service allows idempotent re-approve
reapprove = reply_svc.approve_draft(coff04_id)
check("re-approve already approved returns success (idempotent)", reapprove["success"] is True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 11: list_drafts returns all (for filter tabs)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 11: list_drafts (all drafts for filter tabs) ===")
all_drafts = rpr.list_drafts(batch_id)
check("list_drafts returns 5", len(all_drafts) == 5, f"count={len(all_drafts)}")
statuses = {d["approval_status"] for d in all_drafts}
check("has approved", "approved" in statuses)
check("has edited", "edited" in statuses)
check("has rejected", "rejected" in statuses)
check("has pending (COFF06 rewrite)", "pending" in statuses)
check("has blocked", "blocked" in statuses)

# Verify enriched fields on drafts (as load function does)
with get_connection() as conn:
    for d in all_drafts:
        review = conn.execute(
            "SELECT platform, rating FROM reviews WHERE batch_id=? AND review_id=?",
            (batch_id, d["review_id"]),
        ).fetchone()
        if review:
            check(f"draft {d['review_id']} can be enriched with review data",
                  review["platform"] is not None or review["rating"] is not None)

# ═══════════════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Cleanup ===")
with get_connection() as conn:
    for tbl in ["approval_actions", "insight_evidence", "reply_drafts",
                "review_analysis", "insights", "traces", "eval_results",
                "reviews", "review_batches"]:
        conn.execute(f"DELETE FROM {tbl} WHERE batch_id = ?", (batch_id,))
    conn.commit()
logger.success("Cleanup done")

# ═══════════════════════════════════════════════════════════════════════════
logger.info(f"\n{'='*50}")
logger.info(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    logger.success("ALL REPLY REVIEW FLOW SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
