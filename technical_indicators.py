"""
技术指标计算模块
================
基于 pandas 计算常用技术指标（MACD、KDJ、RSI、BOLL等）

依赖：pandas, numpy
"""

import pandas as pd
import numpy as np
from typing import Dict, List


def calculate_ma(df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
    """
    计算移动平均线

    Args:
        df: 包含 'close' 列的 DataFrame
        periods: 周期列表，默认 [5, 10, 20, 60]

    Returns:
        添加了 MA5, MA10, MA20, MA60 列的 DataFrame
    """
    df = df.copy()
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period, min_periods=1).mean()
    return df


def calculate_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """
    计算 MACD 指标

    Args:
        df: 包含 'close' 列的 DataFrame
        fast: 快线周期，默认 12
        slow: 慢线周期，默认 26
        signal: 信号线周期，默认 9

    Returns:
        添加了 DIF, DEA, MACD 列的 DataFrame
    """
    df = df.copy()

    # 计算 EMA
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

    # DIF = 快线 - 慢线
    df['DIF'] = ema_fast - ema_slow

    # DEA = DIF 的 EMA
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()

    # MACD = (DIF - DEA) * 2
    df['MACD'] = (df['DIF'] - df['DEA']) * 2

    return df


def calculate_kdj(df: pd.DataFrame, n=9, m1=3, m2=3) -> pd.DataFrame:
    """
    计算 KDJ 指标

    Args:
        df: 包含 'high', 'low', 'close' 列的 DataFrame
        n: RSV 周期，默认 9
        m1: K 值平滑周期，默认 3
        m2: D 值平滑周期，默认 3

    Returns:
        添加了 K, D, J 列的 DataFrame
    """
    df = df.copy()

    # 计算 RSV
    low_min = df['low'].rolling(window=n, min_periods=1).min()
    high_max = df['high'].rolling(window=n, min_periods=1).max()

    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)  # 初始值设为 50

    # 计算 K, D, J
    df['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    return df


def calculate_rsi(df: pd.DataFrame, periods: List[int] = [6, 12, 24]) -> pd.DataFrame:
    """
    计算 RSI 指标

    Args:
        df: 包含 'close' 列的 DataFrame
        periods: 周期列表，默认 [6, 12, 24]

    Returns:
        添加了 RSI6, RSI12, RSI24 列的 DataFrame
    """
    df = df.copy()

    # 计算价格变化
    delta = df['close'].diff()

    for period in periods:
        # 分离涨跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均涨跌幅
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        # 计算 RS 和 RSI
        rs = avg_gain / avg_loss.replace(0, 1e-10)  # 避免除零
        rsi = 100 - (100 / (1 + rs))

        df[f'RSI{period}'] = rsi

    return df


def calculate_boll(df: pd.DataFrame, period=20, std_multiplier=2) -> pd.DataFrame:
    """
    计算布林带指标

    Args:
        df: 包含 'close' 列的 DataFrame
        period: 周期，默认 20
        std_multiplier: 标准差倍数，默认 2

    Returns:
        添加了 BOLL_UPPER, BOLL_MID, BOLL_LOWER 列的 DataFrame
    """
    df = df.copy()

    # 中轨 = MA20
    df['BOLL_MID'] = df['close'].rolling(window=period, min_periods=1).mean()

    # 标准差
    std = df['close'].rolling(window=period, min_periods=1).std()

    # 上轨 = 中轨 + 2 * 标准差
    df['BOLL_UPPER'] = df['BOLL_MID'] + std_multiplier * std

    # 下轨 = 中轨 - 2 * 标准差
    df['BOLL_LOWER'] = df['BOLL_MID'] - std_multiplier * std

    return df


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有技术指标

    Args:
        df: 包含 'date', 'open', 'high', 'low', 'close', 'volume' 列的 DataFrame

    Returns:
        添加了所有技术指标列的 DataFrame
    """
    df = df.copy()

    # 确保数据按日期排序
    if 'date' in df.columns:
        df = df.sort_values('date').reset_index(drop=True)

    # 计算各项指标
    df = calculate_ma(df, periods=[5, 10, 20, 60])
    df = calculate_macd(df)
    df = calculate_kdj(df)
    df = calculate_rsi(df, periods=[6, 12, 24])
    df = calculate_boll(df)

    return df


def get_latest_signals(df: pd.DataFrame) -> Dict[str, any]:
    """
    获取最新的技术信号

    Args:
        df: 包含技术指标的 DataFrame

    Returns:
        包含最新技术信号的字典
    """
    if df.empty:
        return {}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    signals = {
        # MACD 信号
        'macd_golden_cross': latest['DIF'] > latest['DEA'] and prev['DIF'] <= prev['DEA'],
        'macd_dead_cross': latest['DIF'] < latest['DEA'] and prev['DIF'] >= prev['DEA'],
        'macd_histogram_positive': latest['MACD'] > 0,

        # KDJ 信号
        'kdj_golden_cross': latest['K'] > latest['D'] and prev['K'] <= prev['D'],
        'kdj_dead_cross': latest['K'] < latest['D'] and prev['K'] >= prev['D'],
        'kdj_overbought': latest['K'] > 80 and latest['D'] > 80,
        'kdj_oversold': latest['K'] < 20 and latest['D'] < 20,

        # RSI 信号
        'rsi6_overbought': latest['RSI6'] > 80,
        'rsi6_oversold': latest['RSI6'] < 20,
        'rsi12_overbought': latest['RSI12'] > 70,
        'rsi12_oversold': latest['RSI12'] < 30,

        # BOLL 信号
        'price_above_upper': latest['close'] > latest['BOLL_UPPER'],
        'price_below_lower': latest['close'] < latest['BOLL_LOWER'],
        'boll_squeeze': (latest['BOLL_UPPER'] - latest['BOLL_LOWER']) / latest['BOLL_MID'] < 0.1,

        # 均线信号
        'ma5_above_ma20': latest['MA5'] > latest['MA20'],
        'ma10_above_ma20': latest['MA10'] > latest['MA20'],
        'price_above_ma60': latest['close'] > latest['MA60'],
    }

    return signals


def format_indicators_for_json(df: pd.DataFrame, max_rows: int = 120) -> List[Dict]:
    """
    格式化技术指标数据为 JSON 格式

    Args:
        df: 包含技术指标的 DataFrame
        max_rows: 最大行数，默认 120（最近120个交易日）

    Returns:
        格式化后的记录列表
    """
    if df.empty:
        return []

    # 取最近 N 条记录
    df = df.tail(max_rows).copy()

    # 选择需要的列
    columns = ['date', 'open', 'high', 'low', 'close', 'volume',
               'MA5', 'MA10', 'MA20', 'MA60',
               'DIF', 'DEA', 'MACD',
               'K', 'D', 'J',
               'RSI6', 'RSI12', 'RSI24',
               'BOLL_UPPER', 'BOLL_MID', 'BOLL_LOWER']

    # 只保留存在的列
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    # 转换为记录列表
    records = df.to_dict('records')

    # 格式化数值（保留2位小数）和日期（转字符串）
    for record in records:
        for key, value in record.items():
            if key == 'date' and value is not None:
                # 转换 Timestamp/date 为字符串
                if hasattr(value, 'strftime'):
                    record[key] = value.strftime('%Y-%m-%d')
                else:
                    record[key] = str(value)[:10]
            elif isinstance(value, (int, float)) and not pd.isna(value):
                record[key] = round(value, 2)
            elif pd.isna(value):
                record[key] = None

    return records
