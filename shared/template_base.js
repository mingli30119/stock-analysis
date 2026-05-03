/* 个股深度研报 · JavaScript 模板 v2.2 */
/* 使用方式：AI 手写 HTML 时，复制此文件全部内容到 <script> 标签内 */
/* 数据注入点（2处）：① rawData 数组  ② renderPie() 中的 pieData */
/* ⚠️ OHLC 格式：[open, close, low, high] — 从原始 [date,open,high,low,close,vol] 转换 */

(function() {
const rawData = __RAW_DATA_ARRAY__;

// ── 数据处理（无需修改）──
const dates = [], ohlc = [], volumesRaw = [];
rawData.forEach(d => {
  dates.push(d[0]);
  ohlc.push([d[1], d[4], d[3], d[2]]);  // [open, close, low, high]
  volumesRaw.push(d[5]);
});
const closes = ohlc.map(d => d[1]);
const calcMA = (arr, n) => arr.map((_, i) => {
  if (i < n - 1) return null;
  let sum = arr.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0);
  return +(sum / n).toFixed(2);
});
const ma5 = calcMA(closes, 5), ma20 = calcMA(closes, 20), ma60 = calcMA(closes, 60);
const volumes = volumesRaw.map(v => +(v / 10000).toFixed(2));
const dateLabels = dates.map(d => { const parts = d.split('-'); return parts[1] + '-' + parts[2]; });

// ── 主题色获取 ──
function getThemeColors() {
  const isLight = document.body.classList.contains('light-mode');
  return {
    textColor: isLight ? '#2a1f12' : '#e8e9ec',
    textSecondary: isLight ? '#6b5634' : '#b0b3be',
    textMuted: isLight ? '#9c8b6e' : '#7a7d8a',
    upColor: isLight ? '#dc2626' : '#f55656',
    downColor: isLight ? '#16a34a' : '#28c75b',
    ma5Color: isLight ? '#2563eb' : '#4a90d9',
    ma20Color: isLight ? '#16a34a' : '#28c75b',
    ma60Color: isLight ? '#c2410c' : '#e8923a',
    volUpColor: isLight ? 'rgba(220,38,38,0.25)' : 'rgba(245,86,86,0.35)',
    volDownColor: isLight ? 'rgba(22,163,74,0.25)' : 'rgba(40,199,91,0.35)',
  };
}

// ── 饼图渲染 ──
let pieChart, klineChart;
function renderPie() {
  if (pieChart) pieChart.dispose();
  pieChart = echarts.init(document.getElementById('chart-business-pie'));
  const c = getThemeColors();
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {d}% (营收{c}亿)' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      data: __PIE_DATA_ARRAY__,
      label: { fontSize: 11, color: c.textSecondary },
      color: ['#f55656', '#d4a853', '#e8923a', '#4a90d9', '#e3c26d']
    }]
  });
}

// ── K线图渲染 ──
function renderKline() {
  if (klineChart) klineChart.dispose();
  klineChart = echarts.init(document.getElementById('chart-kline-full'));
  const c = getThemeColors();
  const volData = volumes.map((v, i) => ({
    value: v,
    itemStyle: { color: ohlc[i][1] >= ohlc[i][0] ? c.volUpColor : c.volDownColor }
  }));
  klineChart.setOption({
    grid: [
      { left: '9%', right: '6%', top: '12%', height: '55%' },
      { left: '9%', right: '6%', top: '74%', height: '14%' }
    ],
    xAxis: [
      { type: 'category', data: dateLabels, gridIndex: 0,
        axisLabel: { color: c.textMuted, fontSize: 9, interval: 5 },
        axisLine: { lineStyle: { color: c.textMuted } }, splitLine: { show: false } },
      { type: 'category', data: dateLabels, gridIndex: 1, show: false, splitLine: { show: false } }
    ],
    yAxis: [
      { scale: true, gridIndex: 0, axisLabel: { color: c.textMuted, fontSize: 10 }, splitLine: { show: false } },
      { scale: true, gridIndex: 1, axisLabel: { color: c.textMuted, fontSize: 10, formatter: '{value}万' }, splitLine: { show: false } }
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }],
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' },
      formatter: function(params) {
        const k = params.find(p => p.seriesName === 'K线');
        const vol = params.find(p => p.seriesName === '成交量');
        if (!k || !vol) return '';
        return k.axisValue + '<br/>开: ' + k.data[0] + '  收: ' + k.data[1] + '<br/>低: ' + k.data[2] + '  高: ' + k.data[3] + '<br/>成交量: ' + vol.data.value + '万手';
      }
    },
    legend: { data: ['K线', 'MA5', 'MA20', 'MA60'], top: 0, textStyle: { color: c.textSecondary } },
    series: [
      { name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: c.upColor, color0: c.downColor, borderColor: c.upColor, borderColor0: c.downColor } },
      { name: 'MA5', type: 'line', data: ma5, smooth: true,
        lineStyle: { width: 1.5, color: c.ma5Color }, showSymbol: false, xAxisIndex: 0, yAxisIndex: 0 },
      { name: 'MA20', type: 'line', data: ma20, smooth: true,
        lineStyle: { width: 1.5, color: c.ma20Color }, showSymbol: false, xAxisIndex: 0, yAxisIndex: 0 },
      { name: 'MA60', type: 'line', data: ma60, smooth: true,
        lineStyle: { width: 1.5, color: c.ma60Color }, showSymbol: false, xAxisIndex: 0, yAxisIndex: 0 },
      { name: '成交量', type: 'bar', data: volData, xAxisIndex: 1, yAxisIndex: 1 }
    ]
  });
}

// ── 渲染入口 ──
function renderCharts() { renderPie(); renderKline(); }

// ── 主题切换 ──
const toggleBtn = document.getElementById('themeToggle');
toggleBtn.addEventListener('click', () => {
  document.body.classList.toggle('light-mode');
  toggleBtn.textContent = document.body.classList.contains('light-mode') ? '🌙 深色模式' : '☀️ 浅色模式';
  renderCharts();
});
renderCharts();

// ── 导航滚动高亮 ──
const sections = document.querySelectorAll('.card[id], .hero[id], .conclusion-top[id]');
const navs = document.querySelectorAll('.nav-links a');
window.addEventListener('scroll', () => {
  let cur = '';
  sections.forEach(s => { if (window.scrollY >= s.offsetTop - 100) cur = s.id; });
  navs.forEach(a => {
    a.classList.remove('active');
    if (a.getAttribute('href') === '#' + cur) a.classList.add('active');
  });
});
document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', function(e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});

// ── 响应式图表 ──
window.addEventListener('resize', () => {
  pieChart && pieChart.resize();
  klineChart && klineChart.resize();
});
})();
