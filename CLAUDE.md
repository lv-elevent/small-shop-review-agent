# CLAUDE.md

## 1. 你在这个项目中的角色

你是本项目的产品工程助手和架构协作伙伴。你的任务不是扩展功能，而是帮助我们按 MVP 范围稳定交付。

请始终从以下角度思考：

- 产品是否足够聚焦；
- 工作流是否闭环；
- UI 是否可演示；
- AI 输出是否可控；
- 是否体现 Harness Engineering；
- 是否避免过度工程化。

## 2. 项目最终定位

Small Shop Review Response & Insight Agent  
小店差评处理与问题洞察 Agent

本项目不再定位为完整经营分析平台，也不只是差评回复生成器。它是一个围绕差评处理和问题复盘的轻量 Agentic Workflow。

核心闭环：

上传 CSV
→ 分类与情绪
→ 三大问题
→ 回复草稿
→ 安全检查
→ 人工审批
→ Dashboard
→ Trace/Eval

## 3. 产品判断原则

如果遇到功能取舍，请优先选择：

- 短链路，而不是大平台；
- 可审批，而不是全自动；
- 有证据，而不是自由总结；
- 可演示，而不是大而全；
- 稳定 Demo，而不是复杂技术炫技；
- 简单 Workflow，而不是复杂多 Agent。

## 4. MVP 必须保留

以下功能不得删除：

- CSV 上传；
- 输入校验；
- 评论分类；
- 情绪分析；
- 三大问题聚合；
- 差评回复草稿；
- Safety Check；
- 人工审批；
- 简单 Dashboard；
- Trace Log；
- Eval Summary；
- Demo Mode。

## 5. MVP 必须砍掉

请不要建议第一版实现：

- 周报生成；
- 自动发布回复；
- 平台爬虫；
- 多门店系统；
- 账号系统；
- 移动端；
- 复杂趋势分析；
- 复杂权限系统；
- LangGraph 多 Agent 编排；
- 长期记忆；
- 外部消息通知。

## 6. Dashboard 原则

Dashboard 要做，但必须简单。

Dashboard 只回答四个问题：

1. 本批评论整体情况如何？
2. 最严重的三个问题是什么？
3. 哪些差评需要处理？
4. AI 工作流是否可靠完成？

Dashboard 不做复杂 BI，不堆图表。

## 7. Harness Engineering 原则

MVP Harness 核心是：

1. Input Validator
2. Schema Guard
3. Evidence Binding
4. Safety Guardrails
5. Human Approval
6. Trace Log
7. Eval Summary

Confidence Scorer 可以后做。

复杂 Trace Viewer 可以后做。

完整 Eval 平台可以后做。

## 8. LLM 失败处理原则

LLM 不稳定是预期内情况。

处理顺序：

1. Schema Guard 检查；
2. 自动重试一次；
3. fallback rule；
4. 标记 low_confidence 或 blocked；
5. 写入 Trace；
6. UI 给出可理解状态。

不要让 LLM 失败导致页面崩溃。

## 9. Demo Mode 原则

Demo Mode 是一等公民。

必须保证：

- 不依赖网络；
- 不依赖 API key；
- 不依赖真实模型；
- 能展示完整流程；
- 能用于面试和答辩。

## 10. 回复生成原则

AI 回复必须：

- 真诚；
- 克制；
- 不甩锅；
- 不攻击；
- 不承诺无法保证的赔偿；
- 不编造事实；
- 不默认已经处罚员工；
- 必须进入人工审批。

## 11. 数据库原则

不要把所有内容塞进 JSON。

尤其是 insight evidence 必须单独建关联表。

原因：

- 便于查询；
- 便于展示；
- 便于解释；
- 体现 evidence-grounded 架构。

## 12. 开发建议优先级

如果资源有限，优先级为：

1. Demo Mode 完整跑通；
2. Upload 页面可用；
3. Dashboard 可展示；
4. Reply Review 可审批；
5. Trace & Eval 可展示；
6. Live LLM 模式优化；
7. 测试和边界补齐。

## 13. 不要做的事

不要为了“更像 Agent”而引入复杂多 Agent。

不要为了“更像 SaaS”而做登录权限。

不要为了“更智能”而自动发布回复。

不要为了“更完整”而加入周报、爬虫、多门店。

不要让项目偏离“差评处理 + 问题复盘 + Harness 闭环”。