<script lang="ts">
	import ChartRenderer from '$chart/ChartRenderer.svelte';
	import type { StoryDashboardSectionView, StoryMetric } from '$lib/browser/storyDashboard';

	let { section }: { section: StoryDashboardSectionView } = $props();

	function sparkPath(values: Array<number | null> | undefined): string {
		const nums = (values ?? []).filter((value): value is number => value != null && Number.isFinite(value));
		if (nums.length < 2) return '';
		const min = Math.min(...nums);
		const max = Math.max(...nums);
		const span = max - min || 1;
		const width = 72;
		const height = 22;
		return nums
			.map((value, index) => {
				const x = (index / Math.max(1, nums.length - 1)) * width;
				const y = height - ((value - min) / span) * height;
				return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ');
	}

	function metricClass(metric: StoryMetric): string {
		return `metric ${metric.tone ?? 'neutral'}`;
	}
</script>

<section class="question-section" id={section.id} data-section>
	<header>
		<div>
			<div class="eyebrow">{section.tocLabel}</div>
			<h2>{section.question}</h2>
			<p>{section.summary}</p>
		</div>
		<div class="badges">
			{#each section.sectionKeys as key}
				<span>{key}</span>
			{/each}
		</div>
	</header>

	<div class="metric-grid">
		{#each section.metrics as metric}
			<article class={metricClass(metric)}>
				<span>{metric.label}</span>
				<strong>{metric.value}</strong>
				{#if sparkPath(metric.sparkValues)}
					<svg viewBox="0 0 72 22" aria-hidden="true">
						<path d={sparkPath(metric.sparkValues)} />
					</svg>
				{/if}
			</article>
		{:else}
			<p class="empty">연결된 핵심 수치가 없습니다.</p>
		{/each}
	</div>

	{#if section.charts.length}
		<div class="chart-grid">
			{#each section.charts as chart}
				<article class="chart-card">
					<ChartRenderer spec={chart} />
				</article>
			{/each}
		</div>
	{/if}

	<div class="block-grid">
		{#each section.blocks as block}
			<article class:emphasized={block.emphasized}>
				<strong>{block.label}</strong>
				<p>{block.description}</p>
			</article>
		{/each}
	</div>
</section>

<style>
	.question-section {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.96);
		padding: 16px;
	}
	header {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 16px;
		align-items: start;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 800;
		letter-spacing: 0;
	}
	h2,
	p {
		margin: 0;
	}
	h2 {
		margin-top: 4px;
		color: #f8fafc;
		font-size: 24px;
		font-weight: 800;
		letter-spacing: 0;
		line-height: 1.24;
	}
	header p {
		margin-top: 8px;
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.45;
	}
	.badges {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: 6px;
		max-width: 300px;
	}
	.badges span {
		border: 1px solid #263145;
		border-radius: 4px;
		background: #070c15;
		color: #bfdbfe;
		font-size: 11px;
		padding: 5px 7px;
	}
	.metric-grid {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 8px;
		margin-top: 14px;
	}
	.metric {
		min-width: 0;
		border: 1px solid #172033;
		border-radius: 6px;
		background: #070c15;
		padding: 10px;
	}
	.metric span {
		display: block;
		color: #94a3b8;
		font-size: 11px;
	}
	.metric strong {
		display: block;
		margin-top: 5px;
		overflow: hidden;
		color: #f8fafc;
		font-size: 18px;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.metric.good strong {
		color: #34d399;
	}
	.metric.bad strong {
		color: #f87171;
	}
	.metric svg {
		display: block;
		width: 72px;
		height: 22px;
		margin-top: 8px;
	}
	.metric path {
		fill: none;
		stroke: #fb923c;
		stroke-width: 2;
		stroke-linecap: round;
	}
	.chart-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 10px;
		margin-top: 12px;
	}
	.chart-card {
		min-width: 0;
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
		padding: 12px;
	}
	.block-grid {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
		margin-top: 12px;
	}
	.block-grid article {
		border-left: 2px solid #263145;
		background: #0b111e;
		padding: 9px 10px;
	}
	.block-grid article.emphasized {
		border-left-color: #ea4647;
	}
	.block-grid strong {
		display: block;
		color: #f8fafc;
		font-size: 12px;
	}
	.block-grid p,
	.empty {
		margin-top: 4px;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.45;
	}
	@media (max-width: 1180px) {
		.metric-grid {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
		.block-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 820px) {
		header,
		.chart-grid {
			grid-template-columns: 1fr;
		}
		.badges {
			justify-content: flex-start;
		}
		.metric-grid,
		.block-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
