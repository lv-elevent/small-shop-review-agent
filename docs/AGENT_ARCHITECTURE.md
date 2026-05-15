# Agent 系统架构

## 1. 项目定位

**Small Shop Review Agent** — 面向线下小型门店的差评处理与问题洞察 Agentic Workflow 系统。

核心原则：短链路而非大平台，可审批而非全自动，有证据而非自由总结。

## 2. 业务流程

```
CSV 上传 → 校验清洗 → 分类+情绪 → 一致性检查
    → Top 3 问题聚合 → 证据绑定 → 回复草稿
    → 安全检查 → 人工审批 → Dashboard → Trace/Eval
```

## 3. 系统分层架构

```
apps/streamlit_app/          ← UI 层（4 页面 + 组件）
        ↓ 调用
src/small_shop_agent/
├── services/                ← 服务层
├── agent_runtime/           ← Agent Runtime（Graph Runner + 条件路由 + 工具）
├── harness/                 ← 防护体系（输入校验 / Schema Guard / Safety / Evidence / 人工审批）
├── llm/                     ← LLM 层（MockProvider / OpenAIProvider / OllamaProvider）
├── storage/                 ← 存储层（11 张表 + Repository）
├── schemas/                 ← Pydantic 模型
├── prompts/                 ← Prompt 注册表
├── observability/           ← 可观测性（Trace / Eval / Metrics）
└── domain/                  ← 领域常量
```

## 4. Agent Runtime

### 4.1 双引擎

通过 `WORKFLOW_RUNTIME` 配置切换：

| 运行时 | 默认 | 特点 |
|--------|------|------|
| Pipeline | 是 | 线性顺序执行 |
| Agent Graph | 否 | 条件路由 DAG + 异步并发 |

```
Pipeline:  WorkflowService.run_analysis() → 顺序执行 pipeline_steps
Agent Graph: runner.run_with_agent_runtime() → route(state) → next node
```

### 4.2 节点图

```
                    ┌─ classification ─┐
reviews ────────────┤                   ├── consistency ── merge ── insight
                    └─ sentiment ──────┘       │
                                               │ (evidence=0?)
                                               ▼
                                         regenerate_insight
                                               │
                    safety ── reply ◄── mark_insufficient ◄── (重试耗尽)
                      │
                   approval ── END
```

节点定义：`agent_runtime/graph/nodes.py`（15 个节点）
路由逻辑：`agent_runtime/graph/edges.py`（16 个路由函数）

### 4.3 重试与降级

每个 LLM 节点最多 1 次 retry，失败后自动 fallback：
- classification → keyword-based fallback
- sentiment → rating-based fallback
- insights → topic-counting fallback

### 4.4 异步执行

通过 `AGENT_ASYNC_ENABLED=true` 开启，classification 与 sentiment 通过 `asyncio.gather` 并发执行。

## 5. Tool Use

### 5.1 工具层

定义于 `agent_runtime/tools.py`，5 个只读工具：

| 工具 | 数据源 | 用途 |
|------|--------|------|
| `lookup_review` | ReviewRepository | 查询单条评论 |
| `search_reviews` | SQL LIKE | 关键词搜索评论 |
| `count_by_topic` | SQL COUNT | 话题频次统计 |
| `get_batch_stats` | 多源聚合 | 批次统计 |
| `get_safety_policy_snippet` | 内存常量 | 安全政策查询 |

每个工具返回 TypedDict，自动记录 tool_name + latency_ms。

### 5.2 Insight 生成流程

三阶段：工具预查 → LLM 生成 → 证据校验
- Phase 1: `count_by_topic` 收集话题频次，注入 enriched_rows
- Phase 2: `run_insights(enriched_rows)` LLM 生成
- Phase 3: 提取 evidence_review_ids，与 valid_review_ids 交叉校验

### 5.3 Reply 生成流程

三阶段：工具上下文 → LLM 生成 → Schema+Safety Guard
- Phase 1a: `get_safety_policy_snippet("all")` 注入安全规则
- Phase 1b: MemoryRetriever 检索历史审批样本
- Phase 2: `run_reply_drafting(enriched_reviews)` LLM 生成

## 6. Guardrails 体系

### 6.1 双层安全引擎

