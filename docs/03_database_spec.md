# DATABASE_SPEC.md

## 1. 数据库选择

MVP 使用 SQLite，原因：

- 本地可演示；
- 零部署成本；
- 适合 Streamlit Demo；
- 便于保存评论、洞察、回复、Trace 和 Eval 结果。

## 2. 表设计总览

数据库包含以下核心表：

1. review_batches
2. reviews
3. review_analysis
4. insights
5. insight_evidence
6. reply_drafts
7. approval_actions
8. traces
9. eval_results

## 3. review_batches 表

用途：记录一次上传或一次 Demo 分析批次。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| batch_id | TEXT | 是 | 批次唯一 ID |
| store_type | TEXT | 是 | 门店类型，如 coffee_shop |
| source_type | TEXT | 是 | csv_upload / demo_mode |
| file_name | TEXT | 否 | 上传文件名 |
| total_rows | INTEGER | 是 | 原始总行数 |
| valid_review_count | INTEGER | 是 | 有效评论数 |
| duplicate_count | INTEGER | 是 | 重复评论数 |
| empty_review_count | INTEGER | 是 | 空评论数 |
| schema_error_count | INTEGER | 是 | 结构错误数 |
| status | TEXT | 是 | uploaded / analyzed / failed |
| created_at | TEXT | 是 | 创建时间 |

## 4. reviews 表

用途：保存原始评论和清洗后评论。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 所属批次 |
| review_id | TEXT | 是 | CSV 中的评论 ID |
| date | TEXT | 否 | 评论日期 |
| platform | TEXT | 否 | 评论平台 |
| rating | INTEGER | 是 | 1–5 分 |
| review_text | TEXT | 是 | 原始评论 |
| cleaned_text | TEXT | 否 | 清洗后文本 |
| is_empty | INTEGER | 是 | 是否空评论 |
| is_duplicate | INTEGER | 是 | 是否重复 |
| is_valid | INTEGER | 是 | 是否进入分析 |
| created_at | TEXT | 是 | 入库时间 |

唯一约束：

- batch_id + review_id 应唯一。

## 5. review_analysis 表

用途：保存每条评论的分类、情绪、严重程度结果。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 批次 ID |
| review_id | TEXT | 是 | 评论 ID |
| topics | TEXT | 是 | JSON 字符串，如 ["waiting_time","service"] |
| sentiment | TEXT | 是 | positive / neutral / negative |
| severity | INTEGER | 是 | 1–5 |
| topic_confidence | REAL | 否 | 主题分类置信度 |
| sentiment_confidence | REAL | 否 | 情绪置信度 |
| is_negative_candidate | INTEGER | 是 | 是否差评候选 |
| needs_review | INTEGER | 是 | 是否需要人工确认 |
| model_name | TEXT | 否 | 使用的模型 |
| created_at | TEXT | 是 | 创建时间 |

## 6. insights 表

用途：保存三大问题聚合结果。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 批次 ID |
| rank | INTEGER | 是 | 排名 1–3 |
| issue_name | TEXT | 是 | 问题名称 |
| topic | TEXT | 是 | 对应主题 |
| mention_count | INTEGER | 是 | 出现次数 |
| severity_level | TEXT | 是 | high / medium / low |
| priority_score | REAL | 是 | 优先级分数 |
| suggested_action | TEXT | 是 | 建议动作 |
| evidence_count | INTEGER | 是 | 证据数量 |
| evidence_status | TEXT | 是 | sufficient / insufficient |
| created_at | TEXT | 是 | 创建时间 |

## 7. insight_evidence 表

用途：保存洞察和评论证据之间的关联。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| insight_id | INTEGER | 是 | 洞察 ID |
| batch_id | TEXT | 是 | 批次 ID |
| review_id | TEXT | 是 | 评论 ID |
| evidence_text | TEXT | 是 | 证据原文 |
| evidence_reason | TEXT | 否 | 为什么该评论支持该洞察 |
| created_at | TEXT | 是 | 创建时间 |

设计原则：

- 不把 evidence_review_ids 只作为 JSON 存在 insights 表里；
- 使用关联表，方便后续查询和展示；
- 删除或更新 insight 时，应同步维护 evidence 记录。

## 8. reply_drafts 表

用途：保存 AI 回复草稿、安全检查结果和审批状态。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| batch_id | TEXT | 是 | 批次 ID |
| review_id | TEXT | 是 | 评论 ID |
| original_review | TEXT | 是 | 原始差评 |
| draft_text | TEXT | 是 | AI 回复草稿 |
| edited_text | TEXT | 否 | 人工修改后的文本 |
| final_text | TEXT | 否 | 最终可发布文本 |
| safety_status | TEXT | 是 | pass / rewrite_required / blocked |
| risk_types | TEXT | 否 | JSON 字符串 |
| approval_status | TEXT | 是 | pending / approved / edited / rejected / blocked |
| model_name | TEXT | 否 | 使用模型 |
| created_at | TEXT | 是 | 创建时间 |
| updated_at | TEXT | 否 | 更新时间 |

## 9. approval_actions 表

用途：记录用户对回复草稿的审批行为。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| draft_id | INTEGER | 是 | 回复草稿 ID |
| action | TEXT | 是 | approve / edit / reject |
| before_text | TEXT | 否 | 修改前文本 |
| after_text | TEXT | 否 | 修改后文本 |
| reject_reason | TEXT | 否 | 拒绝原因 |
| created_at | TEXT | 是 | 操作时间 |

## 10. traces 表

用途：记录工作流步骤。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| trace_id | TEXT | 是 | 运行追踪 ID |
| batch_id | TEXT | 是 | 批次 ID |
| step_name | TEXT | 是 | 步骤名 |
| input_summary | TEXT | 否 | 输入摘要 |
| output_summary | TEXT | 否 | 输出摘要 |
| status | TEXT | 是 | passed / warning / failed / pending |
| error_message | TEXT | 否 | 错误信息 |
| latency_ms | INTEGER | 否 | 耗时 |
| model_name | TEXT | 否 | 模型名 |
| created_at | TEXT | 是 | 创建时间 |

## 11. eval_results 表

用途：保存评测结果。

字段：

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | INTEGER | 是 | 自增主键 |
| eval_run_id | TEXT | 是 | 评测运行 ID |
| topic_accuracy | REAL | 是 | 主题准确率 |
| sentiment_accuracy | REAL | 是 | 情绪准确率 |
| unsafe_reply_count | INTEGER | 是 | 不安全回复数 |
| schema_failure_count | INTEGER | 是 | Schema 失败数 |
| baseline_topic_accuracy | REAL | 否 | baseline 对比 |
| notes | TEXT | 否 | 备注 |
| created_at | TEXT | 是 | 创建时间 |