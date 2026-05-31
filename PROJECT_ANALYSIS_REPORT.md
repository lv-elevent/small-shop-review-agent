# 小店评论经营助手 — 项目分析报告

> 面向 AI 应用开发工程师实习生 / AI Agent 开发实习生岗位的技术分析

---

## 1. 项目概览

### 1.1 项目背景

Small Shop Review Response & Insight Agent 是一个面向小型门店（咖啡店、餐厅等）的轻量级 Agentic Workflow 系统。项目解决的核心问题是：**小型门店缺乏专业的评论处理能力**，需要一个自动化的差评分析-回复-审批闭环工具。

### 1.2 技术栈

| 层次 | 技术选型 | 说明 |
|------|---------|------|
| 语言 | Python 3.11+ | 全栈 Python |
| UI 框架 | Streamlit 1.28+ | 4 页 SaaS 工作台 |
| 数据库 | SQLite (WAL 模式) | 轻量持久化，11 张业务表 |
| 数据处理 | pandas 2.0+ | CSV 解析、清洗、校验 |
| 数据校验 | Pydantic 1.10+ | LLM 输出结构化校验 |
| LLM SDK | OpenAI 1.29+ | GPT-4o-mini 等兼容 API 接入 |
| 本地 LLM | Ollama (HTTP API) | 支持 qwen2.5 等本地模型 |
| 日志 | loguru 0.7+ | 结构化日志 |
| 异步 | asyncio | Agent Graph 并发阶段 |
| 测试 | pytest 8.0+ / ruff / mypy | 25 个单元测试 |

### 1.3 项目规模

- **77 个 Python 源文件**，覆盖 7 层架构
- **11 张数据库表**，完整的数据生命周期管理
- **25 个单元测试** + **19 个冒烟测试脚本** + **1 个 E2E 验收脚本**（67 个检查点）
- **15 条内置示例评论**，支持离线确定性演示
- **5 套 Mock JSON 数据**，覆盖分类/情绪/洞察/回复/Trace
- **4 个 Streamlit 页面**：上传评论、数据看板、回复审核、追踪与评测

---

## 2. 技术分析

### 2.1 架构设计

```
CSV 上传 → 分类与情绪 → Top 3 问题 → 回复草稿 → 安全检查 → 人工审批 → Dashboard → Trace/Eval
```

**分层架构**（自上而下）：

```
apps/streamlit_app/       ← UI 展示层（Streamlit 4 页 + 组件库）
src/small_shop_agent/
├── services/              ← 业务服务层（Review/Workflow/Reply/Insight/Eval/Approval）
├── agent_runtime/         ← Agent 运行时（图执行器 / 条件路由 / 状态管理）
│   ├── graph/             ← 工作流图、节点、条件边
│   ├── tools.py           ← Agent 工具集（只读 DB 查询）
│   ├── memory_retriever.py ← 记忆检索器
│   └── runner.py          ← 入口
├── harness/               ← 防护体系（7 组件）
│   ├── input/             ← 输入校验 & 数据清洗
│   ├── output/            ← Schema Guard & Structured Retry
│   ├── evidence/          ← 证据绑定校验
│   ├── safety/            ← 双引擎安全检查（规则 + LLM 语义）
│   ├── human/             ← 人工审批门控
│   └── verification/      ← 一致性校验 & 降级规则
├── llm/                   ← LLM Provider 层（Mock / OpenAI / Ollama）
├── storage/               ← 持久化层（SQLite + 仓库模式）
├── schemas/               ← Pydantic 数据模型
├── prompts/               ← Prompt 注册中心
├── evals/                 ← 评测运行器 & 评分器
├── observability/         ← 可靠性指标收集
├── domain/                ← 领域实体 & 业务常量
└── core/                  ← 配置 & 枚举
```

### 2.2 语言/框架能力覆盖

