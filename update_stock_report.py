#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个股研究报告增量更新工具
========================

功能：
1. 检查是否需要更新（对比旧数据vs新数据）
2. 如果需要更新，执行增量更新（K线数据 + Hero行情 + 第9章技术指标）

用法：
    python update_stock_report.py 000066
    python update_stock_report.py 000066 --html output/个股研究-中国长城.html
    python update_stock_report.py 000066 --force  # 强制更新

输出：
- 更新检查报告（是否需要更新 + 变化点列表）
- 如果需要更新：生成新的HTML（带日期后缀）+ 覆盖无日期版本
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    print("[X] 未安装依赖，请先 pip install akshare pandas", file=sys.stderr)
    sys.exit(1)

try:
    from technical_indicators import calculate_all_indicators, get_latest_signals, format_indicators_for_json
except ImportError:
    print("[!] 未找到 technical_indicators.py，技术指标更新将被跳过", file=sys.stderr)
    calculate_all_indicators = None
    get_latest_signals = None
    format_indicators_for_json = None


# ============================================================
#  数据提取工具
# ============================================================

def extract_kline_from_html(html_path: str) -> List[List]:
    """从HTML中提取K线数据（rawData数组）"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找 const rawData = [...]; 部分（非贪婪，匹配到第一个 ]; 后跟换行或结束）
    # 使用更精确的正则：先找到 const rawData = [，然后逐行匹配直到 ];
    start_marker = 'const rawData = ['
    start_idx = content.find(start_marker)
    if start_idx == -1:
        return []

    # 从 [ 之后开始找匹配的 ];
    bracket_start = start_idx + len(start_marker) - 1  # 指向 [
    depth = 0
    end_idx = -1
    for i in range(bracket_start, len(content)):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            depth -= 1
            if depth == 0:
                # 检查后面是否跟分号
                j = i + 1
                while j < len(content) and content[j] in ' \t\n\r':
                    j += 1
                if j < len(content) and content[j] == ';':
                    end_idx = i
                    break

    if end_idx == -1:
        return []

    raw_data_str = content[bracket_start+1:end_idx]

    # 解析每一行数据
    kline_data = []
    for line in raw_data_str.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        # 移除末尾的逗号
        if line.endswith(','):
            line = line[:-1]
        # 解析数组 ["2025-11-25",15.08,15.05,15.03,15.22,451792]
        try:
            data = json.loads(line)
            if isinstance(data, list) and len(data) >= 6:
                kline_data.append(data)
        except:
            continue

    return kline_data


def extract_hero_data_from_html(html_path: str) -> Dict:
    """从HTML中提取Hero区域的关键数据"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    hero_data = {}

    # 提取价格
    price_match = re.search(r'<span class="hero-price">([0-9.]+)</span>', content)
    if price_match:
        hero_data['price'] = float(price_match.group(1))

    # 提取涨跌幅
    change_match = re.search(r'<span class="hero-change">([^<]+)</span>', content)
    if change_match:
        hero_data['change'] = change_match.group(1)

    return hero_data


def detect_market(code: str) -> str:
    """检测市场并返回带前缀的代码"""
    code = code.strip().lstrip("sh").lstrip("sz").lstrip("bj")
    if not code.isdigit() or len(code) != 6:
        raise ValueError(f"非法的 A 股代码：{code}")
    if code.startswith(("60", "68", "11", "12", "5")):
        return f"sh{code}"
    if code.startswith(("00", "30", "20", "15", "16", "18")):
        return f"sz{code}"
    if code.startswith(("4", "8", "92")):
        return f"bj{code}"
    return f"sh{code}"


