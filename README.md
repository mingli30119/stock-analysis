# 📊 个股深度分析系统

> 基于akshare的A股个股深度研究报告生成工具
> 
> 自动获取数据 → 8步深度分析 → 生成专业HTML报告

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## ✨ 功能特性

- ✅ **自动数据获取** - 基于akshare获取股票数据（K线、财务、新闻等）
- ✅ **8步分析框架** - 宏观定位、产业链、质量评分、弹性测算、风险分析、估值、对标、跟踪
- ✅ **专业HTML报告** - 双主题切换、响应式布局、ECharts图表
- ✅ **真实K线数据** - 含MA5/20/60均线、成交量、技术指标
- ✅ **产业链可视化** - SVG图表展示上中下游关系
- ✅ **评分系统** - 5维度质量评分（基本面、产业匹配、弹性、估值、治理）

---

## 📸 效果预览

![个股分析报告示例](docs/images/dark-mode.png)

*示例：中国长城（000066）深度分析报告 - 包含K线图、产业链SVG、评分系统、弹性测算等完整分析*

---

## 🚀 快速开始

### 方式零：网页端（直接渲染 HTML 报告）

在浏览器中输入股票代码，自动生成并展示完整 HTML 研报：

```bash
pip install -r requirements.txt
./run_web.sh
# 或: uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```

打开 http://localhost:8000 ，输入代码（如 `600519`）即可。首次生成约 2–5 分钟；1 小时内同一股票会使用缓存。

**部署到腾讯轻量服务器**：见 [docs/deploy-tencent-lighthouse.md](docs/deploy-tencent-lighthouse.md)。首次 `sudo bash deploy/install.sh`，之后推送到 `main` 可由 **GitHub Actions** 自动部署（配置 `DEPLOY_HOST` 等 Secrets）。

| 路径 | 说明 |
|------|------|
| `/` | 首页，输入代码 |
| `/report/{代码}` | 生成中（进度页） |
| `/view/{代码}` | 直接查看 HTML 报告 |
| `/examples/demo` | 示例深度研报（中国长城） |

---

### 方式一：作为 Claude Code Skill 调用（推荐）

**直接对话触发：**

```
用户：分析 600519 股票
用户：分析贵州茅台
用户：个股分析 000066
```

AI 会自动执行完整的三阶段流程：
1. **Phase 1**：运行 `python stock_full_report.py 600519` 采集数据
2. **Phase 2**：AI 深度分析，生成 MD 报告
3. **Phase 3**：AI 手写 HTML，生成可视化报告

**输出文件：**
- `output/data_600519.json` - 原始数据
- `output/个股研究-贵州茅台.md` - 分析报告
- `output/个股研究-贵州茅台.html` - 可视化报告

---

### 方式二：手动运行 Python 脚本

如果只需要数据采集（Phase 1），可以手动运行：

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行数据采集
python stock_full_report.py 000066
```

**注意：** 手动运行只会生成 `data_000066.json`，不会自动进行 Phase 2/3 的分析和 HTML 生成。完整分析需要使用方式一（Skill 调用）。

---

### 方式三：查看已生成的报告

生成的报告位于 `output/` 目录：
- `个股研究-中国长城.md` - Markdown分析报告
- `个股研究-中国长城.html` - HTML可视化报告
- `data_000066.json` - 原始数据

---

## 📁 项目结构

```
stock-analysis/
├── main.py                     # 主入口
├── phase1_data_fetcher.py      # 数据获取
├── phase2_analyzer.py          # 分析生成
├── phase3_html_renderer.py     # HTML渲染
├── requirements.txt            # 依赖包
├── config.yaml                 # 配置文件
├── docs/                       # 文档
│   ├── 设计规范.md
│   ├── 分析框架.md
│   └── 使用指南.md
├── output/                     # 输出目录
└── README.md
```

---

## 📖 使用指南

### 基础用法

```python
from main import StockAnalyzer

