## 小店评论经营助手 — Streamlit UI 设计规范

> 基于设计稿提炼，确保四页视觉一致性

---

## 1. 整体风格

### 1.1 设计语言
- **风格定位**：浅色 SaaS 工作台 + 咖啡店暖色点缀
- **视觉感受**：专业、温暖、可信赖、清晰易读
- **密度控制**：中等信息密度，留白充足（卡片间距 16-20px，内部间距 16-24px）

### 1.2 基础背景
| 区域 | 颜色值 | 说明 |
|------|--------|------|
| Sidebar | `#1A1A1A` / `#2C221B` | 深色导航，咖啡色调 |
| 主内容区 | `#FAFBF7` | 极浅米白，护眼背景 |
| 卡片背景 | `#FFFFFF` | 纯白，突出层级 |
| Hover背景 | `#F5F0E8` | 浅咖啡，悬停反馈 |

### 1.3 圆角与阴影
```css
/* 圆角规范 */
--radius-sm: 8px;    /* 按钮、输入框 */
--radius-md: 10px;   /* 小卡片、徽章 */
--radius-lg: 12px;   /* 指标卡、数据预览 */
--radius-xl: 14px;   /* 主内容卡片 */

/* 阴影规范 */
--shadow-card: 0 1px 4px rgba(0,0,0,0.04);
--shadow-hover: 0 2px 8px rgba(74,55,40,0.08);
--shadow-float: 0 4px 12px rgba(0,0,0,0.08);
```

---

## 2. 色彩规范

### 2.1 主色调（咖啡色系）
```css
--coffee-900: #2C221B;   /* Sidebar 背景 */
--coffee-800: #3D2C20;   /* 最深标题 */
--coffee-700: #4A3728;   /* 正文主色 */
--coffee-600: #5C3D2E;   /* 强调文字 */
--coffee-500: #6B4C3B;   /* Primary按钮、图标 */
--coffee-400: #8B7355;   /* Secondary文字 */
--coffee-300: #A09080;   /* 弱化文字、占位符 */
--coffee-200: #D4C4B0;   /* 边框、分割线 */
--coffee-100: #E8E0D5;   /* 浅边框、分隔线 */
--coffee-50:  #F5F0E8;   /* Hover背景 */
--cream:      #FFFCF8;   /* 上传区背景 */
```

### 2.2 功能色
```css
/* 成功 - 绿色 */
--success-main: #27AE60;
--success-light: #E8F8F0;
--success-border: #A9DFBF;

/* 警告 - 橙色 */
--warning-main: #E67E22;
--warning-light: #FEF5E7;
--warning-border: #F5CBA7;

/* 危险 - 红色 */
--danger-main: #C0392B;
--danger-light: #FDEDEC;
--danger-border: #F5B7B1;

/* 信息 - 蓝色 */
--info-main: #3498DB;
--info-light: #EBF5FB;
--info-border: #AED6F1;
```

### 2.3 中性色
```css
--text-primary: #3D2C20;     /* 主标题 */
--text-secondary: #6B5B4F;   /* 正文 */
--text-tertiary: #8B7355;    /* 辅助说明 */
--text-muted: #A09080;       /* 禁用、占位 */
--border-default: #E8E0D5;   /* 默认边框 */
--border-light: #F5F0E8;     /* 分割线 */
--bg-page: #FAFBF7;          /* 页面背景 */
--bg-card: #FFFFFF;          /* 卡片背景 */
```

---

## 3. 组件规范

### 3.1 页面标题区

**视觉样式：**
- 页面标题：1.5rem / 700 / `#3D2C20`
- 副标题：0.85rem / 400 / `#8B7355`
- 底部间距：20px
- 分隔线：1px solid `#E8E0D5`

**Streamlit 实现：**
```python
st.markdown("""
<div style="margin-bottom: 20px;">
    <h1 style="font-size: 1.5rem; font-weight: 700; color: #3D2C20; margin: 0 0 4px 0;">
        📤 上传评论数据
    </h1>
    <p style="font-size: 0.85rem; color: #8B7355; margin: 0;">
        上传顾客评论 CSV，系统将自动完成分类、情绪分析和回复草稿生成。
    </p>
</div>
<hr style="border: none; border-top: 1px solid #E8E0D5; margin: 0 0 20px 0;">
""", unsafe_allow_html=True)
```

---

### 3.2 指标卡（Metric Card）

**视觉样式：**
- 尺寸：自适应宽度，高度 100px 左右
- 背景：白色或主题浅色（如 `#FFF8F5`）
- 圆角：12px
- 阴影：`0 1px 4px rgba(0,0,0,0.04)`
- 边框：1px solid `#E8E0D5`（警告状态改为警告色边框）
- 内边距：18px 16px

