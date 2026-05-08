"""Smoke test for Safety Guardrails — covers all 7 mandatory scenarios."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from small_shop_agent.harness.safety.safety_guardrails import (
    SafetyCheckResult,
    check_reply_safety,
    check_many_replies,
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


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: 正常真诚道歉回复 → pass
# ═══════════════════════════════════════════════════════════════════════════
print("=== Test 1: 正常真诚道歉 → pass ===")
r = check_reply_safety(
    "您好，非常抱歉给您带来了不好的体验。我们会加强员工培训，努力改进服务质量。欢迎您再次光临。"
)
check("status=pass", r.status == "pass", f"got {r.status}")
check("risk_flags empty", r.risk_flags == [])
check("reasons non-empty", len(r.reasons) > 0)
check("original_reply preserved", r.original_reply is not None)

r2 = check_reply_safety(
    "感谢您的反馈，我们已经注意到您提到的问题，会认真改进。"
)
check("status=pass (2)", r2.status == "pass")

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: 包含「已经开除/处罚员工」→ blocked
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 2: 已开除/处罚员工 → blocked ===")
r = check_reply_safety(
    "我们已经开除了相关员工，并对店长进行了罚款处理。"
)
check("status=blocked", r.status == "blocked", f"got {r.status}")
check("has claim_employee_punished", "claim_employee_punished" in r.risk_flags)

r2 = check_reply_safety(
    "该服务员已被辞退，请您放心。"
)
check("status=blocked (2)", r2.status == "blocked")

r3 = check_reply_safety(
    "The employee has been fired and the manager was dismissed."
)
check("status=blocked (3 EN)", r3.status == "blocked")

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: 包含「免费赔偿/全额赔付」→ rewrite_required
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 3: 赔偿承诺 → rewrite_required ===")
r = check_reply_safety(
    "我们愿意给您全额退款，并额外提供现金赔偿。"
)
check("status=rewrite_required", r.status == "rewrite_required", f"got {r.status}")
check("has unfounded_compensation", "unfounded_compensation" in r.risk_flags)

r2 = check_reply_safety(
    "We will give you a full refund and compensate you with cash."
)
check("status=rewrite_required (EN)", r2.status == "rewrite_required")

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: 言语攻击顾客 → blocked
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 4: 攻击顾客 → blocked ===")
r = check_reply_safety(
    "你这种人就是活该，无理取闹！"
)
check("status=blocked", r.status == "blocked", f"got {r.status}")
check("has attack_customer", "attack_customer" in r.risk_flags)

r2 = check_reply_safety(
    "You are stupid and this is your problem."
)
check("status=blocked (EN)", r2.status == "blocked")

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: 过度营销推销话术 → rewrite_required
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 5: 过度营销 → rewrite_required ===")
r = check_reply_safety(
    "感谢您的反馈！顺便告诉您，我们下周有新品上市和限时优惠活动，欢迎扫码关注公众号了解更多。"
)
check("status=rewrite_required", r.status == "rewrite_required", f"got {r.status}")
check("has over_marketing", "over_marketing" in r.risk_flags)

r2 = check_reply_safety(
    "Join our membership now and get limited time offers!"
)
check("status=rewrite_required (EN)", r2.status == "rewrite_required")

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: 空回复内容 → blocked
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 6: 空回复 → blocked ===")
r = check_reply_safety("")
check("empty string blocked", r.status == "blocked")
check("risk_flag=empty_reply", "empty_reply" in r.risk_flags)

r2 = check_reply_safety("   ")
check("whitespace-only blocked", r2.status == "blocked")

r3 = check_reply_safety(None)  # type: ignore
check("None blocked", r3.status == "blocked")

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: check_many_replies 批量校验
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 7: check_many_replies ===")
drafts = [
    {
        "review_id": "R01",
        "original_review": "咖啡太淡了",
        "draft_text": "您好，非常抱歉，我们会调整配方。",
        "approval_status": "pending",
    },
    {
        "review_id": "R02",
        "original_review": "服务员态度很差",
        "draft_text": "我们已经开除了那个服务员。",
        "approval_status": "pending",
    },
    {
        "review_id": "R03",
        "original_review": "等了半小时",
        "draft_text": "我们给您全额退款并赔偿。",
        "approval_status": "pending",
    },
    {
        "review_id": "R04",
        "original_review": "环境不错",
        "draft_text": "",
        "approval_status": "pending",
    },
]
results = check_many_replies(drafts)

check("returns 4 items", len(results) == 4)
check("R01 preserved review_id", results[0]["review_id"] == "R01")
check("R01 preserved original_review", results[0]["original_review"] == "咖啡太淡了")
check("R01 preserved approval_status=pending", results[0]["approval_status"] == "pending")
check("R01 safety_status=pass", results[0]["safety_status"] == "pass")
check("R01 has risk_types", isinstance(results[0]["risk_types"], list))
check("R01 has safety_reason", bool(results[0].get("safety_reason")))

check("R02 safety_status=blocked", results[1]["safety_status"] == "blocked",
      f"got {results[1]['safety_status']}")
check("R02 approval_status=blocked", results[1]["approval_status"] == "blocked",
      f"got {results[1]['approval_status']}")
check("R02 has risk_types", len(results[1]["risk_types"]) > 0)

check("R03 safety_status=rewrite_required", results[2]["safety_status"] == "rewrite_required")
check("R03 approval_status=unchanged", results[2]["approval_status"] == "pending")

check("R04 safety_status=blocked (empty)", results[3]["safety_status"] == "blocked")
check("R04 approval_status=blocked", results[3]["approval_status"] == "blocked")

# Verify all original fields preserved (except approval_status which guard may override)
_blocked_ids = {r["review_id"] for r in results if r["safety_status"] == "blocked"}
for i, orig in enumerate(drafts):
    for k in orig:
        if k == "approval_status" and orig["review_id"] in _blocked_ids:
            continue  # guard intentionally sets blocked → approval_status="blocked"
        check(f"draft[{i}] preserved '{k}'", results[i][k] == orig[k],
              f"expected {orig[k]!r}, got {results[i][k]!r}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: 推卸责任 → rewrite_required
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 8: 推卸责任 → rewrite_required ===")
r = check_reply_safety("是您自己没有看清楚菜单，不是我们的问题。")
check("status=rewrite_required", r.status == "rewrite_required")
check("has defensive_or_blame_shift", "defensive_or_blame_shift" in r.risk_flags)

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: 编造事实 → blocked
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 9: 编造事实 → blocked ===")
r = check_reply_safety("我们已经查明，监控录像显示是您自己不小心碰倒的。")
check("status=blocked", r.status == "blocked")
check("has fabricated_fact", "fabricated_fact" in r.risk_flags)

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: 泄露隐私 → blocked
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 10: 泄露隐私 → blocked ===")
r = check_reply_safety("我们已经记录，您的电话是138xxxx1234，地址是北京市朝阳区。")
check("status=blocked", r.status == "blocked")
check("has disclose_privacy", "disclose_privacy" in r.risk_flags)

# ═══════════════════════════════════════════════════════════════════════════
# Test 11: SafetyCheckResult dataclass defaults
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 11: SafetyCheckResult defaults ===")
d = SafetyCheckResult()
check("default status=pass", d.status == "pass")
check("default risk_flags=[]", d.risk_flags == [])
check("default reasons=[]", d.reasons == [])
check("default safe_reply=None", d.safe_reply is None)
check("default original_reply=None", d.original_reply is None)

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL SAFETY GUARDRAILS SMOKE TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
