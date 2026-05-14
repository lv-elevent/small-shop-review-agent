# Phase UI-0: 公共 UI 组件与全局样式封装

## 目标
为四个 Streamlit 页面提供统一的 UI 组件和样式基础，不修改业务逻辑，只封装可复用的展示层组件。

## 当前状态
- 已有组件：sidebar.py, metric_card.py, ui_helpers.py（有代码）
- 已有空占位：issue_card.py, reply_queue.py, harness_status.py, trace_timeline.py, validation_result.py
- 已有样式：assets/theme.css

## 实施步骤

### 1. 创建/完善公共组件文件

#### 1.1 components/styles.py
- inject_global_styles() - 全局CSS注入
- get_color_palette() - 颜色变量

#### 1.2 components/ui_components.py（合并扩展）
- render_page_header()
- render_metric_card()（从现有 metric_card.py 迁移改进）
- render_status_badge()
- render_section_title()
- render_empty_state()
- render_progress_metric()
- render_small_table()
- format_latency()
- get_status_style()

#### 1.3 components/layout.py
- render_two_column_layout()
- render_card_container()

#### 1.4 保留现有组件
- sidebar.py（保持不变）
- ui_helpers.py（保持不变，可扩展）

### 2. 全局样式要求
- 页面背景：#FAFBF7
- 卡片背景：#FFFFFF
- 卡片圆角：12px/14px
- 卡片边框：#E8E0D5
- 卡片阴影：0 1px 4px rgba(0,0,0,0.04)
- Primary按钮：深咖啡渐变
- 表格表头：浅咖啡背景
- file_uploader：虚线边框

### 3. 测试要求
- python -m compileall src tests scripts -q
- pytest tests/unit/ -q
- python scripts/e2e_demo_check.py
- python scripts/e2e_demo_check.py --runtime agent_graph

## 文件变更清单

### 新增文件
- apps/streamlit_app/components/styles.py
- apps/streamlit_app/components/layout.py
- apps/streamlit_app/components/ui_components.py（合并现有 metric_card.py 功能）

### 修改文件
- apps/streamlit_app/components/__init__.py（导出公共组件）

### 保留文件（不修改）
- apps/streamlit_app/components/sidebar.py
- apps/streamlit_app/components/ui_helpers.py
- apps/streamlit_app/pages/*.py（本阶段不改）
