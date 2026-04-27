<script lang="ts">
	/**
	 * Scan Studio 메인 그리드 — 가상 스크롤.
	 *
	 * 2,664 row × N 컬럼을 한 화면에. 자체 구현 가상 스크롤 (~120 LOC core)
	 * — 단축 axis 수직, 고정 row height, sticky 첫 2 컬럼.
	 *
	 * 책임:
	 *  - 헤더 클릭 = 정렬 토글 (1차 정렬)
	 *  - 헤더 hover = HeaderTooltip (메트릭 정의)
	 *  - 행 click = onSelect (Detail 패널 — PR-D)
	 *  - 회사명 click = /dashboard/[id] 진입
	 *  - 행 색 = qualGrade 톤 (subtle 6%)
	 *  - 등급 셀 = 색칩
	 *  - placeholder = `—`
	 */
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import HeaderTooltip from './HeaderTooltip.svelte';
	import Sparkline from '$lib/components/ui/Sparkline.svelte';
	import { METRICS_BY_KEY, PINNED_COLUMNS } from './metrics';
	import type { ScanNode, SortKey } from './types';
	import { gradeTone, rowTintColor, toneColor } from './grade';
	import { marketColor, marketLabel, normalizeMarket } from './marketChip';

	interface CellHoverInfo {
		stockCode: string;
		label: string;
		metricKey: string;
		formattedValue: string;
		spark: number[];
		x: number;
		y: number;
	}

	interface Percentile {
		p10: number;
		p90: number;
		higherBetter?: boolean;
	}

	interface Props {
		nodes: ScanNode[] | Record<string, unknown>[];
		columns: string[];
		sort: SortKey | null;
		percentiles?: Map<string, Percentile>;
		selectedId: string | null;
		/** 'screener' = 메인 그리드 (heatmap·hover·등급칩 활성)
		 *  'table'   = 단순 raw 테이블 (모달 내 — 모두 비활성, 동적 컬럼 width) */
		mode?: 'screener' | 'table';
		/** stockCode → 'KOSPI'/'KOSDAQ'/'KONEX' 같은 market 라벨. 노드 자체 market 없을 때 fallback. */
		markets?: Record<string, string>;
		onSort: (s: SortKey) => void;
		onSelect: (id: string) => void;
		onCellHover?: (info: CellHoverInfo | null) => void;
	}

	let {
		nodes,
		columns,
		sort,
		percentiles,
		selectedId,
		mode = 'screener',
		markets,
		onSort,
		onSelect,
		onCellHover
	}: Props = $props();

	function rowMarket(rd: Record<string, unknown>, id: string): unknown {
		const m = (rd as any).market;
		if (m) return m;
		if (markets && id) return markets[id];
		return undefined;
	}
	let isTable = $derived(mode === 'table');

	/** 셀 분위 배경색 — p10 이하 / p90 이상 강조 (subtle 12%). */
	function cellHeatmapBg(key: string, v: unknown): string {
		if (typeof v !== 'number' || !Number.isFinite(v)) return 'transparent';
		const p = percentiles?.get(key);
		if (!p || p.p90 <= p.p10) return 'transparent';
		const ratio = Math.max(0, Math.min(1, (v - p.p10) / (p.p90 - p.p10)));
		const inverted = p.higherBetter === false;
		// 0~1 ratio. higherBetter true: 1 = good 녹, 0 = bad 적. inverted 면 반전.
		let color = '';
		let strength = 0;
		if (ratio >= 0.7) {
			strength = (ratio - 0.7) / 0.3;
			color = inverted ? '#ef4444' : '#22c55e';
		} else if (ratio <= 0.3) {
			strength = (0.3 - ratio) / 0.3;
			color = inverted ? '#22c55e' : '#ef4444';
		}
		if (strength === 0) return 'transparent';
		const pct = Math.round(strength * 14);
		return `color-mix(in srgb, ${color} ${pct}%, transparent)`;
	}

	const ROW_H = 36;
	const OVERSCAN = 6;

	let viewport: HTMLDivElement | undefined = $state(undefined);
	let viewportH = $state(800);
	let scrollTop = $state(0);

	$effect(() => {
		if (!viewport) return;
		const ro = new ResizeObserver((entries) => {
			for (const e of entries) {
				viewportH = e.contentRect.height;
			}
		});
		ro.observe(viewport);
		viewportH = viewport.clientHeight;
		return () => ro.disconnect();
	});

	let totalRows = $derived(nodes.length);
	let visibleCount = $derived(Math.ceil(viewportH / ROW_H) + OVERSCAN * 2);
	let startIdx = $derived(Math.max(0, Math.floor(scrollTop / ROW_H) - OVERSCAN));
	let endIdx = $derived(Math.min(totalRows, startIdx + visibleCount));
	let visibleRows = $derived(nodes.slice(startIdx, endIdx));
	let topPad = $derived(startIdx * ROW_H);
	let bottomPad = $derived((totalRows - endIdx) * ROW_H);

	function handleScroll(e: Event) {
		scrollTop = (e.target as HTMLDivElement).scrollTop;
	}

	function handleSortClick(key: string) {
		const cur = sort;
		if (cur && cur.key === key) {
			onSort({ key, dir: cur.dir === 'asc' ? 'desc' : 'asc' });
		} else {
			const def = METRICS_BY_KEY[key];
			onSort({ key, dir: def?.higherBetter === false ? 'asc' : 'desc' });
		}
	}

	function handleCompanyClick(e: MouseEvent, id: string) {
		e.stopPropagation();
		goto(`${base}/dashboard/${id}`);
	}

	type RowData = Record<string, unknown>;

	function cellValue(node: RowData, key: string): unknown {
		return node[key];
	}

	function rowId(node: RowData, idx: number): string {
		const id = node['id'];
		return typeof id === 'string' ? id : String(idx);
	}

	function rowLabel(node: RowData): string {
		const lbl = node['label'];
		return typeof lbl === 'string' ? lbl : '';
	}

	function rowColor(node: RowData): string {
		const c = node['color'];
		return typeof c === 'string' ? c : '#475569';
	}

	function rowQualGrade(node: RowData): unknown {
		return node['qualGrade'];
	}

	function isPinned(key: string): boolean {
		return PINNED_COLUMNS.includes(key);
	}

	function colWidth(key: string): number {
		const def = METRICS_BY_KEY[key];
		if (key === 'label') return 180;
		if (key === 'industryName') return 130;
		if (key === 'spark') return 110;
		if (!def) return 110;
		if (def.type === 'enum' || def.type === 'text') return 110;
		return 110;
	}

	function colWidthCss(): string {
		return columns.map((k) => `${colWidth(k)}px`).join(' ');
	}

	let stickyOffsets = $derived.by(() => {
		const offsets: Record<string, number> = {};
		let acc = 0;
		for (const k of columns) {
			if (isPinned(k)) {
				offsets[k] = acc;
				acc += colWidth(k);
			}
		}
		return offsets;
	});

	// ── Cell hover dwell ──────────────────────────────
	let hoverTimer: ReturnType<typeof setTimeout> | null = null;
	function onCellMouseEnter(e: MouseEvent, node: RowData, key: string, formatted: string) {
		if (!onCellHover) return;
		if (isPinned(key)) return;
		if (hoverTimer) clearTimeout(hoverTimer);
		const target = e.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		hoverTimer = setTimeout(() => {
			onCellHover?.({
				stockCode: rowId(node, 0),
				label: rowLabel(node),
				metricKey: key,
				formattedValue: formatted,
				spark: Array.isArray(node.spark) ? (node.spark as number[]) : [],
				x: Math.min(window.innerWidth - 260, rect.left + rect.width / 2 - 100),
				y: rect.top - 180
			});
		}, 200);
	}
	function onCellMouseLeave() {
		if (hoverTimer) clearTimeout(hoverTimer);
		hoverTimer = null;
		onCellHover?.(null);
	}
