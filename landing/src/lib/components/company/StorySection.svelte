<script lang="ts">
	import type { StoryDashboardBlock, StoryDashboardSectionView, StoryMetric } from '$lib/browser/storyDashboard';

	let { section }: { section: StoryDashboardSectionView } = $props();

	function metrics(section: StoryDashboardSectionView): StoryMetric[] {
		const seen = new Set<string>();
		return section.blocks
			.flatMap((block) => block.metrics)
			.filter((metric) => {
				const key = `${metric.label}:${metric.value}`;
				if (seen.has(key)) return false;
				seen.add(key);
				return true;
			})
			.slice(0, 6);
	}

	function insightBlocks(section: StoryDashboardSectionView): StoryDashboardBlock[] {
		return section.blocks.filter((block) => block.flags.length || block.text).slice(0, 4);
	}

	function evidenceTotal(section: StoryDashboardSectionView): number {
		return section.blocks.reduce((total, block) => total + block.evidenceCount, 0);
	}
</script>

<section class="story-section" id={section.id} data-section>
	<header>
		<div>
			<div class="eyebrow">{section.actTitle || 'Story'}</div>
			<h2>{section.title}</h2>
			<p>{section.summary}</p>
		</div>
		{#if section.question}
			<aside>{section.question}</aside>
		{/if}
	</header>

	<div class="decision-grid">
		<article class="metric-panel">
			<div class="panel-title">
				<strong>핵심 수치</strong>
				<span>{section.key}</span>
			</div>
			<div class="metrics">
				{#each metrics(section) as metric}
					<div class={metric.tone ?? 'neutral'}>
						<span>{metric.label}</span>
						<strong>{metric.value}</strong>
					</div>
				{:else}
					<p>연결된 핵심 수치를 불러오는 중입니다.</p>
				{/each}
			</div>
		</article>

		<article class="insight-panel">
			<div class="panel-title">
				<strong>판단 근거</strong>
				<span>{evidenceTotal(section) ? `${evidenceTotal(section)}개 근거` : '재무제표 우선'}</span>
			</div>
			<div class="insights">
				{#each insightBlocks(section) as block}
					<section class:emphasized={block.emphasized}>
						<div>
							<b>{block.label}</b>
							<small>{block.description}</small>
						</div>
						{#if block.flags.length}
							<ul>
								{#each block.flags.slice(0, 2) as flag}
									<li>{flag}</li>
								{/each}
							</ul>
						{:else}
							<p>{block.text}</p>
						{/if}
					</section>
				{/each}
			</div>
		</article>
	</div>
</section>

<style>
	.story-section {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: linear-gradient(180deg, rgba(10, 15, 27, 0.96), rgba(5, 8, 17, 0.96));
		padding: 16px;
	}
	header {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 280px;
		gap: 18px;
		align-items: start;
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
	p {
		margin: 0;
	}
	h2 {
		margin-top: 5px;
		font-size: 25px;
		letter-spacing: 0;
	}
	header p,
	header aside,
	article p {
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.5;
	}
	header p {
		margin-top: 6px;
	}
	header aside {
		border-left: 2px solid #ea4647;
		background: #070c15;
		padding: 10px 12px;
	}
	.decision-grid {
		display: grid;
		grid-template-columns: 0.92fr 1.08fr;
		gap: 8px;
	}
	.metric-panel,
	.insight-panel {
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
		padding: 14px;
	}
	.panel-title {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		align-items: center;
	}
	.panel-title strong {
		color: #f8fafc;
		font-size: 14px;
	}
	.panel-title span {
		color: #fb923c;
		font-size: 11px;
		font-weight: 800;
	}
	.metrics {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 6px;
		margin-top: 12px;
	}
	.metrics div {
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0b111e;
		padding: 8px;
		min-width: 0;
	}
	.metrics div.good {
		border-color: rgba(34, 197, 94, 0.5);
	}
	.metrics div.bad {
		border-color: rgba(234, 70, 71, 0.65);
	}
	.metrics span {
		display: block;
		color: #7dd3fc;
		font-size: 11px;
	}
	.metrics strong {
		display: block;
		margin-top: 5px;
		color: #f8fafc;
		font-size: 17px;
	}
	.insights {
		display: grid;
		gap: 8px;
		margin-top: 12px;
	}
	.insights section {
		border-left: 2px solid #263145;
		background: #0b111e;
		padding: 9px 10px;
	}
	.insights section.emphasized {
		border-left-color: #ea4647;
	}
	.insights b,
	.insights small {
		display: block;
	}
	.insights b {
		color: #f8fafc;
		font-size: 13px;
	}
	.insights small {
		margin-top: 2px;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.4;
	}
	ul {
		display: grid;
		gap: 6px;
		margin: 8px 0 0;
		padding: 0;
		list-style: none;
	}
	li {
		color: #f8fafc;
		font-size: 12px;
		line-height: 1.45;
	}
	.insights p,
	.metric-panel p {
		margin-top: 8px;
	}
	@media (max-width: 980px) {
		header,
		.decision-grid {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 520px) {
		.story-section {
			padding: 12px;
		}
		.metrics {
			grid-template-columns: 1fr;
		}
	}
</style>
