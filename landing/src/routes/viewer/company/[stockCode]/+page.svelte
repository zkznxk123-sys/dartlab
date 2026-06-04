<script lang="ts">
	// 공시뷰어 — panel 하나로 브라우저 readWide → TOC + 항목×기간 격자 + 타임라인 + 원본 링크.
	// 디자인 = scan 방식(flat #050811 · #1e2433 보더 · 오렌지 단일 액센트). 풀블리드(좌우 패딩 0 · 갭 0).
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { Maximize2, Minimize2, Columns3, MessageSquare } from 'lucide-svelte';
	import Header from '$lib/components/sections/Header.svelte';
	import { loadPanelBundle } from '$lib/viewer/panelLoad';
	import PanelTocTree from '$lib/components/viewer/PanelTocTree.svelte';
	import PanelMatrix from '$lib/components/viewer/PanelMatrix.svelte';
	import TimelineRibbon from '$lib/components/viewer/TimelineRibbon.svelte';
	import CompanySearch from '$lib/components/viewer/CompanySearch.svelte';
	import GiscusPanel from '$lib/components/viewer/GiscusPanel.svelte';
	import { loadCompanies } from '$lib/viewer/companyNames';
	import type { PanelBundle } from '$lib/viewer/types';

	let { data }: { data: { code: string } } = $props();
	const code = $derived(data.code);

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
	let windowEnd = $state(0); // periods 시작 인덱스 (0 = 최신, 좌측)
	let cols = $state(3);
	let isFullscreen = $state(false);
	let discussOpen = $state(false);

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
		loadPanelBundle(c)
			.then((b) => {
				bundle = b;
				activeSectionKey = b.toc.chapters[0]?.sections[0]?.sectionKey;
				if (!b.periods.length) errorMsg = '이 종목의 panel 데이터가 없습니다 (HF 업로드 대기 중일 수 있음).';
			})
			.catch((e) => {
				errorMsg = `로드 실패: ${e instanceof Error ? e.message : String(e)}`;
			})
			.finally(() => {
				loading = false;
			});
	});

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
	const windowPeriods = $derived(periods.slice(windowEnd, windowEnd + cols));
	const rows = $derived(activeSectionKey && bundle ? (bundle.gridBySection.get(activeSectionKey) ?? []) : []);
	const dartUrls = $derived(bundle?.dartUrlByPeriod ?? {});
	const sectionLabel = $derived(activeSectionKey?.split('␟').pop() ?? '');
	const corpName = $derived(bundle?.corpName || nameMap.get(code) || '');

	function pickSection(sectionKey: string) {
		activeSectionKey = sectionKey;
		windowEnd = 0;
	}
	function pickPeriod(p: string) {
		const idx = periods.indexOf(p);
		if (idx >= 0) windowEnd = idx;
	}
	function moveNewer() {
		windowEnd = Math.max(0, windowEnd - 1);
	}
	function moveOlder() {
		windowEnd = Math.min(periods.length - 1, windowEnd + 1);
	}
	const canNewer = $derived(windowEnd > 0);
	const canOlder = $derived(windowEnd + 1 < periods.length);
</script>

<svelte:head><title>{corpName || code} 공시뷰어 · dartlab</title></svelte:head>

{#if !isFullscreen}
	<Header context="landing" />
{/if}

<main class="viewer-page" class:fullscreen={isFullscreen}>
	<header class="page-head">
		<div class="ph-left">
			<h1 class="ph-corp">{corpName || code}</h1>
			<span class="ph-code">{code}</span>
			{#if bundle && sectionLabel}<span class="ph-section">{sectionLabel}</span>{/if}
		</div>
		<div class="ph-right">
			<CompanySearch />
			<button type="button" class="fs-btn" onclick={() => (discussOpen = true)} title="공시 토론 (GitHub Discussions)">
				<MessageSquare size={13} /> 토론
			</button>
			{#if bundle}
				<span class="meta">항목 {rows.length} · 전체 기간 {periods.length}</span>
				<div class="cols" title="동시 표시 기간 수 (가로 폭)">
					<Columns3 size={13} />
					{#each COL_CHOICES as n (n)}
						<button type="button" class="col-btn" class:active={cols === n} onclick={() => (cols = n)}>{n}</button>
					{/each}
				</div>
				<button type="button" class="fs-btn" onclick={() => (isFullscreen = !isFullscreen)} title={isFullscreen ? '전체보기 해제 (Esc)' : '전체보기'}>
					{#if isFullscreen}<Minimize2 size={13} /> 복귀{:else}<Maximize2 size={13} /> 전체{/if}
				</button>
			{/if}
		</div>
	</header>

	{#if bundle && !loading}
		<div class="ribbon-bar">
			<TimelineRibbon {periods} {windowPeriods} onpick={pickPeriod} onnewer={moveNewer} onolder={moveOlder} {canNewer} {canOlder} />
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
				<PanelTocTree toc={bundle.toc} {activeSectionKey} onpick={pickSection} />
			</aside>
			<section class="board">
				<PanelMatrix {rows} periods={windowPeriods} dartUrlByPeriod={dartUrls} />
			</section>
		</div>
	{/if}
</main>

<GiscusPanel {code} {corpName} open={discussOpen} onclose={() => (discussOpen = false)} />

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
