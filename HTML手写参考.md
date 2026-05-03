# HTML手写参考（Phase 3 时读取）

> AI执行HTML生成时严格遵循。所有CSS class来自 `shared/template_base.css`，不存在于模板的不要用。

---

## ⚠️ 分批手写规则（最高优先级）

**HTML必须分批手写，禁止用Python脚本生成HTML内容。**

| 禁止 | 原因 |
|------|------|
| ❌ **Python f-string/template 生成HTML** | 需要大量 `{{}}` 转义，易出错不可维护 |
| ❌ **Bash heredoc 生成HTML** | 多行HTML下经常EOF匹配失败 |
| ❌ **一次性写出整个HTML** | >300行文件必须分批，每批独立一个Write调用 |
| ❌ **用 `python -c` 拼接HTML字符串** | 属于Python生成，不是手写 |

**正确工具：**

| 操作 | 工具 |
|------|------|
| 写入HTML内容 | **Write**（直接写markup，无转义） |
| 精确局部修改 | **Edit** |
| 合并部分文件 | **Bash `cat`** 或 Python `file.read()`（仅字节拼接） |

**标准分批（~900行→6批）：**

```
Batch 0: Write — DOCTYPE + <head> + <style>（CSS复制）              ~180行
Batch 1: Write — <body> + nav + hero + conclusion + profile         ~150行
Batch 2: Write — K线卡片 + Step 0-3                                 ~200行
Batch 3: Write — Step 4-6                                           ~200行
Batch 4: Write — Step 7-8 + footer + </div>                         ~150行
Batch 5: Write — <script>（JS复制 + 注入data）                      ~150行
```

---

## 模板文件

| 文件 | 用途 | 使用方式 |
|------|------|---------|
| `shared/template_base.css` | 规范CSS（175行） | **完整复制到 `<style>` 标签内**，不做任何修改 |
| `shared/template_base.js` | 规范JS（135行） | **复制到 `<script>` 标签内**，在 `RAW_DATA_PLACEHOLDER` 和 `PIE_DATA_PLACEHOLDER` 处注入数据 |
| `examples/个股研究-中国长城.html` | 成品范例 | 标准参考范例，包含弹性树连线/公式卡片/总结框等全部组件 |

## 页面结构（强制顺序）

```
1. top-nav          — 顶部导航（sticky）
2. .hero            — Hero行情卡片
3. .conclusion-top  — 结论置顶卡片
4. .grid-2          — 公司画像(.card) + 近期动态(.card)
5. .grid-2          — 主营业务饼图(.card) + 关键财务指标(.card)
6. .card            — K线图(#chart-kline-full, 480px) + kpi-info-row
7. .card#mission    — 任务锁定与核心矛盾
8. .card#macro      — 宏观与周期定位
9. .card#chain      — 产业链深度拆解
10. .card#quality   — 公司筛选与质量评分
11. .card#elasticity — 业绩弹性测算
12. .card#risk      — 风险分析
13. .card#valuation  — 估值与买卖时机
14. .card#compare   — 对标分析
15. .card#tracking  — 跟踪计划与综合结论
16. footer          — 页脚（固定模板，禁止修改结构）
```

### 页脚模板（强制）

```html
<footer>
<p>⚠️ 免责声明：本报告仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。</p>
<p>数据截止：{日期} | 研究状态：{首次覆盖/持续跟踪}</p>
<p style="font-size:11px;color:var(--text-muted);">数据来源：akshare(雪球/新浪/同花顺/东方财富/巨潮资讯) · GLM5.1 · DeepSeek-V4-Pro · Claude Opus-4.7 · 2026-05-03 · @明立玩AI · 个股深度研究系统 v2.2</p>
<p style="margin-top:6px;">作者：明立 · AI教育资深玩家 · AI应用落地近4年经验</p>
<p>📮 联系作者获取更多skill：ll-mingli1221</p>
</footer>
```
> 数据截止日期和研究状态由各股票实际情况填充，其余行禁止修改。

### 导航标签（13个固定文本，禁止修改）

