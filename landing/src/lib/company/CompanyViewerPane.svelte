<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { Columns3 } from 'lucide-svelte';
	import { loadPanelBundle } from '$lib/viewer/panelLoad';
	import PanelTocTree from '$lib/components/viewer/PanelTocTree.svelte';
	import PanelMatrix from '$lib/components/viewer/PanelMatrix.svelte';
	import TimelineRibbon from '$lib/components/viewer/TimelineRibbon.svelte';
	import CommandPalette from '$lib/components/viewer/CommandPalette.svelte';
	import { loadCompanies } from '$lib/viewer/companyNames';
	import { buildIndexChunked, type SearchHit, type SearchIndex } from '$lib/viewer/searchIndex';
	import type { PanelBundle } from '$lib/viewer/types';

	let { code, corpName = '' }: { code: string; corpName?: string } = $props();

	const COL_CHOICES = [3, 6, 9] as const;

	let nameMap = $state<Map<string, string>>(new Map());
	let bundle = $state<PanelBundle | null>(null);
	let errorMsg = $state<string | null>(null);
	let loading = $state(true);
	let activeSectionKey = $state<string | undefined>(undefined);
	let activeBlock = $state<string | null>(null);
	let windowEnd = $state(0);
	let cols = $state(3);
	let annualOnly = $state(false);
	let searchIndex = $state<SearchIndex | null>(null);
	let indexing = $state(false);
	let glowCell = $state<{ rowIndex: number; period: string } | null>(null);

	onMount(() => {
		void loadCompanies().then((companies) => (nameMap = new Map(companies.map((item) => [item.code, item.name]))));
	});

	$effect(() => {
		const c = code;
		loading = true;
		errorMsg = null;
		bundle = null;
		windowEnd = 0;
		activeBlock = null;
		void loadPanelBundle(c)
			.then((next) => {
				if (code !== c) return;
				bundle = next;
				activeSectionKey = next.toc.chapters[0]?.sections[0]?.sectionKey;
				if (!next.periods.length) errorMsg = '이 종목의 panel 데이터가 없습니다.';
			})
			.catch((error) => {
				if (code === c) errorMsg = `로드 실패: ${error instanceof Error ? error.message : String(error)}`;
			})
			.finally(() => {
				if (code === c) loading = false;
			});
	});

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

	const periods = $derived(bundle?.periods ?? []);
	const annualPeriods = $derived.by(() => (bundle ? periods.filter((p) => bundle?.periodKind[p] === 'annual') : []));
	const visiblePeriods = $derived(annualOnly && annualPeriods.length ? annualPeriods : periods);
	const windowPeriods = $derived(visiblePeriods.slice(windowEnd, windowEnd + cols));
	const rows = $derived.by(() => {
		if (!activeSectionKey || !bundle) return [];
		const baseRows = bundle.gridBySection.get(activeSectionKey) ?? [];
		return activeBlock ? baseRows.filter((row) => row.blockLeaf === activeBlock) : baseRows;
	});
	const dartUrls = $derived(bundle?.dartUrlByPeriod ?? {});
	const displayName = $derived(corpName || bundle?.corpName || nameMap.get(code) || code);
	const sectionLabel = $derived.by(() => {
		const section = activeSectionKey?.split('␟').pop() ?? '';
		return activeBlock ? `${section} · ${activeBlock}` : section;
	});
	const canNewer = $derived(windowEnd > 0);
	const canOlder = $derived(windowEnd + 1 < visiblePeriods.length);

	function onSearchResult(hit: SearchHit) {
		pickSection(hit.sectionKey);
		pickPeriod(hit.period);
		glowCell = { rowIndex: hit.rowIndex, period: hit.period };
		window.setTimeout(() => (glowCell = null), 2200);
	}

	function pickSection(sectionKey: string) {
		activeSectionKey = sectionKey;
		activeBlock = null;
	}

	function pickBlock(sectionKey: string, blockLeaf: string) {
		activeSectionKey = sectionKey;
		activeBlock = blockLeaf;
	}

	function pickPeriod(period: string) {
		const idx = visiblePeriods.indexOf(period);
		if (idx >= 0) windowEnd = idx;
	}

	function moveNewer() {
		windowEnd = Math.max(0, windowEnd - 1);
	}

	function moveOlder() {
		windowEnd = Math.min(visiblePeriods.length - 1, windowEnd + 1);
	}

	function toggleAnnual() {
		annualOnly = !annualOnly;
		windowEnd = 0;
	}
