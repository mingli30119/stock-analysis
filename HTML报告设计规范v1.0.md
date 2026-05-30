# 个股深度研报 HTML 设计规范 v1.1

> 适用于：股票分析、投资研究、财经报告
> 更新日期：2026-05-01
> 作者：@明立玩AI

---

## 一、设计理念

### 核心原则
1. **信息密度适中** - 关键数据前置，结论置顶，避免过度折叠
2. **红涨绿跌直观** - K线颜色严格遵循：阳线(close≥open)红色，阴线(close<open)绿色；成交量柱同步分色（阳线日红柱，阴线日绿柱），符合中国股民直觉
3. **双主题兼容** - 深色模式适合长时间盯盘，浅色模式适合打印或明亮环境
4. **图表"去噪"** - 去除白色网格线，减少视觉干扰，聚焦价格趋势
5. **层级分明** - 通过卡片、阴影、边框和字号梯度构建清晰的阅读层次

---

## 二、色彩系统

### 2.1 双主题配色

采用**深色/浅色**一键切换，以红涨绿跌、金棕强调为核心语义。

| 色彩角色 | 深色模式（默认） | 浅色模式 | 用途 |
|---------|----------------|---------|------|
| 页面背景 | `#0C0F15` | `#FDF8F0` | 全局底色 |
| 卡片背景 | `#1A1C24` | `#FFFBF5` | 主要内容容器 |
| 次级卡片/表格背景 | `#1E2029` | `#FEF5E7` | 表格、情景卡、信息区块 |
| 边框/分割线 | `#2A2D3A` | `#E2CFA2` | 卡片边框、表格线、分割 |
| 主文字 | `#E8E9EC` | `#2A1F12` | 标题、核心数据 |
| 次要文字 | `#B0B3BE` | `#6B5634` | 正文、表格内容 |
| 辅助文字 | `#7A7D8A` | `#9C8B6E` | 标签、提示、时间戳 |
| 上涨/买入 | `#F55656` | `#DC2626` | K线阳线、涨跌幅、正收益 |
| 下跌/卖出 | `#28C75B` | `#16A34A` | K线阴线、止损信号、悲观情景 |
| 金色/重点 | `#D4A853` | `#B38A3C` | 标题强调、关键结论、标签边框 |
| 浅金 | `#E3C26D` | `#D4A853` | Hero区域数值、标签文字 |
| 蓝色（MA5） | `#4A90D9` | `#2563EB` | 图表均线、链接 |
| 橙色（警告） | `#E8923A` | `#C2410C` | 中等评分、止损信号、威胁信息 |

### 2.2 CSS变量定义

```css
:root {
  --bg: #0c0f15;
  --card-bg: #1a1c24;
  --card-bg-alt: #1e2029;
  --border: #2a2d3a;
  --text-primary: #e8e9ec;
  --text-secondary: #b0b3be;
  --text-muted: #7a7d8a;
  --red-up: #f55656;
  --green-down: #28c75b;
  --gold: #d4a853;
  --gold-light: #e3c26d;
  --blue-accent: #4a90d9;
  --orange-warn: #e8923a;
  --shadow: 0 4px 20px rgba(0,0,0,0.3);
  --radius: 10px;
  --transition: 0.2s ease;
}

body.light-mode {
  --bg: #fdf8f0;
  --card-bg: #fffbf5;
  --card-bg-alt: #fef5e7;
  --border: #e2cfa2;
  --text-primary: #2a1f12;
  --text-secondary: #6b5634;
  --text-muted: #9c8b6e;
  --red-up: #dc2626;
  --green-down: #16a34a;
  --gold: #b38a3c;
  --shadow: 0 4px 20px rgba(162,125,57,0.08);
}
```

### 2.3 渐变使用

- **Hero区深色**：`linear-gradient(105deg, #1C1010 0%, #2C1A1A 50%, #3D2424 100%)`
- **Hero区浅色**：`linear-gradient(105deg, #FEF5E7, #FFFBF5)`
- **结论区深色**：`linear-gradient(135deg, #1E1A10 0%, #241F14 100%)`
- **结论区浅色**：`linear-gradient(135deg, #FFF9F0, #FEF5E7)`
- **表头渐变**：`linear-gradient(180deg, #F55656 0%, #C0392B 100%)`（浅色模式专用）

---

## 三、字体与排版

### 3.1 字体族