**内容布局：**
```
┌─────────────────────────┐
│  📝 总评论数             │  ← 图标 + 标签（0.75rem / #8B7355）
│                         │
│        28               │  ← 数值（1.8rem / 700 / 主题色）
│                         │
│   较昨日 +8 (+40%) ↑    │  ← 变化值（可选，0.7rem）
└─────────────────────────┘
```

**颜色主题：**
| 类型 | 数值颜色 | 背景色 | 用途 |
|------|----------|--------|------|
| 默认 | `#4A3728` | `#FFFFFF` | 总评论、平均评分 |
| 警告 | `#E67E22` | `#FFF3EB` | 差评数、待审核 |
| 成功 | `#27AE60` | `#E8F8F0` | 已通过、安全 |
| 危险 | `#C0392B` | `#FDEDEC` | 已拦截、失败 |

**Streamlit 实现：**
```python
def metric_card(label: str, value, icon: str = "", 
                color: str = "#4A3728", bg_color: str = "#FFFFFF",
                delta: str = None, warn: bool = False):
    border_color = "#F0D0C0" if warn else "#E8E0D5"
    bg = "#FFF3EB" if warn else bg_color
    
    html = f"""
    <div style="
        background: {bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 18px 16px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    ">
        <div style="font-size: 0.75rem; color: #8B7355; font-weight: 500; margin-bottom: 8px;">
            {icon} {label}
        </div>
        <div style="font-size: 1.8rem; font-weight: 700; color: {color}; line-height: 1.2;">
            {value}
        </div>
        {f'<div style="font-size: 0.7rem; color: #8B7355; margin-top: 4px;">{delta}</div>' if delta else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# 使用：4列等宽
c1, c2, c3, c4 = st.columns(4, gap="medium")
with c1:
    metric_card("总评论数", 28, "📝", delta="较昨日 +8 ↑")
with c2:
    metric_card("平均评分", 2.5, "⭐")
with c3:
    metric_card("差评数", 22, "⚠️", color="#C0392B", warn=True, delta="较昨日 +5 ↑")
with c4:
    metric_card("待审核", 22, "✏️", color="#E67E22", warn=True)
```

---

### 3.3 主内容卡片（Section Card）

**视觉样式：**
- 背景：白色
- 圆角：14px
- 边框：1px solid `#E8E0D5`
- 阴影：`0 1px 4px rgba(0,0,0,0.04)`
- 内边距：20px-24px

**标题样式：**
- 字体：1rem / 700 / `#4A3728`
- 图标：与标题同行，16px
- 副标题：0.78rem / 400 / `#A09080`

**Streamlit 实现：**
```python
st.markdown("""
<div style="
    background: #FFFFFF;
    border: 1px solid #E8E0D5;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    margin-bottom: 16px;
">
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
        <span style="font-size: 1rem;">📋</span>
        <span style="font-size: 1rem; font-weight: 700; color: #4A3728;">追踪日志</span>
        <span style="background: #2F6B4F; color: #fff; padding: 2px 8px; 
                     border-radius: 4px; font-size: 0.7rem; margin-left: 8px;">
            🏠 pipeline
        </span>
    </div>
    <p style="font-size: 0.78rem; color: #A09080; margin: -12px 0 16px 0;">
        工作流执行记录 · 共 10 个步骤
    </p>
    <!-- 内容区 -->
</div>
""", unsafe_allow_html=True)
```

---

### 3.4 状态 Badge

**视觉样式：**
- 圆角：10px
- 内边距：2px 10px
- 字体：0.7rem / 600
- 行高：1

**类型定义：**
| 状态 | 文字颜色 | 背景色 | 示例 |
|------|----------|--------|------|
| 通过 | `#27AE60` | `#E8F8F0` | ✓ 通过 |
| 进行中 | `#E67E22` | `#FEF5E7` | ◷ 进行中 |
| 失败 | `#C0392B` | `#FDEDEC` | ✗ 失败 |
| 待审核 | `#8B7355` | `#F5F0E8` | ⏳ 待审核 |
| 安全 | `#27AE60` | `#E8F8F0` | ✓ 安全 |
| 需修改 | `#E67E22` | `#FEF5E7` | ⚠ 需修改 |
| 已拦截 | `#C0392B` | `#FDEDEC` | ✗ 已拦截 |

