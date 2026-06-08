/* =========================================================================
   DartLab Terminal — CHART ENGINE (canvas)
   PriceChart: candlestick + SMA20/60 overlay + volume + RSI or MACD sub.
   Plus: Sparkline, Gauge, MiniBars used across panels.
   ========================================================================= */
(function(){
const { useRef, useEffect, useState } = React;

const CLR = {
  up: '#34d399', down: '#f0616f', amber: '#fb923c', amberDim: '#9c6418',
  grid: '#161b28', axis: '#2a3142', text: '#94a3b8', textHi: '#f1f5f9',
  sma20: '#fb923c', sma60: '#60a5fa', bg: '#0f1219',
};

function fmtNum(n, d = 0) {
  if (n == null || isNaN(n)) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
function fmtAbbr(n) {
  const a = Math.abs(n);
  if (a >= 1e12) return (n / 1e12).toFixed(2) + 'T';
  if (a >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (a >= 1e3) return (n / 1e3).toFixed(0) + 'K';
  return '' + n;
}

// ------------------------------------------------------------------ PriceChart
function PriceChart({ candles, period, indicator, ccy }) {
  const ref = useRef(null);
  const wrapRef = useRef(null);
  const [hover, setHover] = useState(null);
  const [dims, setDims] = useState({ w: 800, h: 360 });

  useEffect(() => {
    const ro = new ResizeObserver((es) => {
      for (const e of es) {
        const cr = e.contentRect;
        setDims({ w: Math.max(320, cr.width), h: Math.max(220, cr.height) });
      }
    });
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // slice by period
  const map = { '1M': 22, '3M': 66, '6M': 110, '1Y': 130 };
  const slice = candles.slice(-Math.min(candles.length, map[period] || 130));
  const closes = slice.map((c) => c.c);
  const s20 = DL.sma(closes, 20);
  const s60 = DL.sma(closes, 60);
  const rsiArr = DL.rsi(closes, 14);
  const macdObj = DL.macd(closes);

  useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const dpr = window.devicePixelRatio || 1;
    const W = dims.w, H = dims.h;
    cv.width = W * dpr; cv.height = H * dpr;
    cv.style.width = W + 'px'; cv.style.height = H + 'px';
    const ctx = cv.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    const padR = 62, padL = 6, padT = 4;
    const subH = 36;       // RSI/MACD sub
    const volH = 22;
    const gap = 4;
    const priceH = H - padT - subH - volH - gap * 2 - 12;
    const plotW = W - padR - padL;

    const lo = Math.min(...slice.map((c) => c.l));
    const hi = Math.max(...slice.map((c) => c.h));
    const pad = (hi - lo) * 0.025;
    const yMin = lo - pad, yMax = hi + pad;
    const Y = (v) => padT + priceH - ((v - yMin) / (yMax - yMin)) * priceH;
    const n = slice.length;
    const cw = plotW / n;
    const X = (i) => padL + i * cw + cw / 2;

    // grid + price axis
    ctx.font = '10px "IBM Plex Mono", monospace';
    ctx.textBaseline = 'middle';
    const ticks = 5;
    for (let k = 0; k <= ticks; k++) {
      const v = yMin + (yMax - yMin) * (k / ticks);
      const y = Y(v);
      ctx.strokeStyle = CLR.grid; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + plotW, y); ctx.stroke();
      ctx.fillStyle = CLR.text; ctx.textAlign = 'left';
      ctx.fillText(fmtNum(v, ccy === 'USD' ? 1 : 0), padL + plotW + 6, y);
    }

    // candles
    slice.forEach((c, i) => {
      const x = X(i);
      const up = c.c >= c.o;
      const col = up ? CLR.up : CLR.down;
      ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, Y(c.h)); ctx.lineTo(x, Y(c.l)); ctx.stroke();
      const bw = Math.max(1, cw * 0.62);
      const yo = Y(c.o), yc = Y(c.c);
      const top = Math.min(yo, yc), bh = Math.max(1, Math.abs(yc - yo));
      ctx.fillRect(x - bw / 2, top, bw, bh);
    });

    // SMA overlays
    function drawLine(arr, color) {
      ctx.strokeStyle = color; ctx.lineWidth = 1.3; ctx.beginPath();
      let started = false;
      arr.forEach((v, i) => { if (v == null) return; const x = X(i), y = Y(v); if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y); });
      ctx.stroke();
    }
    if (indicator !== 'NONE') { drawLine(s20, CLR.sma20); drawLine(s60, CLR.sma60); }

    // volume
    const volTop = padT + priceH + gap;
    const vMax = Math.max(...slice.map((c) => c.v));
    slice.forEach((c, i) => {
      const x = X(i); const up = c.c >= c.o;
      const h = (c.v / vMax) * volH;
      ctx.fillStyle = up ? 'rgba(54,211,153,.45)' : 'rgba(255,91,110,.45)';
      ctx.fillRect(x - Math.max(1, cw * 0.62) / 2, volTop + volH - h, Math.max(1, cw * 0.62), h);
    });
    ctx.fillStyle = CLR.text; ctx.textAlign = 'left';
    ctx.fillText('VOL', padL + 2, volTop + 7);

    // sub indicator (RSI or MACD)
    const subTop = volTop + volH + gap;
    ctx.strokeStyle = CLR.grid; ctx.beginPath(); ctx.moveTo(padL, subTop); ctx.lineTo(padL + plotW, subTop); ctx.stroke();
    if (indicator === 'MACD') {
      const all = macdObj.line.concat(macdObj.sig, macdObj.hist).filter((v) => v != null);
      const m = Math.max(...all.map(Math.abs)) || 1;
      const SY = (v) => subTop + subH / 2 - (v / m) * (subH / 2 - 4);
      // zero line
      ctx.strokeStyle = CLR.axis; ctx.beginPath(); ctx.moveTo(padL, SY(0)); ctx.lineTo(padL + plotW, SY(0)); ctx.stroke();
      macdObj.hist.forEach((v, i) => { if (v == null) return; const x = X(i); ctx.fillStyle = v >= 0 ? 'rgba(54,211,153,.6)' : 'rgba(255,91,110,.6)'; const y0 = SY(0), y1 = SY(v); ctx.fillRect(x - Math.max(1, cw * 0.5) / 2, Math.min(y0, y1), Math.max(1, cw * 0.5), Math.abs(y1 - y0)); });
      function dl(arr, col) { ctx.strokeStyle = col; ctx.lineWidth = 1.1; ctx.beginPath(); let st = false; arr.forEach((v, i) => { if (v == null) return; const x = X(i), y = SY(v); st ? ctx.lineTo(x, y) : (ctx.moveTo(x, y), st = true); }); ctx.stroke(); }
      dl(macdObj.line, CLR.amber); dl(macdObj.sig, CLR.sma60);
      ctx.fillStyle = CLR.text; ctx.textAlign = 'left'; ctx.fillText('MACD 12/26/9', padL + 2, subTop + 7);
    } else {
      const SY = (v) => subTop + subH - (v / 100) * subH;
      [30, 50, 70].forEach((lv) => { ctx.strokeStyle = lv === 50 ? CLR.grid : 'rgba(255,158,44,.18)'; ctx.beginPath(); ctx.moveTo(padL, SY(lv)); ctx.lineTo(padL + plotW, SY(lv)); ctx.stroke(); ctx.fillStyle = CLR.text; ctx.textAlign = 'left'; ctx.fillText('' + lv, padL + plotW + 6, SY(lv)); });
      ctx.strokeStyle = CLR.amber; ctx.lineWidth = 1.2; ctx.beginPath(); let st = false;
      rsiArr.forEach((v, i) => { if (v == null) return; const x = X(i), y = SY(v); st ? ctx.lineTo(x, y) : (ctx.moveTo(x, y), st = true); }); ctx.stroke();
      ctx.fillStyle = CLR.text; ctx.fillText('RSI 14', padL + 2, subTop + 7);
    }

    // date axis labels
    ctx.fillStyle = CLR.text; ctx.font = '9px "IBM Plex Mono", monospace'; ctx.textAlign = 'center';
    const step = Math.floor(n / 6) || 1;
    for (let i = 0; i < n; i += step) {
      const d = slice[i].t;
      ctx.fillText(`${d.getMonth() + 1}/${d.getDate()}`, X(i), H - 6);
    }

    // hover crosshair
    if (hover != null && hover >= 0 && hover < n) {
      const x = X(hover);
      ctx.strokeStyle = 'rgba(255,158,44,.5)'; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + priceH); ctx.stroke(); ctx.setLineDash([]);
    }
  }, [dims, period, indicator, candles, hover, ccy]);

  function onMove(e) {
    const cv = ref.current; if (!cv) return;
    const r = cv.getBoundingClientRect();
    const padR = 62, padL = 6; const plotW = dims.w - padR - padL; const n = slice.length;
    const i = Math.floor((e.clientX - r.left - padL) / (plotW / n));
    setHover(i >= 0 && i < n ? i : null);
  }
  const hv = hover != null ? slice[hover] : slice[slice.length - 1];

  return (
    <div ref={wrapRef} className="chartWrap" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <canvas ref={ref}></canvas>
      {hv && (
        <div className="ohlcTag">
          <span>{hv.t.getFullYear()}-{String(hv.t.getMonth() + 1).padStart(2, '0')}-{String(hv.t.getDate()).padStart(2, '0')}</span>
          <span>O <b>{fmtNum(hv.o, ccy === 'USD' ? 1 : 0)}</b></span>
          <span>H <b>{fmtNum(hv.h, ccy === 'USD' ? 1 : 0)}</b></span>
          <span>L <b>{fmtNum(hv.l, ccy === 'USD' ? 1 : 0)}</b></span>
          <span>C <b style={{ color: hv.c >= hv.o ? CLR.up : CLR.down }}>{fmtNum(hv.c, ccy === 'USD' ? 1 : 0)}</b></span>
          <span>V <b>{fmtAbbr(hv.v)}</b></span>
        </div>
      )}
      <div className="legendTag">
        <span style={{ color: CLR.sma20 }}>━ SMA20</span>
        <span style={{ color: CLR.sma60 }}>━ SMA60</span>
        <span style={{ color: CLR.up }}>RSI {fmtNum(rsiArr[rsiArr.length - 1], 1)}</span>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ Sparkline
function Sparkline({ data, w = 60, h = 18, color = CLR.up }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return; const dpr = window.devicePixelRatio || 1;
    cv.width = w * dpr; cv.height = h * dpr; cv.style.width = w + 'px'; cv.style.height = h + 'px';
    const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
    const lo = Math.min(...data), hi = Math.max(...data); const rng = hi - lo || 1;
    ctx.strokeStyle = color; ctx.lineWidth = 1; ctx.beginPath();
    data.forEach((v, i) => { const x = (i / (data.length - 1)) * (w - 2) + 1; const y = h - 2 - ((v - lo) / rng) * (h - 4); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke();
  }, [data, color, w, h]);
  return <canvas ref={ref}></canvas>;
}

// ------------------------------------------------------------------ Gauge (regime)
function Gauge({ value, label, sub, tone = 'up' }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return; const dpr = window.devicePixelRatio || 1;
    const S = 92; cv.width = S * dpr; cv.height = S * dpr; cv.style.width = S + 'px'; cv.style.height = S + 'px';
    const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, S, S);
    const cx = S / 2, cy = S / 2 + 6, r = 34;
    const a0 = Math.PI * 0.85, a1 = Math.PI * 2.15;
    ctx.lineWidth = 7; ctx.strokeStyle = '#1a1e25'; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(cx, cy, r, a0, a1); ctx.stroke();
    const col = tone === 'up' ? CLR.up : tone === 'down' ? CLR.down : CLR.amber;
    ctx.strokeStyle = col; ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + (a1 - a0) * value); ctx.stroke();
    ctx.fillStyle = col; ctx.font = '700 17px "IBM Plex Mono", monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(label, cx, cy - 2);
  }, [value, label, tone]);
  return (
    <div className="gauge"><canvas ref={ref}></canvas><div className="gaugeSub">{sub}</div></div>
  );
}