```css
--font-sans: "PingFang SC", "Microsoft YaHei", -apple-system, sans-serif;
--font-mono: "JetBrains Mono", "SF Mono", "Consolas", monospace;
```

### 3.2 字号层级

| 元素 | 字号 | 字重 | 行高 | 用途 |
|------|------|------|------|------|
| 价格大字 | 56px | 900 | 1 | Hero区最新价 |
| 涨跌幅标识 | 20px | 700 | - | Hero区涨跌幅 |
| 数据值 | 20-24px | 700-800 | - | 关键指标数值 |
| 卡片标题 | 18px | 700 | - | 各卡片标题 |
| 正文 | 14px | 400 | 1.7 | 段落文字 |
| 表格内容 | 13px | 400 | - | 表格单元格 |
| 辅助文字 | 11-12px | 400-500 | - | 标签、提示 |

### 3.3 字重层级

- **关键数据**：800-900
- **标题**：700
- **强调文字**：600
- **正文**：400-500

---

## 四、间距与布局

### 4.1 间距规范

| 元素 | 间距/尺寸 |
|------|----------|
| 主容器最大宽度 | 1300px，水平居中，左右内边距 20px |
| 卡片内边距 | 22px 28px |
| 卡片间距（垂直） | 20px |
| Hero区内边距 | 28px 32px |
| 结论区内边距 | 22px 28px |
| 网格间距（2列/3列） | 20px / 16px |
| 卡片标题与内容间距 | margin-bottom: 16px，分割线 2px solid |
| 评分条行间距 | margin: 6px 0 |
| K线底部指标行 | margin-top: 18px，上方 2px 分割线 |

### 4.2 圆角规范

- **主卡片、Hero、结论区**：10px
- **情景卡片、标签胶囊**：8-14px
- **按钮/导航标签**：16px

---

## 五、组件规范

### 5.1 顶部导航（Top Nav）

```css
.top-nav {
  position: sticky; top: 0; z-index: 100;
  background: rgba(10,12,18,0.92);
  backdrop-filter: blur(12px);
  border-bottom: 2px solid var(--gold-light);
  padding: 10px 28px;
  display: flex; align-items: center; justify-content: space-between;
}
```

**结构：**
- Logo图标（34x34px，红色渐变背景）
- 股票名称（17px，字重700）
- 股票代码（12px，等宽字体）
- 导航链接（12px，圆角16px）
- 主题切换按钮

### 5.2 Hero行情卡片

**特点：**
- 暗色渐变背景，叠加右上角径向金色光晕
- 左：价格（56px） + 涨跌幅标签（半透明红底，字号20px）
- 中：四个指标项（市盈率、目标价、盈亏比、成交额），数值金色，标签白色半透明
- 右：标签组（央企背景等），半透明白底金色边框

```html
<div class="hero">
  <div class="hero-price-block">
    <span class="hero-price">15.05</span>
    <span class="hero-change">+1.55%</span>
  </div>
  <div class="hero-meta">
    <div class="hero-meta-item">
      <div class="val">20.1x</div>
      <div class="label">市盈率(TTM)</div>
    </div>
    <!-- 更多指标 -->
  </div>
  <div class="hero-tags">
    <span class="hero-tag">央企背景</span>
    <!-- 更多标签 -->
  </div>
</div>
```

### 5.3 结论置顶卡片

**特点：**
- 顶部绝对定位"核心结论"标签（金色背景，黑色文字）
- 内部：加粗结论文字（20px），灰色正文，底部标签组

```html
<div class="conclusion-top">
  <div class="big-verdict">🎯 综合结论：配置型标的，择时参与</div>
  <div class="verdict-detail">详细说明...</div>
  <div class="verdict-tags">
    <span class="tag">配置型</span>
    <!-- 更多标签 -->
  </div>
</div>
```

### 5.4 卡片（Card）

```css
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px 28px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
  transition: var(--transition);
}
.card:hover {
  box-shadow: 0 8px 30px rgba(0,0,0,0.5);
  border-color: var(--gold);
}
```

**卡片头部：**
```html
<div class="card-header">
  <span class="icon">📊</span>
  <h2>标题</h2>
  <span class="sub">副标题</span>
</div>
```

### 5.5 表格（Table）