**Streamlit 实现：**
```python
def status_badge(status: str, label: str = None) -> str:
    config = {
        "passed":   ("#27AE60", "#E8F8F0", "✓ 通过"),
        "pending":  ("#E67E22", "#FEF5E7", "◷ 进行中"),
        "failed":   ("#C0392B", "#FDEDEC", "✗ 失败"),
        "warning":  ("#E67E22", "#FEF5E7", "⚠ 警告"),
        "pass":     ("#27AE60", "#E8F8F0", "✓ 安全"),
        "rewrite":  ("#E67E22", "#FEF5E7", "⚠ 需修改"),
        "blocked":  ("#C0392B", "#FDEDEC", "✗ 已拦截"),
    }
    color, bg, default_label = config.get(status, ("#8B7355", "#F5F0E8", status))
    text = label or default_label
    return f'<span style="display: inline-block; font-size: 0.7rem; font-weight: 600; padding: 2px 10px; border-radius: 10px; color: {color}; background: {bg}; white-space: nowrap;">{text}</span>'

# 使用
st.markdown(status_badge("passed"), unsafe_allow_html=True)
```

---

### 3.5 上传卡片

**视觉样式：**
- 背景：`#FFFCF8`（浅奶油色）
- 边框：2px dashed `#D4C4B0`
- 圆角：14px
- 内边距：40px 20px
- 悬停：边框变 `#A08060`，背景变 `#FFF9F0`

**内部布局：**
```
┌────────────────────────────────────────┐
│                                        │
│              [ 云上传图标 ]             │
│                                        │
│      拖拽 CSV 文件到此处，或点击选择     │
│                                        │
│      支持 UTF-8 / GBK 编码，最大 200MB   │
│                                        │
│           [ 选择文件 按钮 ]             │
│                                        │
└────────────────────────────────────────┘
```

**Streamlit 实现：**
```python
# 使用 CSS 覆盖 st.file_uploader 样式
st.markdown("""
<style>
section[data-testid="stFileUploader"] {
    border: 2px dashed #D4C4B0 !important;
    border-radius: 14px !important;
    background: #FFFCF8 !important;
    padding: 40px 20px !important;
    text-align: center !important;
    transition: border-color 0.25s, background 0.25s !important;
}
section[data-testid="stFileUploader"]:hover {
    border-color: #A08060 !important;
    background: #FFF9F0 !important;
}
</style>
""", unsafe_allow_html=True)

st.file_uploader("上传 CSV", type=["csv"], label_visibility="collapsed")
```

---

### 3.6 Top Issues 卡片

**视觉样式：**
- 左侧严重度条：4px宽，圆角
- 高严重：`#C0392B`
- 中严重：`#E67E22`
- 低严重：`#27AE60`

**内容结构：**
```
┌────────────────────────────────────────┐
│█ 问题 #1    ● 高严重                    │  ← 序号徽章 + 严重度
│█                                        │
│█ 等待时间过长                           │  ← 问题名称（0.95rem / 700）
│█                                        │
│█ 提及 7 次 · 证据 7 条 · 证据充分        │  ← 统计（0.8rem）
│█                                        │
│█ 关联评论: [r001] [r006] [r012] ... +2   │  ← 证据标签（code样式）
│█                                        │
│█ "增加人手，优化服务流程..."             │  ← 建议措施（引用样式）
│█                                        │
│█ 查看证据评论 ▼                         │  ← expander
└────────────────────────────────────────┘
```

**Streamlit 实现：**
```python
def issue_card(rank: int, issue_name: str, severity: str, 
               mention_count: int, evidence_count: int, 
               evidence_status: str, suggested_action: str,
               evidence_reviews: list):
    sev_colors = {"high": "#C0392B", "medium": "#E67E22", "low": "#27AE60"}
    sev_labels = {"high": "高", "medium": "中", "low": "低"}
    stripe = sev_colors.get(severity, "#8B7355")
    sev_label = sev_labels.get(severity, severity)
    
    html = f"""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 14px;
        padding: 16px 20px 16px 24px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        position: relative;
        overflow: hidden;
    ">
        <div style="position: absolute; left: 0; top: 0; bottom: 0; width: 4px; 
                    background: {stripe}; border-radius: 14px 0 0 14px;"></div>
        
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span style="font-size: 0.72rem; font-weight: 700; color: #8B7355; 
                        background: #F5F0E8; padding: 2px 8px; border-radius: 5px;">
                问题 #{rank}
            </span>
            <span style="font-weight: 600; font-size: 0.8rem; color: {stripe};">
                ● {sev_label}严重
            </span>
        </div>
        
        <div style="font-size: 0.95rem; font-weight: 700; color: #3D2C20; margin-bottom: 8px;">
            {issue_name}
        </div>
        
        <div style="font-size: 0.8rem; color: #6B5B4F; margin-bottom: 8px;">
            提及 <b>{mention_count}</b> 次 · 
            证据 <b>{evidence_count}</b> 条 · 
            {evidence_status}
        </div>
        
        <div style="font-size: 0.76rem; color: #8B7355; margin-bottom: 12px; line-height: 1.6;">
            关联评论：{" ".join(f'<code style="background: #F5F0E8; color: #6B4C3B; padding: 1px 6px; border-radius: 3px; font-size: 0.73rem; margin: 0 2px;">{r}</code>' for r in evidence_reviews[:5])}
            {f"<span>+{len(evidence_reviews)-5}</span>" if len(evidence_reviews) > 5 else ""}
        </div>
        
        <div style="background: #F5F0E8; border-radius: 8px; padding: 10px 14px;
                    font-size: 0.82rem; color: #5C3D2E; line-height: 1.5;">
            💡 {suggested_action}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
```

