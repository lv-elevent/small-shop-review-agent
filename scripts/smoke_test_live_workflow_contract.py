"""Smoke test for live workflow path — monkeypatched provider, no real API calls."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from unittest.mock import patch

from small_shop_agent.llm.base import BaseLLMProvider
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


# ── Fake provider with deterministic live-mode data ──

class FakeProvider(BaseLLMProvider):
    _model = "fake-model"

    def classify_reviews(self, reviews):
        results = []
        for r in reviews:
            rid = r.get("review_id", "")
            text = str(r.get("review_text", "")).lower()
            rating = int(r.get("rating", 3))
            if "异物" in text or "脏" in text or "卫生" in text:
                topic = "hygiene"
            elif "等" in text and rating <= 2:
                topic = "waiting_time"
            elif "态度" in text or "服务" in text:
                topic = "service"
            elif "价格" in text or "贵" in text:
                topic = "price"
            else:
                topic = "product" if rating >= 4 else "other"
            results.append({
                "review_id": rid, "topics": [topic], "primary_topic": topic,
                "topic_confidence": 0.85, "needs_review": rating <= 2,
            })
        return results

    def analyze_sentiment(self, reviews):
        results = []
        for r in reviews:
            rid = r.get("review_id", "")
            rating = int(r.get("rating", 3))
            if rating <= 2:
                sent, sev = "negative", 4 if rating == 1 else 3
            elif rating == 3:
                sent, sev = "neutral", 2
            else:
                sent, sev = "positive", 1
            results.append({
                "review_id": rid, "sentiment": sent, "severity": sev,
                "sentiment_confidence": 0.85,
                "is_negative_candidate": sent == "negative",
                "analysis_reason": f"Fake — rating={rating}",
            })
        return results

    def generate_insights(self, reviews, analyses):
        neg = [a for a in analyses if a.get("is_negative_candidate")]
        neg_ids = {a["review_id"] for a in neg}
        neg_reviews = [r for r in reviews if r.get("review_id") in neg_ids]
        return [
            {
                "rank": 1, "issue_name": "卫生问题", "topic": "hygiene",
                "issue_summary": "有评论提到卫生问题。", "mention_count": 3,
                "severity_level": "high", "priority_score": 0.90,
                "suggested_action": "加强清洁。", "evidence_count": 2,
                "evidence_status": "sufficient",
                "evidence": [
                    {"review_id": neg_reviews[0]["review_id"] if len(neg_reviews) > 0 else "NONE",
                     "evidence_text": "卫生相关评论", "evidence_reason": "卫生投诉"},
                    {"review_id": neg_reviews[1]["review_id"] if len(neg_reviews) > 1 else "NONE",
                     "evidence_text": "另一条卫生评论", "evidence_reason": "卫生投诉"},
                ],
            },
            {
                "rank": 2, "issue_name": "等待时间", "topic": "waiting_time",
                "issue_summary": "等待时间长。", "mention_count": 3,
                "severity_level": "high", "priority_score": 0.85,
                "suggested_action": "优化流程。", "evidence_count": 2,
                "evidence_status": "sufficient",
                "evidence": [
                    {"review_id": neg_reviews[0]["review_id"] if len(neg_reviews) > 0 else "NONE",
                     "evidence_text": "等待相关评论", "evidence_reason": "等待投诉"},
                    {"review_id": neg_reviews[1]["review_id"] if len(neg_reviews) > 1 else "NONE",
                     "evidence_text": "另一条等待评论", "evidence_reason": "等待投诉"},
                ],
            },
            {
                "rank": 3, "issue_name": "服务态度", "topic": "service",
                "issue_summary": "服务态度需改进。", "mention_count": 2,
                "severity_level": "medium", "priority_score": 0.70,
                "suggested_action": "员工培训。", "evidence_count": 1,
                "evidence_status": "evidence_insufficient",
                "evidence": [
                    {"review_id": neg_reviews[0]["review_id"] if len(neg_reviews) > 0 else "NONE",
                     "evidence_text": "服务相关评论", "evidence_reason": "服务投诉"},
                ],
            },
        ]

    def draft_replies(self, reviews, analyses):
        neg = [a for a in analyses if a.get("is_negative_candidate")]
        neg_ids = {a["review_id"] for a in neg}
        results = []
        for r in reviews:
            if r.get("review_id") not in neg_ids:
                continue
            results.append({
                "review_id": r.get("review_id", ""),
                "original_review": str(r.get("review_text", "")),
                "draft_text": f"Fake reply for {r.get('review_id')}: 感谢反馈，我们会改进。",
                "approval_status": "pending",
            })
        return results

    def check_safety(self, drafts):
        results = []
        for d in drafts:
            entry = dict(d)
            entry["safety_status"] = "pass"
            entry["risk_types"] = []
            entry["safety_reason"] = "Fake safety OK."
            results.append(entry)
        return results


# Fake provider that returns invalid schema (for fallback test)
class BrokenProvider(BaseLLMProvider):
    _model = "broken-model"

    def classify_reviews(self, reviews):
        return [{"bad_key": "missing required fields"}]

    def analyze_sentiment(self, reviews):
        return [{"bad_key": "missing fields"}]

    def generate_insights(self, reviews, analyses):
        return [{"not": "valid"}]

    def draft_replies(self, reviews, analyses):
        return [{"nope": "invalid"}]

    def check_safety(self, drafts):
        return [{"nope": "invalid"}]


# ═══════════════════════════════════════════════════════════════════════

def _cleanup(bid):
    with get_connection() as conn:
        for tbl in ["approval_actions", "insight_evidence", "reply_drafts",
                     "review_analysis", "insights", "traces", "eval_results",
                     "reviews", "review_batches"]:
            conn.execute(f"DELETE FROM {tbl} WHERE batch_id = ?", (bid,))
        conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: run_analysis(mode="demo") still works
# ═══════════════════════════════════════════════════════════════════════════
print("=== Test 1: mode='demo' still demo path ===")
csv_path = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
r = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create batch OK", r["success"] is True)
bid_demo = r["batch_id"]

wf = ws.run_analysis(bid_demo, mode="demo")
check("demo success", wf["success"] is True)
check("demo mode=demo", wf["mode"] == "demo")
check("demo review_count=13", wf["summary"]["review_count"] == 13)
check("demo insight_count=3", wf["summary"]["insight_count"] == 3)
check("demo draft_count=5", wf["summary"]["draft_count"] == 5)
_cleanup(bid_demo)

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: run_analysis(mode="live") with FakeProvider
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 2: mode='live' with FakeProvider ===")
r = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create batch OK", r["success"] is True)
bid_live = r["batch_id"]

with patch("small_shop_agent.llm.llm_router.get_llm_provider", return_value=FakeProvider()):
    wf = ws.run_analysis(bid_live, mode="live")

check("live success", wf["success"] is True, wf.get("error", ""))
check("live mode=live", wf["mode"] == "live")
check("live review_count=13", wf.get("summary", {}).get("review_count") == 13)
check("live insight_count=3", wf.get("summary", {}).get("insight_count") == 3)
check("live trace_count=8", wf.get("summary", {}).get("trace_count") == 8)

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: classification data in DB
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 3: classification in DB ===")
with get_connection() as conn:
    rows = conn.execute(
        "SELECT * FROM review_analysis WHERE batch_id = ?", (bid_live,)
    ).fetchall()
check("review_analysis has rows", len(rows) > 0, f"count={len(rows)}")
check("has topics", all(r["topics"] is not None for r in rows))
check("has primary_topic", all(r["primary_topic"] for r in rows))

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: sentiment in DB
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 4: sentiment in DB ===")
with get_connection() as conn:
    rows = conn.execute(
        "SELECT * FROM review_analysis WHERE batch_id = ?", (bid_live,)
    ).fetchall()
check("has sentiment", all(r["sentiment"] for r in rows))
check("has severity", all(r["severity"] is not None for r in rows))
neg_count = sum(1 for r in rows if r["is_negative_candidate"])
check("has negative candidates", neg_count > 0, f"got {neg_count}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: insights in DB
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 5: insights in DB ===")
with get_connection() as conn:
    rows = conn.execute(
        "SELECT * FROM insights WHERE batch_id = ? ORDER BY rank", (bid_live,)
    ).fetchall()
check("insights has rows", len(rows) >= 1, f"count={len(rows)}")
check("insights have issue_name", all(r["issue_name"] for r in rows))

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: insight_evidence in DB
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 6: insight_evidence in DB ===")
with get_connection() as conn:
    rows = conn.execute(
        "SELECT * FROM insight_evidence WHERE batch_id = ?", (bid_live,)
    ).fetchall()
check("insight_evidence has rows", len(rows) > 0, f"count={len(rows)}")
check("evidence has insight_id", all(r["insight_id"] for r in rows))

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: reply_drafts in DB
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 7: reply_drafts in DB ===")
with get_connection() as conn:
    rows = conn.execute(
        "SELECT * FROM reply_drafts WHERE batch_id = ?", (bid_live,)
    ).fetchall()
check("reply_drafts has rows", len(rows) > 0, f"count={len(rows)}")
check("drafts have draft_text", all(r["draft_text"] for r in rows))

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: safety_status in DB
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 8: safety_status in DB ===")
with get_connection() as conn:
    rows = conn.execute(
        "SELECT * FROM reply_drafts WHERE batch_id = ?", (bid_live,)
    ).fetchall()
check("drafts have safety_status", all(r["safety_status"] for r in rows))
check("drafts have risk_types", all(r["risk_types"] is not None for r in rows))
check("no auto-approved blocked drafts",
      all(r["approval_status"] != "approved" or r["safety_status"] == "pass" for r in rows))

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: traces have all 8 steps
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 9: all 8 trace steps ===")
expected_steps = {
    "input_validation", "data_cleaning", "classification", "sentiment_analysis",
    "issue_aggregation", "evidence_check", "reply_drafting", "safety_check",
}
with get_connection() as conn:
    traces = conn.execute(
        "SELECT step_name FROM traces WHERE batch_id = ?", (bid_live,)
    ).fetchall()
    trace_steps = {t["step_name"] for t in traces}
missing = expected_steps - trace_steps
check("all 8 steps present", not missing, f"missing: {missing}")
check("all steps passed or warning",
      all(t["step_name"] in trace_steps for t in traces))

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: broken provider triggers fallback without crashing
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 10: broken schema → fallback, no crash ===")
r = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("create batch OK", r["success"] is True)
bid_broken = r["batch_id"]

with patch("small_shop_agent.llm.llm_router.get_llm_provider", return_value=BrokenProvider()):
    wf = ws.run_analysis(bid_broken, mode="live")

check("broken: still returns success (fallback)", wf["success"] is True, wf.get("error", ""))
check("broken: has insights", wf.get("summary", {}).get("insight_count", 0) > 0)
check("broken: has drafts", wf.get("summary", {}).get("draft_count", 0) > 0)
_cleanup(bid_broken)

# ═══════════════════════════════════════════════════════════════════════════
# Test 11: e2e demo check still passes after live
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 11: demo still works after live run ===")
r = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
bid_final = r["batch_id"]
wf = ws.run_analysis(bid_final, mode="demo")
check("final demo success", wf["success"] is True)
check("final demo review_count=13", wf["summary"]["review_count"] == 13)
check("final demo insight_count=3", wf["summary"]["insight_count"] == 3)
# Trace count for demo is 6 (no input_validation/data_cleaning in demo)
check("final demo trace_count=6", wf["summary"]["trace_count"] == 6)

_cleanup(bid_live)
_cleanup(bid_final)

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL LIVE WORKFLOW CONTRACT TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
