"""
Phase 1 smoke test — exercises every repository method.
Deletes the smoke test batch afterwards (cleanup).
"""
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from loguru import logger
from small_shop_agent.storage.database import execute_migrations

# Ensure DB is ready
execute_migrations()

from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.analysis_repository import AnalysisRepository
from small_shop_agent.storage.repositories.insight_repository import InsightRepository
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.storage.repositories.eval_repository import EvalRepository

batch_id = f"smoke-{uuid.uuid4().hex[:8]}"
trace_id = f"trace-{batch_id}"
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
# 1. BatchRepository
logger.info("--- BatchRepository ---")
br = BatchRepository()
b = br.create_batch(batch_id=batch_id, store_type="coffee_shop", source_type="demo_mode",
                    total_rows=2, valid_review_count=2)
check("create_batch returns dict", isinstance(b, dict))
check("create_batch has batch_id", b.get("batch_id") == batch_id)

b2 = br.get_batch(batch_id)
check("get_batch returns dict", isinstance(b2, dict))
check("get_batch matches", b2["batch_id"] == batch_id)

b3 = br.update_status(batch_id, "analyzed", valid_review_count=2)
check("update_status works", b3 and b3["status"] == "analyzed")

b4 = br.get_latest_batch()
check("get_latest_batch works", b4 is not None and b4["batch_id"] is not None)

batches = br.list_batches()
check("list_batches returns list", isinstance(batches, list) and len(batches) > 0)

# ═══════════════════════════════════════════════════════════════════════════
# 2. ReviewRepository
logger.info("--- ReviewRepository ---")
rr = ReviewRepository()
reviews = [
    {"review_id": "R001", "review_text": "等太久了，差评", "rating": 1, "date": "2025-01-01", "platform": "美团"},
    {"review_id": "R002", "review_text": "非常好吃，很棒", "rating": 5, "date": "2025-01-02", "platform": "大众点评"},
]
n = rr.bulk_insert_reviews(batch_id, reviews)
check("bulk_insert_reviews count", n == 2)

all_r = rr.list_reviews(batch_id)
check("list_reviews returns 2", len(all_r) == 2)

valid_r = rr.list_reviews(batch_id, is_valid=True)
check("list_reviews is_valid filter", len(valid_r) == 2)

r1 = rr.get_review(batch_id, "R001")
check("get_review found", r1 is not None and r1["review_text"] == "等太久了，差评")

cnt = rr.count_reviews(batch_id)
check("count_reviews", cnt == 2)

# ═══════════════════════════════════════════════════════════════════════════
# 3. AnalysisRepository
logger.info("--- AnalysisRepository ---")
ar = AnalysisRepository()
analysis = [
    {"review_id": "R001", "topics": ["waiting_time"], "primary_topic": "waiting_time",
     "sentiment": "negative", "severity": 4, "topic_confidence": 0.9,
     "sentiment_confidence": 0.92, "is_negative_candidate": True, "needs_review": False},
    {"review_id": "R002", "topics": ["product", "service"], "primary_topic": "product",
     "sentiment": "positive", "severity": 1, "topic_confidence": 0.88,
     "sentiment_confidence": 0.95, "is_negative_candidate": False, "needs_review": False},
]
n = ar.bulk_insert_analysis(batch_id, analysis)
check("bulk_insert_analysis count", n == 2)

all_a = ar.list_analysis(batch_id)
check("list_analysis returns 2", len(all_a) == 2)
check("topics deserialized", isinstance(all_a[0]["topics"], list))

neg = ar.get_negative_candidates(batch_id)
check("get_negative_candidates returns 1", len(neg) == 1 and neg[0]["review_id"] == "R001")

counts = ar.count_by_sentiment(batch_id)
check("count_by_sentiment negative=1", counts.get("negative") == 1)
check("count_by_sentiment positive=1", counts.get("positive") == 1)

# ═══════════════════════════════════════════════════════════════════════════
# 4. InsightRepository (insights + evidence)
logger.info("--- InsightRepository ---")
ir = InsightRepository()
insights = [
    {"rank": 1, "issue_name": "出餐速度慢", "topic": "waiting_time", "mention_count": 5,
     "severity_level": "high", "priority_score": 0.9, "suggested_action": "增加人手", "evidence_count": 0},
]
n = ir.bulk_insert_insights(batch_id, insights)
check("bulk_insert_insights count", n == 1)