```css
table.cons {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: var(--card-bg-alt);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  margin: 12px 0;
}
table.cons thead th {
  background: linear-gradient(180deg, #2c1a1a 0%, #1c1010 100%);
  color: #fff;
  font-weight: 600;
  padding: 10px 12px;
  text-align: left;
  font-size: 12px;
  letter-spacing: 1px;
}
table.cons tbody tr {
  border-bottom: 1px dashed var(--border);
}
table.cons tbody tr:hover {
  background: rgba(255,255,255,0.02);
}
table.cons tbody td {
  padding: 9px 12px;
  vertical-align: middle;
  color: var(--text-secondary);
}
.val-up { color: var(--red-up); font-weight: 600; }
.val-down { color: var(--green-down); font-weight: 600; }
```

### 5.6 评分条（Score Bar）

```html
<div class="score-bar">
  <span class="score-label">基本面质量</span>
  <div class="score-track">
    <div class="score-fill" style="width:70%;"></div>
  </div>
  <span class="score-num">21/30</span>
</div>
```

**样式：**
- 标签右对齐，90px固定宽度
- 轨道：`#2A2D3A`（深色）或`#F0E4CE`（浅色），高度8px
- 填充：金色`--gold`，宽度百分比表示得分
- 右侧分数：13px等宽加粗

### 5.7 情景卡片（Scenario）

```html
<div class="scenario bear">
  <strong>🐻 悲观</strong>
  <div class="prob">概率20%</div>
  营收240-250亿<br>净利5-8亿<br>PE 25-40x
</div>
```

**样式：**
- 左侧4px色条：悲观绿色，乐观红色，基准金色
- 内部居中对齐，概率文字11px次级色

### 5.8 产业链SVG

```html
<div class="chain-svg">
  <svg viewBox="0 0 800 170" xmlns="http://www.w3.org/2000/svg">
    <!-- 上游 -->
    <rect x="20" y="45" width="150" height="80" fill="var(--card-bg-alt)" 
          stroke="#d4a853" stroke-width="2" rx="10"/>
    <text x="95" y="72" text-anchor="middle" font-weight="700" 
          font-size="15" fill="#fff">上游·种植</text>
    
    <!-- 箭头 -->
    <line x1="170" y1="85" x2="240" y2="85" stroke="#d4a853" 
          stroke-width="2" marker-end="url(#arrow)"/>
    
    <!-- 中游（核心） -->
    <rect x="240" y="25" width="220" height="120" fill="var(--card-bg-alt)" 
          stroke="#f55656" stroke-width="3" rx="12"/>
    <text x="350" y="55" text-anchor="middle" font-weight="800" 
          font-size="17" fill="#f55656">中游·制糖</text>
    
    <!-- 下游 -->
    <rect x="540" y="45" width="210" height="80" fill="var(--card-bg-alt)" 
          stroke="#d4a853" stroke-width="2" rx="10"/>
    
    <!-- 箭头定义 -->
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="10" 
              refX="9" refY="4" orient="auto">
        <polygon points="0 0,10 4,0 8" fill="#d4a853"/>
      </marker>
    </defs>
  </svg>
</div>
```

### 5.9 止损信号列表

```html
<ul class="alert-list">
  <li><strong>1.</strong> 糖价跌破5000元/吨 → 行业亏损</li>
  <li><strong>2.</strong> 进口配额大幅放松 → 低价糖冲击</li>
</ul>
```

**样式：**
- 每项左侧4px橙色边框
- 背景为次级卡片色

---

### 5.10 评级徽章（Rating Callout）

用于质量评分结果（如 B+ 73.0/100）的突出展示。

```html
<div class="rating-callout">
  <div class="badge">B+</div>
  <div class="body">
    <div class="title">73.0 / 100 · 有吸引力的周期成长标的</div>
    <div class="desc">行业地位强、盈利拐点确认，但大股东减持和募投延期拖累治理评分。</div>
  </div>
</div>
```

```css
.rating-callout {
  background: linear-gradient(135deg, #1e1a10, #241f14);
  border: 2px solid var(--gold);
  border-radius: var(--radius);
  padding: 18px 24px; margin-top: 16px;
  display: flex; align-items: center; gap: 16px;
}
.rating-callout .badge {
  min-width: 64px; height: 64px; border-radius: 50%;
  background: var(--gold); color: #000;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 900;
}
.rating-callout .body .title { font-size: 16px; font-weight: 700; color: #fff; }
.rating-callout .body .desc { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
/* 浅色模式 */
body.light-mode .rating-callout { background: linear-gradient(135deg, #fff9f0, #fef5e7); }
body.light-mode .rating-callout .body .title { color: var(--text-primary); }
```

