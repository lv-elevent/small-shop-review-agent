# MVP_TASKS.md

## 阶段 0：项目初始化

目标：搭建项目骨架，不写复杂业务。

任务：

- 创建项目目录结构；
- 创建 docs 文档目录；
- 放入 UI mockup 图片；
- 配置 requirements.txt；
- 配置 .env.example；
- 创建 README.md；
- 创建 AGENT.md 和 CLAUDE.md；
- 准备 sample_reviews.csv；
- 准备 eval_reviews.jsonl；
- 准备 mock_outputs。

验收标准：

- 项目可以被开发者快速理解；
- 文档目录完整；
- Demo 数据存在；
- 不依赖真实 LLM 也能知道要实现什么。

## 阶段 1：数据接入与校验

目标：完成 CSV 上传、校验、清洗、入库。

任务：

- 实现 CSV 字段校验；
- 检查必填字段；
- 检查 rating 范围；
- 检查空评论；
- 标记重复 review_id 或重复 review_text；
- 创建 batch；
- 保存 reviews；
- 生成 validation result；
- 写入 Trace。

验收标准：

- 上传 sample_reviews.csv 后可展示校验结果；
- 缺字段时能提示；
- 空评论不进入分析；
- 重复评论被标记；
- Dashboard 可读取有效评论数量。

## 阶段 2：数据库与基础服务层

目标：建立可持续扩展的数据基础。

任务：

- 初始化 SQLite；
- 建立 review_batches；
- 建立 reviews；
- 建立 review_analysis；
- 建立 insights；
- 建立 insight_evidence；
- 建立 reply_drafts；
- 建立 approval_actions；
- 建立 traces；
- 建立 eval_results；
- 封装 database 操作；
- 封装 ReviewService。

验收标准：

- 所有表可创建；
- 上传批次可持久化；
- 页面刷新后数据不丢失；
- 服务层可读取 batch 和 reviews。

## 阶段 3：Agent Workflow 主流程

目标：跑通分类、情绪、问题聚合、回复生成。

任务：

- 设计 Workflow Controller；
- 实现 Live Mode；
- 实现 Demo Mode；
- 接入 Classifier；
- 接入 Sentiment；
- 接入 Issue Aggregator；
- 接入 Reply Drafter；
- 接入 Safety Checker；
- 每一步写 Trace；
- 所有输出通过 Schema Guard。

验收标准：

- Demo Mode 可完整跑通；
- Live Mode 可至少跑通 sample 数据；
- 每条评论有 topics / sentiment / severity；
- 生成 Top 3 问题；
- 差评生成回复草稿。

## 阶段 4：Harness 核心能力

目标：让 AI 输出可控、可解释、可审批。

任务：

- 实现 Schema Guard；
- 实现 Evidence Guard；
- 实现 Safety Guardrails；
- 实现 fallback rules；
- 实现 Trace Logger；
- 实现 approval action 记录。

验收标准：

- LLM 输出结构错误时可以重试或 fallback；
- 洞察无证据时不展示；
- 回复含风险时自动重写或 block；
- 人工审批动作进入 Trace；
- Dashboard 能显示 Harness 状态。

## 阶段 5：UI 页面开发

目标：完成四个核心页面。

任务：

- 实现 Sidebar；
- 实现 Upload 页面；
- 实现 Dashboard 页面；
- 实现 Reply Review 页面；
- 实现 Trace & Eval 页面；
- 实现 Metric Cards；
- 实现 Issue Cards；
- 实现 Reply Queue；
- 实现 Harness Status Panel；
- 实现 Validation Result Panel。

验收标准：

- UI 与中文 mockup 风格一致；
- Dashboard 显示 4 个 KPI；
- Dashboard 显示三大问题；
- Dashboard 显示回复审核队列；
- Reply Review 可 Approve / Edit / Reject；
- Trace & Eval 可展示工作流和评测摘要。

## 阶段 6：Eval 与演示稳定性

目标：保证面试或展示时稳定运行。

任务：

- 准备 eval_reviews.jsonl；
- 实现 topic accuracy；
- 实现 sentiment accuracy；
- 实现 unsafe reply count；
- 实现 schema failure count；
- 保存 eval_results；
- 接入 Trace & Eval 页面；
- 完善 Demo Mode；
- 准备 5 分钟演示脚本。

验收标准：

- 点击 Run Eval 后有评测结果；
- Demo Mode 5 秒内显示完整结果；
- LLM 不可用时仍能演示；
- README 中包含演示流程。