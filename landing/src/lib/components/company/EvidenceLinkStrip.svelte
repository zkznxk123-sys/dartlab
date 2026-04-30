<script lang="ts">
	import type { EvidenceCoverageView } from '$lib/browser/companyDashboardModel';

	let { view, onOpenEvidence }: { view: EvidenceCoverageView; onOpenEvidence?: () => void } = $props();
</script>

<article class="evidence-strip">
	<header>
		<div>
			<h3>{view.title}</h3>
			<p>{view.subtitle}</p>
		</div>
	</header>
	<div class="coverage-grid">
		{#each view.items as item}
			<button type="button" class={item.status} onclick={onOpenEvidence}>
				<span>{item.label}</span>
				<strong>{item.value}</strong>
				<small>{item.detail}</small>
			</button>
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
	.evidence-strip {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #050811;
		padding: 10px;
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
	.coverage-grid {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
		margin-top: 8px;
	}
	button {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #070c15;
		color: inherit;
		cursor: pointer;
		font: inherit;
		padding: 10px;
		text-align: left;
	}
	button.ready {
		border-color: rgba(52, 211, 153, 0.36);
	}
	button.waiting {
		border-color: rgba(251, 191, 36, 0.36);
	}
	button.missing {
		opacity: 0.72;
	}
	span,
	strong,
	small {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	span {
		color: #94a3b8;
		font-size: 10px;
	}
	strong {
		margin-top: 5px;
		color: #f8fafc;
		font-size: 15px;
	}
	small {
		margin-top: 5px;
		color: #64748b;
		font-size: 10px;
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
	@media (max-width: 920px) {
		.coverage-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 560px) {
		.coverage-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
