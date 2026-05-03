"""
个股全维度数据报告
=================
基于 akshare 调用所有"已确认稳定可用"的接口（雪球/新浪/同花顺/CNINFO/深交所/上交所），
为指定股票生成一份带交互图表的完整 HTML 报告。

设计取舍
- 故意跳过东财（push2/datacenter.eastmoney.com）老接口：在部分网络（境外、办公网）
  下会被对方主动 RST，且 1.18.58 内部尚未切到 curl_cffi。
- K 线主源：新浪日 K（stock_zh_a_daily）+ 新浪 1 分钟分时（stock_zh_a_minute）
- 全市场型接口（公告/业绩/龙虎榜/融资融券）自动按代码筛该股
- 单文件自包含 HTML：ECharts CDN + 内嵌数据，离线打开依然可用（除图表 JS 外）

用法
  python stock_full_report.py 000066
  python stock_full_report.py 600519 -o D:/out
  python stock_full_report.py 002594 --max-kline-years 3
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


# ============================================================
#  HTML 渲染
# ============================================================

def render_html(data: StockReportData) -> str:
    """生成单文件 HTML 报告。"""
    payload = {
        "meta": {
            "code": data.code,
            "prefixed": data.prefixed,
            "market": data.market.upper(),
            "generated_at": data.generated_at,
            "ak_version": data.ak_version,
        },
        "blocks": data.blocks,
    }
    payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    payload_json = payload_json.replace("</", "<\\/")  # 安全嵌入 <script>

    # 取一些首页必要的字段，提前算好放到 hero 卡片
    def _flatten(v: Any) -> str:
        """把雪球字段里偶尔出现的 dict/list 压成可读字符串。"""
        if v is None:
            return "--"
        if isinstance(v, dict):
            for key in ("ind_name", "name", "value"):
                if key in v and v[key]:
                    return str(v[key])
            return " / ".join(str(x) for x in v.values() if x is not None)[:80] or "--"
        if isinstance(v, list):
            return ", ".join(_flatten(x) for x in v[:3])[:80] or "--"
        return str(v)

    basic_dict = {row["item"]: row["value"] for row in data.blocks.get("basic_info", []) if "item" in row}
    spot = (data.blocks.get("spot") or [None])[0] or {}
    name = _flatten(basic_dict.get("org_short_name_cn") or spot.get("名称") or data.code)
    full_name = _flatten(basic_dict.get("org_name_cn") or name)
    listed_date_raw = basic_dict.get("listed_date") or basic_dict.get("established_date")
    if isinstance(listed_date_raw, (int, float)) and listed_date_raw > 1e10:
        # 雪球的 listed_date 是毫秒时间戳
        listed_date = dt.datetime.fromtimestamp(listed_date_raw / 1000).strftime("%Y-%m-%d")
    else:
        listed_date = _flatten(listed_date_raw)
    industry = _flatten(basic_dict.get("affiliate_industry") or basic_dict.get("classi_name"))
    chairman = _flatten(basic_dict.get("chairman") or basic_dict.get("legal_representative"))

    # === 公司业务画像字段 ===
    main_business = _flatten(basic_dict.get("main_operation_business")) or "--"
    intro = _flatten(basic_dict.get("org_cn_introduction")) or ""
    operating_scope = _flatten(basic_dict.get("operating_scope")) or ""
    actual_controller = _flatten(basic_dict.get("actual_controller")) or ""
    concept_tag = _flatten(basic_dict.get("classi_name")) or ""
    staff_num_raw = basic_dict.get("staff_num")
    staff_num = f"{int(staff_num_raw):,}" if isinstance(staff_num_raw, (int, float)) else "--"
    reg_asset_raw = basic_dict.get("reg_asset")
    if isinstance(reg_asset_raw, (int, float)):
        reg_asset = f"{reg_asset_raw/1e8:.2f} 亿" if reg_asset_raw >= 1e8 else f"{reg_asset_raw/1e4:.0f} 万"
    else:
        reg_asset = "--"
    province = _flatten(basic_dict.get("provincial_name")) or ""
    org_website = _flatten(basic_dict.get("org_website")) or ""

    # 最近研报快讯（前 6 条）
    research_recent = []
    for r in (data.blocks.get("research") or [])[:6]:
        title = str(r.get("报告名称", "") or "")
        org = str(r.get("机构", "") or "")
        rate = str(r.get("评级", "") or "")
        date_raw = str(r.get("日期", "") or "")[:10]
        url = r.get("报告链接") or r.get("链接") or ""
        if title:
            research_recent.append({"title": title, "org": org, "rate": rate, "date": date_raw, "url": url})

    last_close = spot.get("最新价") or "--"
    pct = spot.get("涨跌幅")
    pct_str = f"{pct:+.2f}%" if isinstance(pct, (int, float)) else "--"
    pct_class = "rise" if isinstance(pct, (int, float)) and pct > 0 else \
                "fall" if isinstance(pct, (int, float)) and pct < 0 else ""
    volume = spot.get("成交量") or "--"
    amount = spot.get("成交额") or "--"
    amount_yi = f"{amount/1e8:.2f} 亿" if isinstance(amount, (int, float)) else "--"

    counts = {k: len(v) if isinstance(v, list) else 0 for k, v in data.blocks.items()}

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(name)} {data.code} · 全维度数据报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>{CSS}</style>
</head>
<body>

<header class="hero">
  <div class="hero-inner">
    <div class="hero-top">
      <div class="brand">
        <div class="logo">📈</div>
        <div>
          <div class="hero-title">{html.escape(name)} <span class="code">{data.code}.{data.market.upper()}</span></div>
          <div class="hero-sub">{html.escape(full_name)} · {html.escape(industry)} · 上市于 {html.escape(listed_date)}</div>
        </div>
      </div>
      <div class="hero-meta">
        <span>akshare {html.escape(data.ak_version)}</span>
        <span>·</span>
        <span>{html.escape(data.generated_at)}</span>
      </div>
    </div>
    <div class="kpis">
      <div class="kpi"><div class="kpi-label">最新价</div><div class="kpi-value {pct_class}">{last_close}</div></div>
      <div class="kpi"><div class="kpi-label">涨跌幅</div><div class="kpi-value {pct_class}">{pct_str}</div></div>
      <div class="kpi"><div class="kpi-label">成交额</div><div class="kpi-value">{amount_yi}</div></div>
      <div class="kpi"><div class="kpi-label">法定代表人</div><div class="kpi-value text">{html.escape(chairman)}</div></div>
      <div class="kpi"><div class="kpi-label">数据接口</div><div class="kpi-value">{sum(1 for v in counts.values() if v > 0)}/{len(counts)}</div></div>
    </div>
  </div>
</header>

<nav class="tabs">
  <a href="#sec-profile">🪪 公司画像</a>
  <a href="#sec-business">🏭 主营业务</a>
  <a href="#sec-strategy">🧧 量化策略</a>
  <a href="#sec-quote">📈 行情</a>
  <a href="#sec-fund">💰 资金流向</a>
  <a href="#sec-fin">📊 财务</a>
  <a href="#sec-shareholder">👥 股东</a>
  <a href="#sec-dividend">🎁 分红</a>
  <a href="#sec-news">📢 公告新闻</a>
  <a href="#sec-institute">🏛 机构</a>
  <a href="#sec-special">🐉 龙虎榜·融资融券·解禁</a>
  <a href="#sec-basic">🪪 基本资料</a>
</nav>

<main>

  <!-- ========= 公司画像 ========= -->
  <section id="sec-profile" class="card profile-card">
    <h2>🪪 公司画像 · 一眼看懂这家公司</h2>
    <div class="profile-grid">
      <div class="profile-main">
        <div class="profile-tagline">🎯 主营业务</div>
        <div class="profile-business">{html.escape(main_business)}</div>

        <div class="profile-tags">
          {f'<span class="tag tag-red">🏛 {html.escape(actual_controller)}</span>' if actual_controller else ''}
          {f'<span class="tag tag-gold">🏷 {html.escape(concept_tag)}</span>' if concept_tag else ''}
          {f'<span class="tag">📍 {html.escape(industry)}</span>' if industry else ''}
          {f'<span class="tag">📅 上市 {html.escape(listed_date)}</span>' if listed_date else ''}
          {f'<span class="tag">👥 员工 {html.escape(staff_num)}</span>' if staff_num != "--" else ''}
          {f'<span class="tag">💰 注册资本 {html.escape(reg_asset)}</span>' if reg_asset != "--" else ''}
          {f'<span class="tag">🌏 {html.escape(province)}</span>' if province else ''}
        </div>

        {f'<div class="profile-intro">{html.escape(intro)}</div>' if intro else ''}

        {f'''<details class="data-fold" style="margin-top:14px;">
          <summary>📜 完整经营范围</summary>
          <div style="padding: 12px 18px; background:#fff; font-size:13px; line-height:1.8; color: var(--text); max-height: 240px; overflow:auto;">{html.escape(operating_scope)}</div>
        </details>''' if operating_scope else ''}

        {f'<div style="margin-top:10px; font-size:12px; color: var(--text-muted);">🌐 官网：<a href="https://{html.escape(org_website)}" target="_blank" style="color: var(--primary);">{html.escape(org_website)}</a></div>' if org_website else ''}
      </div>

      <div class="profile-news">
        <div class="profile-news-title">🗞 最新研报快讯 <span style="font-size:11px; color: var(--text-muted); font-weight:normal;">（{len(data.blocks.get("research") or [])} 篇）</span></div>
        <div class="profile-news-list">
        {''.join(
          f'''<div class="news-item">
              <div class="news-meta"><span class="news-date">{html.escape(r["date"])}</span><span class="news-org">{html.escape(r["org"])}</span>{f'<span class="news-rate">{html.escape(r["rate"])}</span>' if r["rate"] else ''}</div>
              <div class="news-title">{html.escape(r["title"])}</div>
            </div>'''
          for r in research_recent
        ) or '<div style="padding:14px; color:var(--text-muted); font-size:12px;">暂无研报</div>'}
        </div>
      </div>
    </div>
  </section>

  <!-- ========= 主营构成 ========= -->
  <section id="sec-business" class="card">
    <h2>🏭 主营业务构成</h2>
    <div class="card-sub">东方财富 F10 · 按行业 / 产品 / 地区分类 · 共 {counts.get('zygc', 0)} 行</div>
    <div class="grid-2">
      <div>
        <div style="font-size:13px; font-weight:700; color:var(--primary); margin:4px 0 6px; padding-left:8px;">🛍 按产品 / 业务（最近报告期）</div>
        <div class="chart-box" id="chart-zygc-product"></div>
      </div>
      <div>
        <div style="font-size:13px; font-weight:700; color:var(--primary); margin:4px 0 6px; padding-left:8px;">🌏 按地区（最近报告期）</div>
        <div class="chart-box" id="chart-zygc-region"></div>
      </div>
    </div>
    <div style="font-size:13px; font-weight:700; color:var(--primary); margin:18px 0 6px; padding-left:8px;">📊 历年产品营收堆积（按报告期）</div>
    <div class="chart-box tall" id="chart-zygc-trend"></div>

    <div style="font-size:13px; font-weight:700; color:var(--primary); margin:24px 0 8px; padding-left:8px;">🏷 业务关键词云 <span style="font-weight:normal; font-size:12px; color:var(--text-muted);">（从 {len(data.blocks.get("research") or [])} 篇研报标题自动抽取）</span></div>
    <div id="word-cloud" class="word-cloud"></div>

    <details class="data-fold" style="margin-top:14px;">
      <summary>展开主营构成原始数据 ({counts.get('zygc', 0)} 行)</summary>
      <div class="table-wrap" id="table-zygc"></div>
    </details>
  </section>

  <section id="sec-strategy" class="card strategy-card">
    <h2>🧧 量化策略思路（基于本股已采数据）</h2>
    <div class="card-sub">
      下列 8 个维度的策略建议都可以用本报告里已经采到的数据直接计算落地，无需额外数据源。
      括号里是本股该维度可用的样本量。
    </div>
    <div class="strategy-grid">

      <div class="strategy-item">
        <h4>📈 趋势 / 技术面 <span class="badge">{counts.get('kline_daily', 0)} 根日K · {counts.get('kline_minute', 0)} 个分时点</span></h4>
        <p>基于新浪日 K（前复权）和 1 分钟分时数据。</p>
        <ul>
          <li><b>多周期均线系统</b>：MA5/20/60 已画在 K 线图上，金叉/死叉作为入场出场信号</li>
          <li><b>突破策略</b>：回撤 N 日内新高 + 量能放大（成交量 &gt; 5 日均量 1.5×）</li>
          <li><b>反转因子</b>：CCI / RSI 超卖回升、MACD 底背离</li>
          <li><b>波动率</b>：ATR 仓位管理；20 日年化波动率定 stop-loss</li>
        </ul>
      </div>

      <div class="strategy-item">
        <h4>💰 资金 / 主力博弈 <span class="badge">{counts.get('fund_flow', 0)} 个交易日</span></h4>
        <p>东财个股版资金流向，含主力 / 超大 / 大 / 中 / 小单。</p>
        <ul>
          <li><b>主力净流入连续性</b>：连续 N 日主力净流入 &gt; 0 且累计 / 流通市值 &gt; 阈值时建仓</li>
          <li><b>大单 vs 散户背离</b>：超大单 + 大单流入 + 中小单流出 = 主力吸筹</li>
          <li><b>资金动量因子</b>：5 日 / 20 日主力净流入比；可与价格动量做交叉过滤</li>
        </ul>
      </div>

      <div class="strategy-item">
        <h4>📊 估值 / 价值面 <span class="badge">{counts.get('fin_abstract', 0)} 期摘要 · {counts.get('balance_sheet', 0)} 期资负</span></h4>
        <p>财务摘要 + 三大报表（新浪）+ 同花顺关键指标。</p>
        <ul>
          <li><b>PE/PB/PS 历史分位</b>：以本股自身 5 年分位数判断高估低估</li>
          <li><b>PEG = PE / 净利润增速</b>：&lt; 1 估值有吸引力</li>
          <li><b>EV/EBITDA</b>：剔除资本结构差异，行业内横比更稳</li>
          <li><b>股息率筛选</b>：结合"分红"章节，过滤 5 年连续派息且股息率 &gt; 3% 的股</li>
        </ul>
      </div>

      <div class="strategy-item">
        <h4>🌱 成长 / 业绩面 <span class="badge">{counts.get('yjyg', 0)} 条预告 · {counts.get('yjkb', 0)} 条快报</span></h4>
        <p>业绩预告 + 业绩快报（已筛选本股）+ 同花顺关键指标趋势。</p>
        <ul>
          <li><b>业绩超预期事件驱动</b>：预告增幅上限 &gt; 一致预期 → 财报后 5/20 日漂移</li>
          <li><b>GARP（合理价格成长）</b>：营收增速 + 净利增速 + ROE &gt; 行业中位</li>
          <li><b>盈利质量</b>：经营性现金流 / 净利润 &gt; 1，避免"纸面利润"</li>
        </ul>
      </div>

      <div class="strategy-item">
        <h4>🪙 筹码 / 股东结构 <span class="badge">{counts.get('gdhs', 0)} 期户数 · {counts.get('top10', 0)} 名前十</span></h4>
        <p>股东户数变动 + 十大股东 / 流通股东。</p>
        <ul>
          <li><b>筹码集中信号</b>：户数减少 + 股价上涨 = 主力建仓；2 个季度连续递减时强化</li>
          <li><b>十大股东重叠率</b>：与同行业龙头股的机构重合度（公募 / 社保）</li>
          <li><b>解禁 + 减持事件</b>：限售解禁日前 30 日股价压力测试，配合龙虎榜判断接盘方</li>
        </ul>
      </div>

      <div class="strategy-item">
        <h4>🗞 情绪 / 研报 <span class="badge">{counts.get('research', 0)} 篇研报 · {counts.get('news', 0)} 条新闻</span></h4>
        <p>东财研究报告（已成功）+ 个股新闻。</p>
        <ul>
          <li><b>分析师评级上调事件</b>：N 家券商在 30 日内上调评级 → 入选信号</li>
          <li><b>目标价中位数 / 现价</b>：&gt; 1.2 视为有上行空间</li>
          <li><b>研报覆盖度变化</b>：突然新增覆盖往往伴随主题催化</li>
          <li><b>新闻情感</b>：用 LLM / 中文情感词典对新闻标题打分聚合</li>
        </ul>
      </div>

      <div class="strategy-item">
        <h4>🐉 事件驱动 <span class="badge">{counts.get('lhb', 0)} 条龙虎榜 · {counts.get('release', 0)} 次解禁 · {counts.get('share_hold_change', 0)} 次高管变动</span></h4>
        <p>龙虎榜 + 限售解禁 + 高管持股变动 + 公告。</p>
        <ul>
          <li><b>游资跟踪</b>：龙虎榜买方席位识别（如"国泰君安顺德德民路"= 章盟主），跟单 T+1</li>
          <li><b>高管增持</b>：连续 3 个月净增持金额 &gt; 1000 万 = 强信号</li>
          <li><b>解禁日漂移</b>：解禁前 5 日空头 / 解禁后 20 日反弹是经典套路</li>
        </ul>
      </div>

      <div class="strategy-item">
        <h4>🏛 机构 / 杠杆资金 <span class="badge">{counts.get('fund_hold', 0)} 条基金持仓 · {counts.get('margin', 0)} 行融券</span></h4>
        <p>基金持仓 + 融资融券明细。</p>
        <ul>
          <li><b>公募抱团度</b>：重仓基金数量及持仓占流通比；新增抱团 = 拐点信号</li>
          <li><b>融资余额变化</b>：5 日融资余额 / 流通市值 &gt; 历史 80% 分位 = 杠杆过热</li>
          <li><b>融券卖出量</b>：突增 = 短期看空信号，可与基本面对冲</li>
        </ul>
      </div>

    </div>
    <div class="card-sub" style="margin-top: 16px; padding: 10px 14px; background: var(--primary-soft); border-left: 3px solid var(--primary); border-radius: 6px;">
      <b style="color: var(--primary);">⚠ 风险提示：</b>
      上述均为研究框架与历史规律，不构成投资建议。回测请避免未来函数、生存者偏差，A 股有 T+1 / 涨跌停 / 停牌等约束需在策略中显式建模。
    </div>
  </section>

  <section id="sec-quote" class="card">
    <h2>📈 行情走势</h2>
    <div class="card-sub">数据源：新浪。日 K 默认前复权，分时为新浪 1 分钟。</div>
    <div class="charts-row">
      <div id="chart-kline" class="chart-box tall"></div>
    </div>
    <div class="charts-row">
      <div id="chart-minute" class="chart-box"></div>
    </div>
  </section>

  <section id="sec-fund" class="card">
    <h2>💰 资金流向（近 100 个交易日）</h2>
    <div class="card-sub">数据源：东财（个股版）。展示主力净流入金额与各级别堆叠占比。</div>
    <div id="chart-fund" class="chart-box tall"></div>
    <details class="data-fold">
      <summary>展开原始数据 ({counts.get('fund_flow', 0)} 行)</summary>
      <div class="table-wrap" id="table-fund-flow"></div>
    </details>
  </section>

  <section id="sec-northbound" class="card">
    <h2>🌏 北向资金持股变动（陆股通）</h2>
    <div class="card-sub">数据源：东财 ·  共 {counts.get('northbound', 0)} 个交易日。左轴展示持股占A股百分比 / 股价，右轴展示持股市值。</div>
    <div id="kpi-northbound" class="kpi-grid"></div>
    <div id="chart-northbound" class="chart-box tall"></div>
    <div id="chart-northbound-flow" class="chart-box"></div>
    <details class="data-fold">
      <summary>展开原始数据（{counts.get('northbound', 0)} 行）</summary>
      <div class="table-wrap" id="table-northbound"></div>
    </details>
  </section>

  <section id="sec-fin" class="card">
    <h2>📊 财务表现</h2>
    <div class="card-sub">财务摘要：{counts.get('fin_abstract', 0)} 期；同花顺关键指标：{counts.get('fin_indicator_ths', 0)} 期</div>
    <div class="charts-row">
      <div id="chart-fin" class="chart-box tall"></div>
    </div>
    <div class="grid-2">
      <details class="data-fold">
        <summary>资产负债表（{counts.get('balance_sheet', 0)} 期 × 完整字段）</summary>
        <div class="table-wrap" id="table-balance"></div>
      </details>
      <details class="data-fold">
        <summary>利润表（{counts.get('income_statement', 0)} 期）</summary>
        <div class="table-wrap" id="table-income"></div>
      </details>
      <details class="data-fold">
        <summary>现金流量表（{counts.get('cashflow', 0)} 期）</summary>
        <div class="table-wrap" id="table-cashflow"></div>
      </details>
      <details class="data-fold">
        <summary>财务摘要 / 同花顺关键指标</summary>
        <div class="table-wrap" id="table-fin-abstract"></div>
        <div class="table-wrap" id="table-fin-ths"></div>
      </details>
      <details class="data-fold">
        <summary>业绩预告 ({len(payload['blocks'].get('yjyg', []))} 条) / 快报 ({len(payload['blocks'].get('yjkb', []))} 条)</summary>
        <div class="table-wrap" id="table-yjyg"></div>
        <div class="table-wrap" id="table-yjkb"></div>
      </details>
    </div>
  </section>

  <section id="sec-shareholder" class="card">
    <h2>👥 股东结构</h2>
    <div class="card-sub">十大股东 + 股东户数趋势 + 高管持股变动</div>
    <div class="grid-2">
      <div id="chart-top10" class="chart-box"></div>
      <div id="chart-gdhs" class="chart-box"></div>
    </div>
    <div class="grid-2">
      <details class="data-fold" open>
        <summary>十大股东 / 流通股东（{counts.get('top10', 0)} + {counts.get('top10_free', 0)} 条）</summary>
        <div class="table-wrap" id="table-top10"></div>
        <div class="table-wrap" id="table-top10-free"></div>
      </details>
      <details class="data-fold">
        <summary>高管持股变动（{counts.get('share_hold_change', 0)} 条）</summary>
        <div class="table-wrap" id="table-share-hold"></div>
      </details>
    </div>
  </section>

  <section id="sec-dividend" class="card">
    <h2>🎁 分红 / 送转</h2>
    <div class="grid-2">
      <details class="data-fold" open>
        <summary>历史分红（{counts.get('dividend', 0)} 条）</summary>
        <div class="table-wrap" id="table-dividend"></div>
      </details>
      <details class="data-fold">
        <summary>历史送转 / 配股（{counts.get('share_alloc', 0)} 条）</summary>
        <div class="table-wrap" id="table-share-alloc"></div>
      </details>
    </div>
  </section>

  <section id="sec-news" class="card">
    <h2>📢 公告 / 新闻 / 研报</h2>
    <div class="grid-2">
      <details class="data-fold" open>
        <summary>个股新闻（{counts.get('news', 0)} 条）</summary>
        <div class="table-wrap" id="table-news"></div>
      </details>
      <details class="data-fold" open>
        <summary>研究报告（{counts.get('research', 0)} 条）</summary>
        <div class="table-wrap" id="table-research"></div>
      </details>
    </div>
    <details class="data-fold">
      <summary>当日公告（已筛选该股 {counts.get('notice', 0)} 条）</summary>
      <div class="table-wrap" id="table-notice"></div>
    </details>
  </section>

  <section id="sec-research-field" class="card">
    <h2>🏢 机构调研记录（最近 21 日）</h2>
    <div class="card-sub">数据源：东财 · 含调研机构 / 机构类型 / 接待方式 / 接待人员 · 共 {counts.get('research_field', 0)} 条。</div>
    <div id="kpi-research-field" class="kpi-grid"></div>
    <div class="grid-2">
      <div id="chart-research-field-type" class="chart-box"></div>
      <div id="research-field-list" class="research-timeline"></div>
    </div>
    <details class="data-fold">
      <summary>展开原始数据（{counts.get('research_field', 0)} 条）</summary>
      <div class="table-wrap" id="table-research-field"></div>
    </details>
  </section>

  <section id="sec-institute" class="card">
    <h2>🏛 机构评级与持仓</h2>
    <div class="grid-2">
      <details class="data-fold" open>
        <summary>机构综合评级（{counts.get('recommend', 0)} 条）</summary>
        <div class="table-wrap" id="table-recommend"></div>
      </details>
      <details class="data-fold" open>
        <summary>基金持仓（{counts.get('fund_hold', 0)} 条）</summary>
        <div class="table-wrap" id="table-fund-hold"></div>
      </details>
    </div>
  </section>

  <section id="sec-special" class="card">
    <h2>🐉 龙虎榜 / 融资融券 / 解禁</h2>
    <div class="grid-2">
      <details class="data-fold" {"open" if counts.get('lhb',0) else ""}>
        <summary>龙虎榜（已筛选该股 {counts.get('lhb', 0)} 条）</summary>
        <div class="table-wrap" id="table-lhb"></div>
      </details>
      <details class="data-fold" {"open" if counts.get('margin',0) else ""}>
        <summary>融资融券明细（{counts.get('margin', 0)} 条）</summary>
        <div class="table-wrap" id="table-margin"></div>
      </details>
      <details class="data-fold" {"open" if counts.get('release',0) else ""}>
        <summary>限售解禁排队（{counts.get('release', 0)} 条）</summary>
        <div class="table-wrap" id="table-release"></div>
      </details>
    </div>
  </section>

  <section id="sec-basic" class="card">
    <h2>🪪 基本资料</h2>
    <div class="grid-2">
      <details class="data-fold" open>
        <summary>雪球公司概况（{counts.get('basic_info', 0)} 项）</summary>
        <div class="table-wrap" id="table-basic"></div>
      </details>
      <details class="data-fold">
        <summary>股本结构变动历史（{counts.get('share_structure', 0)} 条）</summary>
        <div class="table-wrap" id="table-share-structure"></div>
      </details>
    </div>
  </section>
</main>

<footer>
  <div class="blessing">🧧  恭 喜 发 财 · 红 包 拿 来  🧧</div>
  <div>数据来源：雪球 / 新浪财经 / 同花顺 / 巨潮资讯 / 深交所·上交所</div>
  <div>由 akshare {html.escape(data.ak_version)} 生成 · {html.escape(data.generated_at)}</div>
</footer>

<script id="payload" type="application/json">{payload_json}</script>
<script>{JS}</script>
</body>
</html>
"""


