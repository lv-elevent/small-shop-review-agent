"""
Phase 3 smoke test — exercises DemoLoader and MockProvider.
Covers: CSV loading, JSON loading, cross-reference integrity, MockProvider
determinism, safety checks, and full pipeline integration.
"""
import sys
import copy
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from loguru import logger

from small_shop_agent.demo.demo_loader import DemoLoader
from small_shop_agent.llm.mock_provider import MockProvider

loader = DemoLoader()
mock = MockProvider(loader)

passed = 0
failed = 0

VALID_TOPICS = {"waiting_time", "service", "product", "price", "environment", "hygiene", "location", "other"}
VALID_SENTIMENTS = {"positive", "neutral", "negative"}
VALID_SAFETY = {"pass", "rewrite_required", "blocked"}
VALID_APPROVAL = {"pending", "approved", "edited", "rejected", "blocked"}
VALID_TRACE_STEPS = {
    "input_validation", "data_cleaning", "classification", "sentiment_analysis",
    "issue_aggregation", "evidence_check", "reply_drafting", "safety_check",
    "human_approval", "eval_run",
}
VALID_TRACE_STATUSES = {"passed", "warning", "failed", "pending"}


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        logger.success(f"  PASS: {label}")
    else:
        failed += 1
        logger.error(f"  FAIL: {label} — {detail}")


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: CSV Loading
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 1: CSV Loading ===")
csv_data = loader.load_sample_reviews()

check("returns list", isinstance(csv_data, list))
check("15 rows", len(csv_data) == 15)

# COFF05 duplicate
coff05_rows = [r for r in csv_data if r["review_id"] == "COFF05"]
check("COFF05 appears twice", len(coff05_rows) == 2)

# COFF10 empty
coff10 = [r for r in csv_data if r["review_id"] == "COFF10"]
check("COFF10 exists", len(coff10) == 1)
check("COFF10 review_text is empty", coff10[0]["review_text"].strip() == "")

# Required fields
check("all rows have review_id", all("review_id" in r for r in csv_data))
check("all rows have rating", all("rating" in r for r in csv_data))
check("all ratings parse as int", all(r["rating"].isdigit() for r in csv_data))
check("all ratings in 1-5", all(1 <= int(r["rating"]) <= 5 for r in csv_data))
check("all rows have platform", all("platform" in r for r in csv_data))

# Platform diversity
platforms = {r["platform"] for r in csv_data}
check("has 美团", "美团" in platforms)
check("has 大众点评", "大众点评" in platforms)
check("has 小红书", "小红书" in platforms)

# Date field
check("all rows have date", all("date" in r for r in csv_data))

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: JSON Loading & Cross-Reference Integrity
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 2: JSON Loading & Cross-Reference ===")

# Build set of valid review_ids from CSV (non-empty, unique)
csv_ids: set[str] = set()
for r in csv_data:
    rid = r["review_id"]
    if r["review_text"].strip():
        csv_ids.add(rid)
# csv_ids should have 13 unique IDs (COFF01-14 minus COFF10, minus duplicate COFF05 counted once)
check("13 valid unique CSV IDs", len(csv_ids) == 13)

# Classification
cls_data = loader.load_mock_classification()
check("classification is list", isinstance(cls_data, list))
check("classification has 13 entries", len(cls_data) == 13)
cls_ids = {e["review_id"] for e in cls_data}
check("all classification IDs in CSV", cls_ids <= csv_ids)
check("all valid CSV IDs have classification (except COFF10 which is empty)", cls_ids == csv_ids)

for entry in cls_data:
    check(f"cls {entry['review_id']} has topics list", isinstance(entry["topics"], list))
    check(f"cls {entry['review_id']} has primary_topic", entry["primary_topic"] in VALID_TOPICS)
    check(f"cls {entry['review_id']} topic_confidence in 0-1", 0 <= entry["topic_confidence"] <= 1)

