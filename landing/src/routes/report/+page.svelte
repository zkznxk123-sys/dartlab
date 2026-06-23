<script lang="ts">
  import type { PageData } from './$types';
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import { setStaticBase, loadJson } from '@dartlab/ui-runtime/data/dartlabData';
  import type { IndexRow } from '@dartlab/ui-contracts';
  import { getPublicRuntime } from '$lib/runtime/publicRuntime';
  // 헤더 = 터미널 top bar 디자인 그대로 재사용(.dlTerm 스코프 + 터미널 클래스). 색·아이콘·SNS 동일 SSOT.
  import '@dartlab/ui-surfaces/terminal/terminal.css';
  import { DARTLAB_BRAND_LINKS, SupportDialog, fetchGithubStars, fmtStars } from '@dartlab/ui-surfaces/terminal';
  import { buildReport, buildOverview } from '$lib/report/build';
  import { isSkipped, type ReportModel, type OverviewModel } from '$lib/report/model';
  import { PERSPECTIVES, findPerspective } from '$lib/report/perspectives';
  // 순수 렌더 헬퍼 — /cards 와 공유(인라인에서 추출, 기계적 동치). $lib/report/render SSOT.
  import {
    clean,
    engineLabel,
    cellTone,
    verdictTone,
    TXT_COLS,
    spark,
    isTimeSeries,
    chunk,
    tableHasSpark,
    lineGeo,
    wonLabel,
    splitTitle
  } from '$lib/report/render';

  let { data }: { data: PageData } = $props();

  // 정적 씨데이터 base 주입 (loadJson SSOT) — search-index.json 등 데이터 작업대 직독 경로 정합.
  setStaticBase(base);
  const rt = getPublicRuntime();
  // SNS·후원 링크 = dartlab 공통 SSOT(터미널 상단과 동일 정본).
  const links = DARTLAB_BRAND_LINKS;
  // GitHub 스타 라이브 배지 — 터미널 SNS 와 동일(fetchGithubStars 재사용). null=미조회/실패(배지 숨김).
  let ghStars = $state<number | null>(null);
  fetchGithubStars(links.repo).then((n) => (ghStars = n));

  // 화이트/다크 — A4 용지 위 두 모드. 기본 = 화이트(진짜 보고서). 헤더 크롬은 항상 다크 에디토리얼.
  let theme = $state<'light' | 'dark'>('light');
  function toggleTheme() {
    theme = theme === 'light' ? 'dark' : 'light';
  }

  // 관점 — 같은 회사를 5개 렌즈로. 데이터 작업대 리얼타임. URL view= 로 초기 관점 동기화. 헤더 탭으로 전환.
  let perspectiveKey = $state<string>('earningsPower');
  $effect(() => {
    if (data.perspective) perspectiveKey = data.perspective;
  });
  // 표지 제목 옆 ! 툴팁(활성 관점 한정) — 클릭=토글, 다음 클릭/관점전환=닫힘. 관점 메타는 렌더에서 findPerspective.
  let perspTipOpen = $state(false);
  $effect(() => {
    if (!perspTipOpen) return;
    const close = () => (perspTipOpen = false);
    const id = setTimeout(() => document.addEventListener('click', close, { once: true }), 0);
    return () => { clearTimeout(id); document.removeEventListener('click', close); };
  });

  // ── 종목 검색 (공통 작업대 SSOT — loadJson, raw fetch·자체 캐시 금지) ──
  // 회사명·코드 유니버스 = map/search-index.json (buildReport 와 동일 직독 경로, 추가 다운로드 0).
  let universe = $state<IndexRow[]>([]);
  loadJson<IndexRow[]>('map/search-index.json', { fetchFn: fetch, preferLocal: true })
    .then((rows) => { universe = rows ?? []; })
    .catch(() => {});
  let query = $state('');
  let showSuggest = $state(false);
  let selIdx = $state(-1);
  let cmdInput = $state<HTMLInputElement | null>(null);
  // ⌘K / `/` 종목검색 포커스 — 터미널 cmdBar 와 동일 거동.
  $effect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      const inInput = tag === 'INPUT' || tag === 'TEXTAREA';
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); cmdInput?.focus(); }
      else if (e.key === '/' && !inInput) { e.preventDefault(); cmdInput?.focus(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
  const suggestions = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [] as IndexRow[];
    const out: IndexRow[] = [];
    for (const r of universe) {
      if ((r.corpName && r.corpName.toLowerCase().includes(q)) || (r.stockCode && r.stockCode.includes(q))) out.push(r);
      if (out.length >= 8) break;
    }
    return out;
  });
  function selectCompany(code: string) {
    query = '';
    showSuggest = false;
    selIdx = -1;
    // URL 갱신 → loader 재실행(ssr=false 클라이언트) → data.sym 변경 → 빌드 effect 재조립. 공유 가능 딥링크.
    void goto(`${base}/report?sym=${code}&view=${perspectiveKey}`);
  }
  function onSearchInput() {
    showSuggest = query.trim().length > 0;
    selIdx = -1;
  }
  function onSearchKey(e: KeyboardEvent) {
    if (!suggestions.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); selIdx = (selIdx + 1) % suggestions.length; }
    else if (e.key === 'ArrowUp') { e.preventDefault(); selIdx = (selIdx - 1 + suggestions.length) % suggestions.length; }
    else if (e.key === 'Escape') { showSuggest = false; selIdx = -1; }
    else if (e.key === 'Enter' && selIdx >= 0) { e.preventDefault(); selectCompany(suggestions[selIdx].stockCode); }
  }
  function onSearchSubmit(e: Event) {
    e.preventDefault();
    if (selIdx >= 0 && suggestions[selIdx]) selectCompany(suggestions[selIdx].stockCode);
    else if (suggestions[0]) selectCompany(suggestions[0].stockCode);
  }

  // 후원·기여 — 터미널 상단과 동일 SupportDialog(♥).
  let supportOpen = $state(false);

  // ── 빌드 — 종목 1개당 5관점 전부 조립(종목 변경 시 동시성 토큰 가드). 화면은 활성 관점만, 인쇄는 전부
  //    이어붙인다(탭은 인쇄 못 하므로 연속 문서). 관점 전환은 재빌드 없이 즉시(이미 빌드된 models 에서 선택). ──
  let models = $state<ReportModel[]>([]);
  let status = $state<'loading' | 'ready' | 'skipped' | 'error'>('loading');
  let skipReason = $state<string>('');
  let buildTok = 0;
  $effect(() => {
    const code = data.sym;
    const tk = ++buildTok;
    status = 'loading';
    models = [];
    skipReason = '';
    Promise.all(PERSPECTIVES.filter((p) => p.built).map((p) => buildReport(rt, code, p.key).catch(() => null)))
      .then((res) => {
        if (tk !== buildTok) return;
        const built = res.filter((r): r is ReportModel => !!r && !isSkipped(r));
        if (!built.length) {
          const firstSkip = res.find((r) => r && isSkipped(r));
          status = 'skipped';
          skipReason = firstSkip && isSkipped(firstSkip) ? firstSkip.reason : '재무 데이터가 없습니다(미상장·미공시).';
        } else {
          models = built; // PERSPECTIVES 순서 보존(Promise.all 순서 → filter 안정)
          status = 'ready';
        }
      })
      .catch((e) => {
        if (tk !== buildTok) return;
        status = 'error';
        skipReason = String(e?.message ?? e);
      });
  });
  // 활성 관점(헤더 탭·검색 view·표지 등) — 빌드된 models 에서 선택. 없으면 첫 관점.
  const model = $derived(models.find((m) => m.perspectiveKey === perspectiveKey) ?? models[0] ?? null);

  // 화면 = 활성 관점 1개만 렌더(빌드된 models 에서 선택). 인쇄/PDF 기능은 제거(헤디드 Chrome 빈 페이지 문제로 폐기).
  const renderModels = $derived(model ? [model] : []);

  function selectPerspective(key: string) {
    perspectiveKey = key;
    perspTipOpen = false;
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── 5관점 통합 리드 — 종목당 1회 빌드(관점과 독립). 5관점을 교차한 thesis. ──
  let overview = $state<OverviewModel | null>(null);
  let ovTok = 0;
  $effect(() => {
    const code = data.sym;
    const tk = ++ovTok;
    overview = null;
    buildOverview(rt, code)
      .then((o) => { if (tk === ovTok) overview = o; })
      .catch(() => {});
  });

  // ── 렌더 헬퍼: clean/cellTone/verdictTone/spark/lineGeo/splitTitle 등은 $lib/report/render 로 추출(상단 import).
  //    /cards 와 공유하는 순수 기하/포맷 SSOT. window/document 쓰는 scrollSec/selectPerspective 만 아래 잔존. ──

  function scrollSec(key: string) {
    document.getElementById(`sec-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const skel = [0, 1, 2, 3];
</script>

<svelte:head>
  <title>기업분석보고서 · {model?.corpName ?? data.sym} | dartlab</title>
  <meta
    name="description"
    content={`${model?.corpName ?? '상장사'} 기업분석보고서 — 수익성·재무안정성·주주환원·시장평가·지배구조 5관점.`}
  />
</svelte:head>

<div class="rptRoot" class:dark={theme === 'dark'}>
  <!-- ── 헤더 = 터미널 top bar 디자인 그대로(.dlTerm 스코프 + terminal.css 재사용). 단일행: brand · 관점탭 · 종목검색 · 테마/인쇄 · SNS ── -->
  <header class="rptHeader dlTerm">
    <div class="topBar">
      <a class="brand" href="{base}/" title="DartLab 홈">
        <picture>
          <source srcset="{base}/avatar.webp" type="image/webp" />
          <img class="brandLogo" src="{base}/avatar.png" alt="DartLab" width="22" height="22" />
        </picture>
        <span class="brandName">DartLab</span>
        <span class="brandSlash">/</span>
        <span class="brandTag">report</span>
      </a>

      <form class="cmdBar" role="search" onsubmit={onSearchSubmit}>
        <span class="cmdPrompt">‹GO›</span>
        <input class="cmdInput" bind:this={cmdInput} bind:value={query} spellcheck={false}
          oninput={onSearchInput} onkeydown={onSearchKey} onfocus={onSearchInput}
          onblur={() => setTimeout(() => (showSuggest = false), 120)}
          placeholder="종목 검색" aria-label="종목 검색" />
        <kbd class="cmdKbd">⌘K</kbd>
        <button class="cmdGo" type="submit">GO</button>
        {#if showSuggest && suggestions.length}
          <div class="suggest">
            {#each suggestions as s, i (s.stockCode)}
              <button type="button" class={'suggestRow' + (i === selIdx ? ' on' : '')}
                onmousedown={() => selectCompany(s.stockCode)} onmouseenter={() => (selIdx = i)}>
                <span class="sgName">{s.corpName}</span>
                <span class="sgCode">{s.stockCode}</span>
                <span class="sgInd">{s.industry ?? ''}</span>
              </button>
            {/each}
          </div>
        {/if}
      </form>

      <div class="hdrLinks perspLinks">
        {#each PERSPECTIVES as p}
          <button class={'hdrLink' + (p.key === perspectiveKey ? ' on' : '')} disabled={!p.built}
            onclick={() => selectPerspective(p.key)} title={p.question}>{p.label}</button>
        {/each}
      </div>

      <div class="topRight">
        <button class="snsBtn" onclick={toggleTheme} title={theme === 'light' ? '다크 모드' : '화이트 모드'} aria-label="테마 전환">
          {#if theme === 'light'}
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
          {:else}
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
          {/if}
        </button>
        <nav class="sns" aria-label="dartlab 채널">
          <a class="snsBtn" href={links.repo} target="_blank" rel="noopener" title="GitHub" aria-label="GitHub">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" /><path d="M9 18c-4.51 2-5-2-7-2" /></svg>
          </a>
          {#if ghStars != null}
            <a class="ghStars" href={links.repo} target="_blank" rel="noopener" title="GitHub 스타로 응원"><span class="ghStar">★</span>{fmtStars(ghStars)}</a>
          {/if}
          <button class="snsBtn snsHeart" onclick={() => (supportOpen = true)} title="후원·기여" aria-label="후원·기여">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="rgba(251, 113, 133, 0.32)" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" /></svg>
          </button>
          <a class="snsBtn" href={links.youtube} target="_blank" rel="noopener" title="YouTube" aria-label="YouTube">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
          </a>
          <a class="snsBtn" href={links.threads} target="_blank" rel="noopener" title="Threads · @dartlab.ai" aria-label="Threads">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 0 1 3.02.142c-.126-.742-.375-1.332-.75-1.757-.513-.586-1.308-.883-2.359-.89h-.029c-.844 0-1.992.232-2.721 1.32L7.734 7.847c.98-1.454 2.568-2.256 4.478-2.256h.044c3.194.02 5.097 1.975 5.287 5.388.108.046.216.094.321.142 1.49.7 2.58 1.761 3.154 3.07.797 1.82.871 4.79-1.548 7.158-1.85 1.81-4.094 2.628-7.277 2.65Zm1.003-11.69c-.242 0-.487.007-.739.021-1.836.103-2.98.946-2.916 2.143.067 1.256 1.452 1.839 2.784 1.767 1.224-.065 2.818-.543 3.086-3.71a10.5 10.5 0 0 0-2.215-.221z"/></svg>
          </a>
          <a class="snsBtn" href={links.instagram} target="_blank" rel="noopener" title="Instagram · @dartlab.ai" aria-label="Instagram">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z"/></svg>
          </a>
        </nav>
      </div>
    </div>
  </header>

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
          <p class="pendBig">「{model.perspectiveLabel}」 관점은 다음 사이클에서 구현됩니다.</p>
          <p class="muted">현재 사이클 = <b>수익성</b> 관점. 관점을 하나씩 추가하고 있습니다.</p>
        </div>
      </article>
    {:else if models.length}
      {#each renderModels as m (m.perspectiveKey)}
      {@const mPersp = findPerspective(m.perspectiveKey)}
      {@const allAnalysis = m.sections.every((s) => s.sourceEngine === 'analysis')}
      <article class="sheet perspSheet">
        <!-- ── 표지 (관점마다 표지로 시작 — 인쇄 시 관점별 섹션 구분) ── -->
        <header class="cover">
          <div class="coverKicker">기업분석보고서 <span class="kSep">·</span> {m.perspectiveLabel}{#if m.perspectiveKey === perspectiveKey}<span class="perspInfoWrap"><button class="perspInfo" onclick={(e) => { e.stopPropagation(); perspTipOpen = !perspTipOpen; }} aria-label="이 관점이 답하는 질문" title="관점 설명">!</button>{#if perspTipOpen}<span class="perspTip" role="tooltip"><b>{mPersp.label}</b> — {mPersp.question}{#if mPersp.focusQuestions.length}<span class="perspTipQs">{#each mPersp.focusQuestions as fq}<span>{fq}</span>{/each}</span>{/if}</span>{/if}</span>{/if}</div>
          <h1 class="coverTitle">{m.corpName}<span class="code">{m.stockCode}</span></h1>
          <dl class="coverFacts">
            {#if m.industry}<div class="fact"><dt>업종</dt><dd>{m.industry}</dd></div>{/if}
            <div class="fact"><dt>데이터 기준</dt><dd>{m.dataBasis}</dd></div>
            <div class="fact"><dt>최근 접수</dt><dd>{m.asOf}</dd></div>
            <div class="fact"><dt>분석범위</dt><dd>{m.sections.length}개 섹션 · 최대 6개년</dd></div>
            <div class="fact"><dt>작성</dt><dd>dartlab 분석엔진</dd></div>
          </dl>
          {#if m.narrativeOverview}<p class="coverIntro">{clean(m.narrativeOverview)}</p>{/if}
        </header>

        <!-- ── 5관점 요약 (표지 다음 = executive summary) ── -->
        {#if overview && overview.takes.length > 1}
          <section class="overviewLead">
            <div class="ovKicker">5관점 요약</div>
            <p class="ovThesis">{clean(overview.thesis)}</p>
            <ol class="ovTakes">
              {#each overview.takes as t}
                <li class:on={t.key === perspectiveKey}>
                  <button class="ovTake" onclick={() => selectPerspective(t.key)} title="이 관점 펼치기">
                    <span class="ovLabel src-{t.engine}">{t.label}</span><span class="ovLine">{clean(t.line)}</span>
                  </button>
                </li>
              {/each}
            </ol>
          </section>
        {/if}

        <div class="printPerspective">관점: {m.perspectiveLabel} — {mPersp.question}</div>

        <!-- ── 요약 (Executive Summary) — 산문 리드 + 요약 지표표 (카드 폐기, 문서형) ── -->
        <section class="block summary">
          <h2 class="blockTitle">요약</h2>
          <p class="leadProse">{clean(m.conclusion)}</p>
          {#if m.narrativeOverview}<p class="leadSub">{clean(m.narrativeOverview)}</p>{/if}
          {#if m.headlineKpis.length}
            <table class="summaryTable">
              <tbody>
                {#each chunk(m.headlineKpis, 3) as rowKpis}
                  <tr>{#each rowKpis as k}<th>{k.label}</th><td class={cellTone(k.value)}>{k.value}</td>{/each}</tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </section>

        {#if m.keyFindings.length}
          <section class="block keyFindings">
            <h2 class="blockTitle">주요 관찰 <span class="subNote">관점별 측정 요지{#if !allAnalysis} · 출처 병기{/if}</span></h2>
            <ul class="obsList">
              {#each m.keyFindings as kf}
                <li><b class="obsKey">{kf.key}</b> — {clean(kf.finding)}{#if !allAnalysis} <span class="obsSrc">({engineLabel[kf.sourceEngine] ?? kf.sourceEngine})</span>{/if}</li>
              {/each}
            </ul>
          </section>
        {/if}

        <!-- ── 목차 ── -->
        {#if m.sections.length > 1}
          <nav class="toc">
            <span class="tocLabel">목차</span>
            {#each m.sections as sec, i (sec.key)}
              <button class="tocItem" onclick={() => scrollSec(`${m.perspectiveKey}-${sec.key}`)}>
                <span class="tocNo">{String(i + 1).padStart(2, '0')}</span>{splitTitle(sec.title).head}
              </button>
            {/each}
          </nav>
        {/if}

        <!-- ── 본문 섹션 ── -->
        <div class="sections">
          {#each m.sections as sec, i (sec.key)}
            {@const t = splitTitle(sec.title)}
            <section class="rptSection src-{sec.sourceEngine}" class:emph={sec.emph} id={`sec-${m.perspectiveKey}-${sec.key}`}>
              <div class="secHead">
                <span class="secNo">{String(i + 1).padStart(2, '0')}</span>
                <div class="secTitleWrap">
                  <h2 class="secTitle">{t.head}</h2>
                  {#if t.sub}<div class="secSub">{t.sub}</div>{/if}
                </div>
                {#if !allAnalysis}<span class="chip srcBadge src-{sec.sourceEngine}">{engineLabel[sec.sourceEngine] ?? sec.sourceEngine}</span>{/if}
                <a class="secSrc" href={`${base}/viewer/company/${m.stockCode}`} target="_blank" rel="noopener" title="이 수치의 원천 — 공시뷰어에서 원본 사업·분기보고서 확인">원공시↗</a>
              </div>
              {#each sec.blocks as b}
                {#if b.type === 'heading'}
                  <h3 class="bHeading">{b.title}</h3>
                {:else if b.type === 'text'}
                  <p class="bText">{clean(b.text)}</p>
                {:else if b.type === 'metrics'}
                  <table class="figTable"><tbody>{#each chunk(b.metrics, 3) as mrow}<tr>{#each mrow as m}<th>{m.label}</th><td class={cellTone(m.value)}>{m.value}</td>{/each}</tr>{/each}</tbody></table>
                {:else if b.type === 'table' && b.data?.length}
                  {@const cols = Object.keys(b.data[0])}
                  {@const ts = isTimeSeries(cols) && tableHasSpark(b.data, cols)}
                  <div class="bTableWrap">
                    {#if b.label || b.unit}<div class="bTableTop">{#if b.label}<span class="tCap">{b.label}</span>{:else}<span></span>{/if}{#if b.unit}<span class="tUnit">단위 {b.unit}</span>{/if}</div>{/if}
                    <table class="bTable" class:snapshot={b.snapshot}>
                      <thead><tr>{#each cols as c, ci}<th class={ci === 0 ? 'lbl' : c === '판정' ? 'verdict-h' : TXT_COLS.has(c) ? 'txt-h' : 'num'}>{c}</th>{/each}{#if ts}<th class="sparkCol">추이</th>{/if}</tr></thead>
                      <tbody>
                        {#each b.data as row}
                          <tr>
                            {#each cols as c, ci}{#if ci === 0}<td class="lbl">{row[c]}</td>{:else if c === '판정'}{@const vt = verdictTone(row[c])}<td class="verdict {vt}"><span class="vPill {vt}">{#if vt === 'ok'}<span class="vMark">●</span>{:else if vt === 'warn'}<span class="vMark">▲</span>{/if}{row[c]}</span></td>{:else if TXT_COLS.has(c)}<td class="txt {c === '기준' ? 'threshold' : ''}">{row[c]}</td>{:else}<td class="num {cellTone(row[c])}" class:dash={String(row[c] ?? '').trim() === '-'}>{row[c]}</td>{/if}{/each}
                            {#if ts}{@const sp = spark(row, cols.slice(1))}<td class="sparkCol">{#if sp}<svg class="spark" width="64" height="22" viewBox="0 0 64 22" preserveAspectRatio="none">{#if sp.zeroY}<line x1="0" y1={sp.zeroY} x2="64" y2={sp.zeroY} stroke="var(--dim)" stroke-width="0.5" stroke-dasharray="2 2" opacity="0.5" />{/if}<polygon points={sp.area} fill="currentColor" opacity="0.10" stroke="none" /><polyline points={sp.points} fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" />{#each sp.clipMarks as cm}<circle cx={cm.x} cy={cm.y} r="1.8" fill="none" stroke="currentColor" stroke-width="0.9" />{/each}<circle cx={sp.lastX} cy={sp.lastY} r="2" fill="currentColor" /></svg>{:else}<span class="sparkDash">·</span>{/if}</td>{/if}
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {:else if b.type === 'bars'}
                  {@const mx = Math.max(...b.rows.map((r) => Math.abs(r.value)), 1e-9)}
                  <div class="barChart">
                    {#if b.label}<div class="tCap">{b.label}</div>{/if}
                    {#each b.rows as r}
                      <div class="barRow">
                        <span class="barLbl">{r.label}</span>
                        <span class="barTrack"><span class="barFill {r.tone ?? ''}" style="width:{Math.max(2, (Math.abs(r.value) / mx) * 100)}%"></span></span>
                        <span class="barVal {cellTone(r.display)}">{r.display}</span>
                      </div>
                    {/each}
                  </div>
                {:else if b.type === 'line'}
                  {@const g = lineGeo(b.series, b.markers ?? [])}
                  {#if g}
                    <div class="lineChart">
                      {#if b.label}<div class="tCap">{b.label}</div>{/if}
                      <div class="lineWrap">
                        <svg class="lineSvg" viewBox="0 0 100 30" preserveAspectRatio="none">
                          {#each g.mk as m}<line x1="0" y1={m.y} x2="100" y2={m.y} class="lineMarker" />{/each}
                          <polygon points={g.area} class="lineArea" />
                          <polyline points={g.pts} class="linePoly" />
                          <circle cx={g.lastX} cy={g.lastY} r="0.9" class="lineDot" />
                        </svg>
                        <span class="lineLast">{b.valueFmt === 'won' ? wonLabel(b.series[b.series.length - 1]) : b.series[b.series.length - 1]}</span>
                      </div>
                      <div class="lineAxis">
                        {#if b.xLabels}<span>{b.xLabels[0]}</span><span>{b.xLabels[1]}</span>{/if}
                      </div>
                      {#if b.markers?.length}<div class="lineLegend">{#each b.markers as m}<span class="lmk">{m.label} {b.valueFmt === 'won' ? wonLabel(m.v) : m.v}</span>{/each}</div>{/if}
                    </div>
                  {/if}
                {:else if b.type === 'share'}
                  <div class="shareChart">
                    {#if b.label}<div class="tCap">{b.label}</div>{/if}
                    {#each b.rows as row}
                      <div class="shareRow">
                        <span class="shareYr">{row.year}</span>
                        <span class="shareBar">{#each row.segs as s}<span class="shareSeg seg-{s.key}" style="width:{Math.max(0, s.pct)}%" title="{s.label} {s.pct.toFixed(1)}%"></span>{/each}</span>
                        <span class="shareTop">{row.segs[0].pct.toFixed(0)}%</span>
                      </div>
                    {/each}
                    <div class="shareLegend">{#each b.legend as l}<span class="slg seg-{l.key}"><span class="slgDot"></span>{l.label}</span>{/each}</div>
                  </div>
                {:else if b.type === 'flags'}
                  <ul class="bFlags {b.kind}">{#each b.flags as f}<li>{f}</li>{/each}</ul>
                {/if}
              {/each}
            </section>
          {/each}
        </div>

        <!-- ── 종합 의견 ── -->
        {#if m.closing.length}
          <section class="block closing">
            <h2 class="blockTitle">종합 의견 <span class="subNote">{m.perspectiveLabel} 관점 요약 (투자판단 아님)</span></h2>
            {#each m.closing as cl}
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
          <h2 class="blockTitle">근거·출처 <span class="subNote">이 보고서를 계산한 dartlab 엔진</span></h2>
          <div class="evEngines">
            {#each Object.entries(m.provenance.engines) as [eng, info]}
              <div class="evEngine"><span class="evDot"></span><span class="evLabel">{info.label ?? engineLabel[eng] ?? eng}</span><span class="evMeta">{info.sections}섹션 · {info.blocks}블록</span></div>
            {/each}
          </div>
          <div class="evNote">{m.provenance.note}</div>
          <a class="evSource" href={`${base}/viewer/company/${m.stockCode}`} target="_blank" rel="noopener">원본 공시 직접 확인 — {m.corpName} 공시뷰어에서 사업·분기보고서 원문 열기 ↗</a>
        </section>

        <!-- ── 푸터 / 서명 ── -->
        <footer class="rptFooter">
          {#if m.assumptionsNote}<div class="assump">가정·한계 — {m.assumptionsNote}</div>{/if}
          <div class="freezeNote">※ 본 출력본(인쇄/PDF)은 <b>데이터 기준 {m.asOf} 시점의 스냅샷</b>입니다. 이후 원천 데이터가 갱신되면 동일 보고서라도 수치가 달라질 수 있습니다.</div>
          <div class="footSign">
            <span class="signMain">{m.corpName} 기업분석보고서</span>
            <span class="dot">·</span><span>{m.perspectiveLabel} 관점</span>
            <span class="dot">·</span><span>데이터 기준 {m.asOf}</span>
            <span class="dot">·</span><span>작성 dartlab 분석엔진</span>
          </div>
          <div class="footLine">
            모든 수치 = dartlab 엔진({Object.values(m.provenance.engines).map((e) => e.label).join('·')}) 산출
            <span class="dot">·</span> sourceEngine = 계산 엔진(원천 DART 공시 줄 아님)
            <span class="dot">·</span> 본 보고서는 투자 권유가 아니며, 투자 판단의 책임은 이용자에게 있습니다.
          </div>
        </footer>
      </article>
      {/each}
    {/if}
  </div>

  <SupportDialog lang="kr" {links} {base} open={supportOpen} onClose={() => (supportOpen = false)} />
</div>

<style>
  /* ── 기본 = 화이트(용지) 테마 ── */
  .rptRoot {
    --backdrop: #e8eaed; --sheet: #ffffff; --ink: #1b1e23; --dim: #6b7178;
    --bd: #e6e9ed; --bd2: #d6dbe1; --soft: #f6f7f9;
    /* accent·emph·analysis = dartlab 시그니처 accent SSOT(tokens.css --dl-accent, 캐러셀 핑크). 흰 용지 대비용 진한 핑크(--dl-accent-dim). */
    --accent: var(--dl-accent-dim); --up: #1a7f37; --down: #c0392b; --warn: #9a6700; --emph: var(--dl-accent-dim);
    --e-analysis: var(--dl-accent-dim); --e-credit: #c0392b; --e-quant: #0a7d86; --e-industry: #1a7f37; --e-macro: #9a6700; --e-story: #6f42c1;
    --mono: ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, monospace;
    --sans: 'Pretendard', -apple-system, system-ui, sans-serif;
    background: var(--backdrop); color: var(--ink); min-height: 100vh; font-family: var(--sans); font-size: 13px; line-height: 1.6;
  }
  .rptRoot.dark {
    --backdrop: #0a0c10; --sheet: #161b24; --ink: #e8eef5; --dim: #8b949e;
    --bd: rgba(255, 255, 255, 0.10); --bd2: rgba(255, 255, 255, 0.18); --soft: #222a36;
    --accent: var(--dl-accent); --up: #2bc583; --down: #f85149; --warn: #d29922; --emph: var(--dl-accent);
    --e-analysis: var(--dl-accent); --e-credit: #f85149; --e-quant: #56d4dd; --e-industry: #2bc583; --e-macro: #d29922; --e-story: #9385ff;
  }

  /* ── 헤더 = 터미널 top bar 그대로 재사용(terminal.css · .dlTerm 스코프). 색·brand·cmdBar·SNS·hdrLink 는
     terminal.css 가 소유(단일 SSOT). 여기선 .dlTerm 의 전체화면 레이아웃(100vh·flex·overflow:hidden)만
     중화해 sticky 헤더로 쓴다 — 내 자체 색/스타일 없음. ── */
  .rptHeader.dlTerm {
    height: auto; display: block; overflow: visible;
    position: sticky; top: 0; z-index: 30;
  }
  /* 종목검색 = 아바타 옆 고정폭(터미널은 flex:1 — 여기선 늘리지 않음). 관점탭 = 중앙(좌측 search·우측 SNS 사이 free space 분할). */
  .rptHeader .cmdBar { flex: 0 1 300px; }
  .rptHeader .perspLinks { margin-left: auto; }
  /* 관점 탭 = 터미널 .hdrLink(amber active) 그대로. 한 줄, 넘치면 가로 스크롤(스크롤바 숨김). */
  .perspLinks { overflow-x: auto; scrollbar-width: none; }
  .perspLinks::-webkit-scrollbar { display: none; }

  .main { min-width: 0; }

  /* ── 표지 제목 옆 관점 ! — 클릭 시 '이 관점이 답하는 질문' 툴팁(AI 사족 prose 폐기, 느낌표로 압축) ── */
  .perspInfoWrap { position: relative; display: inline-block; }
  .perspInfo { width: 15px; height: 15px; margin-left: 7px; padding: 0; border: 1px solid var(--accent); border-radius: 50%; background: transparent; color: var(--accent); font-family: var(--mono); font-weight: 800; font-size: 10px; line-height: 1; cursor: pointer; vertical-align: 1px; }
  .perspInfo:hover { background: var(--accent); color: #fff; }
  .perspTip { position: absolute; top: calc(100% + 8px); left: 0; z-index: 20; width: max-content; max-width: 330px; text-transform: none; letter-spacing: normal; font-weight: 500; background: var(--sheet); color: var(--ink); border: 1px solid var(--bd2); border-radius: 8px; box-shadow: 0 8px 28px rgba(0, 0, 0, 0.16); padding: 10px 13px; font-size: 12px; line-height: 1.6; }
  .perspTip b { color: var(--accent); font-weight: 800; }
  .perspTip .perspTipQs { display: flex; flex-direction: column; gap: 2px; margin-top: 7px; padding-top: 7px; border-top: 1px solid var(--bd); }
  .perspTip .perspTipQs span { font-size: 11px; color: var(--dim); }
  .perspTip .perspTipQs span::before { content: '· '; color: var(--accent); }

  /* ── A4 용지 ── */
  .sheet {
    width: 820px; max-width: calc(100vw - 48px); margin: 28px auto 60px; padding: 52px 56px 44px;
    background: var(--sheet); border: 1px solid var(--bd); border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 12px 40px rgba(0, 0, 0, 0.10);
  }
  /* 5관점은 항상 빌드(models)돼 있고, 화면은 활성 1개만 *렌더*(renderModels), 인쇄는 beforeprint 가 전부 렌더.
     display:none 후 인쇄-되살리기는 헤디드 Chrome 빈 페이지 버그라 쓰지 않는다(렌더 자체를 토글). */
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
  .coverIntro { font-size: 13px; line-height: 1.75; color: var(--dim); margin: 18px 0 0; }

  /* ── 통합 리드 (5관점 한 몸 — 보고서 첫 페이지 executive overview) ── */
  .overviewLead { border: 1px solid var(--bd2); border-radius: 6px; background: var(--soft); padding: 16px 18px; margin-bottom: 26px; }
  .ovKicker { font-size: 11px; font-weight: 800; color: var(--accent); letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 9px; }
  .ovThesis { font-size: 13.5px; line-height: 1.72; font-weight: 600; margin: 0 0 12px; }
  .ovTakes { margin: 0; padding: 0; list-style: none; counter-reset: ov; }
  .ovTakes li { counter-increment: ov; border-top: 1px solid var(--bd); }
  .ovTake { display: block; width: 100%; text-align: left; background: transparent; border: 0; padding: 7px 0 7px 28px; cursor: pointer; font-family: var(--sans); position: relative; }
  .ovTake::before { content: counter(ov, decimal-leading-zero); position: absolute; left: 0; top: 8px; font-family: var(--mono); font-size: 10.5px; font-weight: 700; color: var(--accent); }
  .ovTakes li.on .ovTake { background: color-mix(in srgb, var(--accent) 7%, transparent); }
  .ovTake:hover { background: color-mix(in srgb, var(--accent) 9%, transparent); }
  .ovLabel { font-size: 12.5px; font-weight: 800; margin-right: 8px; color: var(--ink); white-space: nowrap; }
  .ovLabel.src-quant { color: var(--e-quant); }
  .ovLabel.src-industry { color: var(--e-industry); }
  .ovLine { font-size: 12px; color: var(--dim); line-height: 1.5; }

  /* ── 칩 ── */
  .chip { font-size: 11.5px; border-radius: 6px; padding: 3px 9px; border: 1px solid var(--bd2); color: var(--ink); white-space: nowrap; }
  .chip.focus { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 34%, transparent); background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 13px; }

  .focusRow { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 18px; }
  .printPerspective { display: none; }

  /* ── 공통 블록 ── */
  .block { margin-bottom: 26px; }
  .blockTitle { font-size: 13px; font-weight: 800; letter-spacing: 0.02em; margin: 0 0 12px; padding-bottom: 7px; border-bottom: 1px solid var(--bd2); display: flex; align-items: baseline; gap: 8px; }
  .blockTitle .subNote { font-size: 10.5px; font-weight: 400; color: var(--dim); }

  /* ── 요약(Executive Summary) — 문서형 산문 리드 + 요약 지표표(카드 폐기) ── */
  .leadProse { font-size: 15px; font-weight: 600; line-height: 1.68; letter-spacing: -0.005em; margin: 0 0 10px; }
  .leadSub { font-size: 12.5px; line-height: 1.75; color: var(--dim); margin: 0 0 14px; }
  .summaryTable { border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 6px; border-top: 1px solid var(--bd2); }
  .summaryTable th { text-align: left; font-weight: 500; color: var(--dim); font-family: var(--sans); padding: 7px 10px 7px 0; border-bottom: 1px solid var(--bd); white-space: nowrap; width: 1%; }
  .summaryTable td { text-align: left; font-family: var(--mono); font-variant-numeric: tabular-nums; font-weight: 700; padding: 7px 28px 7px 0; border-bottom: 1px solid var(--bd); white-space: nowrap; }
  .summaryTable td.neg { color: var(--down); } .summaryTable td.pos { color: var(--up); }

  /* ── 주요 관찰 — 칩 폐기, 문서형 목록 ── */
  .obsList { margin: 4px 0 0; padding-left: 18px; }
  .obsList li { font-size: 12.5px; line-height: 1.7; padding: 3px 0; }
  .obsKey { color: var(--accent); font-weight: 700; }
  .obsSrc { font-size: 10.5px; color: var(--dim); }
  /* 본문 figure 표 — 메트릭 칩 대체(라벨|값 인라인 표) */
  .figTable { border-collapse: collapse; font-size: 12px; margin: 10px 0; }
  .figTable th { text-align: left; font-weight: 500; color: var(--dim); font-family: var(--sans); padding: 5px 10px 5px 0; white-space: nowrap; }
  .figTable td { text-align: left; font-family: var(--mono); font-variant-numeric: tabular-nums; font-weight: 700; padding: 5px 24px 5px 0; white-space: nowrap; }
  .figTable td.neg { color: var(--down); } .figTable td.pos { color: var(--up); }

  /* ── 목차 ── */
  .toc { display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; margin: 0 0 30px; padding: 14px 16px; background: var(--soft); border: 1px solid var(--bd); border-radius: 10px; }
  .tocLabel { font-size: 11px; color: var(--dim); font-weight: 800; margin-right: 6px; letter-spacing: 0.06em; }
  .tocItem { background: transparent; border: 0; color: var(--ink); font-size: 12.5px; cursor: pointer; padding: 3px 9px; border-radius: 6px; display: inline-flex; align-items: baseline; gap: 6px; font-family: var(--sans); }
  .tocItem:hover { color: var(--accent); background: color-mix(in srgb, var(--accent) 9%, transparent); }
  .tocNo { font-family: var(--mono); font-size: 10.5px; color: var(--accent); font-weight: 700; }

  /* ── 본문 섹션 ── */
  .sections { counter-reset: sec; }
  .rptSection { margin-bottom: 30px; padding: 0; scroll-margin-top: 100px; }
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

  .bMetrics { display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); gap: 8px; margin: 12px 0; }
  .metric { background: var(--soft); border: 1px solid var(--bd); border-left: 2.5px solid color-mix(in srgb, var(--accent) 55%, transparent); border-radius: 7px; padding: 9px 13px; display: flex; flex-direction: column; gap: 4px; }
  .rptSection.src-quant .metric { border-left-color: color-mix(in srgb, var(--e-quant) 60%, transparent); }
  .mLabel { font-size: 10.5px; color: var(--dim); }
  .mValue { font-size: 17px; font-weight: 800; font-family: var(--mono); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
  .mValue.neg { color: var(--down); } .mValue.pos { color: var(--up); }

  .bTableWrap { margin: 12px 0; overflow-x: auto; }
  .tCap { font-size: 11.5px; color: var(--dim); margin-bottom: 6px; font-weight: 600; }
  /* 표 캡션(좌) + 단위 배지(우상단) — 단위를 셀에서 빼 칸 폭 절약·숫자 줄바뀜 방지 */
  .bTableTop { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 6px; }
  .bTableTop .tCap { margin-bottom: 0; }
  .tUnit { font-size: 11px; color: var(--dim); font-family: var(--mono); white-space: nowrap; flex-shrink: 0; }
  .bTable { border-collapse: collapse; font-size: 12px; width: 100%; }
  .bTable th { padding: 7px 10px; border-bottom: 1.5px solid var(--ink); color: var(--dim); font-weight: 700; font-family: var(--mono); background: color-mix(in srgb, var(--soft) 70%, transparent); }
  .bTable th.lbl { text-align: left; font-family: var(--sans); }
  .bTable th.num, .bTable th.sparkCol { text-align: right; }
  /* 라벨열↔연도격자 구분선(첫 데이터열 좌측 경계 — '연구 exhibit' 인상) */
  .bTable th.num:first-of-type, .bTable td.num:first-of-type,
  .bTable th.verdict-h:first-of-type, .bTable td.verdict:first-of-type,
  .bTable th.txt-h:first-of-type, .bTable td.txt:first-of-type { border-left: 1px solid var(--bd); }
  .bTable td { padding: 6px 10px; border-bottom: 1px solid var(--bd); }
  .bTable td.lbl { text-align: left; font-weight: 600; white-space: nowrap; }
  .bTable td.num { text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .bTable td.num.neg { color: var(--down); } .bTable td.num.pos { color: var(--up); }
  .bTable td.num.dash { color: var(--bd2); } /* 결측 '-' 은 옅게 — 있는 숫자가 도드라지게 */
  /* 비숫자 의미 컬럼 — 좌측 sans (시계열표 흉내 방지) */
  .bTable td.txt, .bTable th.txt-h { text-align: left; font-family: var(--sans); color: var(--ink); font-weight: 400; }
  .bTable td.txt.threshold { color: var(--dim); font-size: 11px; }
  /* 판정 — 상태 칩(양호=녹·주의=황갈·산출불가=중립). 적색은 음수 SSOT라 주의에 안 씀 */
  .bTable td.verdict, .bTable th.verdict-h { text-align: center; font-family: var(--sans); white-space: nowrap; }
  .vPill { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 11px; }
  .vPill.ok { color: var(--up); background: color-mix(in srgb, var(--up) 13%, transparent); }
  .vPill.warn { color: var(--warn); background: color-mix(in srgb, var(--warn) 15%, transparent); }
  .vMark { font-size: 8px; vertical-align: 1px; }
  .bTable tbody tr:nth-child(even) { background: var(--soft); }
  .bTable tbody tr:hover { background: color-mix(in srgb, var(--accent) 5%, transparent); }
  /* 스냅샷 표(시계열 아님 — 주요주주·임원보수·감사이력) — 인셋처럼 한 단계 축소 */
  .bTable.snapshot { font-size: 11.5px; }
  .bTable.snapshot th { background: color-mix(in srgb, var(--soft) 45%, transparent); border-bottom-color: var(--bd2); }
  .bTable.snapshot td { padding: 5px 10px; }
  /* 스냅샷 결측은 본문표보다 덜 옅게 — 빈 행이 '깨진 칸'이 아니라 '값 없음'으로 읽히게 */
  .bTable.snapshot td.num.dash { color: color-mix(in srgb, var(--bd2) 55%, var(--dim)); }
  .bTable td.sparkCol { text-align: right; padding-right: 2px; width: 74px; }
  .spark { vertical-align: middle; color: var(--accent); width: 64px; height: 22px; }
  .sparkDash { color: var(--bd2); font-size: 11px; }

  /* ── 막대 차트(채무 만기 사다리 등) ── */
  .barChart { margin: 12px 0; }
  .barRow { display: grid; grid-template-columns: 88px 1fr 80px; align-items: center; gap: 10px; padding: 3px 0; }
  .barLbl { font-size: 11.5px; color: var(--ink); text-align: right; }
  .barTrack { height: 15px; background: var(--soft); border-radius: 3px; overflow: hidden; }
  .barFill { display: block; height: 100%; background: var(--accent); border-radius: 3px; min-width: 2px; }
  .barFill.neg { background: var(--down); }
  .barVal { font-size: 11.5px; font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
  .barVal.neg { color: var(--down); }

  /* ── 라인 차트(주가 궤적) ── */
  .lineChart { margin: 14px 0; }
  .lineWrap { position: relative; }
  .lineSvg { width: 100%; height: 98px; display: block; overflow: visible; }
  .linePoly { fill: none; stroke: var(--e-quant); stroke-width: 1.6; vector-effect: non-scaling-stroke; stroke-linejoin: round; stroke-linecap: round; }
  .lineArea { fill: var(--e-quant); opacity: 0.1; stroke: none; }
  .lineMarker { stroke: var(--dim); stroke-width: 1; stroke-dasharray: 3 3; opacity: 0.5; vector-effect: non-scaling-stroke; }
  .lineDot { fill: var(--e-quant); }
  .lineLast { position: absolute; top: -7px; right: 0; font-size: 11.5px; font-family: var(--mono); font-weight: 800; color: var(--e-quant); }
  .lineAxis { display: flex; justify-content: space-between; font-size: 10px; color: var(--dim); font-family: var(--mono); margin-top: 4px; }
  .lineLegend { display: flex; gap: 14px; margin-top: 5px; }
  .lmk { font-size: 10.5px; color: var(--dim); }

  /* ── 누적 점유 막대(소유 집중도) ── */
  .shareChart { margin: 12px 0; }
  .shareRow { display: grid; grid-template-columns: 50px 1fr 42px; align-items: center; gap: 10px; padding: 2px 0; }
  .shareYr { font-size: 11px; color: var(--dim); font-family: var(--mono); text-align: right; }
  .shareBar { display: flex; height: 16px; border-radius: 3px; overflow: hidden; background: var(--soft); }
  .shareSeg { height: 100%; }
  .shareSeg.seg-major { background: var(--accent); }
  .shareSeg.seg-minor { background: color-mix(in srgb, var(--e-quant) 72%, transparent); }
  .shareSeg.seg-other { background: var(--bd2); }
  .shareTop { font-size: 11px; font-family: var(--mono); text-align: right; color: var(--ink); }
  .shareLegend { display: flex; gap: 14px; margin-top: 7px; padding-left: 60px; }
  .slg { font-size: 10.5px; color: var(--dim); display: inline-flex; align-items: center; gap: 5px; }
  .slgDot { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
  .slg.seg-major .slgDot { background: var(--accent); }
  .slg.seg-minor .slgDot { background: color-mix(in srgb, var(--e-quant) 72%, transparent); }
  .slg.seg-other .slgDot { background: var(--bd2); }

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
  .evSource { display: inline-block; margin-top: 11px; font-size: 11.5px; color: var(--accent); text-decoration: none; font-weight: 600; }
  .evSource:hover { text-decoration: underline; }
  /* 섹션 헤더 원공시 딥링크 — 신뢰 last mile(숫자→원본 공시) */
  .secSrc { font-size: 10px; color: var(--dim); text-decoration: none; border: 1px solid var(--bd2); border-radius: 5px; padding: 2px 7px; white-space: nowrap; align-self: center; }
  .secSrc:hover { color: var(--accent); border-color: var(--accent); }

  /* ── 푸터 ── */
  .rptFooter { margin-top: 36px; padding-top: 16px; border-top: 2px solid var(--ink); font-size: 11px; color: var(--dim); }
  .assump { margin-bottom: 10px; color: var(--warn); }
  .freezeNote { display: none; }
  @media print { .freezeNote { display: block; margin-bottom: 10px; font-size: 10px; color: #6a4a00; border: 1px solid #b9c1c9; border-radius: 4px; padding: 6px 9px; } }
  .footSign { font-size: 12px; color: var(--ink); display: flex; flex-wrap: wrap; gap: 7px; align-items: center; margin-bottom: 8px; }
  .footSign .signMain { font-weight: 700; }
  .footSign .dot, .footLine .dot { opacity: 0.4; }
  .footLine { line-height: 1.7; }
  .muted { color: var(--dim); }

  /* ── 반응형 ── */
  @media (max-width: 860px) {
    .sheet { max-width: calc(100vw - 24px); padding: 32px 22px 30px; }
    .coverTitle { font-size: 28px; }
  }

  /* ── 인쇄 — A4, 화이트 강제 ── */
  @media print {
    /* 루트 레이아웃의 :global(html/body){overflow-x:clip} 이 Chrome 인쇄 페이지네이션을 비워(빈 미리보기)
       인쇄 시에만 해제 — 화면 가로스크롤 가드는 그대로 유지. */
    :global(html), :global(body) { overflow: visible !important; max-width: none !important; height: auto !important; }
    /* 색 변수는 !important 로 강제 — 다크 테마(.rptRoot.dark)나 dev 스타일 주입 순서에 상관없이
       인쇄는 무조건 검정-on-흰색. (override 가 못 이기면 본문이 흰색으로 찍혀 빈 페이지처럼 보였다) */
    .rptRoot, .rptRoot.dark {
      --backdrop: #fff !important; --sheet: #fff !important; --soft: #eef2f6 !important; --ink: #161616 !important; --dim: #555a60 !important;
      --bd: #d8dde3 !important; --bd2: #b9c1c9 !important;
      --accent: var(--dl-accent-dim) !important; --up: #1a7f37 !important; --down: #b02a1a !important; --warn: #8a6100 !important; --emph: var(--dl-accent-dim) !important;
      --e-analysis: var(--dl-accent-dim) !important; --e-credit: #b02a1a !important; --e-quant: #0a7d86 !important; --e-industry: #1a7f37 !important; --e-macro: #8a6100 !important; --e-story: #6f42c1 !important;
      background: #fff !important; color: #161616 !important; font-size: 10.2pt;
      print-color-adjust: exact; -webkit-print-color-adjust: exact;
    }
    .rptHeader, .toc, .secSrc { display: none !important; }
    .printPerspective { display: block; font-size: 11px; color: #555; margin-bottom: 12px; font-weight: 600; }
    .sheet { width: 100%; max-width: 100%; margin: 0; padding: 0; border: 0; box-shadow: none; border-radius: 0; }
    /* 인쇄 = 5관점 전부(beforeprint 가 렌더). 관점마다 새 페이지·"5관점 요약"은 첫 관점에만. */
    .perspSheet + .perspSheet { break-before: page; page-break-before: always; }
    .perspSheet:not(:first-of-type) .overviewLead { display: none; }
    /* break-inside:avoid 는 *작은 원자 단위*에만 — 한 페이지보다 큰 섹션 컨테이너에 걸면 Chrome 이
       클리핑/빈 페이지를 낸다. 섹션은 하위 블록(.bTableWrap·.secHead) 경계에서 깔끔히 쪼개지게 둔다. */
    .clRow, .summaryTable, .coverFacts, .focusRow, .bTableWrap { break-inside: avoid; }
    .cover { break-after: avoid; }
    .bTable thead { display: table-header-group; }
    .secHead { break-after: avoid; }
    .spark { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    .summaryTable th, .figTable th { color: #555a60 !important; }
    .bTable th { border-bottom-color: #161616; }
    .bTable tbody tr:nth-child(even) { background: #eaeff4 !important; }
    .spark polyline { stroke-width: 2px; }
    .spark.flat { color: #5b6470; }
    .chip.focus { background: none; }
    @page { size: A4; margin: 14mm 13mm; }
  }
</style>