---

### 3.7 审核队列项

**视觉样式：**
- 背景：白色
- 边框：1px solid `#E8E0D5`
- 圆角：8px
- 内边距：10px 12px
- 选中状态：左侧3px褐色边框 + `#F5F0E8`背景

**内容结构：**
```
┌────────────────────────────────────────────────────┐
│ r001  咖啡凉了等了半小时...  ● 高  ✗  [审核按钮]   │
└────────────────────────────────────────────────────┘
   ↑      ↑                    ↑    ↑       ↑
 ID    评论摘要(截断)      严重度  安全状态  操作
```

**Streamlit 实现：**
```python
def queue_item(review_id: str, text: str, severity: str, 
               safety_status: str, is_selected: bool = False):
    sev_colors = {"high": "#C0392B", "medium": "#E67E22", "low": "#27AE60"}
    sev_labels = {"high": "高", "medium": "中", "low": "低"}
    
    safety_cfg = {
        "pass": ("#27AE60", "#E8F8F0", "✓"),
        "rewrite": ("#E67E22", "#FEF5E7", "⚠"),
        "blocked": ("#C0392B", "#FDEDEC", "✗"),
    }
    
    bg = "#F5F0E8" if is_selected else "#FFFFFF"
    border_left = "3px solid #6B4C3B" if is_selected else "none"
    
    html = f"""
    <div style="
        background: {bg};
        border: 1px solid #E8E0D5;
        border-left: {border_left};
        border-radius: 8px;
        padding: 10px 12px;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 6px;
    ">
        <span style="font-weight: 700; font-size: 0.82rem; color: #4A3728; min-width: 44px;">
            {review_id}
        </span>
        <span style="flex: 1; font-size: 0.82rem; color: #6B5B4F; 
                     white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            {text[:30]}{"..." if len(text) > 30 else ""}
        </span>
        <span style="font-weight: 600; font-size: 0.76rem; color: {sev_colors.get(severity, '#8B7355')};">
            ● {sev_labels.get(severity, severity)}
        </span>
        {status_badge(safety_status)}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
```

---

### 3.8 Trace 时间线卡片

**视觉样式：**
- 左侧时间线：2px竖线 `#E8E0D5`
- 步骤圆点：8px圆形，状态色
- 内容区：白色卡片，左侧3px状态色边框

**内容结构：**
```
   ●──────────────────────────────────────────
   │  #1  输入校验      15条→15条有效  5ms    [✓ 通过]
   │
   ●──────────────────────────────────────────
   │  #2  数据清洗      15条→15条有效  2ms    [✓ 通过]
   │
   ○──────────────────────────────────────────  ← 进行中为橙色空心/实心
   │  #8  安全检查      通过22条...    218ms   [⚠ 警告]
```

**Streamlit 实现：**
```python
def trace_timeline_item(step_num: int, step_name: str, detail: str, 
                        status: str, latency_ms: int = None):
    status_colors = {
        "passed": "#27AE60",
        "pending": "#E67E22", 
        "failed": "#C0392B",
        "warning": "#E67E22"
    }
    dot_color = status_colors.get(status, "#8B7355")
    
    latency_text = f"耗时 {latency_ms}ms" if latency_ms else ""
    
    html = f"""
    <div style="display: flex; gap: 12px; margin-bottom: 8px; position: relative;">
        <!-- 时间线 -->
        <div style="width: 24px; display: flex; flex-direction: column; align-items: center;">
            <div style="width: 8px; height: 8px; border-radius: 50%; background: {dot_color};"></div>
            <div style="width: 2px; flex: 1; background: #E8E0D5; margin-top: 4px;"></div>
        </div>
        
        <!-- 内容卡片 -->
        <div style="
            flex: 1;
            background: #FFFFFF;
            border: 1px solid #E8E0D5;
            border-left: 3px solid {dot_color};
            border-radius: 8px;
            padding: 10px 14px;
            display: flex;
            align-items: center;
            gap: 12px;
        ">
            <span style="font-weight: 700; font-size: 0.82rem; color: #4A3728; min-width: 24px;">
                #{step_num}
            </span>
            <span style="font-weight: 600; font-size: 0.84rem; color: #4A3728; min-width: 80px;">
                {step_name}
            </span>
            <span style="flex: 1; font-size: 0.8rem; color: #6B5B4F;">
                {detail}
            </span>
            <span style="font-size: 0.74rem; color: #A09080;">
                {latency_text}
            </span>
            {status_badge(status)}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
```

