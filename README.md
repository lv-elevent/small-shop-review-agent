# Small Shop Review Response & Insight Agent

小店差评处理与问题洞察 Agent

## 项目简介

围绕小型门店（咖啡店、餐厅等）的差评处理和问题复盘，提供轻量级 Agentic Workflow：

**核心闭环：** 上传 CSV → 分类与情绪 → 三大问题 → 回复草稿 → 安全检查 → 人工审批 → Dashboard → Trace/Eval

产品原则：短链路、可审批、有证据、可演示、稳定 Demo、简单 Workflow。

## 技术栈

- **UI**: Streamlit
- **语言**: Python 3.11+
- **数据库**: SQLite (WAL mode)
- **数据处理**: pandas
- **日志**: loguru
- **LLM**: Demo Mode 内置 mock 数据，Live 模式支持 OpenAI-compatible API / Ollama

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python scripts/init_db.py

# 3. 启动 Streamlit
streamlit run apps/streamlit_app/app.py
```

浏览器打开 `http://localhost:8501`，即可进入 Demo Mode 体验完整流程。

## Demo Mode

Demo Mode 是本项目的一等公民模式，**不依赖网络、不依赖 API key、不依赖真实 LLM**。

开启方式：在「上传评论」页面打开 **Demo Mode** 开关，系统自动加载 15 条内置示例评论，点击「开始分析」即可跑通完整流程。

适合场景：本地开发、面试演示、项目答辩。

## CSV 格式

| 列名 | 必填 | 说明 |
|------|------|------|
| `review_text` | 是 | 评论正文 |
| `rating` | 是 | 评分 (1-5 整数) |
| `date` | 是 | 评论日期 |
| `review_id` | 否 | 评论 ID（不提供则自动生成） |
| `platform` | 否 | 来源平台 |

支持编码：UTF-8 / GBK / GB2312 / GB18030 / Latin-1

示例文件：[src/small_shop_agent/demo/sample_reviews.csv](src/small_shop_agent/demo/sample_reviews.csv)

## 页面说明

### 1. 上传评论 (Upload)
上传 CSV 文件或开启 Demo Mode，选择门店类型，点击「开始分析」。系统自动完成校验 → 入库 → 分析全流程。

### 2. 数据看板 (Dashboard)
展示本批次的评论概览（总数/均分/差评数/待审核数）、三大问题洞察（含证据关联评论）和 AI 工作流可靠性状态（Harness Engine）。

### 3. 回复审核 (Reply Review)
左侧队列展示待处理草稿，右侧详情面板显示原始评论和 AI 生成回复。支持三种操作：
- **批准** (Approve) — 仅限安全检查通过的草稿
- **编辑** (Edit) — 修改回复内容后保存
- **驳回** (Reject) — 填写原因后驳回

被拦截（blocked）或需重写（rewrite_required）的草稿无法直接批准。

### 4. 追踪与评测 (Trace & Eval)
左栏展示工作流 Trace 时间线（每步名称、状态、输入/输出摘要、耗时），右栏展示评测指标（分类准确率、情绪准确率、不安全回复数、Schema 失败数、综合评分）和评测历史记录。点击「运行评测」可在当前批次上执行规则评估。

## 一次完整演示流程

1. 打开 Streamlit → 进入「上传评论」页面
2. 开启 **Demo Mode** 开关
3. 选择门店类型 → 点击 **「开始分析」**
4. 看到「分析完成」提示 → 前往 **「数据看板」** 查看 3 大问题和 Harness 状态
5. 前往 **「回复审核」** → 选择 COFF04 → 点击「批准发布」
6. 选择 COFF12 → 编辑回复内容 → 点击「保存修改」
7. 前往 **「追踪与评测」** → 查看 Trace 时间线 → 点击「运行评测」

## 不做功能

- 不自动发布回复（所有回复需人工审批）
- 不爬取平台评论
- 不多门店系统
- 不账号/权限系统
- 不复杂 BI / 趋势分析
- 不周报生成
- 不移动端

## 常见问题

### 如何初始化数据库？

```bash
python scripts/init_db.py
```

### 如何运行全部冒烟测试？

```bash
python scripts/smoke_test_repos.py
python scripts/smoke_test_review_service.py
python scripts/smoke_test_demo_loader.py
python scripts/smoke_test_demo_workflow.py
python scripts/smoke_test_services.py
python scripts/smoke_test_upload_flow.py
python scripts/smoke_test_dashboard_data.py
python scripts/smoke_test_reply_review_flow.py
python scripts/smoke_test_trace_eval_page_data.py
```

### 如何运行端到端验收？

```bash
python scripts/e2e_demo_check.py
```

这会从零开始完成：初始化 DB → 上传 CSV → 分析 → 审批 → 评测 → 验证 9 张表数据。

### 如何重置 Demo 数据？

重新运行 `python scripts/e2e_demo_check.py` 即可（脚本会在结束后清理测试数据）。如需在 Streamlit 中重置，重启应用并重新上传即可覆盖。
