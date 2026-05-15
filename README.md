# Small Shop Review Response & Insight Agent

面向线下门店的轻量级 AI Agent 工作流系统，覆盖差评分析、问题洞察、回复生成与人工审批全链路。

## 核心流程

```
CSV 上传 → 分类与情绪分析 → Top 3 问题聚合 → 回复草稿 → 安全检查 → 人工审批 → Dashboard → Trace/Eval
```

设计原则：短链路、可审批、有证据、可观测。

## 技术栈

| 层级 | 技术 |
|------|------|
| UI | Streamlit |
| 语言 | Python 3.11+ |
| 数据库 | SQLite (WAL mode) |
| 数据处理 | pandas |
| 日志 | loguru |
| Schema 校验 | Pydantic |
| LLM 接口 | OpenAI-compatible API / Ollama |

## 快速启动

```bash
pip install -r requirements.txt
python scripts/init_db.py
streamlit run apps/streamlit_app/app.py
```

浏览器访问 `http://localhost:8501`。

## 运行模式

### 内置数据模式（默认）

系统内置 15 条示例评论数据，无需外部 API 即可运行完整流程。适用于本地开发与功能验证。

### Live 模式

配置环境变量以连接 LLM 服务：

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_MODE` | 是 | 设为 `live` |
| `OPENAI_API_KEY` | 是 | API 密钥 |
| `OPENAI_MODEL` | 是 | 模型名称（如 `gpt-4o-mini`） |
| `OPENAI_BASE_URL` | 否 | 自定义 API 地址 |

> 未配置有效 `OPENAI_API_KEY` 时，Live 模式不可用。

## CSV 数据格式

| 列名 | 必填 | 说明 |
|------|------|------|
| `review_text` | 是 | 评论正文 |
| `rating` | 是 | 评分 (1-5) |
| `date` | 是 | 评论日期 |
| `review_id` | 否 | 评论 ID（缺省自动生成 UUID） |
| `platform` | 否 | 来源平台 |
| `customer_name` | 否 | 顾客名称 |

支持编码：UTF-8 / GBK / GB2312 / GB18030 / Latin-1

## 页面架构

### 上传评论 (Upload)
上传 CSV 文件，选择门店类型，启动分析流程。系统自动完成校验、清洗、入库与全链路分析。

### 数据看板 (Dashboard)
展示批次评论概览（总数/均分/差评数/待审核数）、Top 3 问题洞察（含证据关联评论）、Harness Engine 工作流可靠性状态。

### 回复审核 (Reply Review)
左侧待处理草稿队列，右侧详情面板展示原始评论与 AI 生成的回复草稿。支持三种操作：
- **批准** — 仅限安全检查通过的草稿
- **编辑** — 修改回复内容后保存
- **驳回** — 填写原因后驳回

被拦截（blocked）或需重写（rewrite_required）的草稿不可直接批准。

### 追踪与评测 (Trace & Eval)
左侧展示工作流执行时间线（步骤名称、状态、输入/输出摘要、耗时），右侧展示评测指标（分类准确率、情绪准确率、不安全回复数、综合评分）及历史评测记录。

## 功能边界

本系统聚焦差评处理与问题复盘，以下功能不在范围内(属于后续开发方向与功能完善)：

- 自动发布回复（所有回复须人工审批）
- 平台评论爬取
- 多门店系统
- 账号/权限系统
- 复杂 BI 与趋势分析
- 周报生成
- 移动端

## Agent Runtime

系统支持两种运行时，通过 `WORKFLOW_RUNTIME` 配置切换：

| 运行时 | 配置值 | 特点 |
|--------|--------|------|
| Pipeline | `pipeline` | 线性顺序执行，稳定可靠 |
| Agent Graph | `agent_graph` | 条件路由、重试降级、异步并发 |

Agent Graph 特性：
- **条件路由**：根据 LLM 输出状态自动决策下一步（retry / fallback / escalate）
- **工具注入**：`count_by_topic`、`search_reviews`、`lookup_review`、`get_safety_policy_snippet`
- **记忆检索**：基于 SQLite LIKE 检索历史审批样本，注入回复生成上下文
- **异步并发**：classification 与 sentiment 通过 `asyncio.gather` 并发执行
- **双引擎安全**：Rule Guard + LLM Semantic Judge，分歧自动升级为人工处理

## 测试

```bash
pytest tests/unit/ -v
python scripts/e2e_demo_check.py
python scripts/e2e_demo_check.py --runtime agent_graph
```

## 文档

- [AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) — 系统架构、Agent Runtime、Guardrails、Memory
- [Database Spec](docs/03_database_spec.md) — 11 张表设计
- [API Design](docs/04_api_design.md) — 服务层接口
- [MVP Tasks](docs/05_mvp_tasks.md) — 开发阶段任务
- [Roadmap](docs/06_roadmap.md) — 版本路线图
- [UI Design System](docs/ui_design_system.md) — UI 设计规范
