"""
Phase 7 smoke test — simulates Dashboard page data loading:
  InsightService / ReplyService / TraceService / EvalService → verify rendering-ready data
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
from small_shop_agent.services.trace_service import TraceService
from small_shop_agent.services.eval_service import EvalService

rs = ReviewService()
ws = WorkflowService()
insight_svc = InsightService()
reply_svc = ReplyService()
trace_svc = TraceService()
eval_svc = EvalService()

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

# Run eval so latest_eval is available
eval_svc.run_eval({"batch_id": batch_id})

# ═══════════════════════════════════════════════════════════════════════════
# Test 1: InsightService — top_issues (renders "三大问题洞察")
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: InsightService — top_issues ===")
top_issues = insight_svc.get_top_issues(batch_id)
check("get_top_issues returns 3", len(top_issues) == 3, f"count={len(top_issues)}")
check("rank 1,2,3 in order", [i["rank"] for i in top_issues] == [1, 2, 3])

required_fields = ["id", "rank", "issue_name", "topic", "mention_count",
                   "severity_level", "priority_score", "suggested_action",
                   "evidence_count", "evidence_status", "issue_summary"]
for issue in top_issues:
    for field in required_fields:
        check(f"issue #{issue['rank']} has '{field}'", field in issue and issue[field] is not None,
              f"value={issue.get(field)}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: InsightService — evidence per issue (renders "关联评论" in cards)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: InsightService — evidence ===")
total_evidence = 0
for issue in top_issues:
    evidence = insight_svc.get_issue_evidence(issue["id"])
    check(f"issue #{issue['rank']} has evidence", len(evidence) > 0,
          f"count={len(evidence)}")
    check(f"issue #{issue['rank']} evidence_count matches",
          len(evidence) == issue["evidence_count"],
          f"expected={issue['evidence_count']}, got={len(evidence)}")
    for ev in evidence:
        check(f"evidence has review_id", bool(ev.get("review_id")))
        check(f"evidence has evidence_text", bool(ev.get("evidence_text")))
    total_evidence += len(evidence)
check("total evidence = 5", total_evidence == 5, f"count={total_evidence}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: ReplyService — pending_drafts (renders "差评回复审核队列")
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: ReplyService — pending_drafts ===")
pending = reply_svc.get_pending_drafts(batch_id)
check("get_pending_drafts returns 4", len(pending) == 4, f"count={len(pending)}")

draft_fields = ["id", "review_id", "draft_text", "safety_status", "approval_status"]
for d in pending:
    for field in draft_fields:
        check(f"draft {d.get('review_id')} has '{field}'",
              field in d, f"missing: {field}")
    check(f"draft {d.get('review_id')} approval_status=pending",
          d.get("approval_status") == "pending")
    check(f"draft {d.get('review_id')} safety_status set",
          d.get("safety_status") in ("pass", "rewrite_required", "blocked"))

# Verify blocked drafts are NOT in pending
pending_ids = {d["review_id"] for d in pending}
check("COFF08 (blocked) not in pending", "COFF08" not in pending_ids)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: TraceService — traces (renders "Harness 状态")
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: TraceService — traces ===")
traces = trace_svc.get_trace(batch_id)
check("get_trace returns 9 traces (8 workflow + 1 eval)", len(traces) == 9,
      f"count={len(traces)}")

step_names = {t["step_name"] for t in traces}
harness_steps = ["input_validation", "data_cleaning", "classification",
                 "sentiment_analysis", "issue_aggregation", "evidence_check",
                 "reply_drafting", "safety_check", "eval_run"]
for step in harness_steps:
    check(f"trace has '{step}'", step in step_names)

for t in traces:
    check(f"trace '{t['step_name']}' has status", t.get("status") in ("passed", "warning", "failed"),
          f"status={t.get('status')}")
    check(f"trace '{t['step_name']}' has summary", bool(t.get("output_summary")),
          f"output_summary={t.get('output_summary')}")

# ── Derive harness checks (as Dashboard does) ──
trace_map = {t["step_name"]: t for t in traces}
check("input_validation trace usable", trace_map["input_validation"]["status"] in ("passed", "warning"))
check("safety_check trace usable", trace_map["safety_check"]["status"] in ("passed", "warning"))
check("evidence_check trace usable", trace_map["evidence_check"]["status"] == "passed")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: EvalService — latest_eval (renders eval summary)
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: EvalService — latest_eval ===")
latest_eval = eval_svc.get_latest_eval()
check("get_latest_eval returns dict", latest_eval is not None)
check("latest_eval has batch_id", bool(latest_eval.get("batch_id")))
check("latest_eval has topic_accuracy", isinstance(latest_eval.get("topic_accuracy"), (int, float)))
check("latest_eval has sentiment_accuracy", isinstance(latest_eval.get("sentiment_accuracy"), (int, float)))
check("latest_eval has total_eval_cases", latest_eval.get("total_eval_cases", 0) > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: Review counts (renders "指标卡")
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: Review counts (metric cards) ===")
with get_connection() as conn:
    # Total valid reviews
    valid = conn.execute(
        "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ? AND is_valid = 1",
        (batch_id,),
    ).fetchone()["cnt"]
    check("valid review count = 13", valid == 13, f"count={valid}")

    # Average rating
    avg_row = conn.execute(
        "SELECT AVG(CAST(rating AS REAL)) as avg_r FROM reviews WHERE batch_id = ? AND is_valid = 1",
        (batch_id,),
    ).fetchone()
    avg_rating = round(avg_row["avg_r"], 1) if avg_row and avg_row["avg_r"] else 0
    check("avg_rating > 0", avg_rating > 0, f"avg={avg_rating}")
    check("avg_rating is float", isinstance(avg_rating, float), f"type={type(avg_rating)}")

    # Negative count
    neg = conn.execute(
        "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ? AND is_negative_candidate = 1",
        (batch_id,),
    ).fetchone()["cnt"]
    check("negative count = 5", neg == 5, f"count={neg}")

    # Pending draft count
    pending_db = conn.execute(
        "SELECT COUNT(*) as cnt FROM reply_drafts WHERE batch_id = ? AND approval_status = 'pending'",
        (batch_id,),
    ).fetchone()["cnt"]
    check("pending draft count = 4", pending_db == 4, f"count={pending_db}")

    # Analysis exists
    analysis_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?", (batch_id,),
    ).fetchone()["cnt"]
    check("review_analysis has data", analysis_cnt > 0, f"count={analysis_cnt}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: Edge cases — no batch / no analysis
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: Edge cases ===")
nonexistent_issues = insight_svc.get_top_issues("batch-nonexistent")
check("nonexistent batch: empty issues", isinstance(nonexistent_issues, list) and len(nonexistent_issues) == 0)

nonexistent_drafts = reply_svc.get_pending_drafts("batch-nonexistent")
check("nonexistent batch: empty drafts", isinstance(nonexistent_drafts, list) and len(nonexistent_drafts) == 0)

nonexistent_traces = trace_svc.get_trace("batch-nonexistent")
check("nonexistent batch: empty traces", isinstance(nonexistent_traces, list) and len(nonexistent_traces) == 0)

# Edge: draft_detail for non-existent
bad_detail = reply_svc.get_draft_detail(99999)
check("nonexistent draft_detail returns None", bad_detail is None)

# Edge: evidence for non-existent insight
bad_evidence = insight_svc.get_issue_evidence(99999)
check("nonexistent evidence returns empty", isinstance(bad_evidence, list) and len(bad_evidence) == 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: export_approved_replies
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 8: Export approved replies ===")
export = reply_svc.export_approved_replies(batch_id)
check("export returns dict", isinstance(export, dict))
check("export batch_id matches", export["batch_id"] == batch_id)
# No drafts approved yet, so count should be 0
check("export count = 0 (none approved)", export["count"] == 0,
      f"count={export['count']}")
check("export drafts is empty list", isinstance(export["drafts"], list) and len(export["drafts"]) == 0)

# Approve one and verify export works
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
rpr = ReplyRepository()
coff04 = rpr.get_draft_by_review(batch_id, "COFF04")
reply_svc.approve_draft(coff04["id"])
export2 = reply_svc.export_approved_replies(batch_id)
check("export after approve: count=1", export2["count"] == 1,
      f"count={export2['count']}")
check("export has COFF04", export2["drafts"][0]["review_id"] == "COFF04")

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
    logger.success("ALL DASHBOARD DATA SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
