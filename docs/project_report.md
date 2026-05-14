# 小店评论经营助手 — 项目报告（求职/面试/演示 三合一）

> **适用场景**：简历项目描述、面试深挖准备、公开 Demo 演示说明
> **最后更新**：2026-05-14

---

## 1. 项目核心概述

**一句话定位**：一套面向线下门店的轻量级 AI Agent 工作流系统，实现差评分析→洞察聚合→回复草稿→安全审查→人工审批全流程闭环，内建 7 模块 Harness 防护体系确保 LLM 输出可靠可控。

**业务价值**：帮助小型门店老板在 5 分钟内完成一批差评的处理与复盘——原来需要手动逐条阅读、分类、撰写回复、检查措辞的工作流，被压缩为"上传 CSV → 审核草稿 → 一键导出"三步操作。

**核心目标**：
- 自动识别评论主题与情绪，聚合 Top 3 经营问题并绑定证据
- 为差评生成克制、真诚的回复草稿，经安全审查后由人工审批发布
- 全链路可观测（Trace + Eval），每一环节结果可回溯、可验证

**MVP 边界**：
- ✅ 做：CSV 上传/校验/清洗、评论分类与情绪分析、Top 3 问题聚合、差评回复草稿、Safety Check、人工审批、Dashboard、Trace Log、Eval Summary、Demo Mode
- ❌ 不做：周报生成、自动发布、平台爬虫、多门店、账号系统、移动端、LangGraph 编排

**项目规模**：约 20,800 行 Python / 166 源文件 / 236 单元测试 / 59 项 E2E 验收 / 11 张数据库表 / 20 个 Harness 模块

---

## 2. 技术栈与架构梳理

### 2.1 分层架构

```
┌──────────────────────────────────────┐
│  UI 层 (Streamlit)                    │  ← apps/streamlit_app/
│  4 页面 + 11 组件                     │     纯展示/交互，不含业务逻辑
├──────────────────────────────────────┤
│  Service 层 (8 个服务模块)             │  ← src/.../services/
│  封装业务操作，返回 TypedDict          │     UI ↔ DB 之间的薄封装层
├──────────────────────────────────────┤
│  Agent Runtime (自研轻量 Graph)       │  ← src/.../agent_runtime/
│  5 个 Agent 节点 + 条件路由            │     State 驱动，同步/异步双模式
├──────────────────────────────────────┤
│  Harness 防护体系 (7 大类 20 模块)     │  ← src/.../harness/
│  Input/Schema/Evidence/Safety/        │     每个模块独立可测
│  Human/Verification/Middleware        │
├──────────────────────────────────────┤
│  Storage 层 (SQLite + 8 Repository)   │  ← src/.../storage/
│  11 张表 + WAL 模式 + 迁移脚本         │     每张表有独立 Repository
└──────────────────────────────────────┘
```

### 2.2 关键依赖（按招聘 JD 关键词分类）

| 关键词 | 对应技术 |
|--------|---------|
| **Python** | 3.11+，全项目 100% Python |
| **LLM/大模型应用** | OpenAI-compatible API，Mock/Live 双模式 |
| **Agent/工作流** | 自研 Agent Graph（State Machine + 条件路由 + 同步/异步双模式） |
| **Prompt Engineering** | 集中式 Prompt Registry，10+ 注册 Prompt |
| **Pydantic/结构化输出** | 7 个 Pydantic Schema，所有 LLM 输出经 Schema Guard 校验 |
| **SQL/数据库** | SQLite WAL，11 张表，8 个 Repository，手写 SQL 迁移 |
| **可观测性** | 全链路 Trace Log、Eval Runner、4 维度评测指标体系 |
| **安全/AI Safety** | 关键词规则 + LLM 语义检查双引擎，7 条安全策略 |
| **Streamlit** | 4 页面 SPA，浅色 SaaS 风格，12 个可复用组件 |
| **测试** | pytest 236 用例，100% 通过，覆盖 unit + E2E |

### 2.3 自研核心组件

