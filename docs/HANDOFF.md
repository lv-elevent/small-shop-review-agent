# 项目交接文档

**项目名称：** Small Shop Review Response & Insight Agent（小店差评处理与问题洞察 Agent）  
**交接日期：** 2026-05-08  
**当前分支：** master  
**当前版本：** 0.5.x（介于 ROADMAP v0.5 和 v1.0 之间）

---

## 一、项目概述

面向小型门店（咖啡店、餐厅等）的本地可演示 Agentic Workflow 系统。核心闭环：上传 CSV → 分类与情绪 → 三大问题 → 回复草稿 → 安全检查 → 人工审批 → Dashboard → Trace/Eval。

**产品原则：** 短链路、可审批、有证据、可演示、Demo Mode 一等公民、不做过度工程。

**技术栈：** Python 3.11+ / Streamlit / SQLite (WAL) / pandas / loguru / Pydantic

**一行启动：**
```bash
pip install -r requirements.txt && python scripts/init_db.py && streamlit run apps/streamlit_app/app.py
```

---

## 二、架构总览

```
apps/streamlit_app/          ← UI 层（4 个页面，全部接入真实服务）
src/small_shop_agent/
  services/                  ← 服务层（7 个 service，✅ 全部实现）
  storage/
    repositories/            ← 数据访问层（7 个 repository，✅ 全部实现）
    migrations/              ← 9 个 SQL 迁移（✅ 全部实现）
  llm/
    mock_provider.py         ← Demo Mode LLM（✅ 实现）
    openai_provider.py       ← Open AI Live 模式（❌ 空壳）
    ollama_provider.py       ← Ollama 本地模型（❌ 空壳）
    llm_router.py            ← LLM 路由（❌ 空壳）
  evals/                     ← 评测（4 scorer + runner，✅ 规则版实现）
  harness/                   ← Harness 模块（仅 input/ 实现，其余空壳）
  agent_runtime/             ← LangGraph 多 Agent（❌ 15 个空壳文件）
  schemas/                   ← Pydantic Schema（❌ 7 个文件未集成）
  domain/                    ← 领域模型（❌ 未集成到服务层）
  observability/             ← 可观测（❌ 6 个文件未集成）
  prompts/                   ← Prompt 模板（❌ 存在但未集成）
scripts/                     ← 12 个 smoke test + e2e（✅ 1,057 项 0 失败）
docs/                        ← 10 个文档（✅）
```

---

## 三、已实现功能清单

### 数据库层（Phase 2）
| 表名 | 用途 | 状态 |
|------|------|------|
| `review_batches` | 上传批次 | ✅ |
| `reviews` | 评论数据（含清洗标记） | ✅ |
| `review_analysis` | 分类 + 情绪结果 | ✅ |
| `insights` | Top 3 问题 | ✅ |
| `insight_evidence` | 问题 → 评论证据关联 | ✅ |
| `reply_drafts` | AI 回复草稿 + 安全状态 | ✅ |
| `approval_actions` | 人工审批动作日志 | ✅ |
| `traces` | 工作流 Trace 日志 | ✅ |
| `eval_results` | 评测结果 | ✅ |

### 服务层（Phase 3-5）
| Service | 主要方法 | 状态 |
|---------|---------|------|
| `ReviewService` | `validate_csv`, `create_batch`, `list_reviews`, `get_review`, `get_batch_summary` | ✅ |
| `WorkflowService` | `run_demo_analysis`, `run_analysis`, `get_workflow_status` | ✅ Demo 完整，Live 不可用 |
| `InsightService` | `get_top_issues`, `get_issue_evidence` | ✅ |
| `ReplyService` | `get_pending_drafts`, `get_draft_detail`, `approve_draft`, `edit_draft`, `reject_draft`, `export_approved_replies` | ✅ |
| `ApprovalService` | `record_approval_action`（thin wrapper） | ✅ |
| `TraceService` | `log_step`, `get_trace`, `get_latest_trace` | ✅ |
| `EvalService` | `run_eval`, `get_latest_eval`, `list_eval_runs` | ✅ 规则版，非 LLM 版 |

### Workflow 流程（Phase 4）
`WorkflowService.run_demo_analysis(batch_id)` 完整实现 8 步流水线：
```
input_validation → data_cleaning → classification → sentiment_analysis
→ issue_aggregation → evidence_check → reply_drafting → safety_check
```
每步写入 trace，含 status / input_summary / output_summary / latency_ms。

### UI 页面（Phase 6-9）
| 页面 | 文件 | 状态 |
|------|------|------|
| 首页 | `app.py` | ✅ 入口 + 导航 |
| 上传评论 | `upload_page.py` | ✅ 接入 ReviewService + WorkflowService |
| 数据看板 | `dashboard_page.py` | ✅ 接入 InsightService / ReplyService / TraceService / EvalService |
| 回复审核 | `reply_review_page.py` | ✅ Approve / Edit / Reject 真实写库 |
| 追踪评测 | `trace_eval_page.py` | ✅ 接入 TraceService / EvalService，Run Eval 可用 |

