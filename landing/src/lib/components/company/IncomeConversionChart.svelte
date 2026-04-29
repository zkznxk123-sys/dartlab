<script lang="ts">
	import { formatTableValue, type IncomeConversionView } from '$lib/browser/companyDashboardModel';

	let { view }: { view: IncomeConversionView } = $props();
	let hover = $state<{ x: number; y: number; title: string; lines: string[] } | null>(null);

	const W = 900;
	const H = 360;
	const PAD = { top: 22, right: 132, bottom: 30, left: 78 };
	const plotW = W - PAD.left - PAD.right;
	const revenueLane = { y: 34, h: 90 };
	const profitLane = { y: 154, h: 92 };
	const marginLane = { y: 276, h: 48 };

	function finite(value: number | null | undefined): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}
	function tail<T>(values: T[]): T[] {
		return values.slice(-8);
	}
	function maxAbs(series: Array<Array<number | null>>): number {
		const values = series.flatMap((items) => tail(items)).filter(finite).map(Math.abs);
		return Math.max(1, ...values);
	}
	function maxPositive(values: Array<number | null>): number {
		return Math.max(1, ...tail(values).filter(finite).map((value) => Math.max(0, value)));
	}
	function x(index: number, count: number): number {
		return PAD.left + (index + 0.5) * (plotW / Math.max(1, count));
	}
	function barWidth(count: number, ratio = 0.52): number {
		return Math.max(10, Math.min(34, (plotW / Math.max(1, count)) * ratio));
	}
	function yRevenue(value: number, max: number): number {
		return revenueLane.y + revenueLane.h - (Math.max(0, value) / max) * revenueLane.h;
	}
	function ySigned(value: number, max: number): number {
		return profitLane.y + profitLane.h / 2 - (value / max) * (profitLane.h / 2);
	}
	function signedBar(value: number | null, max: number) {
		const zero = profitLane.y + profitLane.h / 2;
		if (!finite(value)) return { y: zero, h: 1, fill: '#1e2433', opacity: 0.45 };
		const y = ySigned(value, max);
		return {
			y: Math.min(zero, y),
			h: Math.max(1, Math.abs(zero - y)),
			fill: value < 0 ? '#ef4444' : '#fb923c',
			opacity: 0.9
		};
	}
	function marginFill(value: number | null): string {
		if (!finite(value)) return '#0f172a';
		if (Math.abs(value) > 100) return '#fbbf24';
		if (value < 0) return '#ef4444';
		return '#34d399';
	}
	function latest(values: Array<number | null>): number | null {
		for (let i = values.length - 1; i >= 0; i -= 1) if (finite(values[i])) return values[i]!;
		return null;
	}
	function labelAt(index: number, values: Array<number | null>, unit: string): string {
		return formatTableValue(tail(values)[index] ?? null, unit);
	}
	function showHover(event: MouseEvent, index: number) {
		const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
		const period = tail(view.periods)[index] ?? '';
		hover = {
			x: rect.left + rect.width / 2,
			y: rect.top + 10,
			title: period,
			lines: [
				`매출 ${labelAt(index, view.revenue.values, 'KRW')}`,
				`영업이익 ${labelAt(index, view.op.values, 'KRW')}`,
				`순이익 ${labelAt(index, view.net.values, 'KRW')}`,
				`영업이익률 ${labelAt(index, view.opMargin.values, '%')}`,
				`순이익률 ${labelAt(index, view.netMargin.values, '%')}`
			]
		};
	}
	function hideHover() {
		hover = null;
	}

	let periods = $derived(tail(view.periods));
	let revenueValues = $derived(tail(view.revenue.values));
	let opValues = $derived(tail(view.op.values));
	let netValues = $derived(tail(view.net.values));
	let opMarginValues = $derived(tail(view.opMargin.values));
	let netMarginValues = $derived(tail(view.netMargin.values));
	let revenueMax = $derived(maxPositive(view.revenue.values));
	let profitMax = $derived(maxAbs([view.op.values, view.net.values]));
	let groupW = $derived(plotW / Math.max(1, periods.length));
	let revW = $derived(barWidth(periods.length, 0.44));
	let profitW = $derived(Math.max(7, Math.min(16, groupW * 0.16)));
</script>