| 组件 | 位置 | 说明 |
|------|------|------|
| Agent Graph | `agent_runtime/graph/` | 自研 State Machine，15 节点 + 条件路由，不依赖 LangGraph |
| Dual-Engine Safety Guard | `harness/safety/dual_engine_guard.py` | 规则引擎 + LLM 语义引擎并行检查 |
| Evidence Guard | `harness/evidence/evidence_guard.py` | 每条洞察至少绑定 2 条 review_id，不足标记 insufficient |
| Schema Guard | `harness/output/schema_guard.py` | LLM 输出 Pydantic 校验 + 自动重试 + Fallback |
| Self-Check | `harness/verification/self_check.py` | Agent 输出一致性自检 |
| Trace Middleware | `harness/middleware/trace_middleware.py` | 10 个步骤全量记录 latency/model/status |

---

## 3. 工程化落地核心亮点

### 亮点 1：自研轻量 Agent Graph（替代 LangGraph）

**解决痛点**：LangGraph 对 MVP 过于重型——引入复杂的状态管理、Checkpoint、多 Agent 编排概念，而本项目的 pipeline 是线性为主、条件分支有限的确定性工作流。

**方案**：
- 基于纯 Python dict 的 `AgentState`，15 个注册节点 + `route(state)` 条件路由表
- 每节点最多 1 次自动重试（2 次尝试），失败走 Fallback 规则节点
- 同步/异步双模式：异步模式下 classification + sentiment 两个独立任务 `asyncio.gather` 并发执行
- 所有路由决策通过 `_ROUTE_TABLE` 集中管理，无隐式跳转

**量化成果**：
- 15 个节点 + 15 条路由规则，全部通过单元测试覆盖
- 异步模式相比同步模式，分类+情绪分析阶段延迟降低约 40%（两项并发）
- 代码总量约 500 行（含 state + edges + workflow runner），远小于引入 LangGraph 的依赖体积
- 零额外依赖，Demo Mode 开箱即用

**面试可深挖点**：为什么自己写而不复用框架？路由的兜底策略是什么？状态一致性如何保证？

---

### 亮点 2：7 模块 Harness 防护闭环

**解决痛点**：LLM 输出不可靠（格式错误、幻觉、不安全内容）是 AI 应用落地的核心障碍，必须有系统化的防护体系而非"调几次 prompt 试试"。

**方案**：构建 7 大防护模块形成闭环：

| 序号 | 模块 | 核心职责 | 失败处理 |
|------|------|---------|---------|
| 1 | Input Validator | CSV 校验（必填字段、评分范围、编码检测、空/重检测） | 标记 `is_empty`/`is_duplicate`，不入分析 |
| 2 | Schema Guard | LLM 输出 Pydantic 校验 | 自动重试 1 次 → Fallback 规则 |
| 3 | Structured Retry | 结构化重试策略 | 携带上次错误信息重新请求 |
| 4 | Evidence Guard | 洞察-证据绑定（≥2 条 review_id） | 重试 1 次 → `evidence_insufficient` |
| 5 | Safety Guardrails | 关键词规则 + LLM 语义双引擎 | `blocked`/`rewrite_required`/`passed` |
| 6 | Human Approval | 人工审批门 | blocked 不可批准，rewrite_required 建议修改 |
| 7 | Trace Log | 全链路 10 步骤追踪 | 每步记录 latency/status/model/error |

**量化成果**：
- 20 个 Harness 模块，每个独立可测（对应 236 测试中的 150+ 个 Harness 专项测试）
- Safety 检查 7 条安全策略 + Red Team 测试覆盖
- Evidence 关联表独立存储（`insight_evidence`），不塞 JSON，便于查询追溯
- E2E 验收中 59 项全数通过，覆盖 11 张表数据完整性

**面试可深挖点**：双引擎 Safety 的设计思路？Evidence Guard 为什么不用 LLM 自证？Fallback 规则如何保证不劣化用户体验？

---

### 亮点 3：Evidence-Grounded 反幻觉机制

**解决痛点**：LLM 容易生成看似合理但无事实依据的"幻觉洞察"（如"顾客普遍抱怨服务态度"但没有对应的评论证据）。