| 技能维度 | 项目体现 | 行业匹配度 |
|----------|---------|-----------|
| Python 编程 | 77 个源文件，使用类型注解、dataclass、ABC、async/await、装饰器 | ★★★★★ |
| pandas 数据处理 | CSV 多编码读取、数据清洗、缺失值处理、统计聚合 | ★★★★★ |
| Pydantic 数据校验 | 5 个 Schema 类，与 Structured Retry 联动 | ★★★★☆ |
| OpenAI SDK | Chat Completions API，支持自定义 base_url（兼容多平台） | ★★★★★ |
| Prompt 工程 | Prompt 注册中心（7 个场景 Prompt），结构化输出约束 | ★★★★★ |
| SQLite | WAL 模式、外键、迁移脚本、Repository 模式、11 表设计 | ★★★★★ |
| Streamlit | 4 页面 SaaS 工作台、自定义组件、CSS 主题 | ★★★★☆ |
| 异步编程 | asyncio + asyncio.gather 并发执行 classification + sentiment | ★★★☆☆ |
| 测试工程 | pytest + ruff + mypy + 25 单元测试 + E2E 验收 | ★★★★☆ |

### 2.3 LLM 集成深度

项目**同时支持 3 种 LLM 后端**，通过 LLM Router 统一切换：

```
LLM_MODE=demo     → MockProvider（确定性离线数据，零依赖）
LLM_MODE=openai   → OpenAIProvider（GPT-4o-mini 等，OpenAI 兼容 API）
LLM_MODE=ollama   → OllamaProvider（本地部署，如 qwen2.5:7b）
```

**LLM 调用场景**（完整业务流程中的 5 个 LLM 步骤）：

1. **评论分类** (`classify_reviews`) — 识别 topic（卫生/服务/等待时间等 7 个类别）
2. **情绪分析** (`analyze_sentiment`) — 判断 positive/neutral/negative + severity 1-5
3. **问题聚合** (`generate_insights`) — 从差评中聚合 Top 3 问题 + 绑定证据
4. **回复草稿** (`draft_replies`) — 为每条差评生成中文回复
5. **安全检查** (`check_safety`) — 判定 pass/rewrite_required/blocked

**前沿特性 — 语义安全判定** (`judge_semantic_safety`)：
- 在传统关键词规则之上增加 LLM 语义层面的安全判断
- 识别 8 类风险：推卸责任、隐私泄露、编造事实、过度承诺、法律风险、声称处罚员工、语气粗鲁、营销垃圾信息

### 2.4 Agent 概念映射

项目在轻量级工程实践中实现了多个核心 Agent 概念：

| Agent 概念 | 项目实现 | 技术细节 |
|-----------|---------|---------|
| **Tools（工具）** | `agent_runtime/tools.py` | 5 个只读工具：`lookup_review`、`search_reviews`、`count_by_topic`、`get_batch_stats`、`get_safety_policy_snippet`。每个工具返回 TypedDict 确保类型安全，支持 trace 记录 |
| **Memory（记忆）** | `MemoryRetriever` + `MemoryRepository` | 3 种记忆类型（approved_reply / rejected_reply / safety_case），按关键词检索，用于辅助回复生成。审批操作自动写入记忆 |
| **State（状态）** | `AgentState` (dict-based) | 贯穿所有图节点的共享状态字典，包含 reviews、classifications、sentiments、insights、reply_drafts、safety_results、warnings、errors 等字段 |
| **Graph/Workflow（工作流图）** | `agent_runtime/graph/` | 9 个主节点 + 5 个 fallback/retry 节点 + 15 条条件路由边。支持同步和异步（`asyncio.gather` 并发）两种执行模式 |
| **Routing（路由）** | `agent_runtime/graph/edges.py` | 15 个路由函数，基于状态做条件跳转（空结果 → 重试 → fallback；证据不足 → 标记 → 继续） |
| **Harness（防护）** | `harness/` 7 模块 | Schema Guard + Structured Retry + Evidence Binding + Safety Guardrails（双引擎） + Human Approval + Consistency Check + Fallback Rules |
| **Observability（可观测性）** | `observability/metrics.py` | 聚合 10+ 可靠性指标：总延迟、LLM 延迟、schema 重试次数、fallback 率、安全拦截率、人工编辑率、记忆命中率、不安全逃逸数 |

