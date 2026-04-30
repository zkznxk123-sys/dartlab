<script lang="ts">
	import { scaleBand, scaleLinear } from 'd3-scale';
	import { formatTableValue, type IncomeConversionView } from '$lib/browser/companyDashboardModel';

	let { view }: { view: IncomeConversionView } = $props();

	const W = 760;
	const H = 286;
	const PAD = { top: 22, right: 66, bottom: 42, left: 62 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = H - PAD.top - PAD.bottom;

	type Datum = {
		period: string;
		revenue: number | null;
		op: number | null;
		net: number | null;
	};

	function finite(value: number | null | undefined): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}

	function data(): Datum[] {
		const periods = view.periods.slice(-8);
		const offset = view.periods.length - periods.length;
		return periods.map((period, i) => ({
			period,
			revenue: view.revenue.values[offset + i] ?? null,
			op: view.op.values[offset + i] ?? null,
			net: view.net.values[offset + i] ?? null
		}));
	}

	function latest(values: Array<number | null>): number | null {
		for (let i = values.length - 1; i >= 0; i -= 1) {
			if (finite(values[i])) return values[i]!;
		}
		return null;
	}

	function latestDatum(): Datum | null {
		const rows = data();
		for (let i = rows.length - 1; i >= 0; i -= 1) {
			const row = rows[i];
			if (finite(row.revenue) || finite(row.op) || finite(row.net)) return row;
		}
		return null;
	}

	function xScale() {
		return scaleBand<string>()
			.domain(data().map((row) => row.period))
			.range([0, plotW])
			.padding(0.34);
	}

	function revenueScale() {
		const values = data().map((row) => row.revenue).filter(finite);
		const max = Math.max(...values, 0);
		return scaleLinear()
			.domain([0, max > 0 ? max * 1.15 : 1])
			.range([plotH, 0])
			.nice(3);
	}

	function profitScale() {
		const values = data()
			.flatMap((row) => [row.op, row.net])
			.filter(finite);
		const min = Math.min(0, ...values);
		const max = Math.max(0, ...values);
		const span = max - min || Math.max(Math.abs(max), Math.abs(min), 1);
		return scaleLinear()
			.domain([min - span * 0.12, max + span * 0.12])
			.range([plotH, 0])
			.nice(3);
	}

	function pathFor(key: 'op' | 'net'): string {
		const x = xScale();
		const y = profitScale();
		let path = '';
		let open = false;
		for (const row of data()) {
			const value = row[key];
			const xPos = (x(row.period) ?? 0) + x.bandwidth() / 2;
			if (!finite(value)) {
				open = false;
				continue;
			}
			path += `${open ? 'L' : 'M'} ${xPos.toFixed(1)} ${y(value).toFixed(1)} `;
			open = true;
		}
		return path.trim();
	}

	function axisLabel(period: string): string {
		return period.replace(/^20/, '');
	}
</script>