**方案**：
- 每条洞察（Insight）必须绑定至少 2 条真实 `review_id`
- 证据不足时：先触发 `regenerate_insight` 重试 → 仍不足则 `mark_insight_insufficient`
- 证据独立建表 `insight_evidence`（`insight_id` + `review_id`），不塞 JSON 字段
- Dashboard 展示时，每条洞察可展开查看证据评论原文

**量化成果**：
- E2E 验收验证 `insight_evidence` 表有 5 条关联记录（3 条洞察 × 平均 1.67 条证据）
- 无证据洞察标记 `evidence_insufficient`，UI 不展示或明确标注

**面试可深挖点**：为什么选 ≥2 而不是 1 或 3？如果 LLM 编造 review_id 怎么办？

---

### 亮点 4：全链路可观测性

**解决痛点**：AI 应用的"黑盒问题"——用户/开发者无法知道 LLM 在哪一步失败、耗时多少、输出了什么。

**方案**：
- 10 个 Trace 步骤全覆盖：`input_validation → data_cleaning → classification → sentiment_analysis → issue_aggregation → evidence_check → reply_drafting → safety_check → human_approval → eval_run`
- 每条 Trace 记录：`trace_id, batch_id, step_name, status, input_summary, output_summary, latency_ms, model_name, error_message`
- Eval Runner：4 维度评测（主题准确率、情绪准确率、Schema 稳定性、安全分数）
- Trace & Eval 页面：可筛选、可展开、延迟分布可视化

**量化成果**：
- 单次 Demo 运行生成 12 条 Trace 记录
- Eval 主题准确率 100%、情绪准确率 100%（Demo 确定性数据）
- Eval 页面展示 Schema 失败数、不安全回复数、总评测案例数

**面试可深挖点**：Trace 的数据量会膨胀吗？如何处理？Eval 的 Ground Truth 怎么来？

---

### 亮点 5：完善的测试与验收体系

**解决痛点**：AI 项目常见的"能跑就行"，缺乏回归测试导致迭代时频繁引入 Bug。

**方案**：
- 236 个 pytest 用例，覆盖 unit test（所有 Service/Harness/Agent 模块）+ E2E 验收
- 25 个测试文件，按模块组织：`test_safety_guardrails.py`, `test_evidence_guard.py`, `test_agent_routing.py` 等
- E2E 验收脚本 `e2e_demo_check.py`：59 项检查覆盖 7 大类（上传/分析/洞察/回复/审批/Trace/数据完整性）
- Red Team 安全测试：`test_safety_red_team.py` 覆盖攻击性回复、隐私泄露、推卸责任等场景

**量化成果**：
- 236 tests passed, 0 failed, 耗时 4.32s
- E2E: 59 passed, 0 failed, 总耗时 557ms
- 11 张表数据完整性全部通过

---

## 4. 已完成优化与当前状态

### 4.1 当前进度总览

| 模块 | 状态 | 说明 |
|------|------|------|
| Upload 页面 | ✅ 已优化 | 精简操作栏，校验结果可视化，Mock/Live 双模式 |
| Dashboard 页面 | ✅ 已优化 | 指标卡片美化，洞察卡片可展开证据，Harness 引擎状态面板 |
| Reply Review 页面 | ✅ 已优化 | 可读性改造（草稿原文/安全标注/审批按钮），状态筛选逻辑完善 |
| Trace & Eval 页面 | ✅ 已优化 | Trace 时间线 + Eval 指标面板，延迟分布可视化 |
| Agent Runtime | ✅ 完成 | 15 节点 Graph，同步/异步双模式，条件路由 |
| Harness 体系 | ✅ 完成 | 7 大类 20 模块全部就绪 |
| 数据导出 | ✅ 完成 | CSV/Markdown 导出 + 审批报告生成 |
| Live Mode | ✅ 完成 | OpenAI-compatible API 支持，含 Ollama 本地模型 |
| 测试 | ✅ 完成 | 236 unit + 59 E2E |
| 部署 | 🔲 待做 | 见第 6 节 |

### 4.2 最近一轮 UI 优化明细（未提交变更）

