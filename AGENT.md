# AGENT.md

## 1. 项目身份

你正在协助开发 Small Shop Review Response & Insight Agent。

这是一个面向小型门店老板的评论分析与差评处理 Agent MVP。第一版使用 Streamlit + Python Workflow + SQLite + Pydantic 构建本地可演示系统。

## 2. 业务目标

系统帮助老板完成：

1. 上传评论 CSV；
2. 校验和清洗评论；
3. 识别评论主题；
4. 判断情绪和严重程度；
5. 聚合三大问题；
6. 为差评生成回复草稿；
7. 进行安全检查；
8. 人工审批回复；
9. 在 Dashboard 展示结果；
10. 在 Trace & Eval 页面展示可靠性。

## 3. 第一版不做

不要实现以下内容：

- 自动发布回复；
- 平台爬虫；
- 多门店系统；
- 账号权限系统；
- 移动端；
- 完整 SaaS 后端；
- 复杂多 Agent 自治；
- 长期记忆；
- 复杂 BI 报表；
- 完整周报生成。

## 4. 架构原则

- UI 层只负责展示和调用 service；
- service 层封装业务操作；
- workflow 层组织 Agent-like 节点；
- agents 层负责 LLM 任务；
- harness 层负责校验、安全、证据、追踪、fallback；
- database 层负责 SQLite 持久化；
- 所有 LLM 输出必须经过 Pydantic Schema 校验；
- 所有洞察必须绑定 review_id 证据；
- 所有回复必须经过 Safety Check；
- 所有客户可见回复必须人工审批。

## 5. UI 风格

风格为浅色 SaaS 工作台 + 咖啡店暖色点缀。

主色：

- #2F6B4F
- #D99A32
- #F7F6F2
- #FFFFFF

页面：

- 上传
- 数据看板
- 回复审核
- 追踪与评测

请参考 docs/ui_mockups/ 中的图片。

## 6. 数据约束

CSV 必填字段：

- review_id
- date
- platform
- rating
- review_text

rating 必须为 1–5。

空评论不进入分析。

重复评论要标记。

rating <= 2 默认进入差评候选。

## 7. LLM 输出要求

不得返回自由文本作为最终结构。

所有 agent 输出必须是结构化对象：

- 分类结果；
- 情绪结果；
- 洞察结果；
- 回复草稿；
- 安全检查结果。

如果 LLM 输出不符合 schema：

1. 自动重试一次；
2. 仍失败则使用 fallback rule；
3. 写入 Trace。

## 8. Safety Rules

回复草稿不得：

- 攻击顾客；
- 讽刺顾客；
- 泄露隐私；
- 编造事实；
- 承诺无法保证的赔偿；
- 声称已经处罚员工；
- 使用过度营销话术。

不安全回复不得进入可发布状态。

## 9. Evidence Rules

Top 3 问题必须有证据评论。

每条洞察至少绑定 2 条 review_id。若数据不足，需要标记 evidence_insufficient。

无证据洞察不得展示在 Dashboard。

## 10. Trace Rules

以下步骤必须记录 Trace：

- input_validation
- data_cleaning
- classification
- sentiment_analysis
- issue_aggregation
- evidence_check
- reply_drafting
- safety_check
- human_approval
- eval_run

Trace 至少包含：

- trace_id
- batch_id
- step_name
- input_summary
- output_summary
- status
- latency_ms
- error_message
- created_at

## 11. Demo Mode

必须支持 Demo Mode。

Demo Mode 不调用真实 LLM，而是读取 data/mock_outputs/ 下的预生成结果。

Demo Mode 的目标是保证演示稳定。

## 12. 开发顺序

请按以下顺序开发：

1. 项目目录和配置；
2. 数据库；
3. CSV 校验；
4. 数据清洗；
5. Demo Mode；
6. Workflow Controller；
7. Agent 节点；
8. Harness 模块；
9. Streamlit 页面；
10. Eval；
11. 测试；
12. README 演示说明。

## 13. 代码风格

- 保持函数短小；
- 避免 UI 与业务逻辑混在一起；
- 避免硬编码业务数据；
- 所有枚举集中管理；
- 所有 prompt 集中管理；
- 所有 schema 集中管理；
- 对失败路径进行处理；
- 优先保证 MVP 闭环，不做过度抽象。

## 14. 判断标准

一次开发任务是否完成，要看：

- 是否符合 MVP 范围；
- 是否能在 Demo Mode 下稳定展示；
- 是否写入数据库；
- 是否写入 Trace；
- 是否经过 Schema/Safety/Evidence 检查；
- 是否能被 UI 正确展示。