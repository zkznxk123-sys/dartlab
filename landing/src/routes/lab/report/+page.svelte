<script lang="ts">
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const report = $derived(data.report);
  const manifest = $derived(data.manifest);

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

  // 6막 스파인 (현재 관점에 존재하는 act)
  const actSpine = $derived.by(() => {
    const seen = new Set<number>();
    const out: { act: number; header: string }[] = [];
    for (const s of view.sections) {
      if (s.act && !seen.has(s.act) && s.actHeader) {
        seen.add(s.act);
        out.push({ act: s.act, header: s.actHeader });
      }
    }
    return out;
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

  function printReport() {
    if (typeof window !== 'undefined') window.print();
  }
  function scrollAct(act: number) {
    document.getElementById(`act-${act}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

<div class="rptRoot">
  <nav class="devbar">
    <span class="devtag">DEV /lab/report</span>
    {#each samples as s}
      <a class="devlink" class:on={data.sym === s.code} href={`/lab/report?sym=${s.code}&type=${activeType}`}>{s.name}</a>
    {/each}
    <span class="spacer"></span>
    <button class="printBtn" onclick={printReport}>🖨 인쇄 / PDF</button>
  </nav>

  {#if !report}
    <div class="rptDoc skip">
      <h1>데이터 부족 — 보고서 미생성</h1>
      <p class="skipReason">종목 {data.sym}: {data.skipReason ?? '분석 페이로드가 굽지 않았습니다(reject-gate).'}</p>
      <p class="muted">약한 발행보다 정직한 스킵 — dartlab 은 데이터가 빈약한 회사의 보고서를 만들지 않습니다.</p>
    </div>
  {:else}
    <article class="rptDoc">
      <header class="metaRibbon">
        <h1>{report.corpName} <span class="code">{report.stockCode}</span></h1>
        <div class="metaSub">
          <span class="kicker">기업분석보고서</span>
          {#if report.template}<span class="dot">·</span><span>{report.template}</span>{/if}
          <span class="dot">·</span><span>as-of {report.bakedAt}</span>
          <span class="dot">·</span><span class="muted">dartlab 엔진 자동생성</span>
          {#if report.meta?.qualityLabel === 'conditional'}<span class="dot">·</span><span class="condBadge">조건부</span>{/if}
        </div>
      </header>

      <div class="tabs">
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

      <section class="summaryCard">
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
        {#if report.summaryCard?.strengths?.length}<ul class="sw strengths">{#each report.summaryCard.strengths as x}<li>✦ {x}</li>{/each}</ul>{/if}
        {#if report.summaryCard?.warnings?.length}<ul class="sw warnings">{#each report.summaryCard.warnings as x}<li>⚠ {x}</li>{/each}</ul>{/if}
      </section>

      <section class="evidenceStrip">
        <div class="evHead">근거 출처 <span class="muted">— 이 보고서를 계산한 dartlab 엔진</span></div>
        <div class="evEngines">
          {#each Object.entries(report.provenanceFrame?.engines ?? {}) as [eng, info]}
            <div class="evEngine"><span class="evDot ready"></span><span class="evLabel">{(info as any).label ?? engineLabel[eng] ?? eng}</span><span class="evMeta">{(info as any).sections}섹션 · {(info as any).blocks}블록</span></div>
          {/each}
          {#each Object.entries(report.evidenceFrame?.axes ?? {}) as [axis, ax]}
            <div class="evEngine"><span class="evDot ready"></span><span class="evLabel">{axis}</span><span class="evMeta">{((ax as any).evidenceIds ?? []).join(' · ')}</span></div>
          {/each}
        </div>
        <div class="evNote">{report.provenanceFrame?.note}</div>
      </section>

      {#if report.keyFindings?.length}
        <section class="keyFindings">
          <div class="kfHead">핵심 발견 <span class="muted">— 엔진 측정값 자동 추출 (판정어휘 제거)</span></div>
          {#each report.keyFindings as kf}
            <div class="kfRow"><span class="chip kfTag">{kf.key}</span><span class="kfText">{kf.finding}</span><span class="kfSrc">{engineLabel[kf.sourceEngine] ?? kf.sourceEngine}</span></div>
          {/each}
        </section>
      {/if}

      <!-- 6막 스파인 내비 -->
      {#if actSpine.length > 1}
        <nav class="actNav">
          {#each actSpine as a}<button class="actNavItem" onclick={() => scrollAct(a.act)}>{a.header.split(':')[0]}</button>{/each}
        </nav>
      {/if}

      {#if view.missing.length && activeType !== 'full'}
        <div class="missingNote">이 관점({activeRt?.label})의 섹션 중 <b>{view.missing.length}개</b>는 이 회사 데이터에서 미산출 — {view.missing.join(', ')} (정직 스킵, 억지 채움 없음)</div>
      {/if}

      <div class="sections">
        {#each view.sections as sec, i (sec.key)}
          {#if (i === 0 || view.sections[i - 1]?.act !== sec.act) && sec.actHeader}
            <h2 class="actHeader" id={`act-${sec.act}`}>{sec.actHeader}</h2>
          {/if}
          <section class="rptSection src-{sec.sourceEngine}" class:emph={sec._emph}>
            <div class="secHead">
              <h3>{sec.title}</h3>
              <span class="chip srcBadge src-{sec.sourceEngine}">{engineLabel[sec.sourceEngine] ?? sec.sourceEngine}</span>
            </div>
            {#each sec.blocks as b}
              {#if b.type === 'heading'}
                <h4 class="bHeading">{b.title}</h4>
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
                <ul class="bFlags {b.kind}">{#each b.flags as f}<li>{b.kind === 'opportunity' ? '✦' : '⚠'} {f}</li>{/each}</ul>
              {/if}
            {/each}
          </section>
        {/each}
      </div>

      <footer class="rptFooter">
        {#if report.assumptionsNote}<div class="assump">가정·한계: {report.assumptionsNote}</div>{/if}
        <div class="footLine">
          <span>데이터 as-of {report.bakedAt}</span><span class="dot">·</span>
          <span>모든 수치 = dartlab 엔진({Object.keys(report.provenanceFrame?.engines ?? {}).map((e) => engineLabel[e] ?? e).join('·')}) 산출</span><span class="dot">·</span>
          <span>sourceEngine = 계산 엔진(원천 DART 공시 줄 아님)</span><span class="dot">·</span><span class="muted">투자 권유 아님</span>
        </div>
      </footer>
    </article>
  {/if}
</div>

<style>
  .rptRoot {
    --bg: #0d1117; --panel: #161b22; --panel2: #1c222b; --ink: #e8eef5; --dim: #8b949e;
    --bd: rgba(255, 255, 255, 0.09); --bd2: rgba(255, 255, 255, 0.16);
    --accent: #58a6ff; --up: #3fb950; --down: #f85149; --warn: #d29922; --emph: #388bfd;
    --e-analysis: #58a6ff; --e-credit: #f85149; --e-quant: #56d4dd; --e-industry: #3fb950; --e-macro: #d29922; --e-story: #bc8cff;
    --mono: ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;
    --sans: 'Pretendard', -apple-system, system-ui, sans-serif;
    background: var(--bg); color: var(--ink); min-height: 100vh; font-family: var(--sans); font-size: 13px; line-height: 1.55;
  }

  .devbar { display: flex; align-items: center; gap: 10px; padding: 8px 16px; background: #090c10; border-bottom: 1px solid var(--bd); position: sticky; top: 0; z-index: 20; }
  .devtag { font-family: var(--mono); font-size: 11px; color: var(--warn); letter-spacing: 0.04em; }
  .devlink { color: var(--dim); text-decoration: none; font-size: 12px; padding: 3px 9px; border-radius: 6px; border: 1px solid transparent; }
  .devlink.on { color: var(--ink); border-color: var(--bd); background: var(--panel); }
  .devlink:hover { color: var(--ink); }
  .spacer { flex: 1; }
  .printBtn { background: var(--accent); color: #06101f; border: 0; padding: 6px 14px; border-radius: 7px; font-weight: 700; cursor: pointer; font-size: 12px; }
  .printBtn:hover { filter: brightness(1.08); }

  .rptDoc { max-width: 1000px; margin: 0 auto; padding: 30px 36px 70px; }
  .skip { text-align: center; padding-top: 90px; }
  .skip h1 { font-size: 23px; } .skipReason { font-family: var(--mono); color: var(--warn); }

  /* 메타 리본 */
  .metaRibbon { border-bottom: 2px solid var(--ink); padding-bottom: 15px; margin-bottom: 18px; }
  .metaRibbon h1 { font-size: 31px; font-weight: 800; letter-spacing: -0.02em; margin: 0 0 5px; }
  .metaRibbon h1 .code { font-family: var(--mono); font-size: 16px; color: var(--dim); font-weight: 500; margin-left: 9px; letter-spacing: 0; }
  .metaSub { font-size: 12px; color: var(--dim); display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
  .metaSub .kicker { color: var(--accent); font-weight: 600; }
  .metaSub .dot { opacity: 0.35; }
  .condBadge { color: var(--warn); border: 1px solid var(--warn); border-radius: 4px; padding: 0 6px; font-size: 11px; }

  /* 칩 통일 (chip 프리미티브) */
  .chip { font-size: 11.5px; border-radius: 6px; padding: 3px 9px; border: 1px solid var(--bd); color: var(--ink); white-space: nowrap; }
  .chip.focus { color: var(--accent); border-color: rgba(88, 166, 255, 0.28); background: rgba(88, 166, 255, 0.07); border-radius: 13px; }
  .chip.grade b { font-family: var(--mono); margin-left: 3px; }
  .chip.grade.gA { border-color: var(--up); color: var(--up); }
  .chip.grade.gB { border-color: var(--accent); color: var(--accent); }
  .chip.grade.gC { border-color: var(--warn); color: var(--warn); }
  .chip.grade.gD, .chip.grade.gF { border-color: var(--down); color: var(--down); }
  .note { font-size: 10.5px; color: var(--dim); align-self: center; font-style: italic; }

  .tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; position: sticky; top: 41px; background: var(--bg); padding: 9px 0; z-index: 15; }
  .tab { background: var(--panel); color: var(--dim); border: 1px solid var(--bd); border-radius: 7px; padding: 5px 12px; font-size: 12.5px; cursor: pointer; transition: all 0.12s; }
  .tab.on { color: #fff; background: var(--emph); border-color: var(--emph); font-weight: 700; box-shadow: 0 1px 6px rgba(56, 139, 253, 0.3); }
  .tab:hover:not(.on) { color: var(--ink); border-color: var(--bd2); }
  .tab.thin { opacity: 0.45; } .tab.thin.on { opacity: 1; }
  .thinMark { font-size: 9.5px; color: var(--warn); margin-left: 3px; }
  .printPerspective { display: none; }

  .focusRow { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 16px; }

  .summaryCard { background: linear-gradient(180deg, var(--panel2), var(--panel)); border: 1px solid var(--bd2); border-radius: 12px; padding: 20px 22px; margin-bottom: 16px; }
  .conclusion { font-size: 18px; font-weight: 700; margin-bottom: 11px; letter-spacing: -0.01em; }
  .kpiBand { display: grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: 8px; margin: 4px 0 14px; }
  .kpi { background: rgba(255, 255, 255, 0.03); border: 1px solid var(--bd); border-radius: 8px; padding: 8px 12px; display: flex; flex-direction: column; gap: 3px; }
  .kLabel { font-size: 10.5px; color: var(--dim); }
  .kVal { font-size: 17px; font-weight: 800; font-family: var(--mono); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
  .kVal.neg { color: var(--down); } .kVal.pos { color: var(--up); }
  .overview { font-size: 13.5px; line-height: 1.72; color: #cdd6df; margin: 0 0 13px; }
  .gradeChips { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
  .sw { margin: 11px 0 0; padding-left: 4px; list-style: none; font-size: 12.5px; }
  .sw.strengths li { color: var(--up); } .sw.warnings li { color: var(--warn); }

  .evidenceStrip { border: 1px dashed var(--bd2); border-radius: 10px; padding: 13px 16px; margin-bottom: 16px; }
  .evHead { font-size: 12.5px; font-weight: 700; margin-bottom: 9px; }
  .evEngines { display: flex; flex-wrap: wrap; gap: 16px; }
  .evEngine { display: flex; align-items: center; gap: 7px; }
  .evDot { width: 8px; height: 8px; border-radius: 50%; background: var(--up); }
  .evLabel { font-size: 12.5px; font-weight: 600; }
  .evMeta { font-size: 11px; color: var(--dim); font-family: var(--mono); }
  .evNote { font-size: 10.5px; color: var(--dim); margin-top: 8px; font-style: italic; }

  .keyFindings { margin-bottom: 18px; }
  .kfHead { font-size: 13px; font-weight: 700; margin-bottom: 9px; border-left: 3px solid var(--accent); padding-left: 9px; }
  .kfRow { display: grid; grid-template-columns: 86px 1fr auto; gap: 11px; padding: 7px 0; border-bottom: 1px solid var(--bd); align-items: baseline; }
  .chip.kfTag { color: var(--accent); border-color: rgba(88, 166, 255, 0.25); font-weight: 600; padding: 1px 8px; font-size: 11px; justify-self: start; }
  .kfText { font-size: 12.5px; line-height: 1.5; }
  .kfSrc { font-size: 10.5px; color: var(--dim); }

  /* 6막 스파인 내비 */
  .actNav { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 18px; padding: 8px 10px; background: var(--panel); border: 1px solid var(--bd); border-radius: 9px; }
  .actNavItem { background: transparent; border: 0; color: var(--dim); font-size: 11.5px; cursor: pointer; padding: 2px 8px; border-radius: 5px; }
  .actNavItem:hover { color: var(--accent); background: rgba(88, 166, 255, 0.08); }

  .missingNote { font-size: 12px; color: var(--warn); background: rgba(210, 153, 34, 0.07); border: 1px solid rgba(210, 153, 34, 0.22); border-radius: 8px; padding: 9px 13px; margin-bottom: 16px; }

  /* 막 헤더 = 전폭 밴드 (챕터 구분) */
  .actHeader { font-size: 18px; font-weight: 800; color: var(--ink); margin: 34px -36px 16px; padding: 9px 36px; letter-spacing: -0.01em; background: linear-gradient(90deg, rgba(56, 139, 253, 0.12), transparent); border-top: 1px solid var(--bd2); border-bottom: 1px solid var(--bd); scroll-margin-top: 92px; }

  /* 섹션 = 좌측 액센트 바(엔진색) */
  .rptSection { margin-bottom: 16px; padding: 15px 17px; background: var(--panel); border: 1px solid var(--bd); border-left: 3px solid var(--e-analysis); border-radius: 8px; }
  .rptSection.src-credit { border-left-color: var(--e-credit); }
  .rptSection.src-quant { border-left-color: var(--e-quant); }
  .rptSection.src-industry { border-left-color: var(--e-industry); }
  .rptSection.src-macro { border-left-color: var(--e-macro); }
  .rptSection.src-story { border-left-color: var(--e-story); }
  .rptSection.emph { box-shadow: 0 0 0 1px rgba(56, 139, 253, 0.35); }
  .secHead { display: flex; justify-content: space-between; align-items: center; margin-bottom: 9px; }
  .secHead h3 { font-size: 16px; font-weight: 700; margin: 0; letter-spacing: -0.01em; }
  .chip.srcBadge { font-size: 10.5px; padding: 2px 8px; color: var(--dim); }
  .chip.srcBadge.src-analysis { color: var(--e-analysis); border-color: rgba(88, 166, 255, 0.3); }
  .chip.srcBadge.src-credit { color: var(--e-credit); border-color: rgba(248, 81, 73, 0.3); }
  .chip.srcBadge.src-quant { color: var(--e-quant); border-color: rgba(86, 212, 221, 0.3); }
  .chip.srcBadge.src-industry { color: var(--e-industry); border-color: rgba(63, 185, 80, 0.3); }
  .chip.srcBadge.src-macro { color: var(--e-macro); border-color: rgba(210, 153, 34, 0.3); }

  .bHeading { font-size: 12.5px; font-weight: 700; margin: 13px 0 6px; color: #aeb9c4; text-transform: none; }
  .bText { font-size: 12.5px; line-height: 1.72; margin: 6px 0; }

  .bMetrics { display: grid; grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); gap: 8px; margin: 9px 0; }
  .metric { background: var(--bg); border: 1px solid var(--bd); border-radius: 7px; padding: 7px 11px; display: flex; flex-direction: column; gap: 2px; }
  .mLabel { font-size: 10.5px; color: var(--dim); }
  .mValue { font-size: 15px; font-weight: 700; font-family: var(--mono); font-variant-numeric: tabular-nums; }
  .mValue.neg { color: var(--down); } .mValue.pos { color: var(--up); }

  .bTableWrap { margin: 10px 0; overflow-x: auto; }
  .tCap { font-size: 11.5px; color: var(--dim); margin-bottom: 5px; font-weight: 600; }
  .bTable { border-collapse: collapse; font-size: 12px; width: 100%; }
  .bTable th { padding: 6px 10px; border-bottom: 1px solid var(--bd2); color: var(--dim); font-weight: 600; font-family: var(--mono); }
  .bTable th.lbl { text-align: left; font-family: var(--sans); }
  .bTable th.num, .bTable th.sparkCol { text-align: right; }
  .bTable td { padding: 5px 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.035); }
  .bTable td.lbl { text-align: left; color: #cdd6df; font-weight: 500; white-space: nowrap; }
  .bTable td.num { text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; }
  .bTable td.num.neg { color: var(--down); } .bTable td.num.pos { color: var(--up); }
  .bTable tbody tr:nth-child(even) { background: rgba(255, 255, 255, 0.022); }
  .bTable tbody tr:hover { background: rgba(88, 166, 255, 0.06); }
  .bTable td.sparkCol { text-align: right; padding-right: 4px; width: 58px; }
  .spark { vertical-align: middle; color: var(--dim); }
  .spark.up { color: var(--up); } .spark.down { color: var(--down); } .spark.flat { color: var(--dim); }

  .bFlags { list-style: none; padding-left: 2px; margin: 8px 0; font-size: 12.5px; }
  .bFlags.warning li { color: var(--warn); } .bFlags.opportunity li { color: var(--up); }

  .rptFooter { margin-top: 32px; padding-top: 15px; border-top: 1px solid var(--bd); font-size: 11px; color: var(--dim); }
  .assump { margin-bottom: 7px; color: var(--warn); opacity: 0.85; }
  .footLine { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .footLine .dot { opacity: 0.35; }
  .muted { color: var(--dim); }

  /* ── 인쇄 — 토큰 변수 라이트 재바인딩 ── */
  @media print {
    .rptRoot {
      --bg: #fff; --panel: #fafafa; --panel2: #f5f7f9; --ink: #1a1a1a; --dim: #555a60; --bd: #e2e6ea; --bd2: #cfd5db;
      --accent: #0550ae; --up: #1a7f37; --down: #b02a1a; --warn: #8a6100; --emph: #0550ae;
      --e-analysis: #0550ae; --e-credit: #b02a1a; --e-quant: #0a7d86; --e-industry: #1a7f37; --e-macro: #8a6100; --e-story: #6f42c1;
      background: #fff; color: #1a1a1a; font-size: 10.2pt;
    }
    .devbar, .tabs, .actNav { display: none !important; }
    .printPerspective { display: block; font-size: 11px; color: #555; margin-bottom: 10px; font-weight: 600; }
    .rptDoc { max-width: 100%; padding: 0; }
    .summaryCard, .rptSection, .evidenceStrip { background: #fafafa !important; break-inside: avoid; }
    .actHeader { margin: 22px 0 12px; padding: 7px 12px; background: #eef2f6 !important; break-after: avoid; }
    .bTable tbody tr:nth-child(even) { background: #f4f6f8 !important; }
    .spark polyline { stroke-width: 1.7px; }
    .spark.flat { color: #6b7280; }
    .kpi { background: #f5f7f9 !important; }
    .chip.focus { background: none; }
    @page { margin: 14mm 13mm; }
  }
</style>