<article class="income-chart">
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
		<line x1={PAD.left} x2={W - PAD.right} y1={revenueLane.y + revenueLane.h} y2={revenueLane.y + revenueLane.h} class="grid" />
		<line x1={PAD.left} x2={W - PAD.right} y1={profitLane.y + profitLane.h / 2} y2={profitLane.y + profitLane.h / 2} class="zero" />
		<line x1={PAD.left} x2={W - PAD.right} y1={marginLane.y} y2={marginLane.y} class="grid" />
		<text x="16" y={revenueLane.y + 13} class="lane-label">매출</text>
		<text x="16" y={profitLane.y + 13} class="lane-label">이익</text>
		<text x="16" y={marginLane.y + 13} class="lane-label">마진</text>

		{#each periods as period, i}
			{@const revenue = revenueValues[i]}
			{@const op = signedBar(opValues[i] ?? null, profitMax)}
			{@const net = signedBar(netValues[i] ?? null, profitMax)}
			{@const cx = x(i, periods.length)}
			<g role="presentation" onmouseenter={(event) => showHover(event, i)} onmouseleave={hideHover}>
				{#if finite(revenue)}
					<rect
						x={cx - revW / 2}
						y={yRevenue(revenue, revenueMax)}
						width={revW}
						height={Math.max(1, revenueLane.y + revenueLane.h - yRevenue(revenue, revenueMax))}
						rx="3"
						fill="#60a5fa"
						opacity="0.78"
					/>
				{:else}
					<rect x={cx - revW / 2} y={revenueLane.y + revenueLane.h - 2} width={revW} height="2" rx="2" fill="#1e2433" />
				{/if}
				<rect x={cx - profitW - 1} y={op.y} width={profitW} height={op.h} rx="2" fill={op.fill} opacity={op.opacity} />
				<rect x={cx + 1} y={net.y} width={profitW} height={net.h} rx="2" fill={netValues[i] != null && (netValues[i] ?? 0) < 0 ? '#ef4444' : '#34d399'} opacity={net.opacity} />
				<rect x={cx - groupW * 0.32} y={marginLane.y + 10} width={groupW * 0.26} height="18" rx="3" fill={marginFill(opMarginValues[i] ?? null)} opacity={finite(opMarginValues[i]) ? 0.72 : 0.3} />
				<rect x={cx + groupW * 0.06} y={marginLane.y + 10} width={groupW * 0.26} height="18" rx="3" fill={marginFill(netMarginValues[i] ?? null)} opacity={finite(netMarginValues[i]) ? 0.72 : 0.3} />
				<rect x={cx - groupW / 2} y={revenueLane.y - 8} width={groupW} height={marginLane.y + marginLane.h - revenueLane.y + 8} fill="transparent" />
				<text x={cx} y={H - 10} text-anchor="middle" class="axis">{period}</text>
			</g>
		{/each}

		<g class="latest" transform={`translate(${W - PAD.right + 18}, 42)`}>
			<text class="latest-title">최신</text>
			<text y="26" class="latest-value">{formatTableValue(latest(view.revenue.values), 'KRW')}</text>
			<text y="43" class="latest-label">매출</text>
			<text y="72" class="latest-value">{formatTableValue(latest(view.op.values), 'KRW')}</text>
			<text y="89" class="latest-label">영업이익</text>
			<text y="118" class:watch={view.watch} class="latest-value">{formatTableValue(latest(view.opMargin.values), '%')}</text>
			<text y="135" class="latest-label">{view.watch ? '구조 확인' : '영업이익률'}</text>
		</g>
	</svg>

	<div class="legend">
		<span><i class="revenue"></i>매출</span>
		<span><i class="op"></i>영업이익</span>
		<span><i class="net"></i>순이익</span>
		<span><i class="margin"></i>마진 band</span>
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
	.income-chart {
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
		min-height: 300px;
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
	.lane-label {
		fill: #cbd5e1;
		font-size: 11px;
		font-weight: 800;
	}
	.axis {
		fill: #64748b;
		font-size: 9px;
	}
	.latest-title,
	.latest-label {
		fill: #64748b;
		font-size: 10px;
		font-weight: 700;
	}
	.latest-value {
		fill: #f8fafc;
		font-size: 13px;
		font-weight: 840;
	}
	.latest-value.watch {
		fill: #fbbf24;
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
		align-items: center;
		gap: 5px;
		color: #94a3b8;
		font-size: 11px;
	}
	.legend i {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	.revenue {
		background: #60a5fa;
	}
	.op {
		background: #fb923c;
	}
	.net {
		background: #34d399;
	}
	.margin {
		background: #fbbf24;
	}
	.notes .watch {
		color: #fbbf24;
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