def fetch_latest_kline(code: str, days: int = 120, max_retries: int = 3) -> Tuple[List[List], pd.DataFrame]:
    """
    获取最新的K线数据（带重试机制）

    Returns:
        (kline_data, df): K线数据列表 和 原始DataFrame（用于技术指标计算）
    """
    import time
    from datetime import date, timedelta

    prefixed = detect_market(code)
    today = date.today()
    start_date = (today - timedelta(days=int(days * 1.5))).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    for attempt in range(max_retries):
        try:
            print(f"   尝试获取数据... (第{attempt+1}/{max_retries}次)")
            df = ak.stock_zh_a_daily(symbol=prefixed, start_date=start_date, end_date=end_date, adjust="qfq")

            if df is None or df.empty:
                if attempt < max_retries - 1:
                    print(f"   数据为空，{2}秒后重试...")
                    time.sleep(2)
                    continue
                return [], pd.DataFrame()

            # 取最近N天
            df = df.tail(days)

            # akshare 列名已变更为英文: date, open, high, low, close, volume
            # 转换为rawData格式: ["YYYY-MM-DD", 开, 收, 低, 高, 成交量]
            # 注意: akshare order = open/high/low/close, rawData order = open/close/low/high
            kline_data = []
            for _, row in df.iterrows():
                # 使用 akshare 原生列序：[date, open, high, low, close, volume]
                kline_data.append([
                    str(row['date'])[:10],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['volume'])
                ])

            return kline_data, df

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   [!] 获取失败: {e}")
                print(f"   {2}秒后重试...")
                time.sleep(2)
            else:
                print(f"   [X] 获取K线数据失败（已重试{max_retries}次）: {e}")
                return [], pd.DataFrame()

    return [], pd.DataFrame()


# ============================================================
#  变化检测
# ============================================================

def compare_kline_data(old_kline: List[List], new_kline: List[List]) -> Dict:
    """对比K线数据变化"""
    changes = {
        'has_change': False,
        'new_days': 0,
        'last_old_date': None,
        'last_new_date': None,
        'details': []
    }

    if not old_kline:
        changes['has_change'] = True
        changes['new_days'] = len(new_kline)
        changes['details'].append(f"旧数据为空，新数据有{len(new_kline)}条")
        return changes

    if not new_kline:
        changes['details'].append("新数据为空")
        return changes

    # 获取最后交易日
    old_last_date = old_kline[-1][0]
    new_last_date = new_kline[-1][0]

    changes['last_old_date'] = old_last_date
    changes['last_new_date'] = new_last_date

    # 检查是否有新交易日
    if new_last_date > old_last_date:
        changes['has_change'] = True

        # 计算新增天数
        old_dates = set(row[0] for row in old_kline)
        new_dates = set(row[0] for row in new_kline)
        added_dates = new_dates - old_dates
        changes['new_days'] = len(added_dates)

        changes['details'].append(f"K线数据更新：{old_last_date} → {new_last_date}，新增{changes['new_days']}个交易日")
    else:
        changes['details'].append(f"K线数据无变化（最新：{new_last_date}）")

    return changes


def check_updates(code: str, html_path: str) -> Dict:
    """检查是否需要更新"""
    print(f"\n📊 检查 {code} 的更新情况...")
    print(f"   旧HTML: {html_path}")

    result = {
        'need_update': False,
        'changes': [],
        'old_kline': [],
        'new_kline': [],
        'new_kline_df': pd.DataFrame(),
        'kline_changes': {}
    }

    # 1. 提取旧K线数据
    print("\n[1/2] 提取旧K线数据...")
    old_kline = extract_kline_from_html(html_path)
    result['old_kline'] = old_kline

    if old_kline:
        print(f"   ✅ 旧K线数据：{len(old_kline)}条，最新日期 {old_kline[-1][0]}")
    else:
        print(f"   ⚠️  未找到旧K线数据")

    # 2. 获取新K线数据
    print("\n[2/2] 获取最新K线数据...")
    new_kline, new_kline_df = fetch_latest_kline(code, days=120)
    result['new_kline'] = new_kline
    result['new_kline_df'] = new_kline_df

    if new_kline:
        print(f"   ✅ 新K线数据：{len(new_kline)}条，最新日期 {new_kline[-1][0]}")
    else:
        print(f"   ❌ 获取新K线数据失败")
        return result

    # 3. 对比变化
    print("\n[3/3] 对比数据变化...")
    kline_changes = compare_kline_data(old_kline, new_kline)
    result['kline_changes'] = kline_changes

    if kline_changes['has_change']:
        result['need_update'] = True
        result['changes'].extend(kline_changes['details'])

    # 输出检查结果
    print("\n" + "="*60)
    print("📋 更新检查报告")
    print("="*60)

    if result['need_update']:
        print("✅ 需要更新")
        print("\n变化点：")
        for i, change in enumerate(result['changes'], 1):
            print(f"  {i}. {change}")
    else:
        print("⏸️  无需更新（数据无变化）")
        if kline_changes['details']:
            print("\n详情：")
            for detail in kline_changes['details']:
                print(f"  • {detail}")

    print("="*60)

    return result


# ============================================================
#  HTML增量更新
# ============================================================