// ------------------------------------------------------------------ Radar
function Radar({ data, lang, size = 116, color = '#a78bfa' }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return; const dpr = window.devicePixelRatio || 1;
    cv.width = size * dpr; cv.height = size * dpr; cv.style.width = size + 'px'; cv.style.height = size + 'px';
    const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, size, size);
    const cx = size / 2, cy = size / 2, r = size / 2 - 16, n = data.length;
    const ang = (i) => -Math.PI / 2 + (i / n) * Math.PI * 2;
    // rings
    for (let g = 1; g <= 4; g++) {
      ctx.strokeStyle = g === 4 ? '#2a3142' : '#1b2130'; ctx.beginPath();
      for (let i = 0; i <= n; i++) { const a = ang(i % n); const rr = r * g / 4; const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
      ctx.stroke();
    }
    // spokes + labels
    ctx.fillStyle = '#64748b'; ctx.font = '8px "Pretendard Variable",sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    data.forEach((d, i) => {
      const a = ang(i); ctx.strokeStyle = '#1b2130'; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); ctx.stroke();
      const lx = cx + Math.cos(a) * (r + 9), ly = cy + Math.sin(a) * (r + 9);
      ctx.fillText(lang === 'en' ? d.en : d.kr, lx, ly);
    });
    // polygon
    ctx.beginPath();
    data.forEach((d, i) => { const a = ang(i); const s = d.s == null ? 0 : d.s; const x = cx + Math.cos(a) * r * s, y = cy + Math.sin(a) * r * s; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.closePath();
    ctx.fillStyle = 'rgba(167,139,250,.22)'; ctx.fill();
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
    data.forEach((d, i) => { const a = ang(i); const s = d.s == null ? 0 : d.s; const x = cx + Math.cos(a) * r * s, y = cy + Math.sin(a) * r * s; ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, 1.8, 0, 7); ctx.fill(); });
  }, [data, lang, size, color]);
  return <canvas ref={ref}></canvas>;
}

window.ChartKit = { PriceChart, Sparkline, Gauge, Radar, CLR, fmtNum, fmtAbbr };
})();
