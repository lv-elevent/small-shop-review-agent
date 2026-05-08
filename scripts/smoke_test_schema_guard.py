"""Smoke test for Schema Guard — validates output against local Pydantic models."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from pydantic import BaseModel, Field

from small_shop_agent.harness.output.schema_guard import (
    SchemaGuardResult,
    validate_output,
)

# ── Local test models (schemas/ are empty, define here temporarily) ──

class ClassificationResult(BaseModel):
    review_id: str
    topics: list[str]
    primary_topic: str
    topic_confidence: float
    needs_review: bool = False


class SentimentResult(BaseModel):
    review_id: str
    sentiment: str
    severity: int = Field(ge=1, le=5)
    sentiment_confidence: float
    is_negative_candidate: bool = False
    analysis_reason: str = ""


class ReplyDraft(BaseModel):
    review_id: str
    original_review: str
    draft_text: str
    safety_status: str = "pending"
    risk_types: list[str] = Field(default_factory=list)
    approval_status: str = "pending"


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


VALID_CLASSIFICATION = [
    {
        "review_id": "R01",
        "topics": ["service", "waiting_time"],
        "primary_topic": "service",
        "topic_confidence": 0.92,
        "needs_review": False,
    },
    {
        "review_id": "R02",
        "topics": ["hygiene"],
        "primary_topic": "hygiene",
        "topic_confidence": 0.95,
        "needs_review": True,
    },
]

# ═══════════════════════════════════════════════════════════════════════════
# Test 1: many=True — all valid
# ═══════════════════════════════════════════════════════════════════════════
print("=== Test 1: many=True all valid ===")
r = validate_output(VALID_CLASSIFICATION, ClassificationResult, many=True)
check("ok is True", r.ok)
check("total_input=2", r.total_input == 2)
check("total_valid=2", r.total_valid == 2)
check("total_invalid=0", r.total_invalid == 0)
check("validated has 2 items", len(r.validated) == 2)
check("validated[0] is ClassificationResult", isinstance(r.validated[0], ClassificationResult))
check("validated[1] fields correct", r.validated[1].review_id == "R02")
check("errors empty", len(r.errors) == 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: many=True — mixed valid/invalid
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 2: many=True with invalid items ===")
mixed_data = [
    {"review_id": "R01", "topics": ["service"], "primary_topic": "service", "topic_confidence": 0.92},
    {"review_id": "bad"},  # missing topics, primary_topic, topic_confidence
    {"review_id": "R03", "topics": ["hygiene"], "primary_topic": "hygiene", "topic_confidence": "not_a_float"},
]
r = validate_output(mixed_data, ClassificationResult, many=True)
check("ok is False", r.ok is False)
check("total_input=3", r.total_input == 3)
check("total_valid=1", r.total_valid == 1)
check("total_invalid=2", r.total_invalid == 2)
check("validated has 1 item (partial success)", len(r.validated) == 1)
check("errors has 2 items", len(r.errors) == 2)
check("errors[0] has index", "index" in r.errors[0])
check("errors[0] has input", "input" in r.errors[0])
check("errors[0] has error details", isinstance(r.errors[0]["errors"], list) and len(r.errors[0]["errors"]) > 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: many=False — valid single dict
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 3: many=False valid ===")
r = validate_output(VALID_CLASSIFICATION[0], ClassificationResult, many=False)
check("ok is True", r.ok)
check("total_input=1", r.total_input == 1)
check("total_valid=1", r.total_valid == 1)
check("validated has 1 item", len(r.validated) == 1)

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: many=False — invalid
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 4: many=False invalid ===")
r = validate_output({"review_id": "bad"}, ClassificationResult, many=False)
check("ok is False", r.ok is False)
check("total_invalid=1", r.total_invalid == 1)
check("errors has 1 item", len(r.errors) == 1)

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: SentimentResult with field constraints
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 5: field constraints ===")
r = validate_output([{
    "review_id": "R01", "sentiment": "positive", "severity": 99,
    "sentiment_confidence": 0.9,
}], SentimentResult, many=True)
check("severity=99 fails validation", r.ok is False)

r2 = validate_output([{
    "review_id": "R01", "sentiment": "positive", "severity": 5,
    "sentiment_confidence": 0.9,
}], SentimentResult, many=True)
check("severity=5 passes", r2.ok is True)

r3 = validate_output([{
    "review_id": "R01", "sentiment": "positive", "severity": 0,
    "sentiment_confidence": 0.9,
}], SentimentResult, many=True)
check("severity=0 fails (below ge=1)", r3.ok is False)

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: empty list → ok=False
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 6: empty list ===")
r = validate_output([], ClassificationResult, many=True)
check("ok is False", r.ok is False)
check("total_input=0", r.total_input == 0)
check("total_valid=0", r.total_valid == 0)

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: ReplyDraft with optional list field
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 7: ReplyDraft model ===")
drafts = [
    {
        "review_id": "R04", "original_review": "太慢了",
        "draft_text": "非常抱歉给您带来不便。",
    },
    {
        "review_id": "R05", "original_review": "态度差",
        "draft_text": "感谢您的反馈，我们会加强培训。",
        "safety_status": "pass", "risk_types": [], "approval_status": "pending",
    },
]
r = validate_output(drafts, ReplyDraft, many=True)
check("reply drafts all valid", r.ok is True)
check("draft[0] has default safety_status", r.validated[0].safety_status == "pending")
check("draft[0] has default risk_types", r.validated[0].risk_types == [])

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: SchemaGuardResult dataclass fields
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 8: SchemaGuardResult fields ===")
r = validate_output(VALID_CLASSIFICATION, ClassificationResult)
check("has ok", hasattr(r, "ok"))
check("has validated", hasattr(r, "validated"))
check("has errors", hasattr(r, "errors"))
check("has total_input", hasattr(r, "total_input"))
check("has total_valid", hasattr(r, "total_valid"))
check("has total_invalid", hasattr(r, "total_invalid"))

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL SCHEMA GUARD SMOKE TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
