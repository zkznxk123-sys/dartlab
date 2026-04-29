<script lang="ts">
	import { formatTableValue, type CashflowBridgeView } from '$lib/browser/companyDashboardModel';

	let { view }: { view: CashflowBridgeView } = $props();
	let hover = $state<{ x: number; y: number; title: string; lines: string[] } | null>(null);

	const W = 900;
	const H = 334;
	const PAD = { top: 24, right: 150, bottom: 34, left: 76 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = H - PAD.top - PAD.bottom;

	function finite(value: number | null | undefined): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}
	function tail<T>(values: T[]): T[] {
		return values.slice(-8);
	}
	function allValues(): number[] {
		return view.series.flatMap((serie) => tail(serie.values)).filter(finite);
	}
	function maxAbs(): number {
		return Math.max(1, ...allValues().map(Math.abs));
	}
	function x(index: number, count: number): number {
		return PAD.left + (index + 0.5) * (plotW / Math.max(1, count));
	}
	function y(value: number, max: number): number {
		return PAD.top + plotH / 2 - (value / max) * (plotH / 2);
	}
	function color(id: string, value: number | null): string {
		if (finite(value) && value < 0) return id === 'icf' ? '#60a5fa' : '#ef4444';
		if (id === 'ocf') return '#34d399';
		if (id === 'fcf') return '#fb923c';
		if (id === 'icf') return '#60a5fa';
		return '#64748b';
	}
	function valuesAt(index: number): string[] {
		return view.series.map((serie) => `${serie.label} ${formatTableValue(tail(serie.values)[index] ?? null, serie.unit)}`);
	}
	function showHover(event: MouseEvent, index: number) {
		const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
		hover = {
			x: rect.left + rect.width / 2,
			y: rect.top + 10,
			title: tail(view.periods)[index] ?? '',
			lines: valuesAt(index)
		};
	}
	function hideHover() {
		hover = null;
	}

	let periods = $derived(tail(view.periods));
	let scale = $derived(maxAbs());
	let groupW = $derived(plotW / Math.max(1, periods.length));
	let barW = $derived(Math.max(5, Math.min(13, groupW * 0.13)));
</script>

