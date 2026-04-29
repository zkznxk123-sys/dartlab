<script lang="ts">
	import { formatTableValue, type FinancialChart } from '$lib/browser/companyDashboardModel';

	let { chart }: { chart: FinancialChart } = $props();

	const W = 720;
	const H = 260;
	const M = { top: 18, right: 18, bottom: 34, left: 64 };
	const plotW = W - M.left - M.right;
	const plotH = H - M.top - M.bottom;

	function finite(value: number | null | undefined): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}

	function visibleCategories(chart: FinancialChart): string[] {
		return chart.categories.slice(-8);
	}

	function visibleValues(values: Array<number | null>): Array<number | null> {
		return values.slice(-8);
	}

	function allValues(chart: FinancialChart): number[] {
		return chart.series.flatMap((serie) => visibleValues(serie.values)).filter(finite);
	}

	function extent(chart: FinancialChart): [number, number] {
		const values = allValues(chart);
		if (!values.length) return [0, 1];
		const min = Math.min(0, ...values);
		const max = Math.max(0, ...values);
		const pad = (max - min || Math.max(Math.abs(max), 1)) * 0.12;
		return [min - pad, max + pad];
	}

	function y(value: number, min: number, max: number): number {
		return M.top + plotH - ((value - min) / (max - min || 1)) * plotH;
	}

	function x(index: number, count: number): number {
		if (count <= 1) return M.left + plotW / 2;
		return M.left + (index / (count - 1)) * plotW;
	}

	function linePath(values: Array<number | null>, min: number, max: number, count: number): string {
		return visibleValues(values)
			.map((value, index) => {
				if (!finite(value)) return '';
				const command = index === 0 || !finite(visibleValues(values)[index - 1]) ? 'M' : 'L';
				return `${command}${x(index, count).toFixed(1)},${y(value, min, max).toFixed(1)}`;
			})
			.filter(Boolean)
			.join(' ');
	}

	function ticks(min: number, max: number): number[] {
		return [min, min + (max - min) / 2, max].filter((value) => Number.isFinite(value));
	}

	function groupedBars(chart: FinancialChart, min: number, max: number) {
		const categories = visibleCategories(chart);
		const groupW = plotW / Math.max(1, categories.length);
		const barW = Math.max(4, (groupW * 0.72) / Math.max(1, chart.series.length));
		return chart.series.flatMap((serie, si) =>
			visibleValues(serie.values).map((value, i) => {
				const baseX = M.left + i * groupW + groupW * 0.14 + si * barW;
				const zero = y(0, min, max);
				const vy = finite(value) ? y(value, min, max) : zero;
				return {
					key: `${serie.id}-${i}`,
					x: baseX,
					y: Math.min(zero, vy),
					width: Math.max(2, barW - 2),
					height: finite(value) ? Math.max(1, Math.abs(zero - vy)) : 1,
					fill: finite(value) && value < 0 ? '#ea4647' : serie.color,
					opacity: finite(value) ? 0.88 : 0.16
				};
			})
		);
	}

	function stackSegments(chart: FinancialChart, index: number) {
		const values = chart.series.map((serie) => Math.max(0, visibleValues(serie.values)[index] ?? 0));
		const total = values.reduce((sum, value) => sum + value, 0);
		let cursor = M.top + plotH;
		return chart.series.map((serie, si) => {
			const share = total > 0 ? values[si] / total : 0;
			const height = share * plotH;
			cursor -= height;
			return {
				key: `${serie.id}-${index}`,
				y: cursor,
				height,
				fill: serie.color,
				label: serie.label,
				share
			};
		});
	}

	function waterfallBars(chart: FinancialChart) {
		const values = chart.series[0]?.values ?? [];
		const visible = visibleValues(values);
		const min = Math.min(0, ...visible.filter(finite));
		const max = Math.max(0, ...visible.filter(finite));
		const yMin = min - Math.abs(max - min) * 0.12;
		const yMax = max + Math.abs(max - min || 1) * 0.12;
		const categories = visibleCategories(chart);
		const barW = plotW / Math.max(1, categories.length) * 0.56;
		return visible.map((value, index) => {
			const zero = y(0, yMin, yMax);
			const vy = finite(value) ? y(value, yMin, yMax) : zero;
			const cx = M.left + (index + 0.5) * (plotW / Math.max(1, categories.length));
			return {
				key: `${categories[index]}-${index}`,
				x: cx - barW / 2,
				y: Math.min(zero, vy),
				width: barW,
				height: finite(value) ? Math.max(1, Math.abs(zero - vy)) : 1,
				fill: finite(value) && value < 0 ? '#ea4647' : index === visible.length - 1 ? '#94a3b8' : '#34d399',
				value,
				yMin,
				yMax
			};
		});
	}

	function matrixTone(value: number | null): string {
		if (!finite(value) || value <= 0) return 'empty';
		if (value >= 8) return 'high';
		if (value >= 3) return 'mid';
		return 'low';
	}

	function empty(chart: FinancialChart): boolean {
		return !chart.series.some((serie) => serie.values.some(finite));
	}
