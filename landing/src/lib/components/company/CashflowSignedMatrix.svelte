<script lang="ts">
	import { formatTableValue, type CashflowBridgeView } from '$lib/browser/companyDashboardModel';
	import LayerMiniBars from './LayerMiniBars.svelte';

	let { view }: { view: CashflowBridgeView } = $props();

	function color(id: string): string {
		if (id === 'ocf') return '#34d399';
		if (id === 'fcf') return '#fb923c';
		if (id === 'icf' || id === 'capex') return '#60a5fa';
		if (id === 'dividendPaid') return '#34d399';
		return '#64748b';
	}
</script>

<article class="cashflow-matrix">
	<header class="matrix-head">
		<div>
			<h3>{view.title}</h3>
			<p>{view.sourceMode} · {view.sourceLabel}</p>
		</div>
	</header>

	<div class="matrix-grid">
		{#each view.series as serie}
			<LayerMiniBars title={serie.label} periods={view.periods} values={serie.values} unit={serie.unit} color={color(serie.id)} signed />
		{/each}
	</div>

	<div class="latest-row">
		{#each view.latest as item}
			<div class={item.tone}>
				<span>{item.label}</span>
				<strong>{formatTableValue(item.value, item.unit)}</strong>
			</div>
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

<style>
	.cashflow-matrix {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #050811;
		padding: 10px;
	}
	.matrix-head {
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
	.matrix-grid {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
	}
	.latest-row {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
		margin-top: 8px;
	}
	.latest-row div {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #070c15;
		padding: 8px;
	}
	.latest-row span,
	.latest-row strong {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.latest-row span {
		color: #94a3b8;
		font-size: 10px;
	}
	.latest-row strong {
		margin-top: 4px;
		color: #f8fafc;
		font-size: 13px;
	}
	.latest-row .good strong {
		color: #34d399;
	}
	.latest-row .bad strong {
		color: #ef4444;
	}
	.latest-row .watch strong {
		color: #fbbf24;
	}
	.notes {
		display: flex;
		flex-wrap: wrap;
		gap: 7px;
		margin-top: 8px;
	}
	.notes span {
		color: #94a3b8;
		font-size: 10px;
	}
	.notes .missing {
		color: #64748b;
	}
	@media (max-width: 1040px) {
		.matrix-grid,
		.latest-row {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 620px) {
		.matrix-grid,
		.latest-row {
			grid-template-columns: 1fr;
		}
	}
</style>
