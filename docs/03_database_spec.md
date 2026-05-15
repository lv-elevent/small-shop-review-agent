# Database Specification

## 1. 数据库选型

MVP 使用 SQLite，理由：
- 零部署成本，本地可运行
- WAL 模式支持并发读写
- 适合 Streamlit 集成
- 持久化评论、洞察、回复、Trace 和 Eval 结果

## 2. 表设计总览

| # | 表名 | 用途 |
|---|------|------|
| 1 | review_batches | 批次元数据 |
| 2 | reviews | 评论数据 |
| 3 | review_analysis | 分类+情绪分析结果 |
| 4 | insights | Top 3 问题洞察 |
| 5 | insight_evidence | 洞察-证据关联 |
| 6 | reply_drafts | 回复草稿 |
| 7 | approval_actions | 审批操作日志 |
| 8 | traces | 工作流追踪 |
| 9 | eval_results | 评测结果 |

## 3. review_batches

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| batch_id | TEXT | 是 | 批次唯一标识 |
| store_type | TEXT | 是 | 门店类型 |
| source_type | TEXT | 是 | csv_upload / builtin |
| file_name | TEXT | 否 | 上传文件名 |
| total_rows | INTEGER | 是 | 原始总行数 |
| valid_review_count | INTEGER | 是 | 有效评论数 |
| duplicate_count | INTEGER | 是 | 重复评论数 |
| empty_review_count | INTEGER | 是 | 空评论数 |
| schema_error_count | INTEGER | 是 | 结构错误数 |
| status | TEXT | 是 | uploaded / analyzing / analyzed / failed |
| created_at | TEXT | 是 | 创建时间 |

## 4. reviews

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 所属批次 |
| review_id | TEXT | 是 | CSV 中的评论标识 |
| date | TEXT | 否 | 评论日期 |
| platform | TEXT | 否 | 评论平台 |
| rating | INTEGER | 是 | 1–5 |
| review_text | TEXT | 是 | 原始评论 |
| cleaned_text | TEXT | 否 | 清洗后文本 |
| is_empty | INTEGER | 是 | 是否空评论 |
| is_duplicate | INTEGER | 是 | 是否重复 |
| is_valid | INTEGER | 是 | 是否进入分析 |
| created_at | TEXT | 是 | 入库时间 |

唯一约束：batch_id + review_id

## 5. review_analysis

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 批次标识 |
| review_id | TEXT | 是 | 评论标识 |
| topics | TEXT | 是 | JSON 数组，如 ["waiting_time","service"] |
| sentiment | TEXT | 是 | positive / neutral / negative |
| severity | INTEGER | 是 | 1–5 |
| topic_confidence | REAL | 否 | 主题分类置信度 |
| sentiment_confidence | REAL | 否 | 情绪置信度 |
| is_negative_candidate | INTEGER | 是 | 是否差评候选 |
| needs_review | INTEGER | 是 | 是否需要人工确认 |
| model_name | TEXT | 否 | 使用模型 |
| created_at | TEXT | 是 | 创建时间 |

## 6. insights

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 批次标识 |
| rank | INTEGER | 是 | 排名 1–3 |
| issue_name | TEXT | 是 | 问题名称 |
| topic | TEXT | 是 | 对应主题 |
| mention_count | INTEGER | 是 | 出现次数 |
| severity_level | TEXT | 是 | high / medium / low |
| priority_score | REAL | 是 | 优先级分数 |
| suggested_action | TEXT | 是 | 建议措施 |
| evidence_count | INTEGER | 是 | 证据数量 |
| evidence_status | TEXT | 是 | sufficient / insufficient |
| created_at | TEXT | 是 | 创建时间 |

## 7. insight_evidence

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| insight_id | INTEGER | 是 | 洞察标识 |
| batch_id | TEXT | 是 | 批次标识 |
| review_id | TEXT | 是 | 评论标识 |
| evidence_text | TEXT | 是 | 证据原文 |
| evidence_reason | TEXT | 否 | 支持该洞察的原因 |
| created_at | TEXT | 是 | 创建时间 |

设计原则：evidence_review_ids 不存入 insights 表的 JSON 字段，使用独立关联表以支持查询与展示。

## 8. reply_drafts

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 批次标识 |
| review_id | TEXT | 是 | 评论标识 |
| original_review | TEXT | 是 | 原始差评 |
| draft_text | TEXT | 是 | AI 回复草稿 |
| edited_text | TEXT | 否 | 人工修改后文本 |
| final_text | TEXT | 否 | 最终可发布文本 |
| safety_status | TEXT | 是 | pass / rewrite_required / blocked |
| risk_types | TEXT | 否 | JSON 字符串 |
| approval_status | TEXT | 是 | pending / approved / edited / rejected / blocked |
| model_name | TEXT | 否 | 使用模型 |
| created_at | TEXT | 是 | 创建时间 |
| updated_at | TEXT | 否 | 更新时间 |

## 9. approval_actions

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| draft_id | INTEGER | 是 | 回复草稿标识 |
| action | TEXT | 是 | approve / edit / reject |
| before_text | TEXT | 否 | 修改前文本 |
| after_text | TEXT | 否 | 修改后文本 |
| reject_reason | TEXT | 否 | 驳回原因 |
| created_at | TEXT | 是 | 操作时间 |

## 10. traces

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| trace_id | TEXT | 是 | 运行追踪标识 |
| batch_id | TEXT | 是 | 批次标识 |
| step_name | TEXT | 是 | 步骤名称 |
| input_summary | TEXT | 否 | 输入摘要 |
| output_summary | TEXT | 否 | 输出摘要 |
| status | TEXT | 是 | passed / warning / failed / pending |
| error_message | TEXT | 否 | 错误信息 |
| latency_ms | INTEGER | 否 | 耗时(ms) |
| model_name | TEXT | 否 | 模型名称 |
| created_at | TEXT | 是 | 创建时间 |

## 11. eval_results

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | INTEGER | 是 | 自增主键 |
| eval_run_id | TEXT | 是 | 评测运行标识 |
| topic_accuracy | REAL | 是 | 主题准确率 |
| sentiment_accuracy | REAL | 是 | 情绪准确率 |
| unsafe_reply_count | INTEGER | 是 | 不安全回复数 |
| schema_failure_count | INTEGER | 是 | Schema 失败数 |
| baseline_topic_accuracy | REAL | 否 | baseline 对比值 |
| notes | TEXT | 否 | 备注 |
| created_at | TEXT | 是 | 创建时间 |
