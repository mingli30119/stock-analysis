# 项目结构说明

```
stock-analysis/
├── .github/
│   └── workflows/
│       ├── test.yml              # CI测试
│       └── release.yml           # 发布流程
├── docs/
│   ├── 设计规范.md               # HTML设计规范
│   ├── 分析框架.md               # 8步分析框架
│   ├── 使用指南.md               # 使用文档
│   └── 优化建议.md               # 优化建议
├── examples/
│   ├── basic_usage.py            # 基础示例
│   └── advanced_usage.py         # 高级示例
├── src/
│   ├── __init__.py
│   ├── data_fetcher.py           # 数据获取（akshare）
│   ├── analyzer.py               # 分析生成（8步框架）
│   ├── html_renderer.py          # HTML渲染（ECharts）
│   └── utils.py                  # 工具函数
├── output/                       # 输出目录（自动创建）
├── cache/                        # 缓存目录（自动创建）
├── logs/                         # 日志目录（自动创建）
├── main.py                       # 主入口
├── config.yaml                   # 配置文件
├── requirements.txt              # 依赖包
├── .gitignore
├── LICENSE
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── PROJECT_STRUCTURE.md
```

## 核心模块说明

### main.py
主入口，提供命令行接口和Python API。

### src/data_fetcher.py
数据获取模块，使用akshare获取：
- 基本信息
- K线数据
- 财务指标
- 主营业务
- 新闻资讯

### src/analyzer.py
分析生成模块，实现8步分析框架：
- Step 0: 任务锁定
- Step 1: 宏观与周期定位
- Step 2: 产业链深度拆解
- Step 3: 公司筛选与质量评分
- Step 4: 业绩弹性测算
- Step 5: 风险分析
- Step 6: 估值与买卖时机
- Step 7: 对标分析
- Step 8: 跟踪计划

### src/html_renderer.py
HTML渲染模块，生成专业报告：
- 双主题切换
- ECharts图表
- 响应式布局
- 交互功能

### src/utils.py
工具函数：
- 日志设置
- 目录管理
- 配置加载

## 数据流

```
用户输入股票代码
    ↓
DataFetcher.fetch()
    ├─ akshare获取数据
    └─ 保存到JSON
    ↓
Analyzer.analyze()
    ├─ 8步分析
    └─ 生成Markdown
    ↓
HTMLRenderer.render()
    ├─ 解析MD+JSON
    ├─ 生成HTML
    └─ 保存到output/
    ↓
返回HTML路径
```

## 扩展指南

### 添加新的数据源

编辑 `src/data_fetcher.py`：
```python
def fetch_new_data(self, code):
    # 实现数据获取逻辑
    pass
```

### 添加新的分析步骤

编辑 `src/analyzer.py`：
```python
def step_9_new_analysis(self, data):
    # 实现分析逻辑
    return "## Step 9: 新分析\n..."
```

### 自定义HTML样式

编辑 `src/html_renderer.py`，修改CSS变量：
```python
:root {
  --bg: #0c0f15;
  --card-bg: #1a1c24;
  ...
}
```
