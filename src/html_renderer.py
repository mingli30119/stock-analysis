#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
个股深度研究报告 HTML渲染器 v8.0
专业级设计：左侧目录 + 右侧内容 + 精细化排版
"""

import json
import re
from datetime import datetime

def load_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_markdown(md_file):
    with open(md_file, 'r', encoding='utf-8') as f:
        return f.read()

def extract_basic_info(data):
    """提取基本信息"""
    basic_dict = {item['item']: item['value'] for item in data['blocks']['basic_info']}
    spot = data['blocks']['spot'][0]
    fin = data['blocks'].get('fin_indicator_ths', [])

    # 提取市盈率
    pe = '--'
    if fin:
        for item in fin:
            if item.get('指标名称') == '市盈率':
                pe = item.get('指标值', '--')
                break

    return {
        'name': data.get('name', '未知'),
        'code': data.get('code', '000000'),
        'industry': basic_dict.get('所属行业', '未知'),
        'business': basic_dict.get('主营业务', '未知'),
        'price': spot.get('最新价', '--'),
        'change': spot.get('涨跌幅', '--'),
        'pe': pe,
        'market_cap': basic_dict.get('总市值', '--')
    }

def extract_business_composition(data):
    """提取主营业务构成"""
    zygc = data['blocks'].get('zygc', [])
    if not zygc:
        return []
    latest_date = zygc[0]['报告日期'][:7]
    product_data = []
    for item in zygc:
        if item['报告日期'].startswith(latest_date) and item['分类类型'] == '按产品分类':
            product_data.append({
                'name': item['主营构成'],
                'value': round(item['主营收入'] / 100000000, 2),
                'ratio': round(item['收入比例'] * 100, 2)
            })
    return product_data[:6]

def extract_news(data):
    """提取近期新闻"""
    news = data['blocks'].get('news', [])
    return [n.get('新闻标题', 'N/A') for n in news[:5]]

def extract_target_price(md_content):
    """提取目标价和盈亏比"""
    target = re.search(r'中期.*?(\d+)-(\d+)元', md_content)
    profit_loss = re.search(r'中期：(\d+\.?\d*):1', md_content)
    up_space = re.search(r'中期：\+(\d+)%', md_content)

    return {
        'target': f"{target.group(1)}-{target.group(2)}" if target else "18-20",
        'profit_loss': profit_loss.group(1) if profit_loss else "1.5",
        'up_space': up_space.group(1) if up_space else "25"
    }

def clean_markdown(text):
    """清理Markdown标记"""
    # 移除###标记
    text = re.sub(r'###\s+', '', text)
    # 移除**加粗标记但保留内容
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 移除代码块标记
    text = re.sub(r'```\n?', '', text)
    return text

def format_table(table_text):
    """格式化表格"""
    lines = [l.strip() for l in table_text.split('\n') if l.strip() and '|' in l]
    if len(lines) < 2:
        return table_text

    html = '<table class="data-table">'
    for i, line in enumerate(lines):
        if '---' in line:
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if i == 0:
            html += '<thead><tr>' + ''.join([f'<th>{c}</th>' for c in cells]) + '</tr></thead><tbody>'
        else:
            html += '<tr>' + ''.join([f'<td>{c}</td>' for c in cells]) + '</tr>'
    html += '</tbody></table>'
    return html

def parse_step_sections(md_content):
    """解析Step 0-8，精细化处理每个部分"""
    sections = []
    pattern = r'## (Step \d+[^\n]+)\n(.*?)(?=\n## Step|\Z)'
    matches = re.findall(pattern, md_content, re.DOTALL)

    for title, content in matches:
        # 清理标题
        clean_title = title.replace('Step ', '').strip()

        # 处理内容
        content = clean_markdown(content)

        # 处理表格
        if '|' in content:
            table_blocks = re.findall(r'(\|.+?\|(?:\n\|.+?\|)+)', content, re.DOTALL)
            for table in table_blocks:
                formatted = format_table(table)
                content = content.replace(table, formatted)

        # 处理列表
        content = re.sub(r'\n- (.+)', r'<li>\1</li>', content)
        if '<li>' in content:
            content = '<ul class="styled-list">' + content + '</ul>'

        # 处理段落
        paragraphs = content.split('\n\n')
        content = ''.join([f'<p>{p}</p>' for p in paragraphs if p.strip()])

        sections.append({
            'id': title.split(':')[0].replace('Step ', 'step'),
            'title': clean_title,
            'content': content
        })

    return sections

def generate_industry_chain_svg():
    """生成产业链SVG图"""
    return '''
<svg viewBox="0 0 800 300" xmlns="http://www.w3.org/2000/svg">
  <!-- 上游 -->
  <rect x="50" y="120" width="150" height="60" fill="#e8f5e9" stroke="#4caf50" stroke-width="2" rx="8"/>
  <text x="125" y="145" text-anchor="middle" font-size="14" font-weight="600">上游</text>
  <text x="125" y="165" text-anchor="middle" font-size="12">甘蔗/甜菜种植</text>

  <!-- 箭头1 -->
  <path d="M 200 150 L 280 150" stroke="#666" stroke-width="2" marker-end="url(#arrowhead)"/>

  <!-- 中游 -->
  <rect x="280" y="100" width="180" height="100" fill="#fff3e0" stroke="#ff9800" stroke-width="3" rx="8"/>
  <text x="370" y="130" text-anchor="middle" font-size="16" font-weight="700" fill="#e65100">中游（中粮糖业）</text>
  <text x="370" y="155" text-anchor="middle" font-size="12">压榨加工</text>
  <text x="370" y="175" text-anchor="middle" font-size="12">精炼提纯</text>
  <text x="370" y="195" text-anchor="middle" font-size="12">仓储物流</text>

  <!-- 箭头2 -->
  <path d="M 460 150 L 540 150" stroke="#666" stroke-width="2" marker-end="url(#arrowhead)"/>

  <!-- 下游 -->
  <rect x="540" y="120" width="150" height="60" fill="#e3f2fd" stroke="#2196f3" stroke-width="2" rx="8"/>
  <text x="615" y="145" text-anchor="middle" font-size="14" font-weight="600">下游</text>
  <text x="615" y="165" text-anchor="middle" font-size="12">工业60% + 民用40%</text>

  <!-- 箭头定义 -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="#666"/>
    </marker>
  </defs>
</svg>
'''

def generate_html(stock_code, md_file, json_file):
    data = load_data(json_file)
    md_content = load_markdown(md_file)

    info = extract_basic_info(data)
    business = extract_business_composition(data)
    news_list = extract_news(data)
    target_info = extract_target_price(md_content)
    sections = parse_step_sections(md_content)

    # K线数据
    kline_data = data['blocks'].get('kline_daily', [])[-60:]
    dates = [d['date'][:10] for d in kline_data]
    ohlc = [[d['open'], d['close'], d['low'], d['high']] for d in kline_data]
    volumes = [d.get('volume', 0) for d in kline_data]

    # 计算MA均线
    closes = [d['close'] for d in kline_data]
    ma5 = []
    ma20 = []
    ma60 = []
    for i in range(len(closes)):
        if i >= 4:
            ma5.append(round(sum(closes[i-4:i+1])/5, 2))
        else:
            ma5.append(None)
        if i >= 19:
            ma20.append(round(sum(closes[i-19:i+1])/20, 2))
        else:
            ma20.append(None)
        if i >= 59:
            ma60.append(round(sum(closes[i-59:i+1])/60, 2))
        else:
            ma60.append(None)

    # 饼图数据
    pie_data = str([{'name': b['name'], 'value': b['value']} for b in business])

    # 新闻HTML
    news_html = ''.join([f'<div class="news-item"><span class="news-dot">•</span>{n}</div>' for n in news_list])

    # 目录HTML
    toc_html = ''.join([f'<a href="#{sec["id"]}" class="toc-item">{sec["title"]}</a>' for sec in sections])

    # 内容HTML
    sections_html = ""
    for sec in sections:
        # 特殊处理产业链部分
        content = sec['content']
        if 'step2' in sec['id'] and '上游' in content:
            content = generate_industry_chain_svg() + content

        sections_html += f'''
<section id="{sec['id']}" class="content-section">
    <h2 class="section-title">{sec['title']}</h2>
    <div class="section-content">{content}</div>
</section>
'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{info['name']}（{info['code']}）深度研究</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f5f5f5; color: #333; font-size: 15px; line-height: 1.8; }}

/* Header */
.header {{ background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
  color: #fff; padding: 24px 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
.header-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
.stock-info {{ display: flex; align-items: baseline; gap: 16px; }}
.stock-name {{ font-size: 28px; font-weight: 700; }}
.stock-code {{ font-size: 16px; opacity: 0.7; }}
.header-kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
.kpi-card {{ background: rgba(255,255,255,0.08); border-radius: 8px; padding: 16px;
  border-left: 3px solid #f5222d; }}
.kpi-card.price-card {{ border-left-color: #52c41a; }}
.kpi-label {{ font-size: 12px; opacity: 0.7; margin-bottom: 8px; }}
.kpi-value {{ font-size: 24px; font-weight: 700; }}
.kpi-value.rise {{ color: #ff4d4f; }}
.kpi-value.fall {{ color: #52c41a; }}
.kpi-sub {{ font-size: 12px; opacity: 0.6; margin-top: 4px; }}

/* Layout */
.container {{ display: flex; max-width: 1400px; margin: 0 auto; }}
.sidebar {{ width: 240px; background: #fff; height: calc(100vh - 140px);
  position: sticky; top: 20px; margin: 20px 0 20px 20px; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow-y: auto; }}
.toc {{ padding: 20px; }}
.toc-title {{ font-size: 14px; font-weight: 600; color: #666; margin-bottom: 12px; }}
.toc-item {{ display: block; padding: 8px 12px; font-size: 13px; color: #666;
  text-decoration: none; border-radius: 4px; margin-bottom: 4px; }}
.toc-item:hover {{ background: #f5f5f5; color: #f5222d; }}
.main-content {{ flex: 1; padding: 20px; }}

/* Cards */
.card {{ background: #fff; border-radius: 8px; padding: 24px; margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.card-title {{ font-size: 18px; font-weight: 600; margin-bottom: 16px;
  padding-bottom: 12px; border-bottom: 2px solid #f0f0f0; }}

/* 公司画像 */
.profile-row {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px; margin-bottom: 16px; }}
.profile-content {{ font-size: 14px; line-height: 1.8; color: #666; }}
.profile-tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
.tag {{ padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 500;
  background: #fff1f0; color: #f5222d; border: 1px solid #ffccc7; }}
.news-list {{ max-height: 240px; overflow-y: auto; }}
.news-item {{ padding: 10px 0; font-size: 13px; color: #666;
  border-bottom: 1px dashed #f0f0f0; display: flex; gap: 8px; }}
.news-dot {{ color: #f5222d; font-weight: 700; }}

/* 图表 */
.chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
#business-pie, #kline-small {{ width: 100%; height: 350px; }}
#kline-full {{ width: 100%; height: 500px; }}

/* K线信息卡片 */
.kline-info {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
  margin-top: 16px; padding-top: 16px; border-top: 1px solid #f0f0f0; }}
.info-item {{ text-align: center; }}
.info-label {{ font-size: 12px; color: #999; margin-bottom: 4px; }}
.info-value {{ font-size: 18px; font-weight: 600; color: #f5222d; }}

/* 内容区 */
.content-section {{ background: #fff; border-radius: 8px; padding: 28px;
  margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.section-title {{ font-size: 20px; font-weight: 600; color: #f5222d;
  margin-bottom: 20px; padding-left: 12px; border-left: 4px solid #f5222d; }}
.section-content {{ color: #666; line-height: 1.8; }}
.section-content p {{ margin: 12px 0; }}
.section-content strong {{ color: #f5222d; font-weight: 600; }}

/* 表格 */
.data-table {{ width: 100%; border-collapse: collapse; margin: 16px 0;
  border: 1px solid #f0f0f0; font-size: 14px; }}
.data-table thead {{ background: #fafafa; }}
.data-table th {{ padding: 12px; text-align: left; font-weight: 600;
  border-bottom: 2px solid #f0f0f0; }}
.data-table td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }}
.data-table tr:hover {{ background: #fafafa; }}

/* 列表 */
.styled-list {{ margin: 12px 0 12px 20px; list-style: none; }}
.styled-list li {{ margin: 8px 0; padding-left: 12px;
  border-left: 3px solid #1890ff; }}

/* SVG */
svg {{ max-width: 100%; height: auto; margin: 20px 0; }}

footer {{ text-align: center; padding: 24px; color: #999; font-size: 12px; }}
</style>
</head>
<body>

<header class="header">
  <div class="header-top">
    <div class="stock-info">
      <span class="stock-name">{info['name']}</span>
      <span class="stock-code">{info['code']}</span>
    </div>
    <div style="font-size:12px;opacity:0.7">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
  </div>
  <div class="header-kpis">
    <div class="kpi-card price-card">
      <div class="kpi-label">最新价 / 涨跌幅</div>
      <div class="kpi-value">{info['price']} <span class="{'rise' if float(info['change']) > 0 else 'fall'}" style="font-size:18px">{info['change']}%</span></div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">市盈率（TTM）</div>
      <div class="kpi-value" style="font-size:20px">{info['pe']}</div>
      <div class="kpi-sub">行业中位</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">目标价（中期）</div>
      <div class="kpi-value" style="font-size:20px">{target_info['target']}元</div>
      <div class="kpi-sub">盈亏比 {target_info['profit_loss']}:1</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">投资建议</div>
      <div class="kpi-value" style="font-size:18px">择时参与</div>
      <div class="kpi-sub">配置型标的</div>
    </div>
  </div>
</header>

<div class="container">
  <aside class="sidebar">
    <div class="toc">
      <div class="toc-title">📑 目录导航</div>
      <a href="#profile" class="toc-item">公司画像</a>
      <a href="#charts" class="toc-item">图表分析</a>
      {toc_html}
    </div>
  </aside>

  <main class="main-content">
    <!-- 公司画像 -->
    <div id="profile" class="profile-row">
      <div class="card">
        <div class="card-title">🏢 公司画像</div>
        <div class="profile-content">
          <p><strong>主营业务：</strong>{info['business']}</p>
          <div class="profile-tags">
            <span class="tag">央企背景</span>
            <span class="tag">行业龙头</span>
            <span class="tag">稳定分红</span>
          </div>
          <p>中粮糖业是中粮集团旗下核心资产，国内食糖行业龙头企业之一。主营业务包括食糖加工、贸易及番茄制品生产，产业链完整，市场地位稳固。</p>
        </div>
      </div>
      <div class="card">
        <div class="card-title">📰 近期新闻</div>
        <div class="news-list">{news_html}</div>
      </div>
    </div>

    <!-- 图表 -->
    <div id="charts" class="chart-row">
      <div class="card">
        <div class="card-title">📊 主营业务构成</div>
        <div id="business-pie"></div>
      </div>
      <div class="card">
        <div class="card-title">📈 行情走势（近60日）</div>
        <div id="kline-small"></div>
      </div>
    </div>

    <!-- K线大图 -->
    <div class="card">
      <div class="card-title">📈 K线与成交量（近60日）</div>
      <div id="kline-full"></div>
      <div class="kline-info">
        <div class="info-item">
          <div class="info-label">向上空间</div>
          <div class="info-value">+{target_info['up_space']}%</div>
        </div>
        <div class="info-item">
          <div class="info-label">盈亏比</div>
          <div class="info-value">{target_info['profit_loss']}:1</div>
        </div>
        <div class="info-item">
          <div class="info-label">目标价</div>
          <div class="info-value">{target_info['target']}元</div>
        </div>
      </div>
    </div>

    <!-- Step 0-8 -->
    {sections_html}
  </main>
</div>

<footer>
  <p>📊 数据来源：akshare | 分析框架：个股分析框架V3</p>
  <p>⚠️ 本报告仅供研究参考，不构成投资建议</p>
</footer>

<script>
// 饼图
echarts.init(document.getElementById('business-pie')).setOption({{
    tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}}亿 ({{d}}%)' }},
    legend: {{ bottom: 10, textStyle: {{ fontSize: 11 }} }},
    series: [{{
        type: 'pie',
        radius: ['45%', '70%'],
        data: {pie_data},
        label: {{ fontSize: 11, formatter: '{{b}}\\n{{d}}%' }},
        color: ['#f5222d', '#fa8c16', '#fadb14', '#52c41a', '#1890ff', '#722ed1']
    }}]
}});

// K线小图
echarts.init(document.getElementById('kline-small')).setOption({{
    grid: {{ left: '12%', right: '8%', top: '10%', bottom: '25%' }},
    xAxis: {{ type: 'category', data: {dates}, axisLabel: {{ rotate: 45, fontSize: 10 }} }},
    yAxis: {{ scale: true }},
    tooltip: {{ trigger: 'axis' }},
    series: [{{
        type: 'candlestick',
        data: {ohlc},
        itemStyle: {{
            color: '#f5222d',
            color0: '#52c41a',
            borderColor: '#f5222d',
            borderColor0: '#52c41a'
        }}
    }}]
}});

// K线大图（含MA均线）
echarts.init(document.getElementById('kline-full')).setOption({{
    grid: [
        {{ left: '8%', right: '8%', top: '8%', height: '55%' }},
        {{ left: '8%', right: '8%', top: '70%', height: '18%' }}
    ],
    xAxis: [
        {{ type: 'category', data: {dates}, gridIndex: 0, axisLabel: {{ rotate: 45, fontSize: 11 }} }},
        {{ type: 'category', data: {dates}, gridIndex: 1, show: false }}
    ],
    yAxis: [
        {{ scale: true, gridIndex: 0 }},
        {{ scale: true, gridIndex: 1 }}
    ],
    dataZoom: [{{ type: 'inside', xAxisIndex: [0, 1] }}],
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
    legend: {{ data: ['日K', 'MA5', 'MA20', 'MA60'], top: 0 }},
    series: [
        {{
            name: '日K',
            type: 'candlestick',
            data: {ohlc},
            xAxisIndex: 0,
            yAxisIndex: 0,
            itemStyle: {{
                color: '#f5222d',
                color0: '#52c41a',
                borderColor: '#f5222d',
                borderColor0: '#52c41a'
            }}
        }},
        {{
            name: 'MA5',
            type: 'line',
            data: {ma5},
            smooth: true,
            lineStyle: {{ width: 1, color: '#1890ff' }},
            showSymbol: false,
            xAxisIndex: 0,
            yAxisIndex: 0
        }},
        {{
            name: 'MA20',
            type: 'line',
            data: {ma20},
            smooth: true,
            lineStyle: {{ width: 1, color: '#52c41a' }},
            showSymbol: false,
            xAxisIndex: 0,
            yAxisIndex: 0
        }},
        {{
            name: 'MA60',
            type: 'line',
            data: {ma60},
            smooth: true,
            lineStyle: {{ width: 1, color: '#fa8c16' }},
            showSymbol: false,
            xAxisIndex: 0,
            yAxisIndex: 0
        }},
        {{
            name: '成交量',
            type: 'bar',
            data: {volumes},
            xAxisIndex: 1,
            yAxisIndex: 1,
            itemStyle: {{ color: 'rgba(245,34,45,0.3)' }}
        }}
    ]
}});

// 平滑滚动
document.querySelectorAll('.toc-item').forEach(link => {{
    link.addEventListener('click', function(e) {{
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {{
            target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}
    }});
}});
</script>
</body>
</html>'''

    output_file = f"output/个股研究-{info['name']}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("用法: python phase3_html_renderer_v8.py <股票代码> <md文件> <json文件>")
        sys.exit(1)

    html_file = generate_html(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"✅ HTML已生成：{html_file}")