</script>

<div class="grid-wrap">
	<!-- viewport (scrollable) — header 도 안에 두고 sticky-top 처리 -->
	<div
		class="viewport"
		bind:this={viewport}
		onscroll={handleScroll}
		role="grid"
		aria-rowcount={totalRows}
	>
		<!-- header row (sticky top + scrolls horizontally with rows) -->
		<div class="grid-header" style:grid-template-columns={colWidthCss()}>
			{#each columns as key (key)}
				{@const def = METRICS_BY_KEY[key]}
				{@const sortDir = sort && sort.key === key ? sort.dir : null}
				<div
					class="hcell"
					class:pinned={isPinned(key)}
					class:numeric={def?.type === 'number'}
					style:left={isPinned(key) ? `${stickyOffsets[key]}px` : ''}
				>
					<button
						type="button"
						class="hbtn"
						onclick={() => handleSortClick(key)}
						aria-label="{def?.label ?? key} 정렬"
					>
						<HeaderTooltip metric={def} fallbackKey={key} />
						{#if sortDir}
							<span class="sort-arr" aria-hidden="true">{sortDir === 'asc' ? '▲' : '▼'}</span>
						{/if}
					</button>
				</div>
			{/each}
		</div>
		{#if topPad > 0}<div style:height="{topPad}px" aria-hidden="true"></div>{/if}

		{#each visibleRows as node, i (rowId(node as RowData, startIdx + i))}
			{@const idx = startIdx + i}
			{@const rd = node as RowData}
			{@const id = rowId(rd, idx)}
			{@const tint = isTable ? 'transparent' : rowTintColor(rowQualGrade(rd))}
			{@const isSel = id === selectedId}
			<div
				class="row"
				class:selected={isSel}
				role="row"
				aria-rowindex={idx + 2}
				aria-selected={isSel}
				style:grid-template-columns={colWidthCss()}
				style:--row-tint={tint}
				onclick={() => onSelect(id)}
				onkeydown={(e) => {
					if (e.key === 'Enter') onSelect(id);
				}}
				tabindex="0"
			>
				{#each columns as key (key)}
					{@const def = METRICS_BY_KEY[key]}
					{@const v = cellValue(rd, key)}
					{@const formatted = def?.format
						? def.format(v)
						: v == null || v === ''
							? '—'
							: String(v)}
					{@const heatBg = !isTable && def?.type === 'number' && !isPinned(key) ? cellHeatmapBg(key, v) : 'transparent'}
					<div
						class="cell"
						class:pinned={isPinned(key)}
						class:numeric={def?.type === 'number'}
						class:enum={!isTable && def?.type === 'enum'}
						class:spark-cell={key === 'spark'}
						style:left={isPinned(key) ? `${stickyOffsets[key]}px` : ''}
						style:background={heatBg}
						role="gridcell"
						tabindex="-1"
						onmouseenter={(e) => !isTable && onCellMouseEnter(e, rd, key, formatted)}
						onmouseleave={onCellMouseLeave}
					>
						{#if key === 'label'}
							{@const rawMarket = rowMarket(rd, id)}
							{@const market = normalizeMarket(rawMarket)}
							<button
								type="button"
								class="company-link"
								onclick={(e) => handleCompanyClick(e, id)}
								title="{rowLabel(rd)} ({id}) · {marketLabel(rawMarket)}"
							>
								{#if market !== 'UNKNOWN'}
									<span
										class="market-tag market-{market.toLowerCase()}"
										style:color={marketColor(rawMarket)}
										style:border-color={marketColor(rawMarket) + '55'}
										style:background={marketColor(rawMarket) + '14'}
									>{marketLabel(rawMarket)}</span>
								{/if}
								<span class="ind-dot" style:background={rowColor(rd)}></span>
								<span class="company-name">{rowLabel(rd)}</span>
							</button>
						{:else if key === 'spark'}
							{@const sparkData = rd.spark}
							{#if Array.isArray(sparkData) && sparkData.length >= 2}
								{@const trend =
									sparkData[sparkData.length - 1] > sparkData[0] * 1.005
										? '#ef4444'
										: sparkData[sparkData.length - 1] < sparkData[0] * 0.995
											? '#3b82f6'
											: '#94a3b8'}
								<span class="spark-wrap" style:color={trend}>
									<Sparkline data={sparkData} width={88} height={24} stroke="currentColor" smooth />
								</span>
							{:else}
								<span class="dim">—</span>
							{/if}
						{:else if def?.type === 'enum'}
							{@const tone = gradeTone(key, v)}
							{#if v && v !== ''}
								<span class="chip" style:color={toneColor(tone)} style:border-color={toneColor(tone)}>
									{v}
								</span>
							{:else}
								<span class="dim">—</span>
							{/if}
						{:else if def?.format}
							<span class:dim={v == null}>{formatted}</span>
						{:else if v == null || v === ''}
							<span class="dim">—</span>
						{:else}
							<span>{formatted}</span>
						{/if}
					</div>
				{/each}
			</div>
		{/each}

		{#if bottomPad > 0}<div style:height="{bottomPad}px" aria-hidden="true"></div>{/if}

		{#if totalRows === 0}
			<div class="empty">
				<p>조건과 일치하는 회사가 없습니다.</p>
				<p class="hint">필터를 줄이거나 산업 선택을 늘려보세요.</p>
			</div>
		{/if}
	</div>

	<!-- footer count -->
	<div class="grid-footer">
		<span class="count">{totalRows.toLocaleString('ko-KR')} 사</span>
		{#if sort}
			<span class="sort-hint">정렬: {METRICS_BY_KEY[sort.key].label} ({sort.dir === 'asc' ? '오름' : '내림'})</span>
		{/if}
	</div>
</div>

<style>
	.grid-wrap {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		overflow: hidden;
	}

	.grid-header {
		display: grid;
		position: sticky;
		top: 0;
		height: 40px;
		flex-shrink: 0;
		background: #0a0e18;
		border-bottom: 1px solid #1e2433;
		z-index: 10;
	}
	.hcell {
		display: flex;
		align-items: center;
		padding: 0 10px;
		border-right: 1px solid #1e2433;
		overflow: visible;
		position: relative;
	}
	.hcell.numeric {
		justify-content: flex-end;
	}
	.hcell.pinned {
		position: sticky;
		z-index: 3;
		background: #0a0e18;
	}
	.hbtn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		background: transparent;
		border: none;
		color: inherit;
		cursor: pointer;
		padding: 0;
		font-family: inherit;
	}
	.sort-arr {
		font-size: 9px;
		color: #fb923c;
	}

	.viewport {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: auto;
		position: relative;
		contain: strict;
	}

	.row {
		display: grid;
		height: 36px;
		border-bottom: 1px solid rgba(30, 36, 51, 0.5);
		position: relative;
		cursor: pointer;
		background: color-mix(in srgb, var(--row-tint, transparent) 4%, transparent);
		transition: background 0.1s;
	}
	.row:hover {
		background: color-mix(in srgb, var(--row-tint, #94a3b8) 10%, rgba(255, 255, 255, 0.02));
	}
	.row.selected {
		background: color-mix(in srgb, var(--row-tint, #fb923c) 14%, rgba(251, 146, 60, 0.06));
	}
	.row:focus-visible {
		outline: 1px solid #fb923c;
		outline-offset: -1px;
	}

	.cell {
		display: flex;
		align-items: center;
		padding: 0 10px;
		font-size: 12px;
		color: #cbd5e1;
		border-right: 1px solid rgba(30, 36, 51, 0.4);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		font-variant-numeric: tabular-nums;
	}
	.cell.numeric {
		justify-content: flex-end;
		font-family: 'JetBrains Mono', 'Fira Code', monospace;
	}
	.cell.enum {
		justify-content: flex-start;
	}
	.cell.spark-cell {
		justify-content: center;
		padding: 0 6px;
	}
	.spark-wrap {
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}
	.cell.pinned {
		position: sticky;
		z-index: 1;
		background: inherit;
	}
	.cell.pinned::before {
		content: '';
		position: absolute;
		inset: 0;
		background: #050811;
		z-index: -1;
	}
	.row:hover .cell.pinned::before {
		background: #0b1120;
	}

	.dim {
		color: #475569;
	}

	.chip {
		display: inline-block;
		padding: 1px 7px;
		font-size: 10px;
		font-weight: 600;
		border: 1px solid currentColor;
		border-radius: 3px;
		background: transparent;
		letter-spacing: -0.01em;
	}

	.company-link {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: transparent;
		border: none;
		color: #f1f5f9;
		cursor: pointer;
		font-family: inherit;
		font-size: 12px;
		font-weight: 500;
		padding: 0;
		text-align: left;
	}
	.company-link:hover .company-name {
		color: #fb923c;
		text-decoration: underline;
	}
	.market-tag {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0 5px;
		height: 16px;
		min-width: 46px;
		border-radius: 3px;
		border: 1px solid;
		font-size: 9px;
		font-weight: 600;
		letter-spacing: 0.04em;
		flex-shrink: 0;
	}
	.ind-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.company-name {
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.empty {
		padding: 40px 20px;
		text-align: center;
		color: #64748b;
		font-size: 13px;
	}
	.empty .hint {
		font-size: 11px;
		color: #475569;
		margin-top: 6px;
	}

	.grid-footer {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 6px 12px;
		background: #0a0e18;
		border-top: 1px solid #1e2433;
		font-size: 11px;
		color: #94a3b8;
		font-family: monospace;
	}
	.count {
		color: #f1f5f9;
		font-weight: 600;
	}
	.sort-hint {
		color: #64748b;
	}
</style>
