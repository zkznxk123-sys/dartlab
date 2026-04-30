<script lang="ts">
	import { Chart, Svg } from 'layerchart';
	import { scaleBand, scaleLinear } from 'd3-scale';
	import { formatTableValue } from '$lib/browser/companyDashboardModel';

	let {
		title,
		periods = [],
		values = [],
		unit = 'KRW',
		color = '#60a5fa',
		signed = false,
		height = 118
	}: {
		title: string;
		periods?: string[];
		values?: Array<number | null>;
		unit?: string;
		color?: string;
		signed?: boolean;
		height?: number;
	} = $props();

	function finite(value: number | null | undefined): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}
	function tone(value: number | null | undefined): string {
		if (!finite(value)) return '#334155';
		if (signed && value < 0) return '#ef4444';
		return color;
	}
	function tail<T>(items: T[]): T[] {
		return items.slice(-8);
	}
	function latest(values: Array<number | null>): number | null {
		for (let i = values.length - 1; i >= 0; i -= 1) {
			if (finite(values[i])) return values[i]!;
		}
		return null;
	}

	let data = $derived(
		tail(periods).map((period, i) => ({
			period,
			value: tail(values)[i] ?? null
		}))
	);
	let nums = $derived(data.map((item) => item.value).filter(finite));
	let maxAbs = $derived(Math.max(1, ...nums.map((value) => Math.abs(value))));
	let maxPositive = $derived(Math.max(1, ...nums.map((value) => Math.max(0, value))));
	let yDomain = $derived(signed ? [-maxAbs, maxAbs] : [0, maxPositive]);
	let latestValue = $derived(latest(values));
</script>

<article class="mini-bars">
	<header>
		<span>{title}</span>
		<strong>{formatTableValue(latestValue, unit)}</strong>
	</header>
	<div class="chart-host">
		<Chart
			ssr
			{data}
			x="period"
			y="value"
			xScale={scaleBand().padding(0.42)}
			yScale={scaleLinear()}
			xDomain={data.map((item) => item.period)}
			{yDomain}
			yBaseline={signed ? 0 : null}
			{height}
			padding={{ top: 5, right: 6, bottom: 18, left: 6 }}
			tooltip={false}
			let:xScale
			let:yScale
			let:width
			let:height
		>
			<Svg>
				{@const zero = signed ? yScale(0) : height}
				<line x1="0" x2={width} y1={zero} y2={zero} class="zero" />
				{#each data as item}
					{@const x = xScale(item.period) ?? 0}
					{@const bw = xScale.bandwidth ? xScale.bandwidth() : 8}
					{@const y = finite(item.value) ? yScale(item.value) : zero}
					<rect
						x={x}
						y={finite(item.value) ? Math.min(y, zero) : zero - 1}
						width={bw}
						height={finite(item.value) ? Math.max(1, Math.abs(zero - y)) : 1}
						rx="2"
						fill={tone(item.value)}
						opacity={finite(item.value) ? 0.88 : 0.18}
					/>
					<text x={x + bw / 2} y={height + 14} text-anchor="middle">{item.period}</text>
				{/each}
			</Svg>
		</Chart>
	</div>
</article>

<style>
	.mini-bars {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #070c15;
		padding: 9px;
	}
	header {
		display: flex;
		justify-content: space-between;
		gap: 10px;
		align-items: baseline;
		margin-bottom: 5px;
	}
	span {
		color: #b8c2d2;
		font-size: 11px;
		font-weight: 800;
	}
	strong {
		min-width: 0;
		overflow: hidden;
		color: #f8fafc;
		font-size: 13px;
		font-weight: 840;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.chart-host {
		height: var(--mini-chart-height, 136px);
		min-height: 126px;
	}
	:global(.mini-bars .layercake-container) {
		height: 100% !important;
	}
	.zero {
		stroke: #263145;
		stroke-width: 1;
	}
	text {
		fill: #64748b;
		font-size: 9px;
	}
</style>