# ============================================================
#  CSS / JS（通过 .format/{} 注入）
# ============================================================

CSS = r"""
/* === 招财进宝主题 · 中国红 × 流光金 === */
:root {
  --bg: #fff8ec;
  --bg-pattern: #fdf0d4;
  --card: #fffefa;
  --line: #e7c373;
  --line-soft: #f7e1a8;
  --text: #3a1108;
  --text-soft: #8b2a0e;
  --text-muted: #a8714a;
  --primary: #c8102e;
  --primary-dark: #8b0000;
  --primary-soft: #fee4d6;
  --gold: #c89b3c;
  --gold-light: #f6c94c;
  --gold-bright: #ffe066;
  --rise: #c8102e;
  --fall: #16a34a;
  --hero-bg: radial-gradient(ellipse at top right, #fbbf24 0%, transparent 50%),
             radial-gradient(ellipse at bottom left, #f59e0b 0%, transparent 55%),
             linear-gradient(135deg, #6b0000 0%, #8b0000 25%, #b91c1c 55%, #c8102e 80%, #dc2626 100%);
}
* { box-sizing: border-box; }
body { margin: 0; padding: 0;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Source Han Sans", sans-serif;
  background: var(--bg);
  background-image:
    radial-gradient(circle at 20% 10%, rgba(245, 158, 11, .08) 0, transparent 40%),
    radial-gradient(circle at 80% 90%, rgba(200, 16, 46, .06) 0, transparent 40%);
  color: var(--text); font-feature-settings: "tnum"; }

/* ========= Hero 红金 ========= */
header.hero {
  background: var(--hero-bg); color: #fff8ec;
  padding: 40px 5vw 100px; position: relative; overflow: hidden;
  border-bottom: 4px solid var(--gold-light);
  box-shadow: 0 4px 20px rgba(139, 0, 0, .35);
}
/* 顶部祥云装饰 */
header.hero::before {
  content: ""; position: absolute; inset: 0;
  background-image:
    radial-gradient(circle at 15% 30%, rgba(255, 224, 102, .25) 0, transparent 25%),
    radial-gradient(circle at 85% 70%, rgba(255, 224, 102, .20) 0, transparent 25%),
    repeating-linear-gradient(45deg, transparent 0 24px, rgba(255, 224, 102, .04) 24px 25px);
  pointer-events: none;
}
/* 右上角金色印章感光环 */
header.hero::after {
  content: "招財進寶"; position: absolute; right: 24px; top: 18px;
  width: 90px; height: 90px; border: 3px double rgba(255, 224, 102, .65);
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  color: rgba(255, 224, 102, .85); font-weight: 700; font-size: 14px;
  font-family: "STKaiti", "KaiTi", serif; letter-spacing: 2px;
  writing-mode: vertical-rl; text-orientation: upright;
  text-shadow: 0 0 8px rgba(255, 224, 102, .5);
  pointer-events: none;
}
.hero-inner { max-width: 1400px; margin: 0 auto; position: relative; z-index: 1; }
.hero-top { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }
.brand { display: flex; gap: 14px; align-items: center; }
.logo { width: 52px; height: 52px; border-radius: 14px;
        background: linear-gradient(135deg, #ffe066 0%, #c89b3c 100%);
        display: flex; align-items: center; justify-content: center;
        font-size: 26px; box-shadow: 0 4px 14px rgba(0, 0, 0, .25),
                                     inset 0 1px 0 rgba(255, 255, 255, .3); }
.hero-title { font-size: 30px; font-weight: 700; margin: 0; letter-spacing: 1px;
              font-family: "STKaiti", "KaiTi", "PingFang SC", serif;
              text-shadow: 0 2px 8px rgba(0, 0, 0, .35), 0 0 16px rgba(255, 224, 102, .25);
              color: #fff; }
.hero-title .code {
  font-size: 14px; opacity: .9; margin-left: 10px; font-weight: 500;
  font-family: "JetBrains Mono", "Consolas", monospace;
  background: rgba(255, 224, 102, .18); padding: 3px 10px; border-radius: 12px;
  border: 1px solid rgba(255, 224, 102, .4); color: var(--gold-bright);
}
.hero-sub { font-size: 13px; opacity: .92; margin-top: 6px; color: #ffe9b8; }
.hero-meta { font-size: 12px; opacity: .85; display: flex; gap: 6px; align-items: center; color: #ffe9b8; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 14px; margin-top: 28px; position: relative; z-index: 1; }
.kpi {
  background: linear-gradient(135deg, rgba(255, 248, 236, .14) 0%, rgba(255, 224, 102, .08) 100%);
  border: 1.5px solid rgba(255, 224, 102, .5);
  border-radius: 14px; padding: 16px 20px;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, .15), inset 0 1px 0 rgba(255, 224, 102, .2);
  position: relative; overflow: hidden;
}
.kpi::after {
  content: ""; position: absolute; top: 0; right: 0; width: 60px; height: 60px;
  background: radial-gradient(circle at top right, rgba(255, 224, 102, .25) 0, transparent 70%);
  pointer-events: none;
}
.kpi-label { font-size: 11px; opacity: .85; letter-spacing: 1.5px; color: var(--gold-bright); font-weight: 600; }
.kpi-value { font-size: 24px; font-weight: 700; margin-top: 6px;
             font-family: "JetBrains Mono", "Consolas", monospace;
             color: #fff; text-shadow: 0 0 8px rgba(255, 224, 102, .4); }
.kpi-value.text { font-size: 15px; font-family: "STKaiti", inherit; font-weight: 600; letter-spacing: 1px; }
.kpi-value.rise { color: #ffd166; text-shadow: 0 0 12px rgba(255, 209, 102, .6); }
.kpi-value.fall { color: #86efac; text-shadow: 0 0 12px rgba(134, 239, 172, .5); }

/* ========= 吸顶导航 ========= */
nav.tabs {
  position: sticky; top: 0; z-index: 50;
  background: linear-gradient(180deg, rgba(255, 248, 236, .98) 0%, rgba(255, 248, 236, .95) 100%);
  backdrop-filter: blur(12px);
  border-bottom: 2px solid var(--gold-light);
  padding: 10px 5vw; margin-top: -50px; border-radius: 16px 16px 0 0;
  max-width: 1400px; margin-left: auto; margin-right: auto;
  box-shadow: 0 4px 20px rgba(139, 0, 0, .12);
  display: flex; flex-wrap: wrap; gap: 4px;
}
nav.tabs a {
  padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
  color: var(--text-soft); text-decoration: none; transition: all .2s;
}
nav.tabs a:hover {
  background: linear-gradient(135deg, var(--primary) 0%, var(--gold) 100%);
  color: #fff; transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(200, 16, 46, .3);
}

main { max-width: 1400px; margin: 0 auto; padding: 24px 5vw 60px; }

/* ========= 章节卡片（金边） ========= */
.card {
  background: var(--card); border-radius: 18px; padding: 28px 32px; margin-bottom: 22px;
  box-shadow: 0 2px 6px rgba(139, 0, 0, .06), 0 8px 28px rgba(139, 0, 0, .06);
  border: 1.5px solid var(--line);
  position: relative; overflow: hidden;
}
/* 卡片左侧红色印章条 */
.card::before {
  content: ""; position: absolute; left: 0; top: 24px; bottom: 24px; width: 5px;
  background: linear-gradient(180deg, var(--primary) 0%, var(--gold) 100%);
  border-radius: 0 4px 4px 0;
}
.card h2 {
  margin: 0 0 6px; font-size: 20px; font-weight: 700;
  display: flex; align-items: center; gap: 10px;
  color: var(--primary); letter-spacing: 1px;
  font-family: "STKaiti", "KaiTi", "PingFang SC", sans-serif;
  text-shadow: 0 1px 0 #fff;
}
.card-sub { font-size: 12px; color: var(--text-muted); margin-bottom: 18px;
            padding-left: 4px; border-left: 2px solid var(--gold-light);
            padding: 4px 0 4px 10px; }

/* ========= 公司画像卡 ========= */
.profile-card {
  background: linear-gradient(135deg, #fff8ec 0%, #fef3c7 60%, #fff5d6 100%);
  border: 2px solid var(--gold);
  position: relative;
}
.profile-card::after {
  content: "福"; position: absolute; right: 24px; bottom: 18px;
  font-family: "STKaiti","STSong","KaiTi", serif; font-size: 90px;
  color: rgba(200, 16, 46, .07); font-weight: 900; pointer-events: none;
  line-height: 1; letter-spacing: -8px;
}
.profile-grid {
  display: grid; grid-template-columns: 1.5fr 1fr; gap: 24px; margin-top: 8px;
  position: relative; z-index: 1;
}
.profile-main {}
.profile-tagline {
  font-size: 12px; color: var(--gold); letter-spacing: 3px; font-weight: 700;
  margin-bottom: 6px;
}
.profile-business {
  font-size: 22px; font-weight: 700; color: var(--primary-dark);
  font-family: "STKaiti","KaiTi", serif; line-height: 1.4;
  letter-spacing: 1px; padding: 6px 0 12px;
  text-shadow: 0 1px 0 #fff;
}
.profile-tags {
  display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 14px;
}
.tag {
  display: inline-flex; align-items: center; padding: 5px 12px; border-radius: 14px;
  font-size: 12px; font-weight: 600;
  background: rgba(255, 255, 255, .8); border: 1px solid var(--line);
  color: var(--text-soft);
}
.tag-red {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border-color: var(--primary); color: var(--primary-dark);
}
.tag-gold {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-color: var(--gold); color: #92400e;
}
.profile-intro {
  font-size: 13px; line-height: 1.7; color: var(--text);
  background: rgba(255, 255, 255, .7); padding: 12px 16px; border-radius: 10px;
  border-left: 3px solid var(--gold);
  margin-top: 6px;
}

/* 研报快讯 */
.profile-news {
  background: #fff; border: 1px solid var(--line-soft); border-radius: 12px;
  padding: 14px 16px;
  box-shadow: inset 0 0 0 1px rgba(212, 160, 23, .15);
  max-height: 360px; overflow-y: auto;
}
.profile-news-title {
  font-size: 14px; font-weight: 700; color: var(--primary);
  padding-bottom: 8px; border-bottom: 2px dashed var(--gold-light);
  margin-bottom: 10px;
}
.profile-news-list { display: flex; flex-direction: column; gap: 10px; }
.news-item {
  padding: 8px 10px; border-radius: 8px;
  border-left: 3px solid var(--primary); background: var(--bg-pattern);
  transition: background .15s, transform .15s;
}
.news-item:hover { background: #fff; transform: translateX(2px); }
.news-meta {
  display: flex; gap: 8px; align-items: center;
  font-size: 11px; color: var(--text-muted); margin-bottom: 4px;
}
.news-date { font-family: "JetBrains Mono", monospace; color: var(--gold); font-weight: 600; }
.news-org { color: var(--primary-dark); font-weight: 600; }
.news-rate {
  margin-left: auto; padding: 1px 6px; border-radius: 8px;
  background: var(--primary-soft); color: var(--primary); font-weight: 700;
}
.news-title {
  font-size: 12.5px; line-height: 1.5; color: var(--text);
  font-weight: 500;
}

/* ========= 业务关键词云 v2 ========= */
.word-cloud {
  padding: 18px 20px; background: #fff;
  border: 1px dashed var(--gold-light); border-radius: 12px;
  min-height: 100px;
  background-image:
    radial-gradient(circle at 10% 20%, rgba(245, 158, 11, .05) 0, transparent 30%),
    radial-gradient(circle at 90% 80%, rgba(200, 16, 46, .05) 0, transparent 30%);
}

/* 明星词（Top 3） */
.wc-stars {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 16px;
  padding-bottom: 14px; border-bottom: 1px dashed var(--gold-light);
}
.wc-star {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 12px 16px; border-radius: 14px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 60%, var(--gold) 100%);
  color: #fff8ec; box-shadow: 0 6px 18px rgba(139, 0, 0, .25),
                              inset 0 1px 0 rgba(255, 255, 255, .2);
  position: relative; overflow: hidden;
  transition: transform .2s;
}
.wc-star:hover { transform: translateY(-3px); }
.wc-star::before {
  content: "✨"; position: absolute; top: 6px; right: 8px;
  font-size: 14px; opacity: .7;
}
.wc-star-1 {
  background: linear-gradient(135deg, #c8102e 0%, #8b0000 50%, #ffd700 100%);
  transform: scale(1.05);
}
.wc-star-1::before { content: "🥇"; }
.wc-star-2::before { content: "🥈"; }
.wc-star-3::before { content: "🥉"; }
.wc-rank {
  font-size: 11px; opacity: .85; letter-spacing: 1px;
  font-family: "JetBrains Mono", monospace; font-weight: 700;
  color: var(--gold-bright);
}
.wc-star .wc-word {
  font-size: 22px; font-weight: 700; margin: 4px 0;
  font-family: "STKaiti", "KaiTi", serif; letter-spacing: 1.5px;
  text-shadow: 0 2px 6px rgba(0, 0, 0, .35);
}
.wc-star-1 .wc-word { font-size: 26px; }
.wc-count {
  font-size: 11px; opacity: .9;
  background: rgba(255, 224, 102, .25); padding: 2px 10px; border-radius: 10px;
  border: 1px solid rgba(255, 224, 102, .4);
  font-weight: 600;
}

/* 主词云区 */
.wc-main {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: center;
  gap: 8px 10px; line-height: 1.6;
}
.wc-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px 4px 12px; border-radius: 14px;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: var(--primary-dark); font-weight: 600;
  border: 1px solid rgba(212, 160, 23, .35);
  transition: transform .15s, box-shadow .15s, filter .15s;
  cursor: default;
}
.wc-tag:hover { transform: translateY(-2px) scale(1.05);
  box-shadow: 0 6px 16px rgba(200, 16, 46, .2);
  filter: brightness(1.05); }
.wc-tag.hot {
  background: linear-gradient(135deg, var(--primary) 0%, #f59e0b 100%);
  color: #fff; border-color: var(--primary);
  box-shadow: 0 2px 8px rgba(200, 16, 46, .25);
}
.wc-tag.warm {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: var(--primary-dark); border-color: var(--primary);
}
.wc-badge {
  display: inline-block; min-width: 18px; padding: 0 5px;
  font-size: 10px; font-weight: 700;
  border-radius: 8px; line-height: 14px; height: 14px;
  background: rgba(255, 255, 255, .35); color: inherit;
  font-family: "JetBrains Mono", monospace;
}
.wc-tag.hot .wc-badge { background: rgba(255, 224, 102, .4); color: #fff; }

.wc-footer {
  margin-top: 14px; padding-top: 10px;
  border-top: 1px dashed var(--line-soft);
  font-size: 11px; color: var(--text-muted); text-align: center;
}

/* 量化策略卡片专用 */
.strategy-card { background: linear-gradient(135deg, #fff8ec 0%, #fef3c7 100%);
                 border: 2px solid var(--gold); }
.strategy-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 8px; }
.strategy-item {
  background: #fffefa; border: 1px solid var(--line-soft); border-radius: 12px;
  padding: 14px 16px; position: relative; transition: transform .15s, box-shadow .15s;
}
.strategy-item:hover { transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(200, 16, 46, .12); border-color: var(--primary); }
.strategy-item h4 { margin: 0 0 6px; font-size: 14px; color: var(--primary);
                    display: flex; align-items: center; gap: 6px; font-weight: 700; }
.strategy-item .badge {
  display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: var(--primary-soft); color: var(--primary); font-weight: 600;
  margin-left: auto;
}
.strategy-item p { margin: 4px 0; font-size: 12px; color: var(--text-soft); line-height: 1.6; }
.strategy-item ul { margin: 4px 0; padding-left: 18px; font-size: 12px; color: var(--text); line-height: 1.7; }
.strategy-item li::marker { color: var(--gold); }

.charts-row { margin: 12px 0; }
.chart-box { width: 100%; height: 360px; }
.chart-box.tall { height: 480px; }
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }
.grid-2 .chart-box { height: 320px; }

/* ========= KPI 数据卡 ========= */
.kpi-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px; margin: 10px 0 18px;
}
.kpi-card {
  background: linear-gradient(135deg, #fff 0%, #fff8ec 100%);
  border: 1.5px solid var(--gold-light); border-radius: 12px;
  padding: 12px 16px; position: relative; overflow: hidden;
  transition: transform .15s, box-shadow .15s;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(200, 16, 46, .12);
  border-color: var(--primary);
}
.kpi-card .kpi-label {
  font-size: 11px; color: var(--text-muted);
  letter-spacing: 1.2px; margin-bottom: 4px;
}
.kpi-card .kpi-value {
  font-size: 22px; font-weight: 800; color: var(--primary);
  font-family: "JetBrains Mono", monospace;
  letter-spacing: -.5px;
}
.kpi-card .kpi-sub {
  font-size: 11px; color: var(--text-soft); margin-top: 4px;
}
.kpi-card .kpi-value.rise { color: var(--rise); }
.kpi-card .kpi-value.fall { color: var(--fall); }
.kpi-card.accent {
  background: linear-gradient(135deg, var(--primary-soft) 0%, #fff 100%);
  border-color: var(--primary);
}
.kpi-card::after {
  content: ""; position: absolute; right: -12px; top: -12px;
  width: 60px; height: 60px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 224, 102, .35) 0%, transparent 70%);
}

/* ========= 机构调研时间线 ========= */
.research-timeline {
  background: #fff; border: 1px solid var(--line-soft); border-radius: 12px;
  padding: 12px 14px; max-height: 320px; overflow-y: auto;
  font-size: 12px;
}
.research-timeline:empty::before {
  content: "（最近 21 日暂无机构调研记录）";
  color: var(--text-muted); font-family: "STKaiti", serif;
  display: block; padding: 24px; text-align: center;
}
.research-item {
  position: relative; padding: 8px 12px 10px 26px;
  border-left: 2px solid var(--gold-light);
  margin-bottom: 8px; transition: background .15s;
}
.research-item:hover { background: var(--primary-soft); border-left-color: var(--primary); }
.research-item:last-child { margin-bottom: 0; }
.research-item::before {
  content: ""; position: absolute; left: -6px; top: 12px;
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--gold); border: 2px solid #fff;
  box-shadow: 0 0 0 1px var(--gold);
}
.research-item:hover::before { background: var(--primary); box-shadow: 0 0 0 1px var(--primary); }
.research-date {
  font-size: 10px; color: var(--text-muted);
  font-family: "JetBrains Mono", monospace;
  letter-spacing: .8px;
}
.research-org {
  font-size: 13px; font-weight: 700; color: var(--text);
  margin: 2px 0; display: flex; align-items: center; gap: 6px;
}
.research-tag {
  display: inline-block; font-size: 10px; padding: 1px 7px;
  background: var(--gold-light); color: var(--text);
  border-radius: 8px; font-weight: 600;
}
.research-tag.证券公司 { background: rgba(200, 16, 46, .12); color: var(--primary); }
.research-tag.基金公司 { background: rgba(212, 175, 55, .25); color: #8a6d10; }
.research-tag.私募基金 { background: rgba(34, 139, 34, .15); color: #2e7d32; }
.research-tag.阳光私募 { background: rgba(34, 139, 34, .15); color: #2e7d32; }
.research-tag.其他 { background: var(--bg-pattern); color: var(--text-muted); }
.research-meta {
  font-size: 11px; color: var(--text-soft); line-height: 1.5;
}
.research-meta .label { color: var(--text-muted); margin-right: 4px; }

/* ========= 折叠表格 ========= */
.data-fold { margin: 10px 0; border: 1px solid var(--line); border-radius: 12px;
             background: var(--bg-pattern); overflow: hidden; }
.data-fold > summary {
  cursor: pointer; padding: 12px 16px; font-size: 13px; font-weight: 700;
  color: var(--text-soft); user-select: none; list-style: none;
  display: flex; align-items: center; gap: 10px;
  background: linear-gradient(90deg, var(--bg-pattern) 0%, transparent 100%);
}
.data-fold > summary::before {
  content: "❖"; font-size: 11px; color: var(--gold);
  transition: transform .2s;
}
.data-fold[open] > summary::before { transform: rotate(90deg); color: var(--primary); }
.data-fold > summary::-webkit-details-marker { display: none; }
.data-fold[open] > summary { border-bottom: 2px solid var(--gold-light); background: #fff; }
.table-wrap { padding: 6px 14px 14px; max-height: 480px; overflow: auto; background: #fff; }
.table-wrap:empty::before {
  content: "（暂无数据，喜事在路上）"; color: var(--text-muted); font-size: 12px;
  display: block; padding: 14px; font-family: "STKaiti", serif;
}
table { border-collapse: collapse; width: 100%; font-size: 12px;
        font-variant-numeric: tabular-nums; }
th, td { border-bottom: 1px dashed var(--line-soft);
         padding: 7px 12px; text-align: left; white-space: nowrap;
         max-width: 360px; overflow: hidden; text-overflow: ellipsis; }
th {
  background: linear-gradient(180deg, var(--primary-dark) 0%, var(--primary) 100%);
  position: sticky; top: 0; color: var(--gold-bright);
  font-weight: 700; font-size: 11px; letter-spacing: 1px;
  border-bottom: 2px solid var(--gold); z-index: 1;
}
tr:hover td { background: rgba(255, 224, 102, .14); }
td.num { text-align: right; font-family: "JetBrains Mono", "Consolas", monospace; font-weight: 600; }
td.num.rise { color: var(--rise); }
td.num.fall { color: var(--fall); }
td a { color: var(--primary); text-decoration: none; font-weight: 500; }
td a:hover { color: var(--primary-dark); text-decoration: underline; }

/* ========= 福气页脚 ========= */
footer {
  max-width: 1400px; margin: 0 auto; padding: 24px 5vw 36px;
  font-size: 12px; color: var(--text-muted);
  display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;
  border-top: 2px dashed var(--gold-light); margin-top: 24px;
}
footer .blessing {
  width: 100%; text-align: center; font-family: "STKaiti", serif;
  font-size: 14px; color: var(--primary); margin-bottom: 8px;
  letter-spacing: 4px; font-weight: 700;
}

@media (max-width: 768px) {
  header.hero { padding: 28px 4vw 86px; }
  header.hero::after { width: 64px; height: 64px; font-size: 11px; right: 12px; top: 12px; }
  .hero-title { font-size: 22px; }
  .kpi-value { font-size: 18px; }
  .grid-2 { grid-template-columns: 1fr; }
  .chart-box { height: 300px !important; }
  .strategy-grid { grid-template-columns: 1fr; }
  .profile-grid { grid-template-columns: 1fr; }
  .profile-business { font-size: 18px; }
  .profile-card::after { font-size: 60px; }
}
"""