</script>

<section class="viewer-pane" aria-label="공시뷰어">
	<header class="vp-head">
		<div class="vp-left">
			<strong>{displayName}</strong>
			<span>{code}</span>
			{#if sectionLabel}<em>{sectionLabel}</em>{/if}
		</div>
		<div class="vp-right">
			<CommandPalette index={searchIndex} toc={bundle?.toc ?? null} {indexing} onResult={onSearchResult} onSection={pickSection} />
			{#if bundle}
				<span class="meta">항목 {rows.length} · 기간 {visiblePeriods.length}{annualOnly ? '(연간)' : ''}</span>
				<button type="button" class="ctrl" class:active={annualOnly} onclick={toggleAnnual}>연간만</button>
				<div class="cols" title="동시 표시 기간 수">
					<Columns3 size={13} />
					{#each COL_CHOICES as n (n)}
						<button type="button" class="col-btn" class:active={cols === n} onclick={() => (cols = n)}>{n}</button>
					{/each}
				</div>
				<a class="ctrl link" href={`${base}/viewer/company/${code}`} target="_blank" rel="noreferrer">전체보기 ↗</a>
			{/if}
		</div>
	</header>

	{#if bundle && !loading}
		<div class="ribbon-bar">
			<TimelineRibbon periods={visiblePeriods} {windowPeriods} onpick={pickPeriod} onnewer={moveNewer} onolder={moveOlder} {canNewer} {canOlder} />
		</div>
	{/if}

	{#if loading}
		<div class="state"><div class="spinner"></div><p>{displayName} 공시 본문을 여는 중</p></div>
	{:else if errorMsg}
		<div class="state"><p>{errorMsg}</p></div>
	{:else if bundle}
		<div class="studio">
			<aside class="toc">
				<PanelTocTree toc={bundle.toc} {activeSectionKey} {activeBlock} onpick={pickSection} onpickBlock={pickBlock} />
			</aside>
			<section class="board">
				<PanelMatrix {rows} periods={windowPeriods} dartUrlByPeriod={dartUrls} glow={glowCell} />
			</section>
		</div>
	{/if}
</section>

<style>
	.viewer-pane {
		height: 100%;
		min-height: 0;
		display: flex;
		flex-direction: column;
		background: #050811;
		color: #f1f5f9;
		border: 1px solid #1e2433;
		border-radius: 8px;
		overflow: hidden;
	}
	.vp-head {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 14px;
		padding: 8px 10px;
		border-bottom: 1px solid #1e2433;
	}
	.vp-left,
	.vp-right {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.vp-left strong {
		font-size: 14px;
		font-weight: 800;
		white-space: nowrap;
	}
	.vp-left span {
		color: #64748b;
		font-family: monospace;
		font-size: 11px;
	}
	.vp-left em {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: #94a3b8;
		font-size: 12px;
		font-style: normal;
	}
	.vp-left em::before {
		content: '·';
		margin-right: 6px;
		color: #475569;
	}
	.vp-right {
		flex-shrink: 0;
	}
	.meta {
		color: #94a3b8;
		font-size: 11px;
		white-space: nowrap;
	}
	.ctrl {
		display: inline-flex;
		align-items: center;
		height: 30px;
		padding: 0 9px;
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #050811;
		color: #94a3b8;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
		text-decoration: none;
		white-space: nowrap;
	}
	.ctrl:hover,
	.ctrl.active {
		border-color: rgba(251, 146, 60, 0.5);
		color: #fb923c;
		background: rgba(251, 146, 60, 0.1);
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
	.col-btn.active {
		background: rgba(251, 146, 60, 0.14);
		color: #fb923c;
	}
	.ribbon-bar {
		flex-shrink: 0;
		padding: 6px 10px;
		border-bottom: 1px solid #1e2433;
	}
	.studio {
		flex: 1 1 auto;
		min-height: 0;
		display: grid;
		grid-template-columns: 220px 1fr;
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
	.state {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		color: #94a3b8;
		text-align: center;
	}
	.spinner {
		width: 26px;
		height: 26px;
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
	@media (max-width: 980px) {
		.vp-head {
			align-items: flex-start;
			flex-direction: column;
		}
		.vp-right {
			flex-wrap: wrap;
		}
		.studio {
			grid-template-columns: 1fr;
		}
		.toc {
			max-height: 160px;
			border-right: none;
			border-bottom: 1px solid #1e2433;
		}
	}
</style>