### Demo Mode（Phase 4）
- `DemoLoader` — 加载 5 个 mock JSON 文件（classification/sentiment/insights/replies/trace）
- `MockProvider` — 模拟 LLM 输出，不依赖网络/API key
- 15 条示例评论（`sample_reviews.csv`），覆盖正/中/负情绪 + 卫生/等待/服务三大问题
- 5 条草稿中：3 pass / 1 rewrite_required / 1 blocked

### 测试基础设施
| 脚本 | 覆盖范围 | 测试数 |
|------|---------|--------|
| `smoke_test_repos` | Repository CRUD | 38 |
| `smoke_test_review_service` | CSV 上传/校验 | 43 |
| `smoke_test_demo_loader` | Demo 数据完整性 | 361 |
| `smoke_test_demo_workflow` | Workflow 全流程 | 145 |
| `smoke_test_services` | 5 个服务综合 | 77 |
| `smoke_test_upload_flow` | Upload 页面调用链 | 56 |
| `smoke_test_dashboard_data` | Dashboard 数据加载 | 137 |
| `smoke_test_reply_review_flow` | Reply Review 审批流 | 67 |
| `smoke_test_trace_eval_page_data` | Trace/Eval 数据加载 | 87 |
| `e2e_demo_check` | 端到端全流程 | 46 |
| **合计** | | **1,057** |

### 验收命令（一键）
```bash
python scripts/init_db.py
for f in smoke_test_repos smoke_test_review_service smoke_test_demo_loader smoke_test_demo_workflow smoke_test_services smoke_test_upload_flow smoke_test_dashboard_data smoke_test_reply_review_flow smoke_test_trace_eval_page_data; do python scripts/$f.py; done
python scripts/e2e_demo_check.py
python -m compileall apps src scripts -q
```

---

## 四、未实现 / 空壳模块

### 高优先级（影响 MVP v1.0）

**1. Live LLM Mode 不可用**
- `llm/openai_provider.py` — 空壳，未实现 `classify_reviews / analyze_sentiment / generate_insights / draft_replies / check_safety`
- `llm/ollama_provider.py` — 空壳
- `llm/llm_router.py` — 空壳，未实现 demo/live 模式切换
- `WorkflowService.run_analysis(mode="live")` — 当前只支持 `mode="demo"`，live 模式会直接报错
- **影响：** 当前只能跑 Demo Mode，无法使用真实 LLM

**2. Harness 模块大量空壳**
- `harness/safety/safety_guardrails.py` — 空壳（安全规则在 `MockProvider.check_safety` 中硬编码）
- `harness/output/schema_guard.py` — 空壳（Schema 校验未落地）
- `harness/evidence/evidence_guard.py` — 空壳（证据绑定逻辑在 WorkflowService 中硬编码）
- `harness/human/approval_gate.py` — 空壳（审批流程在 ReplyService 中直接实现）
- **影响：** 当前 Harness 规则散落在 service 和 mock provider 中，未集中管理

**3. Schemas 未集成**
- `schemas/` 下 7 个 Pydantic model 文件已定义，但 service 层未使用它们做校验
- 当前数据以 `dict[str, Any]` 形式传递，无运行时类型检查

**4. UI 占位功能**
- Trace & Eval 页 "📥 导出报告" / "📋 复制 Trace" — `disabled=True`，无实现
- 部分组件文件为空壳：`issue_card.py`, `reply_queue.py`, `harness_status.py`, `trace_timeline.py`, `validation_result.py`（渲染逻辑内联在页面文件中）

### 中优先级

**5. agent_runtime 全部空壳**
- 15 个文件（graph/state/nodes/edges/agents/tools）全部为空文件
- 原计划用 LangGraph 构建多 Agent 编排，但 MVP 用 WorkflowService 替代了
- 如果未来要升级为多 Agent 自治系统，从这里开始

**6. observability 未集成**
- `observability/` 下 6 个文件（trace_logger, event_bus, metrics, latency_tracker, run_recorder, debug_dump）存在但未接入任何模块
- 当前 trace 直接写入 SQLite，未经过 observability 抽象层

**7. domain 层未集成**
- `domain/entities.py`, `value_objects.py`, `business_rules.py` 存在但 service 层未引用
- 当前业务规则以硬编码方式存在 service 和 mock provider 中

### 低优先级

**8. agents/ 和 mcps/ 目录**
- `agents/review_agent.py` — 旧版单文件 agent，未被引用
- `mcps/reviews/` — MCP server 骨架，包含 validate_data/parse_csv/generate_draft skill，但未与主系统连接

**9. exports 模块未集成**
- `exports/approved_replies_exporter.py`, `report_exporter.py` — 存在但未被 UI 或 service 调用

**10. scripts 目录中的空壳**
- `run_eval.py`, `dump_trace.py`, `export_approved_replies.py`, `reset_demo_data.py`, `demo_load_reviews.py` — 1 行空文件

---

## 五、已知缺陷与问题

