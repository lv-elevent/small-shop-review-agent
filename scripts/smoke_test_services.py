"""
Phase 5 smoke test — exercises Insight/Reply/Approval/Trace/Eval services.
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
from small_shop_agent.services.insight_service import InsightService
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.services.approval_service import ApprovalService
from small_shop_agent.services.trace_service import TraceService
from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.storage.repositories.trace_repository import TraceRepository

rs = ReviewService()
ws = WorkflowService()
insight_svc = InsightService()
reply_svc = ReplyService()
approval_svc = ApprovalService()
trace_svc = TraceService()
eval_svc = EvalService()
trace_repo = TraceRepository()

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
# Setup: create batch and run demo analysis
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Setup: create batch + run_demo_analysis ===")
csv_path = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
result = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create_batch success", result["success"] is True)
batch_id = result["batch_id"]

wf_result = ws.run_demo_analysis(batch_id)
check("workflow success", wf_result["success"] is True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 1: InsightService
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: InsightService ===")
top3 = insight_svc.get_top_issues(batch_id)
check("get_top_issues returns 3", len(top3) == 3)
check("ranks 1,2,3", [i["rank"] for i in top3] == [1, 2, 3])
check("rank1 topic=hygiene", top3[0]["topic"] == "hygiene")
check("rank2 topic=waiting_time", top3[1]["topic"] == "waiting_time")
check("rank3 topic=service", top3[2]["topic"] == "service")

insight_id = top3[0]["id"]
evidence = insight_svc.get_issue_evidence(insight_id)
check("get_issue_evidence has data", len(evidence) > 0, f"count={len(evidence)}")
check("evidence has 2 rows for hygiene", len(evidence) == 2)
for ev in evidence:
    check(f"evidence review_id={ev['review_id']}", bool(ev["review_id"]))
    check(f"evidence has text", bool(ev["evidence_text"]))

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: ReplyService — read
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: ReplyService read ===")
pending = reply_svc.get_pending_drafts(batch_id)
check("get_pending_drafts has data", len(pending) > 0, f"count={len(pending)}")
# COFF08 is blocked so not pending; 4 others are pending
check("pending count = 4", len(pending) == 4, f"count={len(pending)}")

# Get draft IDs by review_id
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
rpr = ReplyRepository()
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

# get_draft_detail
detail = reply_svc.get_draft_detail(coff04_id)
check("get_draft_detail works", detail is not None and detail["review_id"] == "COFF04")

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: ReplyService — approve (happy path: COFF04 safety=pass)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: ReplyService approve ===")
apr_result = reply_svc.approve_draft(coff04_id)
check("approve COFF04 success", apr_result["success"] is True, str(apr_result))
check("approve COFF04 status=approved",
      apr_result["draft"]["approval_status"] == "approved")
check("approve COFF04 final_text populated", bool(apr_result["draft"]["final_text"]))

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: ReplyService — approve blocked should fail
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: ReplyService approve blocked ===")
blocked_result = reply_svc.approve_draft(coff08_id)
check("approve COFF08 (blocked) fails", blocked_result["success"] is False)
check("error message mentions safety_status",
      "safety_status" in blocked_result.get("error", "").lower() or
      "blocked" in blocked_result.get("error", "").lower())

# COFF08 should still be blocked
coff08_check = rpr.get_draft_detail(coff08_id)
check("COFF08 still blocked after failed approve",
      coff08_check["approval_status"] == "blocked")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: ReplyService — edit draft
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: ReplyService edit ===")
edited_text = "感谢您的反馈，我们已经优化了出餐流程，承诺等待时间已缩短至10分钟。"
edit_result = reply_svc.edit_draft(coff12_id, edited_text)
check("edit COFF12 success", edit_result["success"] is True, str(edit_result))
check("edit COFF12 status=edited",
      edit_result["draft"]["approval_status"] == "edited")
check("edit COFF12 has edited_text",
      edit_result["draft"]["edited_text"] == edited_text)
check("edit COFF12 has final_text",
      edit_result["draft"]["final_text"] == edited_text)

# edit with empty text should fail
empty_edit = reply_svc.edit_draft(coff13_id, "")
check("edit with empty text fails", empty_edit["success"] is False)
empty_edit2 = reply_svc.edit_draft(coff13_id, "   ")
check("edit with whitespace fails", empty_edit2["success"] is False)

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: ReplyService — reject draft
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: ReplyService reject ===")
reject_result = reply_svc.reject_draft(coff13_id, "回复不符合品牌调性")
check("reject COFF13 success", reject_result["success"] is True)
check("reject COFF13 status=rejected",
      reject_result["draft"]["approval_status"] == "rejected")
check("reject COFF13 final_text empty",
      reject_result["draft"]["final_text"] in ("", None))

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: ReplyService — export_approved_replies
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: ReplyService export ===")
export = reply_svc.export_approved_replies(batch_id)
check("export returns dict", isinstance(export, dict))
check("export batch_id matches", export["batch_id"] == batch_id)
check("export count = 2 (COFF04 approved + COFF12 edited)", export["count"] == 2,
      f"count={export['count']}")
check("export drafts is list", isinstance(export["drafts"], list))
export_review_ids = {d["review_id"] for d in export["drafts"]}
check("export contains COFF04", "COFF04" in export_review_ids)
check("export contains COFF12", "COFF12" in export_review_ids)
check("export does NOT contain COFF13 (rejected)", "COFF13" not in export_review_ids)
check("export does NOT contain COFF08 (blocked)", "COFF08" not in export_review_ids)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: ApprovalService
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 8: ApprovalService ===")
act = approval_svc.record_approval_action(
    draft_id=coff06_id, batch_id=batch_id, review_id="COFF06",
    action="approve", before_text=coff06["draft_text"],
    after_text=coff06["draft_text"],
)
check("record_approval_action returns dict", isinstance(act, dict))
check("action is approve", act.get("action") == "approve")

# Check approval_actions in DB
with get_connection() as conn:
    aa = conn.execute(
        "SELECT count(*) as cnt FROM approval_actions WHERE batch_id = ?", (batch_id,)
    ).fetchone()
    check("approval_actions has records", aa["cnt"] >= 3,
          f"count={aa['cnt']}")  # 1 approve + 1 edit + 1 reject + 1 via approval_svc = 4

    # Check action types
    actions = conn.execute(
        "SELECT action, count(*) as cnt FROM approval_actions WHERE batch_id = ? GROUP BY action",
        (batch_id,),
    ).fetchall()
    action_counts = {r["action"]: r["cnt"] for r in actions}
    check("has approve actions", action_counts.get("approve", 0) >= 1)
    check("has edit action", action_counts.get("edit", 0) >= 1)
    check("has reject action", action_counts.get("reject", 0) >= 1)

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: TraceService + human_approval traces
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 9: TraceService + human_approval traces ===")
traces = trace_svc.get_trace(batch_id)
check("get_trace returns list", isinstance(traces, list) and len(traces) > 0)

human_traces = [t for t in traces if t["step_name"] == "human_approval"]
check("human_approval traces written", len(human_traces) >= 3,
      f"count={len(human_traces)}")  # approve + edit + reject = 3, +1 approval_svc = 4

for ht in human_traces:
    check(f"human_approval trace status=passed", ht["status"] == "passed",
          f"status={ht['status']}")
    check(f"human_approval has input_summary", bool(ht.get("input_summary")))

latest = trace_svc.get_latest_trace()
check("get_latest_trace returns list", isinstance(latest, list) and len(latest) > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: EvalService
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 10: EvalService ===")
eval_result = eval_svc.run_eval({"batch_id": batch_id})
check("run_eval success", eval_result["success"] is True, str(eval_result))
check("eval has eval_run_id", bool(eval_result.get("eval_run_id")))
eval_run_id = eval_result["eval_run_id"]

report = eval_result["report"]
check("topic_accuracy is float", isinstance(report["topic_accuracy"], float))
check("sentiment_accuracy is float", isinstance(report["sentiment_accuracy"], float))
check("topic_accuracy >= 0", report["topic_accuracy"] >= 0)
check("sentiment_accuracy >= 0", report["sentiment_accuracy"] >= 0)
check("unsafe_reply_count > 0", report["unsafe_reply_count"] > 0,
      f"unsafe={report['unsafe_reply_count']}")  # COFF08 blocked + COFF06 rewrite
check("total_eval_cases > 0", report["total_eval_cases"] > 0)

# Read back
latest_eval = eval_svc.get_latest_eval()
check("get_latest_eval returns dict", latest_eval is not None)
check("get_latest_eval matches eval_run_id",
      latest_eval["eval_run_id"] == eval_run_id if latest_eval else False)

eval_runs = eval_svc.list_eval_runs(limit=5)
check("list_eval_runs returns list", isinstance(eval_runs, list) and len(eval_runs) > 0)

# Verify eval trace was written
eval_traces = [t for t in trace_svc.get_trace(batch_id) if t["step_name"] == "eval_run"]
check("eval_run trace written", len(eval_traces) >= 1,
      f"count={len(eval_traces)}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 11: Edge cases
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 11: Edge cases ===")
# Non-existent draft
bad_approve = reply_svc.approve_draft(99999)
check("approve nonexistent draft fails", bad_approve["success"] is False)
bad_edit = reply_svc.edit_draft(99999, "text")
check("edit nonexistent draft fails", bad_edit["success"] is False)
bad_reject = reply_svc.reject_draft(99999)
check("reject nonexistent draft fails", bad_reject["success"] is False)
bad_detail = reply_svc.get_draft_detail(99999)
check("get_draft_detail nonexistent returns None", bad_detail is None)

# COFF06 is rewrite_required → cannot approve
coff06_approve = reply_svc.approve_draft(coff06_id)
check("approve rewrite_required draft fails", coff06_approve["success"] is False)

# Empty batch eval
eval_empty = eval_svc.run_eval({"batch_id": "batch-nonexistent"})
check("eval nonexistent batch fails", eval_empty["success"] is False)

# ═══════════════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Cleanup ===")
with get_connection() as conn:
    conn.execute("DELETE FROM approval_actions WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM insight_evidence WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM reply_drafts WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM review_analysis WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM insights WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM traces WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM eval_results WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM reviews WHERE batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM review_batches WHERE batch_id = ?", (batch_id,))
    conn.commit()
logger.success("Cleanup done")

# ═══════════════════════════════════════════════════════════════════════════
logger.info(f"\n{'='*50}")
logger.info(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    logger.success("ALL SERVICES SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
