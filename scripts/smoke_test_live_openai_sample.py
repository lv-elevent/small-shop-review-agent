"""Smoke test for live OpenAI workflow — requires OPENAI_API_KEY, skips gracefully without it.
Validates database structure integrity only; does NOT check classification/sentiment/reply accuracy."""
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ── Step 1: Environment check ───────────────────────────────────────────
if not os.environ.get("OPENAI_API_KEY", "").strip():
    print("Skipping live OpenAI test - no API key")
    sys.exit(0)

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
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label} — {detail}")


# ── Step 2: Create batch from sample CSV ────────────────────────────────
print("=== Step 2: Create batch ===")
csv_path = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
result = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create_batch success", result["success"] is True, str(result))
batch_id = result["batch_id"]
check("batch_id returned", bool(batch_id))
check("valid_review_count > 0", result["validation"].get("valid_review_count", 0) > 0)

# ── Step 3: Run live analysis ───────────────────────────────────────────
print("\n=== Step 3: Run live analysis (mode='live') ===")
wf = ws.run_analysis(batch_id, mode="live")
check("workflow success", wf["success"] is True, wf.get("error", str(wf)))
check("mode is live", wf.get("mode") == "live")
summary = wf.get("summary", {})
check("review_count > 0", summary.get("review_count", 0) > 0,
      f"review_count={summary.get('review_count')}")
check("insight_count > 0", summary.get("insight_count", 0) > 0,
      f"insight_count={summary.get('insight_count')}")
check("draft_count > 0", summary.get("draft_count", 0) > 0,
      f"draft_count={summary.get('draft_count')}")
check("trace_count > 0", summary.get("trace_count", 0) > 0,
      f"trace_count={summary.get('trace_count')}")

# ── Step 4: Structure integrity checks ──────────────────────────────────
print("\n=== Step 4: DB structure integrity ===")

with get_connection() as conn:
    # review_analysis
    analysis_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("review_analysis has data", analysis_cnt > 0, f"count={analysis_cnt}")

    # insights
    insight_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM insights WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("insights has data", insight_cnt > 0, f"count={insight_cnt}")

    # insight_evidence
    evidence_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM insight_evidence WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("insight_evidence has data", evidence_cnt > 0, f"count={evidence_cnt}")

    # reply_drafts
    draft_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM reply_drafts WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("reply_drafts has data", draft_cnt > 0, f"count={draft_cnt}")

    # traces
    trace_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM traces WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("traces has data", trace_cnt > 0, f"count={trace_cnt}")

# ── Step 5: Cleanup ─────────────────────────────────────────────────────
print("\n=== Step 5: Cleanup ===")
with get_connection() as conn:
    for tbl in ["approval_actions", "insight_evidence", "reply_drafts",
                "review_analysis", "insights", "traces", "eval_results",
                "reviews", "review_batches"]:
        conn.execute(f"DELETE FROM {tbl} WHERE batch_id = ?", (batch_id,))
    conn.commit()
print("  Cleanup done")

# ── Results ─────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"LIVE OPENAI SMOKE TEST: {passed} passed, {failed} failed")
print("(Structure integrity only — accuracy not checked)")
if failed == 0:
    print("LIVE OPENAI SMOKE TEST PASSED")
else:
    print(f"LIVE OPENAI SMOKE TEST FAILED — {failed} test(s) failed")
    sys.exit(1)