### 5.11 综合结论高亮（Verdict Highlight）

用于 Step 8 综合结论的视觉强化，替代普通表格。

```html
<div class="verdict-highlight">
  <div class="judgment">产业逻辑硬 + 业绩反转中，弹性与风险并存</div>
  <div class="verdict-grid">
    <div class="verdict-item">
      <div class="v-val" style="color: var(--orange-warn);">⚠️ 中</div>
      <div class="v-label">风险等级</div>
    </div>
    <!-- 重复4列：风险等级、操作建议、仓位上限、持有周期 -->
  </div>
</div>
```

```css
.verdict-highlight { background: var(--card-bg-alt); border-radius: 10px; padding: 18px 22px; }
.verdict-highlight .judgment { font-size: 22px; font-weight: 800; color: var(--gold); text-align: center; }
.verdict-highlight .verdict-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.verdict-highlight .verdict-item { text-align: center; padding: 8px; }
.verdict-highlight .verdict-item .v-val { font-size: 18px; font-weight: 800; }
.verdict-highlight .verdict-item .v-label { font-size: 11px; color: var(--text-muted); }
/* 浅色模式 */
body.light-mode .verdict-highlight { background: #fef5e7; }
body.light-mode .verdict-highlight .judgment { color: var(--gold); }
```

### 5.12 SVG 文字双主题（.svg-hdr / .svg-sub）

产业链 SVG 文字不再硬编码 `fill="#fff"`，改用 CSS class 支持双主题切换。

```css
.chain-svg .svg-hdr { fill: #e8e9ec; }       /* 深色：标题白 */
.chain-svg .svg-sub { fill: #b0b3be; }       /* 深色：副文灰 */
body.light-mode .chain-svg .svg-hdr { fill: #2a1f12; }   /* 浅色：标题黑 */
body.light-mode .chain-svg .svg-sub { fill: #6b5634; }   /* 浅色：副文褐 */
```

### 5.13 MathJax 数学公式渲染

使用 MathJax 3 渲染 LaTeX 数学公式，支持 `$...$` (行内) 和 `\(...\)` (行内) 分隔符。

```html
<script>
  MathJax = { tex: { inlineMath: [['$','$'], ['\\(','\\)']] } };
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
```

**适用场景：** 价格敏感度公式、财务比率、PE 计算公式等。

### 5.14 弹性树卡片

业绩弹性树使用 CSS flex 多色卡片替代 ASCII art。

- 顶层：金色边框渐变背景的总利润节点
- 中层：红色半透明（核心业务）、金色半透明（次要业务）的 flex 卡片
- 数字使用 `\(...\)` 包裹由 MathJax 渲染

### 5.15 公式卡片

敏感度公式使用结构化卡片布局，每张卡片包含：
- 顶部标签行（产能/假设说明）
- 中部公式行（monospace 字体，`&times;` `&minus;` 等 HTML 实体）
- 结果数字用 `color: var(--red-up)` 加粗突出

---

## 六、图表配置（ECharts）

### 6.1 饼图（主营业务构成）

```javascript
echarts.init(document.getElementById('chart-business-pie')).setOption({
  tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    data: [
      { value: 34.4, name: '加工糖' },
      { value: 24.4, name: '自产糖' },
      // ...
    ],
    label: { fontSize: 11, color: colors.textSecondary },
    color: ['#f55656', '#d4a853', '#e8923a', '#b38a3c', '#e2cfa2']
  }]
});
```

### 6.2 K线图（含MA均线+成交量）

**OHLC 数据格式（★ 关键）：**

K线数据必须按 ECharts candlestick 标准格式构建：`[open, close, low, high]`

从原始数据（akshare 日K线）提取时注意字段顺序：
```
原始: {date, open, high, low, close, volume}
转换: rawData = [date, open, high, low, close, vol]  // JS 原始数组
ohlc = [open, close, low, high]                      // ECharts candlestick 格式
```

**如果顺序错误（如把 high 当 close），K线颜色会全部错乱。**

**双网格布局：**
- Grid 1（K线）：`left: 9%, right: 6%, top: 12%, height: 55%`
- Grid 2（成交量）：`left: 9%, right: 6%, top: 74%, height: 14%`