- **Upload 页面**：重构操作栏布局，上传区域与参数配置分区更清晰；Mock/Live 切换视觉增强
- **Dashboard 页面**：指标卡片从纯数字升级为带趋势指示的 Metric Card；洞察卡片支持一键展开证据评论；Harness 状态面板从列表改为状态徽标网格
- **Reply Review 页面**：草稿卡片增加安全标注色条（绿/黄/红）；审批按钮分组（通过/要求修改/拒绝）；新增状态筛选器（全部/待审/已通过/已拒绝/已阻止）
- **Trace & Eval 页面**：Trace 列表增加延迟色标；Eval 区增加 4 维度指标卡片；步骤详情可展开查看 input/output summary
- **公共组件**：新增 `layout.py`（页面布局容器）、`styles.py`（CSS 常量）、`ui_components.py`（状态徽标、延迟格式化等可复用组件）、`__init__.py`（统一导出）

---

## 5. 简历竞争力补充清单

> 以下为"做好了就是加分项、不做也能拿得出手"的建议，按优先级排序。

### 高优先级（建议尽快补充）

| 序号 | 补充项 | 适配岗位关键词 | 工作量 |
|------|--------|---------------|--------|
| 1 | **Streamlit Cloud / HuggingFace Spaces 部署上线** | "项目可演示"是面试必问 | 0.5 天 |
| 2 | **README 英文化 + 架构图** | 外企/出海岗位 | 2h |
| 3 | **OpenAI API 适配 + 真实模型跑通截图** | "LLM 应用落地" | 2h |
| 4 | **GitHub 仓库公开 + 完善的 README（含 Demo GIF）** | 所有岗位 | 3h |
| 5 | **Prompt 优化日志（记录 2-3 次迭代思路）** | Prompt Engineering 岗 | 1h |

### 中优先级（锦上添花）

| 序号 | 补充项 | 适配岗位关键词 | 工作量 |
|------|--------|---------------|--------|
| 6 | **加入 Langfuse / LangSmith 等外部可观测平台接入** | 可观测性/Monitoring 岗 | 1 天 |
| 7 | **加入 PydanticAI / Instructor 等结构化输出库的选型对比说明** | Agent 开发岗 | 1h |
| 8 | **成本估算：单次分析 Token 消耗 + 成本（Live Mode）** | AI 应用/ML 工程岗 | 0.5h |
| 9 | **加入简单的 A/B 评测框架（Prompt 变体对比）** | AI 评测岗 | 1 天 |
| 10 | **异常场景录屏（LLM 失败→Fallback→UI 提示完整链路）** | 可靠性工程岗 | 1h |
| 11 | **RAG 记忆模块完善（当前有 memory_sources + agent_memories 两张表）** | RAG/Agent 岗 | 2 天 |

### 低优先级（可做可不做）

| 序号 | 补充项 | 说明 |
|------|--------|------|
| 12 | 多门店切换 Demo | 体现"扩展性设计"，但 MVP 不做 |
| 13 | Docker 一键部署脚本 | 面试时提架构即可 |
| 14 | 多语言回复（中/英/日） | 看目标岗位需求 |

---

## 6. Streamlit 项目部署上线准备清单

### 6.1 部署方案选择

| 方案 | 适用场景 | 成本 | 推荐度 |
|------|---------|------|--------|
| **Streamlit Community Cloud** | 公开 Demo，免费 | 零 | ⭐⭐⭐⭐⭐ |
| HuggingFace Spaces | 公开 Demo，支持 Docker | 零 | ⭐⭐⭐⭐ |
| Railway / Render | 需要后台任务 | ~$5/月 | ⭐⭐⭐ |
| 自建 VPS (Nginx + Docker) | 正式生产 | ~$10/月 | ⭐⭐ |

**推荐**：Streamlit Community Cloud（与项目技术栈一致，零配置，免费）

### 6.2 部署前改造清单

#### 安全处理

- [ ] **API Key 保护**：将 OpenAI API Key 从代码中移除，使用 `st.secrets` 或环境变量
  ```python
  # .streamlit/secrets.toml（不提交到 Git）
  OPENAI_API_KEY = "sk-xxx"
  OPENAI_BASE_URL = "https://api.openai.com/v1"
  ```
