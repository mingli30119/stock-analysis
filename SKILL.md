# 个股深度研究系统（三层架构版）

> 版本：v2.2 | 更新：2026-05-01 | 定位：三层架构 + 强制Step 0-8 + AI手写HTML

---

## 📋 快速导航

- [⚡ 使用方式](#使用方式)
- [🏗️ 三层架构](#三层架构)
- [📊 输出内容](#输出内容)
- [🎨 HTML手写规范](#html手写规范)
- [🔧 执行流程](#执行流程)

---

## ⚡ 使用方式

**当用户说"分析 XXX股票"时，AI一次性完成三阶段全流程（连续执行，中间不询问用户是否继续）：**

### Phase 1: 数据采集（3-5分钟）

```bash
cd G:/vibe/my-skills/stock-analysis-competition
python stock_full_report.py <股票代码>
```

**示例：**
```bash
python stock_full_report.py 600519  # 贵州茅台
python stock_full_report.py 600673  # 东阳光
```

**唯一输出：** `output/data_<股票代码>.json`（包含K线、财务、股东、业务构成等完整数据，供Phase 2/3使用）

**⚠️ Phase 1完成后立即进入Phase 2**，不要停下来询问用户。JSON只是数据中间产物。

---

### Phase 2: AI深度分析（30-60分钟）

**AI必须手动执行以下步骤：**

1. **读取数据：** `output/data_<股票代码>.json`
2. **执行MCP搜索：** 根据实际需要搜索（通常3-6次）
   - 行业趋势、市场规模
   - 竞争对手、市场份额
   - 券商研报、目标价
   - 最新新闻、政策动态
3. **逐步完成Step 0-8分析：** 严格按照分析框架，每个Step达到要求
4. **输出MD报告：** `output/个股研究-<股票名称>.md`

**⚠️ 三阶段连续执行，中间不中断：** Phase 2完成后**立即进入Phase 3**，不要停下来询问用户是否继续。MD报告只是中间产物，HTML才是最终交付物。

---

### Phase 3: HTML生成层（AI手动分批拼装 + 逐批机械校验）

> ⚠️ 写 HTML 只用 Write 工具。整个 Phase 3 只需 6 次 Write 调用，约 30 分钟，完全在单会话内完成。不要用 Python 替代。

**原理：** AI手写完整HTML——从范例提取结构参照，从 `shared/` 搬运CSS/JS，从MD报告提取内容。**分批 Write，每批写完后立即用 grep 对范例做机械校验，通过才继续。**

**核心规则：不靠记范例，靠每批 grep diff。**

**执行步骤：**

1. **读取模板：** `shared/template_base.css` + `shared/template_base.js`
2. **读取范例并提取参照：** `examples/个股研究-中国长城.html` → 用 grep 提取 nav 锚点列表、section id 列表，保存为临时参照文件
3. **读取校验规范：** `HTML手写参考.md` → 严格按「分批机械校验」表格逐批执行
4. **读取数据：** `output/个股研究-{股票名称}.md` + `output/data_{代码}.json`
5. **分批手写HTML（每批 = Write + grep校验）：**
   - 每批 ≤300行，用 **Write工具** 直接写HTML markup
   - **写完后立即跑该批对应的 grep 校验命令**（命令清单见 `HTML手写参考.md` § 分批机械校验）
   - 校验通过 → 下一批。校验失败 → grep 范例对应行 → 比对 → Edit 修正 → 重新校验
6. **合并：** 仅用 `cat` 做机械字节拼接
7. **终验：** 运行合并后终验命令（nav-id 配对 + 结构完整性），全部通过才输出最终文件
8. **输出：** `output/个股研究-{股票名称}.html`

### ⚠️ 分批手写规则（强制）

**禁止行为：**

| 禁止 | 原因 |
|------|------|
| ❌ **Python f-string/template 生成HTML** | 需要大量 `{{}}` 转义，易出错不可维护 |
| ❌ **Bash heredoc 生成HTML** | 多行HTML下经常EOF匹配失败 |
| ❌ **一次性写出整个HTML** | >300行文件必须分批，每批独立一个Write调用 |
| ❌ **用 `python -c` 拼接HTML字符串** | 属于Python生成，不是手写 |

**正确做法：**

| 操作 | 工具 | 说明 |
|------|------|------|
| 写入HTML内容 | **Write** | 直接写HTML markup，无转义问题 |
| 精确局部修改 | **Edit** | 替换特定行，不改动其他部分 |
| 机械合并部分文件 | **Bash `cat`** 或 **Python `file.read()`** | 仅读取+拼接字节，不生成任何markup |

**标准分批方案（~900行HTML）—— 每批三步：Read范例 → Write → grep：**

**参考范例：** `examples/个股研究-中国长城.html`（864行，金标准成品）

> ⚠️ **参考范例路径不可变。** 该文件位于 `examples/` 目录（稳定范例），禁止替换为 `output/` 下的生成结果。行号基于当前版本，如范例更新需同步修正行号。

| 批次 | Step 1: Read范例（先看再写） | Step 2: Write | Step 3: grep兜底 |
|------|---------------------------|---------------|------------------|
| Batch 0 | `Read 中国长城 line=1-160`（head+style段） | Write DOCTYPE + `<head>` + `<style>` | `grep -c '<style>'`=1, `grep 'echarts\|MathJax'` 确认CDN |
| Batch 1 | `Read 中国长城 line=163-240`（nav+hero+conclusion+profile网格） | Write `<body>` + nav + hero + conclusion + grid-2(公司画像+近期动态) | `grep -oc 'href="#'`=13, `grep -c 'hero-meta-item'`=4, `grep -c 'hero-tag'`≤5 |
| Batch 2 | `Read 中国长城 line=241-280`（饼图+财务+K线） | Write 饼图+财务grid-2 + K线card(kline-section) | `grep 'id="kline-section"'` 存在, `grep 'height:480px'` 存在 |
| Batch 3 | `Read 中国长城 line=281-450`（Step 0-3） | Write Step 0-3 卡片（mission/macro/chain/quality） | `grep -o 'id="[^"]*"'` → mission/macro/chain/quality 四者存在 |
| Batch 4 | `Read 中国长城 line=451-600`（Step 4-6） | Write Step 4-6 卡片（elasticity/risk/valuation） | `grep -o 'id="[^"]*"'` → elasticity/risk/valuation 三者存在, `grep -c 'score-fill.*width'`≥10（每个fill必须带width）, `grep 'border-top:2px solid var(--gold)'` 弹性树横线存在 |
| Batch 5 | `Read 中国长城 line=601-720`（Step 7-8+footer） | Write Step 7-8 卡片 + footer + `</div>` | `grep -o 'id="[^"]*"'` → compare/tracking 存在, `grep '📌'` 存在, `grep -c '<p>' footer段`=5, `grep 'strong' footer段`=0 |
| Batch 6 | `Read 中国长城 line=721-末尾`（script段）；从 `data_{代码}.json` 提取K线（最近120条）和业务构成 | Write `<script>...</script>`（搬运JS模板，替换 `__RAW_DATA_ARRAY__` 和 `__PIE_DATA_ARRAY__`，数据直接嵌入Write内容中，不用Python脚本做替换） | `grep -c '__'`=0（占位符清零）, `grep -cF 'const rawData'`=1（唯一声明）, `grep -c '替换为'`=0（无中文残留）, `grep -c '});' _h_part7.html`≥1（IIFE闭合）, `grep -c '</script>' _h_part7.html`=1（必须显式写出闭合标签）, `grep -c 'RAW_DATA_ARRAY\|PIE_DATA_ARRAY' _h_part7.html`=0（确认占位符已被替换为非占位文本） |
| 合并+终验 | — | Bash `cat _h_part*.html > 最终文件`，然后运行 **`HTML手写参考.md` § 终验自检清单** 全部 10 条 + 补充检查：`grep -c 'class=\"svg-hdr\"'`≥2 且 `grep -c 'class=\"svg-sub\"'`≥8（SVG文字使用CSS class做主题切换，禁止inline fill+font-size） | 全部通过才输出最终文件 |

**执行规则（不可跳过）：**
1. 每批第 1 步：**必须用 Read 工具打开范例对应行号区间**。读完范例段落后立即 Write，中间不做其他操作。
2. 写完后跑第 3 步 grep。对不上 → `grep` 范例对应行 → `grep` 自己写的 → 看差异 → Edit 修正 → 重跑 grep。
3. 三步全部通过才进入下一批。

> **若各批写为独立文件，用 `cat _h_part*.html > 最终文件` 合并，然后删临时文件。**

**Step 0-8 关键可视化组件清单：**
- **Step 0:** 4个信息卡片（标的/周期/风格/命题）
- **Step 1:** 核心矛盾高亮框
- **Step 2:** 产业链SVG图谱、grid-2布局、关键判断提示框
- **Step 3:** grid-2布局、6个评分条、评级徽章
- **Step 4:** 弹性树、公式卡片2x2、情景分析grid-3
- **Step 5:** grid-2布局、止损信号列表
- **Step 6:** grid-2布局、三档目标价、盈亏比量化卡片
- **Step 7:** 对比表格、增长引擎切换3卡片
- **Step 8:** grid-2布局、执行清单、verdict-highlight、五维评分、📌总结框（强制，红色左边框）

**关键约束：**
- OHLC 格式必须 `[open, close, low, high]`
- 成交量柱必须每根单独着色（红涨绿跌）
- 产业链 SVG 文字使用 `.svg-hdr` / `.svg-sub` class
- MathJax 使用 `\\(...\\)` 行内分隔符 → **HTML源码中写 `\(...\)`（单反斜杠），禁止 `\\(...\\)`（双反斜杠）**。HTML text 中反斜杠不是转义符，双反斜杠会导致 MathJax 分隔符匹配失败
- 所有CSS class必须来自 `shared/template_base.css`
- **内容区子标题禁止编号前缀**（不用 "1a/1b/2a"），直接写中文描述文字
- **禁止 h2/h3 标题带"Step X"编号前缀**：卡片标题只写中文描述（如"任务锁定与核心矛盾"，不写"Step 0 · 任务锁定"），`.sub` 同样禁止编号
- **Hero 第一项 meta-item** 显示 Step 3 公司质地评分的等级（如"B级"），标签写"公司质地"
- **两套评分标签区分**：Step 3 评分 → 标签"公司质地评分"；Step 8 评分 → 标签"综合交易评分"。两套分维度不同、数值不同是正常的，标签区分清楚即可
- **产业链 SVG 内容质量**：不满足于基础的3节点模板。根据 MD 分析内容扩充节点——多业务线（如 IVD vs SPD）、分支节点（如子公司网络）、关键数据标注（如各业务毛利率）。**每个`<text>`元素≤14个中文字**，超出换新`<text>`行(y+22)。写完自检：最长text字符数×13px < 所在rect的width
- **📌总结框为强制组件**：Step 8 底部必须有一个独立的红色左边框总结框（`border-left:4px solid var(--red-up)`），包含 `📌 总结` 标题和一段话总结，不可省略或用 verdict-highlight 替代
- **弹性树强制HTML模板**：使用flex+CSS边框构建树形图——顶层节点(金色边框)→竖线(2px×6px gold)→横线(border-top:2px solid gold)→三列子节点flex(2:1:1)。🔴红色/🟡金色/⚪灰色分别标记核心/次要/其他业务。每个子节点含业务名+营收占比+毛利率+业务线+弹性因子。**禁止纯文本无树形图**
- **评分条score-fill宽度强制**：每个 `.score-fill` 必须为 `<div>`（**禁止 `<span>`**，inline 元素 width 无效），必须有内联 `style="width:X%"`，X为该维度得分百分比。格式：`<div class="score-fill" style="width:65%;"></div>`——不可省略style属性，不可用CSS class替代width。高分段(≥70%)金色，中分段(40-69%)橙色，低分段(<40%)红色
- **Hero标签限制**：`.hero-tags` 内标签≤5个，每个标签≤4个中文字
- **Footer格式**：作者行和联系方式行**禁止使用strong标签和金色高亮**，保持纯文本

---

### 输出文件

```
output/
├── data_<股票代码>.json           # Phase 1: 原始数据（akshare采集）
├── 个股研究-<股票名称>.md          # Phase 2: 完整分析报告
└── 个股研究-<股票名称>.html        # Phase 3: 可视化HTML报告
```

---

## 🔧 配置要求

### 所有版本通用

**必需配置：**
- Python 3.8+
- akshare库（数据采集）
- Claude Code环境（AI分析和HTML生成）
- **智谱AI MCP配置**（`.mcp.json`）：用于Phase 2的中文信息搜索

**配置示例：**

`.mcp.json`（智谱AI搜索）：
```json
{
  "mcpServers": {
    "zhipu": {
      "command": "npx",
      "args": ["-y", "@zhipu-ai/mcp-server"],
      "env": {
        "ZHIPU_API_KEY": "your_zhipu_api_key"
      }
    }
  }
}
```

**说明：**
- Enhanced版本：本地使用，MCP已配置
- Competition版本：比赛提交，需确保MCP配置文件存在
- GitHub版本：开源发布，需在README中说明MCP配置步骤

---

## 🏗️ 三层架构

### 架构图

```
┌─────────────────────────────────────────────┐
│               用户输入                       │
│     "分析 XXX股票" 或 "分析 600519"         │
└────────────────────┬────────────────────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │  Phase 1: 数据采集（脚本）           │
  │  python stock_full_report.py <code> │
  │  → output/data_{代码}.json          │
  └──────────────────┬──────────────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │  Phase 2: AI分析（手写）             │
  │  读取 data JSON → MCP搜索           │
  │  → 逐步完成 Step 0-8                │
  │  → output/个股研究-{名称}.md         │
  └──────────────────┬──────────────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │  Phase 3: HTML生成（手写）           │
  │  CSS/JS 从 shared/ 搬运             │
  │  内容从 MD + data JSON 提取         │
  │  结构参考 examples/ 范例            │
  │  → output/个股研究-{名称}.html       │
  └──────────────────┬──────────────────┘
                     │
              ┌──────▼──────┐
              │  完成 ✓     │
              └─────────────┘
```

---

## 📊 输出内容

### MD报告结构（540-740行）

```markdown
# {股票名称}（{股票代码}）深度研究

## 基本信息
- 股票名称、代码、行业、市值、PE、PB等

## 财务摘要（最近一年）
- 营业收入、净利润、毛利率、ROE

## 股东结构
- 十大股东表格

## 主营业务构成
- 业务构成表格

---

## Step 0: 任务锁定（10行）
- 标的、周期、数据截止日、研究状态、风格预判

## Step 1: 宏观与周期定位（50行）
- 1a. 经济周期映射
- 1b. 政策与环境扫描
- 1c. 核心矛盾提炼

## Step 2: 产业链深度拆解（100行）
- 2a. 题材来源判断
- 2b. 产业链图谱（ASCII/Mermaid）
- 2c. 趋势三要素
- 2d. 价值链利润分布

## Step 3: 公司筛选与质量评分（50行）
- 3a. 正面筛选清单
- 3b. 不碰清单
- 3c. 质量评分（100分制）

## Step 4: 业绩弹性测算（80行）
- 4a. 分业务弹性树
- 4b. 价格敏感度公式
- 4c. 情景分析

## Step 5: 风险分析（40行）
- 5a. 风险清单
- 5b. 逻辑破坏条件（5个止损信号）

## Step 6: 估值与买卖时机（100行）
- 6a. 估值方法
- 6a+. 资金面分析
- 6a++. 技术面分析
- 6b. 三档目标价
- 6c. 盈亏比量化

## Step 7: 对标分析（60行）
- 7a. 案例类比法
- 7b. 增长引擎切换

## Step 8: 跟踪计划与综合结论（50行）
- 8a. 分层跟踪锚点
- 8b. 执行清单
- 8c. 综合结论（一句话判断、风险等级、操作建议）
- 8d. 五维综合评分
```

### HTML页面结构（实际输出格式）

```
<!DOCTYPE html>
<html>
<head>
  <meta> + <title>
  <script src="echarts CDN">
  <script src="MathJax CDN">
  <style> /* = template_base.css 完整搬运 */ </style>
</head>
<body>
  <nav class="top-nav">        <!-- 顶部导航（sticky） -->
    股票名+代码 · logo · **13个固定nav-links**（行情/结论/画像/K线/任务/宏观/产业链/质量/弹性/风险/估值/对标/跟踪）· 主题切换按钮
  </nav>
  <div class="container">
    <div class="hero">         <!-- Hero行情卡片 -->
      价格 + 涨跌幅 + **hero-meta 4项固定**（质量评级/中期目标价/盈亏比/风险等级）+ 标签组
    </div>
    <div class="conclusion-top"> <!-- 结论置顶卡片 -->
      核心结论标签 + 综合判断 + 详细说明 + 标签组
    </div>
    <!-- 公司画像 + 新闻（grid-2） -->
    <!-- 主营业务饼图 + 关键财务指标（grid-2） -->
    <!-- K线图卡片（ECharts candlestick + 成交量） -->
    <!-- K线底部4指标行（向上空间/盈亏比/目标价/周期） -->
    <!-- 分析章节卡片：任务/宏观/产业链/质量/弹性/风险/估值/对标/跟踪 -->
    <!-- 页脚（固定模板，见 HTML手写参考.md） -->
    <!-- 页脚含：免责声明 + 数据截止/研究状态 + 数据来源行 + 作者信息 + 联系方式 -->
  </div>
  <script> /* = template_base.js 骨架搬运 + 数据注入 */ </script>
</body>
</html>
```

> **关键约束：** HTML不使用左侧目录导航（旧设计规范中的 `nav.toc` 已废弃），改用顶部 sticky 导航 + 滚动高亮。

---

## 🎨 HTML手写规范

> **Phase 3开始时，必须读取 `HTML手写参考.md`。该文件包含：组件速查表、颜色语义、以及分批机械校验的 grep 命令清单。校验命令不可跳过。**

### 核心要点

- `<style>` = `shared/template_base.css` 完整搬运，不做修改
- `<script>` = `shared/template_base.js` 骨架 + 注入 rawData（K线）+ pieData（业务构成）
- `<body>` 结构参考 `examples/个股研究-中国长城.html`
- OHLC 格式 `[open, close, low, high]`，成交量每根单独着色
- 红涨绿跌全篇一致，所有CSS class来自template_base.css
- 产业链SVG文字用 `.svg-hdr` / `.svg-sub` class，MathJax用 `\\(...\\)`

### 页面结构（强制顺序）

```
top-nav → .hero → .conclusion-top → grid-2(公司画像+动态) → grid-2(饼图+财务)
→ .card(K线图) → 分析章节9卡片 → footer
```

### 详细参考

完整组件速查表、颜色语义表、CHECKS自检清单 → **[HTML手写参考.md](HTML手写参考.md)**

---

## 🔧 执行流程

### Phase 1: 数据采集层（3-5分钟）

**脚本：** `stock_full_report.py`

**功能：**
1. 使用akshare采集数据源
2. Fallback机制：akshare失败→跳过
3. **唯一输出：** `output/data_{代码}.json`（供Phase 2/3使用）

**数据源：** 基础信息、行情（3年日K线）、主营业务、资金流向、财务数据、股东结构、公告新闻、研究报告

### Phase 2: AI分析层（45-75分钟）

**AI手动执行，无自动化脚本。**

**2.1 基础信息写入（5分钟）**
- 读取 `output/data_{代码}.json`
- 写入MD头部：股票名称、代码、行业、市值、PE/PB、财务摘要、股东结构、主营业务构成

**2.2 MCP搜索（10分钟）**
- 用智谱AI搜索行业趋势、竞争对手、券商研报、最新新闻（通常3-6次）
- 智谱失败则fallback到Tavily

**2.3 AI逐步分析Step 0-8（30-60分钟）**

**⚠️ MD写作禁止事项（防止内容泄露到HTML）：**
- ❌ MD正文任何位置禁止出现：`@明立玩AI` / `作者：明立` / `ll-mingli1221` / 社交媒体ID
- ❌ MD末尾禁止添加署名行（如 `> 分析框架：... | @明立玩AI`）
- ✅ 这些信息仅出现在HTML的footer中，由Phase 3统一添加

**强制执行清单：**

```
□ Step 0: 任务锁定（10行）
  ├─ 标的（公司名、代码、交易所）
  ├─ 周期（短线/中线/长线）
  ├─ 数据截止日（YYYY-MM-DD）
  ├─ 研究状态（首次覆盖/持续跟踪）
  └─ 风格预判（配置型/交易型/左侧博弈型）

□ Step 1: 宏观与周期定位（50行）
  ├─ 使用MCP搜索结果：行业趋势
  ├─ 1a. 经济周期映射
  ├─ 1b. 政策与环境扫描
  └─ 1c. 核心矛盾提炼（XX vs YY）

□ Step 2: 产业链深度拆解（100行）
  ├─ 使用MCP搜索结果：竞争对手、产业链
  ├─ 2a. 题材来源判断
  ├─ 2b. 产业链图谱（ASCII或Mermaid代码块）
  ├─ 2c. 趋势三要素（表格+打分）
  └─ 2d. 价值链利润分布（表格）

□ Step 3: 公司筛选与质量评分（50行）
  ├─ 使用akshare数据：财务、股东
  ├─ 3a. 正面筛选清单（6项标准）
  ├─ 3b. 不碰清单（负面排查）
  └─ 3c. 公司质地评分（100分制，6个维度——注意：与Step 8综合交易评分维度不同，两个分不一定相等）

□ Step 4: 业绩弹性测算（80行）
  ├─ 使用akshare数据：主营业务、财务
  ├─ 4a. 分业务弹性树（ASCII代码块）
  ├─ 4b. 价格敏感度公式（3个公式）
  └─ 4c. 情景分析（悲观/基准/乐观表格）

□ Step 5: 风险分析（40行）
  ├─ 5a. 风险清单（表格：风险类型、影响程度、发生概率）
  └─ 5b. 逻辑破坏条件（5个止损信号）

□ Step 6: 估值与买卖时机（100行）
  ├─ 使用MCP搜索结果：券商研报
  ├─ 使用akshare数据：K线、资金流向
  ├─ 6a. 估值方法选择
  ├─ 6a+. 资金面分析（筹码分布、主力资金）
  ├─ 6a++. 技术面分析（均线、支撑阻力）
  ├─ 6b. 三档目标价（短期/中期/长期表格）
  └─ 6c. 盈亏比量化（向上空间 vs 向下空间）

□ Step 7: 对标分析（60行）
  ├─ 使用MCP搜索结果：竞争对手
  ├─ 7a. 案例类比法（对比表格）
  └─ 7b. 增长引擎切换（如果适用）

□ Step 8: 跟踪计划与综合结论（50行）
  ├─ 8a. 分层跟踪锚点（高频/季度/事件）
  ├─ 8b. 执行清单（短线/中线）
  ├─ 8c. 综合结论（一句话判断、风险等级、操作建议）
  └─ 8d. 五维综合交易评分（基本面/资金面/技术面/情绪面/事件——与Step 3公司质地评分维度不同）

✅ 总计：540行（最低要求）
```

**执行规则：**
1. AI必须严格按照Step 0→Step 8顺序执行
2. 每完成一个Step，输出：`✅ Step X完成（XX行）`
3. 不能跳过或简化任何Step
4. 每个Step必须达到最低行数要求

### Phase 3: HTML生成层（AI手动分批拼装）

**原理：** AI手写完整HTML——从 `shared/` 搬运CSS/JS，从MD报告提取内容，从范例参考结构。**分批用Write工具写，禁止用Python/Bash heredoc生成HTML内容。**

**执行步骤：**

1. **读取模板：** `shared/template_base.css` + `shared/template_base.js`
2. **读取范例：** `examples/个股研究-中国长城.html`
3. **读取数据：** `output/个股研究-{股票名称}.md` + `output/data_{代码}.json`
4. **分批手写HTML：**
   - 每批 ≤300行，用 **Write工具** 直接写HTML markup
   - `<style>` = 完整搬运 template_base.css（Write工具写入）
   - `<script>` = template_base.js 骨架 + 注入 rawData + pieData（独立一批，Write工具写入）
   - `<body>` = 参考范例结构，分2-4批写入各section
5. **合并部分文件（如有）：** 仅用 `cat` 或 Python `file.read()` 做机械字节拼接，绝不生成HTML内容
6. **输出：** `output/个股研究-{股票名称}.html`

### ⚠️ 分批手写规则（强制）

**禁止行为：**

| 禁止 | 原因 |
|------|------|
| ❌ **Python f-string/template 生成HTML** | 需要大量 `{{}}` 转义，易出错不可维护 |
| ❌ **Bash heredoc 生成HTML** | 多行HTML下经常EOF匹配失败 |
| ❌ **一次性写出整个HTML** | >300行文件必须分批，每批独立一个Write调用 |
| ❌ **用 `python -c` 拼接HTML字符串** | 属于Python生成，不是手写 |

**正确做法：**

| 操作 | 工具 | 说明 |
|------|------|------|
| 写入HTML内容 | **Write** | 直接写HTML markup，无转义问题 |
| 精确局部修改 | **Edit** | 替换特定行，不改动其他部分 |
| 机械合并部分文件 | **Bash `cat`** 或 **Python `file.read()`** | 仅读取+拼接字节，不生成任何markup |

**标准分批方案（~900行HTML）：**

```
Batch 0: Write — DOCTYPE + <head> + <style>（CSS完整复制）           ~180行
Batch 1: Write — <body> + nav + hero + conclusion-top + profile      ~150行
Batch 2: Write — K线图卡片 + Step 0-3 卡片                            ~200行
Batch 3: Write — Step 4-6 卡片（弹性/风险/估值）                      ~200行
Batch 4: Write — Step 7-8 卡片 + footer + </div>                      ~150行
Batch 5: Write — <script>（JS完整复制 + 注入rawData + pieData）       ~150行
```

> **若各批写为独立文件，用 `cat part*.txt >> main.html` 合并，然后删临时文件。Python仅用于 `file.read()` 字节拼接，绝不用f-string生成HTML markup。**

**Step 0-8 关键可视化组件清单：**
- **Step 0:** 4个信息卡片（标的/周期/风格/命题）
- **Step 1:** 核心矛盾高亮框
- **Step 2:** 产业链SVG图谱、grid-2布局、关键判断提示框
- **Step 3:** grid-2布局、6个评分条、评级徽章
- **Step 4:** 弹性树、公式卡片2x2、情景分析grid-3
- **Step 5:** grid-2布局、止损信号列表
- **Step 6:** grid-2布局、三档目标价、盈亏比量化卡片
- **Step 7:** 对比表格、增长引擎切换3卡片
- **Step 8:** grid-2布局、执行清单、verdict-highlight、五维评分、📌总结框

**关键约束：**
- OHLC 格式必须 `[open, close, low, high]`
- 成交量柱必须每根单独着色（红涨绿跌）
- 产业链 SVG 文字使用 `.svg-hdr` / `.svg-sub` class，字号 `.svg-hdr` ≥14px, `.svg-sub` ≥12px
- MathJax 使用 `\\(...\\)` 行内分隔符 → **HTML源码中写 `\(...\)`（单反斜杠），禁止 `\\(...\\)`（双反斜杠）**。HTML text 中反斜杠不是转义符，双反斜杠会导致 MathJax 分隔符匹配失败
- 所有CSS class必须来自 `shared/template_base.css`
- **禁止占位符：HTML 全文不得残留任何 `<!-- AI填充` 或 `<!-- XXX_PLACEHOLDER` 注释**
- **弹性树必须用 `grid-2`（2×2），禁止 flex 单行4列**
- **📌总结框必须为独立 `.card`（红色左边框），位于 Step 8 之后、footer 之前**

> **归档说明：** `gen_html.py`、`gen_ganfeng_html.py`（硬编码模板）、`phase3_html_builder.py`（骨架生成）、`phase3_md_parser.py`（MD解析）、`stock_analysis_main.py`（早期主控）均已归档至 `archive/`。Phase 2/3 全部由AI手写，不使用自动化脚本。

---

## 📝 使用示例

### 示例：分析赣锋锂业（002460）

```bash
cd G:/vibe/my-skills/stock-analysis-competition
python stock_full_report.py 002460
```

**输出：**
```
[Phase 1/3] 数据采集中...
  ✅ Phase 1完成，数据已保存：output/data_002460.json

[Phase 2/3] AI分析中...
  ✅ Step 0-8 完成，MD已保存：output/个股研究-赣锋锂业.md（619行）

[Phase 3/3] AI手写HTML中...
  ✅ 模板已读取（shared/template_base.css + shared/template_base.js）
  ✅ HTML已保存：output/个股研究-赣锋锂业.html（991行/63KB）
```

---

## 🔍 常见问题

### Q1: 为什么Phase 2这么慢？
A: Phase 2需要AI逐步分析Step 0-8，每个Step都需要深度思考和MCP搜索，总计需要30-60分钟。这是为了保证分析质量。

### Q2: 可以跳过某些Step吗？
A: 不可以。Step 0-8是完整的分析框架，跳过任何一步都会导致分析不完整。

### Q3: MCP搜索失败怎么办？
A: 系统会自动fallback：智谱搜索失败→Tavily搜索→继续执行。

### Q4: HTML太长写不下怎么办？
A: HTML最终约900行/60KB，远非"太大"。关键是分批写：用Write工具每批≤300行，分5-6批写完。若写为独立文件，最后用 `cat` 做机械合并。**禁止用Python f-string生成HTML。**

---

## 📚 相关文档

- [shared/template_base.css](shared/template_base.css) — 规范CSS模板，AI复制到`<style>`
- [shared/template_base.js](shared/template_base.js) — 规范JS模板，AI复制到`<script>`并注入数据
- [examples/个股研究-中国长城.html](examples/个股研究-中国长城.html) — 成品参考范例
- [HTML报告设计规范v1.0.md](HTML报告设计规范v1.0.md) — CSS设计系统详细文档
- [分析框架.md](分析框架.md) — Step 0-8 完整分析方法论
- [archive/](archive/) — 已归档的旧脚本和文件

## 🗄️ 已归档

以下脚本/文件已移至 `archive/`：
- `gen_html.py`、`gen_ganfeng_html.py` — 硬编码模板（每股票需单独写脚本）
- `phase3_html_builder.py` — 中间骨架生成（产出`_skeleton.html`，与终版混淆）
- `phase3_md_parser.py` — MD解析工具（Phase 2/3 由AI手写，不需要）
- `stock_analysis_main.py` — 早期主控脚本（已被三层架构替代）
- `stock_report_*.html` — stock_full_report.py 自动生成的简化HTML（只有JSON是Phase 1产出）

---

> **免责声明：** 本系统所有分析仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。
