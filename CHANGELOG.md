# CHANGELOG（stock-analysis 统一修改日志）

> **所有版本的 skill 层面改动统一记录于此。** competition 版本不再保留独立 CHANGELOG。
> 只记录 skill 定义文件改动，不记录 output/ 下的生成结果。

---

## 2026-05-29（续·三）

### [fix] 浅色模式 body 内联白色文字修复 + 新闻去链接 + 跟踪时间戳 + 更新流程文档化

**浅色模式深度审计：** CSS 级别 `color:#fff` 已有覆盖，但 HTML body 中有 3 处内联 `style="color:#fff"`（Step0标的/核心命题/弹性树顶层节点）在 `card-bg-alt`（`#fef5e7`暖奶油色）背景上完全不可见。全部改为 `color:var(--text-primary)`。

**新增禁止规则：** SKILL.md + HTML手写参考.md 新增"禁止HTML body内联硬编码颜色"约束 + Batch 1 grep 检查 `style="color:#fff"`=0。

**新闻列表去链接：** 因暂无新闻链接来源，新闻改为纯文本 `<span>`（保留利好/利空/中性标签），移除 `<a>` 和 Batch grep `<a href=` 检查。

**跟踪表格时间戳：** 每单元格加 `MM-DD:` 前缀（如 `05-28: 14.28元(+2.66%) ✅`），增量更新时新列同理。

**增量更新流程文档化：**
- SKILL.md 跟踪日志章节新增 5 步更新流程（新闻刷新→表头插列→行插单元格→更新记录→分析基准日同步）
- HTML手写参考.md 跟踪日志表组件新增更新规则说明
- 近期动态规范新增：增量更新时替换为当日最新8条新闻，重新判断利好利空

**修改文件：**
- `SKILL.md`: 近期动态规范（去`<a>`+增量刷新规则）、禁止内联白色规则、更新流程5步清单、Batch 1 grep 更新
- `HTML手写参考.md`: 新闻列表重写、跟踪日志表增强、Batch 1 grep 新增内联白字检查
- `output/个股研究-完美世界.html`: 3处内联 `color:#fff` 修复 + 新闻去 `<a>` + 跟踪表加 `MM-DD:` 前缀

---

### [feat] 完美世界报告作为新基线，补齐 skill 文档断层

**背景：** 完美世界 HTML 已落地的新增功能（新闻利好利空标签、K线技术标注、跟踪日志列式表格、浅色模式修复、分析时间戳）从未写入 skill 定义文件，导致新会话无法对齐这些改进。

**补齐内容：**

**近期动态组件（全新规范）：**
- 每条新闻必须用 `<a>` 可点击，禁止滚动容器（`max-height`/`overflow-y`）
- 每条右侧强制利好/利空/中性标签（利好=红底红字、重大利好=红底红字+红色左边框、中性=金底金字），标签文字≤4字
- Batch 1 grep 新增：`利好|利空|中性`≥5条、`<a href=`≥5条、`overflow-y|max-height:300`=0

**K线技术标注组件（全新规范）：**
- 4条markLine（虚线金色）：前高压力/关键均线/加仓位/止损位，价格取自MD报告
- 2个markPoint（pin图标）：当前价位(金色)+关键历史价位(红色)
- Batch 2a grep 新增：`markLine`≥1、`markPoint`≥1

**跟踪日志表组件（全新规范）：**
- 表头：`跟踪指标 | 初始化 YYYY-MM-DD | 数据来源`
- 每行含变化标记（✅红色/⚪灰色/❌绿色），表格下方必有 `📋 更新记录` 区块
- Batch 4 grep 新增：`跟踪日志|初始化 20`存在、`📋 更新记录`存在

**修改文件：**
- `SKILL.md`: 新增3条关键约束（近期动态/K线标注）+ Batch 1/2/5 grep 更新 + nav分析日期位置修正
- `HTML手写参考.md`: 组件速查表新增3行（新闻列表重写/K线标注/跟踪日志）+ Batch 1/2a/4 grep 更新 + nav模板修正
- `shared/template_base.css`: 新增7条浅色覆盖 + nav-analysis-date class + margin修正
- 同步至原版 `stock-analysis-enhanced/`

---

**设计：** 首次分析产生"初始化跟踪结果"表格（Step 8 中），每次增量更新在表中**新增一列**（`更新 YYYY-MM-DD`），所有历史跟踪数据在同一张表中纵向可见。

每列标记变化方向（✅有利/⚪中性/❌不利），表格下方有更新日志摘要列表。