# Sentiment
sent_data = loader.load_mock_sentiment()
check("sentiment is list", isinstance(sent_data, list))
check("sentiment has 13 entries", len(sent_data) == 13)
sent_ids = {e["review_id"] for e in sent_data}
check("all sentiment IDs in CSV", sent_ids <= csv_ids)
check("all valid CSV IDs have sentiment", sent_ids == csv_ids)

neg_candidates = [e for e in sent_data if e.get("is_negative_candidate")]
check("5 negative candidates", len(neg_candidates) == 5)
neg_ids = {e["review_id"] for e in neg_candidates}
check("COFF04 is negative", "COFF04" in neg_ids)
check("COFF06 is negative", "COFF06" in neg_ids)
check("COFF08 is negative", "COFF08" in neg_ids)
check("COFF12 is negative", "COFF12" in neg_ids)
check("COFF13 is negative", "COFF13" in neg_ids)

for entry in sent_data:
    check(f"sent {entry['review_id']} sentiment valid", entry["sentiment"] in VALID_SENTIMENTS)
    check(f"sent {entry['review_id']} severity 1-5", 1 <= entry["severity"] <= 5)
    check(f"sent {entry['review_id']} confidence 0-1", 0 <= entry["sentiment_confidence"] <= 1)
    check(f"sent {entry['review_id']} has analysis_reason", isinstance(entry["analysis_reason"], str) and len(entry["analysis_reason"]) > 0)

# Insights
insights = loader.load_mock_insights()
check("insights is list", isinstance(insights, list))
check("insights has 3 entries", len(insights) == 3)
check("ranks are 1,2,3", [i["rank"] for i in insights] == [1, 2, 3])

for ins in insights:
    check(f"insight rank {ins['rank']} has evidence", isinstance(ins.get("evidence"), list))
    check(f"insight rank {ins['rank']} evidence_count > 0", ins["evidence_count"] > 0)
    check(f"insight rank {ins['rank']} evidence matches", ins["evidence_count"] == len(ins["evidence"]))
    check(f"insight rank {ins['rank']} has evidence_status", ins["evidence_status"] in ("sufficient", "insufficient"))
    check(f"insight rank {ins['rank']} has issue_name", isinstance(ins["issue_name"], str) and ins["issue_name"])
    check(f"insight rank {ins['rank']} topic valid", ins["topic"] in VALID_TOPICS)
    check(f"insight rank {ins['rank']} severity_level valid", ins["severity_level"] in ("low", "medium", "high"))
    for ev in ins["evidence"]:
        check(f"insight {ins['rank']} evidence {ev['review_id']} in CSV", ev["review_id"] in csv_ids)

check("rank 1 topic=hygiene", insights[0]["topic"] == "hygiene")
check("rank 2 topic=waiting_time", insights[1]["topic"] == "waiting_time")
check("rank 3 topic=service", insights[2]["topic"] == "service")

# Replies
replies = loader.load_mock_replies()
check("replies is list", isinstance(replies, list))
check("replies has 5 entries", len(replies) == 5)
reply_ids = {e["review_id"] for e in replies}
check("all reply IDs are negative candidates", reply_ids <= neg_ids)
for rp in replies:
    check(f"reply {rp['review_id']} has draft_text", isinstance(rp["draft_text"], str) and rp["draft_text"])
    check(f"reply {rp['review_id']} has original_review", isinstance(rp["original_review"], str) and rp["original_review"])
    check(f"reply {rp['review_id']} approval_status=pending", rp["approval_status"] == "pending")

# Traces
traces = loader.load_mock_trace()
check("traces is list", isinstance(traces, list))
check("traces has 10 entries", len(traces) == 10)
trace_steps_found = {t["step_name"] for t in traces}
check("covers all 10 step names", trace_steps_found == VALID_TRACE_STEPS)
for t in traces:
    check(f"trace {t['step_name']} status valid", t["status"] in VALID_TRACE_STATUSES)