**Agent 熟练度状态机**（通过条件路由实现）：
```
                 ┌──────────────┐
                 │ 正常流程通过  │──→ 下一步
                 └──────────────┘
                        │
                 ┌──────▼──────┐
                 │  结果为空？  │──→ 重试（最多 1 次）
                 └──────────────┘
                        │
                 ┌──────▼──────┐
                 │  重试仍空？  │──→ Fallback（规则降级）
                 └──────────────┘
                        │
                 ┌──────▼──────┐
                 │ 证据校验失败 │──→ 重新生成洞察
                 └──────────────┘
                        │
                 ┌──────▼──────┐
                 │  再次失败？  │──→ 标记 evidence_insufficient
                 └──────────────┘
```

---

## 3. 工程实践与方法论

### 3.1 防护体系工程（Harness Engineering）

这是项目最大的技术亮点 — 围绕 LLM 输出构建了完整的 **7 层防护体系**：

| 防护层 | 功能 | 工程策略 |
|--------|------|---------|
| **Input Validator** | CSV 格式校验/评分范围检查/空值检测/重复检测 | 多编码兼容（6 种编码），规则引擎 |
| **Schema Guard** | Pydantic 校验 LLM 输出，不抛异常，返回结构化结果 | 每个 item 独立校验，部分失败不影响整体 |
| **Structured Retry** | Schema 校验失败 → 重试 1 次 → 失败 → fallback | 最多 2 次 LLM 调用，每次记录 attempt 序号 |
| **Evidence Guard** | 验证每条洞察是否绑定 ≥2 条真实 review_id | 自动检测 evidence 字段格式（兼容 3 种格式） |
| **Safety Guardrails** | 关键词双引擎安全检查（规则 + LLM 语义） | blocked/rewrite_required 两级拦截，不一致时人工升级 |
| **Consistency Check** | 交叉验证分类↔情绪一致性 + 评分↔情绪冲突检测 | 检测到冲突时自动降级 confidence（×0.5） |
| **Human Approval** | safety_status=blocked 的草稿不可批准 | 审批操作记录完整审计 Trail（before/after 文本） |

### 3.2 Safety Guardrails 双引擎架构

```
输入：回复草稿
        │
   ┌────▼────┐
   │ 规则引擎  │ ← 中英文关键词匹配（~100 个关键词，6 个类别）
   │ (关键词)  │   blocked：攻击/隐私/处罚员工/编造事实
   └────┬────┘   rewrite_required：赔偿承诺/营销/推卸责任
        │
   ┌────▼────┐
   │ 状态判断  │
   └────┬────┘
        │
   ┌────▼────────────┐
   │ pass/rewrite？    │
   │ → 调用语义判定    │ ← LLM 深度语义分析（8 类风险）
   │ blocked → 跳过    │   返回 confidence 分
   └────┬────────────┘
        │
   ┌────▼────┐
   │ 合并规则  │ ← 规则 blocked 优先
   │ & 语义    │ ← 双引擎一致 → 确定结果
   │           │ ← 双引擎冲突 → human_escalation（人工介入）
   └──────────┘
```

### 3.3 失败处理策略

项目对 LLM 的不确定性做了系统性的防御：

```
LLM 调用
    ↓
Schema Guard (Pydantic 校验)
    ↓ 失败
自动重试 (1 次)
    ↓ 仍失败
Fallback 规则引擎 (关键词/评分推断/固定模板)
    ↓
标记 trace → 不阻塞流程 → UI 可见状态
```

