# GitHub 上传前项目整理分析报告

> 生成日期：2026-05-14
> 项目：Small Shop Review Response & Insight Agent
> 目的：简历展示 + GitHub 开源展示

---

## 1. 当前项目结构总览

```
d:\small-shop-review-agent/
├── apps/streamlit_app/       # Streamlit 前端 4 页面 + 11 组件
│   ├── pages/                # upload / dashboard / reply_review / trace_eval
│   ├── components/           # sidebar, styles, layout, ui_components, ui_helpers, metric_card
│   └── assets/icons/         # 空目录
├── src/small_shop_agent/     # 核心 Python 包
│   ├── agent_runtime/        # 自研 Agent Graph（state + graph + runner）
│   │   ├── agents/           # 5 个空壳 Agent 文件
│   │   ├── graph/            # review_workflow.py + 空 checkpoints.py
│   │   └── tools/            # 5 个空壳 Tool 文件
│   ├── core/                 # config.py, enums.py + 空 constants.py, errors.py
│   ├── demo/                 # Demo Loader + sample CSV + mock JSON
│   ├── domain/               # business_rules.py, entity.py
│   ├── evals/                # eval_runner, 空 datasets, 空 reports, scorers
│   ├── exports/              # report_exporter.py
│   ├── harness/              # 7 大类防护：input/output/evidence/safety/human/verification/middleware
│   ├── llm/                  # LLM providers: mock, openai, ollama, router
│   ├── observability/        # metrics.py + 空 debug_dump, latency_tracker
│   ├── prompts/              # prompt_registry + 10 个空 system/template md 文件
│   ├── schemas/              # 6 个空 schema 文件
│   ├── services/             # 8 个业务服务
│   ├── storage/              # database + 11 migrations + 8 repositories
│   └── utils/                # logger.py + 空 __init__.py
├── tests/                    # 236 单元测试
│   ├── unit/                 # 25 个测试文件
│   ├── eval/                 # 空目录
│   ├── integration/          # 空目录
│   └── fixtures/             # 空目录（存在但未检查内容）
├── scripts/                  # 20+ 脚本（E2E / smoke tests / demo helpers）
├── mcps/                     # MCP 服务器实验代码
├── agents/                   # 废弃目录（仅含 .pyc 缓存）
├── data/                     # 运行数据（DB、日志、上传文件）
│   ├── exports/              # 空
│   ├── processed/            # 空
│   └── uploads/              # sample_reviews.csv 副本
├── docs/                     # 20+ 文档文件
├── .streamlit/               # Streamlit 配置（空目录）
├── temp/                     # 空临时目录
├── venv/                     # 虚拟环境（已在 .gitignore）
├── .claude/                  # Claude Code 内部文件
├── .gitignore                # 已存在
├── .env                      # **含真实 API Key！**
├── README.md                 # 已存在（约 85 行）
├── CLAUDE.md                 # 项目指令（约 246 行）
├── pyproject.toml            # 项目元数据
└── requirements.txt          # 依赖列表
```

---

## 2. 空文件与空目录扫描结果

### 2.1 空文件（0 字节）— 按区域分组

#### A. 组件空壳（5 个）

| 文件 | 建议 |
|---|---|
| `apps/streamlit_app/components/harness_status.py` | 建议删除 |
| `apps/streamlit_app/components/issue_card.py` | 建议删除 |
| `apps/streamlit_app/components/reply_queue.py` | 建议删除 |
| `apps/streamlit_app/components/trace_timeline.py` | 建议删除 |
| `apps/streamlit_app/components/validation_result.py` | 建议删除 |

#### B. Agent 空壳（5 个）

| 文件 | 建议 |
|---|---|
| `src/small_shop_agent/agent_runtime/agents/issue_insight_agent.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/agents/reply_drafter_agent.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/agents/review_classifier_agent.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/agents/safety_checker_agent.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/agents/sentiment_agent.py` | 建议删除 |

