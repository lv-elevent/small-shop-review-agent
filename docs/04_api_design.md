# API_DESIGN.md

## 1. 设计原则

- UI 层不得直接操作复杂业务逻辑；
- UI 层只调用 services；
- services 调用 workflow / agents / harness / database；
- 所有服务返回结构化结果；
- 失败时返回可展示的错误信息，不抛出不可读异常。

## 2. 服务层模块

### ReviewService

职责：

- 处理 CSV 上传；
- 执行字段校验；
- 清洗评论；
- 保存 reviews；
- 创建 review_batch。

主要接口：

| 接口名 | 输入 | 输出 |
|---|---|---|
| validate_csv | uploaded_file | ValidationResult |
| create_batch | file, store_type, demo_mode | BatchResult |
| list_reviews | batch_id | ReviewList |
| get_review | batch_id, review_id | ReviewDetail |

### WorkflowService

职责：

- 运行完整分析流程；
- 支持 Live Mode 和 Demo Mode；
- 管理 trace_id；
- 返回 Dashboard 所需汇总数据。

主要接口：

| 接口名 | 输入 | 输出 |
|---|---|---|
| run_analysis | batch_id, mode | WorkflowResult |
| run_demo_analysis | demo_batch_id | WorkflowResult |
| get_workflow_status | batch_id | WorkflowStatus |

### InsightService

职责：

- 聚合三大问题；
- 管理洞察和证据；
- 提供 Dashboard 问题卡数据。

主要接口：

| 接口名 | 输入 | 输出 |
|---|---|---|
| generate_top_issues | batch_id | InsightList |
| get_top_issues | batch_id | InsightList |
| get_issue_evidence | insight_id | EvidenceList |

### ReplyService

职责：

- 生成差评回复草稿；
- 执行安全检查；
- 管理人工审批。

主要接口：

| 接口名 | 输入 | 输出 |
|---|---|---|
| generate_reply_drafts | batch_id | DraftList |
| get_pending_drafts | batch_id | DraftList |
| get_draft_detail | draft_id | DraftDetail |
| approve_draft | draft_id | ApprovalResult |
| edit_draft | draft_id, edited_text | ApprovalResult |
| reject_draft | draft_id, reason | ApprovalResult |
| export_approved_replies | batch_id | ExportResult |

### TraceService

职责：

- 写入工作流日志；
- 读取 Trace 页面数据。

主要接口：

| 接口名 | 输入 | 输出 |
|---|---|---|
| log_step | trace_event | TraceEvent |
| get_trace | batch_id | TraceList |
| get_latest_trace | 无 | TraceList |

### EvalService

职责：

- 运行评测；
- 保存评测结果；
- 提供 Trace & Eval 页面数据。

主要接口：

| 接口名 | 输入 | 输出 |
|---|---|---|
| run_eval | eval_config | EvalResult |
| get_latest_eval | 无 | EvalResult |
| list_eval_runs | limit | EvalRunList |

## 3. 页面与服务调用关系

### Upload 页面

调用：

- ReviewService.validate_csv
- ReviewService.create_batch
- WorkflowService.run_analysis / run_demo_analysis

### Dashboard 页面

调用：

- InsightService.get_top_issues
- ReplyService.get_pending_drafts
- TraceService.get_latest_trace
- EvalService.get_latest_eval

### Reply Review 页面

调用：

- ReplyService.get_pending_drafts
- ReplyService.get_draft_detail
- ReplyService.approve_draft
- ReplyService.edit_draft
- ReplyService.reject_draft

### Trace & Eval 页面

调用：

- TraceService.get_trace
- EvalService.run_eval
- EvalService.get_latest_eval
- EvalService.list_eval_runs

## 4. 业务状态枚举

### batch.status

- uploaded
- validating
- validated
- analyzing
- analyzed
- failed

### reply_drafts.approval_status

- pending
- approved
- edited
- rejected
- blocked

### reply_drafts.safety_status

- pass
- rewrite_required
- blocked

### traces.status

- passed
- warning
- failed
- pending