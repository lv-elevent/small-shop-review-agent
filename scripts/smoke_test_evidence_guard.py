"""Smoke test for Evidence Guard — validates insight evidence binding rules."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from small_shop_agent.harness.evidence.evidence_guard import (
    EvidenceGuardIssueResult,
    EvidenceGuardResult,
    validate_insight_evidence,
)

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


# ── Shared fixtures ──

REVIEWS = [
    {"review_id": "COFF01", "review_text": "环境好"},
    {"review_id": "COFF02", "review_text": "牛角包不错"},
    {"review_id": "COFF04", "review_text": "等了太久"},
    {"review_id": "COFF08", "review_text": "咖啡里有异物"},
    {"review_id": "COFF13", "review_text": "地板油腻腻的"},
]

# insight with evidence as list of dicts (mock_provider shape)
INSIGHT_EVIDENCE_DICTS = [
    {
        "rank": 1,
        "topic": "hygiene",
        "issue_name": "卫生状况堪忧",
        "evidence": [
            {"review_id": "COFF08", "evidence_text": "咖啡里有异物！"},
            {"review_id": "COFF13", "evidence_text": "地板油腻腻的"},
        ],
    },
]

# insight with evidence_review_ids as flat list
INSIGHT_EVIDENCE_LIST = [
    {
        "insight_id": "101",
        "topic": "waiting_time",
        "evidence_review_ids": ["COFF04", "COFF01"],
    },
]

# insight with review_ids variant
INSIGHT_REVIEW_IDS = [
    {
        "id": "201",
        "topic": "service",
        "review_ids": ["COFF02", "COFF04"],
    },
]

# insight with single evidence (insufficient)
INSIGHT_SINGLE = [
    {
        "rank": 2,
        "topic": "service",
        "evidence_review_ids": ["COFF04"],
    },
]

# insight with non-existent review_ids
INSIGHT_BAD_IDS = [
    {
        "rank": 3,
        "topic": "price",
        "evidence_review_ids": ["NONEXISTENT", "FAKE001"],
    },
]

# insight with no evidence field at all
INSIGHT_NO_EV = [
    {
        "rank": 4,
        "topic": "environment",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: >=2 valid evidence → ok=True (evidence as list of dicts)
# ═══════════════════════════════════════════════════════════════════════════
print("=== Test 1: sufficient evidence (dict list) ===")
r = validate_insight_evidence(INSIGHT_EVIDENCE_DICTS, REVIEWS)
check("ok=True", r.ok)
check("1 valid_issue", len(r.valid_issues) == 1)
check("0 rejected", len(r.rejected_issues) == 0)
check("1 issue result", len(r.issues) == 1)
ir = r.issues[0]
check("status=sufficient", ir.status == "sufficient")
check("has both COFF08 and COFF13", set(ir.evidence_review_ids) == {"COFF08", "COFF13"})
check("no missing", ir.missing_review_ids == [])
check("topic=hygiene", ir.topic == "hygiene")
check("issue_id from rank", ir.issue_id == "1")
# Verify normalized output
v = r.valid_issues[0]
check("normalized: has evidence_review_ids", isinstance(v["evidence_review_ids"], list))
check("normalized: evidence_status=sufficient", v["evidence_status"] == "sufficient")
check("normalized: old evidence key removed", "evidence" not in v)

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: evidence_review_ids flat list format
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 2: evidence_review_ids flat list ===")
r = validate_insight_evidence(INSIGHT_EVIDENCE_LIST, REVIEWS)
check("ok=True", r.ok)
check("1 valid", len(r.valid_issues) == 1)
ir = r.issues[0]
check("status=sufficient", ir.status == "sufficient")
check("issue_id from insight_id", ir.issue_id == "101")

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: review_ids variant
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 3: review_ids variant ===")
r = validate_insight_evidence(INSIGHT_REVIEW_IDS, REVIEWS)
check("ok=True", r.ok)
check("issue_id from id", r.issues[0].issue_id == "201")
check("normalized: review_ids removed", "review_ids" not in r.valid_issues[0])

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: single evidence → evidence_insufficient
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 4: insufficient evidence ===")
r = validate_insight_evidence(INSIGHT_SINGLE, REVIEWS)
check("ok=False", r.ok is False)
check("0 valid", len(r.valid_issues) == 0)
check("1 rejected", len(r.rejected_issues) == 1)
ir = r.issues[0]
check("status=evidence_insufficient", ir.status == "evidence_insufficient")
check("has COFF04", ir.evidence_review_ids == ["COFF04"])
check("reasons mention need 2", any("需要至少 2" in s or "2 条" in s for s in ir.reasons))
rj = r.rejected_issues[0]
check("rejected: evidence_status=evidence_insufficient", rj["evidence_status"] == "evidence_insufficient")
check("rejected: has evidence_review_ids", rj["evidence_review_ids"] == ["COFF04"])

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: non-existent review_ids → invalid
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 5: non-existent review_ids → invalid ===")
r = validate_insight_evidence(INSIGHT_BAD_IDS, REVIEWS)
check("ok=False", r.ok is False)
check("0 valid", len(r.valid_issues) == 0)
check("1 rejected", len(r.rejected_issues) == 1)
ir = r.issues[0]
check("status=invalid", ir.status == "invalid")
check("no present ids", ir.evidence_review_ids == [])
check("missing both", set(ir.missing_review_ids) == {"NONEXISTENT", "FAKE001"})
rj = r.rejected_issues[0]
check("rejected: evidence_status=invalid", rj["evidence_status"] == "invalid")

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: no evidence field → invalid
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 6: no evidence field → invalid ===")
r = validate_insight_evidence(INSIGHT_NO_EV, REVIEWS)
check("ok=False", r.ok is False)
ir = r.issues[0]
check("status=invalid", ir.status == "invalid", f"got {ir.status}")
check("empty review_ids", ir.evidence_review_ids == [])
check("reason mentions missing evidence", any("未关联" in s or "缺少" in s for s in ir.reasons))

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: mixed batch (1 sufficient + 1 insufficient + 1 invalid)
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 7: mixed batch ===")
mixed = [
    {
        "rank": 1, "topic": "hygiene",
        "evidence": [
            {"review_id": "COFF08"},
            {"review_id": "COFF13"},
            {"review_id": "COFF01"},
        ],
    },
    {
        "rank": 2, "topic": "waiting_time",
        "evidence_review_ids": ["COFF04"],  # only 1
    },
    {
        "rank": 3, "topic": "service",
        "review_ids": ["FAKE123"],  # invalid
    },
]
r = validate_insight_evidence(mixed, REVIEWS, min_evidence_count=2)
check("ok=False", r.ok is False)
check("1 valid", len(r.valid_issues) == 1)
check("2 rejected", len(r.rejected_issues) == 2)
check("3 issue results", len(r.issues) == 3)

check("issue 0: sufficient", r.issues[0].status == "sufficient")
check("issue 1: evidence_insufficient", r.issues[1].status == "evidence_insufficient")
check("issue 2: invalid", r.issues[2].status == "invalid")

v = r.valid_issues[0]
check("valid: hygiene topic", v["topic"] == "hygiene")
check("valid: 3 evidence", len(v["evidence_review_ids"]) == 3)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: configurable min_evidence_count
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 8: min_evidence_count=3 ===")
r = validate_insight_evidence(INSIGHT_EVIDENCE_DICTS, REVIEWS, min_evidence_count=3)
check("now insufficient (need 3, have 2)", r.issues[0].status == "evidence_insufficient")
check("ok=False", r.ok is False)

r2 = validate_insight_evidence(INSIGHT_SINGLE, REVIEWS, min_evidence_count=1)
check("min=1 makes single sufficient", r2.issues[0].status == "sufficient")
check("ok=True", r2.ok is True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: empty inputs
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 9: empty inputs ===")
r = validate_insight_evidence([], REVIEWS)
check("empty insights: ok=False", r.ok is False)
check("empty insights: 0 issues", len(r.issues) == 0)

r2 = validate_insight_evidence(INSIGHT_EVIDENCE_DICTS, [])
check("empty reviews: insights become invalid", r2.issues[0].status == "invalid")

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: EvidenceGuardResult and EvidenceGuardIssueResult defaults
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 10: dataclass defaults ===")
ir = EvidenceGuardIssueResult()
check("default status=invalid", ir.status == "invalid")
check("default topic=''", ir.topic == "")
check("default evidence_review_ids=[]", ir.evidence_review_ids == [])
check("default missing_review_ids=[]", ir.missing_review_ids == [])
check("default reasons=[]", ir.reasons == [])

gr = EvidenceGuardResult()
check("default ok=False", gr.ok is False)
check("default issues=[]", gr.issues == [])
check("default valid_issues=[]", gr.valid_issues == [])
check("default rejected_issues=[]", gr.rejected_issues == [])

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL EVIDENCE GUARD SMOKE TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
