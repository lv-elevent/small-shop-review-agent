# CLAUDE.md

## 1. 项目身份与定位

Small Shop Review Response & Insight Agent — 小店差评处理与问题洞察 Agent。

面向小型门店（咖啡店、餐厅等）的轻量级 Agentic Workflow 系统。第一版使用 Streamlit + Python Workflow + SQLite + Pydantic 构建本地可演示系统。

技术栈：Python 3.11+ / Streamlit / SQLite (WAL) / pandas / loguru / Pydantic。Demo Mode 内置 mock 数据，Live Mode 支持 OpenAI-compatible API。

## 2. 核心业务闭环

```
上传 CSV → 分类与情绪 → 三大问题 → 回复草稿 → 安全检查 → 人工审批 → Dashboard → Trace/Eval
```

系统帮助老板完成：
1. 上传评论 CSV 并自动校验清洗
2. 识别评论主题与情绪
3. 聚合 Top 3 问题并绑定证据
4. 为差评生成回复草稿
5. 进行安全检查
6. 人工审批回复
7. 在 Dashboard 展示结果
8. 在 Trace & Eval 页面展示可靠性

## 3. 架构原则

- UI 层只负责展示和调用 service
- service 层封装业务操作，返回 TypedDict
- workflow 层组织 pipeline 步骤
- harness 层负责校验、安全、证据、追踪、fallback
- database 层（repositories）负责 SQLite 持久化
- 所有 LLM 输出必须经过 Pydantic Schema 校验
- 所有洞察必须绑定 review_id 证据
- 所有回复必须经过 Safety Check
- 所有客户可见回复必须人工审批

当前源代码分层：
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

## 4. MVP 必须保留

以下功能不得删除：CSV 上传、输入校验、评论分类、情绪分析、三大问题聚合、差评回复草稿、Safety Check、人工审批、简单 Dashboard、Trace Log、Eval Summary、Demo Mode。

以下功能第一版不做：周报生成、自动发布回复、平台爬虫、多门店系统、账号系统、移动端、复杂趋势分析、复杂权限系统、LangGraph 多 Agent 编排、长期记忆、外部消息通知、完整 SaaS 后端。

## 5. 产品判断原则

遇到功能取舍时，优先选择：短链路而非大平台；可审批而非全自动；有证据而非自由总结；可演示而非大而全；稳定 Demo 而非复杂技术炫技；简单 Workflow 而非复杂多 Agent。

## 6. 数据约束

**CSV 必填字段**（3 列）：`review_text`、`rating`、`date`

**CSV 可选字段**：`review_id`（不提供则自动生成 UUID）、`platform`、`customer_name`

- `rating` 必须为 1–5 整数，超出范围默认设为 3（中性）
- 空评论不进入分析（标记 `is_empty=1`）
- 重复评论（相同 review_id 或相同 review_text）标记 `is_duplicate=1`
- `rating <= 2` 默认进入差评候选
- 支持编码：UTF-8 / GBK / GB2312 / GB18030 / Latin-1

## 7. LLM 输出与失败处理

LLM 不稳定是预期内情况。所有 agent 输出必须是结构化对象，不得返回自由文本。

LLM 输出不符合 schema 时的处理顺序：
1. Schema Guard 检查
2. 自动重试一次
3. fallback rule（关键字规则 / 评分推断 / 固定模板）
4. 标记 blocked 或记录到 Trace
5. UI 给出可理解状态

不要让 LLM 失败导致页面崩溃。

## 8. Safety Rules

回复草稿不得：
- 攻击顾客或讽刺顾客
- 泄露隐私（电话、地址、身份证号等）
- 编造事实（声称已调查、已查看监控等）
- 承诺无法保证的赔偿（全额退款、现金赔偿等）
- 声称已经处罚员工（开除、罚款等）
- 使用过度营销话术（新品上市、限时优惠等）
- 推卸责任（"是您自己…"、"跟我们无关"等）

不安全回复不得进入可发布状态。`blocked` 的草稿无法批准，`rewrite_required` 的草稿建议修改后再批准。

当前实现：`harness/safety/safety_policy.py`（关键词规则）+ `safety_guardrails.py`（检查逻辑）。

## 9. Evidence Rules

