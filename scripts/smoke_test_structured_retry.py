"""Smoke test for Structured Retry — validates retry/fallback logic without real LLM."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from pydantic import BaseModel

from small_shop_agent.harness.output.structured_retry import (
    StructuredRetryResult,
    run_with_schema_retry,
)

# ── Local test model ──

class ReplyDraft(BaseModel):
    review_id: str
    original_review: str
    draft_text: str
    safety_status: str = "pending"


VALID_DRAFT = {
    "review_id": "R01",
    "original_review": "太慢了",
    "draft_text": "非常抱歉给您带来不便。",
}
VALID_DRAFT_2 = {
    "review_id": "R02",
    "original_review": "态度差",
    "draft_text": "感谢您的反馈，我们会改进。",
}
INVALID_DRAFT = {"review_id": "bad"}  # missing required fields
FALLBACK_DRAFT = {
    "review_id": "FB01",
    "original_review": "fallback",
    "draft_text": "感谢反馈，我们会认真处理。",
}

# ── Helpers ──

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


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: call_fn succeeds on first attempt
# ═══════════════════════════════════════════════════════════════════════════
print("=== Test 1: first attempt succeeds ===")

def succeed_first(attempt: int):
    return VALID_DRAFT

r = run_with_schema_retry(succeed_first, ReplyDraft, many=False)
check("ok is True", r.ok)
check("attempts=1", r.attempts == 1)
check("used_fallback=False", r.used_fallback is False)
check("data is ReplyDraft", isinstance(r.data, ReplyDraft))
check("data.review_id=R01", r.data.review_id == "R01")
check("errors empty", len(r.errors) == 0)
check("schema_name=ReplyDraft", r.schema_name == "ReplyDraft")

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: first attempt fails schema, retry succeeds
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 2: retry succeeds ===")

call_count = 0

def flaky_once(attempt: int):
    global call_count
    call_count = attempt
    if attempt == 1:
        return INVALID_DRAFT
    return VALID_DRAFT

r = run_with_schema_retry(flaky_once, ReplyDraft, many=False, max_retries=1)
check("ok is True", r.ok)
check("attempts=2", r.attempts == 2, f"got {r.attempts}")
check("used_fallback=False", r.used_fallback is False)
check("data.review_id=R01", r.data.review_id == "R01")
check("errors has 1 entry from attempt 1", len(r.errors) == 1)

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: call_fn raises exception, retry succeeds
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 3: call_fn raises then succeeds ===")

def raises_then_ok(attempt: int):
    if attempt == 1:
        raise RuntimeError("LLM timeout")
    return VALID_DRAFT

r = run_with_schema_retry(raises_then_ok, ReplyDraft, many=False, max_retries=1)
check("ok is True", r.ok)
check("attempts=2", r.attempts == 2)
check("data.review_id=R01", r.data.review_id == "R01")
check("errors has exception message", any("RuntimeError" in e and "LLM timeout" in e for e in r.errors))

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: all attempts fail, fallback succeeds
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 4: all fail, fallback succeeds ===")

def always_invalid(attempt: int):
    return INVALID_DRAFT

def good_fallback():
    return FALLBACK_DRAFT

r = run_with_schema_retry(
    always_invalid, ReplyDraft, many=False, max_retries=1,
    fallback_fn=good_fallback,
)
check("ok is True", r.ok)
check("used_fallback=True", r.used_fallback is True)
check("data.review_id=FB01", r.data.review_id == "FB01")
check("errors has schema failures", len(r.errors) >= 2)

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: all attempts fail, no fallback → ok=False
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 5: all fail, no fallback ===")

r = run_with_schema_retry(always_invalid, ReplyDraft, many=False, max_retries=1)
check("ok is False", r.ok is False)
check("data is None", r.data is None)
check("used_fallback=False", r.used_fallback is False)
check("errors has schema failures", len(r.errors) >= 2)

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: call_fn always raises, fallback also raises → ok=False
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 6: all raise, fallback raises ===")

def always_raises(attempt: int):
    raise RuntimeError("boom")

def bad_fallback():
    raise ValueError("fallback boom")

r = run_with_schema_retry(
    always_raises, ReplyDraft, many=False, max_retries=1,
    fallback_fn=bad_fallback,
)
check("ok is False", r.ok is False)
check("data is None", r.data is None)
check("used_fallback=True", r.used_fallback is True)
check("has RuntimeError", any("RuntimeError" in e for e in r.errors))
check("has ValueError", any("ValueError" in e for e in r.errors))

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: fallback data itself fails schema → ok=False
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 7: fallback output fails schema ===")

def invalid_fallback():
    return {"bad": "data"}

r = run_with_schema_retry(
    always_invalid, ReplyDraft, many=False, max_retries=1,
    fallback_fn=invalid_fallback,
)
check("ok is False", r.ok is False)
check("data is None", r.data is None)
check("used_fallback=True", r.used_fallback is True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: many=True mode
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 8: many=True mode ===")

def return_list(attempt: int):
    return [VALID_DRAFT, VALID_DRAFT_2]

r = run_with_schema_retry(return_list, ReplyDraft, many=True)
check("ok is True", r.ok)
check("data is list", isinstance(r.data, list))
check("data has 2 items", len(r.data) == 2)
check("data[0] is ReplyDraft", isinstance(r.data[0], ReplyDraft))
check("data[1].review_id=R02", r.data[1].review_id == "R02")

# many=True with partial failure → should fail
def return_mixed(attempt: int):
    return [VALID_DRAFT, INVALID_DRAFT]

r2 = run_with_schema_retry(return_mixed, ReplyDraft, many=True)
check("many=True partial fail → ok=False", r2.ok is False)

# many=True fallback
def list_fallback():
    return [VALID_DRAFT]

r3 = run_with_schema_retry(
    return_mixed, ReplyDraft, many=True, max_retries=1,
    fallback_fn=list_fallback,
)
check("many=True fallback succeeds", r3.ok is True)
check("many=True fallback data list", isinstance(r3.data, list) and len(r3.data) == 1)

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: max_retries=0 (only one attempt, no retry)
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 9: max_retries=0 ===")

r = run_with_schema_retry(
    always_invalid, ReplyDraft, many=False, max_retries=0,
    fallback_fn=good_fallback,
)
check("max_retries=0: fallback used", r.used_fallback is True)
check("max_retries=0: fallback success", r.ok is True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: StructuredRetryResult dataclass defaults
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 10: StructuredRetryResult defaults ===")
default = StructuredRetryResult()
check("default ok=False", default.ok is False)
check("default data=None", default.data is None)
check("default attempts=0", default.attempts == 0)
check("default used_fallback=False", default.used_fallback is False)
check("default errors=[]", default.errors == [])
check("default schema_name=''", default.schema_name == "")

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL STRUCTURED RETRY SMOKE TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
