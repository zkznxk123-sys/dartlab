<script lang="ts">
	import { treemap, hierarchy, treemapSquarify } from 'd3-hierarchy';

	interface Props {
		nodes: any[];
		industries: any[];
		colorMetric: string;
		colorFor: (n: any, metric: any) => string;
		sizeMetric?: 'revenue' | 'roe' | 'opMargin' | 'revCagr';
		onNodeClick?: (node: any) => void;
	}

	let {
		nodes,
		industries,
		colorMetric,
		colorFor,
		sizeMetric = 'revenue',
		onNodeClick
	}: Props = $props();

	let containerEl: HTMLDivElement | null = $state(null);
	let width = $state(960);
	let height = $state(600);
	let hoveredId: string | null = $state(null);

	// ResizeObserver
	$effect(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver((entries) => {
			const r = entries[0].contentRect;
			if (r.width > 0) width = r.width;
			if (r.height > 0) height = r.height;
		});
		ro.observe(containerEl);
		return () => ro.disconnect();
	});

	// Industry name map
	let indNameMap = $derived(new Map(industries.map((i: any) => [i.id, i.name || i.id])));

	// Size value extractor — treemap needs positive values
	function sizeValue(n: any): number {
		if (sizeMetric === 'revenue') {
			return Math.max(1, (n.revenue || 0) / 1e8); // 억 단위
		}
		if (sizeMetric === 'roe') {
			return Math.max(0.1, (n.roe ?? 0) + 30); // shift to positive
		}
		if (sizeMetric === 'opMargin') {
			return Math.max(0.1, (n.opMargin ?? 0) + 20);
		}
		if (sizeMetric === 'revCagr') {
			return Math.max(0.1, (n.revCagr ?? 0) + 30);
		}
		return 1;
	}

	// Build hierarchical data: root → industries → companies
	let treemapData = $derived.by(() => {
		// Group nodes by industry
		const groups = new Map<string, any[]>();
		for (const n of nodes) {
			if (n.isIndustry) continue;
			const ind = n.industry || 'unknown';
			if (!groups.has(ind)) groups.set(ind, []);
			groups.get(ind)!.push(n);
		}

		const children = Array.from(groups.entries()).map(([indId, members]) => ({
			id: indId,
			name: indNameMap.get(indId) || indId,
			children: members.map((m) => ({
				id: m.id,
				label: m.label,
				industry: indId,
				_node: m,
				value: sizeValue(m)
			}))
		}));

		return { id: 'root', children };
	});

	// Compute treemap layout
	let cells = $derived.by(() => {
		if (width < 10 || height < 10) return [];

		const root = hierarchy(treemapData)
			.sum((d: any) => d.value || 0)
			.sort((a: any, b: any) => (b.value || 0) - (a.value || 0));

		const tm = treemap<any>()
			.size([width, height])
			.paddingTop(20)
			.paddingInner(1)
			.paddingOuter(2)
			.tile(treemapSquarify.ratio(1.2));

		const laid: any = tm(root);

		// Extract leaf cells + group headers
		const result: any[] = [];

		for (const group of (laid.children || []) as any[]) {
			// Industry group header
			result.push({
				type: 'group',
				id: group.data.id,
				name: group.data.name,
				x0: group.x0,
				y0: group.y0,
				x1: group.x1,
				y1: group.y1
			});

			// Company cells
			for (const leaf of group.leaves() as any[]) {
				const w = leaf.x1 - leaf.x0;
				const h = leaf.y1 - leaf.y0;
				result.push({
					type: 'leaf',
					id: leaf.data.id,
					label: leaf.data.label,
					industry: leaf.data.industry,
					_node: leaf.data._node,
					x0: leaf.x0,
					y0: leaf.y0,
					x1: leaf.x1,
					y1: leaf.y1,
					w,
					h,
					color: colorFor(leaf.data._node, colorMetric),
					showLabel: w > 40 && h > 16
				});
			}
		}

		return result;
	});

	// Size metric labels
	const SIZE_LABELS: Record<string, string> = {
		revenue: '매출',
		roe: 'ROE',
		opMargin: '영업이익률',
		revCagr: '매출 CAGR'
	};

	function metricDisplay(n: any): string {
		if (!n) return '';
		if (colorMetric === 'industry') return '';
		const v = n[colorMetric];
		if (v == null || Number.isNaN(v)) return '';
		if (colorMetric === 'revenue') return `${(v / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}억`;
		return `${v.toFixed(1)}%`;
	}
</script>

