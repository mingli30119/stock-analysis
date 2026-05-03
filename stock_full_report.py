"""
个股数据采集（Phase 1）
=====================
基于 akshare 采集股票全维度数据，输出 JSON 供 Phase 2/3 使用。

- K 线主源：新浪日 K（stock_zh_a_daily）
- 全市场型接口（公告/业绩/龙虎榜/融资融券）自动按代码筛该股

用法
  python stock_full_report.py 000066
  python stock_full_report.py 002594 --max-kline-years 3

输出
  output/data_{代码}.json  — 供 Phase 3 AI手写HTML使用
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import akshare as ak
except ImportError:
    print("[X] 未安装 akshare，请先 pip install akshare --upgrade", file=sys.stderr)
    sys.exit(1)


# ============================================================
#  通用工具
# ============================================================

def detect_market(code: str) -> tuple[str, str]:
    """返回 (prefixed, market)，如 ('sh600519','sh') / ('sz000066','sz')。"""
    code = code.strip().lstrip("sh").lstrip("sz").lstrip("bj")
    if not code.isdigit() or len(code) != 6:
        raise ValueError(f"非法的 A 股代码：{code}")
    if code.startswith(("60", "68", "11", "12", "5")):
        return f"sh{code}", "sh"
    if code.startswith(("00", "30", "20", "15", "16", "18")):
        return f"sz{code}", "sz"
    if code.startswith(("4", "8", "92")):
        return f"bj{code}", "bj"
    return f"sh{code}", "sh"


def _last_trade_day(d: dt.date) -> dt.date:
    d = d - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def _filter_by_code(df: pd.DataFrame, code: str) -> pd.DataFrame:
    """容错地按代码列过滤行；找不到代码列则原样返回。"""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    candidate_cols = ["代码", "股票代码", "证券代码", "symbol", "code"]
    target_col = next((c for c in candidate_cols if c in df.columns), None)
    if target_col is None:
        return df
    series = df[target_col].astype(str).str.strip()
    mask = (series == code) | series.str.endswith(code)
    return df[mask].reset_index(drop=True)


def _safe_call(fn: Callable, *args, retries: int = 3, label: str = "", **kwargs) -> pd.DataFrame | None:
    """带重试的调用；任何失败返回 None，并打印一行简短日志。"""
    backoff = (0.5, 1.5, 3.0)
    for attempt in range(retries + 1):
        try:
            t0 = time.perf_counter()
            res = fn(*args, **kwargs)
            elapsed = time.perf_counter() - t0
            rows = len(res) if isinstance(res, pd.DataFrame) else "?"
            print(f"  ✓ {label:40s} {rows} 行 · {elapsed:.1f}s")
            return res
        except Exception as e:
            err_brief = f"{type(e).__name__}: {e}"[:90]
            transient = any(k in str(e) for k in ("Connection", "Timeout", "Disconnected", "Proxy"))
            if attempt < retries and transient:
                time.sleep(backoff[min(attempt, len(backoff) - 1)])
                continue
            print(f"  ✗ {label:40s} {err_brief}")
            return None


def _flatten_cell(v: Any) -> Any:
    """把单元格里偶发的 dict/list 类型压成易读字符串，避免前端显示 [object Object]。"""
    if isinstance(v, dict):
        for key in ("ind_name", "name", "value", "label"):
            if key in v and v[key] is not None:
                return v[key]
        return ", ".join(f"{k}={vv}" for k, vv in v.items() if vv is not None)[:80]
    if isinstance(v, list):
        return ", ".join(str(_flatten_cell(x)) for x in v[:5])[:120]
    return v


def _df_to_records(df: pd.DataFrame | None, max_rows: int | None = None) -> list[dict]:
    """DataFrame -> list[dict]，自动处理 NaN/Timestamp/dict/list，便于 JSON 序列化。"""
    if df is None or df.empty:
        return []
    out = df.head(max_rows) if max_rows else df
    out = out.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S").where(out[c].notna(), None)
    records = json.loads(out.to_json(orient="records", force_ascii=False, date_format="iso"))
    # 二次 flatten：to_json 会把 dict/list 原样导出，这里把它们变成字符串
    for row in records:
        for k, v in list(row.items()):
            if isinstance(v, (dict, list)):
                row[k] = _flatten_cell(v)
    return records


# ============================================================
#  数据收集
# ============================================================

@dataclass
class StockReportData:
    code: str
    prefixed: str
    market: str
    generated_at: str = field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ak_version: str = ""
    blocks: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def collect(code: str, max_kline_years: int = 3) -> StockReportData:
    prefixed, market = detect_market(code)
    data = StockReportData(code=code, prefixed=prefixed, market=market,
                           ak_version=getattr(ak, "__version__", "未知"))

    today = dt.date.today()
    last_trade = _last_trade_day(today + dt.timedelta(days=1))
    last_trade_prev = _last_trade_day(last_trade)
    today_s = today.strftime("%Y%m%d")
    last_trade_s = last_trade.strftime("%Y%m%d")
    last_trade_prev_s = last_trade_prev.strftime("%Y%m%d")
    kline_start = (today - dt.timedelta(days=int(365.25 * max_kline_years))).strftime("%Y%m%d")
    month_ago_s = (today - dt.timedelta(days=40)).strftime("%Y%m%d")

    print("[1/13] 基础信息")
    df = _safe_call(ak.stock_individual_basic_info_xq,
                    symbol=prefixed.upper(), label="雪球-公司概况")
    data.blocks["basic_info"] = _df_to_records(df)

    df = _safe_call(ak.stock_zh_a_spot, label="新浪-全市场快照")
    if df is not None:
        # spot 表里 代码 列是 sh600519/sz000066 这种带前缀的形式
        df_self = df[df["代码"].astype(str) == prefixed]
        if df_self.empty:
            df_self = df[df["代码"].astype(str).str.endswith(code)]
        data.blocks["spot"] = _df_to_records(df_self)
    else:
        data.blocks["spot"] = []

    df = _safe_call(ak.stock_zh_a_gbjg_em,
                    symbol=f"{code}.{market.upper()}", label="股本结构变动")
    data.blocks["share_structure"] = _df_to_records(df)

    print("[2/13] 主营业务构成")
    df = _safe_call(ak.stock_zygc_em,
                    symbol=f"{market.upper()}{code}", label="主营构成(东财·按行业/产品/地区)")
    data.blocks["zygc"] = _df_to_records(df)

    print("[3/13] 行情 K 线")
    df = _safe_call(ak.stock_zh_a_daily, symbol=prefixed,
                    start_date=kline_start, end_date=today_s, adjust="qfq",
                    label=f"新浪-日K（{max_kline_years}年前复权）")
    data.blocks["kline_daily"] = _df_to_records(df)

    df = _safe_call(ak.stock_zh_a_minute, symbol=prefixed, period="1", adjust="",
                    label="新浪-1分钟分时（最近5日）")
    data.blocks["kline_minute"] = _df_to_records(df)

    print("[4/13] 资金流向")
    df = _safe_call(ak.stock_individual_fund_flow, stock=code, market=market,
                    label="个股资金流向(近100日)")
    data.blocks["fund_flow"] = _df_to_records(df)

    print("[5/13] 龙虎榜")
    df = _safe_call(ak.stock_lhb_detail_em,
                    start_date=month_ago_s, end_date=today_s,
                    label="龙虎榜近30日全市场")
    data.blocks["lhb"] = _df_to_records(_filter_by_code(df, code))

    print("[6/13] 财务核心指标")
    df = _safe_call(ak.stock_financial_abstract, symbol=code,
                    label="财务摘要（按报告期）")
    data.blocks["fin_abstract"] = _df_to_records(df)

    df = _safe_call(ak.stock_financial_abstract_ths, symbol=code, indicator="按报告期",
                    label="同花顺-关键指标")
    data.blocks["fin_indicator_ths"] = _df_to_records(df)

    print("[7/13] 三大报表")
    df = _safe_call(ak.stock_financial_report_sina, stock=prefixed, symbol="资产负债表",
                    label="资产负债表")
    data.blocks["balance_sheet"] = _df_to_records(df)

    df = _safe_call(ak.stock_financial_report_sina, stock=prefixed, symbol="利润表",
                    label="利润表")
    data.blocks["income_statement"] = _df_to_records(df)

    df = _safe_call(ak.stock_financial_report_sina, stock=prefixed, symbol="现金流量表",
                    label="现金流量表")
    data.blocks["cashflow"] = _df_to_records(df)

    print("[8/13] 业绩预告/快报（近 4 个报告期）")
    yj_periods = ["20240331", "20240630", "20240930", "20241231"]
    yjyg_all, yjkb_all = [], []
    for p in yj_periods:
        df = _safe_call(ak.stock_yjyg_em, date=p, label=f"业绩预告 {p}")
        rows = _filter_by_code(df, code)
        if not rows.empty:
            yjyg_all.extend(_df_to_records(rows))
        df = _safe_call(ak.stock_yjkb_em, date=p, label=f"业绩快报 {p}")
        rows = _filter_by_code(df, code)
        if not rows.empty:
            yjkb_all.extend(_df_to_records(rows))
    data.blocks["yjyg"] = yjyg_all
    data.blocks["yjkb"] = yjkb_all

    print("[9/13] 股东结构")
    df = _safe_call(ak.stock_gdfx_top_10_em, symbol=prefixed, date="20231231",
                    label="十大股东（2023Q4）")
    data.blocks["top10"] = _df_to_records(df)

    df = _safe_call(ak.stock_gdfx_free_top_10_em, symbol=prefixed, date="20231231",
                    label="十大流通股东（2023Q4）")
    data.blocks["top10_free"] = _df_to_records(df)

    df = _safe_call(ak.stock_zh_a_gdhs_detail_em, symbol=code,
                    label="股东户数变动")
    data.blocks["gdhs"] = _df_to_records(df)

    if market == "sh":
        df = _safe_call(ak.stock_share_hold_change_sse, symbol=code,
                        label="高管持股变动（上交所）")
    else:
        df = _safe_call(ak.stock_share_hold_change_szse, symbol=code,
                        label="高管持股变动（深交所）")
    data.blocks["share_hold_change"] = _df_to_records(df)

    print("[10/13] 分红 / 解禁")
    df = _safe_call(ak.stock_history_dividend_detail, symbol=code, indicator="分红",
                    label="历史分红")
    data.blocks["dividend"] = _df_to_records(df)

    df = _safe_call(ak.stock_history_dividend_detail, symbol=code, indicator="配股",
                    label="历史送转")
    data.blocks["share_alloc"] = _df_to_records(df)

    df = _safe_call(ak.stock_restricted_release_queue_em, symbol=code,
                    label="限售解禁排队")
    data.blocks["release"] = _df_to_records(df)

    print("[11/13] 公告 / 新闻 / 研报")
    df = _safe_call(ak.stock_notice_report, symbol="全部", date=today_s,
                    label=f"当日公告({today_s})")
    data.blocks["notice"] = _df_to_records(_filter_by_code(df, code))

    df = _safe_call(ak.stock_news_em, symbol=code, label="个股新闻")
    data.blocks["news"] = _df_to_records(df)

    df = _safe_call(ak.stock_research_report_em, symbol=code, label="研究报告")
    data.blocks["research"] = _df_to_records(df)

    print("[12/13] 机构评级 / 基金持仓")
    df = _safe_call(ak.stock_institute_recommend, symbol="股票综合评级",
                    label="机构推荐评级（全市场）")
    data.blocks["recommend"] = _df_to_records(_filter_by_code(df, code))

    df = _safe_call(ak.stock_report_fund_hold_detail, symbol=code, date="20240331",
                    label="基金持仓（2024Q1）")
    data.blocks["fund_hold"] = _df_to_records(df)

    print("[13/13] 融资融券")
    if market == "sh":
        df = _safe_call(ak.stock_margin_detail_sse, date=last_trade_prev_s,
                        label=f"上交所融资融券({last_trade_prev_s})")
    else:
        df = _safe_call(ak.stock_margin_detail_szse, date=last_trade_prev_s,
                        label=f"深交所融资融券({last_trade_prev_s})")
    data.blocks["margin"] = _df_to_records(_filter_by_code(df, code))

    return data



def main() -> None:
    parser = argparse.ArgumentParser(description="个股全维度 HTML 报告（akshare 版）")
    parser.add_argument("code", nargs="?", help="6 位 A 股代码")
    parser.add_argument("-o", "--out-dir",
                        default=None,
                        help="（已废弃，JSON统一输出到 output/ 目录）")
    parser.add_argument("--max-kline-years", type=int, default=3,
                        help="日 K 拉取的最长年限（默认 3 年）")
    args = parser.parse_args()

    code = args.code or input("请输入 6 位 A 股代码：").strip()
    if not code:
        print("[X] 未输入股票代码", file=sys.stderr)
        sys.exit(1)

    try:
        prefixed, market = detect_market(code)
    except ValueError as e:
        print(f"[X] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"📊 生成 {code}（{prefixed}, 市场 {market.upper()}）的全量数据报告")
    print(f"   akshare 版本：{getattr(ak, '__version__', '未知')}")
    print(f"   K 线年限：{args.max_kline_years} 年")
    print()

    t0 = time.perf_counter()
    data = collect(code, max_kline_years=args.max_kline_years)
    elapsed = time.perf_counter() - t0

    n_blocks = sum(1 for v in data.blocks.values() if isinstance(v, list) and v)
    n_total_rows = sum(len(v) for v in data.blocks.values() if isinstance(v, list))
    print(f"\n✅ 数据收集完成：{n_blocks}/{len(data.blocks)} 个数据块，"
          f"共 {n_total_rows} 行，用时 {elapsed:.1f}s")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"data_{code}.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    json_payload = {"blocks": data.blocks}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, default=str)
    print(f"📊 JSON数据已保存：{json_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断")
    except Exception:
        traceback.print_exc()
        sys.exit(1)