---

### 3.9 Reliability 指标卡

**视觉样式：**
- 网格布局：4列 × 2行
- 每个指标：图标 + 数值 + 标签垂直居中
- 背景：白色
- 圆角：10px
- 边框：1px solid `#E8E0D5`

**内容结构：**
```
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│  ⏱️    │  │  🔄    │  │  ↩️    │  │  🛡️    │
│ 15.59s │  │   2    │  │   0%   │  │   0%   │
│ 总延迟  │  │Schema  │  │ Fallback│  │安全拦截 │
│        │  │ 重试   │  │   率   │  │   率   │
└────────┘  └────────┘  └────────┘  └────────┘
```

**Streamlit 实现：**
```python
def reliability_metric(icon: str, value: str, label: str, color: str = "#4A3728"):
    html = f"""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E8E0D5;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    ">
        <div style="font-size: 1.25rem; margin-bottom: 4px;">{icon}</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: {color}; margin-bottom: 2px;">
            {value}
        </div>
        <div style="font-size: 0.7rem; color: #8B7355;">{label}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# 使用：4列网格
c1, c2, c3, c4 = st.columns(4, gap="small")
with c1:
    reliability_metric("⏱️", "15.59s", "总耗时")
with c2:
    reliability_metric("🔄", "2", "Schema重试")
with c3:
    reliability_metric("↩️", "0%", "Fallback率", "#27AE60")
with c4:
    reliability_metric("🛡️", "0%", "安全拦截率", "#27AE60")
```

---

### 3.10 表格

**视觉样式：**
- 表头背景：`#F5F0E8`
- 表头文字：`#4A3728` / 700 / 0.76rem
- 行高：44px
- 行边框：1px solid `#F5F0E8`
- 悬停：行背景 `#FAFAFA`

**Streamlit 实现：**
```python
# 使用 st.dataframe 并覆盖样式
st.markdown("""
<style>
div[data-testid="stDataFrame"] th {
    background: #F5F0E8 !important;
    color: #4A3728 !important;
    font-weight: 700 !important;
    font-size: 0.76rem !important;
}
div[data-testid="stDataFrame"] td {
    font-size: 0.82rem !important;
    color: #4A3728 !important;
}
</style>
""", unsafe_allow_html=True)

st.dataframe(df, use_container_width=True, hide_index=True)
```

---

### 3.11 按钮

**类型定义：**
| 类型 | 背景 | 文字 | 边框 | 用途 |
|------|------|------|------|------|
| Primary | `#6B4C3B` | 白色 | 无 | 主要操作（开始分析、批准） |
| Secondary | 白色 | `#6B4C3B` | 1px solid `#6B4C3B` | 次要操作（导出、保存） |
| Danger | 白色 | `#C0392B` | 1px solid `#C0392B` | 危险操作（驳回） |
| Success | `#27AE60` | 白色 | 无 | 成功操作（批准发布） |

**尺寸：**
- 高度：36px-40px
- 圆角：8px-10px
- 内边距：8px 16px
- 字体：0.85rem / 600

**Streamlit 实现：**
```python
# Primary 按钮（批准、开始分析）
st.button("🚀 开始分析", type="primary", use_container_width=True)

# Secondary 按钮（导出、保存）
st.button("📥 导出", type="secondary", use_container_width=True)

# Danger 按钮使用 HTML 包装
st.markdown("""
<button style="
    background: #FFFFFF;
    color: #C0392B;
    border: 1px solid #C0392B;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
">❌ 驳回</button>
""", unsafe_allow_html=True)
```

---

## 4. 布局规范

### 4.1 上传页 (Upload)

**布局结构：**
```
┌─────────────────────────────────────────────────────────┐
│ [标题区] 上传评论数据 + 副标题                              │
├────────────────────┬────────────────────────────────────┤
│                    │                                    │
│  📋 数据配置        │  [CSV格式说明 | 示例数据 | 数据概况] │
│  ┌──────────────┐  │                                    │
│  │ 内置数据开关  │  │  ─────────────────────────────     │
│  │ 门店类型下拉  │  │  CSV格式要求                        │
│  │ LLM模式下拉   │  │  · 必填字段...                      │
│  └──────────────┘  │                                    │
│                    │  [下载示例CSV]                      │
│  📁 上传 CSV       │                                    │
│  [   拖拽区域    ]  │  ─────────────────────────────     │
│                    │  示例数据预览                       │
│  📋 数据预览       │  [表格]                             │
│  [表格 expander]   │                                    │
│                    │  ─────────────────────────────     │
│  [🚀 开始分析]     │  📈 数据概况                        │
│                    │  总评论  平均评分  平台数  最早日期   │
│  ✅ 分析结果        │                                    │
│  ┌─┬─┬─┬─┐        │                                    │
│  │ │ │ │ │        │                                    │
│  └─┴─┴─┴─┘        │                                    │
│                    │                                    │
└────────────────────┴────────────────────────────────────┘
     5/8                    3/8
```

