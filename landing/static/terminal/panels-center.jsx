/* =========================================================================
   DartLab Terminal — CENTER (KR · ecosystem grades)
   Symbol header · Grade strip · Price action · Radar · Returns · Fundamentals · Analysis
   ========================================================================= */
(function () {
const { Panel, tx, txc, chgClass, toneClass, sign, heat } = window.UI;
const { PriceChart, Radar, fmtNum, fmtAbbr } = window.ChartKit;
const tcls = (t) => ({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' })[t] || 'tNeu';

function SymbolHeader({ co, lang }) {
  const p = co.price; const e = co.eco;
  const stats = [
    { l: '1M', v: p.ret1m == null ? '—' : sign(p.ret1m, 1) + '%', t: chgClass(p.ret1m) },
    { l: '3M', v: p.ret3m == null ? '—' : sign(p.ret3m, 1) + '%', t: chgClass(p.ret3m) },
    { l: '1Y', v: p.ret1y == null ? '—' : sign(p.ret1y, 0) + '%', t: chgClass(p.ret1y) },
    { l: lang === 'en' ? 'MKT CAP' : '시가총액', v: p.mktcap, t: '' },
    { l: lang === 'en' ? 'M.SHARE' : '점유율', v: e.marketShare != null ? e.marketShare.toFixed(1) + '%' : '—', t: '' },
    { l: lang === 'en' ? 'RANK' : '산업순위', v: e.industryRank != null ? e.industryRank + '/' + (e.industryPeerCount || '—') : '—', t: '' },
  ];
  return (
    <div className="symHead">
      <div className="symId">
        <div className="symTop">
          <span className="symCode">{co.code}</span>
          <span className="symBadge kr">{co.marketLabel}</span>
          <span className="symName">{co.name.kr}</span>
        </div>
        <div className="symMeta">{tx(co.sector, lang)}{co.stage ? ' · ' + co.stage : ''}{co.role ? ' · ' + co.role : ''} · DART</div>
      </div>
      <div className="symPrice">
        <span className="symLast">{fmtNum(p.last)}</span>
        <span className={'symChg ' + chgClass(p.ret1m)}>{p.ret1m == null ? '' : sign(p.ret1m, 2) + '% · 1M'}</span>
      </div>
      <div className="symStats">{stats.map((s) => (<div key={s.l} className="symStat"><span>{s.l}</span><b className={'mono ' + s.t}>{s.v}</b></div>))}</div>
    </div>
  );
}

function GradeStrip({ co, lang }) {
  const e = co.eco;
  const meta = [
    { l: lang === 'en' ? 'M.SHARE' : '점유율', v: e.marketShare != null ? e.marketShare.toFixed(1) + '%' : '—' },
    { l: lang === 'en' ? 'IND.RANK' : '산업순위', v: e.industryRank != null ? e.industryRank + '위/' + (e.industryPeerCount || '—') : '—' },
    { l: lang === 'en' ? 'OWNER' : '대주주', v: e.holderPct != null ? e.holderPct.toFixed(1) + '%' : '—' },
    { l: lang === 'en' ? 'EMPLOYEES' : '임직원', v: e.empCount != null ? e.empCount.toLocaleString() + (lang === 'en' ? '' : '명') : '—' },
    { l: 'ROE', v: e.roe != null ? e.roe.toFixed(1) + '%' : '—' },
    { l: lang === 'en' ? 'OP MGN' : '영업이익률', v: e.opMargin != null ? e.opMargin.toFixed(1) + '%' : '—' },
  ];
  return (
    <Panel lang={lang} className="eAnalysis" prov="live" title={{ kr: '스캔 등급', en: 'SCAN GRADES' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }} right={<span className="dim">{co.grades.length} {lang === 'en' ? 'axes' : '축'}</span>} flush>
      <div className="ecoMeta">{meta.map((m) => (<div key={m.l} className="em"><span>{m.l}</span><b>{m.v}</b></div>))}</div>
      <div className="gradeStrip" style={{ gridTemplateColumns: `repeat(${co.grades.length || 1}, 1fr)` }}>
        {co.grades.map((g) => (
          <div key={g.key} className="gradeChip" style={{ '--gc': g.color }}>
            <span className="gcLabel">{txc(g, lang)}</span>
            <span className={'gcVal ' + tcls(g.tone)}>{g.v}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function PriceAction({ co, lang, period, setPeriod, indicator, setIndicator }) {
  const periods = ['1M', '3M', '6M', '1Y']; const inds = ['RSI', 'MACD'];
  return (
    <Panel lang={lang} className="eQuant" prov="wire" title={{ kr: '프라이스 액션', en: 'PRICE ACTION' }}
      sub={{ kr: 'gather.price · σ재구성', en: 'gather.price · σ-recon' }}
      right={<span className="chartCtl">
        <span className="segGroup">{periods.map((x) => <button key={x} className={period === x ? 'seg on' : 'seg'} onClick={() => setPeriod(x)}>{x}</button>)}</span>
        <span className="segGroup">{inds.map((x) => <button key={x} className={indicator === x ? 'seg on' : 'seg'} onClick={() => setIndicator(x)}>{x}</button>)}</span>
      </span>} flush>
      <PriceChart candles={co.candles} period={period} indicator={indicator} ccy={co.ccy} />
    </Panel>
  );
}

function RadarPanel({ co, lang }) {
  return (
    <Panel lang={lang} className="eIndustry" prov="live" title={{ kr: '종합 스노우플레이크', en: 'SNOWFLAKE' }} sub={{ kr: '6축 등급', en: '6-axis' }} flush>
      <div className="radarWrap">
        <Radar data={co.radar} lang={lang} size={104} />
        <div className="radarLegend">
          {co.radar.map((d) => (
            <div key={d.en} className="rl"><span>{txc(d, lang)}</span><b className={d.s == null ? 'tNeu' : d.s >= 0.66 ? 'tUp' : d.s >= 0.4 ? 'tNeu' : 'tDn'}>{d.s == null ? '—' : Math.round(d.s * 100)}</b></div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function ReturnsRisk({ co, lang }) {
  const p = co.price;
  const cells = [{ l: '1M', v: p.ret1m }, { l: '3M', v: p.ret3m }, { l: '1Y', v: p.ret1y }, { l: 'σ 1Y', v: p.vol1y, neu: true }];
  const pos = p.hi52 && p.lo52 && p.hi52 > p.lo52 ? Math.max(0, Math.min(1, (p.last - p.lo52) / (p.hi52 - p.lo52))) : 0.5;
  return (
    <Panel lang={lang} className="eQuant" prov="live" title={{ kr: '수익률 · 리스크', en: 'RETURNS · RISK' }} sub={{ kr: 'prices-snapshot', en: 'prices-snapshot' }} flush>
      <div className="retGrid">{cells.map((c) => (<div key={c.l} className="retCell"><span>{c.l}</span><b className={c.neu ? 'tNeu' : chgClass(c.v)}>{c.v == null ? '—' : sign(c.v, 1) + '%'}</b></div>))}</div>
      <div className="w52">
        <div className="w52Lbl"><span>{lang === 'en' ? '52W LOW' : '52주 최저'}</span><span>{lang === 'en' ? '52W HIGH' : '52주 최고'}</span></div>
        <div className="w52Track"><div className="w52Fill" style={{ width: (pos * 100) + '%' }}></div><div className="w52Dot" style={{ left: (pos * 100) + '%' }}></div></div>
        <div className="w52Lbl"><span className="mono">{fmtNum(p.lo52)}</span><span className="dim mono">{fmtNum(p.last)}</span><span className="mono">{fmtNum(p.hi52)}</span></div>
      </div>
      <div className="finNote">price as of {p.asOf} · KRX</div>
    </Panel>
  );
}

function Fundamentals({ co, lang }) {
  const f = co.fundamentals;
  const cells = [
    { l: 'PER', v: f.per != null ? f.per.toFixed(1) + 'x' : '—' },
    { l: 'PBR', v: f.pbr != null ? f.pbr.toFixed(2) + 'x' : '—' },
    { l: 'PSR', v: f.psr != null ? f.psr.toFixed(2) + 'x' : '—' },
    { l: 'ROE', v: f.roe != null ? f.roe.toFixed(1) + '%' : '—' },
    { l: lang === 'en' ? 'NET MGN' : '순이익률', v: f.npm != null ? f.npm.toFixed(1) + '%' : '—' },
    { l: lang === 'en' ? 'DEBT R' : '부채비율', v: f.dr != null ? f.dr.toFixed(0) + '%' : '—' },
  ];
  return (
    <Panel lang={lang} className="eValuation" prov="derived" title={{ kr: '가치 · 펀더멘털', en: 'VALUATION' }} sub={{ kr: 'finance · derived', en: 'derived' }} flush>
      <div className="fundGrid">{cells.map((c) => (<div key={c.l} className="fundCell"><span className="fundL">{c.l}</span><span className="fundV mono">{c.v}</span></div>))}</div>
    </Panel>
  );
}

function Analysis({ co, lang }) {
  const a = co.analysis;
  return (
    <Panel lang={lang} className="eAnalysis" prov="derived" title={{ kr: '재무 분석', en: 'FINANCIAL ANALYSIS' }} sub={{ kr: 'c.analysis', en: 'c.analysis' }} flush>
      <div className="anSummary">{tx(a.summary, lang)}</div>
      <div className="anTracks">
        {a.tracks.map((t) => (
          <div key={t.en} className="anRow"><span className="anName">{txc(t, lang)}</span><span className={'anDelta mono ' + toneClass(t.tone)}>{t.delta}</span><span className="anVerdict">{tx(t.verdict, lang)}</span></div>
        ))}
      </div>
    </Panel>
  );
}

function Verdict({ co, lang }) {
  const v = co.verdict; const tw = co.tailwind;
  return (
    <Panel lang={lang} className="eAnalysis" prov="derived" title={{ kr: '투자 종합 판단', en: 'VERDICT' }} sub={{ kr: 'grades+value+momentum', en: 'composite' }}
      right={tw ? <span className={'dim ' + (tw.tone === 'up' ? 'tUp' : tw.tone === 'down' ? 'tDn' : '')}>{txc({ kr: tw.kr, en: tw.kr }, lang)} {tw.label}</span> : null} flush>
      <div className="verdictWrap">
        <div className="verdictScore">
          <span className={'vsNum ' + tcls(v.band.tone)}>{v.composite}</span>
          <span className={'vsBand ' + tcls(v.band.tone)}>{lang === 'en' ? v.band.en : v.band.kr}</span>
          <span className="vsLabel">{lang === 'en' ? 'dartlab score' : '종합점수'}</span>
        </div>
        <div className="verdictBody">
          <div className="vRow s"><span className="vk">{lang === 'en' ? 'STRENGTH' : '강점'}</span><span className="vList">{v.strengths.length ? v.strengths.map((s, i) => <span key={i}>· {txc(s, lang)}</span>) : <span className="dim">—</span>}</span></div>
          <div className="vRow c"><span className="vk">{lang === 'en' ? 'CONCERN' : '우려'}</span><span className="vList">{v.concerns.length ? v.concerns.map((s, i) => <span key={i}>· {txc(s, lang)}</span>) : <span className="dim">{lang === 'en' ? 'none flagged' : '특이사항 없음'}</span>}</span></div>
        </div>
      </div>
      <div className="vRiskline">
        <span>{lang === 'en' ? 'Red flags' : '위험 신호'} <b className="tDn">{v.riskRed}</b></span>
        <span>{lang === 'en' ? 'Watch' : '주의'} <b className="tWarn">{v.riskYellow}</b></span>
        {co.tailwind && <span>{lang === 'en' ? 'Sector' : '섹터'} <b className={co.tailwind.tone === 'up' ? 'tUp' : co.tailwind.tone === 'down' ? 'tDn' : 'tNeu'}>{co.tailwind.label}</b></span>}
        <span className="dim" style={{ marginLeft: 'auto' }}>{lang === 'en' ? 'diagnosis, not advice' : '진단 — 투자권유 아님'}</span>
      </div>
    </Panel>
  );
}

function Valuation({ co, lang }) {
  const v = co.valuation;
  if (!v) return (<Panel lang={lang} className="eValuation" prov="derived" title={{ kr: '밸류에이션', en: 'VALUATION' }} flush><div className="storyEmpty">{lang === 'en' ? 'Insufficient data.' : '데이터 부족.'}</div></Panel>);
  const cheap = v.upside != null && v.upside > 8; const rich = v.upside != null && v.upside < -8;
  // fair band positions on a scale spanning [min(low,last)*.9, max(high,last)*1.1]
  const lo = Math.min(v.fairLow || v.last, v.last) * 0.9, hi = Math.max(v.fairHigh || v.last, v.last) * 1.1;
  const pos = (x) => Math.max(0, Math.min(100, ((x - lo) / (hi - lo)) * 100));
  return (
    <Panel lang={lang} className="eValuation" prov="derived" title={{ kr: '밸류에이션 위치', en: 'VALUATION' }} sub={{ kr: '업종 중앙값 대비', en: 'vs peer median' }}
      right={<span className={cheap ? 'tUp' : rich ? 'tDn' : 'tNeu'}>{v.upside != null ? (v.upside >= 0 ? '+' : '') + v.upside.toFixed(0) + '%' : '—'}</span>} flush>
      <div className="valTop">
        <div className="valCell"><div className="vl">PER</div><div className={'vv ' + (v.per != null && v.perMed && v.per <= v.perMed ? 'tUp' : 'tDn')}>{v.per != null ? v.per.toFixed(1) + 'x' : '—'}</div><div className="vsub">{lang === 'en' ? 'peer med' : '업종중앙'} {v.perMed != null ? v.perMed.toFixed(1) + 'x' : '—'}</div></div>
        <div className="valCell"><div className="vl">PBR</div><div className={'vv ' + (v.pbr != null && v.pbrMed && v.pbr <= v.pbrMed ? 'tUp' : 'tDn')}>{v.pbr != null ? v.pbr.toFixed(2) + 'x' : '—'}</div><div className="vsub">{lang === 'en' ? 'peer med' : '업종중앙'} {v.pbrMed != null ? v.pbrMed.toFixed(2) + 'x' : '—'}</div></div>
      </div>
      {v.fairMid != null && (
        <div className="fairBand">
          <div className="fairTrack">
            <div className="fairRange" style={{ left: pos(v.fairLow) + '%', width: (pos(v.fairHigh) - pos(v.fairLow)) + '%' }}></div>
            <div className="fairNow" style={{ left: pos(v.last) + '%' }}></div>
          </div>
          <div className="fairLbl"><span>{fmtNum(Math.round(v.fairLow))}</span><span className="tAmber">{lang === 'en' ? 'now ' : '현재 '}{fmtNum(v.last)}</span><span>{fmtNum(Math.round(v.fairHigh))}</span></div>
        </div>
      )}
      <div className="valVerdict">{v.upside == null ? (lang === 'en' ? 'Fair value n/a.' : '적정가 산출 불가.') : cheap ? (lang === 'en' ? `Trades below peer-median multiples — ~${v.upside.toFixed(0)}% to fair value.` : `업종 중앙값 멀티플 대비 저평가 — 적정가까지 약 +${v.upside.toFixed(0)}% 여력.`) : rich ? (lang === 'en' ? `Above peer median — ${Math.abs(v.upside).toFixed(0)}% rich.` : `업종 중앙값 대비 고평가 — 약 ${Math.abs(v.upside).toFixed(0)}% 비쌈.`) : (lang === 'en' ? 'Roughly in line with peers.' : '업종 평균 수준의 밸류에이션.')}</div>
    </Panel>
  );
}

window.CenterPanels = { SymbolHeader, GradeStrip, PriceAction, RadarPanel, ReturnsRisk, Fundamentals, Analysis, Verdict, Valuation };
})();