**关键配置：**
- 坐标轴：无水平分割线（`splitLine: { show: false }`）
- 日期显示：只显示"月-日"，字体大小9px，间隔显示
- Y轴成交量：单位显示"万"，即原始成交量除以10000
- ★ K线颜色：阳线(close≥open) `#F55656`（深色）/ `#DC2626`（浅色），阴线(close<open)对应绿色
- 均线：MA5蓝色，MA20绿色，MA60橙色，线宽1.5px，无标记点
- ★ 成交量柱：每根柱子单独着色，`close >= open` → 红柱（`rgba(245,86,86,0.35)`），`close < open` → 绿柱（`rgba(40,199,91,0.35)`），不可使用单一颜色
- 十字光标提示：tooltip 中 `k.data[0]`=开, `[1]`=收, `[2]`=低, `[3]`=高（与 ohlc 数组索引一致）
- 底部缩放：内置dataZoom滑块

```javascript
echarts.init(document.getElementById('chart-kline-full')).setOption({
  grid: [
    { left: '9%', right: '6%', top: '12%', height: '55%' },
    { left: '9%', right: '6%', top: '74%', height: '14%' }
  ],
  xAxis: [
    { type: 'category', data: dateLabels, gridIndex: 0,
      axisLabel: { color: c.textMuted, fontSize: 9, interval: 5 },
      splitLine: { show: false } },
    { type: 'category', data: dateLabels, gridIndex: 1, show: false }
  ],
  yAxis: [
    { scale: true, gridIndex: 0, splitLine: { show: false } },
    { scale: true, gridIndex: 1, 
      axisLabel: { formatter: '{value}万' }, splitLine: { show: false } }
  ],
  dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }],
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { data: ['K线', 'MA5', 'MA20', 'MA60'], top: 0 },
  series: [
    { name: 'K线', type: 'candlestick', data: ohlc, 
      itemStyle: { color: c.upColor, color0: c.downColor } },
    { name: 'MA5', type: 'line', data: ma5, smooth: true,
      lineStyle: { width: 1.5, color: c.ma5Color }, showSymbol: false },
    { name: 'MA20', type: 'line', data: ma20, smooth: true,
      lineStyle: { width: 1.5, color: c.ma20Color }, showSymbol: false },
    { name: 'MA60', type: 'line', data: ma60, smooth: true,
      lineStyle: { width: 1.5, color: c.ma60Color }, showSymbol: false },
    { name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
      itemStyle: { color: c.volColor } }
  ]
});
```

---

## 七、主题切换机制

通过`body`的类`light-mode`切换CSS变量集合。

```javascript
const toggleBtn = document.getElementById('themeToggle');
toggleBtn.addEventListener('click', () => {
  document.body.classList.toggle('light-mode');
  toggleBtn.textContent = document.body.classList.contains('light-mode') 
    ? '🌙 深色模式' : '☀️ 浅色模式';
  // 重新渲染图表以适配颜色
  renderCharts();
});
```

**图表颜色适配：**
```javascript
function getThemeColors() {
  const isLight = document.body.classList.contains('light-mode');
  return {
    textColor: isLight ? '#2a1f12' : '#e8e9ec',
    upColor: isLight ? '#dc2626' : '#f55656',
    downColor: isLight ? '#16a34a' : '#28c75b',
    // ...
  };
}
```

---

## 八、响应式断点

| 断点 | 规则 |
|------|------|
| ≤850px | 双列/三列网格强制为单列；Hero区域垂直排列，价格缩小至40px |
| 通用 | 图片和SVG宽度`max-width: 100%`，高度自适应 |

```css
@media (max-width:850px) {
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
  .hero { flex-direction: column; align-items: flex-start; }
  .hero-price { font-size: 40px; }
}
```

---

## 九、交互规范

### 9.1 导航高亮

```javascript
window.addEventListener('scroll', () => {
  let cur = '';
  sections.forEach(s => { 
    if (window.scrollY >= s.offsetTop - 100) cur = s.id; 
  });
  navs.forEach(a => {
    a.classList.remove('active');
    if (a.getAttribute('href') === '#' + cur) a.classList.add('active');
  });
});
```

### 9.2 平滑滚动

```javascript
document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', function(e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
```

### 9.3 图表自适应

```javascript
window.addEventListener('resize', () => {
  pieChart && pieChart.resize();
  klineChart && klineChart.resize();
});
```

---

## 十、数据格式规范

