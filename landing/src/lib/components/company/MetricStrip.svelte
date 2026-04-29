<script lang="ts">
	import type { StatementMetric } from '$lib/browser/companyLive';

	let { metrics }: { metrics: StatementMetric[] } = $props();

	function deltaText(value: number | null): string {
		if (value == null || !Number.isFinite(value)) return '';
		return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
	}
</script>

<div class="metric-strip">
	{#each metrics as metric}
		<article class="metric {metric.tone}">
			<span>{metric.label}</span>
			<strong>{metric.display}</strong>
			<small>{metric.period ?? 'latest'} · {metric.formula}</small>
			{#if deltaText(metric.delta)}
				<b>{deltaText(metric.delta)}</b>
			{/if}
		</article>
	{/each}
</div>

<style>
	.metric-strip {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 8px;
	}
	.metric {
		position: relative;
		min-width: 0;
		border: 1px solid #172033;
		border-radius: 7px;
		background: #0b111d;
		padding: 11px;
	}
	.metric span,
	.metric small {
		display: block;
		color: #94a3b8;
		font-size: 11px;
	}
	.metric strong {
		display: block;
		margin-top: 6px;
		overflow: hidden;
		color: #f8fafc;
		font-size: 18px;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.metric small {
		margin-top: 5px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.metric b {
		position: absolute;
		top: 10px;
		right: 10px;
		color: #94a3b8;
		font-size: 11px;
	}
	.metric.good strong,
	.metric.good b {
		color: #34d399;
	}
	.metric.bad strong,
	.metric.bad b {
		color: #f87171;
	}
	@media (max-width: 1120px) {
		.metric-strip {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	@media (max-width: 720px) {
		.metric-strip {
			grid-template-columns: 1fr;
		}
	}
</style>