<div class="treemap-container" bind:this={containerEl}>
	<!-- Size metric selector -->
	<div class="tm-controls">
		<span class="tm-label">크기</span>
		{#each Object.entries(SIZE_LABELS) as [key, label]}
			<button
				class="tm-btn"
				class:active={sizeMetric === key}
				onclick={() => (sizeMetric = key as any)}
			>{label}</button>
		{/each}
	</div>

	<svg {width} {height} class="tm-svg">
		{#each cells as cell (cell.type + '-' + cell.id)}
			{#if cell.type === 'group'}
				<!-- Industry group background -->
				<rect
					x={cell.x0}
					y={cell.y0}
					width={cell.x1 - cell.x0}
					height={cell.y1 - cell.y0}
					fill="rgba(15, 18, 25, 0.9)"
					stroke="var(--color-dl-border)"
					stroke-width="1"
					rx="2"
				/>
				<!-- Industry label -->
				{#if cell.x1 - cell.x0 > 50}
					<text
						x={cell.x0 + 4}
						y={cell.y0 + 14}
						class="tm-group-label"
					>{cell.name}</text>
				{/if}
			{:else}
				<!-- Company cell -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<g
					class="tm-cell"
					class:hovered={hoveredId === cell.id}
					onmouseenter={() => (hoveredId = cell.id)}
					onmouseleave={() => (hoveredId = null)}
					onclick={() => onNodeClick?.(cell._node)}
				>
					<rect
						x={cell.x0}
						y={cell.y0}
						width={cell.w}
						height={cell.h}
						fill={cell.color}
						rx="1"
						opacity={hoveredId && hoveredId !== cell.id ? 0.5 : 0.85}
					/>
					{#if cell.showLabel}
						<text
							x={cell.x0 + cell.w / 2}
							y={cell.y0 + cell.h / 2 - (cell.h > 30 ? 4 : 0)}
							class="tm-label-text"
							dominant-baseline="central"
							text-anchor="middle"
						>{cell.label}</text>
						{#if cell.h > 30 && cell.w > 50}
							<text
								x={cell.x0 + cell.w / 2}
								y={cell.y0 + cell.h / 2 + 10}
								class="tm-metric-text"
								dominant-baseline="central"
								text-anchor="middle"
							>{metricDisplay(cell._node)}</text>
						{/if}
					{/if}
				</g>
			{/if}
		{/each}
	</svg>

	<!-- Tooltip -->
	{#if hoveredId}
		{@const hc = cells.find((c) => c.type === 'leaf' && c.id === hoveredId)}
		{#if hc}
			<div
				class="tm-tooltip"
				style:left="{Math.min(hc.x0 + hc.w / 2, width - 160)}px"
				style:top="{Math.max(hc.y0 - 44, 4)}px"
			>
				<strong>{hc.label}</strong>
				<span class="tm-tt-ind">{indNameMap.get(hc.industry) || ''}</span>
				{#if hc._node}
					<span class="tm-tt-metric">
						ROE {hc._node.roe?.toFixed(1) ?? '-'}% · OPM {hc._node.opMargin?.toFixed(1) ?? '-'}%
					</span>
				{/if}
			</div>
		{/if}
	{/if}
</div>

<style>
	.treemap-container {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: hidden;
		background: var(--color-dl-bg-dark);
	}
	.tm-controls {
		position: absolute;
		top: 8px;
		right: 12px;
		z-index: 10;
		display: flex;
		align-items: center;
		gap: 4px;
		background: rgba(15, 18, 25, 0.85);
		backdrop-filter: blur(8px);
		padding: 4px 8px;
		border-radius: 6px;
		border: 1px solid var(--color-dl-border);
	}
	.tm-label {
		font-size: 11px;
		color: var(--color-dl-text-muted);
		margin-right: 4px;
	}
	.tm-btn {
		background: transparent;
		border: 1px solid transparent;
		color: var(--color-dl-text-dim);
		font-size: 11px;
		padding: 2px 8px;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.15s;
	}
	.tm-btn:hover {
		color: var(--color-dl-text);
	}
	.tm-btn.active {
		background: rgba(234, 70, 71, 0.15);
		border-color: rgba(234, 70, 71, 0.3);
		color: var(--color-dl-primary-light);
	}
	.tm-svg {
		display: block;
	}
	.tm-group-label {
		fill: var(--color-dl-text-muted);
		font-size: 11px;
		font-weight: 600;
		pointer-events: none;
		text-transform: uppercase;
		letter-spacing: 0.02em;
	}
	.tm-cell {
		cursor: pointer;
		transition: opacity 0.15s;
	}
	.tm-cell.hovered rect {
		stroke: var(--color-dl-text);
		stroke-width: 1.5;
	}
	.tm-label-text {
		fill: white;
		font-size: 10px;
		font-weight: 600;
		pointer-events: none;
		text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
	}
	.tm-metric-text {
		fill: rgba(255, 255, 255, 0.7);
		font-size: 9px;
		pointer-events: none;
	}
	.tm-tooltip {
		position: absolute;
		transform: translateX(-50%);
		background: rgba(15, 18, 25, 0.95);
		border: 1px solid var(--color-dl-border);
		border-radius: 6px;
		padding: 6px 10px;
		pointer-events: none;
		z-index: 20;
		display: flex;
		flex-direction: column;
		gap: 2px;
		white-space: nowrap;
	}
	.tm-tooltip strong {
		color: var(--color-dl-text);
		font-size: 12px;
	}
	.tm-tt-ind {
		color: var(--color-dl-text-dim);
		font-size: 10px;
	}
	.tm-tt-metric {
		color: var(--color-dl-text-muted);
		font-size: 10px;
		font-family: var(--font-mono);
	}
</style>
