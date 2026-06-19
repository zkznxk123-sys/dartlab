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

  // 초기 reportType: URL ?type= 우선
  $effect(() => {
    if (data.reportType && manifest?.reportTypes?.[data.reportType]) activeType = data.reportType;
  });

  const activeRt = $derived(manifest?.reportTypes?.[activeType] ?? null);

  // buildReportView — payload 위 정적 투영 (재fetch 0)
  type Sec = any;
  const sectionsByKey = $derived(
    new Map<string, Sec>((report?.sections ?? []).map((s: Sec) => [s.key, s]))
  );
  const view = $derived.by(() => {
    if (!report || !activeRt) return { sections: [], focusQuestions: [], missing: [] as string[], publishable: true };
    const order: string[] = activeRt.sectionOrder ?? [];
    const emphasize = new Set<string>(activeRt.emphasize ?? []);
    const present: Sec[] = [];
    const missing: string[] = [];
    for (const key of order) {
      const s = sectionsByKey.get(key);
      if (s && s.blocks?.length) present.push({ ...s, _emph: emphasize.has(key) });
      else missing.push(key);
    }
    // full 등 order 가 비었으면 payload 순서 그대로
    const sections = present.length ? present : (report.sections ?? []);
    return {
      sections,
      focusQuestions: activeRt.focusQuestions ?? [],
      missing,
      publishable: sections.length >= 2
    };
  });

  const engineLabel: Record<string, string> = {
    analysis: '재무분석', credit: '신용평가', quant: '시장·기술', industry: '산업비교', macro: '거시', story: '종합서사'
  };

  function actHeaderFor(sec: Sec): string | null {
    return sec.actHeader ?? null;
  }
  function startsNewAct(sec: Sec, idx: number, sections: Sec[]): boolean {
    return idx === 0 || sections[idx - 1]?.act !== sec.act;
  }

  // 관점별 발행 충실도 — sectionOrder 중 실제 present 섹션 수 (정직 dim)
  function presentCount(rt: any): number {
    if (!report) return 0;
    const order: string[] = rt.sectionOrder ?? [];
    if (!order.length) return report.sections?.length ?? 0;
    return order.filter((k: string) => sectionsByKey.get(k)?.blocks?.length).length;
  }
  function chartHasData(b: any): boolean {
    const series = b?.spec?.series ?? b?.spec?.data ?? [];
    const flat = JSON.stringify(series);
    return flat.includes(':') && /[0-9]/.test(flat) && !/^\[?(null,?)+\]?$/.test(flat.replace(/[^null,\[\]]/g, ''));
  }

  function printReport() {
    if (typeof window !== 'undefined') window.print();
  }

  // 회사 전환 (dev) — URL 갱신
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
  <!-- dev 툴바 (인쇄 시 숨김) -->
  <nav class="devbar">
    <span class="devtag">DEV /lab/report</span>
    {#each samples as s}
      <a class="devlink" class:on={data.sym === s.code} href={`/lab/report?sym=${s.code}&type=${activeType}`}>{s.name}</a>
    {/each}
    <span class="spacer"></span>
    <button class="printBtn" onclick={printReport}>🖨 인쇄 / PDF</button>
  </nav>

  {#if !report}
    <!-- honest-skip -->
    <div class="rptDoc skip">
      <h1>데이터 부족 — 보고서 미생성</h1>
      <p class="skipReason">종목 {data.sym}: {data.skipReason ?? '해당 회사의 분석 페이로드가 굽지 않았습니다(reject-gate).'}</p>
      <p class="muted">약한 발행보다 정직한 스킵 — dartlab 은 데이터가 빈약한 회사의 보고서를 만들지 않습니다.</p>
    </div>
  {:else}
    <article class="rptDoc">
      <!-- ── 메타 리본 ── -->
      <header class="metaRibbon">
        <div class="metaMain">
          <h1>{report.corpName} <span class="code">{report.stockCode}</span></h1>
          <div class="metaSub">
            <span>기업분석보고서</span>
            {#if report.template}<span class="dot">·</span><span>{report.template}</span>{/if}
            <span class="dot">·</span><span>as-of {report.bakedAt}</span>
            <span class="dot">·</span><span class="muted">dartlab 엔진 자동생성</span>
            {#if report.meta?.qualityLabel === 'conditional'}
              <span class="dot">·</span><span class="condBadge">조건부</span>
            {/if}
          </div>
        </div>
      </header>

      <!-- ── 관점 탭 (인쇄 시 숨김) ── -->
      <div class="tabs">
        {#each perspectives as rt}
          <button
            class="tab"
            class:on={rt.key === activeType}
            class:thin={presentCount(rt) < 3}
            onclick={() => (activeType = rt.key)}
            title={presentCount(rt) < 3 ? `${rt.description} — 데이터 제한(${presentCount(rt)}개 섹션)` : rt.description}
          >
            {rt.label}{#if presentCount(rt) < 3}<span class="thinMark">·제한</span>{/if}
          </button>
        {/each}
      </div>

      <!-- 인쇄용 관점 라벨 -->
      <div class="printPerspective">관점: {activeRt?.label ?? '전체'}</div>

      <!-- ── focusQuestions ── -->
      {#if view.focusQuestions.length}
        <div class="focusRow">
          {#each view.focusQuestions as q}<span class="focusChip">{q}</span>{/each}
        </div>
      {/if}

      <!-- ── 종합 의견 (SummaryCard) ── -->
      <section class="summaryCard">
        <div class="conclusion">{report.summaryCard?.conclusion}</div>
        {#if report.narrativeOverview}
          <p class="overview">{report.narrativeOverview}</p>
        {/if}
        <div class="gradeChips">
          {#each Object.entries(report.summaryCard?.grades ?? {}) as [area, grade]}
            <span class="gradeChip g{grade}">{area} <b>{grade}</b></span>
          {/each}
          {#if report.summaryCard?.gradesNote}
            <span class="gradesNote">{report.summaryCard.gradesNote}</span>
          {/if}
        </div>
        {#if report.summaryCard?.strengths?.length}
          <ul class="sw strengths">{#each report.summaryCard.strengths as x}<li>✦ {x}</li>{/each}</ul>
        {/if}
        {#if report.summaryCard?.warnings?.length}
          <ul class="sw warnings">{#each report.summaryCard.warnings as x}<li>⚠ {x}</li>{/each}</ul>
        {/if}
      </section>

      <!-- ── 근거 출처 (EvidenceStrip — 점수 비노출, provenance) ── -->
      <section class="evidenceStrip">
        <div class="evHead">근거 출처 <span class="muted">— 이 보고서를 계산한 dartlab 엔진</span></div>
        <div class="evEngines">
          {#each Object.entries(report.provenanceFrame?.engines ?? {}) as [eng, info]}
            <div class="evEngine">
              <span class="evDot ready"></span>
              <span class="evLabel">{(info as any).label ?? engineLabel[eng] ?? eng}</span>
              <span class="evMeta">{(info as any).sections}개 섹션 · {(info as any).blocks}개 블록</span>
            </div>
          {/each}
          {#each Object.entries(report.evidenceFrame?.axes ?? {}) as [axis, ax]}
            <div class="evEngine">
              <span class="evDot ready"></span>
              <span class="evLabel">{axis}</span>
              <span class="evMeta">{((ax as any).evidenceIds ?? []).join(' · ')}</span>
            </div>
          {/each}
        </div>
        <div class="evNote">{report.provenanceFrame?.note}</div>
      </section>

      <!-- ── 핵심 발견 ── -->
      {#if report.keyFindings?.length}
        <section class="keyFindings">
          <div class="kfHead">핵심 발견 <span class="muted">— 엔진 측정값 자동 추출 (판정어휘 제거)</span></div>
          {#each report.keyFindings as kf}
            <div class="kfRow">
              <span class="kfTag">{kf.key}</span>
              <span class="kfText">{kf.finding}</span>
              <span class="kfSrc">{engineLabel[kf.sourceEngine] ?? kf.sourceEngine}</span>
            </div>
          {/each}
        </section>
      {/if}

      <!-- ── 관점 미충족 정직 라벨 ── -->
      {#if view.missing.length && activeType !== 'full'}
        <div class="missingNote">
          이 관점({activeRt?.label})의 섹션 중 <b>{view.missing.length}개</b>는 이 회사 데이터에서 미산출 —
          {view.missing.join(', ')} (정직 스킵, 억지 채움 없음)
        </div>
      {/if}

      <!-- ── 6막 섹션 ── -->
      <div class="sections">
        {#each view.sections as sec, i}
          {#if startsNewAct(sec, i, view.sections) && actHeaderFor(sec)}
            <h2 class="actHeader">{actHeaderFor(sec)}</h2>
          {/if}
          <section class="rptSection" class:emph={sec._emph}>
            <div class="secHead">
              <h3>{sec.title}</h3>
              <span class="srcBadge src-{sec.sourceEngine}">{engineLabel[sec.sourceEngine] ?? sec.sourceEngine}</span>
            </div>
            {#each sec.blocks as b}
              {#if b.type === 'heading'}
                <h4 class="bHeading">{b.title}</h4>
              {:else if b.type === 'text'}
                <p class="bText">{b.text}</p>
              {:else if b.type === 'metrics'}
                <div class="bMetrics">
                  {#each b.metrics as m}
                    <div class="metric"><span class="mLabel">{m.label}</span><span class="mValue">{m.value}</span></div>
                  {/each}
                </div>
              {:else if b.type === 'table'}
                <div class="bTableWrap">
                  {#if b.label}<div class="tCap">{b.label}</div>{/if}
                  {#if b.data?.length}
                    <table class="bTable">
                      <thead><tr>{#each Object.keys(b.data[0]) as c}<th>{c}</th>{/each}</tr></thead>
                      <tbody>
                        {#each b.data as row}
                          <tr>{#each Object.keys(b.data[0]) as c}<td>{row[c]}</td>{/each}</tr>
                        {/each}
                      </tbody>
                    </table>
                  {/if}
                </div>
              {:else if b.type === 'flags'}
                <ul class="bFlags {b.kind}">
                  {#each b.flags as f}<li>{b.kind === 'opportunity' ? '✦' : '⚠'} {f}</li>{/each}
                </ul>
              {:else if b.type === 'chart' && chartHasData(b)}
                <div class="bChart">📊 {b.spec?.title ?? b.caption ?? '차트'} <span class="muted">(차트 렌더는 P2 — 데이터는 위 표 참조)</span></div>
              {/if}
            {/each}
          </section>
        {/each}
      </div>

      <!-- ── 푸터 ── -->
      <footer class="rptFooter">
        <span>데이터 as-of {report.bakedAt}</span>
        <span class="dot">·</span>
        <span>모든 수치는 dartlab 엔진({Object.keys(report.provenanceFrame?.engines ?? {}).map((e) => engineLabel[e] ?? e).join('·')}) 산출</span>
        <span class="dot">·</span>
        <span>sourceEngine = 계산 엔진(원천 DART 공시 줄 아님)</span>
        <span class="dot">·</span>
        <span class="muted">투자 권유 아님</span>
      </footer>
    </article>
  {/if}
</div>

<style>
  /* 자기완결 테마 — 본진 토큰 비의존 (dev 격리). 다크 기본 → 인쇄 라이트. */
  .rptRoot {
    --bg: #0e1116;
    --panel: #161b22;
    --ink: #e6edf3;
    --dim: #8b949e;
    --bd: rgba(255, 255, 255, 0.09);
    --accent: #58a6ff;
    --up: #3fb950;
    --down: #f85149;
    --warn: #d29922;
    --emph: #1f6feb;
    --mono: ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;
    --sans: 'Pretendard', -apple-system, system-ui, sans-serif;
    background: var(--bg);
    color: var(--ink);
    min-height: 100vh;
    font-family: var(--sans);
    font-size: 13px;
    line-height: 1.55;
  }

  .devbar {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 16px; background: #0a0d12; border-bottom: 1px solid var(--bd);
    position: sticky; top: 0; z-index: 10;
  }
  .devtag { font-family: var(--mono); font-size: 11px; color: var(--warn); letter-spacing: 0.04em; }
  .devlink { color: var(--dim); text-decoration: none; font-size: 12px; padding: 3px 9px; border-radius: 6px; border: 1px solid transparent; }
  .devlink.on { color: var(--ink); border-color: var(--bd); background: var(--panel); }
  .devlink:hover { color: var(--ink); }
  .spacer { flex: 1; }
  .printBtn { background: var(--accent); color: #06101f; border: 0; padding: 6px 14px; border-radius: 7px; font-weight: 700; cursor: pointer; font-size: 12px; }

  .rptDoc { max-width: 980px; margin: 0 auto; padding: 28px 34px 60px; }

  .skip { text-align: center; padding-top: 80px; }
  .skip h1 { font-size: 22px; }
  .skipReason { font-family: var(--mono); color: var(--warn); }

  .metaRibbon { border-bottom: 2px solid var(--ink); padding-bottom: 14px; margin-bottom: 16px; }
  .metaMain h1 { font-size: 26px; font-weight: 800; margin: 0 0 4px; }
  .metaMain h1 .code { font-family: var(--mono); font-size: 15px; color: var(--dim); font-weight: 500; margin-left: 8px; }
  .metaSub { font-size: 12px; color: var(--dim); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .metaSub .dot { opacity: 0.4; }
  .condBadge { color: var(--warn); border: 1px solid var(--warn); border-radius: 4px; padding: 0 5px; font-size: 11px; }

  .tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; position: sticky; top: 41px; background: var(--bg); padding: 8px 0; z-index: 5; }
  .tab { background: var(--panel); color: var(--dim); border: 1px solid var(--bd); border-radius: 7px; padding: 5px 12px; font-size: 12.5px; cursor: pointer; }
  .tab.on { color: #fff; background: var(--emph); border-color: var(--emph); font-weight: 700; }
  .tab:hover:not(.on) { color: var(--ink); }
  .tab.thin { opacity: 0.5; }
  .tab.thin.on { opacity: 1; }
  .thinMark { font-size: 9.5px; color: var(--warn); margin-left: 3px; }
  .printPerspective { display: none; }
  .gradesNote { font-size: 10.5px; color: var(--dim); align-self: center; font-style: italic; }

  .focusRow { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 16px; }
  .focusChip { font-size: 12px; color: var(--accent); background: rgba(88, 166, 255, 0.08); border: 1px solid rgba(88, 166, 255, 0.2); border-radius: 14px; padding: 3px 11px; }

  .summaryCard { background: var(--panel); border: 1px solid var(--bd); border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; }
  .conclusion { font-size: 17px; font-weight: 700; margin-bottom: 8px; }
  .overview { font-size: 13.5px; line-height: 1.7; color: #c9d3de; margin: 0 0 12px; }
  .gradeChips { display: flex; flex-wrap: wrap; gap: 7px; }
  .gradeChip { font-size: 12px; border-radius: 6px; padding: 3px 9px; border: 1px solid var(--bd); color: var(--ink); }
  .gradeChip b { font-family: var(--mono); margin-left: 3px; }
  .gradeChip.gA { border-color: var(--up); color: var(--up); }
  .gradeChip.gB { border-color: var(--accent); color: var(--accent); }
  .gradeChip.gC { border-color: var(--warn); color: var(--warn); }
  .gradeChip.gD, .gradeChip.gF { border-color: var(--down); color: var(--down); }
  .sw { margin: 10px 0 0; padding-left: 4px; list-style: none; font-size: 12.5px; }
  .sw.strengths li { color: var(--up); }
  .sw.warnings li { color: var(--warn); }

  .evidenceStrip { border: 1px dashed var(--bd); border-radius: 10px; padding: 13px 16px; margin-bottom: 16px; }
  .evHead { font-size: 12.5px; font-weight: 700; margin-bottom: 9px; }
  .evEngines { display: flex; flex-wrap: wrap; gap: 14px; }
  .evEngine { display: flex; align-items: center; gap: 7px; }
  .evDot { width: 8px; height: 8px; border-radius: 50%; }
  .evDot.ready { background: var(--up); }
  .evLabel { font-size: 12.5px; font-weight: 600; }
  .evMeta { font-size: 11px; color: var(--dim); font-family: var(--mono); }
  .evNote { font-size: 10.5px; color: var(--dim); margin-top: 8px; font-style: italic; }

  .keyFindings { margin-bottom: 18px; }
  .kfHead { font-size: 13px; font-weight: 700; margin-bottom: 8px; border-left: 3px solid var(--accent); padding-left: 8px; }
  .kfRow { display: grid; grid-template-columns: 84px 1fr auto; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--bd); align-items: baseline; }
  .kfTag { font-size: 11.5px; color: var(--accent); font-weight: 600; }
  .kfText { font-size: 12.5px; }
  .kfSrc { font-size: 10.5px; color: var(--dim); }

  .missingNote { font-size: 12px; color: var(--warn); background: rgba(210, 153, 34, 0.07); border: 1px solid rgba(210, 153, 34, 0.2); border-radius: 8px; padding: 9px 13px; margin-bottom: 16px; }

  .actHeader { font-size: 16px; font-weight: 800; color: var(--accent); margin: 26px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--bd); }
  .rptSection { margin-bottom: 18px; padding: 14px 16px; background: var(--panel); border: 1px solid var(--bd); border-radius: 10px; }
  .rptSection.emph { border-color: var(--emph); box-shadow: 0 0 0 1px rgba(31, 111, 235, 0.3); }
  .secHead { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .secHead h3 { font-size: 15px; font-weight: 700; margin: 0; }
  .srcBadge { font-size: 10.5px; padding: 2px 8px; border-radius: 5px; border: 1px solid var(--bd); color: var(--dim); }
  .srcBadge.src-credit { color: var(--down); border-color: rgba(248, 81, 73, 0.3); }
  .srcBadge.src-quant { color: var(--accent); border-color: rgba(88, 166, 255, 0.3); }
  .srcBadge.src-industry { color: var(--up); border-color: rgba(63, 185, 80, 0.3); }

  .bHeading { font-size: 13px; font-weight: 700; margin: 12px 0 6px; color: #c9d3de; }
  .bText { font-size: 13px; line-height: 1.7; margin: 6px 0; }
  .bMetrics { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; margin: 8px 0; }
  .metric { background: var(--bg); border: 1px solid var(--bd); border-radius: 7px; padding: 7px 11px; display: flex; flex-direction: column; gap: 2px; }
  .mLabel { font-size: 10.5px; color: var(--dim); }
  .mValue { font-size: 15px; font-weight: 700; font-family: var(--mono); }

  .bTableWrap { margin: 9px 0; overflow-x: auto; }
  .tCap { font-size: 11.5px; color: var(--dim); margin-bottom: 4px; }
  .bTable { border-collapse: collapse; font-size: 11.5px; width: 100%; font-family: var(--mono); }
  .bTable th { text-align: right; padding: 4px 9px; border-bottom: 1px solid var(--bd); color: var(--dim); font-weight: 600; }
  .bTable th:first-child, .bTable td:first-child { text-align: left; font-family: var(--sans); }
  .bTable td { text-align: right; padding: 4px 9px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }

  .bFlags { list-style: none; padding-left: 2px; margin: 8px 0; font-size: 12.5px; }
  .bFlags.warning li { color: var(--warn); }
  .bFlags.opportunity li { color: var(--up); }

  .bChart { font-size: 12px; color: var(--dim); background: var(--bg); border: 1px dashed var(--bd); border-radius: 7px; padding: 9px 12px; margin: 8px 0; }

  .rptFooter { margin-top: 30px; padding-top: 14px; border-top: 1px solid var(--bd); font-size: 11px; color: var(--dim); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .rptFooter .dot { opacity: 0.4; }
  .muted { color: var(--dim); }

  /* ── 인쇄 — 다크→라이트 A4 문서, zero-dep PDF ──
     PRD: 토큰 *변수 자체*를 라이트로 재바인딩 (요소별 override 아님 — var(--bg) 참조 전부 자동 전환). */
  @media print {
    .rptRoot {
      --bg: #ffffff;
      --panel: #fafafa;
      --ink: #1a1a1a;
      --dim: #555a60;
      --bd: #dfe3e8;
      --accent: #0550ae;
      --up: #1a7f37;
      --down: #b02a1a;
      --warn: #9a6700;
      --emph: #0550ae;
      background: #fff;
      color: #1a1a1a;
      font-size: 10.5pt;
    }
    .devbar, .tabs { display: none !important; }
    .printPerspective { display: block; font-size: 11px; color: #555; margin-bottom: 10px; font-weight: 600; }
    .rptDoc { max-width: 100%; padding: 0; }
    .metaRibbon { border-bottom: 2px solid #1a1a1a; }
    .summaryCard, .rptSection, .evidenceStrip, .metric, .bChart { background: #fafafa !important; break-inside: avoid; }
    .rptSection.emph { box-shadow: none; border: 2px solid var(--emph); }
    .actHeader { break-after: avoid; }
    .focusChip { background: none; }
    .bChart { color: #555; }
    @page { margin: 15mm 13mm; }
  }
</style>