# Batch
batch = loader.load_mock_batch()
check("batch is dict", isinstance(batch, dict))
check("batch_id is batch-demo-001", batch["batch_id"] == "batch-demo-001")
check("store_type is coffee_shop", batch["store_type"] == "coffee_shop")
check("valid_review_count=13", batch["valid_review_count"] == 13)
check("duplicate_count=1", batch["duplicate_count"] == 1)
check("empty_review_count=1", batch["empty_review_count"] == 1)

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: get_demo_payload
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 3: get_demo_payload ===")
payload = loader.get_demo_payload()
check("payload is dict", isinstance(payload, dict))
expected_keys = {"batch", "reviews", "classification", "sentiment", "insights", "replies", "traces"}
check("payload has all 7 keys", set(payload.keys()) == expected_keys)
check("batch is dict", isinstance(payload["batch"], dict))
check("reviews is list", isinstance(payload["reviews"], list) and len(payload["reviews"]) == 15)
check("classification is list", isinstance(payload["classification"], list) and len(payload["classification"]) == 13)
check("sentiment is list", isinstance(payload["sentiment"], list) and len(payload["sentiment"]) == 13)
check("insights is list", isinstance(payload["insights"], list) and len(payload["insights"]) == 3)
check("replies is list", isinstance(payload["replies"], list) and len(payload["replies"]) == 5)
check("traces is list", isinstance(payload["traces"], list) and len(payload["traces"]) == 10)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: MockProvider.classify_reviews
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 4: MockProvider.classify_reviews ===")

# Use reviews from csv_data directly (they have string ratings from CSV)
reviews_in = loader.load_sample_reviews()

cls_result = mock.classify_reviews(reviews_in)
check("returns list", isinstance(cls_result, list))
# 15 rows - 1 empty (COFF10) - 1 duplicate (COFF05 second) = 13
check("13 entries (skip empty + dup)", len(cls_result) == 13)

cls_result_ids = {e["review_id"] for e in cls_result}
check("COFF10 excluded", "COFF10" not in cls_result_ids)
check("COFF05 appears once", sum(1 for e in cls_result if e["review_id"] == "COFF05") == 1)

for entry in cls_result:
    check(f"cls_res {entry['review_id']} in input", entry["review_id"] in csv_ids)
    check(f"cls_res {entry['review_id']} has topics", isinstance(entry["topics"], list))
    check(f"cls_res {entry['review_id']} primary_topic valid", entry["primary_topic"] in VALID_TOPICS)

# Known value check
coff04_cls = next(e for e in cls_result if e["review_id"] == "COFF04")
check("COFF04 primary_topic=waiting_time", coff04_cls["primary_topic"] == "waiting_time")

# Fallback check: create a review with unknown ID
unknown_review = [{"review_id": "UNKNOWN99", "rating": "1", "review_text": "bad stuff", "date": "2026-01-01", "platform": "test"}]
fallback_cls = mock.classify_reviews(unknown_review)
check("unknown ID gets fallback", len(fallback_cls) == 1)
check("fallback topic is waiting_time (rating=1)", fallback_cls[0]["primary_topic"] == "waiting_time")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: MockProvider.analyze_sentiment
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 5: MockProvider.analyze_sentiment ===")

sent_result = mock.analyze_sentiment(reviews_in)
check("returns list", isinstance(sent_result, list))
check("13 entries", len(sent_result) == 13)

sent_result_ids = {e["review_id"] for e in sent_result}
check("COFF10 excluded", "COFF10" not in sent_result_ids)

neg_from_mock = [e for e in sent_result if e.get("is_negative_candidate")]
check("5 negative candidates from mock", len(neg_from_mock) == 5)

# Known values
coff01_sent = next(e for e in sent_result if e["review_id"] == "COFF01")
check("COFF01 sentiment=positive", coff01_sent["sentiment"] == "positive")
check("COFF01 severity=1", coff01_sent["severity"] == 1)

coff14_sent = next(e for e in sent_result if e["review_id"] == "COFF14")
check("COFF14 sentiment=neutral", coff14_sent["sentiment"] == "neutral")

for entry in sent_result:
    check(f"sent_res {entry['review_id']} sentiment valid", entry["sentiment"] in VALID_SENTIMENTS)
    check(f"sent_res {entry['review_id']} severity 1-5", 1 <= entry["severity"] <= 5)