# 创建分析器
analyzer = StockAnalyzer()

# 分析单只股票
analyzer.analyze('600737')

# 批量分析
analyzer.batch_analyze(['600737', '000858', '600737'])
```

### 配置说明

编辑 `config.yaml` 自定义配置：

```yaml
data:
  cache_dir: "./cache"
  cache_ttl: 3600

output:
  html_dir: "./output/html"
  md_dir: "./output/md"

akshare:
  timeout: 30
  retry: 3
```

---

## 🎨 HTML报告特性

### 双主题切换
- **深色模式**：适合长时间盯盘
- **浅色模式**：适合打印或明亮环境

### 核心组件
1. **Hero行情卡片** - 最新价、涨跌幅、关键指标
2. **结论置顶** - 综合判断、投资建议
3. **公司画像** - 主营业务、标签、新闻
4. **主营业务饼图** - ECharts环形图
5. **关键财务指标** - 营收、净利、毛利率、资产负债率
6. **K线图** - 双Grid布局、MA均线、成交量
7. **产业链SVG** - 上中下游可视化
8. **评分条** - 5维度质量评分
9. **情景分析** - 悲观/基准/乐观三情景
10. **风险信号** - 止损条件列表

### 交互功能
- 导航滚动高亮
- 平滑滚动定位
- 图表响应式调整
- 主题切换时图表重绘

---

## 📊 分析框架

### Step 0: 任务锁定
- 股票基本信息
- 行业归属
- 主营业务

### Step 1: 宏观与周期定位
- 经济阶段判断
- 行业周期位置
- 政策方向分析

### Step 2: 产业链深度拆解
- 上中下游关系
- 价值链分析
- 竞争格局

### Step 3: 公司筛选与质量评分
- 市值门槛
- 行业地位
- 业务聚焦度
- 5维度评分（总分100）

### Step 4: 业绩弹性测算
- 悲观/基准/乐观三情景
- 敏感度分析
- 盈利预测

### Step 5: 风险分析
- 风险类型识别
- 影响程度评估
- 止损信号设定

### Step 6: 估值与买卖时机
- 短期/中期/长期目标价
- 盈亏比计算
- 触发条件

### Step 7: 对标分析
- 同行业公司对比
- 增长引擎判断
- 竞争优势分析

### Step 8: 跟踪计划
- 关键指标监控
- 定期复盘计划
- 综合结论

---

## 🔧 技术栈

- **数据获取**: akshare
- **数据分析**: pandas, numpy
- **图表渲染**: ECharts 5.5.1
- **HTML生成**: Python Jinja2
- **样式设计**: CSS3 (双主题)

---

## 📝 数据来源

- **股票数据**: akshare
- **K线数据**: akshare.stock_zh_a_hist()
- **财务数据**: akshare.stock_financial_abstract()
- **新闻数据**: akshare.stock_news_em()
- **行业信息**: 本地知识库 + MCP搜索（可选）

---

## ⚠️ 免责声明

本工具仅供学习研究使用，不构成任何投资建议。

股市有风险，投资需谨慎。使用本工具产生的任何投资决策及其后果，均由使用者自行承担。

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/mingli30119/stock-analysis.git

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/
```

### 提交规范

- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试
- chore: 构建/工具

---

## 📄 许可证

[MIT License](LICENSE)

---

## 👨‍💻 作者

[@mingli30119](https://github.com/mingli30119) - 明立玩AI

---

## 🙏 致谢

- [akshare](https://github.com/akfamily/akshare) - 数据源
- [ECharts](https://echarts.apache.org/) - 图表库
- [Claude](https://claude.ai/) - AI辅助开发

---

## 📮 联系方式

- GitHub: [@mingli30119](https://github.com/mingli30119)
- Email: shemingli@126.com
- 公众号 · 抖音 · 小红书：明立玩AI

---

**⭐ 如果这个项目对你有帮助，请给个Star！**