```
行情 | 结论 | 画像 | K线 | 任务 | 宏观 | 产业链 | 质量 | 弹性 | 风险 | 估值 | 对标 | 跟踪
```

对应锚点：`#hero` `#conclusion-top` `#profile` `#kline-section` `#mission` `#macro` `#chain` `#quality` `#elasticity` `#risk` `#valuation` `#compare` `#tracking`

## 组件速查表

| 组件 | HTML结构 | CSS class | 注意事项 |
|------|----------|-----------|---------|
| **Hero** | `.hero > .hero-price-block + .hero-meta + .hero-tags` | `hero`, `hero-price`, `hero-meta-item` | 价格56px/900weight。**hero-meta 4项固定**：①质量评级（含分数）②中期目标价 ③当前盈亏比 ④风险等级。右上角径向光晕。**hero-tags ≤5个标签，每标签≤4个中文字**，用`.hero-tag`class |
| **结论置顶** | `.conclusion-top > .big-verdict + .verdict-detail + .verdict-tags` | `conclusion-top` | `::before`伪元素生成"核心结论"标签，金色边框 |
| **卡片** | `.card > .card-header + 内容` | `card`, `card-header` | header含icon+h2+.sub，底部2px分割线。**`.sub` 禁止写 "Step X" 编号**，应填有信息量的内容（如 "FY2025年报"）或留空 |
| **表格** | `table.cons > thead > tbody` | `cons` | 表头深色渐变，行底虚线分割，hover半透明 |
| **评分条** | `.score-bar > .score-label + .score-track > .score-fill + .score-num` | `score-bar`, `score-track`, `score-fill` | **`.score-fill` 必须用 `<div>`（禁止 `<span>`）**，`<span>` 默认 inline 导致 width 无效。**必须带内联 `style="width:X%"`**（X为该维度得分百分比），否则光柱不会显示。高分段(≥70%)用var(--gold)，中分段(40-69%)用var(--orange-warn)，低分段(<40%)用var(--red-up)。Step 3和Step 8各一套评分条，每套≥5条 |
| **情景卡片** | `.scenario(.bear/.bull) > strong + .prob + 内容` | `scenario`, `bear`, `bull` | 左侧4px色条：bear绿色/bull红色/默认金色 |
| **止损列表** | `ul.alert-list > li` | `alert-list` | 每项左侧4px橙色边框，次级背景色 |
| **评级徽章** | `.rating-callout > .badge + .body` | `rating-callout` | 金色圆形badge(64×64px)，渐变背景，2px金色边框 |
| **综合结论** | `.verdict-highlight > .judgment + .verdict-grid` | `verdict-highlight` | judgment金色22px/800weight，grid四列 |
| **产业链SVG** | `.chain-svg > svg` | `chain-svg`, `svg-hdr`, `svg-sub` | viewBox 800×180，文字用`.svg-hdr`和`.svg-sub`实现双主题 |
| **弹性树** | 顶层节点 → 竖线 → 横线分支 → flex(2:1:1)三列子节点 | 内联style | **强制使用HTML flex+CSS边框线构建树形图**。顶层金色边框节点，竖线(2px×6px gold)，横线(border-top:2px solid gold)，子节点flex比例2:1:1。颜色语义：🔴红色=核心业务·75%营收，🟡金色=次要业务·20%营收，⚪灰色=其他·5%营收。每个子节点包含：业务名+营收占比+毛利率+业务线明细+弹性因子。**禁止纯文本无树形图** |
| **公式卡片** | 次级背景色圆角卡片 | 内联style | monospace字体，结果红色加粗 |
| **清单** | `ul.checklist > li` | `checklist` | li::before '☐ '金色 |
| **新闻列表** | `.news-list > .news-item` | `news-list`, `news-item` | bullet红色·号，max-height 300px |
| **信息网格** | `dl.info-grid > dt + dd` | `info-grid` | 两列，dt灰色/dd白色 |
| **KPI行** | `.kpi-info-row > .kpi-info-item` | `kpi-info-row`, `kpi-info-item` | K线图下方4指标，分隔线 |
| **双列网格** | `.grid-2 > 子元素` | `grid-2` | 两列等宽，20px间距，850px断点变单列 |
| **三列网格** | `.grid-3 > 子元素` | `grid-3` | 三列等宽，16px间距，用于情景卡片 |