#### C. Tool 空壳（5 个）+ Graph 空壳

| 文件 | 建议 |
|---|---|
| `src/small_shop_agent/agent_runtime/tools/evidence_lookup_tool.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/tools/export_tool.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/tools/issue_aggregation_tool.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/tools/reply_template_tool.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/tools/review_store_tool.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/context.py` | 建议删除 |
| `src/small_shop_agent/agent_runtime/graph/checkpoints.py` | 建议删除 |

#### D. Core / Harness 空壳

| 文件 | 建议 |
|---|---|
| `src/small_shop_agent/core/constants.py` | 建议保留（核心模块预留） |
| `src/small_shop_agent/core/errors.py` | 建议保留（核心模块预留） |
| `src/small_shop_agent/harness/human/approval_events.py` | 需要确认 |
| `src/small_shop_agent/harness/human/approval_policy.py` | 需要确认 |
| `src/small_shop_agent/harness/middleware/retry_middleware.py` | 需要确认 |
| `src/small_shop_agent/harness/safety/reply_risk_rules.py` | 需要确认 |
| `src/small_shop_agent/observability/debug_dump.py` | 建议删除 |
| `src/small_shop_agent/observability/latency_tracker.py` | 需要确认 |

#### E. Schema 空壳（6 个）— 全部建议保留

| 文件 | 建议 |
|---|---|
| `src/small_shop_agent/schemas/analysis_schema.py` | 保留（架构预留） |
| `src/small_shop_agent/schemas/eval_schema.py` | 保留 |
| `src/small_shop_agent/schemas/insight_schema.py` | 保留 |
| `src/small_shop_agent/schemas/reply_schema.py` | 保留 |
| `src/small_shop_agent/schemas/safety_schema.py` | 保留 |
| `src/small_shop_agent/schemas/trace_schema.py` | 保留 |

#### F. Prompt 空壳（10 个 .md）— 全部需要确认

| 文件 | 建议 |
|---|---|
| `src/small_shop_agent/prompts/system/classifier_system.md` | 需要确认 |
| `src/small_shop_agent/prompts/system/insight_system.md` | 需要确认 |
| `src/small_shop_agent/prompts/system/reply_system.md` | 需要确认 |
| `src/small_shop_agent/prompts/system/safety_system.md` | 需要确认 |
| `src/small_shop_agent/prompts/system/sentiment_system.md` | 需要确认 |
| `src/small_shop_agent/prompts/templates/analyze_sentiment.md` | 需要确认 |
| `src/small_shop_agent/prompts/templates/check_safety.md` | 需要确认 |
| `src/small_shop_agent/prompts/templates/classify_review.md` | 需要确认 |
| `src/small_shop_agent/prompts/templates/draft_reply.md` | 需要确认 |
| `src/small_shop_agent/prompts/templates/generate_insight.md` | 需要确认 |

#### G. 文档空壳

| 文件 | 建议 |
|---|---|
| `docs/01_prd.md` | 建议删除或填写 |
| `docs/02_architecture.md` | 建议删除或填写 |
| `docs/07_prompt_spec.md` | 建议删除或填写 |
| `docs/08_eval_spec.md` | 建议删除或填写 |
| `docs/09_ui_style_guide.md` | 建议删除或填写 |

#### H. 脚本 / Eval 空壳

| 文件 | 建议 |
|---|---|
| `scripts/dump_trace.py` | 建议删除 |
| `scripts/export_approved_replies.py` | 建议删除 |
| `scripts/reset_demo_data.py` | 建议删除 |
| `scripts/run_eval.py` | 建议删除 |
| `src/small_shop_agent/evals/datasets/eval_reviews.jsonl` | 建议删除 |
| `src/small_shop_agent/evals/datasets/unsafe_reply_cases.jsonl` | 建议删除 |
| `src/small_shop_agent/evals/reports/latest_eval_result.json` | 保留（运行时占位） |

