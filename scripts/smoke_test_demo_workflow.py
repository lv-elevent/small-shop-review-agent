"""
Phase 4 smoke test — exercises WorkflowService.run_demo_analysis full pipeline.
Covers: valid batch, missing batch, empty-batch, re-run idempotency, workflow status.
"""
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import pandas as pd
from loguru import logger

from small_shop_agent.storage.database import execute_migrations, get_connection
execute_migrations()

from small_shop_agent.services.review_service import ReviewService
from small_shop_agent.services.workflow_service import WorkflowService
from small_shop_agent.storage.repositories.trace_repository import TraceRepository

rs = ReviewService()
ws = WorkflowService()
tr = TraceRepository()

passed = 0
failed = 0

VALID_TRACE_STEPS = {
    "classification", "sentiment_analysis", "issue_aggregation",
    "evidence_check", "reply_drafting", "safety_check",
}


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        logger.success(f"  PASS: {label}")
    else:
        failed += 1
        logger.error(f"  FAIL: {label} — {detail}")


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: run_demo_analysis — full happy path with sample_reviews.csv
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: run_demo_analysis with sample_reviews.csv ===")

sample_csv = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
create_result = rs.create_batch(str(sample_csv), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create_batch success", create_result["success"] is True, str(create_result))
batch_id = create_result["batch_id"]
check("batch_id returned", batch_id is not None and batch_id.startswith("batch-"))

batch_before = rs.get_batch_summary(batch_id)
check("batch has valid reviews", batch_before["valid_review_count"] > 0,
      f"valid_review_count={batch_before.get('valid_review_count')}")

# Run the full demo analysis
result = ws.run_demo_analysis(batch_id)
check("run_demo_analysis success", result["success"] is True, str(result))
check("mode is demo", result["mode"] == "demo")
check("batch_id matches", result["batch_id"] == batch_id)
check("error is None", result["error"] is None)

summary = result["summary"]
check("review_count > 0", summary["review_count"] > 0,
      f"review_count={summary.get('review_count')}")
check("negative_count > 0", summary["negative_count"] > 0,
      f"negative_count={summary.get('negative_count')}")
check("insight_count between 1-3", 1 <= summary["insight_count"] <= 3,
      f"insight_count={summary.get('insight_count')}")
check("draft_count > 0", summary["draft_count"] > 0,
      f"draft_count={summary.get('draft_count')}")
check("evidence_count > 0", summary["evidence_count"] > 0,
      f"evidence_count={summary.get('evidence_count')}")
check("trace_count is 6", summary["trace_count"] == 6)

# Batch status check
batch_after = rs.get_batch_summary(batch_id)
check("batch.status = analyzed", batch_after["status"] == "analyzed",
      f"status={batch_after.get('status')}")
check("negative_review_count populated", batch_after.get("negative_review_count", 0) > 0)
check("pending_reply_count populated", batch_after.get("pending_reply_count", 0) > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: review_analysis has data
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: review_analysis table ===")
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
ar = AnalysisRepository()
analysis_list = ar.list_analysis(batch_id)
check("review_analysis has data", len(analysis_list) > 0,
      f"count={len(analysis_list)}")
check("each row has topics", all(isinstance(a.get("topics"), list) for a in analysis_list))
check("each row has primary_topic", all(a.get("primary_topic") for a in analysis_list))
check("each row has sentiment", all(a.get("sentiment") for a in analysis_list))

negatives = ar.get_negative_candidates(batch_id)
check("negative_candidates > 0", len(negatives) > 0,
      f"count={len(negatives)}")
# Verify negative candidates match the expected COFF04/06/08/12/13
neg_ids = {n["review_id"] for n in negatives}
expected_neg = {"COFF04", "COFF06", "COFF08", "COFF12", "COFF13"}
check("negative candidates match expected COFF04/06/08/12/13",
      expected_neg.issubset(neg_ids),
      f"found={neg_ids}, expected subset={expected_neg}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: insights and insight_evidence
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: insights + insight_evidence ===")
from small_shop_agent.storage.repositories.insight_repository import InsightRepository
ir = InsightRepository()
insights_list = ir.get_top_issues(batch_id)
check("insights between 1-3", 1 <= len(insights_list) <= 3,
      f"count={len(insights_list)}")
check("ranks are 1, 2, 3", [i["rank"] for i in insights_list] == [1, 2, 3])
check("rank 1 topic=hygiene", insights_list[0]["topic"] == "hygiene")
check("rank 2 topic=waiting_time", insights_list[1]["topic"] == "waiting_time")
check("rank 3 topic=service", insights_list[2]["topic"] == "service")

for ins in insights_list:
    check(f"insight rank {ins['rank']} has issue_name", bool(ins["issue_name"]))
    check(f"insight rank {ins['rank']} severity_level valid",
          ins["severity_level"] in ("low", "medium", "high"))
    check(f"insight rank {ins['rank']} evidence_count > 0", ins["evidence_count"] > 0)

evidence_list = ir.get_evidence_by_batch(batch_id)
check("insight_evidence has data", len(evidence_list) > 0,
      f"count={len(evidence_list)}")
check("evidence has 5 rows", len(evidence_list) == 5,
      f"count={len(evidence_list)}")
for ev in evidence_list:
    check(f"evidence has issue_name", bool(ev.get("issue_name")))
    check(f"evidence has review_id", bool(ev.get("review_id")))
    check(f"evidence has evidence_text", bool(ev.get("evidence_text")))

# Verify evidence is linked to valid insight IDs
insight_ids = {i["id"] for i in insights_list}
for ev in evidence_list:
    check(f"evidence {ev['review_id']} links to valid insight", ev["insight_id"] in insight_ids)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: reply_drafts
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: reply_drafts ===")
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
rpr = ReplyRepository()
drafts = rpr.list_drafts(batch_id)
check("reply_drafts has data", len(drafts) > 0, f"count={len(drafts)}")
check("reply_drafts has 5", len(drafts) == 5, f"count={len(drafts)}")

pending_drafts = rpr.get_pending_drafts(batch_id)
check("pending drafts exist", len(pending_drafts) > 0)

safety_counts: dict[str, int] = {}
for d in drafts:
    safety_counts[d["safety_status"]] = safety_counts.get(d["safety_status"], 0) + 1
    check(f"draft {d['review_id']} has draft_text", bool(d["draft_text"]))
    check(f"draft {d['review_id']} has original_review", bool(d["original_review"]))
    check(f"draft {d['review_id']} approval_status valid",
          d["approval_status"] in ("pending", "approved", "edited", "rejected", "blocked"))
check("has pass safety", safety_counts.get("pass", 0) > 0,
      f"safety_counts={safety_counts}")
check("has rewrite_required", safety_counts.get("rewrite_required", 0) == 1,
      f"safety_counts={safety_counts}")
check("has blocked", safety_counts.get("blocked", 0) == 1,
      f"safety_counts={safety_counts}")

# Verify specific safety statuses
coff04 = rpr.get_draft_by_review(batch_id, "COFF04")
check("COFF04 safety=pass", coff04 is not None and coff04["safety_status"] == "pass")
coff06 = rpr.get_draft_by_review(batch_id, "COFF06")
check("COFF06 safety=rewrite_required", coff06 is not None and coff06["safety_status"] == "rewrite_required")
coff08 = rpr.get_draft_by_review(batch_id, "COFF08")
check("COFF08 safety=blocked", coff08 is not None and coff08["safety_status"] == "blocked")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: traces
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: traces ===")
traces = tr.get_traces(batch_id)
check("traces exist", len(traces) > 0, f"count={len(traces)}")

# Check workflow-specific steps (from run_demo_analysis)
workflow_traces = [t for t in traces if t["step_name"] in VALID_TRACE_STEPS]
check("has classification trace", any(t["step_name"] == "classification" for t in workflow_traces))
check("has sentiment_analysis trace", any(t["step_name"] == "sentiment_analysis" for t in workflow_traces))
check("has issue_aggregation trace", any(t["step_name"] == "issue_aggregation" for t in workflow_traces))
check("has evidence_check trace", any(t["step_name"] == "evidence_check" for t in workflow_traces))
check("has reply_drafting trace", any(t["step_name"] == "reply_drafting" for t in workflow_traces))
check("has safety_check trace", any(t["step_name"] == "safety_check" for t in workflow_traces))

for t in workflow_traces:
    step = t["step_name"]
    check(f"trace {step} status valid", t["status"] in ("passed", "warning", "failed", "pending"),
          f"status={t['status']}")
    check(f"trace {step} has input_summary", bool(t.get("input_summary")),
          f"input_summary='{t.get('input_summary', '')}'")
    check(f"trace {step} has output_summary", bool(t.get("output_summary")),
          f"output_summary='{t.get('output_summary', '')}'")
    check(f"trace {step} has latency_ms", isinstance(t.get("latency_ms"), int))
    check(f"trace {step} has trace_id", bool(t.get("trace_id")))

# safety_check should be warning when blocked drafts exist
safety_trace = next((t for t in workflow_traces if t["step_name"] == "safety_check"), None)
if safety_trace:
    check("safety_check has warning status (blocked found)",
          safety_trace["status"] == "warning",
          f"status={safety_trace['status']}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: get_workflow_status
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: get_workflow_status ===")
status = ws.get_workflow_status(batch_id)
check("get_workflow_status success", status["success"] is True)
check("has batch info", status["batch"] is not None)
check("has traces list", isinstance(status["traces"], list) and len(status["traces"]) > 0)
check("has counts", isinstance(status["counts"], dict))
check("counts.reviews > 0", status["counts"]["reviews"] > 0)
check("counts.valid_reviews > 0", status["counts"]["valid_reviews"] > 0)
check("counts.analysis > 0", status["counts"]["analysis"] > 0)
check("counts.insights > 0", status["counts"]["insights"] > 0)
check("counts.drafts > 0", status["counts"]["drafts"] > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: Non-existent batch returns success=False
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: Non-existent batch ===")
fake_result = ws.run_demo_analysis("batch-nonexistent-99999")
check("non-existent batch success=False", fake_result["success"] is False)
check("has error message", bool(fake_result.get("error")))

fake_status = ws.get_workflow_status("batch-nonexistent-99999")
check("non-existent batch status success=False", fake_status["success"] is False)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: Batch with no valid reviews returns success=False
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 8: No valid reviews batch ===")
empty_csv = pd.DataFrame({
    "review_id": ["NV001", "NV002"],
    "date": ["2025-01-01", "2025-01-02"],
    "platform": ["test", "test"],
    "rating": [0, 6],  # both invalid ratings
    "review_text": ["text A", "text B"],
})
empty_result = rs.create_batch(empty_csv.to_csv(index=False).encode("utf-8"),
                               store_type="coffee_shop", file_name="novalid.csv")
check("empty batch created", empty_result["success"] is True)
empty_batch_id = empty_result["batch_id"]
empty_batch = rs.get_batch_summary(empty_batch_id)
check("empty batch valid_review_count=0", empty_batch["valid_review_count"] == 0)

empty_analysis = ws.run_demo_analysis(empty_batch_id)
check("no-valid-reviews batch success=False", empty_analysis["success"] is False)
check("has error message", bool(empty_analysis.get("error")))

# Verify failed trace was written
empty_traces = tr.get_traces(empty_batch_id)
classification_traces = [t for t in empty_traces if t["step_name"] == "classification"]
check("failed trace written for empty batch", len(classification_traces) > 0)
failed_trace = next((t for t in classification_traces if t["status"] == "failed"), None)
check("trace status is failed", failed_trace is not None,
      f"traces={[(t['step_name'], t['status']) for t in empty_traces]}")

# Verify batch marked as failed
empty_batch_after = rs.get_batch_summary(empty_batch_id)
check("empty batch status=failed", empty_batch_after["status"] == "failed")

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: Re-run idempotency — does not crash, no duplicate dirty data
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 9: Re-run idempotency ===")
# Count records before re-run
def count_table(table: str, bid: str) -> int:
    with get_connection() as conn:
        row = conn.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE batch_id = ?", (bid,)).fetchone()
        return row["cnt"] if row else 0

analysis_before = count_table("review_analysis", batch_id)
insights_before = count_table("insights", batch_id)
evidence_before = count_table("insight_evidence", batch_id)
drafts_before = count_table("reply_drafts", batch_id)

# Re-run
rerun_result = ws.run_demo_analysis(batch_id)
check("re-run success", rerun_result["success"] is True)

# Count after
analysis_after = count_table("review_analysis", batch_id)
insights_after = count_table("insights", batch_id)
evidence_after = count_table("insight_evidence", batch_id)
drafts_after = count_table("reply_drafts", batch_id)

# INSERT OR REPLACE ensures counts stay the same
check("re-run: analysis count unchanged", analysis_after == analysis_before,
      f"{analysis_before} → {analysis_after}")
check("re-run: insights count unchanged", insights_after == insights_before,
      f"{insights_before} → {insights_after}")
check("re-run: evidence count unchanged", evidence_after == evidence_before,
      f"{evidence_before} → {evidence_after}")
check("re-run: drafts count unchanged", drafts_after == drafts_before,
      f"{drafts_before} → {drafts_after}")

# Re-run on empty batch should also not crash
rerun_empty = ws.run_demo_analysis(empty_batch_id)
check("re-run empty batch: still fails gracefully", rerun_empty["success"] is False)

# ═══════════════════════════════════════════════════════════════════════════
# Cleanup — remove smoke test data
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Cleanup ===")
for bid in [batch_id, empty_batch_id]:
    if bid:
        with get_connection() as conn:
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
    logger.success("ALL WORKFLOW SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
