"""Smoke test for LLM Router — validates routing, env-var fallback, and error handling."""
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from small_shop_agent.llm.base import BaseLLMProvider
from small_shop_agent.llm.mock_provider import MockProvider
from small_shop_agent.llm.llm_router import LLMRouterConfig, get_llm_provider

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
    for k in ("LLM_MODE", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"):
        os.environ.pop(k, None)


# ═══════════════════════════════════════════════════════════════════════════
# Test 1: mode="demo" → MockProvider
# ═══════════════════════════════════════════════════════════════════════════
print("=== Test 1: mode='demo' → MockProvider ===")
_clear_env()
p = get_llm_provider("demo")
check("returns BaseLLMProvider", isinstance(p, BaseLLMProvider))
check("is MockProvider", isinstance(p, MockProvider))

# ═══════════════════════════════════════════════════════════════════════════
# Test 2: mode="mock" → MockProvider
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 2: mode='mock' → MockProvider ===")
_clear_env()
p = get_llm_provider("mock")
check("returns MockProvider", isinstance(p, MockProvider))

# ═══════════════════════════════════════════════════════════════════════════
# Test 3: mode=None, no LLM_MODE env → defaults to demo
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 3: mode=None, no env → demo default ===")
_clear_env()
p = get_llm_provider(None)
check("defaults to MockProvider", isinstance(p, MockProvider))

# ═══════════════════════════════════════════════════════════════════════════
# Test 4: mode=None, LLM_MODE=demo in env → MockProvider
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 4: mode=None, LLM_MODE=demo ===")
_clear_env()
os.environ["LLM_MODE"] = "demo"
p = get_llm_provider(None)
check("returns MockProvider", isinstance(p, MockProvider))

# ═══════════════════════════════════════════════════════════════════════════
# Test 5: mode="live" without API key → RuntimeError
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 5: mode='live' no API key → RuntimeError ===")
_clear_env()
try:
    get_llm_provider("live")
    check("should have raised", False, "no exception raised")
except RuntimeError as exc:
    msg = str(exc)
    check("is RuntimeError", True)
    check("mentions OPENAI_API_KEY", "OPENAI_API_KEY" in msg)
except Exception as exc:
    check("should be RuntimeError", False, f"got {type(exc).__name__}: {exc}")

# ═══════════════════════════════════════════════════════════════════════════
# Test 6: mode="openai" without API key → RuntimeError
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 6: mode='openai' no API key → RuntimeError ===")
_clear_env()
try:
    get_llm_provider("openai")
    check("should have raised", False, "no exception raised")
except RuntimeError as exc:
    check("mentions OPENAI_API_KEY", "OPENAI_API_KEY" in str(exc))

# ═══════════════════════════════════════════════════════════════════════════
# Test 7: mode="ollama" → NotImplementedError
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 7: mode='ollama' → NotImplementedError ===")
_clear_env()
try:
    get_llm_provider("ollama")
    check("should have raised", False, "no exception raised")
except NotImplementedError as exc:
    msg = str(exc)
    check("mentions Ollama", "Ollama" in msg or "ollama" in msg.lower())
    check("mentions v0.6", "v0.6" in msg)

# ═══════════════════════════════════════════════════════════════════════════
# Test 8: unknown mode → ValueError
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 8: unknown mode → ValueError ===")
_clear_env()
try:
    get_llm_provider("gpt5")
    check("should have raised", False, "no exception raised")
except ValueError as exc:
    msg = str(exc)
    check("mentions unknown", "Unknown" in msg or "unknown" in msg.lower())
    check("mentions supported modes", "Supported" in msg or "demo" in msg)

# ═══════════════════════════════════════════════════════════════════════════
# Test 9: case insensitivity
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 9: case insensitivity ===")
_clear_env()
p1 = get_llm_provider("DEMO")
check("DEMO → MockProvider", isinstance(p1, MockProvider))
p2 = get_llm_provider("Demo")
check("Demo → MockProvider", isinstance(p2, MockProvider))

try:
    get_llm_provider("OLLAMA")
    check("OLLAMA should raise", False, "no exception")
except NotImplementedError:
    check("OLLAMA → NotImplementedError", True)

# ═══════════════════════════════════════════════════════════════════════════
# Test 10: LLMRouterConfig dataclass
# ═══════════════════════════════════════════════════════════════════════════
print("\n=== Test 10: LLMRouterConfig ===")
cfg = LLMRouterConfig(mode="demo", provider_name="MockProvider")
check("mode=demo", cfg.mode == "demo")
check("provider_name=MockProvider", cfg.provider_name == "MockProvider")
check("model=None by default", cfg.model is None)
check("base_url=None by default", cfg.base_url is None)

cfg2 = LLMRouterConfig(mode="live", provider_name="OpenAIProvider", model="gpt-4o", base_url="https://api.example.com")
check("custom model", cfg2.model == "gpt-4o")
check("custom base_url", cfg2.base_url == "https://api.example.com")

# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL LLM ROUTER SMOKE TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