**Streamlit 实现：**
```python
left, right = st.columns([5, 3], gap="large")

with left:
    # 数据配置卡片
    with st.container():
        st.markdown("#### 📋 数据配置")
        builtin_mode = st.toggle("内置数据")
        store_type = st.selectbox("门店类型", STORE_TYPES)
        llm_mode = st.selectbox("LLM模式", ["demo", "live"])
    
    # 上传区
    uploaded = st.file_uploader(...)
    
    # 分析按钮
    st.button("🚀 开始分析", type="primary", use_container_width=True)

with right:
    tab1, tab2, tab3 = st.tabs(["CSV格式说明", "示例数据", "数据概况"])
    with tab1:
        # 格式说明
    with tab2:
        # 示例数据预览
    with tab3:
        # 数据概况 metrics
```

---

### 4.2 数据看板 (Dashboard)

**布局结构：**
```
┌─────────────────────────────────────────────────────────┐
│ 📊 数据看板              [导出] [评测] [追踪]              │
├─────────────────────────────────────────────────────────┤
│ ┌────┐  ┌────┐  ┌────┐  ┌────┐                          │
│ │ 28 │  │2.5 │  │ 22 │  │ 22 │                          │
│ └────┘  └────┘  └────┘  └────┘                          │
├────────────────────┬────────────────────────────────────┤
│                    │ [审核队列 | Harness状态]            │
│  ≡ 三大问题洞察     │                                    │
│                    │                                    │
│  ┌──────────────┐  │  ┌─────────────────────────────┐   │
│  │█ 等待时间过长 │  │  │ 差评回复审核队列            │   │
│  │█ ●高严重      │  │  │ r001 ... ●高 ✗ [审核]       │   │
│  │█ 提及7次...   │  │  │ r002 ... ●中 ⚠ [审核]       │   │
│  │█ 建议措施...  │  │  │ ...                         │   │
│  └──────────────┘  │  │ 1/3 ◀ ▶                     │   │
│                    │  └─────────────────────────────┘   │
│  ┌──────────────┐  │                                    │
│  │█ 产品品质问题 │  │  ┌─────────────────────────────┐   │
│  │█ ●中严重      │  │  │ AI工作流可靠性检查          │   │
│  └──────────────┘  │  │ ✓ 输入校验 28条有效  [通过] │   │
│                    │  │ ✓ Schema约束 ...    [通过]  │   │
│  ┌──────────────┐  │  │ ◷ 安全检查 ...      [进行中]│   │
│  │█ 服务质量差   │  │  └─────────────────────────────┘   │
│  │█ ●中严重      │  │                                    │
│  └──────────────┘  │                                    │
│                    │                                    │
└────────────────────┴────────────────────────────────────┘
        5/10                    5/10
```

**Streamlit 实现：**
```python
# 顶部指标卡
m1, m2, m3, m4 = st.columns(4, gap="medium")

# 主内容区双栏
left, right = st.columns([5, 5], gap="medium")

with left:
    st.markdown("### ≡ 三大问题洞察")
    for issue in issues:
        issue_card(...)

with right:
    tab_queue, tab_harness = st.tabs(["📋 审核队列", "🛡️ Harness状态"])
    with tab_queue:
        for draft in drafts:
            queue_item(...)
        pagination()
    with tab_harness:
        harness_status()
```

---

### 4.3 回复审核 (Reply Review)

