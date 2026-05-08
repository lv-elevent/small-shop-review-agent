"""
Phase 9 smoke test — simulates Trace & Eval page data loading:
  TraceService.get_trace + EvalService.run_eval / get_latest_eval / list_eval_runs
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
from small_shop_agent.services.trace_service import TraceService
from small_shop_agent.services.eval_service import EvalService

rs = ReviewService()
ws = WorkflowService()
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

# ═══════════════════════════════════════════════════════════════════════════
# Test 1: TraceService.get_trace — workflow traces
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: TraceService.get_trace ===")
traces = trace_svc.get_trace(batch_id)
check("get_trace returns 8 traces", len(traces) == 8, f"count={len(traces)}")

expected_steps = [
    "input_validation", "data_cleaning", "classification",
    "sentiment_analysis", "issue_aggregation", "evidence_check",
    "reply_drafting", "safety_check",
]
step_names = [t["step_name"] for t in traces]
for step in expected_steps:
    check(f"trace contains '{step}'", step in step_names)

# Verify trace fields completeness
for t in traces:
    check(f"trace '{t['step_name']}' has status",
          t.get("status") in ("passed", "warning", "failed"),
          f"status={t.get('status')}")
    check(f"trace '{t['step_name']}' has input_summary",
          bool(t.get("input_summary", "").strip()),
          f"input_summary='{t.get('input_summary', '')}'")
    check(f"trace '{t['step_name']}' has output_summary",
          bool(t.get("output_summary", "").strip()),
          f"output_summary='{t.get('output_summary', '')}'")
    check(f"trace '{t['step_name']}' has created_at",
          bool(t.get("created_at")),
          f"created_at={t.get('created_at')}")
    # latency_ms may be 0 for rule-based steps
    check(f"trace '{t['step_name']}' has latency_ms",
          isinstance(t.get("latency_ms"), (int, float)),
          f"latency_ms={t.get('latency_ms')}")

# Verify specific trace details
trace_map = {t["step_name"]: t for t in traces}
input_val = trace_map["input_validation"]
check("input_validation: valid=13 in output", "valid=13" in input_val["output_summary"])
safety = trace_map["safety_check"]
check("safety_check: includes blocked", "blocked" in safety["output_summary"].lower()
      or "1" in safety["output_summary"])
cleaning = trace_map["data_cleaning"]
check("data_cleaning: status=warning", cleaning["status"] == "warning")

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: TraceService.get_latest_trace
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: TraceService.get_latest_trace ===")
latest_traces = trace_svc.get_latest_trace()
check("get_latest_trace returns list", isinstance(latest_traces, list))
check("get_latest_trace not empty", len(latest_traces) > 0)
check("get_latest_trace contains our batch",
      any(t["batch_id"] == batch_id for t in latest_traces))

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: EvalService.run_eval
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: EvalService.run_eval ===")
eval_result = eval_svc.run_eval({"batch_id": batch_id})
check("run_eval success", eval_result["success"] is True, str(eval_result))
check("run_eval has eval_run_id", bool(eval_result.get("eval_run_id")))
eval_run_id = eval_result["eval_run_id"]

report = eval_result["report"]
check("report has topic_accuracy", isinstance(report["topic_accuracy"], float))
check("report has sentiment_accuracy", isinstance(report["sentiment_accuracy"], float))
check("report topic_accuracy >= 0", report["topic_accuracy"] >= 0)
check("report sentiment_accuracy >= 0", report["sentiment_accuracy"] >= 0)
check("report unsafe_reply_count > 0", report["unsafe_reply_count"] > 0)
check("report total_eval_cases > 0", report["total_eval_cases"] > 0)
check("report has schema_failure_count", isinstance(report["schema_failure_count"], int))

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: eval_results DB table
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: eval_results table ===")
with get_connection() as conn:
    eval_rows = conn.execute(
        "SELECT * FROM eval_results WHERE batch_id = ? ORDER BY id", (batch_id,)
    ).fetchall()
    check("eval_results has 1 row", len(eval_rows) == 1, f"count={len(eval_rows)}")
    er = dict(eval_rows[0])
    check("eval_result eval_run_id matches", er["eval_run_id"] == eval_run_id)
    check("eval_result has topic_accuracy", isinstance(er["topic_accuracy"], (int, float)))
    check("eval_result has sentiment_accuracy", isinstance(er["sentiment_accuracy"], (int, float)))
    check("eval_result has unsafe_reply_count", isinstance(er["unsafe_reply_count"], int))
    check("eval_result has schema_failure_count", isinstance(er["schema_failure_count"], int))
    check("eval_result has total_eval_cases", er["total_eval_cases"] > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: eval_run trace written
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: eval_run trace ===")
all_traces = trace_svc.get_trace(batch_id)
check("traces now 9 (8 workflow + 1 eval)", len(all_traces) == 9,
      f"count={len(all_traces)}")
eval_traces = [t for t in all_traces if t["step_name"] == "eval_run"]
check("eval_run trace exists", len(eval_traces) == 1, f"count={len(eval_traces)}")
et = eval_traces[0]
check("eval_run trace status passed/warning", et["status"] in ("passed", "warning"))
check("eval_run trace has output_summary", bool(et.get("output_summary")))

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: EvalService.get_latest_eval
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: EvalService.get_latest_eval ===")
latest = eval_svc.get_latest_eval()
check("get_latest_eval returns dict", latest is not None)
check("get_latest_eval eval_run_id matches", latest["eval_run_id"] == eval_run_id)
check("get_latest_eval has all fields",
      all(k in latest for k in ["topic_accuracy", "sentiment_accuracy",
                                 "unsafe_reply_count", "schema_failure_count",
                                 "total_eval_cases"]))

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: EvalService.list_eval_runs
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: EvalService.list_eval_runs ===")
runs = eval_svc.list_eval_runs(limit=10)
check("list_eval_runs returns list", isinstance(runs, list))
check("list_eval_runs not empty", len(runs) >= 1, f"count={len(runs)}")
# Our run should be in the list
run_ids = [r["eval_run_id"] for r in runs]
check("our eval_run_id in list", eval_run_id in run_ids)

# Run a second eval to test list ordering
eval_svc.run_eval({"batch_id": batch_id})
runs2 = eval_svc.list_eval_runs(limit=10)
check("list_eval_runs after second eval: >= 2", len(runs2) >= 2)
check("list_eval_runs limit=2 works", len(eval_svc.list_eval_runs(limit=2)) == 2)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: Edge cases
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 8: Edge cases ===")
empty_traces = trace_svc.get_trace("batch-nonexistent")
check("nonexistent batch: empty traces", isinstance(empty_traces, list) and len(empty_traces) == 0)

empty_eval = eval_svc.run_eval({"batch_id": "batch-nonexistent"})
check("eval nonexistent batch fails", empty_eval["success"] is False)

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
    logger.success("ALL TRACE & EVAL PAGE DATA SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