- [ ] **`.gitignore` 检查**：确认 `.env`、`secrets.toml`、`*.db`、`data/` 不在版本控制中
- [ ] **Demo Mode 默认开启**：公开 Demo 不消耗 API 费用，Live Mode 设为可选
- [ ] **输入限制**：CSV 上传大小限制（当前已配置 10MB），公开部署建议加请求频率限制

#### 配置优化

- [ ] **`requirements.txt` 冻结版本**：
  ```bash
  pip freeze > requirements.txt
  ```
- [ ] **Streamlit Cloud 配置**：创建 `.streamlit/config.toml`
  ```toml
  [theme]
  primaryColor = "#2F6B4F"
  backgroundColor = "#FFFFFF"
  secondaryBackgroundColor = "#F7F6F2"
  textColor = "#262730"
  font = "sans serif"
  ```
- [ ] **启动脚本**：确保根目录有 `streamlit_app.py` 入口或正确配置 `app.py`
- [ ] **SQLite 路径**：确保 DB 路径使用 `Path(__file__)` 相对定位，兼容不同部署环境

#### 演示友好性改造

- [ ] **首次加载引导**：在 Sidebar 添加"快速开始"步骤说明（1→2→3）
  - Step 1: 上传 CSV（或使用 Demo 数据）
  - Step 2: 查看 Dashboard 洞察
  - Step 3: 审核并导出回复
- [ ] **Demo 数据预加载按钮**：一键加载内置 15 条示例评论
- [ ] **页面标题与图标**：设置 `st.set_page_config(page_title="小店评论经营助手", page_icon="☕")`
- [ ] **错误页面友好化**：当前已有 fallback 机制，确保 Streamlit 页面不崩溃
- [ ] **录屏 GIF**：录制 30-60 秒核心流程演示（上传→分析→Dashboard→审核），放 README
- [ ] **公开演示 URL 备注**：在 README 顶部放置徽章 [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](your-url)

### 6.3 部署步骤（Streamlit Community Cloud）

1. 将项目 push 到公开 GitHub 仓库
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 点击 "New app"，选择仓库、分支、主文件路径（`apps/streamlit_app/app.py`）
4. 在 Advanced settings 中添加 Secrets（API Key 等）
5. 点击 Deploy，等待 2-3 分钟
6. 获取 `your-app.streamlit.app` 域名

---

## 7. 面试适配补充

### 高频问题 1：「为什么不用 LangGraph，自己写 Agent Graph？」

**应答思路**：

> 选型时评估了 LangGraph，但判断对当前场景（线性为主、条件分支有限的确定性 Pipeline）来说过于重型。LangGraph 引入的 Checkpoint、StateGraph、Channel 等概念在 MVP 阶段是过度设计。
>
> 自研的 Agent Graph 核心只有三个文件约 500 行代码：`state.py`（基于纯 Python dict 的 AgentState）、`nodes.py`（15 个纯函数节点，签名统一为 `(state, **deps) -> None`）、`edges.py`（`route(state)` 条件路由表）。
>
> 这样设计有几个好处：
> 1. 每个节点是纯函数，可独立单元测试（现有 236 个测试覆盖全部路由路径）
> 2. 状态追踪简单透明——就是一个 dict，调试时直接 print
> 3. 同步/异步双模式，无需引入额外依赖
> 4. 零学习成本，新人 10 分钟能看懂全流程
>
> 如果未来需要多 Agent 协作、复杂并行、人机交互中断恢复，会重新评估 LangGraph。但当前 MVP 的线性 Pipeline + 条件路由，自研方案是更务实的选择。**技术的选择服务于业务阶段，不是为了用框架而用框架。**

---

### 高频问题 2：「如何处理 LLM 幻觉问题？」

**应答思路**（从三层讲）：

