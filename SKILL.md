---
name: stock-analysis-enhanced
description: 一句话搞定个股分析 — 说"分析XXX"，自动采集30+数据源 → AI完成基本面(Step 0-8)+技术面+资金面的完整研报 → 生成交互式HTML报告。支持增量更新（K线/行情/技术指标自动刷新）。触发词："分析XXX股票"（首次）或"更新XXX股票"（增量）。
trigger_keywords: ["分析股票", "个股分析", "股票研究", "分析一只股票", "更新股票", "刷新报告", "增量更新"]
version: 3.1
last_updated: 2026-05-30
variant: enhanced
---

# 一句话搞定个股分析

> 版本：v3.1 | 更新：2026-05-30 | 用户说一句话 → 30+数据源采集 → Step 0-8 基本面 + 第9章技术面 + 资金面 → 双主题交互式HTML

---

## 📋 快速导航

- [⚡ 使用方式](#使用方式) — 一句话触发，全自动执行
  - [场景判断](#场景判断)
  - [场景A：首次分析](#场景a首次分析) — 完整三阶段
  - [场景B：增量更新](#场景b增量更新) — 快速刷新数据
- [🏗️ 三层架构](#三层架构) — Phase 1 数据采集 → Phase 2 AI分析 → Phase 3 HTML
- [📊 输出内容](#输出内容) — MD 报告 + HTML 报告的完整结构
- [🎨 HTML手写规范](#html手写规范) — 分批手写 + grep 机械校验
- [🔧 执行流程](#执行流程) — Phase 1/2/3 详细步骤
- [🔄 增量更新详细说明](#增量更新详细说明) — 脚本自动 + AI 手动

---

## ⚡ 使用方式

### 场景判断

**AI必须根据用户输入的关键词判断场景：**

#### 场景A：首次分析（完整流程）

**触发关键词：**
- "分析 XXX股票"
- "个股分析 XXX"
- "研究 XXX"
- "生成 XXX报告"
- 用户明确说"首次分析"

**判断逻辑：**
- 用户输入包含上述关键词 → 执行首次分析（Phase 1→2→3）

#### 场景B：增量更新（只更新数据）

**触发关键词：**
- "更新 XXX股票"
- "刷新 XXX报告"
- "增量更新 XXX"
- "更新报告"
- 用户明确说"更新"

**判断逻辑：**
1. 用户输入包含上述关键词
2. 检查 `output/个股研究-{股票名称}.html` 是否存在
3. 如果存在 → 执行增量更新
4. 如果不存在 → 提示用户："未找到 XXX 的报告，是否需要首次分析？"

---

### 场景A：首次分析

**当用户说"分析 XXX股票"时，一句话触发全流程：**

### Phase 1: 数据采集（3-5分钟）

```bash
cd G:/vibe/my-skills/stock-analysis-enhanced
python stock_full_report.py <股票代码>
```

**示例：**
```bash
python stock_full_report.py 600519  # 贵州茅台
python stock_full_report.py 600673  # 东阳光
```

**唯一输出：** `output/data_<股票代码>.json`（包含K线、财务、股东、业务构成等完整数据，供Phase 2/3使用）

**⚠️ Phase 1完成后立即进入Phase 2**，不要停下来询问用户。JSON只是数据中间产物。

**⚠️ Phase 1 新增功能：** 自动计算技术指标（MACD/KDJ/RSI/BOLL/MA），保存到 `data_{代码}.json` 的 `technical_indicators` 和 `technical_signals` 字段，供 Phase 3 生成第9章使用。

---

### 场景B：增量更新

**执行命令：**

```bash
cd G:/vibe/my-skills/stock-analysis-enhanced副本
python update_stock_report.py <股票代码>
```

**常用参数：**
```bash
# 基本用法（自动查找HTML文件）
python update_stock_report.py 000066

# 指定HTML文件
python update_stock_report.py 000066 --html output/个股研究-中国长城.html

# 强制更新（跳过检查，直接更新）
python update_stock_report.py 000066 --force
```

**更新内容：**
- ✅ K线数据（rawData数组）
- ✅ Hero区域（最新价、涨跌幅）
- ✅ 第9章技术指标（MACD/KDJ/RSI/BOLL图表）
- ❌ 基本面分析（Step 0-8，不更新）

**详细说明：** 见本文件末尾"[🔄 增量更新详细说明](#增量更新详细说明)"章节

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
| Batch 0 | `Read 中国长城 line=1-129`（head+style段） | Write DOCTYPE + `<head>` + `<style>` | `grep -c '<style>'`=1, `grep 'echarts\|MathJax'` 确认CDN |
| Batch 1 | `Read 中国长城 line=130-195`（nav+hero+conclusion+profile网格） | Write `<body>` + nav + hero + conclusion(含交易参数行) + grid-2(公司画像+近期动态) | `grep -oc 'href="#'`=14, `grep -c 'hero-meta-item'`=5, `grep 'nav-analysis-date'`存在, `grep -c '利好\|利空\|中性'`≥5, `grep 'overflow-y\|max-height:300'`=0, `grep -c 'style="[^"]*color:#fff[^"]*"\|style="[^"]*color:white[^"]*"\|style="[^"]*color:rgba(255'`=0, `grep -c '买入区间\|止损位\|目标价\|建议仓位'`≥4 |
| Batch 2 | `Read 中国长城 line=196-260`（饼图+财务+K线） | Write 饼图+财务grid-2 + K线card(kline-section) | `grep 'id="kline-section"'` 存在, `grep 'height:480px'` 存在, `grep -c 'markLine'`≥1, `grep -c 'markPoint'`≥1 |
| Batch 3 | `Read 中国长城 line=260-397`（Step 0-3） | Write Step 0-3 卡片（mission/macro/chain/quality） | `grep -o 'id="[^"]*"'` → mission/macro/chain/quality 四者存在 |
| Batch 4 | `Read 中国长城 line=398-550`（Step 4-6） | Write Step 4-6 卡片（elasticity/risk/valuation） | `grep -o 'id="[^"]*"'` → elasticity/risk/valuation 三者存在, `grep -c 'score-fill.*width'`≥10, `grep 'border-top:2px solid var(--gold)'` 弹性树横线存在 |
| Batch 5 | `Read 中国长城 line=551-863`（Step 7-8+第9章+footer） | Write Step 7-8 卡片 + 第9章技术面卡片（信号总览6卡片→技术图表2x2→多周期趋势→位置形态→动量量价→资金面→市场风格→综合研判）+ footer + `</div>` | `grep -o 'id="[^"]*"'` → compare/tracking/technical 存在, `grep '📌'` 存在, `grep -c '<p>' footer段`=5, `grep 'strong' footer段`=0, `grep '催化剂兑现追踪\|已兑现\|待兑现'`存在, `grep '📋 事件记录'`存在, `grep -c 'chart-macd\|chart-kdj\|chart-rsi\|chart-boll'`=4 |
| Batch 6 | `Read 中国长城 line=864-1155`（script段）；从 `data_{代码}.json` 提取K线（最近120条）和业务构成 | Write `<script>...</script>`（搬运 `template_base.js` 完整内容，替换4处占位符：`__RAW_DATA_ARRAY__` → K线JSON数组、`__PIE_DATA_ARRAY__` → 业务构成JSON数组、`__MARKLINE_DATA__` → markLine数组、`__MARKPOINT_DATA__` → markPoint数组。模板已含技术指标计算+6个渲染函数，直接搬运无需修改） | `grep -c '__'`=0, `grep -cF 'const rawData'`=1, `grep -c 'renderMACD'`=1, `grep -c 'renderKDJ'`=1, `grep -c 'renderRSI'`=1, `grep -c 'renderBOLL'`=1, `grep -c '</script>'`=1 |
| 合并+终验 | — | Bash `cat _h_part*.html > 最终文件`，然后运行 **`HTML手写参考.md` § 终验自检清单** 全部 **16** 条 | 全部通过才输出最终文件 |

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
- **OHLC 转换**：`ohlc.push([d[1], d[4], d[3], d[2]])` — rawData 格式 `[日期, 开盘, 最高, 最低, 收盘, 成交量]`（akshare 原生列序），itemStyle 用 `color: c.upColor, color0: c.downColor`。与 stock-analysis-github 验证通过版本一致
- 成交量柱必须每根单独着色（红涨绿跌）
- 产业链 SVG 文字使用 `.svg-hdr` / `.svg-sub` class
- MathJax 使用 `\\(...\\)` 行内分隔符 → **HTML源码中写 `\(...\)`（单反斜杠），禁止 `\\(...\\)`（双反斜杠）**。HTML text 中反斜杠不是转义符，双反斜杠会导致 MathJax 分隔符匹配失败
- 所有CSS class必须来自 `shared/template_base.css`
- **内容区子标题禁止编号前缀**（不用 "1a/1b/2a"），直接写中文描述文字
- **禁止 h2/h3 标题带"Step X"编号前缀**：卡片标题只写中文描述（如"任务锁定与核心矛盾"，不写"Step 0 · 任务锁定"），`.sub` 同样禁止编号
- **Hero meta-item 5项固定顺序**：①分析基准日（`data-cutoff`日期，标签"分析基准日"，值格式`YYYY-MM-DD`）②公司质地等级（Step 3评分，标签"公司质地"）③中期目标价 ④盈亏比 ⑤风险等级
- **两套评分标签区分**：Step 3 评分 → 标签"公司质地评分"；Step 8 评分 → 标签"综合交易评分"。两套分维度不同、数值不同是正常的，标签区分清楚即可
- **产业链 SVG 内容质量**：不满足于基础的3节点模板。根据 MD 分析内容扩充节点——多业务线（如 IVD vs SPD）、分支节点（如子公司网络）、关键数据标注（如各业务毛利率）。**每个`<text>`元素≤14个中文字**，超出换新`<text>`行(y+22)。写完自检：最长text字符数×13px < 所在rect的width
- **📌总结框为强制组件**：Step 8 底部必须有一个独立的红色左边框总结框（`border-left:4px solid var(--red-up)`），包含 `📌 总结` 标题和一段话总结，不可省略或用 verdict-highlight 替代
- **弹性树强制HTML模板**：使用flex+CSS边框构建树形图——顶层节点(金色边框)→竖线(2px×6px gold)→横线(border-top:2px solid gold)→三列子节点flex(2:1:1)。🔴红色/🟡金色/⚪灰色分别标记核心/次要/其他业务。每个子节点含业务名+营收占比+毛利率+业务线+弹性因子。**禁止纯文本无树形图**
- **评分条score-fill宽度强制**：每个 `.score-fill` 必须为 `<div>`（**禁止 `<span>`**，inline 元素 width 无效），必须有内联 `style="width:X%"`，X为该维度得分百分比。格式：`<div class="score-fill" style="width:65%;"></div>`——不可省略style属性，不可用CSS class替代width。高分段(≥70%)金色，中分段(40-69%)橙色，低分段(<40%)红色
- **核心结论区强制附加交易参数行**：`.conclusion-top` 内 verdict-tags 下方必须有一行 `border-top:1px dashed var(--border)` 分隔，展示5个关键交易参数（flex行，居中排列）：①买入区间（绿色）②止损位（绿色）③目标价（红色）④建议仓位（金色）⑤盈亏比（金色）。格式：`<div style="font-size:11px;color:var(--text-muted);">标签</div><div style="font-weight:700;color:语义色;font-size:15px;">值</div>`。参数来源于 MD 报告 Step 6/8 分析结论
- **Hero标签限制**：`.hero-tags` 内标签≤5个，每个标签≤4个中文字
- **Footer格式**：作者行和联系方式行**禁止使用strong标签和金色高亮**，保持纯文本
- **禁止HTML body内联硬编码颜色**：所有 `style="color:#fff"` / `style="color:white"` / `style="color:rgba(255,255,255,...)"` 必须改用CSS变量（`var(--text-primary)` / `var(--text-secondary)` 等），确保双主题切换时文字始终可见。浅色模式下 `card-bg-alt` 为 `#fef5e7`（暖奶油色），白色文字完全不可见
- **近期动态强制规范**：**禁止使用滚动容器**（`max-height`/`overflow-y`），固定高度展示。每条新闻用纯文本 `<span>`（暂不设链接）。每条右侧必须有**利好/利空/中性标签**（`<span>` + 内联style），利好=红色背景+红字（`background:rgba(245,86,86,0.15);color:var(--red-up)`），重大利好另加红色左边框（`border-left:3px solid var(--red-up)`），中性=金色背景+金字（`background:rgba(212,168,83,0.15);color:var(--gold)`），利空=绿色背景+绿字。标签文字≤4字。**增量更新时，近期动态必须替换为当日最新新闻，重新判断利好利空属性**
- **K线图强制技术标注**：必须包含4条markLine（虚线金色`#d4a853`）：前高压力位/关键均线(MA20或MA60)/加仓位/止损位，价格取自MD报告分析内容。2个markPoint（pin图标）：当前价位(金色`#d4a853`)+关键历史价位(红色`#f55656`)。label用`#fff` 字号11px fontWeight bold。markLine label用`#d4a853` 字号10px

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
    股票名+代码 · logo · **14个固定nav-links（含技术面）**（行情/结论/画像/K线/任务/宏观/产业链/质量/弹性/风险/估值/对标/跟踪）· **分析基准日**（格式：`📅 YYYY-MM-DD`，12px字号，颜色跟随主题）· 主题切换按钮
  </nav>
  <div class="container">
    <div class="hero">         <!-- Hero行情卡片 -->
      价格 + 涨跌幅 + **hero-meta 5项固定**（分析基准日/质量评级/中期目标价/盈亏比/风险等级）+ 标签组
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
    <!-- 页脚含：免责声明 + 数据截止/研究状态/分析基准日 + 数据来源行 + 作者信息 + 联系方式 -->
    <!-- 分析基准日格式：📅 分析基准日：YYYY-MM-DD（数据截止日当天或最近交易日） -->
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

## 🌓 双主题颜色规范

> **浅色/深色模式切换通过 `<button class="theme-toggle" id="themeToggle">` 实现，CSS 变量切换由 `:root` 和 `body.light-mode` 两组变量控制。**

### 浅色模式强制检查清单

**Phase 3 分批校验时，每批完成后必须逐项确认浅色模式覆盖完整：**

| 检查项 | 深色模式 | 浅色模式要求 | grep 校验命令 |
|--------|---------|-------------|--------------|
| Nav logo文字 | `color:#fff` | `color:var(--text-primary)` | `grep -c 'light-mode.*logo'` ≥1 |
| Nav logo-icon | `color:#fff` | `color:var(--card-bg)` | `grep 'light-mode.*logo-icon'` 存在 |
| Nav stock-name/stock-code | 继承logo白色 | 继承修复后可见 | 同上条覆盖即可 |
| 卡片标题 h2 | `color:#fff` | `color:var(--text-primary)` | `grep -c 'light-mode.*card-header h2'` ≥1 |
| Hero区域 | `color:#fff` | `color:var(--text-primary)` | `grep -c 'light-mode.*\.hero'` ≥1 |
| 结论大字 `.big-verdict` | `color:#fff` | `color:var(--text-primary)` | `grep 'light-mode.*big-verdict'` 存在 |
| Hero meta label | `color:rgba(255,255,255,0.7)` | `color:var(--text-muted)` | `grep 'light-mode.*hero-meta-item.*label'` 存在 |
| Hero meta val | `color:var(--gold-light)` | `color:var(--gold)` | `grep 'light-mode.*hero-meta-item.*val'` 存在 |
| 评级标题 `.body .title` | `color:#fff` | `color:var(--text-primary)` | `grep 'light-mode.*rating-callout.*title'` 存在 |
| 产业链SVG `.svg-hdr` | `fill:#e8e9ec` | `fill:#2a1f12` | `grep 'light-mode.*svg-hdr'` 存在 |
| 产业链SVG `.svg-sub` | `fill:#b0b3be` | `fill:#6b5634` | `grep 'light-mode.*svg-sub'` 存在 |
| KPI value `.value` | `color:var(--gold-light)` | `color:var(--gold)` | `grep 'light-mode.*kpi-info-item.*value'` 存在 |
| Theme toggle按钮 | 默认样式 | 浅底深字可辨识 | `grep 'light-mode.*theme-toggle'` 存在 |
| 新闻链接 `.news-item a` | 继承text-secondary | 保持可点击辨识 | 无需额外覆盖 |

### 浅色模式覆盖CSS模板

**以下代码必须完整出现在 `<style>` 标签中（template_base.css 已包含）：**

```css
body.light-mode .top-nav{background:rgba(255,251,245,0.92);border-bottom-color:var(--gold)}
body.light-mode .top-nav .logo{color:var(--text-primary)}
body.light-mode .top-nav .logo-icon{color:var(--card-bg)}
body.light-mode .top-nav .stock-name{color:var(--text-primary)}
body.light-mode .top-nav .stock-code{color:var(--text-muted)}
body.light-mode .theme-toggle{background:rgba(0,0,0,0.05);border-color:var(--gold);color:var(--gold)}
body.light-mode .theme-toggle:hover{background:rgba(0,0,0,0.1)}
body.light-mode .nav-links a{color:var(--gold)}
body.light-mode .nav-links a:hover,body.light-mode .nav-links a.active{background:rgba(0,0,0,0.05);color:#7f1d1d}
body.light-mode .hero{background:linear-gradient(105deg,#fef5e7,#fffbf5);color:var(--text-primary);border-color:var(--gold)}
body.light-mode .hero-price{color:var(--text-primary)}
body.light-mode .hero-change{background:rgba(220,38,38,0.1);color:var(--red-up)}
body.light-mode .hero-meta-item .val{color:var(--gold)}
body.light-mode .hero-meta-item .label{color:var(--text-muted)}
body.light-mode .hero-tag{background:rgba(212,168,83,0.15);border-color:var(--gold);color:var(--gold)}
body.light-mode .conclusion-top{background:linear-gradient(135deg,#fff9f0,#fef5e7)}
body.light-mode .conclusion-top .big-verdict{color:var(--text-primary)}
body.light-mode .card-header h2{color:var(--text-primary)}
body.light-mode .tag{background:rgba(212,168,83,0.15);color:var(--gold);border-color:var(--gold)}
body.light-mode table.cons thead th{background:linear-gradient(180deg,#f55656,#c0392b)}
body.light-mode .score-bar .score-track{background:#f0e4ce}
body.light-mode .rating-callout{background:linear-gradient(135deg,#fff9f0,#fef5e7)}
body.light-mode .rating-callout .body .title{color:var(--text-primary)}
body.light-mode .verdict-highlight{background:#fef5e7}
body.light-mode .verdict-highlight .judgment{color:var(--gold)}
body.light-mode .verdict-highlight .v-val{color:var(--text-primary)}
body.light-mode .chain-svg .svg-hdr{fill:#2a1f12}
body.light-mode .chain-svg .svg-sub{fill:#6b5634}
body.light-mode .kpi-info-item .value{color:var(--gold)}
```

### 禁止的硬编码颜色

| 禁止写法 | 原因 | 正确写法 |
|---------|------|---------|
| `color:#fff`（无浅色覆盖） | 浅色模式白色背景上看不见 | 用CSS变量 + body.light-mode覆盖 |
| `color:white`（无浅色覆盖） | 同上 | 同上 |
| `fill:#fff`（SVG文字，无浅色覆盖） | SVG白字在浅色背景不可见 | 用`.svg-hdr`/`.svg-sub` class，已含双主题覆盖 |
| `color:rgba(255,255,255,0.7)`（无浅色覆盖） | 半透明白色同理 | 用`var(--text-muted)` + light-mode覆盖 |

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
- **OHLC 转换**：`ohlc.push([d[1], d[4], d[3], d[2]])` — rawData 格式 `[日期, 开盘, 最高, 最低, 收盘, 成交量]`（akshare 原生列序），itemStyle 用 `color: c.upColor, color0: c.downColor`。与 stock-analysis-github 验证通过版本一致
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
- [第9章技术分析设计.md](第9章技术分析设计.md) — 第9章技术面分析HTML结构设计
- [archive/](archive/) — 已归档的旧脚本和文件

## 🗄️ 已归档

以下脚本/文件已移至 `archive/`：
- `gen_html.py`、`gen_ganfeng_html.py` — 硬编码模板（每股票需单独写脚本）
- `phase3_html_builder.py` — 中间骨架生成（产出`_skeleton.html`，与终版混淆）
- `phase3_md_parser.py` — MD解析工具（Phase 2/3 由AI手写，不需要）
- `stock_analysis_main.py` — 早期主控脚本（已被三层架构替代）
- `stock_report_*.html` — stock_full_report.py 自动生成的简化HTML（只有JSON是Phase 1产出）

---

## 📈 第9章：技术面与资金面分析（强制章节）

### 章节定位

**第9章是基本面分析（Step 0-8）的补充**，用于短期择时和交易信号验证。**每次首次分析和增量更新都必须包含此章节。**

- **位置**：在 Step 8（跟踪计划）之后，footer 之前
- **导航**：顶部 nav 第14个链接 `<a href="#technical">技术面</a>`
- **风格**：与 Step 0-8 保持一致的 `.card` 布局，标题用 `.card-header`
- **标题**：`技术面与资金面分析`，sub 写 `多周期联动 · 形态识别 · 量价配合 · 操作计划`

### 数据来源

- **JS 端计算（首选）：** 从 `rawData` 实时计算 MACD/KDJ/RSI/BOLL（`template_base.js` 已含计算函数，AI 搬运即可）
- **Python 预计算（备选）：** 从 `data_{代码}.json` 读取 `technical_indicators` 和 `technical_signals`（由 `stock_full_report.py` 生成）
- **MD 报告内容：** 从 Phase 2 的 MD 报告中提取关键技术位、形态判断、资金面描述（AI 分析产出）

### HTML结构（9.1-9.7，强制完整）

```html
<div class="card" id="technical">
  <div class="card-header"><span class="icon">📈</span><h2>技术面与资金面分析</h2><span class="sub">多周期联动 · 形态识别 · 量价配合 · 操作计划</span></div>

  <!-- 当前技术信号速览（6个指标卡片，grid-3） -->
  <h3 style="...">当前技术信号</h3>
  <div class="grid-3">
    <div>MACD 信号卡片</div>  <div>KDJ 信号卡片</div>  <div>RSI 信号卡片</div>
    <div>BOLL 信号卡片</div>  <div>均线 信号卡片</div>  <div>成交量 信号卡片</div>
  </div>

  <!-- 技术指标图表（紧接信号速览，与MACD/KDJ等指标关联最近） -->
  <h3>技术指标图表</h3>
  <div class="grid-2"><div id="chart-macd"></div><div id="chart-kdj"></div></div>
  <div class="grid-2"><div id="chart-rsi"></div><div id="chart-boll"></div></div>

  <!-- 多周期趋势分析（grid-3 → 月线/周线/日线，含状态标记+技术信号标签） -->
  <h3>多周期趋势分析</h3>
  <div class="grid-3">月线 · 周线 · 日线 三列卡片</div>
  <p>多周期判断总结（带💡前缀的提示框）</p>

  <!-- 位置与形态分析（grid-2：关键技术位表 + 形态识别表） -->
  <h3>位置与形态分析</h3>
  <div class="grid-2">关键技术位表格 · 形态识别表格</div>

  <!-- 9.4 动量与量价分析（grid-2：动量指标表 + 量价配合表） -->
  <h3>动量与量价分析</h3>
  <div class="grid-2">动量指标表格 · 量价配合表格</div>
  <p>⚠️ 动量预警提示框</p>

  <!-- 9.5 资金面分析（ul列表：主力资金/北向资金/龙虎榜） -->
  <h3>资金面分析</h3>
  <ul>主力资金 · 北向资金 · 龙虎榜</ul>

  <!-- 9.6 市场风格与板块轮动（grid-2：板块TOP5表 + 风格判断卡片） -->
  <h3>市场风格与板块轮动</h3>
  <div class="grid-2">板块TOP5表格 · 风格判断卡片</div>

  <!-- 9.7 综合研判与操作计划（grid-2：技术面评分5维+评级 + 操作计划表） -->
  <h3>综合研判与操作计划</h3>
  <div class="grid-2">技术面评分 · 操作计划表</div>
</div>
```

### 各节详细规范

#### 第9章内部顺序（强制）

**信号速览 → 技术指标图表 → 多周期趋势 → 位置与形态 → 动量与量价 → 资金面 → 市场风格 → 综合研判（操作计划已移至核心结论区）**

#### 当前技术信号速览（6卡片）
- 布局：`grid-3`（3列×2行 = 6卡片）
- 每个卡片：`card-bg-alt` 背景 + `border-left:3px solid` 语义色 + 指标名 + 状态 + 数值
- 颜色语义：多头=红色、空头=绿色、中性=金色、弱势=灰色
- 指标：MACD、KDJ、RSI、BOLL、均线、成交量

#### 技术指标图表（紧接信号速览，与上方MACD/KDJ等指标关联最近）
- 布局：`grid-2` × 2行 = 4个图表
- **MACD图**：DIF(金色折线) + DEA(蓝色折线) + MACD柱(红涨绿跌)
- **KDJ图**：K(金色) + D(蓝色) + J(红色)，Y轴0-100
- **RSI图**：RSI6(蓝) + RSI12(金) + RSI24(红)，Y轴0-100
- **BOLL图**：上轨(红) + 中轨(金) + 下轨(绿) + 收盘价折线(蓝) + 填充区域
- **JS 来源：** `template_base.js` 已含全部计算函数和渲染函数，AI Phase 3 Batch 6 直接搬运
- 图表容器：`chart-macd`/`chart-kdj`/`chart-rsi`/`chart-boll`，高度280px/260px

#### 多周期趋势分析
- 布局：`grid-3`（月线/周线/日线）
- 每列：`card-bg-alt` 背景 + `border-left:4px solid` + 状态描述 + 均线数据 + 信号标签(`<span>`)
- 下方：`💡 多周期判断` 提示框（`border-left:4px solid var(--gold)`）
- 信号标签颜色：多头=红底红字、中性偏多=金底金字、短期透支=橙底橙字

#### 9.3 位置与形态分析
- 布局：`grid-2`
- 左：关键技术位表格（`table.cons`，列：类型/价格/说明，支撑位绿色/压力位红色）
- 右：形态识别表格（`table.cons`，列：形态/完整度/说明）+ 形态评估提示框
- 价格来源于 MD 报告 Step 6 分析内容

#### 9.4 动量与量价分析
- 布局：`grid-2`
- 左：动量指标表格（`table.cons`，列：周期/涨幅/评估，红色涨绿色跌）
- 右：量价配合表格（`table.cons`，列：日期/价格/成交量/关系）
- 下方：⚠️ 动量预警提示框（`border-left:4px solid var(--orange-warn)`）

#### 9.5 资金面分析
- 布局：`<ul>` 列表
- 内容：主力资金流向（近20日累计+超大单/大单拆分）、北向资金持仓变化、龙虎榜数据
- 数据来源：MD 报告 Step 6a+ 资金面分析内容

#### 9.6 市场风格与板块轮动
- 布局：`grid-2`
- 左：近20日涨停板块TOP5表格（`table.cons`，列：板块/涨停次数/趋势）
- 右：市场风格判断卡片（当前风格/轮动特征/对本股影响/操作建议）
- 数据来源：MD 报告 Step 1 宏观分析 + MCP搜索

#### 9.7 综合研判与操作计划
- 布局：`grid-2`
- 左：技术面评分（5个维度的 `score-bar` + 加权总评 + ⭐技术面评级）
- 右：操作计划表格（`table.cons`，列：项目/价格仓位/说明，买入=绿色/卖出/目标=红色）
- 下方：📌 操作建议提示框（`border-left:4px solid var(--red-up)`）
- 评分维度（5维，与 Step 8 综合交易评分区分）：多周期趋势(25%)/技术指标(20%)/形态完整度(20%)/量价配合(15%)/资金面(20%)

### 第9章 Batch 分配

**第9章在 Batch 5 中与 Step 7-8 一同写入**（从范例 Read 对应区域后 Write）。JS 图表渲染函数在 Batch 6 中通过搬运 `template_base.js` 完成。

### 第9章 grep 校验（Batch 5 追加）

| 检查项 | 命令 | 通过条件 |
|--------|------|---------|
| 9.1-9.7 完整 | `grep -c '多周期趋势\|技术指标图表\|位置与形态\|动量与量价\|资金面分析\|市场风格\|综合研判'` | ≥ 7 |
| 4图表容器 | `grep -c 'chart-macd\|chart-kdj\|chart-rsi\|chart-boll'` | = 4 |
| 技术面评分 | `grep -c '技术面评分\|技术面总评\|技术面评级'` | ≥ 3 |
| 操作计划 | `grep -c '买入区间\|加仓位置\|止损位置'` | ≥ 3 |
| 信号标签 | `grep -c '多头信号\|中性偏多\|短期透支\|空头信号'` | ≥ 2 |

---

## 🔄 增量更新详细说明

### 使用场景

报告已生成，需要更新最新数据（K线、Hero行情、技术指标），但不需要重新分析。

### 触发方式

用户说"更新 XXX股票"或"刷新 XXX报告"时，AI执行增量更新。

### 执行命令

```bash
cd G:/vibe/my-skills/stock-analysis-enhanced副本
python update_stock_report.py <股票代码>
```

**常用参数：**
```bash
# 基本用法（自动查找HTML文件）
python update_stock_report.py 000066

# 指定HTML文件
python update_stock_report.py 000066 --html output/个股研究-中国长城.html

# 强制更新（跳过检查，直接更新）
python update_stock_report.py 000066 --force
```

### 更新内容

| 内容 | 是否更新 | 说明 |
|------|---------|------|
| K线数据（rawData数组） | ✅ | 从akshare获取最新120条日K线 |
| Hero区域（最新价、涨跌幅） | ✅ | 从akshare获取实时行情 |
| 第9章技术指标 | ✅ | 重新计算MACD/KDJ/RSI/BOLL，更新图表数据 |
| 基本面分析（Step 0-8） | ❌ | 不更新，需要重新分析请用首次分析 |

### 工作流程

```
1. 提取旧K线数据（从HTML中的rawData数组）
   ↓
2. 获取最新K线数据（akshare实时获取）
   ↓
3. 对比数据变化（最新交易日、新增天数）
   ↓
4. 输出检查报告（需要更新 / 无需更新）
   ↓
5. 如果需要更新：
   - 更新K线数据（替换HTML中的rawData数组）
   - 更新Hero区域数据（价格、涨跌幅等实时数据）
   - 更新第9章技术指标（重新计算并替换technicalData数组）
   - 生成带日期版本（如：个股研究-中国长城_20260528.html）
   - 覆盖最新版本（无日期文件名）
```

### 判断标准

- 如果 `新K线最后交易日 > 旧K线最后交易日` → 需要更新
- 否则 → 无需更新

### 示例输出

```
📊 检查 000066 的更新情况...
   旧HTML: output/个股研究-中国长城.html

[1/2] 提取旧K线数据...
   ✅ 旧K线数据：120条，最新日期 2026-05-20

[2/2] 获取最新K线数据...
   尝试获取数据... (第1/3次)
   ✅ 新K线数据：120条，最新日期 2026-05-27

[3/3] 对比数据变化...

============================================================
📋 更新检查报告
============================================================
✅ 需要更新

变化点：
  1. K线数据更新：2026-05-20 → 2026-05-27，新增5个交易日
============================================================

============================================================
🔄 开始增量更新
============================================================

[1/4] 更新K线数据...
   ✅ K线数据已更新：120条

[2/4] 更新Hero区域数据...
   ✅ Hero数据已更新：价格 18.99，涨跌幅 -3.16%

[3/4] 更新第9章技术指标...
   ✅ 技术指标已更新：120 条记录

[4/4] 覆盖最新版本...
   ✅ 已覆盖：output/个股研究-中国长城.html

============================================================
✅ 更新完成
============================================================

📄 输出文件：
   • 带日期版本：output/个股研究-中国长城_20260527.html
   • 最新版本：output/个股研究-中国长城.html

📊 文件大小：85.3 KB
```

### 版本管理

**生成两个文件：**
1. **带日期版本**：`个股研究-{股票名称}_{YYYYMMDD}.html`
   - 保留历史版本，便于对比分析
   - 建议保留最近30天的版本

2. **最新版本**：`个股研究-{股票名称}.html`（覆盖原文件）
   - 始终保持最新
   - 便于快速访问

### 常见问题

**Q1: 如何判断是否需要更新？**
A: 工具会自动对比旧数据和新数据的最新交易日，如果新数据的最新交易日 > 旧数据，则需要更新。

**Q2: 更新后原文件会被覆盖吗？**
A: 会生成两个文件：带日期版本（新文件，不覆盖）+ 最新版本（覆盖原文件）。历史版本会保留。

**Q3: 网络请求失败怎么办？**
A: 工具会自动重试3次，如果仍然失败，更新失败。建议检查网络连接或稍后重试。

**Q4: 如何回退到旧版本？**
A: 直接使用带日期的历史版本文件即可，例如：
```bash
cp output/个股研究-中国长城_20260520.html output/个股研究-中国长城.html
```

**Q5: 更新频率建议？**
A: 
- **日线数据**：每个交易日收盘后更新一次（15:30后）
- **同一交易日多次触发**：检查发现无新数据，自动跳过更新
- **跨多个交易日触发**：一次性更新到最新

---

## 📋 跟踪日志与版本记录

### 设计理念

每次首次分析产生"初始化跟踪结果"，每次增量更新在跟踪表中**新增一列**，标记更新日期和变化内容。这样所有历史跟踪数据在同一张表中可见，无需翻找旧版本文件。

### 跟踪表格结构：催化剂兑现追踪

**核心理念：** 不是记录数据快照（股价多少/成交量多少），而是追踪**分析中识别的关键催化剂是否兑现**。每行 = 一个催化剂/事件，状态 = 已兑现/待兑现/落空/持续观察。

#### 首次分析（初始化）

```html
<table class="cons" style="font-size:12px;">
<thead><tr><th>跟踪指标 / 催化剂</th><th>预期影响</th><th>兑现状态</th><th>备注</th></tr></thead>
<tbody>
<tr><td>催化剂1（如异环1.1版本）</td><td>流水验证→估值修复</td><td>⏳ 待兑现</td><td>预计6月</td></tr>
<tr><td>催化剂2（如H1业绩预告）</td><td>确认盈利趋势</td><td>⏳ 待兑现</td><td>预计7月</td></tr>
<tr><td>已兑现事件（如首日流水）</td><td>验证吸量能力</td><td style="color:var(--red-up);">✅ 已兑现</td><td>05-28确认</td></tr>
<tr><td>止损观察</td><td>风险控制底线</td><td style="color:var(--text-muted);">⚪ 安全区间</td><td>当前价>止损线</td></tr>
</tbody>
</table>
```

**状态标记：**
- ✅ 已兑现（红色）— 催化剂如期发生，验证分析逻辑
- ⏳ 待兑现（金色）— 尚未发生，仍在等待窗口期
- ❌ 落空（绿色）— 预期落空，需重新评估投资逻辑
- ⚪ 持续观察（灰色）— 中性状态，持续监控

**催化剂来源：** 从 MD 报告的 Step 4（弹性测算）、Step 5（风险/止损信号）、Step 6（估值催化剂）、Step 7（对标）中提取，选取 6-10 个最关键的可验证事件。

#### 增量更新

**每次"更新 XXX股票"时，AI 检查每个催化剂的状态变化：**

1. 已到期的催化剂 → 判断 ✅已兑现 或 ❌落空
2. 仍在等待的 → 保持 ⏳待兑现
3. 新出现的催化剂 → 追加新行
4. 在表格下方"📋 事件记录"中追加更新说明

**不需要插入新列**（与旧设计不同）。催化剂的行是固定的，更新的是每一行的"兑现状态"列。

### 事件记录

**跟踪表格下方必须添加事件记录：**

```html
<div class="update-log" style="margin-top:12px;padding:10px 14px;background:var(--card-bg-alt);border-radius:8px;border-left:4px solid var(--gold);">
<p style="font-weight:700;color:var(--gold);margin-bottom:6px;">📋 事件记录</p>
<ul style="list-style:none;padding:0;font-size:12px;color:var(--text-secondary);">
<li style="padding:3px 0;">• 2026-05-28 首次分析：异环首日流水1亿+已兑现（验证吸量），1.1版本/H1业绩/TI赛事待兑现，当前价14.28>止损12元安全</li>
</ul>
</div>
```

### 更新流程中的跟踪日志维护

**AI执行增量更新时的职责（每次"更新 XXX股票"时执行）：**

1. **刷新近期动态**：将新闻列表替换为当日最新8条新闻，重新判断利好/利空/中性
2. **检查催化剂兑现**：逐行检查到期催化剂是否兑现，更新状态标记
3. **追加新催化剂**：如有新的关键事件，追加新行
4. **在事件记录顶部插入新条目**：日期 + 本次更新发现的变化
5. **同步分析基准日**：nav + hero + footer 三处

**增量更新 HTML 修改清单：**

| 步骤 | 操作 | 位置 |
|------|------|------|
| 1 | 替换新闻列表（8条→新8条+利好利空标签） | grid-2 近期动态卡片 |
| 2 | 逐行检查催化剂兑现状态、必要时更新 | 跟踪日志表 `<tbody>` |
| 3 | 有新催化剂则追加 `<tr>` | 跟踪日志表末尾 |
| 4 | 事件记录顶部插入新 `<li>` | 📋 事件记录 `<ul>` |
| 5 | 更新 `📅 YYYY-MM-DD` | nav + hero + footer 三处 |

**自动更新工具 `update_stock_report.py` 的职责：**
- 更新 K线数据（rawData数组）✅ 已实现
- 更新 Hero行情（价格/涨跌幅）✅ 已实现
- 更新 第9章技术指标 ✅ 已实现
- 更新 跟踪表格（AI手动执行）
- 刷新 新闻列表（AI手动执行）
- 更新 分析基准日（AI手动执行）

### 分析基准日声明

**分析基准日在三处显示：**

| 位置 | 格式 | 说明 |
|------|------|------|
| 顶部Nav | `📅 YYYY-MM-DD` | nav-links右侧、theme-toggle按钮左侧，12px字号，颜色跟随主题 |
| Hero卡片 | hero-meta第1项，标签"分析基准日"，值`YYYY-MM-DD` | 数据截止日/最近交易日 |
| 页脚Footer | `📅 分析基准日：YYYY-MM-DD · 数据来源：akshare/同花顺/新浪` | 与免责声明同一行 |

**Nav中的分析日期CSS：**
```css
.nav-analysis-date{font-size:12px;color:var(--text-muted);margin:0 8px;white-space:nowrap}
body.light-mode .nav-analysis-date{color:var(--text-muted)}
```

---

> **免责声明：** 本系统所有分析仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。

---

> **免责声明：** 本系统所有分析仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。