**修改文件：**
- `SKILL.md`: 新增「📋 跟踪日志与版本记录」章节
- `HTML手写参考.md`: nav结构增加 `nav-analysis-date`，footer增加分析基准日行

### [feat] 分析时间戳三处声明

分析基准日在三个位置同步显示：
1. **Nav**: logo右侧，`📅 YYYY-MM-DD`，class `nav-analysis-date`
2. **Hero**: hero-meta 第1项（4项→5项），标签"分析基准日"
3. **Footer**: 与数据截止日期同行显示

### [fix] 浅色模式白色文字不可见修复

**问题：** `.top-nav .logo{color:#fff}` 和 `.top-nav .logo-icon{color:#fff}` 在浅色模式下白色文字在浅色背景上完全不可见。`.theme-toggle` 按钮在浅色模式下辨识度差。

**修复：** 在 `body.light-mode` 段新增 6 条覆盖规则（logo/logo-icon/stock-name/stock-code/theme-toggle/theme-toggle:hover/kpi-info-item.value）。

**修改文件：**
- `shared/template_base.css`: 新增浅色模式覆盖 + `nav-analysis-date` class
- `SKILL.md`: 新增「🌓 双主题颜色规范」章节，含强制检查清单和禁止硬编码表
- `HTML手写参考.md`: hero-meta 4→5项、nav增加分析日期元素、footer模板更新

### [chore] 版本号 v3.0 → v3.1

---

## 2026-05-03（晚间·二）

### [chore] 文件整理：三版本对齐

**competition/archive/** → `G:/vibe/archive/competition-v1-skeleton/`
**competition/output/\*** (除中国长城) → `enhanced/output/`
**competition 核心文件** → 覆盖 enhanced + github（SKILL.md, HTML手写参考.md, 分析框架.md, 设计规范, stock_full_report.py, shared/, examples/）

竞争版 output 只保留：`data_000066.json` + `个股研究-中国长城.{html,md}`（演示用）

---

## 2026-05-03（晚间）

### [fix] 参考范例路径不变规则写入

**原因：** 之前范例路径从 `examples/中国长城` 被改为 `output/圣阳股份`，output 下文件不稳定。现在在 SKILL.md 中写死规则。

**修改文件：**
- `enhanced/SKILL.md`: 新增 ⚠️ 参考范例路径不可变规则
- `competition/SKILL.md`: 同上

### [chore] CHANGELOG 统一

**原因：** competition 是参赛版本，修改日志统一到 enhanced 下。competition 的 CHANGELOG.md 已删除。

---

## 2026-05-03（下午）

### [fix] 参考范例回退：圣阳股份 → 中国长城

**原因：** 范例引用路径被错误改为 `output/个股研究-圣阳股份.html`。`output/` 下是生成结果（行号每次不同），应使用 `examples/个股研究-中国长城.html`（稳定范例，864行）。

**修改文件（两个版本同步）：**
- `SKILL.md`: 路径 + 全部 batch Read 行号重映射
- `HTML手写参考.md`: 路径 + 行号 + grep 提取命令

### [add] 终验自检清单（10 grep + 4 目视）

**原因：** 4 个已知 Bug 的防御分散在 SKILL.md 合并行和 HTML手写参考.md 5 条终验中，缺少集中、强制、可追溯的终验环节。

每条检查标注防御的具体 Bug，失败 → grep 定位 → Edit 修正 → 重跑。

**修改文件（两个版本同步）：**
- `HTML手写参考.md`: 新增「🔧 终验自检清单」独立章节，替代旧「合并后终验」
- `SKILL.md`: 合并行改为引用终验自检清单

### [fix] Bug 1-4 修复（skill 层面，两个版本同步）

| Bug | 根因 | 防御措施 |
|-----|------|---------|
| **Bug 1:** JS 数据乱码 | `template_base.js` 占位符周围中文注释干扰替换 | 清洁版占位符 + Batch 5 四重 grep |
| **Bug 2:** 全页 JS 炸裂 | `<script>` 未闭合，浏览器把 HTML 当 JS | `</script>≥4` + `tail -20` 检查 |
| **Bug 3:** 评分条不显示 | `<span>` inline → width 无效 | `<div>` 强制 + `grep span=0` |
| **Bug 4:** MathJax 不渲染 | 双反斜杠 `\\(` 不匹配单反斜杠分隔符 `\(` | 单反斜杠规则 + `grep \\\\times=0` |

**修改文件：**
- `shared/template_base.js`: 占位符重写为清洁版
- `SKILL.md`: MathJax 单反斜杠规则 + score-fill div 强制 + Batch 5 增强校验
- `HTML手写参考.md`: 评分条 div 强制 + MathJax 章节 + 终验增强
