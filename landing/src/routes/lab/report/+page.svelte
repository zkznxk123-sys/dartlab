<script lang="ts">
  import type { PageData } from './$types';
  import { base } from '$app/paths';
  import { setStaticBase } from '@dartlab/ui-runtime/data/dartlabData';
  import { getPublicRuntime } from '$lib/runtime/publicRuntime';
  import { buildReport } from '$lib/report/build';
  import { isSkipped, type ReportModel } from '$lib/report/model';
  import { PERSPECTIVES } from '$lib/report/perspectives';

  let { data }: { data: PageData } = $props();

  // 정적 씨데이터 base 주입 (loadJson SSOT) — search-index.json 등 데이터 작업대 직독 경로 정합.
  setStaticBase(base);
  const rt = getPublicRuntime();

  // 화이트/다크 — A4 용지 위 두 모드. 기본 = 화이트(진짜 보고서)
  let theme = $state<'light' | 'dark'>('light');
  function toggleTheme() {
    theme = theme === 'light' ? 'dark' : 'light';
  }

  // 관점 — 같은 회사를 5개 렌즈로. 데이터 작업대 리얼타임. URL view= 로 초기 관점 동기화.
  let perspectiveKey = $state<string>('earningsPower');
  $effect(() => {
    if (data.perspective) perspectiveKey = data.perspective;
  });

  // ── 리얼타임 빌드 (종목·관점 변경 시 동시성 토큰 가드) ──
  let model = $state<ReportModel | null>(null);
  let status = $state<'loading' | 'ready' | 'skipped' | 'error'>('loading');
  let skipReason = $state<string>('');
  let buildTok = 0;
  $effect(() => {
    const code = data.sym;
    const view = perspectiveKey;
    const tk = ++buildTok;
    status = 'loading';
    model = null;
    skipReason = '';
    buildReport(rt, code, view)
      .then((res) => {
        if (tk !== buildTok) return;
        if (isSkipped(res)) {
          status = 'skipped';
          skipReason = res.reason;
        } else {
          model = res;
          status = 'ready';
        }
      })
      .catch((e) => {
        if (tk !== buildTok) return;
        status = 'error';
        skipReason = String(e?.message ?? e);
      });
  });

  function selectPerspective(key: string) {
    perspectiveKey = key;
    if (typeof document !== 'undefined') document.querySelector('.main')?.scrollTo({ top: 0 });
  }

  // ── 렌더 헬퍼 (기존 렌더러 재사용) ──
  function clean(t: unknown): string {
    return String(t ?? '').replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*\*/g, '');
  }

  const engineLabel: Record<string, string> = {
    analysis: '재무분석', credit: '신용평가', quant: '시장·기술', industry: '산업비교', macro: '거시', story: '종합서사'
  };

  function cellTone(v: unknown): string {
    const s = String(v ?? '').trim();
    if (!s || s === '-') return '';
    const core = s.replace(/[%조억원배일pP ,]/g, '');
    if (/^[-−△▼(]/.test(s) || /^-/.test(core)) return 'neg';
    if (/^[+▲]/.test(s)) return 'pos';
    return '';
  }

  // 판정 어휘 신호색 — 신용/건전성 점검표의 '양호/주의' 전용(적색=음수 SSOT와 분리해 주의=황갈).
  function verdictTone(v: unknown): string {
    const s = String(v ?? '').trim();
    if (s.startsWith('양호') || s === '안정' || s === '충족') return 'ok';
    if (s.startsWith('주의') || s === '경계' || s === '미달') return 'warn';
    return ''; // '산출 불가' 등 → 중립
  }
  // 비숫자 의미 컬럼(좌측 텍스트, cellTone 미적용) 화이트리스트
  const TXT_COLS = new Set(['최근 범위', '기준']);

  function spark(row: Record<string, string>, yearCols: string[]) {
    const pairs: { yr: number; n: number }[] = [];
    for (const yk of yearCols) {
      const yr = parseInt(yk, 10);
      if (!Number.isFinite(yr)) continue;
      const raw = String(row[yk] ?? '').replace(/[^0-9.\-]/g, '');
      const n = parseFloat(raw);
      pairs.push({ yr, n: Number.isFinite(n) ? n : NaN });
    }
    pairs.sort((a, b) => a.yr - b.yr);
    const nums: number[] = pairs.map((p) => p.n);
    const valid = nums.filter((n) => Number.isFinite(n));
    if (valid.length < 3) return null;
    // robust 도메인 — 단일 극단값(예: NAVER FY21 순이익률 241.7%)이 나머지를 1px 평지로
    // 깔아 추세를 거짓 전달하지 않게 median±3·IQR 로 *그리는 값만* 클램프(표 숫자는 불변).
    const sorted = [...valid].sort((a, b) => a - b);
    const q = (p: number) => sorted[Math.max(0, Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p)))];
    const med = q(0.5);
    const iqr = (q(0.75) - q(0.25)) || Math.abs(med) || 1;
    const clipLo = med - 3 * iqr, clipHi = med + 3 * iqr;
    const plot = nums.map((n) => (Number.isFinite(n) ? Math.min(clipHi, Math.max(clipLo, n)) : NaN));
    const clipped = nums.map((n) => Number.isFinite(n) && (n > clipHi || n < clipLo));
    const pv = plot.filter((n) => Number.isFinite(n));
    let min = Math.min(...pv);
    let max = Math.max(...pv);
    const hasNeg = Math.min(...valid) < 0;
    if (hasNeg) { min = Math.min(min, 0); max = Math.max(max, 0); }
    const range = max - min || 1;
    const w = 54, h = 15;
    const step = w / (nums.length - 1);
    const xy = plot.map((n, i) => (Number.isFinite(n) ? { x: i * step, y: h - ((n - min) / range) * h, clip: clipped[i] } : null));
    const pts = xy.filter(Boolean) as { x: number; y: number; clip: boolean }[];
    const points = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const clipMarks = pts.filter((p) => p.clip).map((p) => ({ x: p.x.toFixed(1), y: p.y.toFixed(1) }));
    const lastP = [...xy].reverse().find(Boolean) as { x: number; y: number } | undefined;
    const zeroY = min < 0 && max > 0 ? (h - ((0 - min) / range) * h).toFixed(1) : null;
    const first = valid[0];
    const lastV = valid[valid.length - 1];
    const tone = hasNeg ? 'flat' : lastV > first * 1.001 ? 'up' : lastV < first * 0.999 ? 'down' : 'flat';
    return { points, tone, zeroY, clipMarks, lastX: (lastP?.x ?? 0).toFixed(1), lastY: (lastP?.y ?? 0).toFixed(1) };
  }

  function isTimeSeries(cols: string[]): boolean {
    return cols.length >= 4 && /^\d{4}$/.test(cols[1] ?? '');
  }

  function splitTitle(t: string): { head: string; sub: string } {
    const s = String(t ?? '');
    const m = s.split(/\s*(?:--|—|·)\s*/);
    if (m.length >= 2) return { head: m[0].trim(), sub: m.slice(1).join(' · ').trim() };
    return { head: s.trim(), sub: '' };
  }

  function printReport() {
    if (status !== 'ready' || !model || model.pending) return;
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

  const skel = [0, 1, 2, 3];
</script>

<svelte:head>
  <title>기업분석보고서 · {model?.corpName ?? data.sym} | dartlab (dev)</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<div class="rptRoot" class:dark={theme === 'dark'}>
  <nav class="toolbar">
    <span class="devtag">DEV /lab/report · 리얼타임</span>
    {#each samples as s}
      <a class="devlink" class:on={data.sym === s.code} href={`/lab/report?sym=${s.code}&view=${perspectiveKey}`}>{s.name}</a>
    {/each}
    <span class="spacer"></span>
    <button class="themeBtn" onclick={toggleTheme} title="화이트/다크 전환">
      {theme === 'light' ? '🌙 다크' : '☀ 화이트'}
    </button>
    <button class="printBtn" onclick={printReport} disabled={status !== 'ready' || !!model?.pending}>🖨 인쇄 / PDF</button>
  </nav>

  <div class="reportLayout">
    <!-- ── 관점 레일 (화면 전용) ── -->
    <aside class="rail">
      <div class="railHead">관점</div>
      {#each PERSPECTIVES as p}
        <button class="railItem" class:on={p.key === perspectiveKey} class:pending={!p.built}
          onclick={() => selectPerspective(p.key)} title={p.question}>
          <span class="rLabel">{p.label}</span>
          {#if !p.built}<span class="rMeta">준비 중</span>{/if}
        </button>
      {/each}
      <div class="railNote">관점 = 같은 회사를 다른 렌즈로. 숫자는 동일 데이터, 데이터 작업대에서 <b>리얼타임</b> 계산.</div>
    </aside>

    <div class="main">
      {#if status === 'loading'}
        <!-- ── 스켈레톤 (CLS 0, 구조 윤곽) ── -->
        <article class="sheet">
          <div class="sk skCover"></div>
          <div class="sk skBand"></div>
          <div class="skGrid">{#each skel as _}<div class="sk skKpi"></div>{/each}</div>
          {#each skel as _}<div class="sk skSec"></div>{/each}
        </article>
      {:else if status === 'error'}
        <article class="sheet skip">
          <h1>보고서를 불러오지 못했습니다</h1>
          <p class="skipReason">{skipReason}</p>
          <button class="retryBtn" onclick={() => (perspectiveKey = perspectiveKey)}>다시 시도</button>
        </article>
      {:else if status === 'skipped'}
        <article class="sheet skip">
          <h1>데이터 부족 — 보고서 미생성</h1>
          <p class="skipReason">종목 {data.sym}: {skipReason}</p>
          <p class="muted">약한 발행보다 정직한 스킵 — dartlab 은 데이터가 빈약한 회사의 보고서를 만들지 않습니다.</p>
        </article>
      {:else if model?.pending}
        <article class="sheet pending">
          <header class="cover">
            <div class="coverKicker">기업분석보고서 <span class="kSep">·</span> {model.perspectiveLabel}</div>
            <h1 class="coverTitle">{model.corpName}<span class="code">{model.stockCode}</span></h1>
          </header>
          <div class="pendingNote">
            <p class="pendBig">「{model.perspectiveLabel}」 관점은 다음 사이클에서 리얼타임으로 구현됩니다.</p>
            <p class="muted">현재 사이클 = <b>수익체력</b> 관점. 매 사이클마다 전문 애널리스트·UI/UX 전문가 토론 → 개발 → 감수를 거쳐 관점을 하나씩 완성합니다.</p>
          </div>
        </article>
      {:else if model}
        {@const allAnalysis = model.sections.every((s) => s.sourceEngine === 'analysis')}
        <article class="sheet">
          <!-- ── 표지 ── -->
          <header class="cover">
            <div class="coverKicker">기업분석보고서 <span class="kSep">·</span> {model.perspectiveLabel}</div>
            <h1 class="coverTitle">{model.corpName}<span class="code">{model.stockCode}</span></h1>
            <dl class="coverFacts">
              {#if model.industry}<div class="fact"><dt>업종</dt><dd>{model.industry}</dd></div>{/if}
              <div class="fact"><dt>데이터 기준</dt><dd>{model.dataBasis}</dd></div>
              <div class="fact"><dt>최근 접수</dt><dd>{model.asOf}</dd></div>
              <div class="fact"><dt>분석범위</dt><dd>{model.sections.length}개 섹션 · 최대 6개년</dd></div>
              <div class="fact"><dt>작성</dt><dd>dartlab 분석엔진 · 리얼타임</dd></div>
            </dl>
            {#if model.narrativeOverview}<p class="coverIntro">{clean(model.narrativeOverview)}</p>{/if}
          </header>

          <div class="printPerspective">관점: {model.perspectiveLabel} — {PERSPECTIVES.find((p) => p.key === model!.perspectiveKey)?.question}</div>

          {#if model.focusQuestions.length}
            <div class="focusRow">{#each model.focusQuestions as q}<span class="chip focus">{q}</span>{/each}</div>
          {/if}

          <!-- ── 핵심 요약 ── -->
          <section class="block summary">
            <h2 class="blockTitle">핵심 요약</h2>
            <div class="conclusion">{clean(model.conclusion)}</div>
            {#if model.headlineKpis.length}
              <div class="kpiBand">
                {#each model.headlineKpis as k}<div class="kpi"><span class="kLabel">{k.label}</span><span class="kVal {cellTone(k.value)}">{k.value}</span></div>{/each}
              </div>
            {/if}
          </section>

          {#if model.keyFindings.length}
            <section class="block keyFindings">
              <h2 class="blockTitle">핵심 발견 <span class="subNote">엔진 측정값 자동 추출{#if allAnalysis} · 출처 {engineLabel.analysis}{/if}</span></h2>
              {#each model.keyFindings as kf}
                <div class="kfRow" class:noSrc={allAnalysis}>
                  <span class="chip kfTag">{kf.key}</span>
                  <span class="kfText">{clean(kf.finding)}</span>
                  {#if !allAnalysis}<span class="kfSrc">{engineLabel[kf.sourceEngine] ?? kf.sourceEngine}</span>{/if}
                </div>
              {/each}
            </section>
          {/if}

          <!-- ── 목차 ── -->
          {#if model.sections.length > 1}
            <nav class="toc">
              <span class="tocLabel">목차</span>
              {#each model.sections as sec, i (sec.key)}
                <button class="tocItem" onclick={() => scrollSec(sec.key)}>
                  <span class="tocNo">{String(i + 1).padStart(2, '0')}</span>{splitTitle(sec.title).head}
                </button>
              {/each}
            </nav>
          {/if}

          <!-- ── 본문 섹션 ── -->
          <div class="sections">
            {#each model.sections as sec, i (sec.key)}
              {@const t = splitTitle(sec.title)}
              <section class="rptSection src-{sec.sourceEngine}" class:emph={sec.emph} id={`sec-${sec.key}`}>
                <div class="secHead">
                  <span class="secNo">{String(i + 1).padStart(2, '0')}</span>
                  <div class="secTitleWrap">
                    <h2 class="secTitle">{t.head}</h2>
                    {#if t.sub}<div class="secSub">{t.sub}</div>{/if}
                  </div>
                  {#if !allAnalysis}<span class="chip srcBadge src-{sec.sourceEngine}">{engineLabel[sec.sourceEngine] ?? sec.sourceEngine}</span>{/if}
                </div>
                {#each sec.blocks as b}
                  {#if b.type === 'heading'}
                    <h3 class="bHeading">{b.title}</h3>
                  {:else if b.type === 'text'}
                    <p class="bText">{clean(b.text)}</p>
                  {:else if b.type === 'metrics'}
                    <div class="bMetrics">{#each b.metrics as m}<div class="metric"><span class="mLabel">{m.label}</span><span class="mValue {cellTone(m.value)}">{m.value}</span></div>{/each}</div>
                  {:else if b.type === 'table' && b.data?.length}
                    {@const cols = Object.keys(b.data[0])}
                    {@const ts = isTimeSeries(cols)}
                    <div class="bTableWrap">
                      {#if b.label}<div class="tCap">{b.label}</div>{/if}
                      <table class="bTable">
                        <thead><tr>{#each cols as c, ci}<th class={ci === 0 ? 'lbl' : c === '판정' ? 'verdict-h' : TXT_COLS.has(c) ? 'txt-h' : 'num'}>{c}</th>{/each}{#if ts}<th class="sparkCol">추이</th>{/if}</tr></thead>
                        <tbody>
                          {#each b.data as row}
                            <tr>
                              {#each cols as c, ci}{#if ci === 0}<td class="lbl">{row[c]}</td>{:else if c === '판정'}{@const vt = verdictTone(row[c])}<td class="verdict {vt}">{#if vt === 'ok'}<span class="vMark ok">●</span>{:else if vt === 'warn'}<span class="vMark warn">▲</span>{/if}{row[c]}</td>{:else if TXT_COLS.has(c)}<td class="txt {c === '기준' ? 'threshold' : ''}">{row[c]}</td>{:else}<td class="num {cellTone(row[c])}">{row[c]}</td>{/if}{/each}
                              {#if ts}{@const sp = spark(row, cols.slice(1))}<td class="sparkCol">{#if sp}<svg class="spark {sp.tone}" width="54" height="15" viewBox="0 0 54 15">{#if sp.zeroY}<line x1="0" y1={sp.zeroY} x2="54" y2={sp.zeroY} stroke="var(--dim)" stroke-width="0.5" stroke-dasharray="2 2" opacity="0.55" />{/if}<polyline points={sp.points} fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round" />{#each sp.clipMarks as cm}<circle cx={cm.x} cy={cm.y} r="1.7" fill="none" stroke="currentColor" stroke-width="0.8" />{/each}<circle cx={sp.lastX} cy={sp.lastY} r="1.5" fill="currentColor" /></svg>{/if}</td>{/if}
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

          <!-- ── 종합 의견 ── -->
          {#if model.closing.length}
            <section class="block closing">
              <h2 class="blockTitle">종합 의견 <span class="subNote">{model.perspectiveLabel} 관점 요약 (투자판단 아님)</span></h2>
              {#each model.closing as cl}
                <div class="clRow src-{cl.engine}">
                  <span class="clLabel">{cl.label}</span>
                  <span class="clLine">{clean(cl.line)}</span>
                  <span class="clSrc">{engineLabel[cl.engine] ?? cl.engine}</span>
                </div>
              {/each}
            </section>
          {/if}

          <!-- ── 근거·출처 ── -->
          <section class="block evidenceStrip">
            <h2 class="blockTitle">근거·출처 <span class="subNote">이 보고서를 계산한 dartlab 엔진 (조회 시점 리얼타임)</span></h2>
            <div class="evEngines">
              {#each Object.entries(model.provenance.engines) as [eng, info]}
                <div class="evEngine"><span class="evDot"></span><span class="evLabel">{info.label ?? engineLabel[eng] ?? eng}</span><span class="evMeta">{info.sections}섹션 · {info.blocks}블록</span></div>
              {/each}
            </div>
            <div class="evNote">{model.provenance.note}</div>
          </section>

          <!-- ── 푸터 / 서명 ── -->
          <footer class="rptFooter">
            {#if model.assumptionsNote}<div class="assump">가정·한계 — {model.assumptionsNote}</div>{/if}
            <div class="footSign">
              <span class="signMain">{model.corpName} 기업분석보고서</span>
              <span class="dot">·</span><span>{model.perspectiveLabel} 관점</span>
              <span class="dot">·</span><span>데이터 기준 {model.asOf}</span>
              <span class="dot">·</span><span>작성 dartlab 분석엔진 (리얼타임)</span>
            </div>
            <div class="footLine">
              모든 수치 = dartlab 엔진({Object.values(model.provenance.engines).map((e) => e.label).join('·')}) 조회 시점 산출
              <span class="dot">·</span> sourceEngine = 계산 엔진(원천 DART 공시 줄 아님)
              <span class="dot">·</span> 본 보고서는 투자 권유가 아니며, 투자 판단의 책임은 이용자에게 있습니다.
            </div>
          </footer>
        </article>
      {/if}
    </div>
  </div>
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
  .rptRoot.dark {
    --backdrop: #0a0c10; --sheet: #161b24; --ink: #e8eef5; --dim: #8b949e;
    --bd: rgba(255, 255, 255, 0.10); --bd2: rgba(255, 255, 255, 0.18); --soft: #222a36;
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
  .printBtn:disabled { opacity: 0.45; cursor: not-allowed; }

  /* ── 레이아웃: 관점 레일 + 본문 ── */
  .reportLayout { display: grid; grid-template-columns: 186px minmax(0, 1fr); }
  .rail { position: sticky; top: 41px; align-self: start; max-height: calc(100vh - 41px); overflow-y: auto; padding: 20px 12px 16px; border-right: 1px solid var(--bd2); }
  .railHead { font-size: 11px; font-weight: 800; color: var(--dim); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 12px; padding-left: 10px; }
  .railItem { display: flex; justify-content: flex-start; align-items: baseline; gap: 7px; width: 100%; padding: 9px 11px; border-radius: 8px; border: 1px solid transparent; background: transparent; color: var(--dim); font-size: 13.5px; cursor: pointer; text-align: left; font-family: var(--sans); margin-bottom: 2px; transition: all 0.12s; }
  .railItem .rLabel { font-weight: 600; }
  .railItem .rMeta { font-size: 9px; font-family: var(--mono); color: var(--dim); white-space: nowrap; border: 1px dashed var(--bd2); border-radius: 3px; padding: 0 4px; }
  .railItem.on { background: var(--emph); color: #fff; }
  .railItem.on .rLabel { font-weight: 800; }
  .railItem:hover:not(.on) { color: var(--ink); background: var(--soft); }
  .railItem.pending { cursor: default; }
  .railItem.pending:not(.on) { opacity: 0.5; }
  .railNote { font-size: 10.5px; color: var(--dim); line-height: 1.6; margin-top: 14px; padding: 12px 10px 0; border-top: 1px solid var(--bd); }
  .railNote b { color: var(--accent); }
  .main { min-width: 0; }

  /* ── A4 용지 ── */
  .sheet {
    width: 820px; max-width: calc(100vw - 260px); margin: 28px auto 60px; padding: 52px 56px 44px;
    background: var(--sheet); border: 1px solid var(--bd); border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 12px 40px rgba(0, 0, 0, 0.10);
  }
  .skip, .pending { text-align: center; padding-top: 70px; padding-bottom: 70px; }
  .skip h1 { font-size: 22px; } .skipReason { font-family: var(--mono); color: var(--warn); }
  .retryBtn { margin-top: 16px; background: var(--accent); color: #fff; border: 0; padding: 7px 16px; border-radius: 7px; cursor: pointer; font-weight: 700; }
  .pending { text-align: left; }
  .pendingNote { text-align: center; padding: 40px 0; }
  .pendBig { font-size: 17px; font-weight: 700; margin-bottom: 12px; }

  /* ── 스켈레톤 ── */
  .sk { background: linear-gradient(90deg, var(--soft) 25%, color-mix(in srgb, var(--soft) 55%, var(--bd2)) 37%, var(--soft) 63%); background-size: 400% 100%; animation: skim 1.4s ease infinite; border-radius: 6px; }
  @keyframes skim { 0% { background-position: 100% 0; } 100% { background-position: 0 0; } }
  .skCover { height: 90px; margin-bottom: 18px; } .skBand { height: 22px; width: 60%; margin-bottom: 22px; }
  .skGrid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 9px; margin-bottom: 28px; } .skKpi { height: 64px; }
  .skSec { height: 120px; margin-bottom: 20px; }
  @media (prefers-reduced-motion: reduce) { .sk { animation: none; opacity: 0.6; } }

  /* ── 표지 ── */
  .cover { border-bottom: 2px solid var(--ink); padding: 8px 0 22px; margin-bottom: 26px; }
  .coverKicker { font-size: 12px; font-weight: 700; color: var(--accent); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 12px; }
  .coverKicker .kSep { opacity: 0.4; margin: 0 4px; }
  .coverTitle { font-size: 36px; font-weight: 800; letter-spacing: -0.025em; margin: 0 0 18px; line-height: 1.1; }
  .coverTitle .code { font-family: var(--mono); font-size: 16px; color: var(--dim); font-weight: 500; margin-left: 11px; letter-spacing: 0; }
  .coverFacts { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 0; margin: 0; border-top: 1px solid var(--bd2); }
  .coverFacts .fact { display: flex; flex-direction: column; gap: 3px; padding: 9px 14px 9px 0; border-right: 1px solid var(--bd); }
  .coverFacts .fact:last-child { border-right: 0; }
  .coverFacts dt { font-size: 10px; color: var(--dim); letter-spacing: 0.05em; text-transform: uppercase; }
  .coverFacts dd { font-size: 13px; font-weight: 600; margin: 0; font-variant-numeric: tabular-nums; }
  .coverIntro { font-size: 13px; line-height: 1.75; color: var(--dim); margin: 18px 0 0; max-width: 70ch; }

  /* ── 칩 ── */
  .chip { font-size: 11.5px; border-radius: 6px; padding: 3px 9px; border: 1px solid var(--bd2); color: var(--ink); white-space: nowrap; }
  .chip.focus { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 34%, transparent); background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 13px; }

  .focusRow { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 18px; }
  .printPerspective { display: none; }

  /* ── 공통 블록 ── */
  .block { margin-bottom: 26px; }
  .blockTitle { font-size: 13px; font-weight: 800; letter-spacing: 0.02em; margin: 0 0 12px; padding-bottom: 7px; border-bottom: 1px solid var(--bd2); display: flex; align-items: baseline; gap: 8px; }
  .blockTitle .subNote { font-size: 10.5px; font-weight: 400; color: var(--dim); }

  /* ── 핵심 요약 ── */
  .conclusion { font-size: 19px; font-weight: 700; margin-bottom: 14px; letter-spacing: -0.01em; line-height: 1.45; }
  .kpiBand { display: grid; grid-template-columns: repeat(6, 1fr); gap: 9px; margin: 4px 0 4px; }
  .kpi { background: var(--soft); border: 1px solid var(--bd); border-radius: 8px; padding: 10px 13px; display: flex; flex-direction: column; justify-content: flex-start; gap: 4px; min-height: 64px; }
  .kLabel { font-size: 11px; color: var(--dim); font-weight: 500; min-height: 2.4em; line-height: 1.25; }
  .kVal { font-size: clamp(15px, 1.45vw, 18px); font-weight: 800; font-family: var(--mono); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; margin-top: auto; }
  .kVal.neg { color: var(--down); } .kVal.pos { color: var(--up); }

  /* ── 핵심 발견 ── */
  .kfRow { display: grid; grid-template-columns: max-content 1fr auto; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--bd); align-items: baseline; }
  .kfRow.noSrc { grid-template-columns: max-content 1fr; }
  .chip.kfTag { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 28%, transparent); font-weight: 600; padding: 1px 8px; font-size: 11px; justify-self: start; }
  .kfText { font-size: 12.5px; line-height: 1.55; }
  .kfSrc { font-size: 10.5px; color: var(--dim); }

  /* ── 목차 ── */
  .toc { display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; margin: 0 0 30px; padding: 14px 16px; background: var(--soft); border: 1px solid var(--bd); border-radius: 10px; }
  .tocLabel { font-size: 11px; color: var(--dim); font-weight: 800; margin-right: 6px; letter-spacing: 0.06em; }
  .tocItem { background: transparent; border: 0; color: var(--ink); font-size: 12.5px; cursor: pointer; padding: 3px 9px; border-radius: 6px; display: inline-flex; align-items: baseline; gap: 6px; font-family: var(--sans); }
  .tocItem:hover { color: var(--accent); background: color-mix(in srgb, var(--accent) 9%, transparent); }
  .tocNo { font-family: var(--mono); font-size: 10.5px; color: var(--accent); font-weight: 700; }

  /* ── 본문 섹션 ── */
  .sections { counter-reset: sec; }
  .rptSection { margin-bottom: 30px; padding: 0; scroll-margin-top: 56px; }
  .secHead { display: flex; align-items: baseline; gap: 12px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 2px solid var(--ink); }
  .secNo { font-family: var(--mono); font-size: 15px; font-weight: 800; color: var(--accent); letter-spacing: -0.02em; }
  .rptSection.src-credit .secNo { color: var(--e-credit); }
  .rptSection.src-quant .secNo { color: var(--e-quant); }
  .rptSection.src-industry .secNo { color: var(--e-industry); }
  .secTitleWrap { flex: 1; }
  .secTitle { font-size: 19px; font-weight: 800; margin: 0; letter-spacing: -0.015em; }
  .secSub { font-size: 12px; color: var(--dim); margin-top: 3px; font-weight: 500; }
  .rptRoot.dark .cover { border-bottom-width: 1px; border-bottom-color: var(--bd2); }
  .rptRoot.dark .secHead { border-bottom-width: 1px; border-bottom-color: var(--bd2); }
  .rptRoot.dark .rptFooter { border-top-width: 1px; border-top-color: var(--bd2); }
  /* 다크 표 가독성 — 행 구분선·zebra·헤더 대비 강화 (감수 P4) */
  .rptRoot.dark .bTable td { border-bottom-color: rgba(255, 255, 255, 0.07); }
  .rptRoot.dark .bTable th { border-bottom-color: rgba(255, 255, 255, 0.28); }
  .rptRoot.dark .bTable tbody tr:nth-child(even) { background: #1d2531; }
  .rptRoot.dark .kpi, .rptRoot.dark .metric { border-color: rgba(255, 255, 255, 0.14); }
  .chip.srcBadge { font-size: 10.5px; padding: 2px 8px; color: var(--dim); align-self: center; }
  .chip.srcBadge.src-analysis { color: var(--e-analysis); border-color: color-mix(in srgb, var(--e-analysis) 30%, transparent); }
  .rptSection.emph .secTitle::after { content: '핵심'; font-size: 10px; font-weight: 700; color: var(--emph); border: 1px solid var(--emph); border-radius: 4px; padding: 1px 5px; margin-left: 9px; vertical-align: middle; }

  .bHeading { font-size: 13px; font-weight: 700; margin: 16px 0 7px; color: var(--ink); }
  .bText { font-size: 12.5px; line-height: 1.78; margin: 7px 0; }

  .bMetrics { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px; margin: 10px 0; }
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
  /* 비숫자 의미 컬럼 — 좌측 sans (시계열표 흉내 방지) */
  .bTable td.txt, .bTable th.txt-h { text-align: left; font-family: var(--sans); color: var(--ink); font-weight: 400; }
  .bTable td.txt.threshold { color: var(--dim); font-size: 11px; }
  /* 판정 — 신호색(양호=녹·주의=황갈·산출불가=중립). 적색은 음수 SSOT라 주의에 안 씀 */
  .bTable td.verdict, .bTable th.verdict-h { text-align: center; font-family: var(--sans); font-weight: 700; white-space: nowrap; }
  .bTable td.verdict.ok { color: var(--up); }
  .bTable td.verdict.warn { color: var(--warn); }
  .vMark { font-size: 8px; margin-right: 4px; vertical-align: 1px; }
  .vMark.ok { color: var(--up); } .vMark.warn { color: var(--warn); }
  .bTable tbody tr:nth-child(even) { background: var(--soft); }
  .bTable td.sparkCol { text-align: right; padding-right: 4px; width: 58px; }
  .spark { vertical-align: middle; color: var(--dim); }
  .spark.up { color: var(--up); } .spark.down { color: var(--down); } .spark.flat { color: var(--dim); }

  .bFlags { padding-left: 18px; margin: 9px 0; font-size: 12.5px; line-height: 1.7; }
  .bFlags.warning li { color: var(--warn); } .bFlags.opportunity li { color: var(--up); }

  /* ── 종합 의견 ── */
  .clRow { display: grid; grid-template-columns: 54px 1fr auto; gap: 13px; align-items: baseline; padding: 10px 0 10px 13px; border-bottom: 1px solid var(--bd); border-left: 3px solid var(--e-analysis); }
  .clRow.src-credit { border-left-color: var(--e-credit); }
  .clRow.src-industry { border-left-color: var(--e-industry); }
  .clRow.src-quant { border-left-color: var(--e-quant); }
  .clRow:last-child { border-bottom: 0; }
  .clLabel { font-size: 13px; font-weight: 800; letter-spacing: 0.02em; }
  .clLine { font-size: 13px; line-height: 1.55; }
  .clSrc { font-size: 10.5px; color: var(--dim); white-space: nowrap; }

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

  /* ── 반응형 ── */
  @media (max-width: 980px) {
    .reportLayout { grid-template-columns: 1fr; }
    .rail { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--bd2); display: flex; flex-wrap: wrap; gap: 6px; padding: 12px; }
    .railHead, .railNote { width: 100%; }
    .railItem { width: auto; }
    .sheet { max-width: calc(100vw - 32px); }
  }

  /* ── 인쇄 — A4, 화이트 강제 ── */
  @media print {
    .rptRoot, .rptRoot.dark {
      --backdrop: #fff; --sheet: #fff; --soft: #eef2f6; --ink: #161616; --dim: #555a60;
      --bd: #d8dde3; --bd2: #b9c1c9;
      --accent: #0550ae; --up: #1a7f37; --down: #b02a1a; --warn: #8a6100; --emph: #0550ae;
      --e-analysis: #0550ae; --e-credit: #b02a1a; --e-quant: #0a7d86; --e-industry: #1a7f37; --e-macro: #8a6100; --e-story: #6f42c1;
      background: #fff; font-size: 10.2pt;
      print-color-adjust: exact; -webkit-print-color-adjust: exact;
    }
    .toolbar, .rail, .toc { display: none !important; }
    .reportLayout { display: block; }
    .printPerspective { display: block; font-size: 11px; color: #555; margin-bottom: 12px; font-weight: 600; }
    .sheet { width: 100%; max-width: 100%; margin: 0; padding: 0; border: 0; box-shadow: none; border-radius: 0; }
    .rptSection, .summary, .keyFindings, .evidenceStrip, .kpiBand, .clRow { break-inside: avoid; }
    .cover, .coverFacts, .focusRow { break-inside: avoid; }
    .cover { break-after: avoid; }
    .bTableWrap { break-inside: avoid; }
    .bTable thead { display: table-header-group; }
    .secHead { break-after: avoid; }
    .spark { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    .kpi { background: #eef2f6 !important; }
    .bTable th { border-bottom-color: #161616; }
    .bTable tbody tr:nth-child(even) { background: #eaeff4 !important; }
    .spark polyline { stroke-width: 2px; }
    .spark.flat { color: #5b6470; }
    .chip.focus { background: none; }
    @page { size: A4; margin: 14mm 13mm; }
  }
</style>