<article class="cashflow-chart">
	<header>
		<div>
			<h3>{view.title}</h3>
			<p>{view.subtitle}</p>
		</div>
		<div class="source">
			<span>{view.sourceMode}</span>
			<strong>{view.sourceLabel}</strong>
		</div>
	</header>

	<svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={view.title}>
		<rect x="0" y="0" width={W} height={H} rx="8" fill="#070c15" />
		<line x1={PAD.left} x2={W - PAD.right} y1={y(0, scale)} y2={y(0, scale)} class="zero" />
		<line x1={PAD.left} x2={W - PAD.right} y1={y(scale / 2, scale)} y2={y(scale / 2, scale)} class="grid" />
		<line x1={PAD.left} x2={W - PAD.right} y1={y(-scale / 2, scale)} y2={y(-scale / 2, scale)} class="grid" />
		<text x={PAD.left - 10} y={y(scale / 2, scale) + 4} text-anchor="end" class="axis">{formatTableValue(scale / 2, 'KRW')}</text>
		<text x={PAD.left - 10} y={y(-scale / 2, scale) + 4} text-anchor="end" class="axis">{formatTableValue(-scale / 2, 'KRW')}</text>

		{#each periods as period, i}
			{@const cx = x(i, periods.length)}
			<g role="presentation" onmouseenter={(event) => showHover(event, i)} onmouseleave={hideHover}>
				{#each view.series as serie, si}
					{@const value = tail(serie.values)[i] ?? null}
					{@const zero = y(0, scale)}
					{@const vy = finite(value) ? y(value, scale) : zero}
					<rect
						x={cx - barW * 2 - 3 + si * (barW + 2)}
						y={Math.min(zero, vy)}
						width={barW}
						height={finite(value) ? Math.max(1, Math.abs(zero - vy)) : 1}
						rx="2"
						fill={color(serie.id, value)}
						opacity={finite(value) ? 0.86 : 0.18}
					/>
				{/each}
				<rect x={cx - groupW / 2} y={PAD.top} width={groupW} height={plotH} fill="transparent" />
				<text x={cx} y={H - 12} text-anchor="middle" class="axis">{period}</text>
			</g>
		{/each}

		<g transform={`translate(${W - PAD.right + 20}, 44)`}>
			<text class="summary-title">최신 현금 방향</text>
			{#each view.latest as item, i}
				<g transform={`translate(0, ${24 + i * 46})`}>
					<circle cx="0" cy="0" r="4" fill={color(item.id, item.value)} />
					<text x="11" y="4" class="summary-label">{item.label}</text>
					<text x="11" y="21" class="summary-value">{formatTableValue(item.value, item.unit)}</text>
				</g>
			{/each}
		</g>
	</svg>

	<div class="legend">
		{#each view.series as serie}
			<span><i style:background={color(serie.id, 1)}></i>{serie.label}</span>
		{/each}
	</div>

	{#if view.coverageNotes.length}
		<div class="notes">
			{#each view.coverageNotes as note}
				<span class={note.tone}>{note.label}</span>
			{/each}
		</div>
	{/if}
</article>

{#if hover}
	<div class="chart-tip" style:left={`${hover.x}px`} style:top={`${hover.y}px`}>
		<strong>{hover.title}</strong>
		{#each hover.lines as line}
			<span>{line}</span>
		{/each}
	</div>
{/if}

<style>
	.cashflow-chart {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #050811;
		padding: 12px;
	}
	header {
		display: flex;
		justify-content: space-between;
		gap: 16px;
		align-items: flex-start;
		margin-bottom: 8px;
	}
	h3,
	p {
		margin: 0;
	}
	h3 {
		color: #f8fafc;
		font-size: 15px;
		font-weight: 820;
		line-height: 1.25;
	}
	p {
		margin-top: 4px;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.45;
	}
	.source {
		display: grid;
		gap: 2px;
		min-width: 120px;
		text-align: right;
	}
	.source span,
	.source strong {
		color: #94a3b8;
		font-size: 10px;
		font-weight: 700;
	}
	.source strong {
		color: #cbd5e1;
	}
	svg {
		display: block;
		width: 100%;
		height: auto;
		min-height: 288px;
	}
	.grid {
		stroke: #1e2433;
	}
	.zero {
		stroke: #64748b;
		stroke-dasharray: 3 4;
	}
	text {
		fill: #94a3b8;
		font-size: 10px;
	}
	.axis {
		fill: #64748b;
		font-size: 9px;
	}
	.summary-title {
		fill: #cbd5e1;
		font-size: 12px;
		font-weight: 820;
	}
	.summary-label {
		fill: #94a3b8;
		font-size: 10px;
	}
	.summary-value {
		fill: #f8fafc;
		font-size: 12px;
		font-weight: 820;
	}
	.legend,
	.notes {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 12px;
		margin-top: 8px;
	}
	.legend span,
	.notes span {
		display: inline-flex;
		gap: 5px;
		align-items: center;
		color: #94a3b8;
		font-size: 11px;
	}
	.legend i {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	.notes .missing {
		color: #94a3b8;
	}
	.chart-tip {
		position: fixed;
		z-index: 1000;
		transform: translate(-50%, calc(-100% - 8px));
		display: grid;
		gap: 2px;
		border: 1px solid #334155;
		border-radius: 5px;
		background: #020617;
		padding: 7px 9px;
		color: #cbd5e1;
		font-size: 11px;
		pointer-events: none;
		box-shadow: 0 16px 36px rgba(0, 0, 0, 0.36);
	}
	.chart-tip strong {
		color: #f8fafc;
	}
	@media (max-width: 720px) {
		header {
			display: grid;
		}
		.source {
			text-align: left;
		}
		svg {
			min-height: 260px;
		}
	}
</style>
