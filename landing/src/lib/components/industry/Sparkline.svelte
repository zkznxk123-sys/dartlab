<script lang="ts">
	interface Series {
		label: string;
		color: string;
		values: Array<number | null>;
	}

	interface Props {
		labels: string[];
		series: Series[];
		width?: number;
		height?: number;
		// "5년 추이 · 2021~2025" 같은 캡션
		periodLabel?: string;
	}

	let { labels, series, width = 280, height = 80, periodLabel = '' }: Props = $props();

	const PAD = { l: 4, r: 4, t: 8, b: 14 };

	let allValues = $derived(
		series
			.flatMap((s) => s.values)
			.filter((v): v is number => typeof v === 'number' && !isNaN(v))
	);

	let yMin = $derived(allValues.length ? Math.min(...allValues, 0) : 0);
	let yMax = $derived(allValues.length ? Math.max(...allValues, 1) : 1);
	let yRange = $derived(yMax - yMin || 1);

	function x(i: number, n: number): number {
		if (n <= 1) return PAD.l + (width - PAD.l - PAD.r) / 2;
		return PAD.l + (i / (n - 1)) * (width - PAD.l - PAD.r);
	}
	function y(v: number): number {
		return height - PAD.b - ((v - yMin) / yRange) * (height - PAD.t - PAD.b);
	}

	function path(values: Array<number | null>): string {
		const points = values
			.map((v, i) => (typeof v === 'number' && !isNaN(v) ? `${x(i, values.length)},${y(v)}` : null))
			.filter((p): p is string => p !== null);
		if (points.length === 0) return '';
		return 'M' + points.join(' L');
	}

	function fmt(v: number): string {
		const abs = Math.abs(v);
		if (abs >= 1e12) return `${(v / 1e12).toFixed(1)}조`;
		if (abs >= 1e8) return `${Math.round(v / 1e8).toLocaleString()}억`;
		if (abs >= 1e4) return `${Math.round(v / 1e4).toLocaleString()}만`;
		return v.toLocaleString();
	}
</script>

<div class="sparkline">
	<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" {width} {height}>
		<!-- 0 baseline if range crosses zero -->
		{#if yMin < 0 && yMax > 0}
			<line
				x1={PAD.l}
				x2={width - PAD.r}
				y1={y(0)}
				y2={y(0)}
				stroke="#334155"
				stroke-dasharray="2,3"
				stroke-width="1"
			/>
		{/if}

		{#each series as s (s.label)}
			<path d={path(s.values)} fill="none" stroke={s.color} stroke-width="1.8" stroke-linecap="round" />
			{#each s.values as v, i}
				{#if typeof v === 'number' && !isNaN(v)}
					<circle cx={x(i, s.values.length)} cy={y(v)} r="2" fill={s.color} />
				{/if}
			{/each}
		{/each}

		{#each labels as l, i}
			<text
				x={x(i, labels.length)}
				y={height - 2}
				text-anchor="middle"
				font-size="9"
				fill="#64748b"
				font-family="monospace"
			>
				{l}
			</text>
		{/each}
	</svg>

	<div class="legend">
		{#each series as s (s.label)}
			{@const last = [...s.values].reverse().find((v): v is number => typeof v === 'number' && !isNaN(v))}
			<div class="leg-row">
				<span class="leg-dot" style="background:{s.color}"></span>
				<span class="leg-name">{s.label}</span>
				{#if last !== undefined}
					<span class="leg-val" style:color={s.color}>{fmt(last)}</span>
				{/if}
			</div>
		{/each}
	</div>

	{#if periodLabel}
		<div class="period">{periodLabel}</div>
	{/if}
</div>

<style>
	.sparkline {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.sparkline svg {
		display: block;
		width: 100%;
		height: auto;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 4px;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		font-size: 11px;
	}
	.leg-row {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.leg-dot {
		width: 10px;
		height: 3px;
		border-radius: 2px;
	}
	.leg-name {
		color: #94a3b8;
	}
	.leg-val {
		font-weight: 600;
		font-family: monospace;
	}
	.period {
		font-size: 10px;
		color: #64748b;
		font-family: monospace;
		margin-top: 2px;
	}
</style>
