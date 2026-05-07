# ROADMAP.md

## Version 0.1：项目骨架与文档

目标：

- 明确产品范围；
- 建立项目目录；
- 完成核心文档；
- 准备 UI mockups；
- 准备 Demo 数据。

交付物：

- README.md
- PROJECT_CONTEXT.md
- DATABASE_SPEC.md
- API_DESIGN.md
- MVP_TASKS.md
- ROADMAP.md
- AGENT.md
- CLAUDE.md
- sample_reviews.csv
- ui_mockups

## Version 0.2：数据接入 MVP

目标：

- 上传 CSV；
- 校验字段；
- 清洗评论；
- 保存 SQLite；
- 展示校验结果。

核心页面：

- Upload 页面

完成标准：

- 用户上传 CSV 后能看到校验结果；
- 数据可入库；
- Demo Mode 初步可用。

## Version 0.3：Agent Workflow MVP

目标：

- 分类评论；
- 识别情绪；
- 聚合 Top 3 问题；
- 生成差评回复草稿。

核心模块：

- Classifier
- Sentiment
- Issue Aggregator
- Reply Drafter

完成标准：

- sample_reviews 可以生成完整分析结果；
- 所有 LLM 输出符合 schema；
- 所有关键步骤写入 trace。

## Version 0.4：Harness MVP

目标：

- 加入安全和可信机制。

核心模块：

- Schema Guard
- Evidence Guard
- Safety Guardrails
- Human Approval
- Trace Logger

完成标准：

- 无证据洞察不展示；
- 不安全回复不进入审批；
- 审批动作可追踪。

## Version 0.5：产品级 UI Demo

目标：

- 完成 4 个页面；
- 风格接近 UI mockup；
- 可以完整演示。

页面：

- Upload
- Dashboard
- Reply Review
- Trace & Eval

完成标准：

- 5 分钟内完成一轮演示；
- Dashboard 简洁；
- Reply Review 可操作；
- Trace & Eval 可展示系统可靠性。

## Version 1.0：可展示 MVP

目标：

- 本地稳定运行；
- README 完整；
- 支持 Demo Mode；
- 支持 Live Mode；
- 支持 Eval Summary；
- 可用于简历和面试展示。

完成标准：

- 一条命令启动；
- 上传 sample_reviews.csv；
- 跑出 Dashboard；
- 审批回复；
- 展示 Trace/Eval；
- 导出已批准回复。

## Version 1.1：后续增强

可选方向：

- PDF / Markdown 报告导出；
- 邮件或微信通知；
- Ollama 本地模型适配；
- 多门店支持；
- 更完整 Eval；
- 错误分析页面；
- 用户满意度评分；
- LangGraph / OpenAI Agents SDK 升级；
- 自动从平台抓取评论，但必须单独处理合规与授权问题。