| 数据类型 | 格式 | 示例 |
|---------|------|------|
| 金额单位 | 亿元/万元 | "营收265亿""4.40亿" |
| 成交量单位 | 万手 | 图表Y轴显示`{value}万` |
| PE显示 | 保留一位小数 | 20.1x |
| 目标价范围 | 用"-"连接 | 18-20元 |
| 百分比 | 保留两位小数 | 16.27% |
| 日期格式 | YYYY-MM-DD或MM-DD | 2026-04-30或04-30 |

---

## 十一、页面结构模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>股票名称 代码 · 深度研报</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
  <style>/* CSS变量 + 组件样式 */</style>
</head>
<body>
  <!-- 顶部导航 -->
  <nav class="top-nav">...</nav>
  
  <div class="container">
    <!-- Hero行情卡片 -->
    <div class="hero">...</div>
    
    <!-- 结论置顶 -->
    <div class="conclusion-top">...</div>
    
    <!-- 公司画像 + 新闻 -->
    <div class="grid-2">...</div>
    
    <!-- 主营业务饼图 + 关键财务指标 -->
    <div class="grid-2">...</div>
    
    <!-- K线图 -->
    <div class="card">
      <div id="chart-kline-full"></div>
      <div class="kpi-info-row">...</div>
    </div>
    
    <!-- Step 1-7 -->
    <div class="card" id="macro">...</div>
    <div class="card" id="chain">...</div>
    <div class="card" id="quality">...</div>
    <div class="card" id="elasticity">...</div>
    <div class="card" id="risk">...</div>
    <div class="card" id="valuation">...</div>
    <div class="card" id="compare">...</div>
    
    <!-- 页脚 -->
    <footer>...</footer>
  </div>
  
  <script>/* 图表渲染 + 交互逻辑 */</script>
</body>
</html>
```

---

## 十二、文件命名规范

- **HTML文件**：`个股研究-{股票名称}.html` 或 `{股票名称}-深度研报.html`
- **数据文件**：`data_{股票代码}.json`
- **Markdown文件**：`个股研究-{股票名称}.md`

---

## 十三、检查清单

### 设计检查
- [ ] 双主题切换正常
- [ ] 红涨绿跌配色正确
- [ ] 所有卡片有hover效果
- [ ] 表格有hover效果
- [ ] 圆角统一为10px
- [ ] 间距符合规范

### 内容检查
- [ ] Hero区4个关键指标
- [ ] 结论置顶卡片
- [ ] 公司画像 + 新闻
- [ ] 主营业务饼图 + 关键财务指标
- [ ] K线图含MA5/20/60
- [ ] K线底部4个指标
- [ ] Step 1-7完整
- [ ] 产业链SVG
- [ ] 评分条
- [ ] 情景分析
- [ ] 止损信号列表

### 交互检查
- [ ] 导航滚动高亮
- [ ] 平滑滚动定位
- [ ] 图表响应式调整
- [ ] 主题切换时图表重绘

---

## 十四、常见问题

### Q1: 如何添加新的Step？
复制现有Step卡片结构，修改id和内容即可。记得在导航中添加对应链接。

### Q2: 如何修改配色？
修改CSS变量中的颜色值，主题切换会自动适配。

### Q3: 如何优化K线图性能？
- 限制数据量（建议60-120个交易日）
- 使用dataZoom内置缩放
- 关闭不必要的动画效果

### Q4: 如何适配移动端？
已包含响应式断点（850px），移动端自动切换为单列布局。

---

## 十五、更新日志

### v1.1 (2026-05-01)
- 新增 `.rating-callout` 评级徽章组件
- 新增 `.verdict-highlight` 综合结论高亮组件
- 新增 `.svg-hdr` / `.svg-sub` SVG 文字双主题 CSS
- 新增 MathJax 数学公式渲染集成
- 新增弹性树卡片、公式卡片组件规范
- 明确 OHLC 数据格式 `[open, close, low, high]` 及常见错误
- 成交量柱分色逻辑（每柱单独着色，非单一颜色）
- 统一免责声明数据来源行

### v1.0 (2026-05-01)
- 初始版本
- 完整的双主题系统
- K线图含MA均线
- 产业链SVG
- 评分条组件
- 情景分析卡片

---

**文档维护：** @明立玩AI  
**技术栈：** HTML5 + CSS3 + ECharts 5.5.1  
**适用场景：** 股票分析、投资研究、财经报告
