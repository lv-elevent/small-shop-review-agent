# API Design

## 1. 设计原则

- UI 层不直接操作业务逻辑
- UI 层仅调用 services
- services 调用 workflow / harness / database
- 所有服务返回结构化结果
- 失败时返回可展示的错误信息，不抛出不可读异常

## 2. 服务层

### ReviewService

职责：CSV 上传、字段校验、评论清洗、批次创建与查询。

| 接口 | 输入 | 输出 |
|------|------|------|
| validate_csv | uploaded_file | ValidationResult |
| create_batch | file, store_type | BatchResult |
| list_reviews | batch_id | ReviewList |
| get_review | batch_id, review_id | ReviewDetail |

### WorkflowService

职责：运行完整分析流程，支持 Live 与内置数据两种模式，返回 Dashboard 所需汇总数据。

| 接口 | 输入 | 输出 |
|------|------|------|
| run_analysis | batch_id, mode | WorkflowResult |
| get_workflow_status | batch_id | WorkflowStatus |

### InsightService

职责：聚合 Top 3 问题，管理洞察与证据关联，提供 Dashboard 数据。

| 接口 | 输入 | 输出 |
|------|------|------|
| get_top_issues | batch_id | InsightList |
| get_issue_evidence | insight_id | EvidenceList |

### ReplyService

职责：生成差评回复草稿，安全检查，管理人工审批流程。

| 接口 | 输入 | 输出 |
|------|------|------|
| get_pending_drafts | batch_id | DraftList |
| get_draft_detail | draft_id | DraftDetail |
| approve_draft | draft_id | ApprovalResult |
| edit_draft | draft_id, edited_text | ApprovalResult |
| reject_draft | draft_id, reason | ApprovalResult |

### TraceService

职责：工作流日志写入与查询。

| 接口 | 输入 | 输出 |
|------|------|------|
| log_step | trace_event | TraceEvent |
| get_trace | batch_id | TraceList |
| get_latest_trace | — | TraceList |

### EvalService

职责：评测执行、结果保存与查询。

| 接口 | 输入 | 输出 |
|------|------|------|
| run_eval | eval_config | EvalResult |
| get_latest_eval | — | EvalResult |
| get_latest_eval_by_batch | batch_id | EvalResult |
| list_eval_runs | limit | EvalRunList |
| list_eval_runs_by_batch | batch_id, limit | EvalRunList |

## 3. 页面与服务调用

### Upload 页面
- ReviewService.validate_csv / create_batch
- WorkflowService.run_analysis

### Dashboard 页面
- InsightService.get_top_issues
- ReplyService.get_pending_drafts
- TraceService.get_latest_trace
- EvalService.get_latest_eval

### Reply Review 页面
- ReplyService.get_pending_drafts / get_draft_detail
- ReplyService.approve_draft / edit_draft / reject_draft

### Trace & Eval 页面
- TraceService.get_trace
- EvalService.run_eval / get_latest_eval_by_batch / list_eval_runs_by_batch

## 4. 业务状态枚举

### batch.status
`uploaded` | `validating` | `validated` | `analyzing` | `analyzed` | `failed`

### reply_drafts.approval_status
`pending` | `approved` | `edited` | `rejected` | `blocked`

### reply_drafts.safety_status
`pass` | `rewrite_required` | `blocked`

### traces.status
`passed` | `warning` | `failed` | `pending`