JS = r"""
const PAYLOAD = JSON.parse(document.getElementById("payload").textContent);
const BLOCKS = PAYLOAD.blocks;
const colors = {
  rise: "#c8102e", fall: "#16a34a", primary: "#c8102e", gold: "#d4a017", goldLight: "#f6c94c", muted: "#a8714a",
  series: ["#c8102e", "#d4a017", "#8b0000", "#16a34a", "#dc2626", "#f59e0b", "#a16207", "#7c2d12"]
};

// ----------- 工具函数 -----------
const fmtNum = (v, digits = 2) => {
  if (v === null || v === undefined || v === "" || Number.isNaN(+v)) return "--";
  const n = Number(v);
  if (!isFinite(n)) return "--";
  if (Math.abs(n) >= 1e8) return (n/1e8).toFixed(digits) + " 亿";
  if (Math.abs(n) >= 1e4) return (n/1e4).toFixed(digits) + " 万";
  return n.toLocaleString("zh-CN", { maximumFractionDigits: digits });
};
const fmtPct = v => {
  if (v === null || v === undefined || v === "" || Number.isNaN(+v)) return "--";
  return (+v).toFixed(2) + "%";
};

// ----------- 表格渲染 -----------
function renderTable(elId, rows, opts = {}) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!rows || rows.length === 0) { el.innerHTML = ""; return; }
  const cols = opts.cols || Object.keys(rows[0]);
  const numCols = new Set(opts.numCols || []);
  const colorCols = new Set(opts.colorCols || []);
  const linkCols = opts.linkCols || {};
  let html = '<table><thead><tr>';
  cols.forEach(c => html += `<th>${escapeHtml(c)}</th>`);
  html += '</tr></thead><tbody>';
  rows.slice(0, opts.maxRows || 500).forEach(row => {
    html += '<tr>';
    cols.forEach(c => {
      let v = row[c];
      let cls = "";
      let display = v == null ? "" : String(v);
      if (numCols.has(c) && typeof v === "number") {
        display = v.toLocaleString("zh-CN", { maximumFractionDigits: 4 });
        cls = "num";
      }
      if (colorCols.has(c) && typeof v === "number") {
        cls = "num " + (v > 0 ? "rise" : v < 0 ? "fall" : "");
        if (c.includes("幅") || c.includes("率") || c.includes("%")) {
          display = (v > 0 ? "+" : "") + v.toFixed(2) + "%";
        } else {
          display = (v > 0 ? "+" : "") + fmtNum(v, 2);
        }
      }
      if (linkCols[c] && row[linkCols[c]]) {
        display = `<a href="${escapeAttr(row[linkCols[c]])}" target="_blank" rel="noreferrer">${escapeHtml(display)}</a>`;
        html += `<td class="${cls}">${display}</td>`;
      } else {
        html += `<td class="${cls}">${escapeHtml(display)}</td>`;
      }
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  if (rows.length > (opts.maxRows || 500)) {
    html += `<div style="text-align:center; padding: 8px; color: var(--text-muted); font-size: 12px;">仅显示前 ${opts.maxRows||500} 行（共 ${rows.length} 行）</div>`;
  }
  el.innerHTML = html;
}

const escapeHtml = s => String(s).replace(/[<>&"']/g, c => ({
  "<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;","'":"&#39;"
}[c]));
const escapeAttr = s => String(s).replace(/"/g, "&quot;");

// ----------- ECharts 公共配置 -----------
const baseGrid = { left: 60, right: 16, top: 32, bottom: 40, containLabel: false };

// ----------- 1. K 线图（日 K + 成交量） -----------
function renderKline() {
  const data = BLOCKS.kline_daily || [];
  if (!data.length) return;
  const dates = data.map(d => (d.date || "").substring(0, 10));
  const ohlc = data.map(d => [+d.open, +d.close, +d.low, +d.high]);
  const volumes = data.map((d, i) => [i, +d.volume, ohlc[i][1] >= ohlc[i][0] ? 1 : -1]);
  const ma = (n) => dates.map((_, i) => {
    if (i < n - 1) return null;
    const sum = data.slice(i - n + 1, i + 1).reduce((a, b) => a + +b.close, 0);
    return +(sum / n).toFixed(2);
  });

  echarts.init(document.getElementById("chart-kline")).setOption({
    animation: false,
    legend: { data: ["日K", "MA5", "MA20", "MA60"], top: 4 },
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 60, right: 20, top: 36, height: "62%" },
      { left: 60, right: 20, top: "76%", height: "16%" }
    ],
    xAxis: [
      { type: "category", data: dates, scale: true, boundaryGap: false,
        axisLine: { onZero: false }, splitLine: { show: false }, axisLabel: { fontSize: 10 } },
      { type: "category", gridIndex: 1, data: dates, axisLabel: { show: false }, axisTick: { show: false } }
    ],
    yAxis: [
      { scale: true, splitLine: { lineStyle: { color: "#eee" } }, axisLabel: { fontSize: 10 } },
      { gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } }
    ],
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1], start: 80, end: 100 },
      { type: "slider", xAxisIndex: [0, 1], top: "94%", height: 20, start: 80, end: 100 }
    ],
    series: [
      { name: "日K", type: "candlestick", data: ohlc,
        itemStyle: { color: colors.rise, color0: colors.fall,
                     borderColor: colors.rise, borderColor0: colors.fall } },
      { name: "MA5", type: "line", data: ma(5), smooth: true, symbol: "none",
        lineStyle: { width: 1.4, color: "#d4a017" } },
      { name: "MA20", type: "line", data: ma(20), smooth: true, symbol: "none",
        lineStyle: { width: 1.4, color: "#8b0000" } },
      { name: "MA60", type: "line", data: ma(60), smooth: true, symbol: "none",
        lineStyle: { width: 1.4, color: "#a16207" } },
      { name: "成交量", type: "bar", xAxisIndex: 1, yAxisIndex: 1,
        data: volumes,
        itemStyle: { color: p => p.data[2] > 0 ? colors.rise : colors.fall } }
    ]
  });
}

// ----------- 2. 1 分钟分时 -----------
function renderMinute() {
  const data = BLOCKS.kline_minute || [];
  if (!data.length) return;
  const times = data.map(d => (d.day || "").substring(5));
  const closes = data.map(d => +d.close);
  echarts.init(document.getElementById("chart-minute")).setOption({
    animation: false,
    title: { text: `${data.length} 个 1 分钟点（含最近 5 个交易日）`, textStyle: { fontSize: 12, fontWeight: 500, color: "#5b6878" }, left: 0, top: 0 },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: times, axisLabel: { fontSize: 10 } },
    yAxis: { scale: true, axisLabel: { fontSize: 10 } },
    series: [{
      type: "line", data: closes, smooth: false, symbol: "none",
      areaStyle: { color: "rgba(200,16,46,.12)" }, lineStyle: { color: colors.primary, width: 1.8 }
    }]
  });
}

// ----------- 3. 资金流向 -----------
function renderFundFlow() {
  const data = (BLOCKS.fund_flow || []).slice().reverse();  // 时间正序
  if (!data.length) return;
  const dates = data.map(d => d["日期"]);
  const main = data.map(d => +d["主力净流入-净额"]);
  const huge = data.map(d => +d["超大单净流入-净额"]);
  const big = data.map(d => +d["大单净流入-净额"]);
  const med = data.map(d => +d["中单净流入-净额"]);
  const small = data.map(d => +d["小单净流入-净额"]);

  echarts.init(document.getElementById("chart-fund")).setOption({
    animation: false,
    legend: { data: ["主力净流入", "超大单", "大单", "中单", "小单"], top: 4, textStyle: { fontSize: 11 } },
    tooltip: { trigger: "axis", valueFormatter: v => fmtNum(v) },
    grid: { left: 70, right: 20, top: 34, bottom: 50 },
    xAxis: { type: "category", data: dates, axisLabel: { fontSize: 10 } },
    yAxis: { type: "value", axisLabel: { formatter: v => fmtNum(v, 0), fontSize: 10 } },
    dataZoom: [{ type: "inside", start: 60, end: 100 }, { type: "slider", height: 20, bottom: 16, start: 60, end: 100 }],
    series: [
      { name: "主力净流入", type: "line", data: main, smooth: true, symbol: "none",
        lineStyle: { color: colors.primary, width: 2 },
        markLine: { symbol: "none", lineStyle: { color: colors.muted, type: "dashed" }, data: [{ yAxis: 0 }] } },
      { name: "超大单", type: "bar", stack: "fund", data: huge, itemStyle: { color: "#c8102e" } },
      { name: "大单", type: "bar", stack: "fund", data: big, itemStyle: { color: "#d4a017" } },
      { name: "中单", type: "bar", stack: "fund", data: med, itemStyle: { color: "#a8714a" } },
      { name: "小单", type: "bar", stack: "fund", data: small, itemStyle: { color: "#16a34a" } }
    ]
  });
}

// ----------- 4. 财务核心指标趋势（从 fin_abstract 抽取） -----------
function renderFinancial() {
  const data = BLOCKS.fin_abstract || [];
  if (!data.length) return;
  // 财务摘要表格的结构：每行是一个指标，列是各报告期日期
  const periods = Object.keys(data[0]).filter(k => /^\d{8}$/.test(k) || /^\d{4}-\d{2}-\d{2}/.test(k)).slice(0, 16).reverse();
  const wantedKeys = ["归母净利润", "营业总收入", "扣非净利润", "净资产收益率"];
  const series = [];
  wantedKeys.forEach((kw, idx) => {
    const row = data.find(r => Object.values(r).some(v => typeof v === "string" && v.includes(kw)));
    if (!row) return;
    const vals = periods.map(p => { const v = row[p]; return typeof v === "number" ? v : (parseFloat(v) || null); });
    series.push({
      name: kw, type: "line", data: vals, smooth: true, symbol: "circle", symbolSize: 5,
      lineStyle: { width: 2, color: colors.series[idx % colors.series.length] },
      itemStyle: { color: colors.series[idx % colors.series.length] }
    });
  });
  if (!series.length) return;
  echarts.init(document.getElementById("chart-fin")).setOption({
    animation: false,
    legend: { top: 4, textStyle: { fontSize: 11 } },
    tooltip: { trigger: "axis", valueFormatter: v => fmtNum(v) },
    grid: { left: 70, right: 20, top: 34, bottom: 36 },
    xAxis: { type: "category", data: periods, axisLabel: { fontSize: 10 } },
    yAxis: { type: "value", axisLabel: { formatter: v => fmtNum(v, 0), fontSize: 10 } },
    series: series
  });
}

// ----------- 5. 十大股东饼图 -----------
function renderTop10() {
  const data = BLOCKS.top10 || [];
  if (!data.length) return;
  const pieData = data.map(d => ({
    name: (d["股东名称"] || "").substring(0, 20), value: +(d["持股比例"] || d["占总股本比例"] || 0)
  })).filter(d => d.value > 0);
  echarts.init(document.getElementById("chart-top10")).setOption({
    animation: false,
    title: { text: "十大股东持股比例", left: "center", top: 4, textStyle: { fontSize: 13 } },
    tooltip: { trigger: "item", formatter: "{b}<br/>{c}% ({d}%)" },
    series: [{
      type: "pie", radius: ["32%", "62%"], center: ["50%", "55%"],
      data: pieData, label: { fontSize: 10, formatter: "{b}\n{c}%" },
      itemStyle: { borderRadius: 4, borderColor: "#fff", borderWidth: 2 }
    }]
  });
}

// ----------- 6. 股东户数趋势 -----------
function renderGdhs() {
  const data = (BLOCKS.gdhs || []).slice().reverse();
  if (!data.length) return;
  const dates = data.map(d => d["截止日期"] || d["统计日期"] || "");
  const counts = data.map(d => +d["股东户数-本次"] || +d["股东户数"] || null);
  echarts.init(document.getElementById("chart-gdhs")).setOption({
    animation: false,
    title: { text: "股东户数趋势", left: "center", top: 4, textStyle: { fontSize: 13 } },
    tooltip: { trigger: "axis", valueFormatter: v => fmtNum(v) },
    grid: { left: 70, right: 20, top: 36, bottom: 30 },
    xAxis: { type: "category", data: dates, axisLabel: { fontSize: 9, rotate: 45 } },
    yAxis: { type: "value", axisLabel: { formatter: v => fmtNum(v, 0), fontSize: 10 } },
    series: [{
      type: "line", data: counts, smooth: true, symbol: "circle", symbolSize: 4,
      lineStyle: { color: colors.primary, width: 2 }, areaStyle: { color: "rgba(200, 16, 46, .12)" }
    }]
  });
}

// ----------- 渲染所有表格 -----------
function renderAllTables() {
  renderTable("table-fund-flow", BLOCKS.fund_flow,
    { numCols: ["收盘价", "主力净流入-净额", "超大单净流入-净额", "大单净流入-净额", "中单净流入-净额", "小单净流入-净额"],
      colorCols: ["涨跌幅", "主力净流入-净占比", "超大单净流入-净占比", "大单净流入-净占比", "中单净流入-净占比", "小单净流入-净占比"] });
  renderTable("table-balance", BLOCKS.balance_sheet, { maxRows: 30 });
  renderTable("table-income", BLOCKS.income_statement, { maxRows: 30 });
  renderTable("table-cashflow", BLOCKS.cashflow, { maxRows: 30 });
  renderTable("table-fin-abstract", BLOCKS.fin_abstract, { maxRows: 80 });
  renderTable("table-fin-ths", BLOCKS.fin_indicator_ths, { maxRows: 100 });
  renderTable("table-yjyg", BLOCKS.yjyg);
  renderTable("table-yjkb", BLOCKS.yjkb);
  renderTable("table-top10", BLOCKS.top10);
  renderTable("table-top10-free", BLOCKS.top10_free);
  renderTable("table-share-hold", BLOCKS.share_hold_change);
  renderTable("table-dividend", BLOCKS.dividend);
  renderTable("table-share-alloc", BLOCKS.share_alloc);
  renderTable("table-news", BLOCKS.news, { linkCols: { "新闻标题": "新闻链接" } });
  renderTable("table-research", BLOCKS.research);
  renderTable("table-notice", BLOCKS.notice, { linkCols: { "公告标题": "网址" } });
  renderTable("table-recommend", BLOCKS.recommend);
  renderTable("table-fund-hold", BLOCKS.fund_hold);
  renderTable("table-lhb", BLOCKS.lhb);
  renderTable("table-margin", BLOCKS.margin);
  renderTable("table-release", BLOCKS.release);
  renderTable("table-basic", BLOCKS.basic_info);
  renderTable("table-share-structure", BLOCKS.share_structure);
  renderTable("table-zygc", BLOCKS.zygc);
}

// ----------- 主营构成饼图（产品 / 地区） -----------
function renderZYGC(elId, classifyType) {
  const rows = (BLOCKS.zygc || []).filter(r => r["分类类型"] === classifyType);
  if (!rows.length) return;
  // 取最近一期
  const latestDate = rows.reduce((acc, r) => r["报告日期"] > acc ? r["报告日期"] : acc, "");
  const latest = rows.filter(r => r["报告日期"] === latestDate)
                     .filter(r => +r["主营收入"] > 0)
                     .sort((a, b) => +b["主营收入"] - +a["主营收入"]);
  if (!latest.length) return;
  const pieData = latest.map(r => ({
    name: r["主营构成"], value: +r["主营收入"],
    pct: +r["收入比例"], gross: +r["毛利率"]
  }));
  const totalRev = pieData.reduce((s, x) => s + x.value, 0);
  echarts.init(document.getElementById(elId)).setOption({
    title: { text: `${latestDate} · 营收 ${fmtNum(totalRev)}`,
             left: "center", top: 8,
             textStyle: { fontSize: 12, fontWeight: 600, color: "#8b2a0e" } },
    tooltip: {
      trigger: "item",
      formatter: p => {
        const d = p.data;
        const grossStr = isFinite(d.gross) && d.gross !== 0 ? `<br/>毛利率：${(d.gross*100).toFixed(2)}%` : "";
        return `<b>${d.name}</b><br/>营收：${fmtNum(d.value)}<br/>占比：${(d.pct*100).toFixed(2)}%${grossStr}`;
      }
    },
    legend: { type: "scroll", orient: "horizontal", bottom: 0, textStyle: { fontSize: 11 } },
    color: colors.series,
    series: [{
      name: classifyType, type: "pie",
      radius: ["38%", "62%"], center: ["50%", "48%"],
      avoidLabelOverlap: true,
      label: {
        formatter: "{b}\n{d}%", fontSize: 11, fontWeight: 600,
        color: "#3a1108"
      },
      labelLine: { lineStyle: { color: "#d4a017" } },
      itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
      data: pieData
    }]
  });
}

// ----------- 历年产品营收趋势（堆积面积） -----------
function renderZYGCTrend() {
  const rows = (BLOCKS.zygc || []).filter(r => r["分类类型"] === "按产品分类");
  if (!rows.length) return;
  const dates = [...new Set(rows.map(r => r["报告日期"]))].sort();
  const products = [...new Set(rows.map(r => r["主营构成"]))];
  // 按"该产品出现次数"排序，主要业务排前面
  const productCount = Object.fromEntries(products.map(p => [p, rows.filter(r => r["主营构成"] === p).length]));
  products.sort((a, b) => productCount[b] - productCount[a]);
  const series = products.map((p, i) => ({
    name: p, type: "line", stack: "rev", smooth: true, symbol: "none",
    areaStyle: { opacity: .8 },
    lineStyle: { width: 1.5 },
    itemStyle: { color: colors.series[i % colors.series.length] },
    data: dates.map(d => {
      const row = rows.find(r => r["报告日期"] === d && r["主营构成"] === p);
      return row ? +row["主营收入"] : null;
    })
  }));
  echarts.init(document.getElementById("chart-zygc-trend")).setOption({
    grid: { left: 60, right: 24, top: 50, bottom: 40 },
    tooltip: { trigger: "axis", valueFormatter: fmtNum },
    legend: { type: "scroll", top: 6, textStyle: { fontSize: 11 } },
    xAxis: { type: "category", data: dates, axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: "value", axisLabel: { formatter: v => fmtNum(v, 1), fontSize: 10 } },
    series: series
  });
}

// ----------- 业务关键词云 v3（白名单 + 严格分词 + 明星词） -----------
const BIZ_WHITELIST = [
  // AI / 算力 / 大模型
  "AI算力","算力","大模型","训推一体机","一体机","推理","训练","训推","DeepSeek","ChatGPT",
  "通用人工智能","AGI","AIGC","千问","文心","盘古","豆包","Sora","多模态","具身智能",
  // 信创 / 国产替代 / 自主可控
  "信创","行业信创","党政信创","国产替代","自主可控","国产化","国家队","央企","国资",
  "国企改革","专精特新","小巨人","新质生产力","数字经济","东数西算","数据要素","算力网络",
  // 半导体 / 硬件 / 计算
  "半导体","芯片","存储","封测","光刻","设备","光模块","液冷","服务器","PC","笔电",
  "国产芯片","昇腾","鲲鹏","海光","龙芯","兆芯","飞腾","鹏腾","RISC-V","计算产业","系统装备",
  "训推一体","算力底座","X86","ARM","CPU","GPU","DCU",
  // 新能源
  "光伏","风电","储能","锂电","电池","电解液","正极","负极","隔膜","钠电池",
  "氢能","固态电池","硅料","组件","逆变器","HJT","TOPCon","BC电池",
  // 汽车
  "新能源车","智能驾驶","自动驾驶","智能座舱","车规","激光雷达","800V","域控","线控",
  "整车","零部件","新势力","出海",
  // 医药 / 创新药
  "创新药","CXO","医美","集采","医保","出海授权","license-out","BD","临床",
  "ADC","GLP-1","CAR-T","双抗","减肥药","创新医疗器械",
  // 游戏 / 传媒（重点补强）
  "游戏","手游","端游","网游","页游","网络游戏","移动游戏","休闲游戏",
  "新游","老游","买量","流水","版号","自研","代理发行","出海","海外",
  "电竞","二次元","IP","短剧","小游戏","Mini游戏","卡牌","SLG","RPG","MMO","FPS","MOBA",
  "新游表现","新游储备","新游上线","存量","流水曲线","ARPU","LTV","回本",
  // 互联网 / 传媒 / 内容
  "信息流","短视频","直播","私域","广告","社交","电商","内容","UGC","PGC",
  "影视","动漫","音乐","VR","AR","元宇宙","虚拟人","数字人","AI游戏","AI 游戏","AIGC",
  // 消费 / 必选
  "白酒","啤酒","调味品","乳制品","免税","旅游","出行","纺服","国货","谷子",
  "餐饮","食品","饮料","奶粉","母婴","休闲零食","次新","品牌升级",
  // 金融地产
  "保险","券商","银行","房地产","物业","REITs","保障性住房","城中村",
  "股息率","派息","分红率","高分红","季度分红","中期分红",
  // 主题概念
  "机器人","人形机器人","低空经济","商业航天","卫星互联网","元宇宙","脑机接口",
  "可控核聚变","量子","6G","车路云","高股息","红利","央国企","并购重组",
  "并购","重组","回购","股权激励","分拆上市","IPO","定增",
  // 财务 / 业绩
  "业绩超预期","业绩预增","扭亏","减亏","并表","商誉减值","订单","在手订单",
  "毛利率","净利率","ROE","现金流","收入增长","利润释放","降本增效",
  // 操作建议 / 评级
  "首次覆盖","维持买入","上调评级","目标价","催化剂","拐点","底部","龙头","卡位",
  // 业务通用词（中性但有价值）
  "聚焦主业","核心业务","研发投入","产能扩张","技术迭代","生态建设","客户拓展",
  "市占率","行业龙头","稀缺标的"
];

function extractKeywords(text) {
  // ========= 严格停用词（含标点黏连产生的高频垃圾） =========
  const stopwords = new Set([
    // 套话
    "公司","业绩","业务","点评","研报","报告","年报","季报","半年报","快报","事件","深度",
    "中报","年度","季度","上半年","下半年","三季","二季","首季","简评","专题","季报点评",
    "事件点评","公司事件","公司信息","信息更新","更新报告","系列报告","点评报告","三季报",
    "一季报","半年报点评","年报点评",
    // 修饰词
    "增长","下降","回升","承压","改善","稳定","上行","下行","核心","主业","聚焦","推出",
    "持续","明显","暂时","预计","预期","值得","期待","可期","布局","加速","深化","释放","深耕",
    "拐点","积极","良好","显著","略有","维持","推荐","买入","增持","看好","观点","跟踪",
    "调研","纪要","公告","披露","发布","公布","召开","完成","通过","签署","签订","实现",
    "推动","加快","抓住","紧抓","引领","开启","保持","创新","升级","优化","提升","增强",
    "推进","静待","受益","回暖","助力","长期","发展","更新","系列","信息","大幅","净利润",
    "营业","主要","下游","上游","本期","小幅","稳步","平稳","受到","致力","助推","巩固",
    // 太宽泛
    "营收","收入","利润","毛利","净利","生态","产品","研发","技术","产业","市场","客户",
    "项目","订单","主要","目前","未来","近期","当前","新品","行业","领域","空间","机遇",
    "前景","机会","趋势","格局","逻辑","趋势","环境","背景","展望","观察","思考",
    // 评级动作
    "首次","覆盖","上调","下调","目标","评级","建议","策略",
    // 虚词
    "及","和","与","的","了","在","已","等","为","是","有","并","以","将","对","从",
    "或","但","若","如","还","再","也","其","能","可","可能","或将","有望","拟","预",
    // 时间
    "季","年","月","日","上半","下半","本季","本年","全年","一二三四"
  ]);

  // ========= isJunk: 严格垃圾判定 =========
  const isJunk = w => {
    if (!w) return true;
    if (w.length < 2 || w.length > 8) return true;
    if (stopwords.has(w)) return true;
    if (/^[\d.\-+%]+$/.test(w)) return true;             // 纯数字/百分号
    if (/^20\d\d年?$/.test(w)) return true;              // 年份
    if (/^[12]?\d月$/.test(w)) return true;              // 月份
    if (/^[一二三四]季报?$/.test(w)) return true;         // 季度
    if (/^[HQ][1-4]$/i.test(w)) return true;            // H1/Q1
    if (/[，,。.！!？?；;：:""''《》（）()【】\s]/.test(w)) return true; // 含任意标点空白
    // 仅 1 个有意义的中文字 + 修饰
    if (/^[，。！？]/.test(w) || /[，。！？]$/.test(w)) return true;
    return false;
  };

  // ========= 1. 白名单匹配（直接 regex 在原文搜，不依赖分词） =========
  const wlHit = {};
  for (const w of BIZ_WHITELIST) {
    const re = new RegExp(w.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&"), "gi");
    const matches = text.match(re);
    if (matches) wlHit[w] = (wlHit[w] || 0) + matches.length;
  }

  // ========= 2. 严格清洗：把所有标点 → 空格，再分词 =========
  // 拆成多次 replace 以避免 character class 中出现连续三引号导致 Python r-string 误闭合
  const cleaned = text
    .replace(/[\u3000-\u303f]/g, " ")        // CJK 标点（、。《》「」『』〔〕等）
    .replace(/[\uff00-\uffef]/g, " ")        // 全角 ASCII（，。！？；：等）
    .replace(/[\u2000-\u206f]/g, " ")        // 通用标点（""''—…等）
    .replace(/[!"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]/g, " ")  // ASCII 标点
    .replace(/\d+[年月日季度]/g, " ")          // "2023年"、"3月"
    .replace(/\s+/g, " ").trim();

  // ========= 3. 分词 + n-gram =========
  let segs = [];
  if (typeof Intl !== "undefined" && typeof Intl.Segmenter === "function") {
    const seg = new Intl.Segmenter("zh", { granularity: "word" });
    segs = [...seg.segment(cleaned)]
      .filter(s => s.isWordLike)
      .map(s => s.segment.trim())
      .filter(w => w);
  } else {
    segs = cleaned.split(/\s+/).filter(Boolean);
  }

  const ngrams = {};
  for (let i = 0; i < segs.length; i++) {
    const w = segs[i];
    if (!isJunk(w)) ngrams[w] = (ngrams[w] || 0) + 1;
    if (i + 1 < segs.length) {
      const a = segs[i], b = segs[i + 1], ab = a + b;
      if (!isJunk(ab) && !isJunk(a) && !isJunk(b)) {
        ngrams[ab] = (ngrams[ab] || 0) + 1;
      }
    }
  }

  // ========= 4. 合并：白名单不被覆盖 =========
  const merged = Object.assign({}, wlHit);
  for (const [w, c] of Object.entries(ngrams)) {
    if (c >= 3 && !(w in merged) && !isJunk(w)) merged[w] = c;
  }

  // ========= 5. 子串吸收（短词频次扣除被长词覆盖的次数） =========
  const sortedByLen = Object.entries(merged).sort((a, b) => b[0].length - a[0].length);
  const subtract = {};
  for (let i = 0; i < sortedByLen.length; i++) {
    const [longer, lc] = sortedByLen[i];
    for (let j = i + 1; j < sortedByLen.length; j++) {
      const [shorter] = sortedByLen[j];
      if (longer !== shorter && longer.includes(shorter)) {
        subtract[shorter] = (subtract[shorter] || 0) + lc;
      }
    }
  }
  const final = sortedByLen
    .map(([w, c]) => [w, Math.max(0, c - (subtract[w] || 0))])
    .filter(([w, c]) => c >= 2 && !isJunk(w))
    .sort((a, b) => b[1] - a[1]);

  return final.slice(0, 50);
}

function renderWordCloud() {
  const el = document.getElementById("word-cloud");
  if (!el) return;
  const titles = (BLOCKS.research || []).map(r => r["报告名称"] || "").join("  ");
  if (!titles.trim()) {
    el.innerHTML = '<div style="color:var(--text-muted); font-size:12px;">暂无研报数据，无法抽取关键词</div>';
    return;
  }
  const arr = extractKeywords(titles);
  if (!arr.length) {
    el.innerHTML = '<div style="color:var(--text-muted); font-size:12px;">研报标题中未提取到高频词</div>';
    return;
  }
  const maxC = arr[0][1];
  // Top 3 = 明星词；Top 4-10 = hot；11-25 = warm；其余 normal
  const stars = arr.slice(0, 3);
  const hots = arr.slice(3, 10);
  const warms = arr.slice(10, 25);
  const cools = arr.slice(25);

  let html = "";
  // 明星词：大字号 + 红金渐变 + 序号
  html += '<div class="wc-stars">';
  stars.forEach(([w, c], i) => {
    html += `<div class="wc-star wc-star-${i + 1}">
      <span class="wc-rank">#${i + 1}</span>
      <span class="wc-word">${w}</span>
      <span class="wc-count">${c} 次</span>
    </div>`;
  });
  html += "</div>";

  // 主词云
  html += '<div class="wc-main">';
  const renderTag = ([w, c], cls) => {
    const ratio = c / maxC;
    const fs = (12 + ratio * 14).toFixed(0);
    return `<span class="${cls}" style="font-size:${fs}px;" title="共出现 ${c} 次">${w}<span class="wc-badge">${c}</span></span>`;
  };
  hots.forEach(item => html += renderTag(item, "wc-tag hot"));
  warms.forEach(item => html += renderTag(item, "wc-tag warm"));
  cools.forEach(item => html += renderTag(item, "wc-tag"));
  html += "</div>";

  // 底部统计
  const total = arr.reduce((s, [, c]) => s + c, 0);
  html += `<div class="wc-footer">从 ${BLOCKS.research?.length || 0} 篇研报标题中识别 ${arr.length} 个关键词（共出现 ${total} 次）</div>`;

  el.innerHTML = html;
}

// ----------- 9. 北向资金 -----------
function renderNorthbound() {
  const raw = (BLOCKS.northbound || []).slice();
  const kpiEl = document.getElementById("kpi-northbound");
  if (!raw.length) {
    if (kpiEl) kpiEl.innerHTML = '<div class="kpi-card"><div class="kpi-label">提示</div><div class="kpi-value" style="font-size:14px;">该股暂未纳入陆股通持股名单</div></div>';
    return;
  }
  const data = raw.slice().sort((a, b) =>
    String(a["持股日期"] || "").localeCompare(String(b["持股日期"] || ""))
  );
  const dates = data.map(d => d["持股日期"] || "");
  const pct   = data.map(d => +d["持股数量占A股百分比"] || null);
  const close = data.map(d => +d["当日收盘价"] || null);
  const mv    = data.map(d => (+d["持股市值"] || 0) / 1e8);  // 亿元
  const flow  = data.map(d => (+d["今日增持资金"] || 0) / 1e4);  // 万元

  // KPI
  const last = data[data.length - 1] || {};
  const lastPct  = +last["持股数量占A股百分比"] || 0;
  const lastMv   = (+last["持股市值"] || 0) / 1e8;
  const peakPct  = Math.max(...pct.filter(x => x !== null && !isNaN(x)));
  const sum30Flow = data.slice(-30).reduce((s, d) => s + (+d["今日增持资金"] || 0), 0) / 1e8;
  const tradingDays = data.length;
  if (kpiEl) {
    const dirCls = sum30Flow >= 0 ? "rise" : "fall";
    kpiEl.innerHTML = `
      <div class="kpi-card accent">
        <div class="kpi-label">最新持股占比</div>
        <div class="kpi-value">${lastPct.toFixed(2)}%</div>
        <div class="kpi-sub">${last["持股日期"] || ""}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">最新持股市值</div>
        <div class="kpi-value">${lastMv.toFixed(2)} 亿</div>
        <div class="kpi-sub">收盘价 ${(+last["当日收盘价"] || 0).toFixed(2)}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">历史最高占比</div>
        <div class="kpi-value">${peakPct.toFixed(2)}%</div>
        <div class="kpi-sub">${tradingDays} 个交易日内</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">近 30 日净增持</div>
        <div class="kpi-value ${dirCls}">${sum30Flow >= 0 ? "+" : ""}${sum30Flow.toFixed(2)} 亿</div>
        <div class="kpi-sub">${sum30Flow >= 0 ? "外资在加仓" : "外资在减仓"}</div>
      </div>`;
  }

  // 主图：持股占比 + 股价 + 持股市值
  const c1 = document.getElementById("chart-northbound");
  if (c1) {
    echarts.init(c1).setOption({
      animation: false,
      title: { text: "陆股通持股占比 / 股价 / 持股市值", left: "center", top: 4, textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis", valueFormatter: v => v == null ? "—" : (typeof v === "number" ? v.toFixed(3) : v) },
      legend: { top: 28, textStyle: { fontSize: 11 }, icon: "roundRect" },
      grid: { left: 60, right: 60, top: 64, bottom: 36 },
      xAxis: { type: "category", data: dates, axisLabel: { fontSize: 9 } },
      yAxis: [
        { type: "value", name: "占比 / 股价", position: "left",
          axisLabel: { formatter: "{value}", fontSize: 10 } },
        { type: "value", name: "市值(亿)", position: "right",
          axisLabel: { formatter: v => v.toFixed(0), fontSize: 10 } },
      ],
      series: [
        { name: "持股占比%", type: "line", yAxisIndex: 0, data: pct,
          smooth: true, symbol: "none",
          lineStyle: { color: colors.primary, width: 2 },
          areaStyle: { color: "rgba(200, 16, 46, .12)" } },
        { name: "收盘价", type: "line", yAxisIndex: 0, data: close,
          smooth: true, symbol: "none",
          lineStyle: { color: colors.gold, width: 1.5, type: "dashed" } },
        { name: "持股市值(亿)", type: "line", yAxisIndex: 1, data: mv,
          smooth: true, symbol: "none",
          lineStyle: { color: "#2563eb", width: 1.5 } },
      ],
      dataZoom: [{ type: "inside", start: Math.max(0, 100 - 100 * 250 / Math.max(dates.length, 1)), end: 100 }],
    });
  }

  // 副图：每日净增持金额柱状（红涨绿跌反转色：买入红、卖出绿）
  const c2 = document.getElementById("chart-northbound-flow");
  if (c2) {
    echarts.init(c2).setOption({
      animation: false,
      title: { text: "陆股通日度净增持资金（万元）", left: "center", top: 4, textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis", valueFormatter: v => v == null ? "—" : (+v).toFixed(0) + " 万" },
      grid: { left: 70, right: 20, top: 36, bottom: 30 },
      xAxis: { type: "category", data: dates, axisLabel: { fontSize: 9 } },
      yAxis: { type: "value", axisLabel: { fontSize: 10 } },
      series: [{
        type: "bar", data: flow,
        itemStyle: {
          color: p => p.value >= 0 ? colors.primary : colors.green || "#16a34a",
        },
      }],
      dataZoom: [{ type: "inside", start: Math.max(0, 100 - 100 * 90 / Math.max(dates.length, 1)), end: 100 }],
    });
  }
}

// ----------- 10. 机构调研 -----------
function renderResearchField() {
  const data = (BLOCKS.research_field || []).slice();
  const kpiEl = document.getElementById("kpi-research-field");
  const listEl = document.getElementById("research-field-list");
  const chartEl = document.getElementById("chart-research-field-type");

  if (!data.length) {
    if (kpiEl) kpiEl.innerHTML = '<div class="kpi-card"><div class="kpi-label">最近 21 日</div><div class="kpi-value" style="font-size:14px;">暂无机构调研记录</div></div>';
    if (listEl) listEl.innerHTML = "";
    if (chartEl) chartEl.style.display = "none";
    return;
  }

  // KPI 统计
  const totalEvents = data.length;
  const orgs = new Set(data.map(d => d["调研机构"] || "")), uniqOrg = orgs.size;
  const types = {};
  data.forEach(d => {
    const t = d["机构类型"] || "其他";
    types[t] = (types[t] || 0) + 1;
  });
  const topType = Object.entries(types).sort((a, b) => b[1] - a[1])[0] || ["—", 0];
  const dateSet = new Set(data.map(d => d["调研日期"] || ""));
  const earliestDate = [...dateSet].sort()[0] || "";
  const latestDate = [...dateSet].sort().slice(-1)[0] || "";

  if (kpiEl) {
    kpiEl.innerHTML = `
      <div class="kpi-card accent">
        <div class="kpi-label">调研次数</div>
        <div class="kpi-value">${totalEvents}</div>
        <div class="kpi-sub">最近 21 日</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">参与机构数</div>
        <div class="kpi-value">${uniqOrg}</div>
        <div class="kpi-sub">去重后机构数量</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">主力调研方</div>
        <div class="kpi-value" style="font-size:16px;">${topType[0]}</div>
        <div class="kpi-sub">${topType[1]} 次（占 ${(topType[1] / totalEvents * 100).toFixed(0)}%）</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">调研日期跨度</div>
        <div class="kpi-value" style="font-size:13px;">${earliestDate}<br/>~ ${latestDate}</div>
        <div class="kpi-sub">${dateSet.size} 个交易日</div>
      </div>`;
  }

  // 机构类型饼图
  if (chartEl) {
    chartEl.style.display = "";
    const pieData = Object.entries(types).map(([k, v]) => ({ name: k, value: v }));
    echarts.init(chartEl).setOption({
      animation: false,
      title: { text: "调研机构类型分布", left: "center", top: 4, textStyle: { fontSize: 13 } },
      tooltip: { trigger: "item", formatter: "{b}<br/>{c} 次 ({d}%)" },
      legend: { bottom: 4, textStyle: { fontSize: 11 } },
      series: [{
        type: "pie", radius: ["38%", "65%"], center: ["50%", "50%"],
        data: pieData, label: { fontSize: 11, formatter: "{b}\n{c}次" },
        itemStyle: { borderRadius: 4, borderColor: "#fff", borderWidth: 2 },
        color: [colors.primary, colors.gold, "#2563eb", "#16a34a", "#9333ea", "#94a3b8"],
      }],
    });
  }

  // 时间线列表
  if (listEl) {
    let html = "";
    data.forEach(d => {
      const date = d["调研日期"] || "";
      const org = d["调研机构"] || "—";
      const type = d["机构类型"] || "其他";
      const way = d["接待方式"] || "";
      const recv = d["接待人员"] || "";
      const place = d["接待地点"] || "";
      const tagCls = ["证券公司", "基金公司", "私募基金", "阳光私募"].includes(type) ? type : "其他";
      html += `<div class="research-item">
        <div class="research-date">${date}${d["公告日期"] && d["公告日期"] !== date ? ` · 公告 ${d["公告日期"]}` : ""}</div>
        <div class="research-org">${org} <span class="research-tag ${tagCls}">${type}</span></div>
        <div class="research-meta">
          ${way ? `<span class="label">📞 接待:</span>${way}　` : ""}
          ${recv ? `<span class="label">👥 接待人:</span>${recv}` : ""}
          ${place ? `　<span class="label">📍 地点:</span>${place}` : ""}
        </div>
      </div>`;
    });
    listEl.innerHTML = html;
  }
}

// ----------- 启动 -----------
window.addEventListener("DOMContentLoaded", () => {
  try { renderKline(); } catch (e) { console.error("kline:", e); }
  try { renderMinute(); } catch (e) { console.error("minute:", e); }
  try { renderFundFlow(); } catch (e) { console.error("fund:", e); }
  try { renderFinancial(); } catch (e) { console.error("fin:", e); }
  try { renderTop10(); } catch (e) { console.error("top10:", e); }
  try { renderGdhs(); } catch (e) { console.error("gdhs:", e); }
  try { renderZYGC("chart-zygc-product", "按产品分类"); } catch (e) { console.error("zygc-product:", e); }
  try { renderZYGC("chart-zygc-region", "按地区分类"); } catch (e) { console.error("zygc-region:", e); }
  try { renderZYGCTrend(); } catch (e) { console.error("zygc-trend:", e); }
  try { renderWordCloud(); } catch (e) { console.error("wordcloud:", e); }
  try { renderNorthbound(); } catch (e) { console.error("northbound:", e); }
  try { renderResearchField(); } catch (e) { console.error("research_field:", e); }
  try { renderAllTables(); } catch (e) { console.error("tables:", e); }
});
window.addEventListener("resize", () => {
  document.querySelectorAll(".chart-box").forEach(box => {
    const inst = echarts.getInstanceByDom(box);
    if (inst) inst.resize();
  });
});
"""


# ============================================================
#  主入口
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="个股全维度 HTML 报告（akshare 版）")
    parser.add_argument("code", nargs="?", help="6 位 A 股代码")
    parser.add_argument("-o", "--out-dir",
                        default=os.path.dirname(os.path.abspath(__file__)),
                        help="HTML 输出目录（默认为脚本同目录）")
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

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"stock_report_{code}.html")
    html_text = render_html(data)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_text)
    print(f"📄 报告已生成：{out_path}")
    print(f"   文件大小：{os.path.getsize(out_path)/1024:.1f} KB")

    # Also save raw JSON for gen_html.py (Phase 3)
    json_path = os.path.join(out_dir, "output", f"data_{code}.json")
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