</script>

<article class="chart-card {chart.kind}">
	<header>
		<div>
			<h3>{chart.title}</h3>
			<p>{chart.subtitle}</p>
		</div>
		<span>{chart.sourceLabel}</span>
	</header>

	{#if empty(chart)}
		<div class="empty">{chart.emptyLabel ?? '데이터 없음'}</div>
	{:else if chart.kind === 'small-multiples'}
		<div class="multiples">
			{#each chart.series as serie}
				{@const vals = visibleValues(serie.values)}
				{@const nums = vals.filter(finite)}
				{@const max = Math.max(...nums.map((value) => Math.abs(value)), 1)}
				<section>
					<div class="mini-head">
						<strong>{serie.label}</strong>
						<span>{formatTableValue(vals.at(-1) ?? null, serie.unit)}</span>
					</div>
					<div class="mini-bars">
						{#each vals as value}
							<i
								class:negative={(value ?? 0) < 0}
								style:height={`${finite(value) ? Math.max(3, (Math.abs(value) / max) * 72) : 2}px`}
								style:background={finite(value) && value < 0 ? '#ea4647' : serie.color}
							></i>
						{/each}
					</div>
				</section>
			{/each}
		</div>
	{:else if chart.kind === 'matrix'}
		<div class="matrix-grid">
			{#each chart.categories as category, index}
				{@const value = chart.series[0]?.values[index] ?? null}
				<div class={matrixTone(value)}>
					<span>{category}</span>
					<strong>{value ?? 0}</strong>
				</div>
			{/each}
		</div>
	{:else if chart.kind === 'stacked-share'}
		{@const categories = visibleCategories(chart)}
		<svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={chart.title}>
			<g>
				{#each categories as category, i}
					{@const groupW = plotW / Math.max(1, categories.length)}
					{@const barX = M.left + i * groupW + groupW * 0.18}
					{@const barW = groupW * 0.64}
					{#each stackSegments(chart, i) as segment}
						<rect
							x={barX}
							y={segment.y}
							width={barW}
							height={Math.max(0, segment.height)}
							fill={segment.fill}
							opacity={segment.height > 0 ? 0.86 : 0}
						/>
					{/each}
					<text x={barX + barW / 2} y={H - 12} text-anchor="middle">{category}</text>
				{/each}
			</g>
		</svg>
	{:else if chart.kind === 'waterfall'}
		{@const bars = waterfallBars(chart)}
		{@const yMin = bars[0]?.yMin ?? 0}
		{@const yMax = bars[0]?.yMax ?? 1}
		<svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={chart.title}>
			{#each ticks(yMin, yMax) as tick}
				<line x1={M.left} x2={W - M.right} y1={y(tick, yMin, yMax)} y2={y(tick, yMin, yMax)} />
				<text class="axis" x={M.left - 8} y={y(tick, yMin, yMax)} text-anchor="end">{formatTableValue(tick, chart.unit)}</text>
			{/each}
			<line class="zero" x1={M.left} x2={W - M.right} y1={y(0, yMin, yMax)} y2={y(0, yMin, yMax)} />
			{#each bars as bar, i}
				<rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} fill={bar.fill} rx="3" />
				<text x={bar.x + bar.width / 2} y={Math.max(16, bar.y - 7)} text-anchor="middle">{formatTableValue(bar.value, chart.unit)}</text>
				<text x={bar.x + bar.width / 2} y={H - 12} text-anchor="middle">{visibleCategories(chart)[i]}</text>
			{/each}
		</svg>
	{:else}
		{@const [min, max] = extent(chart)}
		{@const categories = visibleCategories(chart)}
		<svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={chart.title}>
			{#each ticks(min, max) as tick}
				<line x1={M.left} x2={W - M.right} y1={y(tick, min, max)} y2={y(tick, min, max)} />
				<text class="axis" x={M.left - 8} y={y(tick, min, max)} text-anchor="end">{formatTableValue(tick, chart.unit)}</text>
			{/each}
			<line class="zero" x1={M.left} x2={W - M.right} y1={y(0, min, max)} y2={y(0, min, max)} />
			{#if chart.kind === 'signed-bars' || chart.kind === 'valuation'}
				{#each groupedBars(chart, min, max) as bar}
					<rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} fill={bar.fill} opacity={bar.opacity} rx="2" />
				{/each}
			{/if}
			{#if chart.kind === 'lines'}
				{#each chart.series as serie}
					<path d={linePath(serie.values, min, max, categories.length)} stroke={serie.color} />
					{#each visibleValues(serie.values) as value, i}
						{#if finite(value)}
							<circle cx={x(i, categories.length)} cy={y(value, min, max)} r="3" fill={serie.color} />
						{/if}
					{/each}
				{/each}
			{/if}
			{#each categories as category, i}
				<text x={x(i, categories.length)} y={H - 12} text-anchor="middle">{category}</text>
			{/each}
		</svg>
	{/if}

	{#if chart.kind !== 'matrix'}
		<div class="legend">
			{#each chart.series as serie}
				<span><i style:background={serie.color}></i>{serie.label}</span>
			{/each}
		</div>
	{/if}
</article>

<style>
	.chart-card {
		min-width: 0;
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
		padding: 13px;
	}
	header {
		display: flex;
		justify-content: space-between;
		gap: 14px;
		align-items: flex-start;
		margin-bottom: 10px;
	}
	h3,
	p {
		margin: 0;
	}
	h3 {
		color: #f8fafc;
		font-size: 14px;
		font-weight: 780;
		line-height: 1.3;
	}
	p {
		margin-top: 4px;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.45;
	}
	header > span {
		flex: 0 0 auto;
		border: 1px solid #263145;
		border-radius: 5px;
		color: #94a3b8;
		font-size: 10px;
		padding: 4px 6px;
	}
	svg {
		display: block;
		width: 100%;
		height: auto;
		min-height: 220px;
	}
	line {
		stroke: #1e2433;
		stroke-width: 1;
	}
	.zero {
		stroke: #64748b;
	}
	text {
		fill: #94a3b8;
		font-size: 10px;
	}
	.axis {
		dominant-baseline: middle;
	}
	path {
		fill: none;
		stroke-width: 2.2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 9px 12px;
		margin-top: 8px;
	}
	.legend span {
		display: inline-flex;
		gap: 5px;
		align-items: center;
		color: #94a3b8;
		font-size: 11px;
	}
	.legend i {
		width: 9px;
		height: 9px;
		border-radius: 2px;
	}
	.multiples {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 10px;
	}
	.multiples section {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0a111d;
		padding: 10px;
	}
	.mini-head {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		align-items: baseline;
	}
	.mini-head strong,
	.mini-head span {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.mini-head strong {
		color: #cbd5e1;
		font-size: 12px;
	}
	.mini-head span {
		color: #f8fafc;
		font-size: 13px;
		font-weight: 780;
	}
	.mini-bars {
		display: flex;
		align-items: end;
		gap: 4px;
		height: 78px;
		margin-top: 11px;
		border-bottom: 1px solid #263145;
	}
	.mini-bars i {
		flex: 1 1 0;
		min-width: 5px;
		border-radius: 3px 3px 0 0;
	}
	.matrix-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 8px;
	}
	.matrix-grid div {
		border: 1px solid #263145;
		border-radius: 6px;
		background: #0a111d;
		padding: 14px;
	}
	.matrix-grid span,
	.matrix-grid strong {
		display: block;
	}
	.matrix-grid span {
		color: #94a3b8;
		font-size: 12px;
	}
	.matrix-grid strong {
		margin-top: 8px;
		color: #f8fafc;
		font-size: 24px;
	}
	.matrix-grid .empty strong {
		color: #64748b;
	}
	.matrix-grid .low {
		border-color: rgba(96, 165, 250, 0.45);
	}
	.matrix-grid .mid {
		border-color: rgba(251, 146, 60, 0.55);
	}
	.matrix-grid .high {
		border-color: rgba(52, 211, 153, 0.55);
	}
	.empty {
		display: grid;
		place-items: center;
		min-height: 190px;
		color: #64748b;
		font-size: 13px;
	}
	@media (max-width: 760px) {
		.multiples,
		.matrix-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
