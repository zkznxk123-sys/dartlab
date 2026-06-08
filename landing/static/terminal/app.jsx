/* =========================================================================
   DartLab Terminal — APP SHELL (KR-only · async boot · REAL data via window.DL)
   EDGAR-ready: market/provider are data-driven (eco.market, co.provider);
   when EDGAR companies land in the same dataset they resolve unchanged.
   ========================================================================= */
(function () {
const { useState, useEffect } = React;
const { MacroQuadrant, Screener, SectorMap, Movers } = window.LeftPanels;
const { SymbolHeader, GradeStrip, PriceAction, RadarPanel, ReturnsRisk, Fundamentals, Analysis, Verdict, Valuation } = window.CenterPanels;
const { Financials, Credit, Changes, Peers, Governance, Story, AIAssistant, Percentile, RiskFlags } = window.RightPanels;
const { fmtNum } = window.ChartKit;

function Clock() {
  const [t, setT] = useState(new Date());
  useEffect(() => { const id = setInterval(() => setT(new Date()), 1000); return () => clearInterval(id); }, []);
  const p = (n) => String(n).padStart(2, '0');
  return <span className="clock mono">{p(t.getHours())}:{p(t.getMinutes())}:{p(t.getSeconds())} KST</span>;
}

function TickerStrip({ onPick }) {
  const codes = DL.featured(14); const items = codes.concat(codes);
  return (
    <div className="tickerStrip"><div className="tickerTrack">
      {items.map((c, i) => {
        const p = DL.DB.prices[c]; const idx = DL.DB.byCode[c]; if (!p) return null;
        const chg = p.return1m;
        return (<span key={i} className="tickerItem" onClick={() => onPick(c)}><b>{idx ? idx.corpName : c}</b><span className="mono">{fmtNum(p.currentPrice)}</span><span className={'mono ' + (chg >= 0 ? 'tUp' : 'tDn')}>{(chg >= 0 ? '+' : '') + (chg == null ? 0 : chg).toFixed(1)}%</span></span>);
      })}
    </div></div>
  );
}

function Boot({ msg }) {
  return (
    <div className="bootScreen">
      <img className="bootLogo" src="assets/dartlab-logo.png" alt="DartLab" width="64" height="64" style={{ borderRadius: '16px' }} />
      <div className="bootMark">DART<span>LAB</span> TERMINAL</div>
      <div className="bootBar"><div className="bootFill"></div></div>
      <div className="bootMsg">{msg}</div>
    </div>
  );
}

function App() {
  const [ready, setReady] = useState(false);
  const [msg, setMsg] = useState('HuggingFace · dartlab-data 연결 중 …');
  const [sym, setSym] = useState('005930');
  const [co, setCo] = useState(null);
  const [lang, setLang] = useState('kr');
  const [period, setPeriod] = useState('1Y');
  const [indicator, setIndicator] = useState('RSI');
  const [stmt, setStmt] = useState('SUM');
  const [acct, setAcct] = useState('kr');
  const [cmd, setCmd] = useState('');
  const [flash, setFlash] = useState(null);

  useEffect(() => {
    (async () => {
      await DL.boot();
      setMsg('회사 분석 뷰 생성 …');
      const first = DL.featured(1)[0] || '005930';
      setSym(first); setCo(DL.buildCompany(first));
      setReady(true);
    })();
  }, []);

  function pick(code) {
    const built = DL.buildCompany(code);
    if (!built) { setFlash('데이터 없음'); setTimeout(() => setFlash(null), 1400); return; }
    setSym(code); setCo(built); setFlash(code + ' · ' + built.name.kr); setTimeout(() => setFlash(null), 900);
  }
  function go(e) {
    e && e.preventDefault();
    const r = DL.search(cmd);
    if (r) { pick(r); setCmd(''); } else { setFlash('검색 결과 없음'); setTimeout(() => setFlash(null), 1300); }
  }

  if (!ready || !co) return <Boot msg={msg} />;

  const langTabs = [{ k: 'kr', l: '한국어' }, { k: 'en', l: 'EN' }, { k: 'dual', l: 'KR+EN' }];
  const src = DL.DB.source;

  return (
    <div className="terminal">
      <header className="topBar">
        <div className="brand"><img className="brandLogo" src="assets/dartlab-logo.png" alt="DartLab" /><span className="brandName">DARTLAB</span><span className="brandTag">KR TERMINAL</span></div>
        <form className="cmdBar" onSubmit={go}>
          <span className="cmdPrompt">‹GO›</span>
          <input className="cmdInput" value={cmd} onChange={(e) => setCmd(e.target.value)} placeholder={lang === 'en' ? 'Search code or name  (005930 · 삼성전자 · 기아)' : '종목코드/이름 검색  (005930 · 삼성전자 · SK하이닉스)'} spellCheck={false} />
          <button className="cmdGo" type="submit">GO</button>
          {flash && <span className="cmdFlash">{flash}</span>}
        </form>
        <div className="topRight">
          <div className="langSwitch">{langTabs.map((t) => <button key={t.k} className={'langBtn ' + (lang === t.k ? 'on' : '')} onClick={() => setLang(t.k)}>{t.l}</button>)}</div>
          <Clock />
          <span className="connDot"><span className="dot"></span>{src.indexOf('Hugging') >= 0 ? 'HuggingFace' : 'local'}</span>
        </div>
      </header>

      <TickerStrip onPick={pick} />

      <main className="board">
        <div className="col colL">
          <MacroQuadrant lang={lang} />
          <Screener lang={lang} onPick={pick} active={sym} />
          <SectorMap lang={lang} />
          <Movers lang={lang} onPick={pick} />
        </div>

        <div className="col colC">
          <SymbolHeader co={co} lang={lang} />
          <GradeStrip co={co} lang={lang} />
          <Verdict co={co} lang={lang} />
          <PriceAction co={co} lang={lang} period={period} setPeriod={setPeriod} indicator={indicator} setIndicator={setIndicator} />
          <div className="rowSplit">
            <RadarPanel co={co} lang={lang} />
            <ReturnsRisk co={co} lang={lang} />
          </div>
          <div className="rowSplit">
            <Valuation co={co} lang={lang} />
            <Fundamentals co={co} lang={lang} />
          </div>
          <Analysis co={co} lang={lang} />
        </div>

        <div className="col colR">
          <RiskFlags co={co} lang={lang} />
          <Percentile co={co} lang={lang} />
          <Financials co={co} lang={lang} stmt={stmt} setStmt={setStmt} acct={acct} setAcct={setAcct} />
          <div className="rowSplit">
            <Credit co={co} lang={lang} />
            <Changes co={co} lang={lang} />
          </div>
          <div className="rowSplit">
            <Peers co={co} lang={lang} onPick={pick} />
            <Governance co={co} lang={lang} />
          </div>
          <div className="rowSplit">
            <Story co={co} lang={lang} />
            <AIAssistant co={co} lang={lang} />
          </div>
        </div>
      </main>

      <footer className="statusBar">
        <span className="sbItem"><b className="tAmber">F1</b> SCREENER</span>
        <span className="sbItem"><b className="tAmber">F2</b> CHART</span>
        <span className="sbItem"><b className="tAmber">F3</b> GRADES</span>
        <span className="sbItem"><b className="tAmber">F5</b> SNAPSHOT</span>
        <span className="sbItem dim">DATA · {src}</span>
        <span className="sbItem" style={{ gap: '6px' }}><span className="provTag pLive">LIVE</span><span className="dim">{lang === 'en' ? 'real' : '실데이터'}</span><span className="provTag pDeriv">파생</span><span className="dim">{lang === 'en' ? 'computed' : '계산'}</span><span className="provTag pWire">배선필요</span><span className="dim">{lang === 'en' ? 'to wire' : '미연동'}</span></span>
        <span className="sbSpacer"></span>
        <span className="sbItem dim">finance v{(DL.DB.finance && DL.DB.finance.version) || '—'} · prices {co.price.asOf} · {DL.DB.index.length} 종목 · KR</span>
        <span className="sbItem"><b className="tUp">{co.code}</b> {co.name.kr} · {co.marketLabel}</span>
      </footer>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
})();