#### I. `__init__.py` 空壳 — 全部保留

| 文件 | 建议 |
|---|---|
| `src/small_shop_agent/__init__.py` | 保留（Python 包标记） |
| `src/small_shop_agent/utils/__init__.py` | 保留 |
| `tests/__init__.py` | 保留 |
| `tests/unit/__init__.py` | 保留 |

### 2.2 空目录

| 目录 | 建议 |
|---|---|
| `.claude/worktrees/` | 保留（Claude Code 内部） |
| `.sixth/skills/` | 需要确认 |
| `apps/streamlit_app/assets/icons/` | 保留（加 `.gitkeep`） |
| `data/exports/` | 保留（运行时目录） |
| `data/processed/` | 保留（运行时目录） |
| `temp/` | 建议删除 |
| `tests/eval/` | 保留（加 `.gitkeep`） |
| `tests/integration/` | 保留（加 `.gitkeep`） |

---

## 3. 缓存、临时文件、数据库、日志扫描结果

### 3.1 必须删除（不提交到 Git）

| 类型 | 路径 | 说明 |
|---|---|---|
| Python 缓存 | 30+ `__pycache__/` 目录 | 已在 .gitignore |
| 测试缓存 | `.pytest_cache/` | 已在 .gitignore |
| 数据库 | `data/small_shop.db` | 运行生成，已 gitignore |
| 数据库 | `data/e2e_test.db` | 运行生成，已 gitignore |
| 日志 | `data/app.log` | `*.log` 已覆盖 |
| 上传文件 | `data/uploads/sample_reviews.csv` | `data/uploads/` 已 gitignore |
| 虚拟环境 | `venv/` | 已在 .gitignore |
| 废弃缓存 | `agents/__pycache__/` | 整个 `agents/` 目录建议删除 |
| egg 信息 | `src/small_shop_agent.egg-info/` | 删除 |
| 空 temp | `temp/` | 删除目录 |

### 3.2 .gitignore 现有覆盖

当前 `.gitignore` 已覆盖：`__pycache__/`、`*.py[cod]`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`venv/`、`.venv/`、`env/`、`.env`、`.env.*`、`data/*.db`、`data/uploads/`、`data/processed/`、`data/exports/`、`.streamlit/secrets.toml`、`.DS_Store`、`Thumbs.db`、`.vscode/`、`.idea/`、`*.log`、`dist/`、`build/`、`*.egg-info/`。

**缺失项**：`temp/`、`agents/`。

---

## 4. 敏感信息风险扫描

### 4.1 CRITICAL — 真实 API Key 泄露

| 文件 | 行 | 内容 | 风险 |
|---|---|---|---|
| `.env` | 4 | `OPENAI_API_KEY=sk-qusrygxoicgtgdsypiyiptlektdobbgwjawvddlchejchsfa` | **极高 — 真实 SiliconFlow API Key！** |
| `.env` | 7 | `OPENAI_BASE_URL=https://api.siliconflow.cn/v1` | 高（暴露服务商） |
| `.env` | 12 | `LLM_MODE=live` | 低 |

**处理方式**：
1. **立即撤销**该 API Key（在 SiliconFlow 控制台重新生成）
2. `.env` 已在 `.gitignore` 中，不会被 commit，但该 key 已经暴露在本机
3. 创建 `.env.example` 文件，只保留占位符

### 4.2 代码中 API Key 引用（均为示例/占位符）

| 文件 | 内容 | 风险 |
|---|---|---|
| `docs/project_report.md:263` | `OPENAI_API_KEY = "sk-xxx"` | 低风险示例 |
| `scripts/smoke_test_openai_provider_contract.py:38` | `api_key="sk-test-123"` | 低风险测试占位 |
| `scripts/smoke_test_openai_provider_contract.py:58` | `os.environ["OPENAI_API_KEY"] = "sk-env-456"` | 低风险测试占位 |
| `src/.../llm/llm_router.py:70` | 提示文案提到 `sk-...` | 低风险示例文案 |

