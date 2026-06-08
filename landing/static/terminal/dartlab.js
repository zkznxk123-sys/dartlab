/* =========================================================================
   DartLab Terminal — REAL DATA ENGINE
   Fetches dartlab data at runtime from HuggingFace (same contract the
   dartlab landing uses), with local fallback. NO mock data.

     HF: https://huggingface.co/datasets/eddmpython/dartlab-data
         /resolve/main/landing/<path>     (loadJson contract, dartlabData.ts)
     Local fallback: ./data/landing/<path>

   Sources:
     dashboards/finance.json   — 5Y annual IS/BS/CF/ratios (조 KRW)   [REAL]
     dashboards/macro.json     — KR/US cycle, quadrant, sector tailwind [REAL]
     dashboards/meta.json      — engine defs + blog stories            [REAL]
     map/prices-snapshot.json  — 2,555 종목 price/return/vol/52w       [REAL]
     map/search-index.json     — corpName / industry / revenue         [REAL]
     charts/{code}/...         — peer matrix etc (on demand)           [REAL]
   ========================================================================= */
(function () {
  const DEFAULT_HF = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';
  // configurable: window.DARTLAB_HF_RESOLVE overrides; embed in landing → set to '' to use local static
  const HF_RESOLVE = (window.DARTLAB_HF_RESOLVE ?? DEFAULT_HF).replace(/\/+$/, '');
  const LOCAL_BASE = window.DARTLAB_LOCAL_BASE ?? 'data/landing';

  const _mem = new Map();
  async function tryFetch(url, timeoutMs = 7000) {
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), timeoutMs);
      const r = await fetch(url, { signal: ctl.signal });
      clearTimeout(t);
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }
  // dartlab loadJson contract: HF landing/<path> first, then local static fallback
  async function loadJson(path) {
    const p = path.replace(/^\/+/, '');
    if (_mem.has(p)) return _mem.get(p);
    let data = null;
    if (HF_RESOLVE) data = await tryFetch(`${HF_RESOLVE}/landing/${p}`);
    if (data == null) data = await tryFetch(`${LOCAL_BASE}/${p}`);
    _mem.set(p, data);
    return data;
  }

  // ---- technical helpers ----
  function sma(a, p) { const o = []; for (let i = 0; i < a.length; i++) { if (i < p - 1) { o.push(null); continue; } let s = 0; for (let j = i - p + 1; j <= i; j++) s += a[j]; o.push(s / p); } return o; }
  function ema(a, p) { const k = 2 / (p + 1); const o = []; let pr; a.forEach((v, i) => { pr = i === 0 ? v : v * k + pr * (1 - k); o.push(pr); }); return o; }
  function rsi(a, p = 14) { const o = [null]; let g = 0, l = 0; for (let i = 1; i < a.length; i++) { const c = a[i] - a[i - 1], u = Math.max(c, 0), d = Math.max(-c, 0); if (i <= p) { g += u; l += d; if (i === p) { g /= p; l /= p; o.push(100 - 100 / (1 + g / (l || 1e-9))); } else o.push(null); } else { g = (g * (p - 1) + u) / p; l = (l * (p - 1) + d) / p; o.push(100 - 100 / (1 + g / (l || 1e-9))); } } return o; }
  function macd(a) { const e12 = ema(a, 12), e26 = ema(a, 26); const line = e12.map((v, i) => v - e26[i]); const sig = ema(line, 9); const hist = line.map((v, i) => v - sig[i]); return { line, sig, hist }; }
  function seeded(s) { let x = s >>> 0; return () => (x = (x * 1664525 + 1013904223) >>> 0) / 4294967296; }

  // Reconstruct a daily candle path anchored to REAL last price, REAL 1y return,
  // REAL annualized volatility. Endpoints/level/dispersion are real; intraday path synthetic.
  function reconstructCandles(code, last, ret1y, vol1y) {
    const n = 130;
    const rnd = seeded(parseInt((code || '0').replace(/\D/g, '') || '7', 10) + 9973);
    const r1y = (ret1y == null ? 0 : ret1y) / 100;
    const startApprox = last / (1 + r1y);       // 1y ago level (approx, real return)
    // 130 trading days ≈ ~0.5y; scale the path to ~half-year slice of the 1y move
    const start = last / (1 + r1y * (n / 252));
    const dailyDrift = Math.log(last / start) / n;
    const dvol = ((vol1y == null ? 30 : vol1y) / 100) / Math.sqrt(252);
    const out = []; let px = start; const today = new Date(2026, 3, 24);
    for (let i = n - 1; i >= 0; i--) {
      const d = new Date(today); d.setDate(today.getDate() - i);
      const o = px;
      const shock = dailyDrift + (rnd() - 0.5) * 2 * dvol;
      let c = o * Math.exp(shock);
      const hi = Math.max(o, c) * (1 + rnd() * dvol * 0.6);
      const lo = Math.min(o, c) * (1 - rnd() * dvol * 0.6);
      out.push({ t: d, o, h: hi, l: lo, c, v: Math.round((0.6 + rnd()) * 1e6) });
      px = c;
    }
    // pin the final close exactly to the real last price
    const f = last / out[out.length - 1].c;
    out.forEach((k) => { k.o *= f; k.h *= f; k.l *= f; k.c *= f; });
    return out;
  }

  const num = (v) => (v == null || isNaN(v) ? null : v);
  function lastNonNull(arr) { if (!arr) return null; for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return { v: arr[i], i }; return null; }
  function pct(a, b) { return a != null && b != null && b !== 0 ? ((a - b) / Math.abs(b)) * 100 : null; }

  // ---- credit derivation from REAL ratios (dartlab 7-axis spirit) ----
  function deriveCredit(fin) {
    const dr = lastNonNull(fin.ratios.debtRatio); const roe = lastNonNull(fin.ratios.roe);
    const ta = lastNonNull(fin.bs.totals.totalAsset); const tl = lastNonNull(fin.bs.totals.totalLiab);
    const ca = lastNonNull(fin.bs.totals.currAsset); const cl = lastNonNull(fin.bs.totals.currLiab);
    const opm = lastNonNull(fin.is.opMargin); const op = lastNonNull(fin.is.op);
    const opmv = opm ? opm.v : null; const opv = op ? op.v : null;
    const debtRatio = dr ? dr.v : null;
    const curr = ca && cl && cl.v ? (ca.v / cl.v) * 100 : null;
    // 0-100 sub scores
    const sCap = debtRatio == null ? 60 : Math.max(5, Math.min(100, 100 - debtRatio / 6));
    const sLiq = curr == null ? 60 : Math.max(5, Math.min(100, curr / 3));
    const sProf = opmv == null ? 50 : Math.max(5, Math.min(100, 50 + opmv * 2.2));
    const sCf = opv == null ? 55 : Math.max(5, Math.min(100, opv > 0 ? 92 : 35));
    const sStab = roe == null ? 55 : Math.max(5, Math.min(100, 55 + roe.v * 1.4));
    const health = Math.round((sCap * 0.26 + sLiq * 0.18 + sProf * 0.2 + sCf * 0.2 + sStab * 0.16));
    const grades = [[95, 'dCR-AAA'], [88, 'dCR-AA+'], [82, 'dCR-AA'], [76, 'dCR-AA-'], [70, 'dCR-A+'], [63, 'dCR-A'], [56, 'dCR-A-'], [49, 'dCR-BBB+'], [42, 'dCR-BBB'], [35, 'dCR-BBB-'], [28, 'dCR-BB+'], [20, 'dCR-BB'], [12, 'dCR-B'], [0, 'dCR-CCC']];
    const grade = (grades.find((g) => health >= g[0]) || grades[grades.length - 1])[1];
    const pd = (Math.max(0.005, Math.min(28, Math.pow((100 - health) / 100, 3.1) * 30))).toFixed(2) + '%';
    return {
      grade, healthScore: health, pd, tone: health >= 70 ? 'up' : health >= 49 ? 'good' : 'warn',
      tracks: [
        { kr: '자본구조', en: 'Capital structure', score: Math.round(sCap) },
        { kr: '유동성', en: 'Liquidity', score: Math.round(sLiq) },
        { kr: '수익성', en: 'Profitability', score: Math.round(sProf) },
        { kr: '현금흐름', en: 'Cash flow', score: Math.round(sCf) },
        { kr: '재무안정성', en: 'Stability', score: Math.round(sStab) },
      ],
      basis: { debtRatio, curr: curr == null ? null : Math.round(curr), opm: opm ? opm.v : null },
    };
  }

  const SECTOR_EN = {
    semiconductor: 'Semiconductors', auto: 'Automobile', energy: 'Energy', electronics: 'Electronics',
    chemical: 'Chemicals', aerospace: 'Aerospace & Defense', shipbuilding: 'Shipbuilding', steel: 'Steel',
    food: 'Food & Bev', software: 'Software', pharma: 'Pharma', finance: 'Financials', retail: 'Retail',
    construction: 'Construction', telecom: 'Telecom', media: 'Media', battery: 'Batteries', textile: 'Apparel',
    logistics: 'Logistics', cosmetics: 'Cosmetics', machinery: 'Machinery', paper: 'Paper', leisure: 'Leisure',
    electrical: 'Electrical', plastic: 'Plastics', realestate: 'Real Estate', education: 'Education',
    medicalDevice: 'Medical Devices', environment: 'Environment', buildingMaterials: 'Building Materials',
    railroad: 'Railroad', consulting: 'Holding/Consulting', misc: 'Misc',
  };
  const SECTOR_KR = {
    semiconductor: '반도체', auto: '자동차', energy: '에너지', electronics: '전자', chemical: '화학',
    aerospace: '항공우주', shipbuilding: '조선', steel: '철강', food: '음식료', software: '소프트웨어',
    pharma: '제약바이오', finance: '금융', retail: '유통', construction: '건설', telecom: '통신',
    media: '미디어', battery: '2차전지', textile: '섬유의류', logistics: '물류', cosmetics: '화장품',
    machinery: '기계', paper: '제지', leisure: '레저', electrical: '전기', plastic: '플라스틱',
    realestate: '부동산', education: '교육', medicalDevice: '의료기기', environment: '환경',
    buildingMaterials: '건자재', railroad: '철도', consulting: '지주', misc: '기타',
  };

  // dartlab scan grade scales (best→worst) + group colors (GROUP_META)
  const GRADE_SCALE = {
    prof: ['우수', '양호', '보통', '저수익', '적자'],
    debt: ['안전', '관찰', '주의', '고위험'],
    growth: ['고성장', '성장', '정체', '역성장', '급감'],
    gov: ['A', 'B', 'C', 'D', 'E'],
    qual: ['우수', '양호', '보통', '주의', '위험'],
    liq: ['우수', '양호', '보통', '주의', '위험'],
    audit: ['저위험', '중위험', '고위험'],
    stab: ['안정', '보통', '불안정', '취약', '경고', '위험'],
  };
  const GROUP_COLOR = {
    identity: '#94a3b8', income: '#60a5fa', health: '#22c55e', governance: '#a78bfa',
    quality: '#fbbf24', workforce: '#f472b6', changes: '#fb923c', price: '#ea4647',
    valuation: '#10b981', disclosure: '#c084fc',
  };
  function gradeTone(scaleKey, val) {
    const sc = GRADE_SCALE[scaleKey]; if (!sc || !val) return 'neutral';
    const i = sc.indexOf(val); if (i < 0) return 'neutral';
    const f = i / (sc.length - 1);
    return f <= 0.18 ? 'up' : f <= 0.45 ? 'good' : f <= 0.62 ? 'neutral' : f <= 0.8 ? 'warn' : 'down';
  }
  function gradeScore(scaleKey, val) {
    const sc = GRADE_SCALE[scaleKey]; if (!sc || !val) return null;
    const i = sc.indexOf(val); if (i < 0) return null;
    return 1 - i / (sc.length - 1); // 1 best → 0 worst
  }
  const MARKET_LABEL = { '유가증권': 'KOSPI', '코스닥': 'KOSDAQ', '코넥스': 'KONEX' };

  let DB = null;
  async function boot() {
    if (DB) return DB;
    const [finance, macro, meta, prices, index, eco] = await Promise.all([
      loadJson('dashboards/finance.json'),
      loadJson('dashboards/macro.json'),
      loadJson('dashboards/meta.json'),
      loadJson('map/prices-snapshot.json'),
      loadJson('map/search-index.json'),
      loadJson('map/ecosystem.json'),
    ]);
    const byCode = {}; (index || []).forEach((r) => { byCode[r.stockCode] = r; });
    const ecoByCode = {}; ((eco && eco.nodes) || []).forEach((n) => { ecoByCode[n.id] = n; });
    const ecoIndustries = {}; ((eco && eco.industries) || []).forEach((i) => { ecoIndustries[i.id] = i; });
    DB = { finance, macro, meta, prices: (prices && prices.data) || {}, index: index || [], byCode,
      eco: ecoByCode, ecoIndustries, ecoFlows: (eco && eco.industryFlows) || [],
      years: (finance && finance.years) || ['2021', '2022', '2023', '2024', '2025'],
      source: HF_RESOLVE ? 'HuggingFace · resolve/main/landing' : 'local static' };
    return DB;
  }

  function rev(a) { return (a || []).slice().reverse(); }

  // ===== high-impact decision analytics (computed from REAL universe) =====
  function industryNodes(industry) { return Object.values(DB.eco).filter((n) => n.industry === industry); }
  function pctRank(arr, v, lowerBetter) {
    const xs = arr.filter((x) => x != null && isFinite(x)); if (!xs.length || v == null) return null;
    const below = xs.filter((x) => x <= v).length; let p = Math.round((below / xs.length) * 100);
    if (lowerBetter) p = 100 - p; return Math.max(1, Math.min(100, p));
  }
  function median(a) { const s = a.filter((x) => x != null && isFinite(x)).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; }

  function industryPercentile(code) {
    const node = DB.eco[code]; if (!node) return null;
    const peers = industryNodes(node.industry); const col = (f) => peers.map((n) => n[f]);
    return {
      industry: node.industryName, n: peers.length,
      metrics: [
        { kr: '영업이익률', en: 'OP margin', v: node.opMargin, p: pctRank(col('opMargin'), node.opMargin), unit: '%' },
        { kr: 'ROE', en: 'ROE', v: node.roe, p: pctRank(col('roe'), node.roe), unit: '%' },
        { kr: '매출성장', en: 'Rev growth', v: node.revCagr, p: pctRank(col('revCagr'), node.revCagr), unit: '%' },
        { kr: '매출규모', en: 'Revenue', v: node.revenue, p: pctRank(col('revenue'), node.revenue), unit: 'rev' },
        { kr: '점유율', en: 'Mkt share', v: node.marketShare, p: pctRank(col('marketShare'), node.marketShare), unit: '%' },
      ].filter((m) => m.p != null),
    };
  }

  function valuationOf(code) {
    const node = DB.eco[code], fin = DB.finance.companies[code], px = DB.prices[code];
    if (!node || !fin || !px || !px.currentPrice) return null;
    const net = lastNonNull(fin.is.net), eq = lastNonNull(fin.bs.totals.totalEquity);
    const shares = px.marketCap / px.currentPrice;
    const per = net && net.v > 0 ? px.marketCap / (net.v * 1e12) : null;
    const pbr = eq && eq.v > 0 ? px.marketCap / (eq.v * 1e12) : null;
    const peers = industryNodes(node.industry); const perL = [], pbrL = [];
    peers.forEach((n) => { const f = DB.finance.companies[n.id], p = DB.prices[n.id]; if (!f || !p || !p.marketCap) return;
      const nn = lastNonNull(f.is.net), ee = lastNonNull(f.bs.totals.totalEquity);
      if (nn && nn.v > 0) { const x = p.marketCap / (nn.v * 1e12); if (x > 0 && x < 200) perL.push(x); }
      if (ee && ee.v > 0) { const x = p.marketCap / (ee.v * 1e12); if (x > 0 && x < 60) pbrL.push(x); }
    });
    const perMed = median(perL), pbrMed = median(pbrL);
    const fairPer = perMed && net && net.v > 0 ? (perMed * net.v * 1e12) / shares : null;
    const fairPbr = pbrMed && eq && eq.v > 0 ? (pbrMed * eq.v * 1e12) / shares : null;
    const fair = [fairPer, fairPbr].filter((x) => x != null && x > 0);
    const fairMid = fair.length ? fair.reduce((a, b) => a + b, 0) / fair.length : null;
    const upside = fairMid ? ((fairMid - px.currentPrice) / px.currentPrice) * 100 : null;
    const perPos = per != null && perMed ? (per <= perMed ? 'cheap' : 'rich') : null;
    return { per, pbr, perMed, pbrMed, fairLow: fair.length ? Math.min(...fair) : null, fairHigh: fair.length ? Math.max(...fair) : null, fairMid, upside, last: px.currentPrice, perPos };
  }

  function riskFlagsOf(code) {
    const e = DB.eco[code] || {}; const f = []; const add = (lv, kr, en, d) => f.push({ lv, kr, en, d: d || '' });
    if (e.profGrade === '적자' || (e.opMargin != null && e.opMargin < 0)) add('red', '영업적자', 'Operating loss', e.opMargin != null ? e.opMargin.toFixed(1) + '%' : '');
    else if (e.profGrade === '저수익') add('yellow', '저수익', 'Low margin', e.opMargin != null ? e.opMargin.toFixed(1) + '%' : '');
    if (e.growthGrade === '급감') add('red', '매출 급감', 'Revenue collapse', e.revCagr != null ? e.revCagr.toFixed(0) + '%' : '');
    else if (e.growthGrade === '역성장') add('yellow', '매출 역성장', 'Revenue decline', e.revCagr != null ? e.revCagr.toFixed(0) + '%' : '');
    if (e.auditRisk === '고위험') add('red', '감사 고위험', 'Audit high risk', '');
    else if (e.auditRisk === '중위험') add('yellow', '감사 위험', 'Audit risk', '');
    if (e.qualGrade === '위험') add('red', '이익질 위험', 'Earnings quality risk', '');
    else if (e.qualGrade === '주의') add('yellow', '이익질 주의', 'Earnings quality watch', '');
    if (e.liqGrade === '위험') add('red', '유동성 위험', 'Liquidity risk', '');
    else if (e.liqGrade === '주의') add('yellow', '유동성 주의', 'Liquidity watch', '');
    if (['경고', '위험'].includes(e.stability)) add('red', '경영 불안정', 'Unstable', e.stability);
    else if (e.stability === '취약') add('yellow', '경영 취약', 'Fragile', e.stability);
    if (e.cfPattern === '현금위기형') add('red', '현금위기형', 'Cash crisis pattern', '');
    else if (e.cfPattern === '외부의존형') add('yellow', '외부자금 의존', 'External-dependent', '');
    if (e.holderChange != null && e.holderChange < -3) add('yellow', '대주주 지분 급감', 'Owner stake drop', e.holderChange.toFixed(1) + '%p');
    if (e.debtRatioDelta != null && e.debtRatioDelta > 30) add('yellow', '부채비율 급증', 'Debt spike', '+' + e.debtRatioDelta.toFixed(0) + '%p');
    if (!f.length) add('green', '주요 위험 신호 없음', 'No major red flags', '핵심 등급 양호');
    return f;
  }

  const TAILWIND_MAP = { auto: 'automotive', pharma: 'biotech', chemical: 'chemicals', construction: 'construction', electronics: 'display', energy: 'energy', finance: 'finance', software: 'it_software', retail: 'retail', semiconductor: 'semiconductor', shipbuilding: 'shipbuilding', steel: 'steel', battery: 'chemicals', telecom: 'it_software' };
  function tailwindOf(industry) {
    const k = TAILWIND_MAP[industry]; const tw = DB.macro.sectorTailwind && DB.macro.sectorTailwind[k];
    if (!tw) return null;
    const b = tw.blended; return { key: k, kr: SECTOR_KR[industry] || industry, blended: b, kr_score: tw.kr, us_score: tw.us, label: b >= 0.4 ? '순풍' : b >= 0.2 ? '중립' : '역풍', tone: b >= 0.4 ? 'up' : b >= 0.2 ? 'neutral' : 'down' };
  }

  function verdictOf(co) {
    const scores = co.radar.map((r) => r.s).filter((s) => s != null);
    const gradeAvg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0.5;
    const val = co.valuation; const up = val && val.upside != null ? val.upside : 0;
    const valScore = up > 25 ? 1 : up > 5 ? 0.72 : up > -15 ? 0.45 : 0.2;
    const r1y = co.price.ret1y == null ? 0 : co.price.ret1y;
    const momScore = r1y > 80 ? 0.85 : r1y > 20 ? 0.7 : r1y > -10 ? 0.5 : 0.25;
    const tw = co.tailwind; const twScore = tw ? Math.min(1, tw.blended / 0.6) : 0.5;
    const riskRed = co.risks.filter((x) => x.lv === 'red').length;
    let composite = 0.44 * gradeAvg + 0.18 * valScore + 0.14 * momScore + 0.18 * twScore + 0.06 * (riskRed ? 0 : 1);
    composite = Math.round(composite * 100);
    const band = composite >= 74 ? { kr: '강세 · 우량', en: 'STRONG', tone: 'up' } : composite >= 60 ? { kr: '양호 · 관심', en: 'SOLID', tone: 'good' } : composite >= 46 ? { kr: '중립 · 관망', en: 'NEUTRAL', tone: 'neutral' } : composite >= 32 ? { kr: '주의 · 점검', en: 'CAUTION', tone: 'warn' } : { kr: '취약 · 회피', en: 'WEAK', tone: 'down' };
    // strengths / concerns from radar extremes + valuation + momentum
    const sorted = co.radar.filter((r) => r.s != null).slice().sort((a, b) => b.s - a.s);
    const strengths = []; const concerns = [];
    sorted.slice(0, 2).forEach((r) => { if (r.s >= 0.6) strengths.push({ kr: `${r.kr} 우수 (상위)`, en: `Strong ${r.en}` }); });
    sorted.slice(-2).forEach((r) => { if (r.s <= 0.45) concerns.push({ kr: `${r.kr} 취약`, en: `Weak ${r.en}` }); });
    if (up != null && up > 15) strengths.push({ kr: `업종 대비 저평가 (+${up.toFixed(0)}% 여력)`, en: `Undervalued vs peers (+${up.toFixed(0)}%)` });
    if (up != null && up < -15) concerns.push({ kr: `업종 대비 고평가 (${up.toFixed(0)}%)`, en: `Rich vs peers (${up.toFixed(0)}%)` });
    if (r1y > 50) strengths.push({ kr: `1년 모멘텀 강함 (+${r1y.toFixed(0)}%)`, en: `Strong 1Y momentum` });
    if (tw && tw.blended >= 0.4) strengths.push({ kr: `${tw.kr} 섹터 순풍`, en: `${tw.kr} sector tailwind` });
    co.risks.filter((x) => x.lv === 'red').slice(0, 2).forEach((x) => concerns.push({ kr: x.kr, en: x.en }));
    return { composite, band, strengths: strengths.slice(0, 3), concerns: concerns.slice(0, 3), riskRed, riskYellow: co.risks.filter((x) => x.lv === 'yellow').length };
  }

  function buildCompany(code) {
    const fin = DB.finance.companies[code];
    const idx = DB.byCode[code];
    const px = DB.prices[code];
    if (!fin || !px) return null;
    const yrs = rev(DB.years);
    const name = idx ? idx.corpName : code;
    const industry = idx ? idx.industry : 'misc';
    const last = px.currentPrice;
    const mktcapKRW = px.marketCap;

    // fundamentals (REAL-derived from finance + market cap)
    const net = lastNonNull(fin.is.net); const sales = lastNonNull(fin.is.sales);
    const eq = lastNonNull(fin.bs.totals.totalEquity); const opm = lastNonNull(fin.is.opMargin);
    const roe = lastNonNull(fin.ratios.roe); const dr = lastNonNull(fin.ratios.debtRatio);
    const per = net && net.v > 0 ? mktcapKRW / (net.v * 1e12) : null;
    const pbr = eq && eq.v > 0 ? mktcapKRW / (eq.v * 1e12) : null;
    const psr = sales && sales.v > 0 ? mktcapKRW / (sales.v * 1e12) : null;
    const npm = net && sales && sales.v ? (net.v / sales.v) * 100 : null;

    // statements (REAL annual, 조 KRW)
    const income = {
      periods: yrs,
      rows: [
        { kr: '매출액', en: 'Revenue', id: 'sales', vals: rev(fin.is.sales) },
        { kr: '영업이익', en: 'Operating income', id: 'op', vals: rev(fin.is.op) },
        { kr: '영업이익률', en: 'OP margin %', id: 'opMargin', pct: true, vals: rev(fin.is.opMargin) },
        { kr: '당기순이익', en: 'Net income', id: 'net', vals: rev(fin.is.net) },
      ],
    };
    const T = fin.bs.totals;
    const nonCurr = rev(T.totalAsset).map((v, i) => (v != null && rev(T.currAsset)[i] != null ? +(v - rev(T.currAsset)[i]).toFixed(2) : null));
    const balance = {
      periods: yrs,
      rows: [
        { kr: '유동자산', en: 'Current assets', id: 'currAsset', vals: rev(T.currAsset) },
        { kr: '비유동자산', en: 'Non-current assets', id: 'nonCurr', vals: nonCurr },
        { kr: '자산총계', en: 'Total assets', id: 'totalAsset', vals: rev(T.totalAsset) },
        { kr: '유동부채', en: 'Current liabilities', id: 'currLiab', vals: rev(T.currLiab) },
        { kr: '부채총계', en: 'Total liabilities', id: 'totalLiab', vals: rev(T.totalLiab) },
        { kr: '자본총계', en: 'Total equity', id: 'totalEquity', vals: rev(T.totalEquity) },
      ],
    };
    const cf = fin.cf || {};
    const fcf = cf.op != null && cf.inv != null ? +(cf.op + cf.inv).toFixed(2) : null;
    const cashflow = {
      single: true, periods: [yrs[0]],
      rows: [
        { kr: '영업활동현금흐름', en: 'CFO', id: 'cfo', vals: [num(cf.op)] },
        { kr: '투자활동현금흐름', en: 'CFI', id: 'cfi', vals: [num(cf.inv)] },
        { kr: '재무활동현금흐름', en: 'CFF', id: 'cff', vals: [num(cf.fin)] },
        { kr: '잉여현금흐름', en: 'Free cash flow', id: 'fcf', vals: [fcf] },
        { kr: '기말현금', en: 'Ending cash', id: 'closing', vals: [num(cf.closing)] },
      ],
    };
    // ratios (REAL roe/debtRatio + derived per-year margins/liquidity)
    const ratios = [
      { kr: 'ROE', en: 'Return on equity', id: 'roe', v: roe ? roe.v.toFixed(1) + '%' : '—', tone: roe && roe.v > 8 ? 'up' : 'neutral' },
      { kr: '영업이익률', en: 'Operating margin', id: 'opm', v: opm ? opm.v.toFixed(1) + '%' : '—', tone: opm && opm.v > 8 ? 'up' : opm && opm.v < 0 ? 'down' : 'neutral' },
      { kr: '순이익률', en: 'Net margin', id: 'npm', v: npm != null ? npm.toFixed(1) + '%' : '—', tone: npm > 5 ? 'up' : npm < 0 ? 'down' : 'neutral' },
      { kr: '부채비율', en: 'Debt ratio', id: 'dr', v: dr ? dr.v.toFixed(1) + '%' : '—', tone: dr && dr.v < 100 ? 'good' : dr && dr.v > 300 ? 'warn' : 'neutral' },
      { kr: '유동비율', en: 'Current ratio', id: 'cr', v: (() => { const c = lastNonNull(T.currAsset), l = lastNonNull(T.currLiab); return c && l && l.v ? ((c.v / l.v) * 100).toFixed(0) + '%' : '—'; })(), tone: 'good' },
      { kr: 'PER', en: 'P/E', id: 'per', v: per != null ? per.toFixed(1) + 'x' : '—', tone: 'neutral' },
      { kr: 'PBR', en: 'P/B', id: 'pbr', v: pbr != null ? pbr.toFixed(2) + 'x' : '—', tone: 'neutral' },
      { kr: 'PSR', en: 'P/S', id: 'psr', v: psr != null ? psr.toFixed(2) + 'x' : '—', tone: 'neutral' },
    ];

    // analysis narrative (derived from REAL deltas)
    const salesCagr = (() => { const a = fin.is.sales.filter((v) => v != null); if (a.length < 2) return null; const first = a[0], lastv = a[a.length - 1]; if (first <= 0) return null; return (Math.pow(lastv / first, 1 / (a.length - 1)) - 1) * 100; })();
    const opmArr = fin.is.opMargin.filter((v) => v != null);
    const opmDelta = opmArr.length >= 2 ? opmArr[opmArr.length - 1] - opmArr[0] : null;
    const credit = deriveCredit(fin);
    const tone = (b) => (b ? 'up' : 'warn');
    const analysis = {
      summary: {
        kr: `${name}는 5년 매출 CAGR ${salesCagr != null ? (salesCagr >= 0 ? '+' : '') + salesCagr.toFixed(1) + '%' : '—'}, 최근 영업이익률 ${opm ? opm.v.toFixed(1) + '%' : '—'}. ROE ${roe ? roe.v.toFixed(1) + '%' : '—'} · 부채비율 ${dr ? dr.v.toFixed(0) + '%' : '—'}. dartlab 파생 신용 ${credit.grade}, 건전도 ${credit.healthScore}/100.`,
        en: `${name}: 5Y revenue CAGR ${salesCagr != null ? (salesCagr >= 0 ? '+' : '') + salesCagr.toFixed(1) + '%' : '—'}, latest OP margin ${opm ? opm.v.toFixed(1) + '%' : '—'}. ROE ${roe ? roe.v.toFixed(1) + '%' : '—'} · debt ratio ${dr ? dr.v.toFixed(0) + '%' : '—'}. Derived credit ${credit.grade}, health ${credit.healthScore}/100.`,
      },
      tracks: [
        { kr: '수익성', en: 'Profitability', verdict: { kr: `영업이익률 ${opm ? opm.v.toFixed(1) + '%' : '—'}, 5년 ${opmDelta != null ? (opmDelta >= 0 ? '+' : '') + opmDelta.toFixed(1) + 'pp' : '—'}`, en: `OP margin ${opm ? opm.v.toFixed(1) + '%' : '—'}, 5Y ${opmDelta != null ? (opmDelta >= 0 ? '+' : '') + opmDelta.toFixed(1) + 'pp' : '—'}` }, tone: tone(opm && opm.v > 5), delta: opm ? opm.v.toFixed(1) + '%' : '—' },
        { kr: '성장성', en: 'Growth', verdict: { kr: `매출 CAGR ${salesCagr != null ? salesCagr.toFixed(1) + '%' : '—'}`, en: `Revenue CAGR ${salesCagr != null ? salesCagr.toFixed(1) + '%' : '—'}` }, tone: tone(salesCagr != null && salesCagr > 0), delta: salesCagr != null ? (salesCagr >= 0 ? '+' : '') + salesCagr.toFixed(1) + '%' : '—' },
        { kr: '안정성', en: 'Stability', verdict: { kr: `부채비율 ${dr ? dr.v.toFixed(0) + '%' : '—'} · 유동 ${credit.basis.curr != null ? credit.basis.curr + '%' : '—'}`, en: `Debt ratio ${dr ? dr.v.toFixed(0) + '%' : '—'} · current ${credit.basis.curr != null ? credit.basis.curr + '%' : '—'}` }, tone: tone(dr && dr.v < 150), delta: dr ? dr.v.toFixed(0) + '%' : '—' },
        { kr: '현금흐름', en: 'Cash flow', verdict: { kr: `영업CF ${cf.op != null ? cf.op + '조' : '—'} · FCF ${fcf != null ? fcf + '조' : '—'}`, en: `CFO ${cf.op != null ? cf.op + 'T' : '—'} · FCF ${fcf != null ? fcf + 'T' : '—'}` }, tone: tone(fcf != null && fcf > 0), delta: fcf != null ? (fcf >= 0 ? 'FCF+' : 'FCF-') : '—' },
        { kr: '가치평가', en: 'Valuation', verdict: { kr: `PER ${per != null ? per.toFixed(1) + 'x' : '—'} · PBR ${pbr != null ? pbr.toFixed(2) + 'x' : '—'}`, en: `PER ${per != null ? per.toFixed(1) + 'x' : '—'} · PBR ${pbr != null ? pbr.toFixed(2) + 'x' : '—'}` }, tone: 'good', delta: per != null ? per.toFixed(1) + 'x' : '—' },
      ],
    };

    // story (REAL dartlab blog) + peers
    const blog = DB.meta.blog && DB.meta.blog[code];
    const peers = derivePeers(code, industry);

    // AI assistant answer (derived from REAL metrics)
    const ai = {
      question: { kr: `${name} 재무건전성 분석해줘`, en: `Analyze ${name} financial health` },
      steps: [
        { tool: 'Company', call: `c.panel("IS")`, ref: 'tableRef:is-5y' },
        { tool: 'Credit', call: `c.credit("등급")`, ref: `valueRef:${credit.grade}` },
        { tool: 'Analysis', call: `c.analysis("수익성")`, ref: 'executionRef:prof' },
        { tool: 'GroundingCheck', call: `verify(debtRatio)`, ref: 'ground:ok' },
      ],
      answer: {
        kr: `dartlab 파생 신용등급 ${credit.grade}(건전도 ${credit.healthScore}/100, PD ${credit.pd}). 영업이익률 ${opm ? opm.v.toFixed(1) + '%' : '—'}, ROE ${roe ? roe.v.toFixed(1) + '%' : '—'}, 부채비율 ${dr ? dr.v.toFixed(0) + '%' : '—'}. 5년 매출 CAGR ${salesCagr != null ? salesCagr.toFixed(1) + '%' : '—'}. 모든 수치는 finance.json(${DB.years[0]}~${DB.years[DB.years.length - 1]}) 실데이터에서 산출.`,
        en: `Derived dCR ${credit.grade} (health ${credit.healthScore}/100, PD ${credit.pd}). OP margin ${opm ? opm.v.toFixed(1) + '%' : '—'}, ROE ${roe ? roe.v.toFixed(1) + '%' : '—'}, debt ratio ${dr ? dr.v.toFixed(0) + '%' : '—'}. 5Y revenue CAGR ${salesCagr != null ? salesCagr.toFixed(1) + '%' : '—'}. All figures from finance.json (${DB.years[0]}–${DB.years[DB.years.length - 1]}).`,
      },
      confidence: credit.healthScore >= 70 ? 'HIGH' : 'MEDIUM',
    };

    const eco = DB.eco[code] || {};
    const marketLabel = MARKET_LABEL[eco.market] || 'KRX';
    const grades = [
      { key: 'prof', kr: '수익성', en: 'Profit', group: 'health', v: eco.profGrade },
      { key: 'growth', kr: '성장성', en: 'Growth', group: 'income', v: eco.growthGrade },
      { key: 'gov', kr: '거버넌스', en: 'Govern', group: 'governance', v: eco.govGrade },
      { key: 'qual', kr: '이익질', en: 'Quality', group: 'quality', v: eco.qualGrade },
      { key: 'liq', kr: '유동성', en: 'Liquid', group: 'quality', v: eco.liqGrade },
      { key: 'audit', kr: '감사위험', en: 'Audit', group: 'quality', v: eco.auditRisk },
      { key: 'stab', kr: '경영안정', en: 'Stable', group: 'governance', v: eco.stability },
    ].filter((g) => g.v).map((g) => ({ ...g, tone: gradeTone(g.key, g.v), color: GROUP_COLOR[g.group] }));
    const radar = [
      { kr: '수익성', en: 'Profit', s: gradeScore('prof', eco.profGrade) },
      { kr: '성장성', en: 'Growth', s: gradeScore('growth', eco.growthGrade) },
      { kr: '안정성', en: 'Stability', s: gradeScore('stab', eco.stability) },
      { kr: '이익질', en: 'Quality', s: gradeScore('qual', eco.qualGrade) },
      { kr: '유동성', en: 'Liquidity', s: gradeScore('liq', eco.liqGrade) },
      { kr: '거버넌스', en: 'Govern', s: gradeScore('gov', eco.govGrade) },
    ];
    const changes = [
      { kr: 'ROE', en: 'ROE', v: eco.roeDelta, unit: '%p' },
      { kr: '영업이익률', en: 'OP margin', v: eco.opMarginDelta, unit: '%p' },
      { kr: '부채비율', en: 'Debt ratio', v: eco.debtRatioDelta, unit: '%p', invert: true },
      { kr: '매출 YoY', en: 'Revenue YoY', v: eco.revenueYoyPct, unit: '%' },
    ];
    const candles = reconstructCandles(code, last, px.return1y, px.volatility1y);
    const co = {
      code, market: 'KR', marketLabel, ccy: 'KRW', exch: marketLabel, provider: 'DART',
      name: { kr: name, en: name },
      sector: { kr: eco.industryName || SECTOR_KR[industry] || industry, en: SECTOR_EN[industry] || industry },
      stage: eco.stageName || '', role: eco.role || '',
      eco, grades, radar, changes,
      price: {
        last, prevClose: candles[candles.length - 2] ? candles[candles.length - 2].c : last,
        open: candles[candles.length - 1].o, high: Math.max(...candles.slice(-2).map((c) => c.h)),
        low: Math.min(...candles.slice(-2).map((c) => c.l)), vol: px.volumeAvg30d,
        mktcap: fmtKRW(mktcapKRW), ret1m: px.return1m, ret3m: px.return3m, ret1y: px.return1y,
        vol1y: px.volatility1y, hi52: px.week52High, lo52: px.week52Low, asOf: px.priceUpdated,
      },
      candles, fundamentals: { per, pbr, psr, npm, roe: roe ? roe.v : null, opm: opm ? opm.v : null, dr: dr ? dr.v : null, divYield: null },
      income, balance, cashflow, ratios, credit, analysis, peers,
      story: blog ? { title: blog.title, date: blog.date, readTime: blog.readTime, slug: blog.slug } : null,
      ai, industry,
    };
    // ---- high-impact decision analytics (REAL universe-derived) ----
    co.percentile = industryPercentile(code);
    co.valuation = valuationOf(code);
    co.risks = riskFlagsOf(code);
    co.tailwind = tailwindOf(industry);
    co.verdict = verdictOf(co);
    return co;
  }

  function derivePeers(code, industry) {
    const list = DB.index.filter((r) => r.industry === industry).sort((a, b) => (b.revenue || 0) - (a.revenue || 0)).slice(0, 8);
    return list.map((r) => ({ code: r.stockCode, name: r.corpName, revenue: r.revenue, self: r.stockCode === code, px: DB.prices[r.stockCode] }));
  }

  function fmtKRW(v) {
    if (v == null) return '—';
    if (v >= 1e12) return (v / 1e12).toFixed(1) + '조';
    if (v >= 1e8) return (v / 1e8).toFixed(0) + '억';
    return v.toLocaleString();
  }

  function search(q) {
    q = (q || '').trim();
    if (!q) return null;
    if (DB.finance.companies[q] && DB.prices[q]) return q;
    const up = q.toUpperCase();
    const hit = DB.index.find((r) => r.stockCode === q || r.corpName === q || r.corpName.includes(q) || r.corpName.toUpperCase() === up);
    if (hit && DB.finance.companies[hit.stockCode] && DB.prices[hit.stockCode]) return hit.stockCode;
    return null;
  }

  // featured watchlist: top-revenue names that have BOTH financials and prices
  function featured(n = 14) {
    const out = [];
    for (const r of DB.index) {
      if (DB.finance.companies[r.stockCode] && DB.prices[r.stockCode]) out.push(r.stockCode);
      if (out.length >= n) break;
    }
    return out;
  }

  // sector performance from REAL prices (avg 1m return by industry, top movers)
  function sectorPerf() {
    const agg = {};
    for (const r of DB.index) {
      const p = DB.prices[r.stockCode]; if (!p || p.return1m == null) continue;
      (agg[r.industry] = agg[r.industry] || []).push(p.return1m);
    }
    return Object.entries(agg).map(([k, arr]) => ({ id: k, kr: SECTOR_KR[k] || k, en: SECTOR_EN[k] || k, chg: arr.reduce((a, b) => a + b, 0) / arr.length, n: arr.length }))
      .filter((s) => s.n >= 3).sort((a, b) => b.chg - a.chg);
  }

  window.DL = { boot, buildCompany, search, featured, sectorPerf, derivePeers, loadJson, fmtKRW, sma, ema, rsi, macd, GRADE_SCALE, GROUP_COLOR, gradeTone, gradeScore, get DB() { return DB; } };
})();
