"""End-to-end demo check — full MVP flow from zero DB to verified results.

Usage:
    python scripts/e2e_demo_check.py                          # pipeline + mock
    python scripts/e2e_demo_check.py --runtime agent_graph     # agent_graph + mock
    python scripts/e2e_demo_check.py --mode mock              # mock (default)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ── Argument parsing ─────────────────────────────────────────────────
_args = sys.argv[1:]
_RUNTIME = "pipeline"
_MODE = "mock"

i = 0
while i < len(_args):
    if _args[i] == "--runtime" and i + 1 < len(_args):
        _RUNTIME = _args[i + 1]; i += 2
    elif _args[i] == "--mode" and i + 1 < len(_args):
        _MODE = _args[i + 1]; i += 2
    else:
        i += 1

if _RUNTIME not in ("pipeline", "agent_graph"):
    _RUNTIME = "pipeline"
if _MODE not in ("mock", "openai", "ollama"):
    _MODE = "mock"

# ── Temp DB isolation ────────────────────────────────────────────────
_E2E_DB = _PROJECT_ROOT / "data" / "e2e_test.db"
import small_shop_agent.core.config as _cfg
# multi_agent is the only runtime now
_cfg.DB_PATH = _E2E_DB  # isolate from production DB

from loguru import logger

from small_shop_agent.storage.database import execute_migrations, get_connection

_t_total = time.time()
logger.info(f"=== 步骤 0：初始化数据库 (运行时={_RUNTIME}, 模式={_MODE}) ===")
execute_migrations()

from small_shop_agent.services.review_service import ReviewService
from small_shop_agent.services.workflow_service import WorkflowService
from small_shop_agent.services.reply_service import ReplyService
from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.storage.repositories.reply_repository import ReplyRepository

rs = ReviewService()
ws = WorkflowService()
reply_svc = ReplyService()
eval_svc = EvalService()
rpr = ReplyRepository()

passed = 0
failed = 0
_failures: list[str] = []


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        logger.success(f"  通过: {label}")
    else:
        failed += 1
        _failures.append(f"{label}: {detail}" if detail else label)
        logger.error(f"  失败: {label} — {detail}")


def _step_time(t_start: float) -> str:
    return f"({int((time.time() - t_start) * 1000)}ms)"


# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Upload CSV (create_batch)
# ═══════════════════════════════════════════════════════════════════════════
_t1 = time.time()
logger.info("=== 步骤 1：创建批次（上传 CSV）===")
csv_path = _SRC_DIR / "small_shop_agent" / "demo" / "sample_reviews.csv"
result = rs.create_batch(str(csv_path), store_type="coffee_shop", file_name="sample_reviews.csv")
check("创建批次成功", result["success"] is True, str(result))
batch_id = result["batch_id"]
check("batch_id 已返回", bool(batch_id))
check("total_rows=15", result["validation"]["total_rows"] == 15)
check("valid_review_count=13", result["validation"]["valid_review_count"] == 13)
check("duplicate_count=1", result["validation"]["duplicate_count"] == 1)
check("empty_review_count=1", result["validation"]["empty_review_count"] == 1)

with get_connection() as conn:
    batch = conn.execute(
        "SELECT * FROM review_batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()
    check("review_batches 表有记录", batch is not None)
    check("批次状态=analyzed", batch["status"] == "analyzed")
    review_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("reviews table: 15 rows", review_count == 15, f"count={review_count}")
    valid_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ? AND is_valid = 1",
        (batch_id,),
    ).fetchone()["cnt"]
    check("reviews table: 13 valid", valid_count == 13)
logger.info(f"  步骤 1 完成 {_step_time(_t1)}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Run analysis
# ═══════════════════════════════════════════════════════════════════════════
_t2 = time.time()
logger.info(f"=== 步骤 2：运行分析 (运行时={_RUNTIME}, 模式={_MODE}) ===")
llm_mode = _MODE if _MODE != "mock" else "demo"
if _RUNTIME == "agent_graph":
    from small_shop_agent.agent_runtime.runner import run_with_agent_runtime
    agent_state = run_with_agent_runtime(batch_id, mode=llm_mode)
    errs = agent_state.get("errors", [])
    rv_count = len(agent_state.get("reviews", []))
    wf = {
        "success": len(errs) == 0,
        "batch_id": batch_id, "mode": llm_mode,
        "summary": {
            "review_count": rv_count,
            "negative_count": agent_state.get("_negative_count", 0),
            "insight_count": agent_state.get("_insight_count", 0),
            "draft_count": agent_state.get("_draft_count", 0),
            "blocked_count": agent_state.get("_blocked_count", 0),
            "evidence_count": agent_state.get("_evidence_count", 0),
            "pass_count": agent_state.get("_pass_count", 0),
            "trace_count": 9,
        },
        "error": errs[0]["message"] if errs else None,
    }
else:
    wf = ws.run_analysis(batch_id, mode=llm_mode)
check("工作流执行成功", wf["success"] is True, str(wf))
check("review_count=13", wf["summary"]["review_count"] == 13)
check("insight_count=3", wf["summary"]["insight_count"] == 3)
check("draft_count=5", wf["summary"]["draft_count"] == 5)
check("blocked_count=1", wf["summary"]["blocked_count"] == 1)
check("evidence_count=5", wf["summary"]["evidence_count"] == 5)
logger.info(f"  步骤 2 完成 {_step_time(_t2)}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Verify Dashboard-required data
# ═══════════════════════════════════════════════════════════════════════════
_t3 = time.time()
logger.info("=== 步骤 3：验证看板数据 ===")
with get_connection() as conn:
    analysis_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("review_analysis: 13 rows", analysis_cnt == 13, f"count={analysis_cnt}")

    insights = conn.execute(
        "SELECT * FROM insights WHERE batch_id = ? ORDER BY rank", (batch_id,)
    ).fetchall()
    check("insights: 3 rows", len(insights) == 3)
    check("rank1=hygiene", insights[0]["topic"] == "hygiene")
    check("insights have issue_summary", all(bool(i["issue_summary"]) for i in insights))

    evidence_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM insight_evidence WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    check("insight_evidence: 5 rows", evidence_cnt == 5)

    drafts = conn.execute(
        "SELECT * FROM reply_drafts WHERE batch_id = ?", (batch_id,)
    ).fetchall()
    check("reply_drafts: 5 rows", len(drafts) == 5)
    safety_set = {d["safety_status"] for d in drafts}
    check("drafts: has pass", "pass" in safety_set)
    check("drafts: has rewrite_required", "rewrite_required" in safety_set)
    check("drafts: has blocked", "blocked" in safety_set)

    trace_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM traces WHERE batch_id = ?", (batch_id,)
    ).fetchone()["cnt"]
    _exp_trace_steps = 10 if _RUNTIME == "agent_graph" else 9
    check(f"traces: {_exp_trace_steps} steps", trace_cnt == _exp_trace_steps, f"count={trace_cnt}")

    neg_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ? AND is_negative_candidate = 1",
        (batch_id,),
    ).fetchone()["cnt"]
    check("negative candidates: 5", neg_cnt == 5, f"count={neg_cnt}")

    pending_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM reply_drafts WHERE batch_id = ? AND approval_status = 'pending'",
        (batch_id,),
    ).fetchone()["cnt"]
    check("pending drafts: 4", pending_cnt == 4, f"count={pending_cnt}")
logger.info(f"  步骤 3 完成 {_step_time(_t3)}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Approve & edit drafts
# ═══════════════════════════════════════════════════════════════════════════
_t4 = time.time()
logger.info("=== 步骤 4：审批与编辑 ===")
coff04 = rpr.get_draft_by_review(batch_id, "COFF04")
check("COFF04 draft exists", coff04 is not None)
apr = reply_svc.approve_draft(coff04["id"])
check("审批成功", apr["success"] is True)
check("approve status=approved", apr["draft"]["approval_status"] == "approved")

logger.info("    测试：已拦截草稿无法审批")
coff08 = rpr.get_draft_by_review(batch_id, "COFF08")
check("COFF08 draft exists", coff08 is not None)
check("COFF08 safety_status=blocked", coff08["safety_status"] == "blocked")
apr_blocked = reply_svc.approve_draft(coff08["id"])
check("blocked draft approve fails", apr_blocked["success"] is False)
check("blocked approve error message", "Cannot approve" in apr_blocked.get("error", ""))

logger.info("    测试：编辑记录 before/after 文本")
coff06 = rpr.get_draft_by_review(batch_id, "COFF06")
check("COFF06 draft exists", coff06 is not None)
original_coff06_text = coff06["draft_text"]
new_text = "非常抱歉让您有不愉快的体验，我们已经着手改进服务流程，感谢您的反馈。"
edit_result = reply_svc.edit_draft(coff06["id"], new_text)
check("编辑成功", edit_result["success"] is True)
check("edit status=edited", edit_result["draft"]["approval_status"] == "edited")

with get_connection() as conn:
    actions = conn.execute(
        "SELECT * FROM approval_actions WHERE batch_id = ? ORDER BY id",
        (batch_id,),
    ).fetchall()
    action_types = {a["action"] for a in actions}
    check("has approve action", "approve" in action_types)
    check("has edit action", "edit" in action_types)
    edit_actions = [a for a in actions if a["action"] == "edit"]
    check("edit records before_text", edit_actions[0]["before_text"] == original_coff06_text)
    check("edit records after_text", edit_actions[0]["after_text"] == new_text)
logger.info(f"  步骤 4 完成 {_step_time(_t4)}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Run eval
# ═══════════════════════════════════════════════════════════════════════════
_t5 = time.time()
logger.info("=== 步骤 5：运行评测 ===")
eval_result = eval_svc.run_eval({"batch_id": batch_id})
check("评测执行成功", eval_result["success"] is True, str(eval_result))
check("eval has eval_run_id", bool(eval_result.get("eval_run_id")))
check("topic_accuracy >= 0", eval_result["report"]["topic_accuracy"] >= 0)
check("sentiment_accuracy >= 0", eval_result["report"]["sentiment_accuracy"] >= 0)
check("unsafe_reply_count > 0", eval_result["report"]["unsafe_reply_count"] > 0)
check("total_eval_cases > 0", eval_result["report"]["total_eval_cases"] > 0)
logger.info(f"  步骤 5 完成 {_step_time(_t5)}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 6: Final 11-table verification
# ═══════════════════════════════════════════════════════════════════════════
_t6 = time.time()
logger.info("=== 步骤 6：11 表完整性验证 ===")
with get_connection() as conn:
    tables = {
        "review_batches": "SELECT COUNT(*) as cnt FROM review_batches WHERE batch_id = ?",
        "reviews": "SELECT COUNT(*) as cnt FROM reviews WHERE batch_id = ?",
        "review_analysis": "SELECT COUNT(*) as cnt FROM review_analysis WHERE batch_id = ?",
        "insights": "SELECT COUNT(*) as cnt FROM insights WHERE batch_id = ?",
        "insight_evidence": "SELECT COUNT(*) as cnt FROM insight_evidence WHERE batch_id = ?",
        "reply_drafts": "SELECT COUNT(*) as cnt FROM reply_drafts WHERE batch_id = ?",
        "approval_actions": "SELECT COUNT(*) as cnt FROM approval_actions WHERE batch_id = ?",
        "traces": "SELECT COUNT(*) as cnt FROM traces WHERE batch_id = ?",
        "eval_results": "SELECT COUNT(*) as cnt FROM eval_results WHERE batch_id = ?",
        "memory_sources": "SELECT COUNT(*) as cnt FROM memory_sources WHERE batch_id = ?",
        "agent_memories": "SELECT COUNT(*) as cnt FROM agent_memories WHERE source_id IN (SELECT source_id FROM memory_sources WHERE batch_id = ?)",
    }
    expected = {
        "review_batches": 1, "reviews": 15, "review_analysis": 13,
        "insights": 3, "insight_evidence": 5, "reply_drafts": 5,
        "approval_actions": 2, "traces": 13 if _RUNTIME == "agent_graph" else 12, "eval_results": 1,
        "memory_sources": 3,   # approve COFF04 + edit before + edit after
        "agent_memories": 3,   # approve(COFF04) + before(COFF06) + after(COFF06)
    }
    for table, query in tables.items():
        cnt = conn.execute(query, (batch_id,)).fetchone()["cnt"]
        exp = expected[table]
        check(f"Table '{table}': {cnt} rows (expected {exp})",
              cnt == exp, f"got {cnt}, expected {exp}")
logger.info(f"  步骤 6 完成 {_step_time(_t6)}")

# ═══════════════════════════════════════════════════════════════════════════
# Step 7: Cleanup & summary
# ═══════════════════════════════════════════════════════════════════════════
_t7 = time.time()
logger.info("=== 步骤 7：清理 ===")
with get_connection() as conn:
    conn.execute("DELETE FROM agent_memories WHERE source_id IN (SELECT source_id FROM memory_sources WHERE batch_id = ?)", (batch_id,))
    conn.execute("DELETE FROM memory_sources WHERE batch_id = ?", (batch_id,))
    for tbl in ["approval_actions", "insight_evidence", "reply_drafts",
                "review_analysis", "insights", "traces", "eval_results",
                "reviews", "review_batches"]:
        conn.execute(f"DELETE FROM {tbl} WHERE batch_id = ?", (batch_id,))
    conn.commit()
logger.success("清理完成")

# Delete temp DB
try:
    _E2E_DB.unlink(missing_ok=True)
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════════════
_total_elapsed = int((time.time() - _t_total) * 1000)
logger.info(f"\n{'='*50}")
logger.info(f"E2E 演示验收：通过 {passed}, 失败 {failed} | 总耗时={_total_elapsed}ms")
if _failures:
    for f in _failures:
        logger.error(f"  ✗ {f}")
if failed == 0:
    logger.success("E2E 演示验收通过 — MVP 就绪")
else:
    logger.error(f"E2E 演示验收失败 — {failed} 项未通过")
    sys.exit(1)