**三层 fallback**：
1. **分类 fallback**：关键词匹配（6 组规则覆盖中英文）
2. **情绪 fallback**：评分推导（rating≤2→negative, =3→neutral, ≥4→positive）
3. **回复 fallback**：固定中文模板（真诚致歉 + 承诺改进）

### 3.4 Prompt 工程

- **集中管理**：所有 Prompt 在 `prompt_registry.py` 统一注册（7 个场景）
- **结构化输出强制**：每个 Prompt 都明确要求 "只返回 JSON 数组，不要 markdown、不要解释、不要代码块"
- **中英文混合**：系统 Prompt 使用中文（业务场景），但 topic key 使用英文（便于数据库索引）
- **证据约束**：洞察 Prompt 明确要求 "每条证据必须引用输入中真实存在的 review_id"
- **安全前置**：回复 Prompt 内嵌 7 条行为准则（不甩锅、不攻击、不编造等）

### 3.5 数据工程

- **多编码兼容**：UTF-8 / UTF-8-SIG / GBK / GB2312 / GB18030 / Latin-1 自动检测
- **数据清洗**：空白规范化、NaN 处理、自动 review_id 生成（UUID）
- **验证统计**：total_rows / valid_review_count / duplicate_count / empty_review_count / invalid_rating_count / schema_error_count
- **异常值处理**：rating 超出 1-5 范围 → 默认设为 3（中性），满足 DB CHECK 约束

### 3.6 可观测性

`observability/metrics.py` 提供完整的可靠性指标：

- **延迟指标**：总延迟、LLM 调用延迟
- **质量指标**：Schema 重试次数、Fallback 率、安全拦截率、不安全逃逸数
- **人工效率**：人工编辑率
- **记忆价值**：记忆命中率（从历史审批中检索到的有用模式比例）

### 3.7 测试策略

```
测试金字塔
    ┌──────────────┐
    │  E2E 验收 ×1  │  scripts/e2e_demo_check.py（67 个检查点，覆盖 11 张表）
    ├──────────────┤
    │ 冒烟测试 ×19  │  scripts/smoke_test_*.py（服务、工作流、UI 页面数据）
    ├──────────────┤
    │ 单元测试 ×25  │  tests/unit/test_*.py（防护组件、服务、Agent 路由/工具）
    └──────────────┘
```

E2E 脚本特别值得关注：它从头创建隔离数据库、上传 CSV、执行完整工作流、逐项验证 11 张表的数据完整性、执行审批流程、运行评测、最后清理数据库。是一个完整的一键验收工具。

---

## 4. 亮点与成果提炼

### 4.1 核心架构亮点

| 亮点 | 技术价值 | 行业匹配 |
|------|---------|---------|
| **Agentic Workflow 架构** | 实现了图节点 + 条件路由 + 状态管理的 Agent 运行时，支持 sync/async 双模式 | 直接对标 Agent 开发岗位的核心能力要求 |
| **7 层防护体系（Harness）** | 围绕 LLM 非确定性的系统性工程防御，是生产级 AI 系统的关键特征 | 体现 AI 系统落地能力 |
| **双引擎安全架构** | 规则 + LLM 语义双层安全检查，冲突时人工升级 | GPT-4 级安全对齐实践 |
| **Prompt 工程体系** | 7 个场景 Prompt 集中管理，结构化输出强制，可版本化、可 A/B 测试 | 大模型应用核心技能 |
| **LLM 多后端支持** | Mock/OpenAI/Ollama 三模式，通过 Router 统一切换 | 体现工程抽象能力 |
| **记忆系统（Memory）** | 审批操作自动沉淀为记忆，在回复生成时关键词检索，辅助 LLM 决策 | 对标 Agent 记忆/上下文管理 |
| **结构化输出 + 重试 + Fallback** | Schema Guard → Structured Retry → Fallback 三级防御 | LLM 可靠性工程的最佳实践 |

### 4.2 工程实践亮点