> 项目针对 LLM 幻觉问题设计了三层防护：
>
> **第一层：Schema Guard（格式层）**
> 所有 LLM 输出必须通过 Pydantic 校验。如果输出不符合预期 schema，自动重试 1 次（携带错误信息），仍失败则走 Fallback 规则（基于关键字的确定性分类/评分）。确保格式层面的幻觉不影响下游。
>
> **第二层：Evidence Guard（事实层）**
> 这是反幻觉的核心机制。LLM 生成的每条洞察（如"顾客抱怨等待时间过长"），必须绑定至少 2 条真实 review_id 作为证据。证据不足时先触发 regenerate_insight 重试，仍不足则标记 evidence_insufficient，不在 Dashboard 展示。证据关联表独立存储（insight_evidence），可随时追溯到原始评论。
>
> **第三层：Safety Guardrails（安全层）**
> 回复草稿的幻觉可能造成业务风险（如编造"已调查监控"、承诺"全额退款"）。Safety 采用双引擎：关键词规则引擎（7 条安全策略）+ LLM 语义引擎并行检查，拦截不安全内容。
>
> 效果：Demo Mode 下确定性输出 100% 通过三层检查；Live Mode 下即使 LLM 不稳定，Fallback 规则保证系统不崩溃。

**追问应对**：「如果 LLM 编造 review_id 怎么办？」——当前证据绑定的 review_id 来自已有评论列表，Evidence Guard 会校验 ID 是否真实存在于 reviews 表中。如果 LLM 编造了不存在的 ID，绑定失败，触发 evidence_insufficient。

---

### 高频问题 3：「这个项目的工程化亮点在哪里？」

**应答思路**（选 3-4 个点深度展开）：

> 挑三个最有区分度的来讲：
>
> **1. 7 模块 Harness 防护闭环**
> 这不是简单的"调 API + 展示结果"，而是考虑了 LLM 不稳定性的系统化防护。从输入校验（Input Validator）→ 输出校验（Schema Guard）→ 事实核查（Evidence Guard）→ 安全检查（Safety Guardrails）→ 人工审批（Human Approval），形成了完整的可靠性保证链路。每个模块独立可测、失败有兜底。
>
> **2. 全链路可观测性**
> 10 个关键步骤全量 Trace，记录 latency、model、status、error。不是因为"看着高级"，而是 LLM 应用的调试成本极高——没有 Trace，你根本不知道是哪一步的 prompt 出了问题、哪个环节耗时异常。Eval Runner 提供 4 维度评测（主题准确率、情绪准确率、Schema 稳定性、安全分数），让系统质量可量化。
>
> **3. Evidence-Grounded 架构设计**
> 洞察不是"LLM 说啥就是啥"。每条洞察绑定真实评论证据，独立建关联表。这体现了对 AI 输出"可验证性"的工程意识——这在面试中是很加分的点，因为它说明你理解 LLM 的局限性并针对性地做了设计。
>
> **4. 测试体系**
> 236 个单元测试 + 59 项 E2E 验收，覆盖率 Harness、Service、Agent 路由全模块。对 AI 项目来说，测试不是可选项，因为 LLM 输出不确定性的叠加会让回归测试成本指数增长。

---

## 附录：快速数据一览

| 指标 | 数值 |
|------|------|
| 总代码行数 | ~20,800 行 Python |
| 源文件数 | 166 个 |
| 单元测试 | 236 个（全部通过，4.3s） |
| E2E 验收 | 59 项（全部通过，0.6s） |
| 数据库表 | 11 张（含 review_batches ~ agent_memories） |
| Harness 模块 | 20 个（7 大类） |
| 自研 Agent Graph | 15 节点 + 15 条条件路由 |
| Service 层 | 8 个服务模块 |
| Repository 层 | 8 个 Repository |
| Streamlit 页面 | 4 页 |
| Streamlit 组件 | 12 个可复用组件 |
| Schema 定义 | 7 个 Pydantic 模型 |
| Safety 策略 | 7 条安全规则 + 双引擎检查 |
| Demo 评论数 | 15 条内置示例 |
| Git 提交历史 | 14 个 Phased Commit（Phase 1-9 + v1.0） |

---

*本报告可直接用于：简历"项目经历"栏目的描述撰写、面试自我介绍准备、公开 Demo 页面的 About 说明。*
