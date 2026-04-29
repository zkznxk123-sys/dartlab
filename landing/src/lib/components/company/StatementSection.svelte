<script lang="ts">
	import MetricStrip from './MetricStrip.svelte';
	import type { StatementDashboard, StatementGroupRow } from '$lib/browser/companyLive';

	let {
		dashboard,
		selectedKey = null,
		onSelect
	}: {
		dashboard: StatementDashboard;
		selectedKey?: string | null;
		onSelect?: (row: StatementGroupRow) => void;
	} = $props();

	function fmt(value: number | string | null, unit: string): string {
		if (typeof value === 'string') return value || '—';
		if (value == null || !Number.isFinite(value)) return '—';
		if (unit === '%') return `${value.toFixed(1)}%`;
		if (unit === '조원') return `${value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}조`;
		const abs = Math.abs(value);
		if (abs >= 1e12) return `${(value / 1e12).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}조`;
		if (abs >= 1e8) return `${Math.round(value / 1e8).toLocaleString('ko-KR')}억`;
		return Math.round(value).toLocaleString('ko-KR');
	}

	function row(key: string): StatementGroupRow | null {
		for (const group of dashboard.groups) {
			const found = group.rows.find((r) => r.key === key);
			if (found) return found;
		}
		return null;
	}

	function latest(r: StatementGroupRow | null): number | null {
		const value = r?.values.at(-1);
		return typeof value === 'number' && Number.isFinite(value) ? value : null;
	}

	function width(value: number | null, max: number): number {
		if (value == null || max <= 0) return 0;
		return Math.max(4, Math.min(100, (Math.abs(value) / max) * 100));
	}

	function pct(num: number | null, den: number | null): string {
		if (num == null || den == null || den === 0) return '—';
		return `${((num / den) * 100).toFixed(1)}%`;
	}

	function yoy(value: number | null): string {
		if (value == null || !Number.isFinite(value)) return '—';
		return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
	}

	let revenue = $derived(row('revenue'));
	let op = $derived(row('op'));
	let net = $derived(row('net'));
	let assets = $derived(row('assets'));
	let liabilities = $derived(row('liabilities'));
	let equity = $derived(row('equity'));
	let cash = $derived(row('cash'));
	let ocf = $derived(row('ocf'));
	let icf = $derived(row('icf'));
	let financingCf = $derived(row('financingCf'));
	let closingCash = $derived(row('closingCash'));
	let fcfMetric = $derived(dashboard.metrics.find((m) => m.key === 'fcf'));

	let maxIncome = $derived(Math.max(latest(revenue) ?? 0, latest(op) ?? 0, latest(net) ?? 0, 1));
	let maxBalance = $derived(Math.max(latest(assets) ?? 0, latest(liabilities) ?? 0, latest(equity) ?? 0, 1));
	let maxCash = $derived(Math.max(Math.abs(latest(ocf) ?? 0), Math.abs(latest(icf) ?? 0), Math.abs(latest(financingCf) ?? 0), 1));

	function statementId(topic: string): string {
		if (topic === 'IS') return 'income';
		if (topic === 'BS') return 'balance';
		return 'cashflow';
	}
</script>

