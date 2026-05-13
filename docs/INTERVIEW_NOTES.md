# 面试/答辩 Notes

## 项目速览

| 项 | 值 |
|----|-----|
| 项目名 | Small Shop Review Agent |
| 定位 | 轻量级 Agentic Workflow 系统 |
| 场景 | 咖啡店 / 小型餐饮差评处理 |
| 技术栈 | Python / Streamlit / SQLite / Pydantic / loguru |
| LLM | MockProvider(内置) / OpenAI / Ollama(本地) |
| 代码规模 | ~200 个测试，~55 个源文件，~8K 行 Python |
| 核心特性 | Agent Runtime / 条件路由 / 工具层 / 双引擎安全 / 长期记忆 |

## 架构决策

### Q: 为什么不直接用 LangChain/LangGraph？
**A**: 项目定位轻量级可演示系统。LangChain 太重且抽象层多，不利于展示核心 Workflow 逻辑。自研 Graph Runner (~350 行) 足够表达条件路由、重试降级、异步执行的完整流程，面试官能清晰看到每一步的实现。

### Q: 为什么不用 ChromaDB/Qdrant 做向量检索？
**A**: 第一版先轻量落地 SQLite LIKE 检索。数据库表和 Repository 已支持未来升级到向量检索。当前 MemoryRetriever 的搜索接口与向量检索接口一致，未来切换无需改动调用方。

### Q: Pipeline vs Agent Graph 双引擎设计的考量？
**A**: Pipeline 是稳定的生产路径（WorkflowService），Agent Graph 是可扩展的实验路径。两者共享 `pipeline_steps.py` 核心函数，通过 `WORKFLOW_RUNTIME` 配置切换。渐进式演进，不破坏现有稳定性。

### Q: 为什么分类和情绪可以并发？
**A**: 两者读相同的 reviews 输入，但互不依赖输出。Async Graph Runner 用 `asyncio.gather` 并发执行，单任务失败不影响另一个，single-failure → partial-result + fallback。

## 安全机制亮点

### 双引擎安全检查
关键词 Rule Guard（毫秒级）先跑，命中 blocked 直接拦截。pass/rewrite 的走 LLM Semantic Judge（语义深度检测）。两者不一致时 escalation 到人工。

### 规则优先级
blocked-by-rule 的回复永远不会被 LLM 覆盖（hard safety constraint）。

### 红队测试
20 条覆盖 7 种风险类型的测试用例，包含 5 条安全对照。当前召回率 100%，零误报，零漏报。

### 一致性检查
classification 和 sentiment 的交叉验证：检测 review_id 不匹配 + rating/sentiment 逻辑冲突（如 rating=1 但 sentiment=positive）。

## 可靠性指标

| 指标 | 当前值 | 目标 |
|------|--------|------|
| 单元测试 | 200+ | ≥ 100 |
| E2E 检查 | 57 项 | 全覆盖 |
| 降级率 | < 5% | < 10% |
| Schema 校验 | 100% | 100% |
| 安全召回率 | 100% | ≥ 95% |

## 可扩展性

| 方向 | 当前状态 | 计划 |
|------|---------|------|
| LLM Provider | Mock + OpenAI + Ollama | 可插拔接口 |
| 向量检索 | SQLite LIKE | ChromaDB 接口兼容 |
| 多门店 | 单门店硬编码 | store_type 字段已预留 |
| Agent Tool | 5 个只读工具 | 工具注册表可扩展 |
| 异步执行 | classification+sentiment | 可扩展到更多独立节点 |
| 监控 | Streamlit 仪表盘 | 可对接外部监控 |

## 一次面试演示路线

```
1. 快速启动 (run_app.py) → Demo Mode 开箱即用
2. 上传 CSV → 分析全过程
3. 看板展示 Top 3 问题 + 证据
4. 回复审核 → approve + edit + blocked 拒绝
5. Trace 时间线 + 评测指标
6. E2E 自动化验收 → 全部通过
```

全程不依赖网络，不依赖 API key，5 分钟内完成。
