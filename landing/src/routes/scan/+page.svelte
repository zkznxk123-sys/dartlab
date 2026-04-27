<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import Header from '$lib/components/sections/Header.svelte';
	import FreshnessBadge from '$lib/components/industry/FreshnessBadge.svelte';
	import Grid from '$lib/scan/Grid.svelte';
	import ColumnGroupBar from '$lib/scan/ColumnGroupBar.svelte';
	import PresetModal from '$lib/scan/PresetModal.svelte';
	import CellTooltip from '$lib/scan/CellTooltip.svelte';
	import Distribution from '$lib/scan/Distribution.svelte';
	import Detail from '$lib/scan/Detail.svelte';
	import SavedSets from '$lib/scan/SavedSets.svelte';
	import { encodeScanPayload, decodeScanPayload } from '$lib/scan/url';
	import type { SavedColumnSet } from '$lib/scan/types';
	import { DEFAULT_COLUMNS, METRICS_BY_KEY, PINNED_COLUMNS } from '$lib/scan/metrics';
	import type { ScanNode, FilterCond, SortKey } from '$lib/scan/types';
	import type { Preset } from '$lib/scan/presets';
	import { PRESETS_BY_ID } from '$lib/scan/presets';
	import {
		loadPriceMetrics,
		loadValuation,
		loadChanges,
		type PriceMetrics,
		type ValuationMetrics,
		type ChangeMetrics,
		type DbState
	} from '$lib/scan/duckSql';
	import type { DartDb } from '$lib/data/duckdb';

	let { data } = $props();

	// ── State ──────────────────────────────────────────
	let baseNodes = $derived((data.ecosystem?.nodes || []) as ScanNode[]);
	let industries = $derived(
		(data.ecosystem?.industries || []) as Array<{
			id: string;
			name: string;
			color: string;
			count: number;
		}>
	);

	let activeColumns = $state<string[]>([...DEFAULT_COLUMNS]);
	let sort = $state<SortKey | null>({ key: 'marketCap', dir: 'desc' });
	let conds = $state<FilterCond[]>([]);
	let selectedIndustries = $state<Set<string>>(new Set());
	let selectedRow = $state<string | null>(null);
	let searchQuery = $state('');
	let presetOpen = $state(false);
	let activePresetId = $state<string | null>(null);

	// ── DuckDB lifecycle ──────────────────────────────
	let dbState = $state<DbState>('idle');
	let dbError = $state<string | null>(null);
	let dartDb = $state<DartDb | null>(null);
	let priceMap = $state<Map<string, PriceMetrics>>(new Map());
	let valuationMap = $state<Map<string, ValuationMetrics>>(new Map());
	let changesMap = $state<Map<string, ChangeMetrics>>(new Map());

	// ── Cell hover tooltip ────────────────────────────
	let cellHover = $state<{
		stockCode: string;
		label: string;
		metricKey: string;
		formattedValue: string;
		spark: number[];
		x: number;
		y: number;
	} | null>(null);

	// ── Distribution panel: bin highlight (양방향) ────
	let highlightBin = $state<{ x0: number; x1: number } | null>(null);

	// ── Merge ecosystem with parquet maps ─────────────
	let allNodes = $derived.by(() => {
		if (priceMap.size === 0 && valuationMap.size === 0 && changesMap.size === 0) {
			return baseNodes;
		}
		return baseNodes.map((n) => {
			const p = priceMap.get(n.id);
			const val = valuationMap.get(n.id);
			const chg = changesMap.get(n.id);
			return {
				...n,
				// price (KRX)
				currentPrice: p?.currentPrice ?? null,
				return1m: p?.return1m ?? null,
				return3m: p?.return3m ?? null,
				return1y: p?.return1y ?? null,
				volatility1y: p?.volatility1y ?? null,
				week52High: p?.week52High ?? null,
				week52Low: p?.week52Low ?? null,
				volumeAvg30d: p?.volumeAvg30d ?? null,
				spark: p?.spark ?? [],
				// valuation (Naver) — marketCap 우선 valuation, fallback KRX
				marketCap: val?.marketCap ?? p?.marketCap ?? null,
				per: val?.per ?? null,
				pbr: val?.pbr ?? null,
				dividendYield: val?.dividendYield ?? null,
				// changes
				numericChanges1y: chg?.numericChanges1y ?? null,
				structuralChanges1y: chg?.structuralChanges1y ?? null
			} as ScanNode;
		});
	});

	// ── Filter / sort ──────────────────────────────────
	function evalCond(node: ScanNode, c: FilterCond): boolean {
		const v = (node as any)[c.metric];
		let result: boolean;
		if (c.op === 'between') {
			const a = typeof c.value === 'number' ? c.value : Number(c.value);
			const b = typeof c.value2 === 'number' ? c.value2 : Number(c.value2);
			const num = typeof v === 'number' ? v : Number(v);
			result = !Number.isNaN(num) && num >= a && num <= b;
		} else {
			const expected = c.value;
			if (c.op === '==') result = v == expected;
			else if (c.op === '!=') result = v != expected;
			else {
				const num = typeof v === 'number' ? v : Number(v);
				const target = typeof expected === 'number' ? expected : Number(expected);
				if (Number.isNaN(num) || Number.isNaN(target)) result = false;
				else if (c.op === '>=') result = num >= target;
				else if (c.op === '<=') result = num <= target;
				else result = false;
			}
		}
		return c.negate ? !result : result;
	}

	let filteredNodes = $derived.by(() => {
		const q = searchQuery.trim().toLowerCase();
		return allNodes.filter((node) => {
			if (selectedIndustries.size > 0 && !selectedIndustries.has(node.industry as string)) {
				return false;
			}
			if (q) {
				const lblOk = node.label.toLowerCase().includes(q);
				const codeOk = node.id.includes(q);
				const indOk = (node.industryName as string)?.toLowerCase().includes(q);
				if (!lblOk && !codeOk && !indOk) return false;
			}
			for (const c of conds) {
				if (!evalCond(node, c)) return false;
			}
			return true;
		});
	});

	let sortedNodes = $derived.by(() => {
		const list = filteredNodes.slice();
		if (sort) {
			const key = sort.key;
			const dir = sort.dir === 'asc' ? 1 : -1;
			list.sort((a, b) => {
				const va = (a as any)[key];
				const vb = (b as any)[key];
				if (va == null && vb == null) return 0;
				if (va == null) return 1;
				if (vb == null) return -1;
				if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir;
				return String(va).localeCompare(String(vb), 'ko-KR') * dir;
			});
		}
		return list;
	});

	// ── Industry chip bar ──────────────────────────────
	function toggleIndustry(id: string) {
		const next = new Set(selectedIndustries);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedIndustries = next;
	}

	function clearFilters() {
		conds = [];
		selectedIndustries = new Set();
		searchQuery = '';
		activePresetId = null;
	}

	// ── Preset ─────────────────────────────────────────
	function applyPreset(p: Preset) {
		conds = [...p.conds];
		if (p.sorts.length > 0) sort = p.sorts[0];
		if (p.cols && p.cols.length > 0) {
			const next = new Set(activeColumns);
			for (const c of p.cols) next.add(c);
			activeColumns = Array.from(next);
		}
		activePresetId = p.id;
		selectedIndustries = new Set();
	}

	// ── onMount: URL ?q= 우선, ?preset= fallback, then DuckDB ─
	onMount(() => {
		const url = new URL(page.url);
		const q = url.searchParams.get('q');
		const presetId = url.searchParams.get('preset');
		if (q) {
			const payload = decodeScanPayload(q);
			if (payload) {
				selectedIndustries = new Set(payload.i);
				conds = payload.c;
				if (payload.s.length > 0) sort = payload.s[0];
				if (payload.cols.length > 0) {
					// PINNED 항상 보존 + payload cols
					const pinned = PINNED_COLUMNS;
					const rest = payload.cols.filter((k) => !pinned.includes(k));
					activeColumns = [...pinned, ...rest];
				}
				if (payload.p) activePresetId = payload.p;
				if (payload.sel) selectedRow = payload.sel;
			}
		} else if (presetId) {
			const preset = PRESETS_BY_ID.get(presetId);
			if (preset) applyPreset(preset);
		}
		void bootDuckDb();
	});

	// ── URL share encode (현재 상태 → ?q=) ────────────
	let shareUrl = $derived.by(() => {
		const payload = {
			v: 2 as const,
			i: Array.from(selectedIndustries),
			c: conds,
			s: sort ? [sort] : [],
			cols: activeColumns,
			p: activePresetId ?? undefined,
			sel: selectedRow ?? undefined
		};
		const q = encodeScanPayload(payload);
		if (typeof window === 'undefined') return '';
		const url = new URL(window.location.href);
		url.searchParams.set('q', q);
		url.searchParams.delete('preset');
		return url.toString();
	});

	function loadSavedSet(s: SavedColumnSet) {
		const pinned = PINNED_COLUMNS;
		const rest = s.cols.filter((k) => !pinned.includes(k));
		activeColumns = [...pinned, ...rest];
		conds = s.conds.slice();
		if (s.sort.length > 0) sort = s.sort[0];
		activePresetId = null;
	}

	async function bootDuckDb() {
		dbState = 'loading';
		const result = await loadPriceMetrics();
		if (result.error) dbError = result.error;
		dbState = result.state;
		if (result.metrics.size > 0) priceMap = result.metrics;
		if (result.db) {
			dartDb = result.db;
			// 백그라운드 비차단 — 가격 query 가 끝났으니 valuation/changes 는 둘이 병렬로 OK
			void loadValuation(result.db).then((m) => {
				if (m.size > 0) valuationMap = m;
			});
			void loadChanges(result.db).then((m) => {
				if (m.size > 0) changesMap = m;
			});
		}
	}

	// ── Column toggle ─────────────────────────────────
	function handleColumnsChange(next: string[]) {
		// PINNED 는 항상 맨 앞 + 보존
		const pinned = activeColumns.filter((k) => PINNED_COLUMNS.includes(k));
		const rest = next.filter((k) => !PINNED_COLUMNS.includes(k));
		activeColumns = [...pinned, ...rest];
	}

	// ── Sort handler ──────────────────────────────────
	function handleSort(s: SortKey) {
		sort = s;
	}

	function handleSelect(id: string) {
		selectedRow = selectedRow === id ? null : id;
	}

	function handleCellHover(info: typeof cellHover) {
		cellHover = info;
	}

	// ── Industry list (display order: 회사 수 내림) ────
	let industryDisplay = $derived(
		industries
			.map((i) => ({ id: i.id, name: i.name, color: i.color, count: i.count }))
			.sort((a, b) => b.count - a.count)
	);
