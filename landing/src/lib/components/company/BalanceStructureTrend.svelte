<script lang="ts">
	import { formatTableValue, type BalanceStructureView } from '$lib/browser/companyDashboardModel';
	import LayerMiniBars from './LayerMiniBars.svelte';
	import LayerStackedBars from './LayerStackedBars.svelte';

	let { view }: { view: BalanceStructureView } = $props();

	function visibleDeltas() {
		return view.assetDeltaParts.filter((part) => !part.missing || part.id.startsWith('other'));
	}
	function liabilityTotal(): number | null {
		const values = view.fundingParts.filter((part) => part.id !== 'equity').map((part) => part.value);
		const nums = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
		return nums.length ? nums.reduce((sum, value) => sum + value, 0) : null;
	}
	function equityTotal(): number | null {
		const nums = view.equityParts.map((part) => part.value).filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
		return nums.length ? nums.reduce((sum, value) => sum + value, 0) : null;
	}
</script>

<article class="balance-trend">
	<header class="trend-head">
		<div>
			<h3>{view.title}</h3>
			<p>{view.sourceMode} · {view.sourceLabel}</p>
		</div>
		<div class="totals">
			<span>총자산 <strong>{formatTableValue(view.totalAssets, 'KRW')}</strong></span>
			<span>부채+자본 <strong>{formatTableValue(view.totalFunding, 'KRW')}</strong></span>
		</div>
	</header>

	<div class="trend-grid">
		<LayerMiniBars title="총자산 추이" periods={view.periods} values={view.totalAssetsSeries} unit="KRW" color="#60a5fa" />
		<LayerStackedBars title="자산 구성 100%" periods={view.periods} parts={view.assetTrendParts} />
		<LayerStackedBars title="조달 구성 100%" periods={view.periods} parts={view.fundingTrendParts} />
		<section class="delta-panel">
			<header>
				<span>최신 분기 자산 증감</span>
				<strong>{view.period ?? '기간 대기'}</strong>
			</header>
			<div class="delta-list">
				{#each visibleDeltas() as part}
					<div class:missing={part.missing}>
						<span><i style:background={part.color}></i>{part.label}</span>
						<strong>{formatTableValue(part.value, part.unit)}</strong>
					</div>
				{/each}
			</div>
		</section>
	</div>

	<div class="equation-row">
		<div>
			<span>자산</span>
			<strong>{formatTableValue(view.totalAssets, 'KRW')}</strong>
		</div>
		<b>=</b>
		<div>
			<span>부채</span>
			<strong>{formatTableValue(liabilityTotal(), 'KRW')}</strong>
		</div>
		<b>+</b>
		<div>
			<span>자본</span>
			<strong>{formatTableValue(equityTotal(), 'KRW')}</strong>
		</div>
		<div class="equity-inset">
			{#each view.equityTrendParts.filter((part) => !part.missing || part.id.startsWith('other')) as part}
				<span><i style:background={part.color}></i>{part.label}</span>
			{/each}
		</div>
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
	.balance-trend {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #050811;
		padding: 10px;
	}
	.trend-head {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		align-items: flex-start;
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
	.totals {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: 6px;
	}
	.totals span {
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #070c15;
		color: #94a3b8;
		font-size: 10px;
		padding: 5px 7px;
	}
	.totals strong {
		margin-left: 5px;
		color: #f8fafc;
	}
	.trend-grid {
		display: grid;
		grid-template-columns: 0.9fr 1.35fr 1.35fr 1fr;
		gap: 8px;
	}
	.delta-panel {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #070c15;
		padding: 9px;
	}
	.delta-panel header {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		align-items: baseline;
		margin-bottom: 7px;
	}
	.delta-panel header span,
	.delta-panel header strong {
		color: #b8c2d2;
		font-size: 11px;
		font-weight: 800;
	}
	.delta-list {
		display: grid;
		gap: 5px;
	}
	.delta-list div {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 8px;
		align-items: center;
		border-bottom: 1px solid #172033;
		padding: 5px 0;
	}
	.delta-list span,
	.equity-inset span {
		display: inline-flex;
		min-width: 0;
		align-items: center;
		gap: 5px;
		overflow: hidden;
		color: #94a3b8;
		font-size: 10px;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.delta-list strong {
		color: #f8fafc;
		font-size: 11px;
	}
	.delta-list .missing strong {
		color: #64748b;
	}
	i {
		width: 8px;
		height: 8px;
		border-radius: 2px;
		flex: 0 0 auto;
	}
	.equation-row {
		display: grid;
		grid-template-columns: 1fr auto 1fr auto 1fr minmax(220px, 1.4fr);
		gap: 8px;
		align-items: center;
		margin-top: 8px;
	}
	.equation-row > div {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #070c15;
		padding: 8px;
	}
	.equation-row b {
		color: #64748b;
		font-size: 18px;
	}
	.equation-row span,
	.equation-row strong {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.equation-row span {
		color: #94a3b8;
		font-size: 10px;
	}
	.equation-row strong {
		margin-top: 4px;
		color: #f8fafc;
		font-size: 13px;
	}
	.equity-inset {
		display: flex;
		flex-wrap: wrap;
		gap: 5px 10px;
	}
	.equity-inset span {
		display: inline-flex;
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
	.notes .watch {
		color: #fbbf24;
	}
	.notes .missing {
		color: #64748b;
	}
	@media (max-width: 1220px) {
		.trend-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.equation-row {
			grid-template-columns: 1fr auto 1fr auto 1fr;
		}
		.equity-inset {
			grid-column: 1 / -1;
		}
	}
	@media (max-width: 720px) {
		.trend-head,
		.trend-grid,
		.equation-row {
			grid-template-columns: 1fr;
		}
		.equation-row b {
			display: none;
		}
		.totals {
			justify-content: flex-start;
		}
	}
</style>