top3 = ir.get_top_issues(batch_id)
check("get_top_issues returns 1", len(top3) == 1 and top3[0]["issue_name"] == "出餐速度慢")
insight_id = top3[0]["id"]

evidence = [
    {"insight_id": insight_id, "review_id": "R001", "evidence_text": "等太久了", "evidence_reason": "明确抱怨等待时间"},
]
n = ir.bulk_insert_evidence(batch_id, evidence)
check("bulk_insert_evidence count", n == 1)

ev = ir.get_issue_evidence(insight_id)
check("get_issue_evidence returns 1", len(ev) == 1 and ev[0]["review_id"] == "R001")

evb = ir.get_evidence_by_batch(batch_id)
check("get_evidence_by_batch", len(evb) == 1 and evb[0]["issue_name"] == "出餐速度慢")

# ═══════════════════════════════════════════════════════════════════════════
# 5. ReplyRepository (drafts + approval_actions)
logger.info("--- ReplyRepository ---")
rpr = ReplyRepository()
drafts = [
    {"review_id": "R001", "original_review": "等太久了，差评",
     "draft_text": "非常抱歉让您久等了，我们会改进。", "safety_status": "pass",
     "risk_types": [], "approval_status": "pending", "model_name": "demo"},
]
n = rpr.bulk_insert_drafts(batch_id, drafts)
check("bulk_insert_drafts count", n == 1)

draft_detail = rpr.get_draft_by_review(batch_id, "R001")
check("get_draft_by_review found", draft_detail is not None)
draft_id = draft_detail["id"] if draft_detail else 0

pending = rpr.get_pending_drafts(batch_id)
check("get_pending_drafts returns 1", len(pending) == 1)

all_d = rpr.list_drafts(batch_id)
check("list_drafts returns 1", len(all_d) == 1)

updated = rpr.update_approval_status(draft_id, "approved",
                                      edited_text="已编辑回复", final_text="最终回复")
check("update_approval_status approved", updated is not None and updated["approval_status"] == "approved")

aa = rpr.insert_approval_action(draft_id=draft_id, batch_id=batch_id,
                                 review_id="R001", action="approve",
                                 before_text="非常抱歉让您久等了", after_text="已编辑回复")
check("insert_approval_action", isinstance(aa, dict) and aa.get("action") == "approve")

# ═══════════════════════════════════════════════════════════════════════════
# 6. TraceRepository
logger.info("--- TraceRepository ---")
tr = TraceRepository()
t1 = tr.log_step(trace_id=trace_id, batch_id=batch_id,
                  step_name="input_validation", status="passed",
                  input_summary="2 reviews", output_summary="all valid", latency_ms=5)
check("log_step creates trace", isinstance(t1, dict) and t1["step_name"] == "input_validation")

t2 = tr.log_step(trace_id=trace_id, batch_id=batch_id,
                  step_name="classification", status="passed",
                  input_summary="2 reviews", output_summary="classified", latency_ms=12)
check("log_step second", isinstance(t2, dict) and t2["step_name"] == "classification")

traces = tr.get_traces(batch_id)
check("get_traces returns 2", len(traces) == 2)

latest = tr.get_latest_trace()
check("get_latest_trace returns list", isinstance(latest, list))

by_id = tr.get_trace_by_id(trace_id)
check("get_trace_by_id returns 2", len(by_id) == 2)

# ═══════════════════════════════════════════════════════════════════════════
# 7. EvalRepository
logger.info("--- EvalRepository ---")
er = EvalRepository()
eval_run_id = f"eval-{uuid.uuid4().hex[:8]}"
ev1 = er.save_eval_result(eval_run_id=eval_run_id, batch_id=batch_id,
                           topic_accuracy=0.92, sentiment_accuracy=0.88,
                           unsafe_reply_count=0, schema_failure_count=0,
                           total_eval_cases=2, topic_correct_count=2,
                           sentiment_correct_count=2)
check("save_eval_result", isinstance(ev1, dict) and ev1["eval_run_id"] == eval_run_id)

ev2 = er.get_eval_result(eval_run_id)
check("get_eval_result found", ev2 is not None and ev2["topic_accuracy"] == 0.92)

ev3 = er.get_latest_eval()
check("get_latest_eval found", ev3 is not None)

runs = er.list_eval_runs(limit=5)
check("list_eval_runs", isinstance(runs, list) and len(runs) > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Cleanup — delete smoke test data
logger.info("--- Cleanup ---")
from small_shop_agent.storage.database import get_connection
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
    logger.success("ALL SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
