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

	interface CellHoverInfo {
		stockCode: string;
		label: string;
		metricKey: string;
		formattedValue: string;
		spark: number[];
		x: number;
		y: number;
	}

	interface Props {
		nodes: ScanNode[];
		columns: string[];
		sort: SortKey | null;
		selectedId: string | null;
		onSort: (s: SortKey) => void;
		onSelect: (id: string) => void;
		onCellHover?: (info: CellHoverInfo | null) => void;
	}

	let { nodes, columns, sort, selectedId, onSort, onSelect, onCellHover }: Props = $props();

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

	function cellValue(node: ScanNode, key: string): unknown {
		return (node as Record<string, unknown>)[key];
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
	function onCellMouseEnter(e: MouseEvent, node: ScanNode, key: string, formatted: string) {
		if (!onCellHover) return;
		if (isPinned(key)) return;
		if (hoverTimer) clearTimeout(hoverTimer);
		const target = e.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		hoverTimer = setTimeout(() => {
			onCellHover?.({
				stockCode: node.id,
				label: node.label,
				metricKey: key,
				formattedValue: formatted,
				spark: Array.isArray((node as any).spark) ? ((node as any).spark as number[]) : [],
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
	<!-- header row (sticky) -->
	<div class="grid-header" style:grid-template-columns={colWidthCss()}>
		{#each columns as key (key)}
			{@const def = METRICS_BY_KEY[key]}
			{@const sortDir = sort && sort.key === key ? sort.dir : null}
			<div
				class="hcell"
				class:pinned={isPinned(key)}
				class:numeric={def.type === 'number'}
				style:left={isPinned(key) ? `${stickyOffsets[key]}px` : ''}
			>
				<button
					type="button"
					class="hbtn"
					onclick={() => handleSortClick(key)}
					aria-label="{def.label} 정렬"
				>
					<HeaderTooltip metric={def} />
					{#if sortDir}
						<span class="sort-arr" aria-hidden="true">{sortDir === 'asc' ? '▲' : '▼'}</span>
					{/if}
				</button>
			</div>
		{/each}
	</div>

	<!-- viewport (scrollable) -->
	<div
		class="viewport"
		bind:this={viewport}
		onscroll={handleScroll}
		role="grid"
		aria-rowcount={totalRows}
	>
		{#if topPad > 0}<div style:height="{topPad}px" aria-hidden="true"></div>{/if}

		{#each visibleRows as node, i (node.id)}
			{@const idx = startIdx + i}
			{@const tint = rowTintColor(node.qualGrade)}
			{@const isSel = node.id === selectedId}
			<div
				class="row"
				class:selected={isSel}
				role="row"
				aria-rowindex={idx + 2}
				aria-selected={isSel}
				style:grid-template-columns={colWidthCss()}
				style:--row-tint={tint}
				onclick={() => onSelect(node.id)}
				onkeydown={(e) => {
					if (e.key === 'Enter') onSelect(node.id);
				}}
				tabindex="0"
			>
				{#each columns as key (key)}
					{@const def = METRICS_BY_KEY[key]}
					{@const v = cellValue(node, key)}
					{@const formatted = def?.format
						? def.format(v)
						: v == null || v === ''
							? '—'
							: String(v)}
					<div
						class="cell"
						class:pinned={isPinned(key)}
						class:numeric={def?.type === 'number'}
						class:enum={def?.type === 'enum'}
						class:spark-cell={key === 'spark'}
						style:left={isPinned(key) ? `${stickyOffsets[key]}px` : ''}
						role="gridcell"
						tabindex="-1"
						onmouseenter={(e) => onCellMouseEnter(e, node, key, formatted)}
						onmouseleave={onCellMouseLeave}
					>
						{#if key === 'label'}
							<button
								type="button"
								class="company-link"
								onclick={(e) => handleCompanyClick(e, node.id)}
								title="{node.label} ({node.id}) — 대시보드 진입"
							>
								<span class="ind-dot" style:background={node.color || '#475569'}></span>
								<span class="company-name">{node.label}</span>
							</button>
						{:else if key === 'spark'}
							{@const sparkData = (node as any).spark}
							{#if Array.isArray(sparkData) && sparkData.length >= 2}
								{@const trend =
									sparkData[sparkData.length - 1] > sparkData[0] * 1.005
										? '#22c55e'
										: sparkData[sparkData.length - 1] < sparkData[0] * 0.995
											? '#ef4444'
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
		position: relative;
		height: 40px;
		flex-shrink: 0;
		background: #0a0e18;
		border-bottom: 1px solid #1e2433;
		z-index: 2;
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
