/* =========================================================================
   DartLab Terminal — RIGHT (KR · ecosystem grades)
   Financials · Credit · Changes(Δ) · Peers · Governance · Story · AI
   ========================================================================= */
(function () {
const { Panel, tx, txc, chgClass, toneClass, sign, heat } = window.UI;
const { fmtNum, fmtAbbr } = window.ChartKit;
const tcls = (t) => ({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' })[t] || 'tNeu';

function Financials({ co, lang, stmt, setStmt, acct, setAcct }) {
  const summary = { periods: co.income.periods, rows: co.income.rows.concat(co.balance.rows.filter((r) => ['totalAsset', 'totalLiab', 'totalEquity'].includes(r.id))) };
  const map = { SUM: summary, IS: co.income, BS: co.balance, CF: co.cashflow };
  const tabs = [{ k: 'SUM', kr: '요약', en: 'Key' }, { k: 'IS', kr: '손익', en: 'IS' }, { k: 'BS', kr: '재무상태', en: 'BS' }, { k: 'CF', kr: '현금흐름', en: 'CF' }, { k: 'RT', kr: '비율', en: 'Ratios' }];
  return (
    <Panel lang={lang} className="eAnalysis" prov="live" title={{ kr: '재무제표', en: 'FINANCIAL STATEMENTS' }} sub={{ kr: 'c.panel · 연간', en: 'c.panel · annual' }}
      right={<span className="finCtl"><button className={'seg acct ' + (acct === 'kr' ? 'on' : '')} onClick={() => setAcct(acct === 'kr' ? 'en' : 'kr')}>{acct === 'kr' ? '한글' : 'EN'}</button></span>} flush>
      <div className="finTabs">{tabs.map((t) => <button key={t.k} className={'finTab ' + (stmt === t.k ? 'on' : '')} onClick={() => setStmt(t.k)}>{lang === 'en' ? t.en : t.kr}</button>)}</div>
      {stmt === 'RT' ? <RatiosTable co={co} acct={acct} /> : <StatementTable data={map[stmt] || summary} acct={acct} lang={lang} />}
      <div className="finNote">finance.json · {co.income.periods[co.income.periods.length - 1]}–{co.income.periods[0]} · 조 KRW</div>
    </Panel>
  );
}
function StatementTable({ data, acct, lang }) {
  return (
    <div className="finScroll"><table className="finTable">
      <thead><tr><th className="finAcct">{lang === 'en' ? 'ACCOUNT' : '계정'}</th>{data.periods.map((p) => <th key={p} className="r">{p}</th>)}</tr></thead>
      <tbody>{data.rows.map((r) => (
        <tr key={r.id} className={['op', 'net', 'fcf', 'totalEquity', 'totalAsset'].includes(r.id) ? 'finKey' : ''}>
          <td className="finAcct">{acct === 'kr' ? r.kr : r.en}</td>
          {r.vals.map((v, i) => (<td key={i} className={'r mono ' + (r.pct ? (v >= 8 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu') : (v < 0 ? 'tDn' : ''))}>{v == null ? '—' : r.pct ? v.toFixed(1) + '%' : fmtNum(v, 1)}</td>))}
        </tr>
      ))}</tbody>
    </table></div>
  );
}
function RatiosTable({ co, acct }) {
  return (
    <div className="finScroll"><table className="finTable"><tbody>
      {co.ratios.map((r) => (<tr key={r.id}><td className="finAcct">{acct === 'kr' ? r.kr : r.en}</td><td className="finAcct dim">{acct === 'kr' ? r.en : r.kr}</td><td className={'r mono ' + toneClass(r.tone)}>{r.v}</td></tr>))}
    </tbody></table></div>
  );
}

function Credit({ co, lang }) {
  const c = co.credit;
  return (
    <Panel lang={lang} className="eCredit" prov="derived" title={{ kr: '신용 분석', en: 'CREDIT' }} sub={{ kr: 'c.credit · derived', en: 'derived' }} right={<span className="dim">{lang === 'en' ? '7-axis spirit' : '7축 정신'}</span>} flush>
      <div className="creditTop"><div className="creditGrade"><span className="cgVal tCredit">{c.grade}</span><span className="cgSub">{lang === 'en' ? 'health' : '건전도'} <b className={toneClass(c.tone)}>{c.healthScore}</b>/100 · PD <b className="tNeu">{c.pd}</b></span></div></div>
      <div className="creditTracks">{c.tracks.map((t) => (<div key={t.en} className="ctRow"><span className="ctName">{txc(t, lang)}</span><div className="ctTrack"><div className="ctFill" style={{ width: t.score + '%' }}></div></div><span className="ctVal mono">{t.score}</span></div>))}</div>
      <div className="creditDiv">{lang === 'en' ? `Derived from finance.json: debt ${c.basis.debtRatio != null ? c.basis.debtRatio.toFixed(0) + '%' : '—'}, current ${c.basis.curr != null ? c.basis.curr + '%' : '—'}, OP margin ${c.basis.opm != null ? c.basis.opm.toFixed(1) + '%' : '—'}. Heuristic dCR — not official.` : `finance.json 기반: 부채비율 ${c.basis.debtRatio != null ? c.basis.debtRatio.toFixed(0) + '%' : '—'}, 유동비율 ${c.basis.curr != null ? c.basis.curr + '%' : '—'}, 영업이익률 ${c.basis.opm != null ? c.basis.opm.toFixed(1) + '%' : '—'}. 휴리스틱 dCR — 공식등급 아님.`}</div>
    </Panel>
  );
}

function Changes({ co, lang }) {
  const ch = co.changes;
  const max = Math.max(...ch.map((c) => (c.v == null ? 0 : Math.abs(c.v))), 1);
  return (
    <Panel lang={lang} className="eChanges" prov="live" title={{ kr: '전년 대비 변화', en: 'YoY CHANGES' }} sub={{ kr: 'Δ', en: 'Δ' }} flush>
      <div className="chgList">
        {ch.map((c) => {
          const has = c.v != null;
          const good = has && (c.invert ? c.v < 0 : c.v > 0);
          const w = has ? Math.min(50, Math.abs(c.v) / max * 50) : 0;
          return (
            <div key={c.en} className="chgRow">
              <span className="chgName">{txc(c, lang)}</span>
              <div className="chgBarWrap"><div className="chgBarMid"></div>{has && <div className={'chgBar ' + (c.v >= 0 ? 'pos' : 'neg')} style={{ width: w + '%', background: good ? 'var(--up)' : 'var(--dn)' }}></div>}</div>
              <span className={'chgVal ' + (has ? (good ? 'tUp' : 'tDn') : 'tNeu')}>{has ? sign(c.v, 1) + c.unit : '—'}</span>
            </div>
          );
        })}
      </div>
      <div className="finNote">ecosystem · {co.eco.deltaYear ? co.eco.deltaYear + ' vs prior' : '직전 사업연도'}</div>
    </Panel>
  );
}

function Peers({ co, lang, onPick }) {
  const peers = co.peers || [];
  const max = Math.max(...peers.map((p) => p.revenue || 0), 1);
  return (
    <Panel lang={lang} className="eIndustry" prov="live" title={{ kr: '동종업종', en: 'INDUSTRY PEERS' }} sub={{ kr: 'industry:peers', en: 'peers' }} flush>
      <div className="peerList">
        {peers.map((p) => (
          <div key={p.code} className={'peerRow' + (p.self ? ' self' : '')} onClick={() => onPick && onPick(p.code)}>
            <span className="peerName"><b>{p.name}</b><span className="pc">{p.code}</span></span>
            <span className="peerBar"><span className="peerBarTrack"><span className="peerBarFill" style={{ width: ((p.revenue || 0) / max * 100) + '%' }}></span></span><span className="peerRev">{p.revenue != null ? (p.revenue / 10000).toFixed(1) + '조' : '—'}</span></span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Governance({ co, lang }) {
  const e = co.eco;
  const cells = [
    { l: lang === 'en' ? 'GOV GRADE' : '거버넌스', v: e.govGrade || '—', t: DL.gradeTone('gov', e.govGrade) },
    { l: lang === 'en' ? 'STABILITY' : '경영안정', v: e.stability || '—', t: DL.gradeTone('stab', e.stability) },
    { l: lang === 'en' ? 'OWNER %' : '대주주지분', v: e.holderPct != null ? e.holderPct.toFixed(1) + '%' : '—', t: 'neutral' },
    { l: lang === 'en' ? 'OWNER Δ' : '지분변화', v: e.holderChange != null ? sign(e.holderChange, 1) + '%p' : '—', t: 'neutral' },
    { l: lang === 'en' ? 'AUDIT' : '감사위험', v: e.auditRisk || (lang === 'en' ? 'n/a' : '해당없음'), t: DL.gradeTone('audit', e.auditRisk) },
    { l: lang === 'en' ? 'QUALITY' : '이익질', v: e.qualGrade || '—', t: DL.gradeTone('qual', e.qualGrade) },
  ];
  return (
    <Panel lang={lang} className="eIndustry" prov="live" title={{ kr: '거버넌스 · 현금흐름', en: 'GOVERNANCE' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }} flush>
      {e.cfPattern && <div className="patBig"><div className="pv">{e.cfPattern}</div><div className="ps">{lang === 'en' ? 'cash-flow pattern' : '현금흐름 패턴'}{e.empCount != null ? ' · ' + e.empCount.toLocaleString() + (lang === 'en' ? ' emp' : '명') : ''}</div></div>}
      <div className="govGrid">{cells.map((c) => (<div key={c.l} className="govCell"><span>{c.l}</span><b className={tcls(c.t)}>{c.v}</b></div>))}</div>
    </Panel>
  );
}

function Story({ co, lang }) {
  const s = co.story; const dart = 'https://dart.fss.or.kr/dsab007/main.do';
  return (
    <Panel lang={lang} className="eCredit" prov="live" title={{ kr: 'DART · 스토리', en: 'DART · STORY' }} sub={{ kr: 'story · 공시', en: 'filings' }} flush>
      {s ? (<div className="storyCard"><span className="storyTag">DARTLAB STORY</span><div className="storyTitle">{s.title}</div><div className="storyMeta">{s.date} · {s.readTime} · <a className="storyLink" href={'https://eddmpython.github.io/dartlab/blog/' + s.slug} target="_blank" rel="noopener">read ↗</a></div></div>)
        : (<div className="storyEmpty">{lang === 'en' ? 'No published dartlab story yet.' : '발간된 dartlab 스토리는 아직 없습니다.'}</div>)}
      <div className="storyCard" style={{ borderTop: '1px solid var(--bd)' }}><div className="storyMeta">{lang === 'en' ? 'Primary filings — DART viewer:' : '원문 공시 — DART 뷰어:'}</div><a className="storyLink" href={dart} target="_blank" rel="noopener" style={{ fontFamily: 'var(--mono)', fontSize: '10px' }}>dart.fss.or.kr · {co.name.kr} ↗</a></div>
    </Panel>
  );
}

function AIAssistant({ co, lang }) {
  const a = co.ai;
  return (
    <Panel lang={lang} className="eAnalysis" prov="wire" title={{ kr: 'AI 어시스턴트', en: 'AI ASSISTANT' }} sub={{ kr: 'dartlab.ask', en: 'dartlab.ask' }} right={<span className="conf">CONF <b className={a.confidence === 'HIGH' ? 'tUp' : 'tWarn'}>{a.confidence}</b></span>} flush>
      <div className="aiQ">▸ {tx(a.question, lang)}</div>
      <div className="aiSteps">{a.steps.map((s, i) => (<div key={i} className="aiStep"><span className="aiTool">{s.tool}</span><span className="aiCall mono">{s.call}</span><span className="aiRef">{s.ref}</span></div>))}</div>
      <div className="aiAnswer">{tx(a.answer, lang)}</div>
    </Panel>
  );
}

function Percentile({ co, lang }) {
  const pc = co.percentile;
  if (!pc || !pc.metrics.length) return (<Panel lang={lang} className="eQuant" prov="live" title={{ kr: '업종 내 백분위', en: 'PERCENTILE' }} flush><div className="storyEmpty">{lang === 'en' ? 'No peer data.' : '비교 데이터 없음.'}</div></Panel>);
  const col = (p) => (p >= 80 ? 'var(--up)' : p >= 55 ? 'var(--good)' : p >= 35 ? 'var(--warn)' : 'var(--dn)');
  const fmtV = (m) => m.unit === 'rev' ? (m.v != null ? (m.v / 1e12).toFixed(1) + '조' : '—') : (m.v != null ? m.v.toFixed(1) + (m.unit === '%' ? '%' : '') : '—');
  return (
    <Panel lang={lang} className="eQuant" prov="live" title={{ kr: '업종 내 백분위', en: 'INDUSTRY PERCENTILE' }} sub={{ kr: pc.industry + ' ' + pc.n + '사', en: pc.industry + ' n=' + pc.n }} flush>
      <div className="pctList">
        {pc.metrics.map((m) => (
          <div key={m.en} className="pctRow">
            <span className="pctName">{txc(m, lang)}</span>
            <div className="pctTrack"><div className="pctFill" style={{ width: m.p + '%', background: col(m.p) }}></div><div className="pctMark" style={{ left: '50%' }}></div></div>
            <span className="pctVal"><b style={{ color: col(m.p) }}>{lang === 'en' ? 'top ' + (100 - m.p + 1) + '%' : '상위 ' + (100 - m.p + 1) + '%'}</b> <span className="dim">{fmtV(m)}</span></span>
          </div>
        ))}
      </div>
      <div className="pctNote">{lang === 'en' ? 'percentile across industry peers · ecosystem' : '동종업종 전 종목 대비 위치 · ecosystem'}</div>
    </Panel>
  );
}

function RiskFlags({ co, lang }) {
  const risks = co.risks || [];
  return (
    <Panel lang={lang} className="eCredit" prov="live" title={{ kr: '리스크 경고등', en: 'RISK FLAGS' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }}
      right={<span><b className="tDn">{risks.filter((r) => r.lv === 'red').length}</b> <b className="tWarn">{risks.filter((r) => r.lv === 'yellow').length}</b></span>} flush>
      <div className="riskWrap">
        {risks.map((r, i) => (
          <div key={i} className={'riskRow ' + r.lv}>
            <span className={'riskDot ' + r.lv}></span>
            <span className="riskName">{lang === 'en' ? r.en : r.kr}</span>
            {r.d && <span className="riskDetail">{r.d}</span>}
          </div>
        ))}
      </div>
    </Panel>
  );
}

window.RightPanels = { Financials, Credit, Changes, Peers, Governance, Story, AIAssistant, Percentile, RiskFlags };
})();
