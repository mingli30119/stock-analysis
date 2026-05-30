/* 个股深度研报 · JavaScript 模板 v3.1 */
/* 使用方式：AI 手写 HTML 时，复制此文件全部内容到 <script> 标签内 */
/* 数据注入点（4处）：① rawData 数组  ② renderPie() 的 pieData  ③ markLine 价格  ④ markPoint 价格 */
/* ⚠️ rawData格式：[date, open, high, low, close, vol]（akshare原生顺序） */
/* ⚠️ OHLC转换：ohlc.push([d[1], d[4], d[3], d[2]]) → [open, close, low, high] */

(function() {
const rawData = __RAW_DATA_ARRAY__;

// ── 数据处理（无需修改）──
const dates = [], ohlc = [], volumesRaw = [];
rawData.forEach(d => {
  dates.push(d[0]);
  ohlc.push([d[1], d[4], d[3], d[2]]);  // [open, close, low, high] — rawData=[date,open,high,low,close,vol]
  volumesRaw.push(d[5]);
});
const closes = ohlc.map(d => d[1]);
const highs = rawData.map(d => d[4]), lows = rawData.map(d => d[3]);
const calcMA = (arr, n) => arr.map((_, i) => {
  if (i < n - 1) return null;
  let sum = arr.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0);
  return +(sum / n).toFixed(2);
});
const ma5 = calcMA(closes, 5), ma20 = calcMA(closes, 20), ma60 = calcMA(closes, 60);
const volumes = volumesRaw.map(v => +(v / 10000).toFixed(2));
const dateLabels = dates.map(d => { const parts = d.split('-'); return parts[1] + '-' + parts[2]; });

// ── 主题色获取（支持浅色/深色双模式）──
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

// ── 技术指标计算（第9章数据源）──
function calcEMA(arr, n) { const k = 2/(n+1); let ema = [arr[0]]; for(let i=1;i<arr.length;i++) ema.push(arr[i]*k+ema[i-1]*(1-k)); return ema; }
function calcMACDData(closes) { const ema12=calcEMA(closes,12), ema26=calcEMA(closes,26), dif=ema12.map((v,i)=>v-ema26[i]), dea=calcEMA(dif,9); return {dif:dif,dea:dea,macd:dif.map((v,i)=>2*(v-dea[i]))}; }
function calcKDJData(highs,lows,closes,n) { n=n||9; let k=[],d=[],j=[]; for(let i=0;i<closes.length;i++){if(i<n-1){k.push(50);d.push(50);j.push(50);continue;}let h=Math.max(...highs.slice(i-n+1,i+1)),l=Math.min(...lows.slice(i-n+1,i+1)),rsv=((closes[i]-l)/(h-l))*100||50;k.push(i===n-1?rsv:(2/3)*k[i-1]+(1/3)*rsv);d.push(i===n-1?k[i]:(2/3)*d[i-1]+(1/3)*k[i]);j.push(3*k[i]-2*d[i]);} return {k:k,d:d,j:j}; }
function calcRSI(closes,n){let gains=[],losses=[],rsi=[];for(let i=0;i<closes.length;i++){if(i===0){gains.push(0);losses.push(0);rsi.push(50);continue;}let ch=closes[i]-closes[i-1];gains.push(ch>0?ch:0);losses.push(ch<0?-ch:0);if(i<n){rsi.push(50);continue;}let ag=gains.slice(i-n+1,i+1).reduce((a,b)=>a+b,0)/n,al=losses.slice(i-n+1,i+1).reduce((a,b)=>a+b,0)/n;rsi.push(al===0?100:100-(100/(1+ag/al)));} return rsi; }
function calcBOLL(closes,n){n=n||20;let mid=[],upper=[],lower=[];for(let i=0;i<closes.length;i++){if(i<n-1){mid.push(null);upper.push(null);lower.push(null);continue;}let slice=closes.slice(i-n+1,i+1),avg=slice.reduce((a,b)=>a+b,0)/n,std=Math.sqrt(slice.reduce((a,b)=>a+Math.pow(b-avg,2),0)/n);mid.push(avg);upper.push(avg+2*std);lower.push(avg-2*std);} return {mid:mid,upper:upper,lower:lower}; }

const macdData=calcMACDData(closes), kdjData=calcKDJData(highs,lows,closes);
const rsi6=calcRSI(closes,6), rsi12=calcRSI(closes,12), rsi24=calcRSI(closes,24);
const bollData=calcBOLL(closes);

// ── 图表实例 ──
let pieChart, klineChart, macdChart, kdjChart, rsiChart, bollChart;

// ── 饼图渲染 ──
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

// ── K线图渲染（含技术标注 markLine + markPoint）──
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
        itemStyle: { color: c.upColor, color0: c.downColor, borderColor: c.upColor, borderColor0: c.downColor },
        // ── 技术标注（AI替换实际价格）──
        markLine: {
          symbol: 'none',
          lineStyle: { color: '#d4a853', width: 1.5, type: 'dashed' },
          label: { position: 'end', fontSize: 10, color: '#d4a853', formatter: '{b}' },
          data: __MARKLINE_DATA__
        },
        markPoint: {
          symbol: 'pin',
          symbolSize: 50,
          label: { fontSize: 11, color: '#fff', fontWeight: 'bold' },
          data: __MARKPOINT_DATA__
        }
      },
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

