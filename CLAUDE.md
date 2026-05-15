# CLAUDE.md

## 1. 项目身份与定位

Small Shop Review Response & Insight Agent — 面向小型门店（咖啡店、餐厅等）的轻量级 Agentic Workflow 系统。

技术栈：Python 3.11+ / Streamlit / SQLite (WAL) / pandas / loguru / Pydantic。内置 mock 数据提供确定性离线运行能力，同时支持 OpenAI-compatible API。

## 2. 核心业务闭环

```
CSV 上传 → 分类与情绪 → Top 3 问题 → 回复草稿 → 安全检查 → 人工审批 → Dashboard → Trace/Eval
```

系统功能：
1. 上传评论 CSV 并自动校验清洗
2. 识别评论主题与情绪
3. 聚合 Top 3 问题并绑定证据
4. 为差评生成回复草稿
5. 执行安全检查
6. 人工审批回复
7. Dashboard 展示分析结果
8. Trace & Eval 页面展示系统可靠性

## 3. 架构原则

- UI 层负责展示，调用 service 层
- service 层封装业务操作，返回 TypedDict
- workflow 层组织 pipeline 步骤
- harness 层负责校验、安全、证据、追踪、fallback
- database 层（repositories）负责 SQLite 持久化
- 所有 LLM 输出须经 Pydantic Schema 校验
- 所有洞察须绑定 review_id 证据
- 所有回复须经 Safety Check
- 所有客户可见回复须人工审批

源代码分层：
```
src/small_shop_agent/
├── core/           配置、枚举、错误
├── domain/         实体、值对象、业务常量
├── schemas/        Pydantic 模型
├── storage/        数据库连接、迁移、repository
├── services/       服务层（ReviewService, WorkflowService 等）
├── harness/        防护体系（input / output / evidence / safety / human / verification）
├── llm/            LLM Provider（MockProvider / OpenAIProvider）
├── evals/          评测运行器
├── observability/  指标收集
├── prompts/        Prompt 注册表
└── utils/          日志工具
apps/streamlit_app/   Streamlit 前端（4 页面 + 组件）
```

## 4. MVP 范围

必须保留：CSV 上传、输入校验、评论分类、情绪分析、Top 3 问题聚合、差评回复草稿、Safety Check、人工审批、Dashboard、Trace Log、Eval Summary、内置数据模式。

第一版不做：周报生成、自动发布回复、平台爬虫、多门店系统、账号系统、移动端、复杂趋势分析、复杂权限系统、LangGraph 多 Agent 编排、长期记忆、外部消息通知、完整 SaaS 后端。

## 5. 产品判断原则

功能取舍优先：短链路而非大平台；可审批而非全自动；有证据而非自由总结；稳定运行而非复杂技术；简单 Workflow 而非复杂多 Agent。

## 6. 数据约束

**CSV 必填字段**（3 列）：`review_text`、`rating`、`date`

**CSV 可选字段**：`review_id`（缺省自动生成 UUID）、`platform`、`customer_name`

- `rating` 须为 1–5 整数，超出范围默认设为 3（中性）
- 空评论不进入分析（标记 `is_empty=1`）
- 重复评论（相同 review_id 或相同 review_text）标记 `is_duplicate=1`
- `rating <= 2` 默认进入差评候选
- 支持编码：UTF-8 / GBK / GB2312 / GB18030 / Latin-1

## 7. LLM 输出与失败处理

LLM 输出须为结构化对象，不得返回自由文本。处理顺序：
1. Schema Guard 检查
2. 自动重试一次
3. fallback rule（关键字规则 / 评分推断 / 固定模板）
4. 标记 blocked 或写入 Trace
5. UI 给出可理解状态

LLM 失败不得导致页面崩溃。

## 8. Safety Rules

回复草稿禁止：
- 攻击或讽刺顾客
- 泄露隐私（电话、地址、身份证号等）
- 编造事实（声称已调查、已查看监控等）
- 承诺无法保证的赔偿（全额退款、现金赔偿等）
- 声称已处罚员工（开除、罚款等）
- 过度营销话术（新品上市、限时优惠等）
- 推卸责任

不安全回复不得进入可发布状态。`blocked` 草稿无法批准，`rewrite_required` 草稿须修改后再批准。

