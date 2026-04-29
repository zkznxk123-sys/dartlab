<script lang="ts">
	import type { EvidenceCoverageView } from '$lib/browser/companyDashboardModel';

	let { view, onOpenEvidence }: { view: EvidenceCoverageView; onOpenEvidence?: () => void } = $props();

	function statusLabel(status: string): string {
		if (status === 'ready') return '연결';
		if (status === 'waiting') return '대기';
		return '없음';
	}
</script>

<article class="evidence-chart">
	<header>
		<div>
			<h3>{view.title}</h3>
			<p>{view.subtitle}</p>
		</div>
		<button type="button" onclick={onOpenEvidence}>근거 보기</button>
	</header>

	<div class="coverage-grid">
		{#each view.items as item}
			<button type="button" class="coverage {item.status}" onclick={onOpenEvidence}>
				<span>{item.label}</span>
				<strong>{item.value}</strong>
				<small>{item.detail}</small>
				<em>{statusLabel(item.status)}</em>
			</button>
		{/each}
	</div>

	<div class="linked-list">
		{#each view.links as link}
			<button type="button" onclick={onOpenEvidence}>
				<span>{link.label}</span>
				<strong>{link.value}</strong>
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
	.evidence-chart {
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
		margin-bottom: 12px;
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
	button {
		border: 1px solid #263145;
		border-radius: 6px;
		background: #070c15;
		color: #cbd5e1;
		cursor: pointer;
		font: inherit;
	}
	header button {
		flex: 0 0 auto;
		padding: 7px 10px;
		font-size: 12px;
	}
	.coverage-grid {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
	}
	.coverage {
		position: relative;
		min-height: 132px;
		padding: 12px;
		text-align: left;
	}
	.coverage.ready {
		border-color: rgba(52, 211, 153, 0.42);
	}
	.coverage.waiting {
		border-color: rgba(251, 191, 36, 0.35);
	}
	.coverage.missing {
		border-color: #1e2433;
	}
	.coverage span,
	.coverage strong,
	.coverage small {
		display: block;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.coverage span {
		color: #94a3b8;
		font-size: 11px;
	}
	.coverage strong {
		margin-top: 9px;
		color: #f8fafc;
		font-size: 17px;
		font-weight: 820;
		white-space: nowrap;
	}
	.coverage small {
		margin-top: 8px;
		color: #64748b;
		font-size: 11px;
		line-height: 1.35;
		display: -webkit-box;
		line-clamp: 2;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}
	.coverage em {
		position: absolute;
		right: 9px;
		bottom: 9px;
		color: #94a3b8;
		font-size: 10px;
		font-style: normal;
		font-weight: 800;
	}
	.coverage.ready em {
		color: #34d399;
	}
	.coverage.waiting em {
		color: #fbbf24;
	}
	.linked-list,
	.notes {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 10px;
	}
	.linked-list button {
		display: inline-flex;
		gap: 8px;
		align-items: center;
		padding: 7px 9px;
	}
	.linked-list span {
		color: #94a3b8;
		font-size: 11px;
	}
	.linked-list strong {
		color: #f8fafc;
		font-size: 11px;
	}
	.notes span {
		color: #94a3b8;
		font-size: 11px;
	}
	@media (max-width: 900px) {
		.coverage-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 560px) {
		header {
			display: grid;
		}
		.coverage-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
