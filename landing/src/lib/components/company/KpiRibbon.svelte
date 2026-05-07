<script lang="ts">
	import type { DashboardMetric } from '$lib/browser/companyDashboardModel';

	let {
		metrics = [],
		onSelect
	}: { metrics?: DashboardMetric[]; onSelect?: (metric: DashboardMetric) => void } = $props();

	function handleClick(metric: DashboardMetric) {
		if (typeof onSelect === 'function') onSelect(metric);
	}

	function values(metric: DashboardMetric): Array<number | null> {
		return metric.series.slice(-8);
	}

	function metricColor(metric: DashboardMetric): string {
		if (metric.id === 'revenue') return '#60a5fa';
		if (metric.id === 'op' || metric.id === 'opMargin') return '#fb923c';
		if (metric.id === 'net' || metric.id === 'roe' || metric.id === 'cashflow') return '#34d399';
		if (metric.id === 'debtRatio') return '#ef4444';
		return '#64748b';
	}

	function barStyle(metric: DashboardMetric, value: number | null): string {
		const nums = values(metric).filter((item): item is number => item != null && Number.isFinite(item));
		if (!nums.length || value == null || !Number.isFinite(value)) return 'height: 2px; opacity: 0.18; background: #64748b;';
		const min = Math.min(0, ...nums);
		const max = Math.max(...nums);
		const span = max - min || 1;
		const height = Math.max(3, ((value - min) / span) * 28 + 3);
		const color = value < 0 ? '#ef4444' : metricColor(metric);
		return `height: ${height.toFixed(1)}px; background: ${color};`;
	}
</script>

<section class="kpi-ribbon" aria-label="핵심 지표">
	{#each metrics as metric}
		<article
			class="kpi {metric.tone}"
			class:clickable={typeof onSelect === 'function'}
			role={typeof onSelect === 'function' ? 'button' : undefined}
			tabindex={typeof onSelect === 'function' ? 0 : undefined}
			onclick={() => handleClick(metric)}
			onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick(metric)}
		>
			<div class="top">
				<span>{metric.label}</span>
				{#if metric.note}<em>{metric.note}</em>{/if}
			</div>
			<strong>{metric.value}</strong>
			<div class="bottom">
				<small class={metric.deltaTone}>{metric.delta || metric.period || '비교 대기'}</small>
				{#if metric.note}<small>{metric.note}</small>{/if}
			</div>
			{#if values(metric).length}
				<div class="spark" aria-hidden="true">
					{#each values(metric) as value}
						<i class:negative={(value ?? 0) < 0} style={barStyle(metric, value)}></i>
					{/each}
				</div>
			{/if}
		</article>
	{/each}
</section>

<style>
	.kpi-ribbon {
		display: grid;
		grid-template-columns: repeat(8, minmax(0, 1fr));
		gap: 8px;
		max-width: var(--company-shell-width, 1320px);
		margin: 12px auto 0;
	}
	.kpi {
		min-width: 0;
		height: 132px;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: linear-gradient(180deg, #08101c 0%, #060b13 100%);
		padding: 11px;
		text-align: left;
	}
	.kpi.clickable {
		cursor: pointer;
		transition: border-color 0.15s ease, transform 0.15s ease;
	}
	.kpi.clickable:hover {
		border-color: #fb923c;
		transform: translateY(-1px);
	}
	.top,
	.bottom {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		align-items: center;
	}
	span,
	small,
	em {
		color: #94a3b8;
		font-size: 11px;
		font-style: normal;
	}
	em {
		color: #fbbf24;
	}
	strong {
		display: block;
		margin-top: 8px;
		min-height: 42px;
		color: #f8fafc;
		font-size: clamp(16px, 1vw, 20px);
		font-weight: 820;
		letter-spacing: 0;
		line-height: 1.08;
		overflow-wrap: anywhere;
		white-space: normal;
	}
	small.good {
		color: #34d399;
	}
	.bad strong,
	small.bad {
		color: #f87171;
	}
	.watch strong {
		color: #fbbf24;
	}
	small.watch {
		color: #fbbf24;
	}
	.missing strong {
		color: #64748b;
	}
	.spark {
		display: flex;
		align-items: end;
		gap: 3px;
		height: 28px;
		margin-top: 6px;
	}
	.spark i {
		display: block;
		flex: 1 1 0;
		min-width: 3px;
		border-radius: 2px 2px 0 0;
		background: #fb923c;
	}
	.spark i.negative {
		background: #ea4647;
	}
	@media (max-width: 1260px) {
		.kpi-ribbon {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}
	@media (max-width: 700px) {
		.kpi-ribbon {
			display: flex;
			gap: 8px;
			overflow-x: auto;
			overscroll-behavior-x: contain;
			padding-bottom: 6px;
			scroll-snap-type: x proximity;
			scrollbar-width: thin;
		}
		.kpi {
			flex: 0 0 142px;
			height: 112px;
			padding: 9px;
			scroll-snap-align: start;
		}
		strong {
			margin-top: 6px;
			min-height: 31px;
			font-size: 16px;
		}
		.spark {
			height: 22px;
			margin-top: 4px;
		}
	}
</style>