### Bug 修复记录
| 问题 | 状态 |
|------|------|
| Insights `issue_summary` 字段未写入 DB | ✅ 已修复（Phase 5 + Phase 7 验证） |
| Reply Review 驳回 toast `icon="✗"` 非法 emoji | ✅ 已修复（改用 `icon="❌"`） |
| Popover 驳回按钮 `disabled=not reason.strip()` 需点两次 | ✅ 已修复（去掉 disabled，点击时校验） |
| Dashboard issue card topic/evidence_status 英文显示 | ✅ 已修复（添加中文映射表） |

### 已知设计问题
1. **Service 返回 `dict` 而非 TypedDict/Pydantic：** 数据形状靠约定而非类型系统，IDE 无补全提示
2. **UI 页面渲染逻辑内联：** 4 个页面文件均 300-600 行，组件逻辑未抽取到 `components/`
3. **`data_cleaning` 和 `safety_check` trace status 固定为 `warning`：** 因为 CSV 有 1 empty + 1 dup，且 COFF08 被 blocked。这是正确的但可能引起困惑
4. **Eval 完全基于 rule-based：** 对比 mock ground truth，topic_acc=100% 是因为数据自洽。真实 LLM 模式下这个值会下降
5. **无错误重试机制：** WorkflowService 中某步失败直接标记 batch 为 failed，不会重试
6. **无 batch_id 过期机制：** 所有 demo 数据跑完后需手动清理或等 smoke test 自动清理

---

## 六、后续开发方向（建议优先级）

### 第一优先：Live LLM Mode（通往 v1.0）
1. **实现 `openai_provider.py`：** 继承 `BaseLLMProvider`，对接 OpenAI-compatible API
2. **实现 `llm_router.py`：** 根据环境变量/配置切换 demo/ollama/openai
3. **改造 `WorkflowService.run_analysis`：** 支持 `mode="live"` 调用真实 LLM
4. **集成 schemas：** 使用 Pydantic 校验所有 LLM 输出，失败时 fallback
5. **添加重试逻辑：** `harness/output/structured_retry.py` 目前是空壳

### 第二优先：Harness 落地
1. **实现 `harness/safety/safety_guardrails.py`：** 将 MockProvider 中的安全规则迁移过来
2. **实现 `harness/output/schema_guard.py`：** 基于 `schemas/` 做结构化校验
3. **实现 `harness/evidence/evidence_guard.py`：** 确保每项洞察有充分证据
4. **接入 `harness/middleware/`：** trace_middleware、retry_middleware、guardrail_middleware

### 第三优先：代码质量
1. **抽取 UI 组件：** 将 4 个页面中的渲染函数迁移到 `components/` 同名文件
2. **TypedDict 类型定义：** 为 service 返回值添加类型注解
3. **实现导出功能：** Trace & Eval 页的导出报告、Dashboard 的导出回复
4. **清理空壳 scripts：** 删除或实现 `run_eval.py` 等空文件

### 远期（v1.1+）
- 引入 LangGraph 替代 WorkflowService（`agent_runtime/` 已预留骨架）
- 接入 Ollama 本地模型
- PDF/Markdown 报告生成
- 多门店支持
- 平台爬虫（需合规审批）

---

## 七、开发环境速查

```bash
# 激活虚拟环境
. venv/Scripts/activate   # Windows
source venv/bin/activate  # Linux/Mac

# 快速全量验收
python scripts/init_db.py
python scripts/e2e_demo_check.py    # 46 项端到端
python -m compileall apps src scripts -q

# 完整验收（10 条 smoke test，约 30 秒）
for f in smoke_test_repos smoke_test_review_service smoke_test_demo_loader smoke_test_demo_workflow smoke_test_services smoke_test_upload_flow smoke_test_dashboard_data smoke_test_reply_review_flow smoke_test_trace_eval_page_data; do python scripts/$f.py; done

# 启动 UI
streamlit run apps/streamlit_app/app.py

# 查看数据库
sqlite3 data/small_shop.db
.tables                           # 列出 9 张表
.schema reply_drafts              # 查看表结构
SELECT * FROM traces ORDER BY id;  # 查看 Trace
```

## 八、关键文件速查

| 需求 | 文件 |
|------|------|
| 项目规范 | `CLAUDE.md`, `AGENT.md` |
| 产品需求 | `docs/01_prd.md` |
| 架构设计 | `docs/02_architecture.md` |
| 数据库设计 | `docs/03_database_spec.md` |
| API 设计 | `docs/04_api_design.md` |
| MVP 任务清单 | `docs/05_mvp_tasks.md` |
| 路线图 | `docs/06_roadmap.md` |
| 验收流程 | `docs/acceptance_guide.md` |
| Demo 数据 | `src/small_shop_agent/demo/`（5 个 mock JSON + 1 个 CSV） |
| 核心 Workflow | `src/small_shop_agent/services/workflow_service.py` |
| 审批逻辑 | `src/small_shop_agent/services/reply_service.py` |
| 评测逻辑 | `src/small_shop_agent/evals/eval_runner.py` |
| 上传页面 | `apps/streamlit_app/pages/upload_page.py` |
| 看板页面 | `apps/streamlit_app/pages/dashboard_page.py` |
