# MVP Tasks

## Phase 0：项目初始化

目标：搭建项目骨架。

任务：
- 创建项目目录结构
- 建立 docs 文档目录
- 配置 requirements.txt
- 配置 .env.example
- 创建 README.md
- 创建 CLAUDE.md
- 准备 sample_reviews.csv 示例数据
- 准备 eval_reviews.jsonl 评测基准
- 准备 mock 输出数据

## Phase 1：数据接入与校验

目标：完成 CSV 上传、校验、清洗、入库。

任务：
- 实现 CSV 字段校验
- 检查必填字段
- 检查 rating 范围
- 检查空评论
- 标记重复 review_id 或重复 review_text
- 创建 batch
- 保存 reviews
- 生成 validation result
- 写入 Trace

验收标准：
- 上传 sample_reviews.csv 后展示校验结果
- 缺字段时提示
- 空评论不进入分析
- 重复评论被标记
- Dashboard 可读取有效评论数量

## Phase 2：数据库与基础服务层

目标：建立可持续扩展的数据基础。

任务：
- 初始化 SQLite
- 建立 review_batches、reviews、review_analysis 等 11 张表
- 封装 database 操作
- 封装 ReviewService

验收标准：
- 所有表可创建
- 上传批次可持久化
- 页面刷新后数据不丢失
- 服务层可读取 batch 和 reviews

## Phase 3：Agent Workflow 主流程

目标：完成分类、情绪、问题聚合、回复生成全链路。

任务：
- 设计 Workflow Controller
- 实现 Live 模式与内置数据模式
- 接入 Classifier、Sentiment、Issue Aggregator、Reply Drafter、Safety Checker
- 每步写入 Trace
- 所有输出经 Schema Guard

验收标准：
- 内置数据可完整运行
- 每条评论有 topics / sentiment / severity
- 生成 Top 3 问题
- 差评生成回复草稿

## Phase 4：Harness 核心能力

目标：使 AI 输出可控、可解释、可审批。

任务：
- 实现 Schema Guard
- 实现 Evidence Guard
- 实现 Safety Guardrails
- 实现 fallback rules
- 实现 Trace Logger
- 实现 approval action 记录

验收标准：
- LLM 输出结构错误时可重试或 fallback
- 洞察无证据时不展示
- 回复含风险时自动重写或 block
- 人工审批动作进入 Trace
- Dashboard 显示 Harness 状态

## Phase 5：UI 页面开发

目标：完成四个核心页面。

任务：
- 实现 Sidebar
- 实现 Upload / Dashboard / Reply Review / Trace & Eval 页面
- 实现 Metric Cards、Issue Cards、Reply Queue、Harness Status Panel、Validation Result Panel

验收标准：
- UI 与设计规范一致
- Dashboard 显示 KPI 指标、三大问题、回复审核队列
- Reply Review 支持 Approve / Edit / Reject
- Trace & Eval 展示工作流和评测摘要

## Phase 6：Eval 与稳定性

目标：保证系统在展示场景下稳定运行。

任务：
- 准备 eval_reviews.jsonl
- 实现 topic accuracy、sentiment accuracy
- 实现 unsafe reply count、schema failure count
- 保存 eval_results
- 接入 Trace & Eval 页面

验收标准：
- 执行评测后产生结果
- 系统在离线模式下完整运行
- README 包含运行说明