<section class="statement" id={statementId(dashboard.topic)} data-section>
	<header class="head">
		<div>
			<div class="eyebrow">재무제표 근거</div>
			<h2>{dashboard.title}</h2>
			<p>{dashboard.subtitle}</p>
		</div>
		<div class="source">
			<strong>{dashboard.quality.sourceLabel}</strong>
			<span>{dashboard.periods.at(-1) ?? 'period 없음'}</span>
		</div>
	</header>

	<MetricStrip metrics={dashboard.metrics} />

	{#if dashboard.topic === 'IS'}
		<div class="analysis-chart income-chart">
			<div class="chart-title">
				<strong>매출에서 순이익까지</strong>
				<span>마진 구조</span>
			</div>
			<div class="income-bars">
				<div>
					<span>매출</span>
					<b>{fmt(latest(revenue), revenue?.unit ?? 'KRW')}</b>
					<i style={`width:${width(latest(revenue), maxIncome)}%`}></i>
				</div>
				<div>
					<span>영업이익</span>
					<b>{fmt(latest(op), op?.unit ?? 'KRW')} · {pct(latest(op), latest(revenue))}</b>
					<i style={`width:${width(latest(op), maxIncome)}%`}></i>
				</div>
				<div>
					<span>순이익</span>
					<b>{fmt(latest(net), net?.unit ?? 'KRW')} · {pct(latest(net), latest(revenue))}</b>
					<i style={`width:${width(latest(net), maxIncome)}%`}></i>
				</div>
			</div>
		</div>
	{:else if dashboard.topic === 'BS'}
		<div class="analysis-chart balance-chart">
			<div class="chart-title">
				<strong>자산 = 부채 + 자본</strong>
				<span>재무 구조</span>
			</div>
			<div class="balance-grid">
				<div class="asset">
					<span>총자산</span>
					<strong>{fmt(latest(assets), assets?.unit ?? 'KRW')}</strong>
					<i style={`height:${width(latest(assets), maxBalance)}%`}></i>
				</div>
				<div class="stack">
					<div style={`height:${width(latest(liabilities), maxBalance)}%`}>
						<span>부채</span>
						<strong>{fmt(latest(liabilities), liabilities?.unit ?? 'KRW')}</strong>
					</div>
					<div style={`height:${width(latest(equity), maxBalance)}%`}>
						<span>자본</span>
						<strong>{fmt(latest(equity), equity?.unit ?? 'KRW')}</strong>
					</div>
				</div>
				<div class="balance-notes">
					<p>부채비율 {dashboard.metrics.find((m) => m.key === 'debtRatio')?.display ?? '—'}</p>
					<p>현금 {fmt(latest(cash), cash?.unit ?? 'KRW')}</p>
				</div>
			</div>
		</div>
	{:else}
		<div class="analysis-chart cash-chart">
			<div class="chart-title">
				<strong>영업현금에서 기말현금까지</strong>
				<span>현금 브릿지</span>
			</div>
			<div class="cash-bridge">
				{#each [
					{ label: '영업CF', item: ocf },
					{ label: '투자CF', item: icf },
					{ label: '재무CF', item: financingCf },
					{ label: 'FCF', display: fcfMetric?.display ?? '—' },
					{ label: '기말현금', item: closingCash }
				] as step}
					<div class:negative={step.item && (latest(step.item) ?? 0) < 0}>
						<span>{step.label}</span>
						<strong>{step.display ?? fmt(latest(step.item ?? null), step.item?.unit ?? 'KRW')}</strong>
						{#if step.item}
							<i style={`height:${width(latest(step.item), maxCash)}%`}></i>
						{:else}
							<i style="height:55%"></i>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<div class="groups">
		{#each dashboard.groups as group}
			{#if group.rows.length}
				<section class="group">
					<h3>{group.label}</h3>
					<div class="table-wrap">
						<table>
							<thead>
								<tr>
									<th>계정</th>
									{#each dashboard.periods as period}
										<th>{period}</th>
									{/each}
									<th>YoY</th>
								</tr>
							</thead>
							<tbody>
								{#each group.rows as item}
									<tr
										class:selected={selectedKey === item.key}
										role="button"
										tabindex="0"
										onclick={() => onSelect?.(item)}
										onkeydown={(event) => {
											if (event.key === 'Enter' || event.key === ' ') onSelect?.(item);
										}}
									>
										<td><strong>{item.label}</strong></td>
										{#each item.values as value}
											<td>{fmt(value, item.unit)}</td>
										{/each}
										<td class:up={(item.yoy ?? 0) > 0} class:down={(item.yoy ?? 0) < 0}>{yoy(item.yoy)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</section>
			{/if}
		{/each}
	</div>

	{#if dashboard.quality.missingAccounts.length}
		<div class="missing">누락 계정: {dashboard.quality.missingAccounts.join(', ')}</div>
	{/if}
</section>

<style>
	.statement {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.92);
		padding: 16px;
	}
	.head {
		display: flex;
		justify-content: space-between;
		gap: 16px;
		align-items: flex-start;
		margin-bottom: 14px;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 800;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	h2,
	h3,
	p {
		margin: 0;
	}
	h2 {
		margin-top: 5px;
		font-size: 26px;
		letter-spacing: 0;
	}
	p {
		margin-top: 6px;
		color: #94a3b8;
		font-size: 13px;
		line-height: 1.45;
	}
	.source {
		display: grid;
		gap: 3px;
		min-width: 120px;
		border: 1px solid #263145;
		border-radius: 6px;
		padding: 8px 10px;
		text-align: right;
	}
	.source strong {
		color: #f8fafc;
		font-size: 12px;
	}
	.source span,
	.missing {
		color: #94a3b8;
		font-size: 11px;
	}
	.analysis-chart {
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
		margin-top: 12px;
		padding: 14px;
	}
	.chart-title {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		margin-bottom: 14px;
	}
	.chart-title span {
		color: #7dd3fc;
		font-size: 12px;
	}
	.income-bars {
		display: grid;
		gap: 10px;
	}
	.income-bars div {
		display: grid;
		grid-template-columns: 90px minmax(120px, 180px) minmax(0, 1fr);
		gap: 10px;
		align-items: center;
	}
	.income-bars span,
	.balance-grid span,
	.cash-bridge span {
		color: #94a3b8;
		font-size: 12px;
	}
	.income-bars b,
	.balance-grid strong,
	.cash-bridge strong {
		color: #f8fafc;
		font-size: 13px;
	}
	.income-bars i {
		display: block;
		height: 22px;
		border-radius: 3px;
		background: linear-gradient(90deg, #ea4647, #fb923c);
	}
	.balance-grid {
		display: grid;
		grid-template-columns: 1fr 1fr 220px;
		gap: 12px;
		min-height: 190px;
	}
	.asset,
	.stack,
	.balance-notes {
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0b111e;
		padding: 10px;
	}
	.asset,
	.stack {
		display: flex;
		flex-direction: column;
		justify-content: end;
	}
	.asset i,
	.stack div,
	.cash-bridge i {
		display: block;
		border-radius: 4px 4px 0 0;
	}
	.asset i {
		margin-top: 8px;
		background: linear-gradient(180deg, #ea4647, #fb923c);
		min-height: 8px;
	}
	.stack div {
		min-height: 24px;
		padding: 8px;
	}
	.stack div:first-child {
		background: rgba(96, 165, 250, 0.42);
	}
	.stack div:last-child {
		background: rgba(52, 211, 153, 0.38);
	}
	.balance-notes {
		display: flex;
		flex-direction: column;
		justify-content: center;
	}
	.cash-bridge {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 8px;
		align-items: end;
		height: 180px;
	}
	.cash-bridge div {
		display: flex;
		flex-direction: column;
		justify-content: end;
		height: 100%;
		border-bottom: 1px solid #263145;
	}
	.cash-bridge i {
		margin-top: 8px;
		min-height: 8px;
		background: linear-gradient(180deg, #34d399, #0f766e);
	}
	.cash-bridge div.negative i {
		background: linear-gradient(180deg, #ea4647, #7f1d1d);
	}
	.groups {
		display: grid;
		gap: 10px;
		margin-top: 12px;
	}
	.group {
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
	}
	.group h3 {
		padding: 11px 12px;
		border-bottom: 1px solid #172033;
		font-size: 15px;
	}
	.table-wrap {
		overflow: auto;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}
	th,
	td {
		padding: 8px 10px;
		border-bottom: 1px solid #172033;
		text-align: right;
		white-space: nowrap;
	}
	th {
		color: #94a3b8;
		background: #0d1422;
	}
	th:first-child,
	td:first-child {
		position: sticky;
		left: 0;
		min-width: 210px;
		background: #070c15;
		text-align: left;
	}
	tr {
		cursor: pointer;
	}
	tr:hover td,
	tr.selected td {
		background: #0d1422;
	}
	td.up {
		color: #34d399;
	}
	td.down {
		color: #f87171;
	}
	.missing {
		margin-top: 10px;
	}
	@media (max-width: 980px) {
		.balance-grid,
		.cash-bridge {
			grid-template-columns: 1fr;
			height: auto;
		}
		.cash-bridge div {
			min-height: 110px;
		}
	}
	@media (max-width: 720px) {
		.statement {
			padding: 12px;
		}
		.head {
			flex-direction: column;
		}
		.source {
			width: 100%;
			text-align: left;
		}
		.income-bars div {
			grid-template-columns: 1fr;
		}
		th:first-child,
		td:first-child {
			min-width: 170px;
		}
	}
</style>