def update_html_kline(html_path: str, new_kline: List[List], output_path: str) -> bool:
    """更新HTML中的K线数据"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 构建新的rawData数组
        kline_lines = []
        for row in new_kline:
            # ["2025-11-25",15.08,15.05,15.03,15.22,451792]
            line = f'["{row[0]}",{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}]'
            kline_lines.append(line)

        new_raw_data = "const rawData = [\n" + ",\n".join(kline_lines) + "\n];"

        # 替换rawData部分
        pattern = r'const rawData = \[.*?\];'
        new_content = re.sub(pattern, new_raw_data, content, flags=re.DOTALL)

        # 写入新文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"[X] 更新HTML失败: {e}")
        return False


def update_html_hero(html_path: str, code: str, output_path: str) -> bool:
    """更新HTML中的Hero区域数据（价格、涨跌幅等）"""
    try:
        # 获取最新行情
        prefixed = detect_market(code)

        # 获取实时行情（使用东财实时行情接口，仅取单只股票）
        try:
            df = ak.stock_zh_a_spot()
            stock_data = df[df['代码'] == prefixed]
            if stock_data.empty:
                # 尝试不带前缀匹配
                stock_data = df[df['代码'].astype(str).str.contains(code)]
            if stock_data.empty:
                print(f"[!] 未找到 {code} 的实时行情")
                return False
            latest_price = float(stock_data.iloc[0]['最新价'])
            change_pct = float(stock_data.iloc[0]['涨跌幅'])
        except Exception as e:
            print(f"[!] 获取实时行情失败: {e}，使用日K线最后收盘价")
            # Fallback: 使用最新K线的收盘价
            df_kline = ak.stock_zh_a_daily(symbol=prefixed, start_date=(date.today()-timedelta(days=7)).strftime("%Y%m%d"), end_date=date.today().strftime("%Y%m%d"), adjust="qfq")
            if df_kline is not None and not df_kline.empty:
                latest_price = float(df_kline.iloc[-1]['close'])
                prev_close = float(df_kline.iloc[-2]['close']) if len(df_kline) > 1 else latest_price
                change_pct = (latest_price - prev_close) / prev_close * 100
            else:
                return False

        # 读取HTML
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 更新价格
        content = re.sub(
            r'<span class="hero-price">[0-9.]+</span>',
            f'<span class="hero-price">{latest_price}</span>',
            content
        )

        # 更新涨跌幅
        if change_pct >= 0:
            change_text = f'+{change_pct:.2f}%'
        else:
            change_text = f'{change_pct:.2f}%'

        content = re.sub(
            r'<span class="hero-change">[^<]+</span>',
            f'<span class="hero-change">{change_text}</span>',
            content
        )

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"   ✅ Hero数据已更新：价格 {latest_price}，涨跌幅 {change_text}")
        return True

    except Exception as e:
        print(f"[!] 更新Hero数据失败: {e}")
        return False


def update_html_technical(html_path: str, new_kline_df: pd.DataFrame, output_path: str) -> bool:
    """更新HTML中的第9章技术指标数据"""
    if calculate_all_indicators is None:
        print(f"[!] 技术指标模块未加载，跳过技术指标更新")
        return False

    try:
        # 标准化列名
        df = new_kline_df.copy()
        column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)

        # 计算技术指标
        df_with_indicators = calculate_all_indicators(df)
        technical_data = format_indicators_for_json(df_with_indicators, max_rows=120)
        technical_signals = get_latest_signals(df_with_indicators)

        # 读取HTML
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 构建新的 technicalData 数组
        technical_lines = []
        for record in technical_data:
            technical_lines.append(json.dumps(record, ensure_ascii=False))

        new_technical_data = "const technicalData = [\n" + ",\n".join(technical_lines) + "\n];"

        # 替换 technicalData 部分
        pattern = r'const technicalData = \[.*?\];'
        if re.search(pattern, content, re.DOTALL):
            new_content = re.sub(pattern, new_technical_data, content, flags=re.DOTALL)

            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"   ✅ 技术指标已更新：{len(technical_data)} 条记录")
            return True
        else:
            print(f"   [!] HTML中未找到 technicalData，跳过技术指标更新")
            return False

    except Exception as e:
        print(f"[!] 更新技术指标失败: {e}")
        return False


def perform_update(code: str, html_path: str, check_result: Dict) -> bool:
    """执行增量更新"""
    print("\n" + "="*60)
    print("🔄 开始增量更新")
    print("="*60)

    # 生成输出文件名
    today = datetime.now().strftime('%Y%m%d')
    base_name = os.path.basename(html_path)
    name_without_ext = os.path.splitext(base_name)[0]

    # 带日期的版本
    dated_output = os.path.join(
        os.path.dirname(html_path),
        f"{name_without_ext}_{today}.html"
    )

    # 无日期的版本（覆盖）
    latest_output = html_path

    print(f"\n[1/4] 更新K线数据...")

    # 先更新到带日期的版本
    success = update_html_kline(html_path, check_result['new_kline'], dated_output)

    if not success:
        print("[X] K线数据更新失败")
        return False

    print(f"   ✅ K线数据已更新：{len(check_result['new_kline'])}条")

    print(f"\n[2/4] 更新Hero区域数据...")
    update_html_hero(dated_output, code, dated_output)

    print(f"\n[3/4] 更新第9章技术指标...")
    if not check_result['new_kline_df'].empty:
        update_html_technical(dated_output, check_result['new_kline_df'], dated_output)
    else:
        print(f"   [!] K线DataFrame为空，跳过技术指标更新")

    print(f"\n[4/4] 覆盖最新版本...")

    # 复制到无日期版本
    with open(dated_output, 'r', encoding='utf-8') as f:
        content = f.read()

    with open(latest_output, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ 已覆盖：{latest_output}")

    print("\n" + "="*60)
    print("✅ 更新完成")
    print("="*60)
    print(f"\n📄 输出文件：")
    print(f"   • 带日期版本：{dated_output}")
    print(f"   • 最新版本：{latest_output}")

    # 输出文件大小
    size_kb = os.path.getsize(dated_output) / 1024
    print(f"\n📊 文件大小：{size_kb:.1f} KB")

    return True


# ============================================================
#  主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="个股研究报告增量更新工具")
    parser.add_argument("code", help="6位股票代码（如 000066）")
    parser.add_argument("--html", help="旧HTML文件路径（默认自动查找）")
    parser.add_argument("--force", action="store_true", help="强制更新（跳过检查）")

    args = parser.parse_args()

    code = args.code.strip()

    # 查找HTML文件
    if args.html:
        html_path = args.html
    else:
        # 同时查找 output/ 和 examples/ 目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs = [
            os.path.join(base_dir, "output"),
            os.path.join(base_dir, "examples"),
        ]

        # 收集所有HTML文件（排除.bak和带日期的历史版本）
        all_html_files = []
        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue
            for f in os.listdir(search_dir):
                if f.endswith('.html') and not f.endswith('.bak') and not f.endswith('.backup'):
                    # 排除带日期后缀的历史版本（如 _20260528.html）
                    if not re.search(r'_\d{8}\.html$', f):
                        all_html_files.append(os.path.join(search_dir, f))

        if not all_html_files:
            print(f"[X] 未找到HTML文件，请使用 --html 参数指定", file=sys.stderr)
            sys.exit(1)

        # 按文件内容匹配股票代码：查找 HTML 中包含该代码的 <title> 或 stock-code
        matched_files = []
        for fpath in all_html_files:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read(4096)  # 只读头部，够匹配了
                # 匹配 title 中的代码 或 stock-code 中的代码 或 文件名含代码
                fname = os.path.basename(fpath)
                if (code in content[:2000] and ('深度研报' in content[:2000] or 'stock-code' in content[:2000])) \
                   or code in fname:
                    matched_files.append(fpath)
            except Exception:
                continue

        if not matched_files:
            print(f"[X] 未找到包含 {code} 的HTML文件，请使用 --html 参数指定", file=sys.stderr)
            print(f"   已搜索目录：{search_dirs}")
            print(f"   找到的HTML文件：{all_html_files}")
            sys.exit(1)

        # 优先选 output/ 下的，其次 examples/
        output_files = [f for f in matched_files if 'output' in f]
        html_path = output_files[0] if output_files else matched_files[0]
        print(f"[i] 自动匹配HTML文件：{html_path}")

    if not os.path.exists(html_path):
        print(f"[X] HTML文件不存在：{html_path}", file=sys.stderr)
        sys.exit(1)

    # 检查更新
    check_result = check_updates(code, html_path)

    # 判断是否需要更新
    if args.force:
        print("\n⚠️  强制更新模式")
        perform_update(code, html_path, check_result)
    elif check_result['need_update']:
        perform_update(code, html_path, check_result)
    else:
        print("\n✅ 无需更新，退出")


if __name__ == "__main__":
    main()
