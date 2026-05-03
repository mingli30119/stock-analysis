#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2: AI分析层
分3个子阶段：
  2.1 基础信息写入（5分钟）
  2.2 触发MCP搜索（10分钟）
  2.3 AI逐步分析Step 0-8（30-60分钟）
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Step 0-8 强制执行配置
ANALYSIS_STEPS = [
    {
        "step": "Step 0",
        "name": "任务锁定",
        "min_lines": 10,
        "required_fields": ["标的", "周期", "数据截止日", "研究状态", "风格预判"],
        "prompt": """
生成任务锁定表格，包含：
- 标的（公司名、代码、交易所）
- 周期（短线/中线/长线）
- 数据截止日（YYYY-MM-DD）
- 研究状态（首次覆盖/持续跟踪）
- 风格预判（配置型/交易型/左侧博弈型）
"""
    },
    {
        "step": "Step 1",
        "name": "宏观与周期定位",
        "min_lines": 50,
        "mcp_searches": [
            "{行业} 行业趋势 2026 市场规模",
            "{概念} 政策 2026 国家支持"
        ],
        "prompt": """
必须包含：
1a. 经济周期映射（经济阶段、公司所处周期、政策阶段）
1b. 政策与环境扫描（核心政策驱动、外部环境）
1c. 核心矛盾提炼（一句话判断：XX vs YY）

使用MCP搜索结果中的行业趋势数据。
"""
    },
    {
        "step": "Step 2",
        "name": "产业链深度拆解与趋势验证",
        "min_lines": 100,
        "mcp_searches": [
            "{股票名称} 竞争对手 市场份额",
            "{行业} 产业链 上下游"
        ],
        "prompt": """
必须包含：
2a. 题材来源判断（消息面筛选法 or 炒作脉络延伸法）
2b. 产业链图谱（用代码块呈现，格式：上游→中游→下游）
2c. 业务线拆解与趋势三要素（表格+打分：供需格局、价格锚点、海外验证）
2d. 价值链利润分布分析（表格：上游/中游/下游的毛利率、净利率）

使用MCP搜索结果中的竞争对手和产业链数据。
"""
    },
    {
        "step": "Step 3",
        "name": "公司筛选与质量评分",
        "min_lines": 50,
        "prompt": """
必须包含：
3a. 正面筛选清单（6项标准：市值门槛、行业地位、业务相关度、业绩弹性、位置性价比、管理层信号）
3b. 不碰清单（负面排查：市值<50亿、蹭概念、分销商、看不到业绩落地、主业拖后腿）
3c. 质量评分（100分制，6个维度：基本面质量30分、产业匹配度20分、业绩弹性20分、估值与位置15分、资金与交易结构10分、治理与风险5分）

使用akshare数据中的财务数据和股东结构。
"""
    },
    {
        "step": "Step 4",
        "name": "业绩弹性测算",
        "min_lines": 80,
        "prompt": """
必须包含：
4a. 分业务弹性树（用代码块呈现，格式：公司→业务A→业务B→当前估值→结论）
4b. 价格敏感度公式（至少3个公式，格式：关键变量每变动X单位 → 年利润影响Y亿）
4c. 情景分析（表格：悲观/基准/乐观，包含触发条件、营收区间、净利区间、对应PE）

使用akshare数据中的主营业务构成和财务数据。
"""
    },
    {
        "step": "Step 5",
        "name": "风险分析与逻辑破坏条件",
        "min_lines": 40,
        "prompt": """
必须包含：
5a. 风险清单（表格：风险类型、具体场景、影响程度、发生概率）
    至少包含：行业周期、竞争格局、交付/产能、客户集中度、财务质量、治理/关联交易、技术替代
5b. 逻辑破坏条件（5个止损信号，每条需可量化或可观测）
    示例：价格跌回XX以下、新增大额减值计提、核心客户流失
"""
    },
    {
        "step": "Step 6",
        "name": "估值-赔率与买卖时机",
        "min_lines": 100,
        "mcp_searches": [
            "{股票名称} 券商研报 目标价 2026"
        ],
        "prompt": """
必须包含：
6a. 估值方法选择（成长型用PE/PEG、周期型用PB/EV-EBITDA、困境反转用PB+减值出清）
6a+. 资金面分析（表格：筹码分布、资金流向、关键判断）
6a++. 技术面分析（表格：价格位置、均线系统、成交量、技术指标、关键价格位）
6b. 三档目标价（表格：短期/中期/长期，包含时间窗口、目标价、估值依据、核心假设、触发条件、盈亏比）
6c. 盈亏比量化（当前位置：向下空间XX%、向上空间XX%、盈亏比X:X）

使用MCP搜索结果中的券商研报，使用akshare数据中的K线和资金流向。
"""
    },
    {
        "step": "Step 7",
        "name": "对标与对比分析",
        "min_lines": 60,
        "prompt": """
必须包含：
7a. 案例类比法（表格：本票 vs 对标公司A vs 对标公司B，对比维度：产业周期、业绩趋势、估值水平、确定性、弹性来源、框架匹配度、适合风格）
7b. 增长引擎切换分析（如果适用，表格：原引擎 vs 新引擎，对比维度：驱动力来源、营收占比、毛利率、确定性、竞争格局）

使用MCP搜索结果中的竞争对手数据。
"""
    },
    {
        "step": "Step 8",
        "name": "跟踪计划与综合结论",
        "min_lines": 50,
        "prompt": """
必须包含：
8a. 分层跟踪锚点（表格：高频周度、季度、事件驱动，包含跟踪内容和数据来源）
8b. 执行清单（短线：触发条件、失效条件；中线：3财务+3事件）
8c. 综合结论（强制格式）：
    - 一句话判断：当前更像___（趋势/修复/博弈）
    - 风险等级：低/中/高/极高
    - 风格标签：配置型/交易型/左侧博弈型
    - 操作建议：核心配置/择时参与/仅观察
8d. 五维综合评分（100分制）：
    - 基本面（40%）：产业逻辑15% + 业绩弹性15% + 财务质量10%
    - 资金面（20%）：筹码分布8% + 主力资金7% + 融资融券5%
    - 技术面（15%）：位置判断6% + 趋势判断5% + 量价配合4%
    - 情绪面（15%）：市场热度6% + 拥挤度5% + 预期差4%
    - 事件催化（10%）：政策催化4% + 业绩催化3% + 事件催化3%
"""
    }
]