**布局结构：**
```
┌─────────────────────────────────────────────────────────┐
│ ✏️ 回复审核    [22 待审]                                  │
├─────────────────────────────────────────────────────────┤
│ [全部|待审核|需修改|已拦截|已处理]                         │
├────────────────────┬────────────────────────────────────┤
│                    │                                    │
│  📋 待处理队列 22条 │  💬 AI 回复草稿 ← r001            │
│                    │  ┌─────────────────────────────┐   │
│  ┌──────────────┐  │  │ ✓ 安全  ⏳ 待审核           │   │
│  │ r001 咖啡... │  │  └─────────────────────────────┘   │
│  │ ●高  ✗    ›  │  │                                    │
│  └──────────────┘  │  📝 原始评论                        │
│  ┌──────────────┐  │  ┌─────────────────────────────┐   │
│  │ r002 蛋糕...●│  │  │ 等了四十分钟才上咖啡...      │   │
│  │ ●中  ⚠    ✓  │  │  └─────────────────────────────┘   │
│  └──────────────┘  │  大众点评 ⭐ 1/5  2026-04-20       │
│                    │                                    │
│  ┌──────────────┐  │  🛡️ 安全检测结果                  │
│  │ r003 面包... │  │  ┌────┬────┬────┬────┐            │
│  │ ●低  ✓    ›  │  │ │ ✓  │ ✓  │ ✓  │ ✓  │            │
│  └──────────────┘  │ └────┴────┴────┴────┘            │
│                    │ 安全 违规词 敏感 合规              │
│  1/3  ◀ ▶          │                                    │
│                    │  ✏️ 编辑回复内容                   │
│                    │  [文本编辑区 57/500]               │
│                    │                                    │
│                    │  [✅ 批准] [📝 保存] [❌ 驳回]     │
│                    │                                    │
└────────────────────┴────────────────────────────────────┘
        5/12                    7/12
```

**Streamlit 实现：**
```python
# 筛选标签
filters = st.columns(5, gap="small")
for i, (key, label) in enumerate([("all", "全部"), ("pending", "待审核"), ...]):
    with filters[i]:
        st.button(label, type="primary" if active else "secondary")

# 主内容双栏
left, right = st.columns([5, 7], gap="medium")

with left:
    for draft in page_items:
        queue_item(...)
    pagination()

with right:
    # 详情卡片
    with st.container():
        st.markdown("### 💬 AI 回复草稿")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(status_badge("pass"), unsafe_allow_html=True)
        with col2:
            st.markdown(status_badge("pending"), unsafe_allow_html=True)
        
        st.markdown("#### 📝 原始评论")
        st.info(original_text)
        
        st.markdown("#### 🛡️ 安全检测")
        c1, c2, c3, c4 = st.columns(4)
        # 4个检测项...
        
        edited = st.text_area("编辑回复", height=120)
        st.caption(f"{len(edited)}/500")
        
        b1, b2, b3 = st.columns([1, 1, 1])
        with b1:
            st.button("✅ 批准发布", type="primary")
        with b2:
            st.button("📝 保存修改")
        with b3:
            with st.popover("❌ 驳回"):
                st.text_area("驳回原因")
                st.button("确认驳回")
```

---

### 4.4 追踪与评测 (Trace & Eval)

**布局结构：**
```
┌─────────────────────────────────────────────────────────┐
│ 🔍 追踪与评测                                             │
├─────────────────────────────────────────────────────────┤
│ [日期筛选] [运行类型] [最新运行]                          │
├────────────────────┬────────────────────────────────────┤
│                    │ [评测摘要 | 可靠性指标 | 评测记录]   │
│  执行步骤(共10步)   │                                    │
│  [已完成]          │  ┌─────────────────────────────┐   │
│                    │  │ 📊 分类准确率    情绪准确率  │   │
│   ● 输入校验 ✓     │  │      71%           93%      │   │
│   │ 15条→15条 5ms  │  │ 目标≥70%         目标≥80%   │   │
│   ● 数据清洗 ✓     │  │  ─────────────────────────  │   │
│   ● 评论分类 ✓     │  │ 📊 综合评分      评测样例   │   │
│   ● ...            │  │     82/100         28       │   │
│   ○ 人工审批 ◷     │  └─────────────────────────────┘   │
│   ● 评测运行 ✓     │                                    │
│                    │  ┌─────────────────────────────┐   │
│                    │  │ ⏱️ 15.59s  🔄 2次  ↩️ 0%   │   │
│                    │  │ 🛡️ 0%      📝 0次  💾 0次  │   │
│                    │  └─────────────────────────────┘   │
│                    │                                    │
│                    │  ┌─────────────────────────────┐   │
│                    │  │ 📜 评测记录                 │   │
│                    │  │ ● 10:30 eval-001 92% [通过] │   │
│                    │  │ ● 10:15 eval-002 78% [通过] │   │
│                    │  └─────────────────────────────┘   │
│                    │                                    │
│                    │  [🧪 运行评测] [📥 导出] [📋复制] │
│                    │                                    │
└────────────────────┴────────────────────────────────────┘
       11/20                  9/20
```

