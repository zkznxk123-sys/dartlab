<script lang="ts">
	import type {
		DashboardQuestionView,
		FinancialTableGroup,
		FinancialTableRow
	} from '$lib/browser/companyDashboardModel';
	import BalanceStructureChart from './BalanceStructureChart.svelte';
	import CashflowBridgeChart from './CashflowBridgeChart.svelte';
	import EvidenceCoverageChart from './EvidenceCoverageChart.svelte';
	import FinancialChart from './FinancialChart.svelte';
	import FinancialTable from './FinancialTable.svelte';
	import IncomeConversionChart from './IncomeConversionChart.svelte';

	let {
		section,
		onOpenEvidence,
		onSelectRow
	}: {
		section: DashboardQuestionView;
		onOpenEvidence?: () => void;
		onSelectRow?: (row: FinancialTableRow, group: FinancialTableGroup) => void;
	} = $props();
</script>

<section class="question-section" id={section.id} data-section>
	<header class="section-head">
		<div>
			<div class="eyebrow">{section.tocLabel}</div>
			<h2>{section.question}</h2>
			<p>{section.answer}</p>
		</div>
		<div class="evidence-links">
			{#each section.evidenceLinks as link}
				<button type="button" onclick={onOpenEvidence}>
					<span>{link.label}</span>
					<strong>{link.value}</strong>
				</button>
			{/each}
		</div>
	</header>

	{#if section.metrics.length}
		<div class="metric-row">
			{#each section.metrics as metric}
				<article class={metric.tone}>
					<span>{metric.label}</span>
					<strong>{metric.value}</strong>
					<small class={metric.deltaTone}>{metric.note || metric.delta || metric.period || '비교 대기'}</small>
				</article>
			{/each}
		</div>
	{/if}

	{#if section.coverageNotes.length}
		<div class="coverage-notes">
			{#each section.coverageNotes as note}
				<span class={note.tone}>{note.label}</span>
			{/each}
		</div>
	{/if}

	{#if section.visuals.length}
		<div class="visual-stack">
			{#each section.visuals as visual}
				{#if visual.type === 'income-conversion'}
					<IncomeConversionChart view={visual.view} />
				{:else if visual.type === 'balance-structure'}
					<BalanceStructureChart view={visual.view} />
				{:else if visual.type === 'cashflow-bridge'}
					<CashflowBridgeChart view={visual.view} />
				{:else if visual.type === 'evidence-coverage'}
					<EvidenceCoverageChart view={visual.view} {onOpenEvidence} />
				{:else}
					<FinancialChart chart={visual.chart} />
				{/if}
			{/each}
		</div>
	{:else if section.charts.length}
		<div class="visual-stack">
			{#each section.charts.slice(0, 1) as chart}
				<FinancialChart {chart} />
			{/each}
		</div>
	{/if}

	<FinancialTable groups={section.tableGroups} onSelect={onSelectRow} />
</section>

<style>
	.question-section {
		display: grid;
		gap: 12px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.96);
		padding: 16px;
	}
	.section-head {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 18px;
		align-items: start;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 900;
		letter-spacing: 0;
	}
	h2,
	p {
		margin: 0;
	}
	h2 {
		margin-top: 5px;
		color: #f8fafc;
		font-size: clamp(21px, 2.2vw, 28px);
		font-weight: 840;
		letter-spacing: 0;
		line-height: 1.2;
	}
	p {
		margin-top: 7px;
		color: #a8b4c6;
		font-size: 13px;
		line-height: 1.45;
	}
	.evidence-links {
		display: grid;
		grid-template-columns: repeat(2, minmax(98px, 1fr));
		gap: 7px;
		min-width: 250px;
	}
	.evidence-links button {
		border: 1px solid #263145;
		border-radius: 6px;
		background: #070c15;
		color: #cbd5e1;
		cursor: pointer;
		font: inherit;
		padding: 8px 9px;
		text-align: left;
	}
	.evidence-links span,
	.evidence-links strong {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.evidence-links span {
		color: #94a3b8;
		font-size: 10px;
	}
	.evidence-links strong {
		margin-top: 4px;
		font-size: 12px;
	}
	.metric-row {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 8px;
	}
	.metric-row article {
		min-width: 0;
		border: 1px solid #172033;
		border-radius: 6px;
		background: #070c15;
		padding: 10px;
	}
	.metric-row span,
	.metric-row small {
		display: block;
		color: #94a3b8;
		font-size: 11px;
	}
	.metric-row strong {
		display: block;
		margin-top: 6px;
		overflow: hidden;
		color: #f8fafc;
		font-size: 18px;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.metric-row .good strong,
	.metric-row small.good {
		color: #34d399;
	}
	.metric-row .bad strong,
	.metric-row small.bad {
		color: #f87171;
	}
	.metric-row .watch strong,
	.metric-row small.watch {
		color: #fbbf24;
	}
	.metric-row .missing strong {
		color: #64748b;
	}
	.coverage-notes {
		display: flex;
		flex-wrap: wrap;
		gap: 7px;
	}
	.coverage-notes span {
		border: 1px solid #263145;
		border-radius: 5px;
		background: #070c15;
		color: #94a3b8;
		font-size: 11px;
		padding: 6px 8px;
	}
	.coverage-notes .watch {
		border-color: rgba(251, 191, 36, 0.45);
		color: #fbbf24;
	}
	.visual-stack {
		display: grid;
		grid-template-columns: 1fr;
		gap: 12px;
	}
	@media (max-width: 1120px) {
		.metric-row {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	@media (max-width: 840px) {
		.section-head {
			grid-template-columns: 1fr;
		}
		.evidence-links {
			min-width: 0;
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 640px) {
		.metric-row,
		.evidence-links {
			grid-template-columns: 1fr;
		}
	}
</style>
