"""Smoke test for OpenAI Provider — contract validation, no real API calls."""
import json
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from small_shop_agent.llm.base import BaseLLMProvider
from small_shop_agent.llm.openai_provider import OpenAIProvider

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


def _clear_env():
    for k in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "OPENAI_TIMEOUT_SECONDS"):
        os.environ.pop(k, None)


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: init with explicit api_key
# ═══════════════════════════════════════════════════════════════════════════
print("=== Test 1: init with explicit api_key ===")
_clear_env()
p = OpenAIProvider(api_key="sk-test-123")
check("is BaseLLMProvider", isinstance(p, BaseLLMProvider))
check("has _api_key", p._api_key == "sk-test-123")
check("default model", p._model == "gpt-4o-mini")
check("default base_url", p._base_url == "https://api.openai.com/v1")

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: init without api_key (no env)
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 2: init without api_key ===")
_clear_env()
p = OpenAIProvider()
check("api_key is empty", p._api_key == "")
check("no crash on init", True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: init reads env vars
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 3: init reads env vars ===")
_clear_env()
os.environ["OPENAI_API_KEY"] = "sk-env-456"
os.environ["OPENAI_MODEL"] = "gpt-4o"
os.environ["OPENAI_BASE_URL"] = "https://custom.api.com/v1"
os.environ["OPENAI_TIMEOUT_SECONDS"] = "60"
p = OpenAIProvider()
check("reads OPENAI_API_KEY", p._api_key == "sk-env-456")
check("reads OPENAI_MODEL", p._model == "gpt-4o")
check("reads OPENAI_BASE_URL", p._base_url == "https://custom.api.com/v1")
check("reads OPENAI_TIMEOUT_SECONDS", p._timeout == 60)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: explicit param overrides env
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 4: explicit param overrides env ===")
os.environ["OPENAI_MODEL"] = "gpt-4o"
p = OpenAIProvider(model="gpt-4.1-mini")
check("explicit model wins", p._model == "gpt-4.1-mini")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: _extract_json — raw JSON
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 5: _extract_json — raw JSON ===")
data = OpenAIProvider._extract_json('[{"a": 1}, {"b": 2}]')
check("parses list", isinstance(data, list) and len(data) == 2)
check("item 0 correct", data[0] == {"a": 1})

data2 = OpenAIProvider._extract_json('{"key": "value"}')
check("parses dict", data2 == {"key": "value"})

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: _extract_json — ```json fence
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 6: _extract_json — json fence ===")
fenced = '```json\n[{"x": 1}]\n```'
data = OpenAIProvider._extract_json(fenced)
check("parses fenced JSON", data == [{"x": 1}])

fenced2 = '```\n[{"y": 2}]\n```'
data2 = OpenAIProvider._extract_json(fenced2)
check("parses plain fence", data2 == [{"y": 2}])

# leading/trailing text
messy = 'Here is the result:\n```json\n[{"z": 3}]\n```\nHope that helps.'
data3 = OpenAIProvider._extract_json(messy)
check("extracts from messy text", data3 == [{"z": 3}])

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: _extract_json — invalid JSON
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 7: _extract_json — invalid ===")
try:
    OpenAIProvider._extract_json("not json at all")
    check("should raise", False, "no exception")
except ValueError as exc:
    check("raises ValueError on invalid", True)
    check("message contains hint", "not valid JSON" in str(exc) or "200" in str(exc))

try:
    OpenAIProvider._extract_json("")
    check("empty should raise", False, "no exception")
except ValueError as exc:
    check("raises ValueError on empty", "empty" in str(exc).lower())

try:
    OpenAIProvider._extract_json("```json\nnot valid\n```")
    check("invalid in fence should raise", False, "no exception")
except ValueError:
    check("raises on invalid inside fence", True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: prompt builders contain "JSON only"
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 8: prompt builders contain 'JSON only' ===")
_clear_env()
p = OpenAIProvider(api_key="sk-test")
reviews = [{"review_id": "R01", "rating": 2, "review_text": "太慢了"}]
analyses = [{"review_id": "R01", "is_negative_candidate": True, "primary_topic": "waiting_time"}]
drafts = [{"review_id": "R01", "draft_text": "抱歉。"}]

cp = p._build_classification_prompt(reviews)
check("classification has JSON only", "JSON only" in cp)

sp = p._build_sentiment_prompt(reviews)
check("sentiment has JSON only", "JSON only" in sp)

ip = p._build_insights_prompt(reviews, analyses)
check("insights has JSON only", "JSON only" in ip)

rp = p._build_replies_prompt(reviews, analyses)
check("replies has JSON only", "JSON only" in rp)

sap = p._build_safety_prompt(drafts)
check("safety has JSON only", "JSON only" in sap)

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: all 5 provider methods have correct signature
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 9: method signatures match BaseLLMProvider ===")
check("classify_reviews exists", callable(p.classify_reviews))
check("analyze_sentiment exists", callable(p.analyze_sentiment))
check("generate_insights exists", callable(p.generate_insights))
check("draft_replies exists", callable(p.draft_replies))
check("check_safety exists", callable(p.check_safety))

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: methods can be monkeypatched to return mock data
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 10: monkeypatch _call_json_model → methods work ===")
mock_classification = [
    {"review_id": "R01", "topics": ["service"], "primary_topic": "service", "topic_confidence": 0.9, "needs_review": False},
]
mock_sentiment = [
    {"review_id": "R01", "sentiment": "negative", "severity": 4, "sentiment_confidence": 0.92, "is_negative_candidate": True, "analysis_reason": "差评"},
]
mock_insights = [
    {"rank": 1, "issue_name": "测试问题", "issue_summary": "summary", "topic": "service", "mention_count": 1, "severity_level": "high", "priority_score": 0.9, "suggested_action": "改进", "evidence_count": 1, "evidence_status": "sufficient", "evidence": [{"review_id": "R01", "evidence_text": "text", "evidence_reason": "reason"}]},
]
mock_replies = [
    {"review_id": "R01", "original_review": "太慢了", "draft_text": "抱歉。", "approval_status": "pending"},
]
mock_safety = [
    {"review_id": "R01", "safety_status": "pass", "risk_types": [], "safety_reason": "OK"},
]

original = p._call_json_model
def fake_call(**kwargs):
    step = kwargs.get("step_name", "")
    if step == "classification": return mock_classification
    if step == "sentiment_analysis": return mock_sentiment
    if step == "insight_generation": return mock_insights
    if step == "reply_drafting": return mock_replies
    if step == "safety_check": return mock_safety
    return []

p._call_json_model = fake_call  # type: ignore[method-assign]

r1 = p.classify_reviews(reviews)
check("classify returns list", isinstance(r1, list) and len(r1) == 1)
check("classify has review_id", r1[0]["review_id"] == "R01")
check("classify has topics", "topics" in r1[0])

r2 = p.analyze_sentiment(reviews)
check("sentiment returns list", isinstance(r2, list) and len(r2) == 1)
check("sentiment has is_negative_candidate", r2[0]["is_negative_candidate"] is True)

r3 = p.generate_insights(reviews, analyses)
check("insights returns list", isinstance(r3, list) and len(r3) == 1)
check("insights has evidence", "evidence" in r3[0])
check("evidence is list", isinstance(r3[0]["evidence"], list))

r4 = p.draft_replies(reviews, analyses)
check("replies returns list", isinstance(r4, list) and len(r4) == 1)
check("replies has draft_text", "draft_text" in r4[0])

r5 = p.check_safety(drafts)
check("safety returns list", isinstance(r5, list) and len(r5) == 1)
check("safety has safety_status", "safety_status" in r5[0])

# restore
p._call_json_model = original  # type: ignore[method-assign]

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL OPENAI PROVIDER CONTRACT TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