### 4.3 其他

- 无真实手机号、邮箱、门店数据
- 示例 CSV 评论数据为合成假数据
- README 和文档只提到环境变量名，未暴露真实值

---

## 5. 无效引用与废弃代码风险

### 5.1 空壳目录引用

所有 5 个 `agent_runtime/tools/` 空文件 + 5 个 `agent_runtime/agents/` 空文件 + `context.py` + `checkpoints.py` — 这些文件虽存在但内容为空，import 不会报错但也没有功能。建议删除。

### 5.2 废弃目录

| 目录 | 说明 |
|---|---|
| `agents/` | 仅含 `__pycache__/review_agent.cpython-312.pyc`，无源码。**建议删除** |
| `mcps/` | 含 MCP 服务器实验代码（`reviews/`）。**需要确认**是否保留 |

### 5.3 components/ `__init__.py` 导出空壳

`apps/streamlit_app/components/__init__.py` 导出列表中不包含那 5 个空壳组件（`harness_status`, `issue_card`, `reply_queue`, `trace_timeline`, `validation_result`）。删除它们不会破坏任何 import。

### 5.4 TODO / FIXME / Deprecated 标记

仅 4 处，均为 legacy wrapper 标记（`metric_card.py` 和 `__init__.py`）。属于有意保留的兼容层，非待清理 TODO。

### 5.5 .egg-info 冗余

`src/small_shop_agent.egg-info/` — 已在 `.gitignore` 的 `*.egg-info/` 中。

---

## 6. 测试与脚本保留建议

### 6.1 测试文件（全部保留，25 个）

```
tests/conftest.py
tests/unit/test_agent_async.py
tests/unit/test_agent_routing.py
tests/unit/test_agent_tools.py
tests/unit/test_approval_memory.py
tests/unit/test_consistency_check.py
tests/unit/test_csv_validator.py
tests/unit/test_dual_engine_guard.py
tests/unit/test_eval_service.py
tests/unit/test_evidence_guard.py
tests/unit/test_memory_repository.py
tests/unit/test_memory_retriever.py
tests/unit/test_ollama_provider.py
tests/unit/test_pipeline_steps.py
tests/unit/test_prompt_registry.py
tests/unit/test_reliability_metrics.py
tests/unit/test_reply_service.py
tests/unit/test_safety_guardrails.py
tests/unit/test_safety_red_team.py
tests/unit/test_schema_guard.py
tests/unit/test_semantic_safety_schema.py
tests/unit/test_structured_retry.py
tests/unit/test_ui_components.py
tests/unit/test_workflow_service.py
```

### 6.2 脚本保留建议

#### 必须保留

| 脚本 | 原因 |
|---|---|
| `e2e_demo_check.py` | 59 项 E2E 验收 |
| `smoke_test_demo_workflow.py` | Demo 全流程验证 |
| `smoke_test_demo_loader.py` | Demo 数据加载验证 |
| `smoke_test_safety_guardrails.py` | Safety 冒烟测试 |
| `smoke_test_evidence_guard.py` | Evidence 冒烟测试 |
| `smoke_test_schema_guard.py` | Schema 冒烟测试 |
| `smoke_test_structured_retry.py` | 重试机制测试 |
| `smoke_test_upload_flow.py` | 上传流程测试 |
| `smoke_test_review_service.py` | Review 服务测试 |
| `smoke_test_reply_review_flow.py` | 回复审核流程测试 |
| `smoke_test_services.py` | 服务层冒烟测试 |
| `smoke_test_repos.py` | Repository 冒烟测试 |
| `smoke_test_dashboard_data.py` | 看板数据测试 |
| `smoke_test_trace_eval_page_data.py` | Trace/Eval 数据测试 |
| `smoke_test_llm_router.py` | LLM 路由测试 |
| `smoke_test_live_workflow_contract.py` | Live 模式合约测试 |
| `smoke_test_live_openai_sample.py` | Live OpenAI 测试 |
| `smoke_test_openai_provider_contract.py` | Provider 合约测试 |
| `demo_load_reviews.py` | Demo 数据初始化 |
| `init_db.py` | 数据库初始化 |