**Streamlit 实现：**
```python
# 筛选栏
c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    st.date_input("日期")
with c2:
    st.selectbox("运行类型", ["全部运行"])
with c3:
    st.selectbox("排序", ["最新运行"])

# 主内容双栏
left, right = st.columns([11, 9], gap="medium")

with left:
    st.markdown("### 执行步骤 (共10步)")
    st.markdown("<span style='color: #27AE60;'>●</span> 已完成", unsafe_allow_html=True)
    
    for i, step in enumerate(steps):
        trace_timeline_item(i+1, ...)

with right:
    tab1, tab2, tab3 = st.tabs(["📊 评测摘要", "📈 可靠性指标", "📜 评测记录"])
    
    with tab1:
        # 2x2 指标网格
        r1 = st.columns(2)
        r2 = st.columns(2)
        # metrics...
    
    with tab2:
        # 4x2 可靠性网格
        for row in range(2):
            cols = st.columns(4, gap="small")
            # reliability_metric(...)
    
    with tab3:
        for run in eval_runs:
            eval_history_item(...)
    
    # 操作按钮
    b1, b2, b3 = st.columns([1, 1, 1])
    with b1:
        st.button("🧪 运行评测", type="primary")
    with b2:
        st.download_button("📥 导出报告", ...)
    with b3:
        with st.popover("📋 复制 Trace"):
            st.code(trace_text)
```

---

## 5. Streamlit 落地方式总结

### 5.1 布局组件使用原则

| 组件 | 使用场景 | 注意事项 |
|------|----------|----------|
| `st.columns` | 页面分栏、指标卡排列、按钮组 | 使用 `gap="medium"` 或 `"small"` 控制间距 |
| `st.container` | 卡片包裹、区域分组 | 配合 `border=True` 实现边框卡片 |
| `st.tabs` | 右侧面板切换、内容分区 | 上传页/数据看板/追踪页右侧使用 |
| `st.expander` | 证据评论展开、详细数据折叠 | 默认折叠减少信息密度 |
| `st.dataframe` | 示例数据预览、评测记录 | 覆盖样式匹配设计规范 |
| `st.metric` | 简单指标展示（带delta） | 样式受限，复杂指标用自定义HTML |
| `st.progress` | 准确率可视化、完成度 | 颜色需要CSS覆盖 |

### 5.2 自定义 CSS 注入方式

每个页面顶部注入全局样式：

```python
st.markdown("""
<style>
    /* 页面背景 */
    .stApp { background: #FAFBF7; }
    
    /* 卡片容器 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF !important;
        border: 1px solid #E8E0D5 !important;
        border-radius: 14px !important;
        padding: 20px !important;
    }
    
    /* 主按钮 */
    button[kind="primary"] {
        background: linear-gradient(135deg, #6B4C3B 0%, #5C3D2E 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        color: #FFF !important;
        font-weight: 600 !important;
    }
    
    /* 表格 */
    div[data-testid="stDataFrame"] th {
        background: #F5F0E8 !important;
        color: #4A3728 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)
```

### 5.3 状态管理

使用 `st.session_state` 保持页面状态：

```python
# 初始化
if "current_batch_id" not in st.session_state:
    st.session_state.current_batch_id = None
if "reply_selected_idx" not in st.session_state:
    st.session_state.reply_selected_idx = 0
if "queue_page" not in st.session_state:
    st.session_state.queue_page = 0

# URL参数同步
batch_id = st.session_state.get("current_batch_id")
if not batch_id:
    qp_bid = st.query_params.get("batch_id")
    if qp_bid:
        st.session_state.current_batch_id = qp_bid
        batch_id = qp_bid
```

---

## 6. 组件调用速查表

```python
# === 页面结构 ===
st.set_page_config(page_title="...", page_icon="☕", layout="wide")
st.markdown("<style>...</style>", unsafe_allow_html=True)

# === 标题区 ===
page_header("📤 上传评论数据", "副标题说明...")

# === 布局 ===
left, right = st.columns([5, 3], gap="large")
with left:
    with st.container(border=True):
        pass
tab1, tab2, tab3 = st.tabs(["标签1", "标签2", "标签3"])

# === 组件 ===
metric_card("标签", value, "图标", color="#4A3728")
status_badge("passed")  # 返回 HTML 字符串
issue_card(rank=1, issue_name="...", severity="high", ...)
queue_item("r001", "评论摘要...", "high", "blocked", is_selected=True)
trace_timeline_item(1, "输入校验", "15条→15条", "passed", 5)
reliability_metric("⏱️", "15.59s", "总耗时")

# === 交互 ===
st.button("标签", type="primary"|"secondary")
st.toggle("标签")
st.selectbox("标签", options)
st.file_uploader("标签", type=["csv"])
st.text_area("标签", height=120)
with st.expander("标题"):
    pass
with st.popover("标题"):
    pass
```

---

**文档版本**: v1.0  
**适用范围**: 小店评论经营助手 Streamlit 前端四页  
**更新日期**: 2026-05-13