- **数据库设计**：11 张表的完整数据生命周期（review_batches → reviews → review_analysis → insights → insight_evidence → reply_drafts → approval_actions → traces → eval_results → memory_sources → agent_memories）
- **代码质量**：函数短小（核心 <50 行，编排 <100 行），UI 与业务分离，5 个 Pydantic Schema 保证类型安全
- **E2E 自动化**：一键运行 `python scripts/e2e_demo_check.py` 即可完成 67 个检查点的完整验收

### 4.3 量化成果（Mock 数据非生产环境）

| 指标 | 数据 |
|------|------|
| 评论处理能力 | 15 条评论 → 13 条有效（检出 1 条空、1 条重复） |
| 差评识别 | 5 条差评候选（rating≤2） |
| 洞察生成 | Top 3 问题（卫生/服务/等待时间） |
| 回复生成 | 5 条草稿，其中 1 条 blocked、1 条 rewrite_required |
| 证据绑定 | 5 条证据（每条洞察绑定 ≥2 条 review_id） |
| Trace 记录 | 9 个步骤完整记录 |
| 评测维度 | Topic 准确率、Sentiment 准确率、Unsafe 检出、Schema 稳定性 |
| 审批流程 | 支持 approve / edit / reject，审批操作自动写入记忆 |

---

## 5. 改进建议（AI/Agent 实习岗位视角）

### 5.1 技术增强方向

1. **工具调用（Function Calling）**：当前 tools.py 中的工具是代码直接调用的，可以改造为 OpenAI Function Calling 格式，让 LLM 自主决定调用哪些工具 → **直接对标 Agent 工具使用能力**

2. **多步推理链（Chain-of-Thought）**：在洞察生成和回复草稿步骤引入显式的推理链，记录中间推理步骤 → **提升可解释性**

3. **Prompt 版本管理与 A/B 测试**：当前 Prompt 已集中管理，但缺少版本追踪和效果对比机制 → **增加工程严谨性**

4. **增量学习闭环**：审批结果反馈给 LLM（类似 RLHF），当前记忆系统只做检索不做微调 → **体现持续学习能力**

5. **流式输出**：Streamlit + SSE 实现的打字机效果 → **提升用户体验**

6. **Docker 化部署**：增加 Dockerfile 和 docker-compose → **体现部署优化能力**

### 5.2 架构演进方向

7. **LangGraph/LangChain 集成**：当前自研图执行器功能完整，但缺少生态集成（检查点、持久化、可视化）→ **行业标准工具经验**

8. **多 Agent 协作**：分类 Agent + 情绪 Agent + 回复 Agent + 审核 Agent 各自独立 → **体现 Multi-Agent 设计能力**（但需注意项目定位为"简单 Workflow 而非复杂多 Agent"）

9. **长期记忆外化**：当前记忆在 SQLite 中，可扩展至向量数据库（Chroma/Qdrant） → **体现 RAG 经验**

---

## 6. 总结

该项目是一个**完整度很高的 AI Agent 应用实践**，在以下维度上直接匹配 AI 应用/Agent 开发岗位的核心要求：

- **LLM 集成**：3 种 Provider，完整业务流程中 5 个 LLM 步骤
- **Prompt 工程**：7 个场景 Prompt 集中管理，结构化输出约束
- **Agent 架构**：图节点 + 条件路由 + 状态管理 + 工具调用 + 记忆检索
- **工程化**：7 层防护体系，Schema Guard，结构化重试，fallback 降级
- **安全对齐**：双引擎安全检查（规则 + 语义），人工审批门
- **可观测性**：Trace 记录 + 可靠性指标 + Eval 评测
- **工程规范**：类型注解、测试覆盖、E2E 自动化验收

从 AI 应用开发工程师实习生的角度看，这个项目展示了**从 Pipeline 到 Agentic Workflow 的完整演进路径**，具备较强的工程展示价值。
