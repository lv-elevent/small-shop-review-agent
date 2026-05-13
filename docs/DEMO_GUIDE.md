# Demo 演示指南

## 快速启动（3 步）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用（默认 Demo Mode）
python run_app.py

# 3. 浏览器打开 http://localhost:8501
```

## 完整演示流程（7 步）

### Step 1: 进入上传评论页面

打开浏览器 `http://localhost:8501`，默认进入「上传评论」页面。

### Step 2: 开启 Demo Mode

点击页面顶部的 **🎭 演示模式** 开关。系统自动加载内置 15 条示例评论数据（咖啡店场景）。

### Step 3: 运行分析

点击 **🚀 开始分析** 按钮。系统自动执行：
```
CSV 校验 → 入库 → 分类 → 情绪 → 一致性检查
  → 问题聚合 → 证据绑定 → 回复草稿 → 安全检查
```

耗时约 25-30ms（纯本地）。看到「✅ 分析完成」提示后进入下一步。

### Step 4: 查看数据看板

点击左侧导航「📊 数据看板」：
- 顶部显示批次概览：13 条评论 / 5 条差评 / 4 条待审核
- 中间展示 Top 3 问题洞察（卫生状况堪忧 / 等待时间过长 / 服务态度需改善）
- 每个问题绑定 2-3 条证据评论
- 底部显示审核队列

### Step 5: 审批回复草稿

点击左侧导航「✍️ 回复审核」：
- 左侧队列：5 条待处理草稿，按风险优先级排序
- 危险标记：COFF08（blocked）COFF06（rewrite_required）

操作：
1. 点击 **COFF04** → 详情面板显示原始评论「等了太久…」和 AI 回复
2. 安全状态显示「pass」→ 点击 **✅ 批准发布**
3. 点击 **COFF06** → 安全状态显示「rewrite_required」→ 点击 **✏️ 编辑**，修改后保存

**注意**：blocked 的草稿（COFF08）无法直接批准。

### Step 6: 运行评测

点击左侧导航「🔍 追踪与评测」：
- 左栏：Trace 时间线，展示 9 个步骤的执行状态和耗时
- 右栏：评测指标（话题准确率 100%、情绪准确率 100%）
- 点击 **🧪 运行评测** 按钮

### Step 7: 查看可靠性仪表盘

在「追踪与评测」页面右下方：
- 📊 可靠性指标：总延迟、LLM 延迟、Schema 重试、降级率
- 安全拦截率、人工编辑数、记忆命中数、不安全漏报数

## E2E 自动化验收

```bash
# 完整自动化测试（57 项检查）
python scripts/e2e_demo_check.py

# Agent Graph 模式测试
python scripts/e2e_demo_check.py --runtime agent_graph
```

## 运行测试

```bash
# 全部单元测试（200+ 个）
pytest tests/unit/ -v

# 按模块测试
pytest tests/unit/test_safety_red_team.py -v    # 安全红队
pytest tests/unit/test_agent_async.py -v         # 异步执行
pytest tests/unit/test_ollama_provider.py -v     # Ollama 连接
pytest tests/unit/test_dual_engine_guard.py -v   # 双引擎安全
pytest tests/unit/test_consistency_check.py -v   # 一致性检查
```

## Ollama 本地模型配置

```bash
# 安装 Ollama 并拉取模型
ollama pull qwen2.5:7b

# 启动时指定
export LLM_MODE=ollama
export OLLAMA_MODEL=qwen2.5:7b
python run_app.py
```
