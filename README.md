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

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行分析

```bash
python main.py 600737
```

### 3. 查看报告

生成的报告位于 `output/` 目录：
- `个股研究-中粮糖业.md` - Markdown分析报告
- `个股研究-中粮糖业.html` - HTML可视化报告
- `data_600737.json` - 原始数据

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
- Email: longquan830@163.com
- 公众号: 明立玩AI

---

**⭐ 如果这个项目对你有帮助，请给个Star！**
