<script lang="ts">
	import type {
		DashboardQuestionView,
		FinancialTableGroup,
		FinancialTableRow
	} from '$lib/browser/companyDashboardModel';
	import BalanceStructureTrend from './BalanceStructureTrend.svelte';
	import CashflowSignedMatrix from './CashflowSignedMatrix.svelte';
	import EvidenceLinkStrip from './EvidenceLinkStrip.svelte';
	import FinancialChart from './FinancialChart.svelte';
	import FinancialTable from './FinancialTable.svelte';
	import IncomeTrendMatrix from './IncomeTrendMatrix.svelte';

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

<section class="story-report-section" id={section.id} data-section>
	<header class="section-head">
		<div>
			<span>{section.tocLabel}</span>
			<h2>{section.question}</h2>
			<p>{section.answer}</p>
		</div>
	</header>

	{#if section.metrics.length}
		<div class="kpi-strip">
			{#each section.metrics.slice(0, 6) as metric}
				<article class={metric.tone}>
					<span>{metric.label}</span>
					<strong>{metric.value}</strong>
					<small class={metric.deltaTone}>{metric.note || metric.delta || metric.period || '비교 대기'}</small>
				</article>
			{/each}
		</div>
	{/if}

	<div class="visual-grid">
		{#each section.visuals as visual}
			{#if visual.type === 'income-trend-matrix'}
				<div class="wide"><IncomeTrendMatrix view={visual.view} /></div>
			{:else if visual.type === 'balance-structure-trend'}
				<div class="wide"><BalanceStructureTrend view={visual.view} /></div>
			{:else if visual.type === 'cashflow-signed-matrix' || visual.type === 'capital-allocation-bridge'}
				<div class="wide"><CashflowSignedMatrix view={visual.view} /></div>
			{:else if visual.type === 'evidence-link-strip'}
				<div class="wide"><EvidenceLinkStrip view={visual.view} {onOpenEvidence} /></div>
			{:else if visual.type === 'legacy-chart'}
				<div><FinancialChart chart={visual.chart} /></div>
			{/if}
		{/each}
	</div>

	{#if section.coverageNotes.length}
		<div class="coverage-notes">
			{#each section.coverageNotes as note}
				<span class={note.tone}>{note.label}</span>
			{/each}
		</div>
	{/if}

	<FinancialTable groups={section.tableGroups.slice(0, 2)} onSelect={onSelectRow} />

	{#if section.evidenceLinks.length}
		<div class="evidence-row">
			{#each section.evidenceLinks.slice(0, 4) as link}
				<button type="button" onclick={onOpenEvidence}>
					<span>{link.label}</span>
					<strong>{link.value}</strong>
				</button>
			{/each}
		</div>
	{/if}
</section>

<style>
	.story-report-section {
		display: grid;
		gap: 8px;
		border-top: 1px solid #1e2433;
		background: rgba(5, 8, 17, 0.74);
		padding: 14px 0 18px;
	}
	.section-head {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		align-items: start;
	}
	.section-head span {
		color: #fb923c;
		font-size: 11px;
		font-weight: 900;
	}
	h2,
	p {
		margin: 0;
	}
	h2 {
		margin-top: 3px;
		color: #f8fafc;
		font-size: clamp(19px, 1.8vw, 25px);
		font-weight: 860;
		letter-spacing: 0;
		line-height: 1.18;
	}
	p {
		margin-top: 5px;
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.38;
	}
	.evidence-row {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 6px;
	}
	.evidence-row button {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #070c15;
		color: inherit;
		cursor: pointer;
		font: inherit;
		padding: 7px 8px;
		text-align: left;
	}
	.evidence-row button span,
	.evidence-row button strong {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.evidence-row button span {
		color: #64748b;
		font-size: 10px;
	}
	.evidence-row button strong {
		margin-top: 3px;
		color: #cbd5e1;
		font-size: 11px;
	}
	.kpi-strip {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 6px;
	}
	.kpi-strip article {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #070c15;
		padding: 8px;
	}
	.kpi-strip span,
	.kpi-strip small,
	.coverage-notes span {
		display: block;
		color: #94a3b8;
		font-size: 10px;
	}
	.kpi-strip strong {
		display: block;
		margin-top: 5px;
		overflow: hidden;
		color: #f8fafc;
		font-size: 15px;
		font-weight: 840;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.kpi-strip .good strong,
	.kpi-strip small.good {
		color: #34d399;
	}
	.kpi-strip .bad strong,
	.kpi-strip small.bad {
		color: #ef4444;
	}
	.kpi-strip .watch strong,
	.kpi-strip small.watch {
		color: #fbbf24;
	}
	.kpi-strip .missing strong {
		color: #64748b;
	}
	.visual-grid {
		display: grid;
		grid-template-columns: repeat(12, minmax(0, 1fr));
		gap: 8px;
	}
	.visual-grid > div {
		grid-column: span 6;
		min-width: 0;
	}
	.visual-grid > .wide {
		grid-column: 1 / -1;
	}
	.coverage-notes {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.coverage-notes span {
		display: inline-flex;
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #070c15;
		padding: 5px 7px;
	}
	.coverage-notes .watch {
		color: #fbbf24;
	}
	.coverage-notes .missing {
		color: #64748b;
	}
	@media (max-width: 1080px) {
		.section-head {
			grid-template-columns: 1fr;
			align-items: start;
		}
		.kpi-strip {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
		.visual-grid > div {
			grid-column: 1 / -1;
		}
	}
	@media (max-width: 640px) {
		.kpi-strip {
			display: flex;
			overflow-x: auto;
			overscroll-behavior-x: contain;
			padding-bottom: 4px;
			scrollbar-width: thin;
		}
		.kpi-strip article {
			flex: 0 0 128px;
			padding: 7px;
		}
		.evidence-row {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
</style>
