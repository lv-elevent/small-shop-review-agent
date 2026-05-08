# 完整验收流程

## 一、环境准备

```bash
cd d:\small-shop-review-agent

# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python scripts/init_db.py

# 3. 编译检查（无报错 = 通过）
python -m compileall apps src scripts -q
```

## 二、自动化测试（10 条冒烟 + 1 条 E2E）

```bash
python scripts/smoke_test_repos.py              # 38 pass
python scripts/smoke_test_review_service.py     # 43 pass
python scripts/smoke_test_demo_loader.py        # 361 pass
python scripts/smoke_test_demo_workflow.py      # 145 pass
python scripts/smoke_test_services.py           # 77 pass
python scripts/smoke_test_upload_flow.py        # 56 pass
python scripts/smoke_test_dashboard_data.py     # 137 pass
python scripts/smoke_test_reply_review_flow.py  # 67 pass
python scripts/smoke_test_trace_eval_page_data.py  # 87 pass
python scripts/e2e_demo_check.py                # 46 pass
```

**通过标准：** 每条输出 `ALL XXX SMOKE TESTS PASSED` 或 `E2E DEMO CHECK PASSED`，failed=0。合计 1,057 项全部 pass。

## 三、启动 Streamlit

```bash
streamlit run apps/streamlit_app/app.py
```

浏览器打开 `http://localhost:8501`

### 操作流程

**步骤 1：首页**
看到 ☕ 图标 + "小店评论经营助手" + 左侧导航栏 4 个入口。点击「📤 上传」进入上传页面。左侧导航栏当前页高亮。

**步骤 2：上传评论（Demo Mode）**
- 打开 **🎭 Demo Mode** 开关
- 看到蓝色提示 "Demo Mode 已开启 — 使用内置 15 条示例评论数据"
- 右侧显示 CSV 格式说明、示例数据预览表（15 行）、数据概况
- 点击 **🚀 开始分析**
- 看到 spinner → 校验结果卡片（有效13/重复1/空1/评分异常0）→ 分析完成提示："13 条评论 → 3 个洞察 → 5 条回复草稿"

**步骤 3：数据看板**
- 点击左侧「📊 数据看板」
- 4 个指标卡：总评论数 13 / 平均评分 ~3.X / 差评数 5 / 待审核回复 4
- 左侧「三大问题洞察」：3 张卡片，rank 1/2/3，分别显示 hygiene/waiting_time/service，每张有提及次数、证据条数、关联评论 ID、建议措施
- 右侧「AI 工作流可靠性检查」：5 项 harness 状态（输入校验/证据绑定/安全检查/人工审批等），各有绿色 ✓ 或橙色 ⚠ 状态
- 右侧「差评回复审核队列」：4 条待审核草稿，每条显示 review_id、回复片段、安全状态

**步骤 4：回复审核**
- 点击左侧「💌 回复审核」
- 左侧队列显示 5 条草稿（COFF04/COFF06/COFF12/COFF13 pending，COFF08 blocked）
- 筛选标签：全部/待审核/需修改/已拦截/已处理，点击可切换
- 点击队列中的 **COFF04** → 右侧显示原始评论 + AI 回复草稿 + 安全状态 "✓ 安全"
- 点击 **✅ 批准发布** → toast 提示 "已批准" → 队列刷新，COFF04 从 pending 消失
- 点击队列中的 **COFF12** → 编辑文本区修改回复内容 → 点击 **📝 保存修改** → toast "已保存"
- 点击队列中的 **COFF08**（已拦截）→ 批准按钮灰色 disabled，显示 "🚫 内容已拦截"
- 点击队列中的 **COFF13** → 点击 **✗ 驳回** → 输入原因 → 确认驳回 → toast "已驳回"

**步骤 5：追踪与评测**
- 点击左侧「🔍 追踪评测」
- 左侧「追踪日志」：显示工作流时间线（输入校验 → 数据清洗 → 评论分类 → 情绪分析 → 问题聚合 → 证据绑定 → 回复草稿 → 安全检查），每步有状态 badge + 输入/输出摘要
- 右侧「评测摘要」：6 个指标卡（分类准确率/情绪准确率/不安全回复/Schema 失败/评测样例数/综合评分）
- 点击 **🧪 运行评测** → spinner → toast "评测完成" → 刷新后指标卡更新，评测记录新增一行

## 四、通过标准

| 检查项 | 预期结果 |
|---|---|
| compileall | 无输出 = 无语法错误 |
| 10 条 smoke test | 全部 `0 failed` |
| e2e_demo_check | `E2E DEMO CHECK PASSED` |
| 上传页面 | Demo Mode 可加载 CSV 预览，分析按钮调用真实服务 |
| 数据看板 | 4 指标卡 + 3 问题卡 + Harness 状态 + 审核队列均来自 DB |
| 回复审核 | Approve/Edit/Reject 真实写库，st.rerun() 后状态更新 |
| 追踪与评测 | Trace 时间线来自 traces 表，Run Eval 写入 eval_results + trace |
| 数据库 | sqlite3 查看 9 张表均有数据 |
| 无报错 | 整个流程无红色 error toast，无页面崩溃 |