#### 建议删除（空文件）

| 脚本 | 原因 |
|---|---|
| `dump_trace.py` | 空文件 |
| `export_approved_replies.py` | 空文件 |
| `reset_demo_data.py` | 空文件 |
| `run_eval.py` | 空文件 |

---

## 7. .gitignore 建议

当前 `.gitignore` 已覆盖大部分场景。建议补充：

```gitignore
# 补充条目
temp/
agents/
*.swp
*.swo
*~
.ipynb_checkpoints/
```

**必须新增的示例文件**：

- **`.env.example`**：
  ```bash
  OPENAI_API_KEY=sk-your-key-here
  OPENAI_BASE_URL=https://api.openai.com/v1
  OPENAI_MODEL=gpt-4o-mini
  LLM_MODE=demo
  ```

- **`.gitkeep` 文件**（空目录需要保留占位）：
  - `data/uploads/.gitkeep`
  - `data/exports/.gitkeep`
  - `data/processed/.gitkeep`
  - `tests/eval/.gitkeep`
  - `tests/integration/.gitkeep`
  - `apps/streamlit_app/assets/icons/.gitkeep`

---

## 8. requirements.txt 分析

### 8.1 当前状态

| 来源 | 内容 |
|---|---|
| `pyproject.toml` | 8 个核心依赖 + 3 个 dev 依赖 |
| `requirements.txt` | 12 个（含 dev 工具），注释风格 |
| `setup.py` | 不存在 |
| `poetry.lock` / `uv.lock` | 不存在 |

### 8.2 问题

1. `requirements.txt` 列出了 `streamlit-option-menu>=0.3.0` 和 `streamlit-aggrid>=0.4.2` — 项目未实际 import 这两个包。**建议删除**。
2. `requirements.txt` 包含 dev 工具，应在 `requirements-dev.txt` 中单独管理。
3. `pyproject.toml` 中 `requires-python = ">=3.11"`，`typing-extensions` 可移除。

### 8.3 推荐 requirements.txt（最小运行依赖）

```
streamlit>=1.28
pandas>=2.0
loguru>=0.7
pydantic>=1.10
python-dotenv>=1.0
openai>=1.29.0
requests>=2.31
```

---

## 9. README.md 结构建议

```markdown
# ☕ 小店评论经营助手

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](your-url)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)]()

> 面向线下门店的轻量级 AI Agent 工作流系统 — 差评分析 → 洞察聚合 → 回复草稿 → 安全审查 → 人工审批。

## 🎯 在线演示
## 🚀 核心功能
## 🏗 架构设计
## 🛡️ Harness 防护体系
## 🔍 Trace & Eval
## 🏃 本地运行
## 🧪 测试
## 📁 项目结构
## ✨ 简历亮点
```

---

## 10. GitHub 上传前最终待办清单

### 🔴 必须做（安全 & 合规）

- [ ] **撤销 `.env` 中的真实 API Key**，在 SiliconFlow 控制台重新生成
- [ ] **创建 `.env.example`** 带占位符
- [ ] **删除 `data/small_shop.db`、`data/e2e_test.db`、`data/app.log`**
- [ ] **清理所有 `__pycache__/` 和 `.pytest_cache/`**
- [ ] **删除 `agents/` 目录**（废弃 .pyc）
- [ ] **删除 `src/small_shop_agent.egg-info/`**
- [ ] **删除 `temp/` 目录**
- [ ] **运行 `python -m compileall apps src -q`**
- [ ] **运行 `python -m pytest tests/unit/ -q`**
- [ ] **运行 `python scripts/e2e_demo_check.py --runtime agent_graph --mode mock`**

