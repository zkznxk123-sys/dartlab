/* =========================================================================
   DartLab Terminal — LEFT RAIL (KR · ecosystem grades)
   Macro Quadrant · Screener(grade chips) · Sector Map · Movers
   ========================================================================= */
(function () {
const { Panel, tx, txc, chgClass, toneClass, sign, heat } = window.UI;
const { fmtNum } = window.ChartKit;
const tcls = (t) => ({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' })[t] || 'tNeu';

function MacroQuadrant({ lang }) {
  const m = DL.DB.macro;
  function box(side, label) {
    const q = m[side].quadrant; const ai = q.assetImplication;
    const chips = [['주식', 'equity'], ['채권', 'bond'], ['원자재', 'commodity'], ['금', 'gold'], ['현금', 'cash']];
    const cls = (w) => (w === 'overweight' ? 'ow' : w === 'underweight' ? 'uw' : 'nu');
    return (
      <div className="quadBox" key={side}>
        <div className="quadMkt">{label} · {lang === 'en' ? m[side].phase.toUpperCase() : m[side].phaseLabel}</div>
        <div className={'quadPhase ' + (q.growth === 'rising' ? 'tUp' : 'tDn')}>{lang === 'en' ? q.quadrant : q.quadrantLabel}</div>
        <div className="quadDesc">{q.description}</div>
        <div className="quadAssets">{chips.map(([kr, key]) => <span key={key} className={'assetChip ' + cls(ai[key])}>{lang === 'en' ? key.slice(0, 4) : kr}</span>)}</div>
      </div>
    );
  }
  return (
    <Panel lang={lang} className="eMacro" prov="live" title={{ kr: '마켓 펄스 · 매크로', en: 'MARKET PULSE' }} sub={{ kr: 'dartlab.macro', en: 'dartlab.macro' }} right={<span className="liveDot">LIVE</span>} flush>
      <div className="quadWrap">{box('kr', 'KR')}{box('us', 'US')}</div>
    </Panel>
  );
}

function Screener({ lang, onPick, active }) {
  const codes = DL.featured(18);
  return (
    <Panel lang={lang} className="eQuant" prov="live" title={{ kr: '스캔 스크리너', en: 'SCAN SCREENER' }} sub={{ kr: 'ecosystem 등급', en: 'ecosystem grades' }} right={<span className="dim">{codes.length}</span>} flush>
      <div style={{ overflowY: 'auto', maxHeight: '300px' }}>
        {codes.map((c) => {
          const eco = DL.DB.eco[c] || {}; const px = DL.DB.prices[c]; const idx = DL.DB.byCode[c]; if (!px) return null;
          const pills = [
            { v: eco.profGrade, t: DL.gradeTone('prof', eco.profGrade) },
            { v: eco.growthGrade, t: DL.gradeTone('growth', eco.growthGrade) },
          ].filter((p) => p.v);
          return (
            <div key={c} className={'scrRow' + (active === c ? ' on' : '')} onClick={() => onPick && onPick(c)}>
              <span className="scrName"><b>{idx ? idx.corpName : c}</b><span className="si">{c} · {eco.industryName || ''}</span></span>
              <span className="scrGrades">{pills.map((p, i) => <span key={i} className={'gPill ' + tcls(p.t)}>{p.v}</span>)}</span>
              <span className={'scrRet ' + chgClass(px.return1m)}>{sign(px.return1m, 1)}</span>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function SectorMap({ lang }) {
  const s = DL.sectorPerf().slice(0, 12);
  const max = Math.max(...s.map((x) => Math.abs(x.chg)), 1);
  return (
    <Panel lang={lang} className="eIndustry" prov="live" title={{ kr: '섹터 맵', en: 'SECTOR MAP' }} sub={{ kr: '평균 1M', en: 'avg 1M' }}>
      <div className="sectorGrid">
        {s.map((x) => (
          <div key={x.id} className="sectorCell" style={{ background: heat(x.chg, max) }}>
            <span className="sName">{txc(x, lang)}</span>
            <span className={'sChg ' + chgClass(x.chg)}>{sign(x.chg, 1)}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Movers({ lang, onPick }) {
  const codes = DL.featured(60);
  const rows = codes.map((c) => ({ c, p: DL.DB.prices[c], idx: DL.DB.byCode[c] })).filter((r) => r.p && r.p.return1m != null);
  const sorted = rows.slice().sort((a, b) => b.p.return1m - a.p.return1m);
  const up = sorted.slice(0, 6), dn = sorted.slice(-6).reverse();
  const row = (r) => (
    <div key={r.c} className="moverRow" onClick={() => onPick && onPick(r.c)}>
      <span className="mn">{r.idx ? r.idx.corpName : r.c}</span>
      <span className={'mv ' + chgClass(r.p.return1m)}>{sign(r.p.return1m, 1)}</span>
    </div>
  );
  return (
    <Panel lang={lang} className="eQuant" prov="live" title={{ kr: '톱 무버스', en: 'TOP MOVERS' }} sub={{ kr: '1M', en: '1M' }} flush>
      <div className="moversWrap">
        <div className="moverCol"><div className="moverHd tUp">▲ {lang === 'en' ? 'GAINERS' : '상승'}</div>{up.map(row)}</div>
        <div className="moverCol"><div className="moverHd tDn">▼ {lang === 'en' ? 'LOSERS' : '하락'}</div>{dn.map(row)}</div>
      </div>
    </Panel>
  );
}

window.LeftPanels = { MacroQuadrant, Screener, SectorMap, Movers };
})();
