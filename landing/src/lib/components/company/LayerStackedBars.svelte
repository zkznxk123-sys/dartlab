<script lang="ts">
	import { Chart, Svg } from 'layerchart';
	import { scaleBand, scaleLinear } from 'd3-scale';
	import type { StructureTrendPart } from '$lib/browser/companyDashboardModel';

	let {
		title,
		periods = [],
		parts = [],
		height = 176
	}: {
		title: string;
		periods?: string[];
		parts?: StructureTrendPart[];
		height?: number;
	} = $props();

	function finite(value: number | null | undefined): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}
	function tail<T>(items: T[]): T[] {
		return items.slice(-8);
	}
	function shareAt(part: StructureTrendPart, index: number): number {
		const value = tail(part.shares)[index];
		if (!finite(value)) return 0;
		return Math.max(0, Math.min(100, value));
	}

	let visiblePeriods = $derived(tail(periods));
	let data = $derived(visiblePeriods.map((period) => ({ period, value: 100 })));
	let visibleParts = $derived(parts.filter((part) => !part.missing || part.id.startsWith('other')));
</script>

<article class="stacked-bars">
	<header>
		<span>{title}</span>
	</header>
	<div class="chart-host">
		<Chart
			ssr
			{data}
			x="period"
			y="value"
			xScale={scaleBand().padding(0.28)}
			yScale={scaleLinear()}
			xDomain={visiblePeriods}
			yDomain={[0, 100]}
			{height}
			padding={{ top: 5, right: 6, bottom: 18, left: 6 }}
			tooltip={false}
			let:xScale
			let:width
			let:height
		>
			<Svg>
				<line x1="0" x2={width} y1="0" y2="0" class="grid" />
				<line x1="0" x2={width} y1={height / 2} y2={height / 2} class="grid" />
				{#each visiblePeriods as period, i}
					{@const x = xScale(period) ?? 0}
					{@const bw = xScale.bandwidth ? xScale.bandwidth() : 10}
					{@const totalH = height}
					{@const baseY = height}
					{#each visibleParts as part}
						{@const before = visibleParts.slice(0, visibleParts.indexOf(part)).reduce((sum, item) => sum + shareAt(item, i), 0)}
						{@const h = (shareAt(part, i) / 100) * totalH}
						<rect
							x={x}
							y={baseY - ((before / 100) * totalH + h)}
							width={bw}
							height={Math.max(0, h)}
							fill={part.color}
							opacity={part.missing ? 0.12 : 0.82}
						/>
					{/each}
					<rect x={x} y="0" width={bw} height={height} fill="none" stroke="#172033" />
					<text x={x + bw / 2} y={height + 14} text-anchor="middle">{period}</text>
				{/each}
			</Svg>
		</Chart>
	</div>
	<div class="legend">
		{#each visibleParts as part}
			<span><i style:background={part.color}></i>{part.label}</span>
		{/each}
	</div>
</article>

<style>
	.stacked-bars {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #070c15;
		padding: 9px;
	}
	header {
		margin-bottom: 5px;
	}
	header span {
		color: #b8c2d2;
		font-size: 11px;
		font-weight: 800;
	}
	.chart-host {
		height: 194px;
		min-height: 182px;
	}
	:global(.stacked-bars .layercake-container) {
		height: 100% !important;
	}
	.grid {
		stroke: #172033;
		stroke-width: 1;
	}
	text {
		fill: #64748b;
		font-size: 9px;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 5px 10px;
		margin-top: 7px;
	}
	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		color: #94a3b8;
		font-size: 10px;
	}
	i {
		width: 8px;
		height: 8px;
		border-radius: 2px;
	}
</style>