Top 3 问题必须有证据评论绑定。每条洞察至少绑定 2 条有效的 `review_id`。证据不足时标记 `evidence_insufficient`。无证据洞察不可展示在 Dashboard。

insight evidence 必须单独建关联表（`insight_evidence`），不塞进 JSON。原因：便于查询、展示、解释，体现 evidence-grounded 架构。

当前实现：`harness/evidence/evidence_guard.py`。

## 10. Trace Rules

以下步骤必须记录 Trace（`traces` 表）：

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

Trace 每条记录包含：trace_id、batch_id、step_name、status、input_summary、output_summary、latency_ms、model_name、error_message。

## 11. 回复生成原则

AI 回复必须：真诚、克制、不甩锅、不攻击顾客、不承诺无法保证的赔偿、不编造事实、不默认已处罚员工。所有回复必须进入人工审批。

## 12. Harness Engineering 原则

MVP Harness 核心 7 个模块：

| 模块 | 实现位置 |
|------|---------|
| Input Validator | `harness/input/csv_validator.py` |
| Schema Guard | `harness/output/schema_guard.py` |
| Structured Retry | `harness/output/structured_retry.py` |
| Evidence Binding | `harness/evidence/evidence_guard.py` |
| Safety Guardrails | `harness/safety/safety_guardrails.py` |
| Human Approval | `harness/human/approval_gate.py` + `services/reply_service.py` |
| Trace Log | `observability/` + `storage/repositories/trace_repository.py` |

Eval Summary 通过 `evals/eval_runner.py` + `services/eval_service.py` 实现。Confidence Scorer、复杂 Trace Viewer、完整 Eval 平台可以后做。

## 13. Dashboard 原则

Dashboard 只回答四个问题：
1. 本批评论整体情况如何？（总评论数 / 平均评分 / 差评数 / 待审核数）
2. 最严重的三个问题是什么？（Top 3 洞察 + 证据关联）
3. 哪些差评需要处理？（回复审核队列）
4. AI 工作流是否可靠完成？（Harness Engine 状态）

不做复杂 BI，不堆图表。

## 14. Demo Mode 原则

Demo Mode 是一等公民。必须保证：不依赖网络、不依赖 API key、不依赖真实 LLM、能展示完整流程、能用于面试和答辩。

默认启用，使用内置 15 条示例评论（`src/small_shop_agent/demo/sample_reviews.csv`）和预生成的 mock 数据（`mock_classification.json` 等），通过 `MockProvider` 提供确定性输出。

## 15. UI 风格

浅色 SaaS 工作台 + 咖啡店暖色点缀。主色：#2F6B4F / #D99A32 / #F7F6F2 / #FFFFFF。四页面：上传评论、数据看板、回复审核、追踪与评测。

## 16. 开发建议优先级

1. Demo Mode 完整跑通
2. Upload 页面可用
3. Dashboard 可展示
4. Reply Review 可审批
5. Trace & Eval 可展示
6. Live LLM 模式优化
7. 测试和边界补齐

## 17. 代码风格

- 保持函数短小（核心方法 < 50 行，编排器 < 100 行）
- 单文件代码控制在200行，最多不超过300行
- 避免 UI 与业务逻辑混在一起
- 避免硬编码业务数据（魔法数字集中在 `core/config.py`）
- 所有枚举集中管理（`core/enums.py`）
- 所有 prompt 集中管理（`prompts/prompt_registry.py`）
- 所有共享 schema 集中管理（`services/pipeline_steps.py`）
- 对失败路径进行处理，不要裸 except
- 优先保证 MVP 闭环，不做过度抽象

## 18. 判断标准

一次开发任务是否完成，要看：
- 是否符合 MVP 范围
- 是否能在 Demo Mode 下稳定展示
- 是否写入数据库（9 张表完整性）
- 是否写入 Trace
- 是否经过 Schema/Safety/Evidence 检查
- 是否能被 UI 正确展示
- 单元测试通过（`pytest tests/unit/ -v`）
- E2E 验收通过（`python scripts/e2e_demo_check.py`）

## 19. 不要做的事

不要为了"更像 Agent"而引入复杂多 Agent。不要为了"更像 SaaS"而做登录权限。不要为了"更智能"而自动发布回复。不要为了"更完整"而加入周报、爬虫、多门店。不要让项目偏离"差评处理 + 问题复盘 + Harness 闭环"。