// ── 第9章·技术指标图表渲染 ──
function renderMACD(){if(macdChart)macdChart.dispose();macdChart=echarts.init(document.getElementById('chart-macd'));const c=getThemeColors();macdChart.setOption({grid:{left:'10%',right:'4%',top:'8%',height:'60%'},xAxis:{data:dateLabels,axisLabel:{color:c.textMuted,fontSize:8,interval:8}},yAxis:{axisLabel:{color:c.textMuted,fontSize:9}},series:[{name:'DIF',type:'line',data:macdData.dif,lineStyle:{color:'#e3c26d',width:1.2},showSymbol:false},{name:'DEA',type:'line',data:macdData.dea,lineStyle:{color:'#4a90d9',width:1.2},showSymbol:false},{name:'MACD',type:'bar',data:macdData.macd,itemStyle:{color:params=>params.value>=0?'rgba(245,86,86,0.5)':'rgba(40,199,91,0.5)'}}],legend:{data:['DIF','DEA','MACD'],top:0,textStyle:{color:c.textSecondary,fontSize:10}}});}
function renderKDJ(){if(kdjChart)kdjChart.dispose();kdjChart=echarts.init(document.getElementById('chart-kdj'));const c=getThemeColors();kdjChart.setOption({grid:{left:'10%',right:'4%',top:'8%',height:'60%'},xAxis:{data:dateLabels,axisLabel:{color:c.textMuted,fontSize:8,interval:8}},yAxis:{min:0,max:100,axisLabel:{color:c.textMuted,fontSize:9}},series:[{name:'K',type:'line',data:kdjData.k,lineStyle:{color:'#e3c26d',width:1.2},showSymbol:false},{name:'D',type:'line',data:kdjData.d,lineStyle:{color:'#4a90d9',width:1.2},showSymbol:false},{name:'J',type:'line',data:kdjData.j,lineStyle:{color:'#f55656',width:1},showSymbol:false}],legend:{data:['K','D','J'],top:0,textStyle:{color:c.textSecondary,fontSize:10}}});}
function renderRSI(){if(rsiChart)rsiChart.dispose();rsiChart=echarts.init(document.getElementById('chart-rsi'));const c=getThemeColors();rsiChart.setOption({grid:{left:'10%',right:'4%',top:'8%',height:'60%'},xAxis:{data:dateLabels,axisLabel:{color:c.textMuted,fontSize:8,interval:8}},yAxis:{min:0,max:100,axisLabel:{color:c.textMuted,fontSize:9}},series:[{name:'RSI6',type:'line',data:rsi6,lineStyle:{color:'#4a90d9',width:1.2},showSymbol:false},{name:'RSI12',type:'line',data:rsi12,lineStyle:{color:'#e3c26d',width:1.2},showSymbol:false},{name:'RSI24',type:'line',data:rsi24,lineStyle:{color:'#f55656',width:1.2},showSymbol:false}],legend:{data:['RSI6','RSI12','RSI24'],top:0,textStyle:{color:c.textSecondary,fontSize:10}}});}
function renderBOLL(){if(bollChart)bollChart.dispose();bollChart=echarts.init(document.getElementById('chart-boll'));const c=getThemeColors();bollChart.setOption({grid:{left:'10%',right:'4%',top:'8%',height:'60%'},xAxis:{data:dateLabels,axisLabel:{color:c.textMuted,fontSize:8,interval:8}},yAxis:{axisLabel:{color:c.textMuted,fontSize:9}},series:[{name:'上轨',type:'line',data:bollData.upper,lineStyle:{color:'rgba(245,86,86,0.4)',width:1},showSymbol:false},{name:'中轨',type:'line',data:bollData.mid,lineStyle:{color:'#e3c26d',width:1.2},showSymbol:false},{name:'下轨',type:'line',data:bollData.lower,lineStyle:{color:'rgba(40,199,91,0.4)',width:1},showSymbol:false,areaStyle:{color:'rgba(212,168,83,0.05)'}},{name:'收盘价',type:'line',data:closes,lineStyle:{color:'#4a90d9',width:1.5},showSymbol:false}],legend:{data:['上轨','中轨','下轨','收盘价'],top:0,textStyle:{color:c.textSecondary,fontSize:10}}});}

// ── 渲染入口（全部6个图表）──
function renderCharts() { renderPie(); renderKline(); renderMACD(); renderKDJ(); renderRSI(); renderBOLL(); }

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

// ── 响应式图表（全部6个）──
window.addEventListener('resize', () => {
  pieChart && pieChart.resize();
  klineChart && klineChart.resize();
  macdChart && macdChart.resize();
  kdjChart && kdjChart.resize();
  rsiChart && rsiChart.resize();
  bollChart && bollChart.resize();
});
})();