<article class="income-matrix">
	<header class="chart-head">
		<div>
			<h3>{view.title}</h3>
			<p>{view.sourceMode} · 좌축 매출 / 우축 이익 · {view.sourceLabel}</p>
		</div>
		<div class="latest-pills">
			<span>매출 <strong>{formatTableValue(latest(view.revenue.values), 'KRW')}</strong></span>
			<span class:watch={view.watch}>영업이익 <strong>{formatTableValue(latest(view.op.values), 'KRW')}</strong></span>
			<span>당기순이익 <strong>{formatTableValue(latest(view.net.values), 'KRW')}</strong></span>
		</div>
	</header>

	<div class="combo-wrap">
		<svg viewBox="0 0 {W} {H}" role="img" aria-label="매출액 막대와 영업이익, 순이익 라인">
			<g transform="translate({PAD.left},{PAD.top})">
				{#each revenueScale().ticks(3) as tick}
					<line x1="0" x2={plotW} y1={revenueScale()(tick)} y2={revenueScale()(tick)} class="grid" />
					<text x="-10" y={revenueScale()(tick)} dy="0.35em" text-anchor="end" class="axis left">
						{formatTableValue(tick, 'KRW')}
					</text>
				{/each}

				{#each profitScale().ticks(3) as tick}
					<text x={plotW + 10} y={profitScale()(tick)} dy="0.35em" text-anchor="start" class="axis right">
						{formatTableValue(tick, 'KRW')}
					</text>
				{/each}

				<line x1="0" x2={plotW} y1={profitScale()(0)} y2={profitScale()(0)} class="zero" />

				{#each data() as row}
					{@const x = xScale()(row.period) ?? 0}
					{@const barW = xScale().bandwidth()}
					{@const y = finite(row.revenue) ? revenueScale()(row.revenue) : plotH}
					{@const h = finite(row.revenue) ? plotH - y : 0}
					<rect
						x={x}
						y={y}
						width={barW}
						height={Math.max(h, finite(row.revenue) ? 2 : 0)}
						rx="3"
						class="revenue-bar"
					>
						<title>{row.period} 매출 {formatTableValue(row.revenue, 'KRW')}</title>
					</rect>
				{/each}

				<path d={pathFor('op')} class:watch={view.watch} class="line op" />
				<path d={pathFor('net')} class="line net" />

				{#each data() as row}
					{@const x = (xScale()(row.period) ?? 0) + xScale().bandwidth() / 2}
					{#if finite(row.op)}
						<circle cx={x} cy={profitScale()(row.op)} r="3.2" class:watch={view.watch} class="dot op-dot">
							<title>{row.period} 영업이익 {formatTableValue(row.op, 'KRW')}</title>
						</circle>
					{/if}
					{#if finite(row.net)}
						<circle cx={x} cy={profitScale()(row.net)} r="3.2" class="dot net-dot">
							<title>{row.period} 당기순이익 {formatTableValue(row.net, 'KRW')}</title>
						</circle>
					{/if}
				{/each}

				{#each data() as row}
					<text
						x={(xScale()(row.period) ?? 0) + xScale().bandwidth() / 2}
						y={plotH + 20}
						text-anchor="middle"
						class="period"
					>
						{axisLabel(row.period)}
					</text>
				{/each}
			</g>
		</svg>
	</div>

	<div class="legend-row">
		<span><i class="rev"></i>매출액 막대</span>
		<span><i class={view.watch ? 'watch-line' : 'op-line'}></i>영업이익 라인</span>
		<span><i class="net-line"></i>당기순이익 라인</span>
		{#if latestDatum()}
			<em>{latestDatum()?.period}</em>
		{/if}
	</div>

	{#if view.coverageNotes.length}
		<div class="notes">
			{#each view.coverageNotes as note}
				<span class={note.tone}>{note.label}</span>
			{/each}
		</div>
	{/if}
</article>

<style>
	.income-matrix {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #050811;
		padding: 10px;
	}
	.chart-head {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 12px;
		align-items: start;
		margin-bottom: 8px;
	}
	h3,
	p {
		margin: 0;
	}
	h3 {
		color: #f8fafc;
		font-size: 14px;
		font-weight: 840;
	}
	p {
		margin-top: 3px;
		color: #64748b;
		font-size: 10px;
	}
	.latest-pills {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: 6px;
		max-width: 520px;
	}
	.latest-pills span {
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #070c15;
		color: #94a3b8;
		font-size: 10px;
		padding: 5px 7px;
	}
	.latest-pills strong {
		margin-left: 5px;
		color: #f8fafc;
		font-size: 11px;
	}
	.latest-pills .watch strong {
		color: #fbbf24;
	}
	.combo-wrap {
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #070c15;
		padding: 8px;
	}
	svg {
		display: block;
		width: 100%;
		height: auto;
		min-height: 238px;
	}
	.grid {
		stroke: #1e2433;
		stroke-width: 1;
	}
	.zero {
		stroke: #334155;
		stroke-width: 1.2;
		stroke-dasharray: 4 4;
	}
	.axis,
	.period {
		fill: #64748b;
		font-size: 10px;
		font-weight: 700;
	}
	.axis.left {
		fill: #7db6f5;
	}
	.axis.right {
		fill: #b8c2d2;
	}
	.revenue-bar {
		fill: #60a5fa;
		opacity: 0.82;
	}
	.line {
		fill: none;
		stroke-width: 2.8;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.line.op {
		stroke: #fb923c;
	}
	.line.op.watch {
		stroke: #fbbf24;
	}
	.line.net {
		stroke: #34d399;
	}
	.dot {
		stroke: #070c15;
		stroke-width: 1.5;
	}
	.op-dot {
		fill: #fb923c;
	}
	.op-dot.watch {
		fill: #fbbf24;
	}
	.net-dot {
		fill: #34d399;
	}
	.legend-row,
	.notes {
		display: flex;
		flex-wrap: wrap;
		gap: 7px 12px;
		align-items: center;
		margin-top: 7px;
	}
	.legend-row span,
	.legend-row em,
	.notes span {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		color: #94a3b8;
		font-size: 10px;
		font-style: normal;
	}
	.legend-row em {
		margin-left: auto;
		color: #64748b;
	}
	i {
		width: 14px;
		height: 8px;
		border-radius: 2px;
	}
	.rev {
		background: #60a5fa;
	}
	.op-line,
	.net-line,
	.watch-line {
		height: 3px;
		border-radius: 99px;
	}
	.op-line {
		background: #fb923c;
	}
	.net-line {
		background: #34d399;
	}
	.watch-line {
		background: #fbbf24;
	}
	.notes .watch {
		color: #fbbf24;
	}
	.notes .missing {
		color: #64748b;
	}
	@media (max-width: 720px) {
		.chart-head {
			grid-template-columns: 1fr;
		}
		.latest-pills {
			justify-content: flex-start;
		}
		svg {
			min-height: 220px;
		}
		.legend-row em {
			margin-left: 0;
		}
	}
</style>
