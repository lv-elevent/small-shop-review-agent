# Roadmap

## v0.1：项目骨架与文档

目标：明确产品范围，建立项目目录，完成核心文档和数据准备。

交付物：
- README.md、Project Context、Database Spec、API Design、MVP Tasks、Roadmap
- CLAUDE.md
- sample_reviews.csv 示例数据
- UI mockups

## v0.2：数据接入

目标：CSV 上传、字段校验、评论清洗、SQLite 持久化、校验结果展示。

核心页面：Upload

完成标准：用户上传 CSV 后展示校验结果，数据入库。

## v0.3：Agent Workflow

目标：分类评论、识别情绪、聚合 Top 3 问题、生成差评回复草稿。

核心模块：Classifier、Sentiment、Issue Aggregator、Reply Drafter

完成标准：示例数据生成完整分析结果，所有 LLM 输出符合 schema，所有关键步骤写入 trace。

## v0.4：Harness 安全层

目标：Schema Guard、Evidence Guard、Safety Guardrails、Human Approval、Trace Logger。

完成标准：无证据洞察不展示，不安全回复不进入审批，审批动作可追踪。

## v0.5：产品级 UI

目标：完成四个核心页面，风格符合设计规范。

完成标准：Dashboard 简洁、Reply Review 可操作、Trace & Eval 展示系统可靠性。

## v1.0：可发布 MVP

目标：本地稳定运行，支持 Live 模式，Eval Summary 可用。

完成标准：一条命令启动，完整的分析→审批→评测闭环。

## v1.1：后续增强

可选方向：
- PDF / Markdown 报告导出
- 消息通知集成
- Ollama 本地模型适配
- 多门店支持
- 增强评测体系
- LangGraph / OpenAI Agents SDK 升级
- 平台评论抓取（须单独处理合规与授权）
