/* =========================================================================
   DartLab Terminal — SHARED UI PRIMITIVES
   ========================================================================= */
(function(){
const { fmtNum, fmtAbbr } = window.ChartKit;

// bilingual resolver — lang: 'kr' | 'en' | 'dual'
function tx(obj, lang) {
  if (obj == null) return '';
  if (typeof obj === 'string') return obj;
  if (lang === 'dual') return obj.kr + (obj.en && obj.en !== obj.kr ? ' · ' + obj.en : '');
  return obj[lang] || obj.kr || obj.en || '';
}

// compact resolver — for dense tabular labels: 'dual' collapses to KR
function txc(obj, lang) {
  if (obj == null) return '';
  if (typeof obj === 'string') return obj;
  return lang === 'en' ? (obj.en || obj.kr) : (obj.kr || obj.en);
}

// provenance badge — marks real vs derived vs not-yet-wired data
const PROV = {
  live: { kr: 'LIVE', en: 'LIVE', cls: 'pLive', t: { kr: 'HuggingFace 실데이터', en: 'real HF data' } },
  derived: { kr: '파생', en: 'DERIVED', cls: 'pDeriv', t: { kr: '실데이터에서 계산 (엔진출력 아님)', en: 'computed from real data' } },
  wire: { kr: '배선필요', en: 'WIRE', cls: 'pWire', t: { kr: '비실데이터 — 연동 필요', en: 'not real data — needs wiring' } },
};
function ProvTag({ prov, lang }) {
  const p = PROV[prov]; if (!p) return null;
  return <span className={'provTag ' + p.cls} title={lang === 'en' ? p.t.en : p.t.kr}>{lang === 'en' ? p.en : p.kr}</span>;
}

// Panel shell — title bar + provenance badge + scroll body
function Panel({ id, title, sub, right, children, lang, className = '', flush, prov }) {
  return (
    <section className={'panel ' + className} data-screen-label={typeof title === 'string' ? title : (title && title.en)}>
      <header className="panelHead">
        <span className="panelTitle">{tx(title, lang)}</span>
        {prov && <ProvTag prov={prov} lang={lang} />}
        {sub && <span className="panelSub">{tx(sub, lang)}</span>}
        <span className="panelRight">{right}</span>
      </header>
      <div className={'panelBody' + (flush ? ' flush' : '')}>{children}</div>
    </section>
  );
}

function toneClass(t) {
  return ({ up: 'tUp', down: 'tDn', good: 'tGood', warn: 'tWarn', neutral: 'tNeu' })[t] || '';
}
function chgClass(n) { return n > 0 ? 'tUp' : n < 0 ? 'tDn' : 'tNeu'; }
function sign(n, d = 2) { return (n > 0 ? '+' : '') + fmtNum(n, d); }

// heat color for correlation / change cells
function heat(v, max = 1) {
  const t = Math.max(-1, Math.min(1, v / max));
  if (t >= 0) return `rgba(54,211,153,${0.08 + t * 0.5})`;
  return `rgba(255,91,110,${0.08 + (-t) * 0.5})`;
}

window.UI = { tx, txc, Panel, toneClass, chgClass, sign, heat };
})();