```
草稿 → Rule Guard (关键词) → blocked? → 直接拦截
         │ pass/rewrite
         ▼
    LLM Semantic Judge → 合并决策
         │
    ┌────┴────┬─────────┐
    pass    rewrite   escalate(human)
```

规则优先：blocked-by-rule 不可被 LLM 覆盖。
定义于 `harness/safety/dual_engine_guard.py`

### 6.2 Schema Guard

所有 LLM 输出经 Pydantic 校验 → 失败自动 retry 1 次 → 失败进入 fallback。
定义于 `harness/output/schema_guard.py` + `structured_retry.py`

### 6.3 Evidence Guard

Top 3 洞察证据须绑定真实 review_id → 无效 ID 过滤 → evidence_insufficient 标记。
定义于 `harness/evidence/evidence_guard.py`

### 6.4 一致性检查

classification 与 sentiment 交叉校验：
- review_id 一致性
- rating/sentiment 冲突检测
- 冲突时下调 confidence，设置 needs_review=True

定义于 `harness/verification/consistency_check.py` + `self_check.py`

## 7. Human-in-the-Loop

```
AI 生成回复 → Safety Check → 人工审批队列
                                  │
                    ┌─────────────┼─────────────┐
                  approve        edit         reject
                    │             │              │
              写入记忆       写入前后记忆     写入记忆
```

审批通过 `ReplyService` (approve/edit/reject)，自动写入 `agent_memories`。

## 8. Memory/RAG

### 8.1 数据模型

```
memory_sources (source_id, batch_id, review_id, reply_id)
     │
     └── agent_memories (memory_id, store_type, memory_type, content, metadata_json, source_id)
           memory_type ∈ {issue_trend, approved_reply, rejected_reply, safety_case}
```

### 8.2 记忆写入

`ReplyService` 审批操作自动写入：
- approve → approved_reply
- edit → before→safety_case + after→approved_reply
- reject → rejected_reply / safety_case

### 8.3 记忆检索

`MemoryRetriever`（关键词 LIKE 匹配）在回复生成时检索：
- 相似 approved_reply（正向参考）
- 相似 rejected_reply（须避免）
- 相关 safety_case（安全警示）

每类最多 3 条，控制 prompt 长度。

## 9. Trace/Eval

### 9.1 Trace 步骤

| 步骤 | step_name | 说明 |
|------|-----------|------|
| 输入校验 | input_validation | CSV schema + 清洗 |
| 分类 | classification | 话题分类 |
| 情绪 | sentiment_analysis | 情绪分析 |
| 一致性检查 | consistency_check | 交叉验证 |
| 问题聚合 | issue_aggregation | Top 3 洞察 |
| 证据绑定 | evidence_check | review_id 校验 |
| 回复草稿 | reply_drafting | 回复生成 |
| 安全检查 | safety_check | 双引擎安全 |
| 人工审批 | human_approval | approve/edit/reject |

### 9.2 Eval 指标

- topic_accuracy：话题分类准确率
- sentiment_accuracy：情绪判断准确率
- schema_failure_count：Schema 校验失败次数
- unsafe_reply_count：不安全回复数量

### 9.3 可靠性指标

- 总延迟 / LLM 延迟
- Schema 重试数 / 降级率
- 安全拦截率 / 人工编辑数
- 记忆命中数 / 不安全漏报数

## 10. LLM Provider

| Provider | 模式 | 依赖 | 说明 |
|----------|------|------|------|
| MockProvider | 内置 | 无 | 15 条预生成数据，确定性输出 |
| OpenAIProvider | live | openai 包 | OpenAI-compatible API |
| OllamaProvider | ollama | requests | 本地 Ollama（qwen/llama3） |

通过 `LLM_MODE` 环境变量切换。

## 11. 数据库（11 张表）

| 表 | 说明 |
|----|------|
| review_batches | 批次元数据 |
| reviews | 评论数据 |
| review_analysis | 分类+情绪结果 |
| insights | Top 3 问题 |
| insight_evidence | 洞察-证据关联 |
| reply_drafts | 回复草稿 |
| approval_actions | 审批日志 |
| traces | 工作流追踪 |
| eval_results | 评测结果 |
| memory_sources | 记忆数据源 |
| agent_memories | 长期记忆 |