### 🟡 建议做（代码整洁）

- [ ] 删除 5 个空组件文件
- [ ] 删除 5 个空 Agent + 5 个空 Tool + 空 context/checkpoints
- [ ] 删除 4 个空脚本
- [ ] 空目录添加 `.gitkeep`
- [ ] 精简 `requirements.txt`（移除 `streamlit-option-menu`、`streamlit-aggrid`）
- [ ] 完善 `README.md`
- [ ] 更新 `.gitignore`

### 🟢 可选做

- [ ] 部署到 Streamlit Community Cloud
- [ ] 录制 Demo GIF
- [ ] 添加 GitHub Actions CI
- [ ] 填写空 prompt .md 和空 schema .py

---

## 11. 推荐执行命令

```bash
# === 1. 清理缓存 ===
find . -type d -name '__pycache__' -not -path './venv/*' -exec rm -rf {} + 2>/dev/null
rm -rf .pytest_cache/

# === 2. 删除废弃目录 ===
rm -rf agents/ temp/ src/small_shop_agent.egg-info/

# === 3. 删除空壳文件（组件） ===
rm -f apps/streamlit_app/components/harness_status.py
rm -f apps/streamlit_app/components/issue_card.py
rm -f apps/streamlit_app/components/reply_queue.py
rm -f apps/streamlit_app/components/trace_timeline.py
rm -f apps/streamlit_app/components/validation_result.py

# === 4. 删除空壳文件（Agent） ===
rm -f src/small_shop_agent/agent_runtime/agents/issue_insight_agent.py
rm -f src/small_shop_agent/agent_runtime/agents/reply_drafter_agent.py
rm -f src/small_shop_agent/agent_runtime/agents/review_classifier_agent.py
rm -f src/small_shop_agent/agent_runtime/agents/safety_checker_agent.py
rm -f src/small_shop_agent/agent_runtime/agents/sentiment_agent.py

# === 5. 删除空壳文件（Tool + Graph） ===
rm -f src/small_shop_agent/agent_runtime/tools/evidence_lookup_tool.py
rm -f src/small_shop_agent/agent_runtime/tools/export_tool.py
rm -f src/small_shop_agent/agent_runtime/tools/issue_aggregation_tool.py
rm -f src/small_shop_agent/agent_runtime/tools/reply_template_tool.py
rm -f src/small_shop_agent/agent_runtime/tools/review_store_tool.py
rm -f src/small_shop_agent/agent_runtime/context.py
rm -f src/small_shop_agent/agent_runtime/graph/checkpoints.py
rm -f src/small_shop_agent/observability/debug_dump.py

# === 6. 删除空脚本 ===
rm -f scripts/dump_trace.py scripts/export_approved_replies.py
rm -f scripts/reset_demo_data.py scripts/run_eval.py

# === 7. 清理数据文件 ===
rm -f data/small_shop.db data/e2e_test.db data/app.log

# === 8. 创建 .gitkeep ===
touch data/uploads/.gitkeep data/exports/.gitkeep data/processed/.gitkeep
touch tests/eval/.gitkeep tests/integration/.gitkeep
touch apps/streamlit_app/assets/icons/.gitkeep

# === 9. 创建 .env.example ===
cat > .env.example << 'EOF'
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
LLM_MODE=demo
EOF

# === 10. 验证 ===
python -m compileall apps src -q
python -m pytest tests/unit/ -q
python scripts/e2e_demo_check.py --runtime agent_graph --mode mock

# === 11. Git 初始化与推送 ===
git init
git checkout -b main
git add .
git commit -m "Initial public release: Small Shop Review Agent v0.1.0"
git remote add origin https://github.com/YOUR_USER/small-shop-review-agent.git
git push -u origin main
```

---

> ⚠️ 本报告为只读分析，未对项目做任何实际修改。请在确认后手动执行上述命令。
