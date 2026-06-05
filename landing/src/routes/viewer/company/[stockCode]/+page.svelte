<script lang="ts">
	// 공시뷰어 — panel 하나로 브라우저 readWide → TOC + 항목×기간 격자 + 타임라인 + 원본 링크.
	// 디자인 = scan 방식(flat #050811 · #1e2433 보더 · 오렌지 단일 액센트). 풀블리드(좌우 패딩 0 · 갭 0).
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { dev } from '$app/environment'; // 회사 비교 = 미완성 → dev 에서만(GitHub Pages 프로덕션 숨김)
	import { Maximize2, Minimize2, Columns3, MessageSquare, Table2, X, Plus } from 'lucide-svelte';
	import Header from '$lib/components/sections/Header.svelte';
	import { loadPanelBundle } from '$lib/viewer/panelLoad';
	import PanelTocTree from '$lib/components/viewer/PanelTocTree.svelte';
	import PanelMatrix from '$lib/components/viewer/PanelMatrix.svelte';
	import ComparisonMatrix from '$lib/components/viewer/ComparisonMatrix.svelte';
	import TimelineRibbon from '$lib/components/viewer/TimelineRibbon.svelte';
	import CommandPalette from '$lib/components/viewer/CommandPalette.svelte';
	import CompanySearch from '$lib/components/viewer/CompanySearch.svelte';
	import GiscusPanel from '$lib/components/viewer/GiscusPanel.svelte';
	import FinanceDialog from '$lib/components/viewer/FinanceDialog.svelte';
	import { loadCompanies } from '$lib/viewer/companyNames';
	import { buildIndexChunked, type SearchIndex, type SearchHit } from '$lib/viewer/searchIndex';
	import { alignBundles, commonPeriods } from '$lib/viewer/align';
	import { alignFinance, isFinanceSection } from '$lib/viewer/financeCells';
	import type { PanelBundle } from '$lib/viewer/types';

	let { data }: { data: { code: string; vs?: string[] } } = $props();
	const code = $derived(data.code);
	const vsCodes = $derived(data.vs ?? []);

	// 회사명 — panel 엔 없음 → ecosystem(code→name) 해석. corp(panel) 우선, 없으면 ecosystem.
	let nameMap = $state<Map<string, string>>(new Map());
	onMount(() => {
		void loadCompanies().then((l) => (nameMap = new Map(l.map((c) => [c.code, c.name]))));
	});

	const COL_CHOICES = [3, 6, 9] as const;

	let bundle = $state<PanelBundle | null>(null);
	let errorMsg = $state<string | null>(null);
	let loading = $state(true);
	let activeSectionKey = $state<string | undefined>(undefined);
	let activeBlock = $state<string | null>(null); // 활성 주석(blockLeaf) — null 이면 섹션 전체
	let windowEnd = $state(0); // periods 시작 인덱스 (0 = 최신, 좌측)
	let cols = $state(3);
	let isFullscreen = $state(false);
	let discussOpen = $state(false);
	let financeOpen = $state(false); // 정량재무제표 다이얼로그
	let annualOnly = $state(false); // 연간만(사업보고서) 필터 — period 축을 회사별 결산보정 annual 로 거름
	let searchIndex = $state<SearchIndex | null>(null);
	let indexing = $state(false);
	let glowCell = $state<{ rowIndex: number; period: string } | null>(null);

	// ── 회사 간 비교 (?vs=) ── 단일 뷰어 위에 additive. vs 없으면 전부 비활성.
	let vsBundles = $state<PanelBundle[]>([]); // 비교 추가 회사 bundle (reference=bundle, 나머지=여기)
	let lockedPeriod = $state(''); // 비교 모드 = 한 시점 lock
	let addOpen = $state(false); // 회사 추가 팝오버
	// 비교 모드 판정 — 파생을 일찍 선언(windowPeriods 등이 참조). vsCodes/bundle/vsBundles 에만 의존.
	// dev 게이트: 회사 비교는 미완성 → 로컬 dev 에서만. 프로덕션(GitHub Pages)은 ?vs= 무시(단일 뷰어).
	const compareMode = $derived(dev && vsCodes.length > 0);
	const allBundles = $derived(bundle ? [bundle, ...vsBundles] : []);

	// code 바뀌면(검색 이동) 재로드.
	$effect(() => {
		const c = code;
		try {
			localStorage.setItem('dartlab:lastViewer', c); // 마지막 본 종목 캐시 (재방문 시 /viewer 가 복원)
		} catch {
			/* localStorage 불가 무시 */
		}
		loading = true;
		errorMsg = null;
		bundle = null;
		windowEnd = 0;
		activeBlock = null;
		loadPanelBundle(c)
			.then((b) => {
				bundle = b;
				activeSectionKey = b.toc.chapters[0]?.sections[0]?.sectionKey;
				activeBlock = null;
				if (!b.periods.length) errorMsg = '이 종목의 panel 데이터가 없습니다 (HF 업로드 대기 중일 수 있음).';
			})
			.catch((e) => {
				errorMsg = `로드 실패: ${e instanceof Error ? e.message : String(e)}`;
			})
			.finally(() => {
				loading = false;
			});
	});

	// 본문 검색 색인 — bundle 로드 후 타임슬라이싱 빌드(메인스레드 비차단). code 바뀌면 재빌드.
	$effect(() => {
		const b = bundle;
		searchIndex = null;
		if (!b || !b.periods.length) {
			indexing = false;
			return;
		}
		indexing = true;
		let cancelled = false;
		void buildIndexChunked(b).then((idx) => {
			if (!cancelled) {
				searchIndex = idx;
				indexing = false;
			}
		});
		return () => {
			cancelled = true;
		};
	});

	// 비교 회사(?vs) 병렬 로드 — allSettled(한 회사 실패해도 나머지 비교). code/vs 바뀌면 재로드.
	$effect(() => {
		const codes = vsCodes;
		void code; // code 바뀌면도 재로드(reference 교체)
		if (!codes.length) {
			vsBundles = [];
			return;
		}
		let cancelled = false;
		void Promise.allSettled(codes.map((c) => loadPanelBundle(c))).then((results) => {
			if (cancelled) return;
			vsBundles = results
				.filter((r): r is PromiseFulfilledResult<PanelBundle> => r.status === 'fulfilled' && r.value.periods.length > 0)
				.map((r) => r.value);
		});
		return () => {
			cancelled = true;
		};
	});

	// 검색 결과 클릭 → 그 섹션·기간으로 격자 점프 + 셀 글로우.
	function onSearchResult(hit: SearchHit) {
		pickSection(hit.sectionKey);
		pickPeriod(hit.period);
		glowCell = { rowIndex: hit.rowIndex, period: hit.period };
		setTimeout(() => (glowCell = null), 2200);
	}

	// 전체보기 Esc 해제.
	$effect(() => {
		if (!isFullscreen) return;
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') isFullscreen = false;
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	const periods = $derived(bundle?.periods ?? []);
	// "연간만" 필터 시 사업보고서(annual) period 만 — 빈 결과면 자동으로 전체로 폴백(빈 화면 방지).
	const annualPeriods = $derived.by(() => {
		const b = bundle;
		return b ? periods.filter((p) => b.periodKind[p] === 'annual') : [];
	});
	const visiblePeriods = $derived(annualOnly && annualPeriods.length ? annualPeriods : periods);
	// 비교 모드 = 한 시점만 강조(타임라인은 시점 선택기). 단일 모드 = 기존 윈도.
	const windowPeriods = $derived(
		compareMode ? (lockedPeriod ? [lockedPeriod] : []) : visiblePeriods.slice(windowEnd, windowEnd + cols)
	);
	// 활성 섹션 행 — 주석(blockLeaf) 선택 시 그 주석만(기간별), 아니면 섹션 전체.
	const rows = $derived.by(() => {
		if (!activeSectionKey || !bundle) return [];
		const base = bundle.gridBySection.get(activeSectionKey) ?? [];
		return activeBlock ? base.filter((r) => r.blockLeaf === activeBlock) : base;
	});
	const dartUrls = $derived(bundle?.dartUrlByPeriod ?? {});
	const sectionLabel = $derived.by(() => {
		const s = activeSectionKey?.split('␟').pop() ?? '';
		return activeBlock ? `${s} · ${activeBlock}` : s;
	});
	const corpName = $derived(bundle?.corpName || nameMap.get(code) || '');

	// ── 비교 모드 파생 (compareMode·allBundles 는 위에서 선언) ──
	const cmpCompanies = $derived(
		allBundles.map((b) => ({ code: b.stockCode, corpName: b.corpName || nameMap.get(b.stockCode) || b.stockCode }))
	);
	// 활성 섹션이 재무 5표(BS/IS/CF…)면 셀(항목) 단위 비교(acode 정렬+원환산), 아니면 행(통짜) 비교.
	const isFinance = $derived(
		compareMode && !!bundle && !!activeSectionKey && isFinanceSection(bundle.gridBySection.get(activeSectionKey) ?? [])
	);
	const financeRows = $derived(
		isFinance && lockedPeriod && allBundles.length >= 2
			? alignFinance(allBundles, activeSectionKey!, lockedPeriod, 'quarter')
			: []
	);
	const alignedRows = $derived(
		compareMode && !isFinance && activeSectionKey && lockedPeriod && allBundles.length >= 2
			? alignBundles(allBundles, activeSectionKey, lockedPeriod)
			: []
	);
	// 비교 시점 기본 = 최신 공통 기간. 유효하지 않으면 보정.
	$effect(() => {
		if (!compareMode || allBundles.length < 2) return;
		const cp = commonPeriods(allBundles);
		if (!lockedPeriod || !cp.includes(lockedPeriod)) lockedPeriod = cp[0] ?? '';
	});

	// ── 비교 회사 추가/제거 (URL ?vs=) ──
	function vsUrl(codes: string[]): string {
		const q = codes.filter((c) => c && c !== code).join(',');
		return `${base}/viewer/company/${code}${q ? `?vs=${q}` : ''}`;
	}
	function addCompany(c: string) {
		if (!c || c === code || vsCodes.includes(c) || allBundles.length >= 6) return;
		addOpen = false;
		void goto(vsUrl([...vsCodes, c]));
	}
	function removeCompany(c: string) {
		void goto(vsUrl(vsCodes.filter((x) => x !== c)));
	}

	// 섹션/주석 이동은 보고 있던 기간 윈도우를 보존 — 기간축은 섹션 무관 글로벌이라 리셋할 이유 없음(같은 시점의
	// 다른 TOC 를 보려는 흐름). 리셋은 축 변경(연간토글)·회사 변경 때만.
	function pickSection(sectionKey: string) {
		activeSectionKey = sectionKey;
		activeBlock = null; // 섹션 헤더 클릭 = 전체
	}
	function pickBlock(sectionKey: string, blockLeaf: string) {
		activeSectionKey = sectionKey;
		activeBlock = blockLeaf; // 개별 주석 선택 = 그 주석만
	}
	function pickPeriod(p: string) {
		if (compareMode) {
			lockedPeriod = p; // 비교 = 시점 lock (N사 동시 그 시점)
			return;
		}
		const idx = visiblePeriods.indexOf(p);
		if (idx >= 0) windowEnd = idx;
	}
	function moveNewer() {
		if (compareMode) {
			const i = visiblePeriods.indexOf(lockedPeriod);
			if (i > 0) lockedPeriod = visiblePeriods[i - 1];
			return;
		}
		windowEnd = Math.max(0, windowEnd - 1);
	}
	function moveOlder() {
		if (compareMode) {
			const i = visiblePeriods.indexOf(lockedPeriod);
			if (i >= 0 && i + 1 < visiblePeriods.length) lockedPeriod = visiblePeriods[i + 1];
			return;
		}
		windowEnd = Math.min(visiblePeriods.length - 1, windowEnd + 1);
	}
	function toggleAnnual() {
		annualOnly = !annualOnly;
		windowEnd = 0; // 축이 바뀌므로 최신으로 리셋
	}
	const lockedIdx = $derived(visiblePeriods.indexOf(lockedPeriod));
	const canNewer = $derived(compareMode ? lockedIdx > 0 : windowEnd > 0);
	const canOlder = $derived(compareMode ? lockedIdx >= 0 && lockedIdx + 1 < visiblePeriods.length : windowEnd + 1 < visiblePeriods.length);
</script>

<svelte:head><title>{corpName || code} 공시뷰어 · dartlab</title></svelte:head>

{#if !isFullscreen}
	<Header context="landing" />
{/if}

<main class="viewer-page" class:fullscreen={isFullscreen}>
	<header class="page-head">
		<div class="ph-left">
			{#if compareMode}
				<div class="chips">
					{#each cmpCompanies as c (c.code)}
						<span class="chip" class:ref={c.code === code}>
							<span class="chip-name">{c.corpName}</span>
							{#if c.code !== code}
								<button type="button" class="chip-x" onclick={() => removeCompany(c.code)} title="비교에서 제거"><X size={10} /></button>
							{/if}
						</span>
					{/each}
				</div>
				{#if sectionLabel}<span class="ph-section">{sectionLabel}</span>{/if}
			{:else}
				<h1 class="ph-corp">{corpName || code}</h1>
				<span class="ph-code">{code}</span>
				{#if bundle && sectionLabel}<span class="ph-section">{sectionLabel}</span>{/if}
			{/if}
		</div>
		<div class="ph-right">
			<CommandPalette index={searchIndex} toc={bundle?.toc ?? null} {indexing} onResult={onSearchResult} onSection={pickSection} />
			<button type="button" class="fs-btn" onclick={() => (financeOpen = true)} title="재무제표 정량 (IS/BS/CF/CIS/자본변동 · 연결/개별)">
				<Table2 size={13} /> 재무제표(정량)
			</button>
			<button type="button" class="fs-btn" onclick={() => (discussOpen = true)} title="공시 토론 (GitHub Discussions)">
				<MessageSquare size={13} /> 토론
			</button>
			{#if bundle}
				{#if dev}
					<div class="add-wrap">
						<button type="button" class="fs-btn" class:active={compareMode} onclick={() => (addOpen = !addOpen)} title="회사 간 비교 — 회사 추가 (최대 6) · 미완성(dev 전용)" disabled={allBundles.length >= 6}>
							<Plus size={13} /> 비교
						</button>
						{#if addOpen}
							<div class="add-pop"><CompanySearch onpick={addCompany} /></div>
						{/if}
					</div>
				{/if}
				{#if compareMode}
					<span class="meta">{cmpCompanies.length}사 · {lockedPeriod} · {isFinance ? `재무 ${financeRows.length}항목` : `항목 ${alignedRows.length}`}</span>
				{:else}
					<span class="meta">항목 {rows.length} · 기간 {visiblePeriods.length}{annualOnly ? '(연간)' : ''}</span>
				{/if}
				<button type="button" class="annual-btn" class:active={annualOnly} onclick={toggleAnnual} title="사업보고서(연간)만 표시 — 회사 결산월 보정">연간만</button>
				{#if !compareMode}
					<div class="cols" title="동시 표시 기간 수 (가로 폭)">
						<Columns3 size={13} />
						{#each COL_CHOICES as n (n)}
							<button type="button" class="col-btn" class:active={cols === n} onclick={() => (cols = n)}>{n}</button>
						{/each}
					</div>
				{/if}
				<button type="button" class="fs-btn" onclick={() => (isFullscreen = !isFullscreen)} title={isFullscreen ? '전체보기 해제 (Esc)' : '전체보기'}>
					{#if isFullscreen}<Minimize2 size={13} /> 복귀{:else}<Maximize2 size={13} /> 전체{/if}
				</button>
			{/if}
		</div>
	</header>

	{#if bundle && !loading}
		<div class="ribbon-bar">
			<TimelineRibbon periods={visiblePeriods} {windowPeriods} onpick={pickPeriod} onnewer={moveNewer} onolder={moveOlder} {canNewer} {canOlder} />
		</div>
	{/if}

	{#if loading}
		<div class="state">
			<picture>
				<source srcset="{base}/avatar-study.webp" type="image/webp" />
				<img class="state-avatar" src="{base}/avatar-study.png" alt="" width="72" height="72" />
			</picture>
			<div class="spinner"></div>
			<p>{corpName || code} 공시 본문을 여는 중</p>
		</div>
	{:else if errorMsg}
		<div class="state">
			<picture>
				<source srcset="{base}/avatar-curious.webp" type="image/webp" />
				<img class="state-avatar" src="{base}/avatar-curious.png" alt="" width="72" height="72" />
			</picture>
			<p>{errorMsg}</p>
		</div>
	{:else if bundle}
		<div class="studio">
			<aside class="toc">
				<PanelTocTree toc={bundle.toc} {activeSectionKey} {activeBlock} onpick={pickSection} onpickBlock={pickBlock} />
			</aside>
			<section class="board">
				{#if compareMode}
					{#if allBundles.length < 2}
						<div class="cmp-loading"><div class="spinner"></div><p>비교 회사 여는 중…</p></div>
					{:else}
						<ComparisonMatrix rows={alignedRows} financeRows={isFinance ? financeRows : null} companies={cmpCompanies} period={lockedPeriod} />
					{/if}
				{:else}
					<PanelMatrix {rows} periods={windowPeriods} dartUrlByPeriod={dartUrls} glow={glowCell} />
				{/if}
			</section>
		</div>
	{/if}
</main>

<GiscusPanel {code} {corpName} open={discussOpen} onclose={() => (discussOpen = false)} />
<FinanceDialog {code} {corpName} open={financeOpen} onclose={() => (financeOpen = false)} />

<style>
	.viewer-page {
		height: 100vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		background: #050811;
		color: #f1f5f9;
		padding: 56px 0 0;
	}
	.viewer-page.fullscreen {
		position: fixed;
		inset: 0;
		z-index: 100;
		padding: 0;
	}

	.page-head {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 8px 12px;
		border-bottom: 1px solid #1e2433;
	}
	.ph-left {
		display: flex;
		align-items: baseline;
		gap: 8px;
		min-width: 0;
	}
	.ph-corp {
		margin: 0;
		font-size: 20px;
		font-weight: 800;
		letter-spacing: -0.02em;
		color: #f1f5f9;
		white-space: nowrap;
	}
	.ph-code {
		flex-shrink: 0;
		font-size: 11px;
		color: #64748b;
		font-family: monospace;
	}
	.ph-section {
		min-width: 0;
		font-size: 12px;
		color: #94a3b8;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.ph-section::before {
		content: '·';
		margin-right: 6px;
		color: #475569;
	}
	.ph-right {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-shrink: 0;
	}
	.meta {
		font-size: 11px;
		color: #94a3b8;
		white-space: nowrap;
	}
	.cols {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		padding: 2px 4px 2px 6px;
		border: 1px solid #1e2433;
		border-radius: 5px;
		color: #64748b;
	}
	.col-btn {
		padding: 2px 6px;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: #94a3b8;
		font-family: monospace;
		font-size: 11px;
		cursor: pointer;
	}
	.col-btn:hover {
		color: #cbd5e1;
	}
	.col-btn.active {
		background: rgba(251, 146, 60, 0.14);
		color: #fb923c;
	}
	.fs-btn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		height: 30px;
		padding: 0 9px;
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #050811;
		color: #94a3b8;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
		white-space: nowrap;
	}
	.fs-btn:hover {
		border-color: #fb923c;
		color: #fb923c;
	}
	.fs-btn.active {
		border-color: rgba(251, 146, 60, 0.5);
		background: rgba(251, 146, 60, 0.12);
		color: #fb923c;
		font-weight: 600;
	}
	.fs-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	/* 회사 간 비교 — 칩 + 추가 팝오버 */
	.chips {
		display: flex;
		align-items: center;
		gap: 5px;
		flex-wrap: wrap;
		min-width: 0;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		height: 24px;
		padding: 0 4px 0 9px;
		border: 1px solid #1e2433;
		border-radius: 12px;
		background: #0a0e18;
		font-size: 12px;
		color: #cbd5e1;
		white-space: nowrap;
	}
	.chip.ref {
		border-color: rgba(251, 146, 60, 0.5);
		background: rgba(251, 146, 60, 0.1);
		color: #f8fafc;
		padding-right: 9px;
	}
	.chip-name {
		font-weight: 600;
		max-width: 130px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.chip-x {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		border: none;
		border-radius: 50%;
		background: transparent;
		color: #64748b;
		cursor: pointer;
		padding: 0;
	}
	.chip-x:hover {
		background: rgba(248, 113, 113, 0.15);
		color: #f87171;
	}
	.add-wrap {
		position: relative;
	}
	.add-pop {
		position: absolute;
		top: calc(100% + 6px);
		right: 0;
		z-index: 60;
	}
	.cmp-loading {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		color: #94a3b8;
		font-size: 13px;
	}
	.annual-btn {
		height: 30px;
		padding: 0 10px;
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #050811;
		color: #94a3b8;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
		white-space: nowrap;
	}
	.annual-btn:hover {
		border-color: #fb923c;
		color: #fb923c;
	}
	.annual-btn.active {
		border-color: rgba(251, 146, 60, 0.5);
		background: rgba(251, 146, 60, 0.12);
		color: #fb923c;
		font-weight: 600;
	}

	.ribbon-bar {
		flex-shrink: 0;
		padding: 6px 12px;
		border-bottom: 1px solid #1e2433;
	}

	.state {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 14px;
		text-align: center;
	}
	.state-avatar {
		border-radius: 50%;
		opacity: 0.95;
		filter: drop-shadow(0 4px 16px rgba(251, 146, 60, 0.18));
	}
	.state p {
		color: #94a3b8;
		font-size: 13px;
		margin: 0;
	}
	.spinner {
		width: 28px;
		height: 28px;
		border: 2px solid #1e2433;
		border-top-color: #fb923c;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.studio {
		flex: 1 1 auto;
		min-height: 0;
		display: grid;
		grid-template-columns: 240px 1fr;
	}
	.toc {
		min-height: 0;
		overflow-y: auto;
		border-right: 1px solid #1e2433;
		padding: 8px;
	}
	.board {
		min-width: 0;
		min-height: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	@media (max-width: 880px) {
		.studio {
			grid-template-columns: 1fr;
		}
		.toc {
			max-height: 180px;
			border-right: none;
			border-bottom: 1px solid #1e2433;
		}
	}
</style>