### 内容区子标题格式

**禁止使用 "1a/1b/1c/2a/3b" 等编号前缀。** 子标题直接写中文描述。

```
❌ <h3>1a. 经济周期映射</h3>
❌ <strong>2b. 产业链图谱</strong>
✅ <h3>经济周期映射</h3>
✅ <strong>产业链图谱</strong>
```

Step 卡片的子标题应使用 `<strong style="color:var(--gold);">` 或 `<h3 style="font-size:15px;color:var(--gold-light);...">` 样式，只写描述文字。

## 颜色语义（强制）

| 语义 | CSS变量 | 使用场景 |
|------|---------|---------|
| 上涨/买入/利好 | `--red-up` | K线阳线、正收益、乐观情景、强势标签 |
| 下跌/卖出/利空 | `--green-down` | K线阴线、止损价、悲观情景、风险指标 |
| 重点/结论/标题强调 | `--gold` / `--gold-light` | Hero数值、评分、关键结论、边框高亮 |
| 警告/中等/注意 | `--orange-warn` | 中等评分、止损信号、威胁提示 |
| 链接/MA5 | `--blue-accent` | K线MA5均线 |

## MathJax 公式（强制）

**⚠️ HTML源码中写单反斜杠，不是双反斜杠：**

| 写法 | HTML源码 | 浏览器textContent | MathJax匹配`\(`分隔符? |
|------|----------|-------------------|---------------------|
| ✅ 正确 | `\(E=mc^2\)` | `\(E=mc^2\)` | ✅ 匹配 |
| ❌ 错误 | `\\(E=mc^2\\)` | `\\(E=mc^2\\)` | ❌ 不匹配（多一个`\`） |

HTML text 中 `\` 不是转义符，所以源码写 `\\(` → 浏览器看到的就是两个字面反斜杠 `\\(`。MathJax 配置的分隔符是 `\(`（单反斜杠），不匹配双反斜杠。

**grep 自检：** `grep '\\\\times\|\\\\frac\|\\\\alpha\|\\\\cdot'` 应返回空（无残留双反斜杠公式）。

## 🔧 分批机械校验

**核心方式：每批先 Read 中国长城范例对应段落 → 再 Write → 最后 grep 兜底。范例刚读完就在上下文中，AI 的参照源就是它而不是自己的通用模板。**

**参考范例：** `examples/个股研究-中国长城.html`（864行，已知正确产出）。

### 前置：提取范例参照数据

```bash
# 提取范例的13个导航锚点（参照基准）
grep -o 'href="[^"]*"' examples/个股研究-中国长城.html | sort > /tmp/ref_nav.txt

# 提取范例的section id列表
grep -o 'id="[^"]*"' examples/个股研究-中国长城.html | grep -v 'chart-\|MathJax\|themeToggle\|arrow-\|svg-' | sort > /tmp/ref_ids.txt
```

### 执行规则

每批**强顺序三步**，不可跳过：
1. **Read 范例对应行号区间**（行号见下表）
2. **Write 本批 HTML**
3. **Bash grep 兜底**（命令见下表）

三步全部通过才进入下一批。grep 不通过 → `grep` 范例对应行 → `grep` 自己写的 → 看差异 → Edit 修正 → 重跑 grep。

### Batch 0: DOCTYPE + head + style

| 步骤 | 操作 | 校验命令 | 通过条件 |
|------|------|---------|---------|
| 1. Read | `Read examples/个股研究-中国长城.html line=1-121` | — | — |
| 2. Write | 写 `_h_part1.html` | — | — |
| 3. Grep | — | `grep -c '<style>' _h_part1.html` | = 1 |
| 3. Grep | — | `grep 'echarts' _h_part1.html` | 含 `echarts@5.5.1` |
| 3. Grep | — | `grep 'MathJax' _h_part1.html` | 含 `mathjax@3` CDN |

### Batch 1: nav + hero + conclusion-top + profile grid-2

| 步骤 | 操作 | 校验命令 | 通过条件 |
|------|------|---------|---------|
| 1. Read | `Read 中国长城 line=122-181` | — | — |
| 2. Write | 写 `_h_part2.html` | — | — |
| 3. Grep | — | `grep -oc 'href="#' _h_part2.html` | = 13 |
| 3. Grep | — | `grep -o 'href="[^"]*"' _h_part2.html \| sort \| diff - /tmp/ref_nav.txt` | 无差异 |
| 3. Grep | — | `grep -o 'id="[^"]*"' _h_part2.html \| sort` | 含 hero/conclusion-top/profile |
| 3. Grep | — | `grep 'news-list' _h_part2.html` | 存在 |
| 3. Grep | — | `grep -c 'hero-tag' _h_part2.html` | ≥ 3 |

### Batch 2a: 饼图 + 关键财务 grid-2 + K线card

| 步骤 | 操作 | 校验命令 | 通过条件 |
|------|------|---------|---------|
| 1. Read | `Read 中国长城 line=183-204`（饼图+财务） | — | — |
| 1. Read | `Read 中国长城 line=206-215`（K线card） | — | — |
| 2. Write | 写 `_h_part3.html` | — | — |
| 3. Grep | — | `grep 'kline-section' _h_part3.html` | 存在 |
| 3. Grep | — | `grep 'height:480px' _h_part3.html` | 存在 |

### Batch 2b: Step 0-3 卡片

| 步骤 | 操作 | 校验命令 | 通过条件 |
|------|------|---------|---------|
| 1. Read | `Read 中国长城 line=218-229`（mission/Step0） | — | — |
| 1. Read | `Read 中国长城 line=230-256`（macro/Step1） | — | — |
| 1. Read | `Read 中国长城 line=257-315`（chain/Step2） | — | — |
| 1. Read | `Read 中国长城 line=316-355`（quality/Step3） | — | — |
| 2. Write | 写 `_h_part4.html` | — | — |
| 3. Grep | — | `grep -o 'id="[^"]*"' _h_part4.html \| sort` | mission/macro/chain/quality 四者存在 |
| 3. Grep | — | `grep -c 'class="sub"' _h_part4.html` | ≥ 4 |
| 3. Grep | — | `grep 'rating-callout' _h_part4.html` | 存在 |
| 3. Grep | — | `grep 'chain-svg' _h_part4.html` | 存在 |

### Batch 3: Step 4-6 卡片

| 步骤 | 操作 | 校验命令 | 通过条件 |
|------|------|---------|---------|
| 1. Read | `Read 中国长城 line=356-436`（elasticity/Step4） | — | — |
| 1. Read | `Read 中国长城 line=437-465`（risk/Step5） | — | — |
| 1. Read | `Read 中国长城 line=466-508`（valuation/Step6） | — | — |
| 2. Write | 写 `_h_part5.html` | — | — |
| 3. Grep | — | `grep -o 'id="[^"]*"' _h_part5.html \| sort` | elasticity/risk/valuation 三者存在 |
| 3. Grep | — | `grep -c 'scenario' _h_part5.html` | = 3 |
| 3. Grep | — | `grep 'alert-list' _h_part5.html` | 存在 |
| 3. Grep | — | `grep '盈亏比' _h_part5.html` | 存在 |

### Batch 4: Step 7-8 + footer

| 步骤 | 操作 | 校验命令 | 通过条件 |
|------|------|---------|---------|
| 1. Read | `Read 中国长城 line=509-530`（compare/Step7） | — | — |
| 1. Read | `Read 中国长城 line=531-608`（tracking/Step8+footer） | — | — |
| 2. Write | 写 `_h_part6.html` | — | — |
| 3. Grep | — | `grep -o 'id="[^"]*"' _h_part6.html \| sort` | compare/tracking 存在 |
| 3. Grep | — | `grep 'verdict-highlight' _h_part6.html` | 存在 |
| 3. Grep | — | `grep '📌' _h_part6.html` | 存在 |
| 3. Grep | — | `grep 'footer' _h_part6.html` | 存在 |

### Batch 5: script

| 步骤 | 操作 | 校验命令 | 通过条件 |
|------|------|---------|---------|
| 1. Read | `Read 中国长城 line=610-864`（script段结构） | — | — |
| 1. Read | 读取 `_kline_120.json` 和 `_pie_js.json` | — | — |
| 2. Write | 写 `_h_part7.html` | — | — |
| 3. Grep | — | `grep -c 'PLACEHOLDER' _h_part7.html` | = 0 |
| 3. Grep | — | `grep -c 'rawData' _h_part7.html` | = 1 |

### 合并

```bash
cat _h_part*.html > 个股研究-XXX.html
```

---

## 🔧 终验自检清单（强制，不可跳过）

> **每条检查都是已知 Bug 的防御。全部 10 条通过才可输出最终文件。**
> **失败 → grep 定位问题 → Edit 修正 → 重跑该条，不推导原因。**

| # | 检查项 | 命令 | 通过条件 | Bug 防御 |
|---|--------|------|---------|---------|
| 1 | 导航锚点配对 | `grep -oc 'href="#' 个股研究-XXX.html` + `grep -o 'id="[^"]*"' \| grep -cE 'hero\|conclusion-top\|...'` | nav数 = 13, 关键id = 13 | 导航死链 |
| 2 | 锚点逐对验证 | `grep -o 'href="[^"]*"' \| tr -d 'href="' \| while read a; do grep -q "id=\\"${a#\#}\\"" || echo "MISSING: ${a#\#}"; done` | 无输出 | 导航死链 |
| 3 | `</html>` 唯一 | `grep -c '</html>' 个股研究-XXX.html` | = 1 | 结构缺失 |
| 4 | `</script>` 齐全 | `grep -c '</script>' 个股研究-XXX.html` | ≥ 4（3 CDN + 1 主JS） | **Bug 2: 全页 JS 炸裂** |
| 5 | 主JS闭合在末尾 | `tail -20 个股研究-XXX.html \| grep '</script>'` | 存在 | **Bug 2** |
| 6 | 评分条用 `<div>` | `grep -c '<span class="score-fill"' 个股研究-XXX.html` | = 0 | **Bug 3: 色条不显示** |
| 7 | MathJax 单反斜杠 | `grep -c '\\\\times\|\\\\frac\|\\\\alpha' 个股研究-XXX.html` | = 0 | **Bug 4: 公式不渲染** |
| 8 | 占位符清零 | `grep -c '__RAW_DATA_ARRAY__\|__PIE_DATA_ARRAY__\|替换为' 个股研究-XXX.html` | = 0 | **Bug 1: 数据乱码** |
| 9 | 子标题无编号前缀 | `grep -cE '<(h3\|strong)[^>]*>[0-9]+[a-c]\.' 个股研究-XXX.html` | = 0 | 格式污染 |
| 10 | Footer 结构完整 | `grep -c '免责声明' 个股研究-XXX.html` + `grep -c '作者：明立' 个股研究-XXX.html` + `grep -c 'll-mingli1221' 个股研究-XXX.html` | 全部 ≥ 1 | Footer 丢失 |

**必须也通过的补充检查（非 grep 可做，需目视确认）：**
- [ ] K线图成交量柱每根单独着色（红涨绿跌），不是统一颜色
- [ ] ECharts CDN 含 `echarts@5.5.1`，MathJax CDN 含 `mathjax@3`
- [ ] 所有 CSS class 来自 `template_base.css`，无自创 class 名
- [ ] `const rawData` 声明存在且仅一次（`grep -cF 'const rawData'` = 1）

**失败处理规则：**
1. 不推导原因、不猜测意图
2. 直接 `grep` 中国长城范例对应结构 → `grep` 自己写的对应位置 → 看差异 → Edit 修正
3. 修正后重跑同一条校验命令，通过才继续
4. 全部 10 条 + 补充检查通过 → 输出最终文件