</script>

<svelte:head>
	<title>Scan Studio — 횡단조회 판떼기 | 전자공시 dartlab</title>
	<meta
		name="description"
		content="dartlab 의 회사 2,664 사를 한 화면 그리드로. 매출·영업이익률·ROE·부채·등급 + DuckDB-WASM 으로 HF parquet 직접 query."
	/>
</svelte:head>

<Header context="landing" />

<main class="scan-page">
	<!-- Page header strip -->
	<header class="page-head">
		<div class="page-head-left">
			<h1 class="page-title">Scan Studio</h1>
			<span class="page-sub">횡단조회 판떼기 — 회사 {allNodes.length.toLocaleString('ko-KR')} 사</span>
		</div>
		<div class="page-head-right">
			<span class="db-badge db-{dbState}" title={dbError ?? ''}>
				{#if dbState === 'idle' || dbState === 'loading'}
					<span class="db-dot"></span> 가격·재무비율 로드 중
				{:else if dbState === 'ready'}
					<span class="db-dot"></span> 전체 데이터 활성
				{:else if dbState === 'unsupported'}
					<span class="db-dot"></span> 모바일 — 가격·비율 비활성
				{:else if dbState === 'error'}
					<span class="db-dot"></span> 데이터 로드 실패
				{/if}
			</span>
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="회사명 / 종목코드 / 산업"
				class="search-input"
				aria-label="검색"
			/>
			<button type="button" class="cmdk-btn" onclick={() => (presetOpen = true)} aria-label="프리셋 모달 열기">
				<span>⌘K</span>
				<span class="cmdk-lbl">프리셋</span>
			</button>
			<SavedSets cols={activeColumns} {conds} {sort} {shareUrl} onLoad={loadSavedSet} />
			{#if data.meta?.dataAsOf}
				<FreshnessBadge dataAsOf={data.meta.dataAsOf} variant="compact" />
			{/if}
		</div>
	</header>

	<!-- Industry chip bar -->
	<div class="industry-bar" role="group" aria-label="산업 필터">
		{#if selectedIndustries.size > 0 || conds.length > 0 || searchQuery}
			<button class="clear-btn" type="button" onclick={clearFilters} title="모든 필터 해제">
				✕ 초기화
			</button>
		{/if}
		<div class="industry-chips">
			{#each industryDisplay as ind (ind.id)}
				<button
					type="button"
					class="ind-chip"
					class:active={selectedIndustries.has(ind.id)}
					onclick={() => toggleIndustry(ind.id)}
					title="{ind.name} ({ind.count}사)"
				>
					<span class="ind-chip-dot" style:background={ind.color}></span>
					<span class="ind-chip-name">{ind.name}</span>
					<span class="ind-chip-count">{ind.count}</span>
				</button>
			{/each}
		</div>
	</div>

	<!-- Active preset chip -->
	{#if activePresetId}
		{@const p = PRESETS_BY_ID.get(activePresetId)}
		{#if p}
			<div class="active-preset">
				<span class="ap-label">활성 프리셋</span>
				<span class="ap-title">{p.title}</span>
				<span class="ap-sub">{p.subtitle}</span>
				<button type="button" class="ap-x" onclick={clearFilters} aria-label="프리셋 해제">✕</button>
			</div>
		{/if}
	{/if}

	<!-- Column group toggle -->
	<ColumnGroupBar activeColumns={activeColumns} onToggle={handleColumnsChange} />

	<!-- Main grid + side panels -->
	<div class="studio">
		<div class="grid-area">
			<Grid
				nodes={sortedNodes}
				columns={activeColumns}
				{sort}
				selectedId={selectedRow}
				onSort={handleSort}
				onSelect={handleSelect}
				onCellHover={handleCellHover}
			/>
		</div>
		<aside class="distribution-area" aria-label="분포 패널">
			{#if sort && METRICS_BY_KEY[sort.key]?.type === 'number'}
				<Distribution
					nodes={allNodes}
					filteredNodes={sortedNodes}
					metricKey={sort.key}
					{highlightBin}
					onBinHover={(b) => (highlightBin = b)}
				/>
			{:else}
				<div class="placeholder">
					<div class="ph-title">분포 패널</div>
					<div class="ph-desc">숫자 컬럼으로 정렬하면 분포가 표시됩니다.</div>
				</div>
			{/if}
		</aside>
	</div>

	<!-- Detail panel -->
	{#if selectedRow}
		{@const node = allNodes.find((n) => n.id === selectedRow)}
		{#if node}
			<Detail {node} db={dartDb} onClose={() => (selectedRow = null)} />
		{/if}
	{/if}

	<PresetModal bind:open={presetOpen} nodes={allNodes} onClose={() => (presetOpen = false)} onApplyPreset={applyPreset} />

	{#if cellHover}
		<CellTooltip
			stockCode={cellHover.stockCode}
			label={cellHover.label}
			metricKey={cellHover.metricKey}
			formattedValue={cellHover.formattedValue}
			spark={cellHover.spark}
			x={cellHover.x}
			y={cellHover.y}
		/>
	{/if}
</main>

<style>
	.scan-page {
		max-width: 100%;
		padding: 16px 20px 20px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		min-height: calc(100vh - 64px);
	}

	.page-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 16px;
		flex-wrap: wrap;
	}
	.page-head-left {
		display: flex;
		align-items: baseline;
		gap: 12px;
	}
	.page-title {
		font-size: 18px;
		font-weight: 700;
		color: #f1f5f9;
		letter-spacing: -0.02em;
		margin: 0;
	}
	.page-sub {
		font-size: 12px;
		color: #64748b;
		font-family: monospace;
	}
	.page-head-right {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.search-input {
		width: 260px;
		padding: 7px 12px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 5px;
		color: #f1f5f9;
		font-size: 12px;
		font-family: inherit;
	}
	.db-badge {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		font-size: 10px;
		font-family: monospace;
		border: 1px solid #1e2433;
		border-radius: 4px;
		color: #94a3b8;
		background: #050811;
		white-space: nowrap;
	}
	.db-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
	}
	.db-idle, .db-loading { color: #fbbf24; }
	.db-loading .db-dot {
		animation: pulse 1.4s ease-in-out infinite;
	}
	.db-ready { color: #22c55e; border-color: rgba(34, 197, 94, 0.3); }
	.db-unsupported { color: #94a3b8; }
	.db-error { color: #ef4444; border-color: rgba(239, 68, 68, 0.3); }
	@keyframes pulse {
		0%, 100% { opacity: 0.3; }
		50% { opacity: 1; }
	}
	.search-input:focus {
		outline: none;
		border-color: #fb923c;
	}
	.cmdk-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		background: #050811;
		border: 1px solid #334155;
		border-radius: 5px;
		color: #cbd5e1;
		font-size: 12px;
		cursor: pointer;
		font-family: inherit;
	}
	.cmdk-btn:hover {
		border-color: #fb923c;
		color: #fb923c;
	}
	.cmdk-btn span:first-child {
		font-family: monospace;
		font-size: 10px;
		padding: 1px 5px;
		background: #1e2433;
		border-radius: 3px;
	}
	.cmdk-lbl {
		font-weight: 500;
	}

	.industry-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 0;
	}
	.clear-btn {
		flex-shrink: 0;
		padding: 4px 10px;
		font-size: 11px;
		color: #fb923c;
		background: rgba(251, 146, 60, 0.08);
		border: 1px solid rgba(251, 146, 60, 0.3);
		border-radius: 4px;
		cursor: pointer;
		font-family: inherit;
	}
	.industry-chips {
		display: flex;
		gap: 4px;
		overflow-x: auto;
		padding-bottom: 4px;
		scrollbar-width: thin;
	}
	.ind-chip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 4px 9px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 4px;
		color: #94a3b8;
		font-size: 11px;
		cursor: pointer;
		flex-shrink: 0;
		font-family: inherit;
	}
	.ind-chip:hover {
		border-color: #334155;
		color: #cbd5e1;
	}
	.ind-chip.active {
		background: rgba(251, 146, 60, 0.08);
		border-color: rgba(251, 146, 60, 0.5);
		color: #f1f5f9;
	}
	.ind-chip-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.ind-chip-count {
		font-family: monospace;
		font-size: 9px;
		color: #475569;
	}
	.ind-chip.active .ind-chip-count {
		color: #fb923c;
	}

	.active-preset {
		display: inline-flex;
		align-items: baseline;
		gap: 8px;
		padding: 8px 12px;
		background: linear-gradient(135deg, rgba(234, 70, 71, 0.08), rgba(251, 146, 60, 0.04));
		border: 1px solid rgba(234, 70, 71, 0.3);
		border-radius: 5px;
		font-size: 11px;
	}
	.ap-label {
		color: #94a3b8;
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.ap-title {
		color: #f1f5f9;
		font-weight: 600;
		font-size: 12px;
	}
	.ap-sub {
		color: #fb923c;
		font-family: monospace;
	}
	.ap-x {
		margin-left: 8px;
		background: transparent;
		border: none;
		color: #64748b;
		cursor: pointer;
		font-size: 11px;
	}
	.ap-x:hover {
		color: #fb923c;
	}

	.studio {
		flex: 1;
		min-height: 0;
		display: grid;
		grid-template-columns: 1fr 320px;
		gap: 10px;
	}
	.grid-area {
		min-width: 0;
		min-height: 0;
		display: flex;
		flex-direction: column;
	}
	.distribution-area {
		min-width: 0;
		min-height: 0;
	}
	.placeholder {
		height: 100%;
		display: flex;
		flex-direction: column;
		gap: 6px;
		justify-content: center;
		align-items: center;
		padding: 24px;
		background: #050811;
		border: 1px dashed #1e2433;
		border-radius: 6px;
		color: #475569;
		text-align: center;
	}
	.ph-title {
		font-size: 13px;
		font-weight: 600;
		color: #94a3b8;
	}
	.ph-desc {
		font-size: 11px;
		color: #64748b;
		line-height: 1.5;
	}
	.ph-current {
		font-size: 11px;
		color: #fb923c;
		font-family: monospace;
		margin-top: 4px;
	}

	.detail-panel {
		flex-shrink: 0;
		background: #0a0e18;
		border: 1px solid #1e2433;
		border-radius: 6px;
		overflow: hidden;
	}
	.detail-head {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		background: #0f172a;
		border-bottom: 1px solid #1e2433;
	}
	.d-label {
		font-size: 14px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.d-id {
		font-size: 11px;
		font-family: monospace;
		color: #64748b;
	}
	.d-ind {
		font-size: 11px;
		color: #94a3b8;
	}
	.d-cta {
		margin-left: auto;
		padding: 4px 10px;
		font-size: 11px;
		color: #fb923c;
		background: rgba(251, 146, 60, 0.08);
		border: 1px solid rgba(251, 146, 60, 0.3);
		border-radius: 4px;
		text-decoration: none;
		font-weight: 500;
	}
	.d-cta:hover {
		background: rgba(251, 146, 60, 0.16);
		color: #f1f5f9;
	}
	.d-close {
		background: transparent;
		border: none;
		color: #64748b;
		cursor: pointer;
		font-size: 14px;
		padding: 4px 6px;
	}
	.d-close:hover {
		color: #fb923c;
	}
	.detail-body {
		padding: 24px;
		text-align: center;
	}

	@media (max-width: 1024px) {
		.studio {
			grid-template-columns: 1fr;
		}
		.distribution-area {
			display: none;
		}
	}
</style>