# Fallback check
fallback_sent = mock.analyze_sentiment(unknown_review)
check("unknown ID sentiment fallback negative", fallback_sent[0]["sentiment"] == "negative")
check("unknown ID is_negative_candidate=True", fallback_sent[0]["is_negative_candidate"] is True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: MockProvider.generate_insights
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 6: MockProvider.generate_insights ===")

ins_result = mock.generate_insights(reviews_in, sent_result)
check("returns 3 insights", len(ins_result) == 3)
check("ranks are 1,2,3", [i["rank"] for i in ins_result] == [1, 2, 3])
check("rank 1 hygiene", ins_result[0]["topic"] == "hygiene")
check("rank 2 waiting_time", ins_result[1]["topic"] == "waiting_time")
check("rank 3 service", ins_result[2]["topic"] == "service")

for ins in ins_result:
    check(f"ins {ins['rank']} has evidence list", isinstance(ins.get("evidence"), list) and len(ins["evidence"]) > 0)
    check(f"ins {ins['rank']} evidence_count matches", ins["evidence_count"] == len(ins["evidence"]))
    for ev in ins["evidence"]:
        check(f"ins {ins['rank']} ev {ev['review_id']} in valid IDs", ev["review_id"] in csv_ids)

# Empty input still returns 3 insights (insights are batch-level)
ins_empty = mock.generate_insights([], [])
check("empty input still returns 3", len(ins_empty) == 3)

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: MockProvider.draft_replies
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 7: MockProvider.draft_replies ===")

drafts = mock.draft_replies(reviews_in, sent_result)
check("5 drafts (matching 5 negative candidates)", len(drafts) == 5)

draft_ids = {d["review_id"] for d in drafts}
check("only negative candidates get drafts", draft_ids == neg_ids)

for d in drafts:
    check(f"draft {d['review_id']} has draft_text", isinstance(d["draft_text"], str) and d["draft_text"])
    check(f"draft {d['review_id']} has original_review", isinstance(d["original_review"], str) and d["original_review"])
    check(f"draft {d['review_id']} approval_status=pending", d["approval_status"] == "pending")

# COFF04 original text matches CSV
coff04_draft = next(d for d in drafts if d["review_id"] == "COFF04")
check("COFF04 draft original matches CSV", coff04_draft["original_review"] == "等了太久，而且没有人解释情况。")

# Empty analysis → empty drafts
drafts_empty = mock.draft_replies(reviews_in, [])
check("empty analysis → 0 drafts", len(drafts_empty) == 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: MockProvider.check_safety
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 8: MockProvider.check_safety ===")

safe_results = mock.check_safety(drafts)
check("safety returns same count", len(safe_results) == len(drafts))

for s in safe_results:
    rid = s["review_id"]
    check(f"safety {rid} status valid", s["safety_status"] in VALID_SAFETY)
    check(f"safety {rid} has risk_types", isinstance(s["risk_types"], list))
    check(f"safety {rid} has safety_reason", isinstance(s["safety_reason"], str) and s["safety_reason"])

# COFF04: pass
coff04_safe = next(s for s in safe_results if s["review_id"] == "COFF04")
check("COFF04 safety=pass", coff04_safe["safety_status"] == "pass")
check("COFF04 risk_types empty", coff04_safe["risk_types"] == [])
check("COFF04 approval_status stays pending", coff04_safe["approval_status"] == "pending")

# COFF06: rewrite_required
coff06_safe = next(s for s in safe_results if s["review_id"] == "COFF06")
check("COFF06 safety=rewrite_required", coff06_safe["safety_status"] == "rewrite_required")
check("COFF06 risk_types has over_marketing", "over_marketing" in coff06_safe["risk_types"])
check("COFF06 approval_status stays pending", coff06_safe["approval_status"] == "pending")

# COFF08: blocked
coff08_safe = next(s for s in safe_results if s["review_id"] == "COFF08")
check("COFF08 safety=blocked", coff08_safe["safety_status"] == "blocked")
check("COFF08 approval_status=blocked", coff08_safe["approval_status"] == "blocked")

# COFF12: pass
coff12_safe = next(s for s in safe_results if s["review_id"] == "COFF12")
check("COFF12 safety=pass", coff12_safe["safety_status"] == "pass")

# COFF13: pass
coff13_safe = next(s for s in safe_results if s["review_id"] == "COFF13")
check("COFF13 safety=pass", coff13_safe["safety_status"] == "pass")

# Empty input
safe_empty = mock.check_safety([])
check("empty safety input → empty output", safe_empty == [])

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: Determinism — same input → same output
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 9: Determinism ===")

# classify_reviews x3
cls1 = mock.classify_reviews(reviews_in)
cls2 = mock.classify_reviews(reviews_in)
cls3 = mock.classify_reviews(reviews_in)
check("classify_reviews deterministic (2 runs)", cls1 == cls2 == cls3)

# analyze_sentiment x3
sent1 = mock.analyze_sentiment(reviews_in)
sent2 = mock.analyze_sentiment(reviews_in)
sent3 = mock.analyze_sentiment(reviews_in)
check("analyze_sentiment deterministic (2 runs)", sent1 == sent2 == sent3)

# generate_insights x3
ins1 = mock.generate_insights(reviews_in, sent_result)
ins2 = mock.generate_insights(reviews_in, sent_result)
ins3 = mock.generate_insights(reviews_in, sent_result)
check("generate_insights deterministic (2 runs)", ins1 == ins2 == ins3)

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: Full Pipeline Integration
# ═══════════════════════════════════════════════════════════════════════════
logger.info("=== Test 10: Full Pipeline Integration ===")

payload = loader.get_demo_payload()
reviews = payload["reviews"]

# Run full pipeline: classify → sentiment → insights → replies → safety
pipe_cls = mock.classify_reviews(reviews)
check("pipeline: classify succeeds", len(pipe_cls) == 13)

pipe_sent = mock.analyze_sentiment(reviews)
check("pipeline: sentiment succeeds", len(pipe_sent) == 13)

pipe_ins = mock.generate_insights(reviews, pipe_sent)
check("pipeline: insights succeeds", len(pipe_ins) == 3)

# Merge classification + sentiment for analysis (as workflow would do)
merged_analysis = []
for cls_entry in pipe_cls:
    rid = cls_entry["review_id"]
    sent_entry = next((s for s in pipe_sent if s["review_id"] == rid), None)
    if sent_entry:
        merged_analysis.append({**cls_entry, **sent_entry})
check("pipeline: analysis merged", len(merged_analysis) == 13)

pipe_drafts = mock.draft_replies(reviews, merged_analysis)
check("pipeline: draft_replies succeeds", len(pipe_drafts) == 5)

pipe_safe = mock.check_safety(pipe_drafts)
check("pipeline: check_safety succeeds", len(pipe_safe) == 5)

# Verify safety_status distribution
safety_counts = {"pass": 0, "rewrite_required": 0, "blocked": 0}
for s in pipe_safe:
    safety_counts[s["safety_status"]] += 1
check("safety: 3 pass", safety_counts["pass"] == 3)
check("safety: 1 rewrite_required", safety_counts["rewrite_required"] == 1)
check("safety: 1 blocked", safety_counts["blocked"] == 1)

# Evidence review_ids all reference valid classified review IDs
for ins in pipe_ins:
    for ev in ins["evidence"]:
        check(f"pipeline evidence {ev['review_id']} classifiable", ev["review_id"] in {e["review_id"] for e in pipe_cls})

# No duplicate review_ids in classification or sentiment results
check("pipeline: no dup IDs in classification", len(pipe_cls) == len({e["review_id"] for e in pipe_cls}))
check("pipeline: no dup IDs in sentiment", len(pipe_sent) == len({e["review_id"] for e in pipe_sent}))

# ═══════════════════════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════════════════════
logger.info(f"\n{'='*50}")
logger.info(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    logger.success("ALL DEMO LOADER SMOKE TESTS PASSED")
else:
    logger.error(f"{failed} TEST(S) FAILED")
