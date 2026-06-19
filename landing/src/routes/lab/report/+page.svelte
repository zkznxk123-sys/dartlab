<script lang="ts">
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const report = $derived(data.report);
  const manifest = $derived(data.manifest);

  // 화이트/다크 토글 — A4 용지 위 두 모드. 기본 = 화이트(진짜 보고서)
  let theme = $state<'light' | 'dark'>('light');
  function toggleTheme() {
    theme = theme === 'light' ? 'dark' : 'light';
  }

  // 관점 탭 — manifest.reportTypes (thesis 제외 = 정적 투영 불가)
  const perspectives = $derived<any[]>(
    manifest?.reportTypes
      ? (Object.values(manifest.reportTypes) as any[]).filter((rt: any) => rt.key !== 'thesis')
      : []
  );
  let activeType = $state<string>('full');
  $effect(() => {
    if (data.reportType && manifest?.reportTypes?.[data.reportType]) activeType = data.reportType;
  });
  const activeRt = $derived(manifest?.reportTypes?.[activeType] ?? null);

  type Sec = any;
  const sectionsByKey = $derived(new Map<string, Sec>((report?.sections ?? []).map((s: Sec) => [s.key, s])));
  const view = $derived.by(() => {
    if (!report || !activeRt) return { sections: [] as Sec[], focusQuestions: [] as string[], missing: [] as string[] };
    const order: string[] = activeRt.sectionOrder ?? [];
    const emphasize = new Set<string>(activeRt.emphasize ?? []);
    const present: Sec[] = [];
    const missing: string[] = [];
    for (const key of order) {
      const s = sectionsByKey.get(key);
      if (s && s.blocks?.length) present.push({ ...s, _emph: emphasize.has(key) });
      else missing.push(key);
    }
    const sections = present.length ? present : (report.sections ?? []);
    return { sections, focusQuestions: activeRt.focusQuestions ?? [], missing };
  });

  // 표지 인트로 — 실제 존재하는 섹션 제목으로 동적 구성(억지 단정 없음)
  const introLine = $derived.by(() => {
    const titles = view.sections.map((s: Sec) => s.title).filter(Boolean);
    const domains = titles.length ? titles.join(' · ') : '재무 분석';
    return `${domains}을(를) 종합한 dartlab 기업분석 리포트입니다. 모든 수치는 공시 확정 데이터 기준이며, 각 섹션에 계산 출처 엔진을 표기했습니다.`;
  });

  const engineLabel: Record<string, string> = {
    analysis: '재무분석', credit: '신용평가', quant: '시장·기술', industry: '산업비교', macro: '거시', story: '종합서사'
  };

  function presentCount(rt: any): number {
    if (!report) return 0;
    const order: string[] = rt.sectionOrder ?? [];
    if (!order.length) return report.sections?.length ?? 0;
    return order.filter((k: string) => sectionsByKey.get(k)?.blocks?.length).length;
  }

  // 셀 부호 판정 — 신호값만 색(음수 빨강 / 명시 양수+ 초록). 무지개 방지(일반 양수=중립).
  function cellTone(v: any): string {
    const s = String(v ?? '').trim();
    if (!s || s === '-') return '';
    const core = s.replace(/[%조억원pP ,]/g, '');
    if (/^[-−△▼(]/.test(s) || /^-/.test(core)) return 'neg';
    if (/^[+▲]/.test(s)) return 'pos';
    return '';
  }

  // 시계열 행 → 스파크라인 (시간순) + 추세색 + 0-baseline + 최신값 endpoint dot
  function spark(row: any, yearCols: string[]) {
    const nums: number[] = [];
    for (let i = yearCols.length - 1; i >= 0; i--) {
      const raw = String(row[yearCols[i]] ?? '').replace(/[^0-9.\-]/g, '');
      const n = parseFloat(raw);
      nums.push(Number.isFinite(n) ? n : NaN);
    }
    const valid = nums.filter((n) => Number.isFinite(n));
    if (valid.length < 3) return null;
    let min = Math.min(...valid);
    let max = Math.max(...valid);
    const hasNeg = min < 0;
    if (hasNeg) { min = Math.min(min, 0); max = Math.max(max, 0); } // 부호 의미 계열: 0 포함
    const range = max - min || 1;
    const w = 54, h = 15;
    const step = w / (nums.length - 1);
    const xy = nums.map((n, i) => (Number.isFinite(n) ? { x: i * step, y: h - ((n - min) / range) * h } : null));
    const points = xy.filter(Boolean).map((p: any) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const last: any = [...xy].reverse().find(Boolean);
    const zeroY = min < 0 && max > 0 ? (h - ((0 - min) / range) * h).toFixed(1) : null;
    const first = valid[0];
    const lastV = valid[valid.length - 1];
    const tone = lastV > first * 1.001 ? 'up' : lastV < first * 0.999 ? 'down' : 'flat';
    return { points, tone, zeroY, lastX: last.x.toFixed(1), lastY: last.y.toFixed(1) };
  }

  function isTimeSeries(cols: string[]): boolean {
    return cols.length >= 4 && /^\d{4}$/.test(cols[1] ?? '');
  }

  // 섹션 제목 = "{도메인} -- {질문}" → 도메인(큰 제목) + 질문(부제) 분리
  function splitTitle(t: string): { head: string; sub: string } {
    const s = String(t ?? '');
    const m = s.split(/\s*(?:--|—|·)\s*/);
    if (m.length >= 2) return { head: m[0].trim(), sub: m.slice(1).join(' · ').trim() };
    return { head: s.trim(), sub: '' };
  }

  function printReport() {
    if (typeof window !== 'undefined') window.print();
  }
  function scrollSec(key: string) {
    document.getElementById(`sec-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const samples = [
    { code: '005930', name: '삼성전자' },
    { code: '000660', name: 'SK하이닉스' },
    { code: '035420', name: 'NAVER' }
  ];
</script>

<svelte:head>
  <title>기업분석보고서 · {report?.corpName ?? data.sym} | dartlab (dev)</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<div class="rptRoot" class:dark={theme === 'dark'}>
  <nav class="toolbar">
    <span class="devtag">DEV /lab/report</span>
    {#each samples as s}
      <a class="devlink" class:on={data.sym === s.code} href={`/lab/report?sym=${s.code}&type=${activeType}`}>{s.name}</a>
    {/each}
    <span class="spacer"></span>
    <button class="themeBtn" onclick={toggleTheme} title="화이트/다크 전환">
      {theme === 'light' ? '🌙 다크' : '☀ 화이트'}
    </button>
    <button class="printBtn" onclick={printReport}>🖨 인쇄 / PDF</button>
  </nav>

  {#if !report}
    <article class="sheet skip">
      <h1>데이터 부족 — 보고서 미생성</h1>
      <p class="skipReason">종목 {data.sym}: {data.skipReason ?? '분석 페이로드가 굽지 않았습니다(reject-gate).'}</p>
      <p class="muted">약한 발행보다 정직한 스킵 — dartlab 은 데이터가 빈약한 회사의 보고서를 만들지 않습니다.</p>
    </article>
  {:else}
    <article class="sheet">
      <!-- ── 표지 / 제목 블록 ── -->
      <header class="cover">
        <div class="coverKicker">기업분석보고서 <span class="kSep">·</span> dartlab</div>
        <h1 class="coverTitle">{report.corpName}<span class="code">{report.stockCode}</span></h1>
        <div class="coverMeta">
          {#if report.template}<span>{report.template}</span><span class="dot">·</span>{/if}
          <span>기준 {report.bakedAt}</span>
          <span class="dot">·</span><span>작성 dartlab 분석엔진</span>
          {#if report.meta?.qualityLabel === 'conditional'}<span class="dot">·</span><span class="condBadge">조건부</span>{/if}
        </div>
        <p class="coverIntro">{introLine}</p>
      </header>

      <!-- ── 관점 (화면 전용) ── -->
      <div class="tabs">
        <span class="tabsLabel">관점</span>
        {#each perspectives as rt}
          <button class="tab" class:on={rt.key === activeType} class:thin={presentCount(rt) < 3}
            onclick={() => (activeType = rt.key)}
            title={presentCount(rt) < 3 ? `${rt.description} — 데이터 제한(${presentCount(rt)}섹션)` : rt.description}>
            {rt.label}{#if presentCount(rt) < 3}<span class="thinMark">·제한</span>{/if}
          </button>
        {/each}
      </div>
      <div class="printPerspective">관점: {activeRt?.label ?? '전체'}</div>

      {#if view.focusQuestions.length}
        <div class="focusRow">{#each view.focusQuestions as q}<span class="chip focus">{q}</span>{/each}</div>
      {/if}

      <!-- ── 핵심 요약 ── -->
      <section class="block summary">
        <h2 class="blockTitle">핵심 요약</h2>
        <div class="conclusion">{report.summaryCard?.conclusion}</div>
        {#if report.headlineKpis?.length}
          <div class="kpiBand">
            {#each report.headlineKpis as k}<div class="kpi"><span class="kLabel">{k.label}</span><span class="kVal {cellTone(k.value)}">{k.value}</span></div>{/each}
          </div>
        {/if}
        {#if report.narrativeOverview}<p class="overview">{report.narrativeOverview}</p>{/if}
        <div class="gradeChips">
          {#each Object.entries(report.summaryCard?.grades ?? {}) as [area, grade]}
            <span class="chip grade g{grade}">{area} <b>{grade}</b></span>
          {/each}
          {#if report.summaryCard?.gradesNote}<span class="note">{report.summaryCard.gradesNote}</span>{/if}
        </div>
        {#if report.summaryCard?.strengths?.length}<ul class="sw strengths">{#each report.summaryCard.strengths as x}<li>{x}</li>{/each}</ul>{/if}
        {#if report.summaryCard?.warnings?.length}<ul class="sw warnings">{#each report.summaryCard.warnings as x}<li>{x}</li>{/each}</ul>{/if}
      </section>

      {#if report.keyFindings?.length}
        <section class="block keyFindings">
          <h2 class="blockTitle">핵심 발견 <span class="subNote">엔진 측정값 자동 추출</span></h2>
          {#each report.keyFindings as kf}
            <div class="kfRow"><span class="chip kfTag">{kf.key}</span><span class="kfText">{kf.finding}</span><span class="kfSrc">{engineLabel[kf.sourceEngine] ?? kf.sourceEngine}</span></div>
          {/each}
        </section>
      {/if}

      <!-- ── 목차 (섹션 제목 기반) ── -->
      {#if view.sections.length > 1}
        <nav class="toc">
          <span class="tocLabel">목차</span>
          {#each view.sections as sec, i (sec.key)}
            <button class="tocItem" onclick={() => scrollSec(sec.key)}>
              <span class="tocNo">{String(i + 1).padStart(2, '0')}</span>{splitTitle(sec.title).head}
            </button>
          {/each}
        </nav>
      {/if}

      {#if view.missing.length && activeType !== 'full'}
        <div class="missingNote">이 관점({activeRt?.label})의 섹션 중 <b>{view.missing.length}개</b>는 이 회사 데이터에서 미산출 — {view.missing.join(', ')} (정직 스킵, 억지 채움 없음)</div>
      {/if}

      <!-- ── 본문 섹션 (제목별, 순차) ── -->
      <div class="sections">
        {#each view.sections as sec, i (sec.key)}
          {@const t = splitTitle(sec.title)}
          <section class="rptSection src-{sec.sourceEngine}" class:emph={sec._emph} id={`sec-${sec.key}`}>
            <div class="secHead">
              <span class="secNo">{String(i + 1).padStart(2, '0')}</span>
              <div class="secTitleWrap">
                <h2 class="secTitle">{t.head}</h2>
                {#if t.sub}<div class="secSub">{t.sub}</div>{/if}
              </div>
              <span class="chip srcBadge src-{sec.sourceEngine}">{engineLabel[sec.sourceEngine] ?? sec.sourceEngine}</span>
            </div>
            {#each sec.blocks as b}
              {#if b.type === 'heading'}
                <h3 class="bHeading">{b.title}</h3>
              {:else if b.type === 'text'}
                <p class="bText">{b.text}</p>
              {:else if b.type === 'metrics'}
                <div class="bMetrics">{#each b.metrics as m}<div class="metric"><span class="mLabel">{m.label}</span><span class="mValue {cellTone(m.value)}">{m.value}</span></div>{/each}</div>
              {:else if b.type === 'table' && b.data?.length}
                {@const cols = Object.keys(b.data[0])}
                {@const ts = isTimeSeries(cols)}
                <div class="bTableWrap">
                  {#if b.label}<div class="tCap">{b.label}</div>{/if}
                  <table class="bTable">
                    <thead><tr>{#each cols as c, ci}<th class={ci === 0 ? 'lbl' : 'num'}>{c}</th>{/each}{#if ts}<th class="sparkCol">추이</th>{/if}</tr></thead>
                    <tbody>
                      {#each b.data as row}
                        <tr>
                          {#each cols as c, ci}<td class={ci === 0 ? 'lbl' : 'num ' + cellTone(row[c])}>{row[c]}</td>{/each}
                          {#if ts}{@const sp = spark(row, cols.slice(1))}<td class="sparkCol">{#if sp}<svg class="spark {sp.tone}" width="54" height="15" viewBox="0 0 54 15">{#if sp.zeroY}<line x1="0" y1={sp.zeroY} x2="54" y2={sp.zeroY} stroke="var(--dim)" stroke-width="0.5" stroke-dasharray="2 2" opacity="0.55" />{/if}<polyline points={sp.points} fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round" /><circle cx={sp.lastX} cy={sp.lastY} r="1.5" fill="currentColor" /></svg>{/if}</td>{/if}
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {:else if b.type === 'flags'}
                <ul class="bFlags {b.kind}">{#each b.flags as f}<li>{f}</li>{/each}</ul>
              {/if}
            {/each}
          </section>
        {/each}
      </div>

      <!-- ── 근거·출처 ── -->
      <section class="block evidenceStrip">
        <h2 class="blockTitle">근거·출처 <span class="subNote">이 보고서를 계산한 dartlab 엔진</span></h2>
        <div class="evEngines">
          {#each Object.entries(report.provenanceFrame?.engines ?? {}) as [eng, info]}
            <div class="evEngine"><span class="evDot"></span><span class="evLabel">{(info as any).label ?? engineLabel[eng] ?? eng}</span><span class="evMeta">{(info as any).sections}섹션 · {(info as any).blocks}블록</span></div>
          {/each}
          {#each Object.entries(report.evidenceFrame?.axes ?? {}) as [axis, ax]}
            <div class="evEngine"><span class="evDot"></span><span class="evLabel">{axis}</span><span class="evMeta">{((ax as any).evidenceIds ?? []).join(' · ')}</span></div>
          {/each}
        </div>
        <div class="evNote">{report.provenanceFrame?.note}</div>
      </section>

      <!-- ── 푸터 / 서명 ── -->
      <footer class="rptFooter">
        {#if report.assumptionsNote}<div class="assump">가정·한계 — {report.assumptionsNote}</div>{/if}
        <div class="footSign">
          <span class="signMain">{report.corpName} 기업분석보고서</span>
          <span class="dot">·</span><span>기준 {report.bakedAt}</span>
          <span class="dot">·</span><span>작성 dartlab 분석엔진</span>
        </div>
        <div class="footLine">
          모든 수치 = dartlab 엔진({Object.keys(report.provenanceFrame?.engines ?? {}).map((e) => engineLabel[e] ?? e).join('·')}) 산출
          <span class="dot">·</span> sourceEngine = 계산 엔진(원천 DART 공시 줄 아님)
          <span class="dot">·</span> 본 보고서는 투자 권유가 아니며, 투자 판단의 책임은 이용자에게 있습니다.
        </div>
      </footer>
    </article>
  {/if}
</div>

<style>
  /* ── 기본 = 화이트(용지) 테마 ── */
  .rptRoot {
    --backdrop: #e8eaed; --sheet: #ffffff; --ink: #1b1e23; --dim: #6b7178;
    --bd: #e6e9ed; --bd2: #d6dbe1; --soft: #f6f7f9;
    --accent: #0b63d6; --up: #1a7f37; --down: #c0392b; --warn: #9a6700; --emph: #0b63d6;
    --e-analysis: #0b63d6; --e-credit: #c0392b; --e-quant: #0a7d86; --e-industry: #1a7f37; --e-macro: #9a6700; --e-story: #6f42c1;
    --mono: ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;
    --sans: 'Pretendard', -apple-system, system-ui, sans-serif;
    background: var(--backdrop); color: var(--ink); min-height: 100vh; font-family: var(--sans); font-size: 13px; line-height: 1.6;
  }

  /* ── 다크 용지 테마 (참조 보고서 색조: 청 #5C97FF · 녹 #2BC583 · 자 #9385FF) ── */
  .rptRoot.dark {
    --backdrop: #0a0c10; --sheet: #14181f; --ink: #e8eef5; --dim: #8b949e;
    --bd: rgba(255, 255, 255, 0.09); --bd2: rgba(255, 255, 255, 0.16); --soft: #1b212b;
    --accent: #5c97ff; --up: #2bc583; --down: #f85149; --warn: #d29922; --emph: #5c97ff;
    --e-analysis: #5c97ff; --e-credit: #f85149; --e-quant: #56d4dd; --e-industry: #2bc583; --e-macro: #d29922; --e-story: #9385ff;
  }

  /* ── 툴바 ── */
  .toolbar { display: flex; align-items: center; gap: 10px; padding: 8px 16px; background: color-mix(in srgb, var(--backdrop) 80%, #000 8%); border-bottom: 1px solid var(--bd2); position: sticky; top: 0; z-index: 20; }
  .devtag { font-family: var(--mono); font-size: 11px; color: var(--warn); letter-spacing: 0.04em; }
  .devlink { color: var(--dim); text-decoration: none; font-size: 12px; padding: 3px 9px; border-radius: 6px; border: 1px solid transparent; }
  .devlink.on { color: var(--ink); border-color: var(--bd2); background: var(--sheet); }
  .devlink:hover { color: var(--ink); }
  .spacer { flex: 1; }
  .themeBtn { background: var(--sheet); color: var(--ink); border: 1px solid var(--bd2); padding: 6px 12px; border-radius: 7px; cursor: pointer; font-size: 12px; }
  .themeBtn:hover { border-color: var(--accent); }
  .printBtn { background: var(--accent); color: #fff; border: 0; padding: 6px 14px; border-radius: 7px; font-weight: 700; cursor: pointer; font-size: 12px; }
  .printBtn:hover { filter: brightness(1.08); }

  /* ── A4 용지 ── */
  .sheet {
    width: 820px; max-width: calc(100vw - 32px); margin: 28px auto 60px; padding: 52px 56px 44px;
    background: var(--sheet); border: 1px solid var(--bd); border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 12px 40px rgba(0, 0, 0, 0.10);
  }
  .skip { text-align: center; padding-top: 70px; padding-bottom: 70px; }
  .skip h1 { font-size: 22px; } .skipReason { font-family: var(--mono); color: var(--warn); }

  /* ── 표지 ── */
  .cover { border-bottom: 2px solid var(--ink); padding-bottom: 20px; margin-bottom: 24px; }
  .coverKicker { font-size: 12px; font-weight: 700; color: var(--accent); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 10px; }
  .coverKicker .kSep { opacity: 0.4; margin: 0 4px; }
  .coverTitle { font-size: 34px; font-weight: 800; letter-spacing: -0.025em; margin: 0 0 10px; line-height: 1.12; }
  .coverTitle .code { font-family: var(--mono); font-size: 16px; color: var(--dim); font-weight: 500; margin-left: 11px; letter-spacing: 0; }
  .coverMeta { font-size: 12.5px; color: var(--dim); display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
  .coverMeta .dot { opacity: 0.4; }
  .condBadge { color: var(--warn); border: 1px solid var(--warn); border-radius: 4px; padding: 0 6px; font-size: 11px; }
  .coverIntro { font-size: 13px; line-height: 1.75; color: var(--dim); margin: 14px 0 0; max-width: 64ch; }

  /* ── 칩 프리미티브 ── */
  .chip { font-size: 11.5px; border-radius: 6px; padding: 3px 9px; border: 1px solid var(--bd2); color: var(--ink); white-space: nowrap; }
  .chip.focus { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 34%, transparent); background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 13px; }
  .chip.grade b { font-family: var(--mono); margin-left: 3px; }
  .chip.grade.gA { border-color: var(--up); color: var(--up); }
  .chip.grade.gB { border-color: var(--accent); color: var(--accent); }
  .chip.grade.gC { border-color: var(--warn); color: var(--warn); }
  .chip.grade.gD, .chip.grade.gF { border-color: var(--down); color: var(--down); }
  .note { font-size: 10.5px; color: var(--dim); align-self: center; font-style: italic; }

  /* ── 관점 탭 ── */
  .tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; align-items: center; }
  .tabsLabel { font-size: 11px; color: var(--dim); font-weight: 700; margin-right: 4px; letter-spacing: 0.04em; }
  .tab { background: var(--soft); color: var(--dim); border: 1px solid var(--bd2); border-radius: 7px; padding: 5px 12px; font-size: 12.5px; cursor: pointer; transition: all 0.12s; }
  .tab.on { color: #fff; background: var(--emph); border-color: var(--emph); font-weight: 700; }
  .tab:hover:not(.on) { color: var(--ink); border-color: var(--accent); }
  .tab.thin { opacity: 0.5; } .tab.thin.on { opacity: 1; }
  .thinMark { font-size: 9.5px; color: var(--warn); margin-left: 3px; }
  .printPerspective { display: none; }

  .focusRow { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 18px; }

  /* ── 공통 블록 ── */
  .block { margin-bottom: 26px; }
  .blockTitle { font-size: 13px; font-weight: 800; letter-spacing: 0.02em; margin: 0 0 12px; padding-bottom: 7px; border-bottom: 1px solid var(--bd2); display: flex; align-items: baseline; gap: 8px; }
  .blockTitle .subNote { font-size: 10.5px; font-weight: 400; color: var(--dim); }

  /* ── 핵심 요약 ── */
  .conclusion { font-size: 19px; font-weight: 700; margin-bottom: 14px; letter-spacing: -0.01em; line-height: 1.45; }
  .kpiBand { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 9px; margin: 4px 0 16px; }
  .kpi { background: var(--soft); border: 1px solid var(--bd); border-radius: 8px; padding: 10px 13px; display: flex; flex-direction: column; gap: 4px; }
  .kLabel { font-size: 10.5px; color: var(--dim); }
  .kVal { font-size: 18px; font-weight: 800; font-family: var(--mono); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
  .kVal.neg { color: var(--down); } .kVal.pos { color: var(--up); }
  .overview { font-size: 13.5px; line-height: 1.78; margin: 0 0 14px; }
  .gradeChips { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
  .sw { margin: 13px 0 0; padding-left: 18px; font-size: 12.5px; line-height: 1.7; }
  .sw.strengths li { color: var(--up); } .sw.warnings li { color: var(--warn); }

  /* ── 핵심 발견 ── */
  .kfRow { display: grid; grid-template-columns: 92px 1fr auto; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--bd); align-items: baseline; }
  .chip.kfTag { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 28%, transparent); font-weight: 600; padding: 1px 8px; font-size: 11px; justify-self: start; }
  .kfText { font-size: 12.5px; line-height: 1.55; }
  .kfSrc { font-size: 10.5px; color: var(--dim); }

  /* ── 목차 ── */
  .toc { display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; margin: 0 0 30px; padding: 14px 16px; background: var(--soft); border: 1px solid var(--bd); border-radius: 10px; }
  .tocLabel { font-size: 11px; color: var(--dim); font-weight: 800; margin-right: 6px; letter-spacing: 0.06em; }
  .tocItem { background: transparent; border: 0; color: var(--ink); font-size: 12.5px; cursor: pointer; padding: 3px 9px; border-radius: 6px; display: inline-flex; align-items: baseline; gap: 6px; font-family: var(--sans); }
  .tocItem:hover { color: var(--accent); background: color-mix(in srgb, var(--accent) 9%, transparent); }
  .tocNo { font-family: var(--mono); font-size: 10.5px; color: var(--accent); font-weight: 700; }

  .missingNote { font-size: 12px; color: var(--warn); background: color-mix(in srgb, var(--warn) 8%, transparent); border: 1px solid color-mix(in srgb, var(--warn) 24%, transparent); border-radius: 8px; padding: 9px 13px; margin-bottom: 20px; }

  /* ── 본문 섹션 ── */
  .sections { counter-reset: sec; }
  .rptSection { margin-bottom: 30px; padding: 0; scroll-margin-top: 56px; }
  .secHead { display: flex; align-items: baseline; gap: 12px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 2px solid var(--ink); }
  .secNo { font-family: var(--mono); font-size: 15px; font-weight: 800; color: var(--accent); letter-spacing: -0.02em; }
  .rptSection.src-credit .secNo { color: var(--e-credit); }
  .rptSection.src-quant .secNo { color: var(--e-quant); }
  .rptSection.src-industry .secNo { color: var(--e-industry); }
  .rptSection.src-macro .secNo { color: var(--e-macro); }
  .rptSection.src-story .secNo { color: var(--e-story); }
  .secTitleWrap { flex: 1; }
  .secTitle { font-size: 19px; font-weight: 800; margin: 0; letter-spacing: -0.015em; }
  .secSub { font-size: 12px; color: var(--dim); margin-top: 3px; font-weight: 500; }
  .chip.srcBadge { font-size: 10.5px; padding: 2px 8px; color: var(--dim); align-self: center; }
  .chip.srcBadge.src-analysis { color: var(--e-analysis); border-color: color-mix(in srgb, var(--e-analysis) 30%, transparent); }
  .chip.srcBadge.src-credit { color: var(--e-credit); border-color: color-mix(in srgb, var(--e-credit) 30%, transparent); }
  .chip.srcBadge.src-quant { color: var(--e-quant); border-color: color-mix(in srgb, var(--e-quant) 30%, transparent); }
  .chip.srcBadge.src-industry { color: var(--e-industry); border-color: color-mix(in srgb, var(--e-industry) 30%, transparent); }
  .chip.srcBadge.src-macro { color: var(--e-macro); border-color: color-mix(in srgb, var(--e-macro) 30%, transparent); }
  .rptSection.emph .secTitle::after { content: '핵심'; font-size: 10px; font-weight: 700; color: var(--emph); border: 1px solid var(--emph); border-radius: 4px; padding: 1px 5px; margin-left: 9px; vertical-align: middle; }

  .bHeading { font-size: 13px; font-weight: 700; margin: 16px 0 7px; color: var(--ink); }
  .bText { font-size: 12.5px; line-height: 1.78; margin: 7px 0; }

  .bMetrics { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; margin: 10px 0; }
  .metric { background: var(--soft); border: 1px solid var(--bd); border-radius: 7px; padding: 8px 12px; display: flex; flex-direction: column; gap: 3px; }
  .mLabel { font-size: 10.5px; color: var(--dim); }
  .mValue { font-size: 15px; font-weight: 700; font-family: var(--mono); font-variant-numeric: tabular-nums; }
  .mValue.neg { color: var(--down); } .mValue.pos { color: var(--up); }

  .bTableWrap { margin: 12px 0; overflow-x: auto; }
  .tCap { font-size: 11.5px; color: var(--dim); margin-bottom: 6px; font-weight: 600; }
  .bTable { border-collapse: collapse; font-size: 12px; width: 100%; }
  .bTable th { padding: 7px 10px; border-bottom: 2px solid var(--bd2); color: var(--dim); font-weight: 700; font-family: var(--mono); }
  .bTable th.lbl { text-align: left; font-family: var(--sans); }
  .bTable th.num, .bTable th.sparkCol { text-align: right; }
  .bTable td { padding: 6px 10px; border-bottom: 1px solid var(--bd); }
  .bTable td.lbl { text-align: left; font-weight: 600; white-space: nowrap; }
  .bTable td.num { text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; }
  .bTable td.num.neg { color: var(--down); } .bTable td.num.pos { color: var(--up); }
  .bTable tbody tr:nth-child(even) { background: var(--soft); }
  .bTable td.sparkCol { text-align: right; padding-right: 4px; width: 58px; }
  .spark { vertical-align: middle; color: var(--dim); }
  .spark.up { color: var(--up); } .spark.down { color: var(--down); } .spark.flat { color: var(--dim); }

  .bFlags { padding-left: 18px; margin: 9px 0; font-size: 12.5px; line-height: 1.7; }
  .bFlags.warning li { color: var(--warn); } .bFlags.opportunity li { color: var(--up); }

  /* ── 근거·출처 ── */
  .evEngines { display: flex; flex-wrap: wrap; gap: 16px; }
  .evEngine { display: flex; align-items: center; gap: 7px; }
  .evDot { width: 8px; height: 8px; border-radius: 50%; background: var(--up); }
  .evLabel { font-size: 12.5px; font-weight: 600; }
  .evMeta { font-size: 11px; color: var(--dim); font-family: var(--mono); }
  .evNote { font-size: 10.5px; color: var(--dim); margin-top: 10px; font-style: italic; }

  /* ── 푸터 ── */
  .rptFooter { margin-top: 36px; padding-top: 16px; border-top: 2px solid var(--ink); font-size: 11px; color: var(--dim); }
  .assump { margin-bottom: 10px; color: var(--warn); }
  .footSign { font-size: 12px; color: var(--ink); display: flex; flex-wrap: wrap; gap: 7px; align-items: center; margin-bottom: 8px; }
  .footSign .signMain { font-weight: 700; }
  .footSign .dot, .footLine .dot { opacity: 0.4; }
  .footLine { line-height: 1.7; }
  .muted { color: var(--dim); }

  /* ── 인쇄 — A4, 화이트 강제 ── */
  @media print {
    .rptRoot, .rptRoot.dark {
      --backdrop: #fff; --sheet: #fff; --soft: #f5f7f9; --ink: #161616; --dim: #555a60;
      --bd: #e2e6ea; --bd2: #c3cad1;
      --accent: #0550ae; --up: #1a7f37; --down: #b02a1a; --warn: #8a6100; --emph: #0550ae;
      --e-analysis: #0550ae; --e-credit: #b02a1a; --e-quant: #0a7d86; --e-industry: #1a7f37; --e-macro: #8a6100; --e-story: #6f42c1;
      background: #fff; font-size: 10.2pt;
    }
    .toolbar, .tabs, .toc { display: none !important; }
    .printPerspective { display: block; font-size: 11px; color: #555; margin-bottom: 12px; font-weight: 600; }
    .sheet { width: 100%; max-width: 100%; margin: 0; padding: 0; border: 0; box-shadow: none; border-radius: 0; }
    .rptSection, .summary, .keyFindings, .evidenceStrip { break-inside: avoid; }
    .secHead { break-after: avoid; }
    .bTable tbody tr:nth-child(even) { background: #f4f6f8 !important; }
    .spark polyline { stroke-width: 1.7px; }
    .spark.flat { color: #6b7280; }
    .chip.focus { background: none; }
    @page { size: A4; margin: 14mm 13mm; }
  }
</style>