def load_data(data_file):
    """加载akshare数据"""
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_basic_info(stock_code, data):
    """2.1 基础信息写入"""
    print("  ✅ 2.1 基础信息写入中...")

    # 提取基础信息
    stock_name = data.get('stock_name', '未知')
    industry = data.get('industry', '未知')

    # 创建MD文件
    md_content = f"""# {stock_name}（{stock_code}）深度研究

> 数据截止日：{datetime.now().strftime('%Y-%m-%d')}
> 研究状态：首次覆盖
> 分析框架：个股分析框架V3

---

## 基本信息

| 项目 | 内容 |
|------|------|
| 股票名称 | {stock_name} |
| 股票代码 | {stock_code} |
| 所属行业 | {industry} |
| 主营业务 | {data.get('business', '未知')} |

## 财务摘要（最近一年）

| 指标 | 数值 |
|------|------|
| 营业收入 | {data.get('revenue', '未知')} |
| 净利润 | {data.get('profit', '未知')} |
| 毛利率 | {data.get('gross_margin', '未知')} |
| ROE | {data.get('roe', '未知')} |

## 股东结构

{data.get('shareholders_table', '暂无数据')}

## 主营业务构成

{data.get('business_table', '暂无数据')}

---

"""

    output_file = f"output/个股研究-{stock_name}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"  ✅ 2.1 基础信息写入完成（约50行）")
    return output_file

def trigger_mcp_searches(stock_name, industry):
    """2.2 触发MCP搜索"""
    print("  ✅ 2.2 触发MCP搜索中...")

    # 这里应该调用MCP搜索
    # 由于是Python脚本，实际的MCP搜索需要在AI执行时完成
    # 这里只是记录需要搜索的内容

    searches = [
        f"{industry} 行业趋势 2026 市场规模",
        f"{stock_name} 竞争对手 市场份额",
        f"{stock_name} 券商研报 目标价 2026",
        f"{stock_name} 最新新闻 2026"
    ]

    print(f"  ✅ 2.2 需要执行{len(searches)}次MCP搜索")
    print("  ⚠️  MCP搜索需要AI执行，请在AI分析时完成")

    return searches

def analyze_stock(stock_code, data_file):
    """
    Phase 2主函数

    ⚠️ 重要：这个函数只是框架，实际的Step 0-8分析需要AI执行

    AI执行时必须：
    1. 读取data_file获取akshare数据
    2. 执行MCP搜索获取行业、竞争对手、研报数据
    3. 严格按照ANALYSIS_STEPS配置，逐步完成Step 0-8
    4. 每完成一个Step，输出：✅ Step X完成（XX行）
    5. 最终生成540-740行的完整MD报告
    """

    # 加载数据
    data = load_data(data_file)
    stock_name = data.get('stock_name', '未知')
    industry = data.get('industry', '未知')

    # 2.1 基础信息写入
    md_file = write_basic_info(stock_code, data)

    # 2.2 触发MCP搜索
    searches = trigger_mcp_searches(stock_name, industry)

    # 2.3 AI逐步分析Step 0-8
    print("\n  ⚠️  Phase 2.3 需要AI执行")
    print("  ⚠️  AI必须严格按照以下顺序完成：\n")

    for step_config in ANALYSIS_STEPS:
        print(f"  □ {step_config['step']}: {step_config['name']}（{step_config['min_lines']}行）")
        if 'mcp_searches' in step_config:
            print(f"     需要MCP搜索：{len(step_config['mcp_searches'])}次")

    print(f"\n  ✅ 总计：540行（最低要求）")
    print(f"\n  📝 输出文件：{md_file}")
    print("  ⚠️  请AI继续完成Step 0-8的分析")

    return md_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python phase2_analyzer_v2.py <股票代码> <data_file>")
        sys.exit(1)

    stock_code = sys.argv[1]
    data_file = sys.argv[2]

    md_file = analyze_stock(stock_code, data_file)
    print(f"\n✅ Phase 2完成：{md_file}")