当前实现：`harness/safety/safety_policy.py`（关键词规则）+ `safety_guardrails.py`（检查逻辑）。

## 9. Evidence Rules

Top 3 问题须绑定证据评论。每条洞察至少绑定 2 条有效 `review_id`。证据不足时标记 `evidence_insufficient`。无证据洞察不可在 Dashboard 展示。

insight evidence 须单独建关联表（`insight_evidence`），不得塞入 JSON，以保证可查询、可展示、可解释。

当前实现：`harness/evidence/evidence_guard.py`。

## 10. Trace Rules

以下步骤须记录 Trace（`traces` 表）：

| 步骤 | step_name | 执行时机 |
|------|-----------|---------|
| 输入校验 | `input_validation` | CSV 上传后 |
| 数据清洗 | `data_cleaning` | 清洗后 |
| 评论分类 | `classification` | LLM 分类后 |
| 情绪分析 | `sentiment_analysis` | LLM 情绪分析后 |
| 问题聚合 | `issue_aggregation` | 洞察生成后 |
| 证据绑定 | `evidence_check` | 证据验证后 |
| 回复草稿 | `reply_drafting` | 回复生成后 |
| 安全检查 | `safety_check` | 安全检查后 |
| 人工审批 | `human_approval` | 审批操作时 |
| 评测运行 | `eval_run` | 评测执行后 |

每行 Trace 包含：trace_id、batch_id、step_name、status、input_summary、output_summary、latency_ms、model_name、error_message。

## 11. 回复生成原则

AI 回复须真诚、克制、不甩锅、不攻击顾客、不承诺无法保证的赔偿、不编造事实、不默认已处罚员工。所有回复须进入人工审批。

## 12. Harness Engineering 原则

核心 7 个模块：

| 模块 | 实现位置 |
|------|---------|
| Input Validator | `harness/input/csv_validator.py` |
| Schema Guard | `harness/output/schema_guard.py` |
| Structured Retry | `harness/output/structured_retry.py` |
| Evidence Binding | `harness/evidence/evidence_guard.py` |
| Safety Guardrails | `harness/safety/safety_guardrails.py` |
| Human Approval | `harness/human/approval_gate.py` + `services/reply_service.py` |
| Trace Log | `observability/` + `storage/repositories/trace_repository.py` |

Eval 通过 `evals/eval_runner.py` + `services/eval_service.py` 实现。

## 13. Dashboard 原则

Dashboard 回答四个问题：
1. 批次整体情况（总评论数 / 平均评分 / 差评数 / 待审核数）
2. 最严重的三个问题（Top 3 洞察 + 证据关联）
3. 需处理的差评（回复审核队列）
4. 工作流可靠性（Harness Engine 状态）

不做复杂 BI，不堆叠图表。

## 14. 内置数据模式

系统默认以内置 15 条示例评论和预生成 mock 数据运行，不依赖网络、外部 API 或真实 LLM，可离线展示完整流程。

通过 `MockProvider` 提供确定性输出。

## 15. UI 风格

浅色 SaaS 工作台 + 咖啡店暖色点缀。主色：#2F6B4F / #D99A32 / #F7F6F2 / #FFFFFF。四页面：上传评论、数据看板、回复审核、追踪与评测。

## 16. 代码风格

- 函数保持短小（核心方法 < 50 行，编排器 < 100 行）
- 单文件控制在 200 行以内，最多不超过 300 行
- UI 与业务逻辑分离
- 业务常量集中在 `core/config.py`
- 枚举集中在 `core/enums.py`
- prompt 集中在 `prompts/prompt_registry.py`
- 共享 schema 集中在 `services/pipeline_steps.py`
- 处理失败路径，不使用裸 except
- 优先保证 MVP 闭环，不做过度抽象

## 17. 判断标准

开发任务完成的判定：
- 符合 MVP 范围
- 内置数据模式下稳定运行
- 数据写入数据库
- 写入 Trace
- 经 Schema/Safety/Evidence 检查
- UI 正确展示
- 单元测试通过（`pytest tests/unit/ -v`）
- E2E 验收通过（`python scripts/e2e_demo_check.py`）

## 18. 约束

不引入复杂多 Agent 编排、不做登录权限系统、不自动发布回复、不加周报/爬虫/多门店功能。项目聚焦差评处理与问题复盘。
