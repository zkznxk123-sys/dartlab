<script lang="ts">
	import type { Lang } from '../lib/types';
	import type { RegimeMarketView, RegimeQuadrantView } from '../lib/macroLens';

	interface Props {
		view: RegimeQuadrantView;
		lang: Lang;
	}
	let { view, lang }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const cellMarkets = (key: string) => view.markets.filter((m) => m.cellKey === key);
	const assetMark = (w: string) => w === 'overweight' ? '▲' : w === 'underweight' ? '▼' : '△';
	const marketLens = (m: RegimeMarketView) => `${T('국면 모델', 'phase')}: ${lang === 'en' ? m.phase : m.phaseLabel} · ${T('격자', 'grid')}: ${m.quadrantLabel}`;
</script>

<section class={'rq ' + view.freshness.status} aria-label="Regime quadrant">
	<div class="rqTop">
		<span>{T('성장', 'growth')} ↑</span>
		<b>{T('물가', 'inflation')} →</b>
		<em>{view.asOf ?? '—'} · {view.freshness.label}</em>
	</div>
	<div class="rqGrid">
		{#each view.cells as cell (cell.key)}
			<div class={'rqCell ' + cell.key} class:active={cellMarkets(cell.key).length > 0}>
				<span>{T(cell.labelKr, cell.labelEn)}</span>
				<div class="rqMarks">
					{#each cellMarkets(cell.key) as market (market.market)}
						<i title={marketLens(market)}>{market.market}</i>
					{/each}
				</div>
			</div>
		{/each}
	</div>
	<div class="rqLens">
		{#each view.markets as market (market.market)}
			<div class="rqLensRow" title={market.description}>
				<b>{market.market}</b>
				<span>{marketLens(market)}</span>
				<em>{market.transitionLabel}</em>
			</div>
		{/each}
	</div>
	<div class="rqAssets">
		{#each view.markets[0]?.assets ?? [] as asset (asset.key)}
			<span class={'assetChip ' + asset.tone} title={asset.weight}>{lang === 'en' ? asset.labelEn : asset.labelKr}{assetMark(asset.weight)}</span>
		{/each}
	</div>
</section>

<style>
	.rq { padding: 7px; display: flex; flex-direction: column; gap: 5px; min-width: 0; }
	.rqTop { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; gap: 6px; align-items: center; color: var(--dim); font-size: 8.5px; font-family: var(--mono); }
	.rqTop span, .rqTop b, .rqTop em { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-style: normal; }
	.rqTop b { color: var(--amber); font-weight: 700; }
	.rq.stale .rqTop em, .rq.watch .rqTop em { color: var(--warn); }
	.rqGrid { display: grid; grid-template-columns: 1fr 1fr; border: 1px solid var(--bd); border-radius: 3px; overflow: hidden; min-height: 70px; }
	.rqCell { min-width: 0; min-height: 35px; display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 4px; padding: 5px 6px; border-right: 1px solid var(--bd); border-bottom: 1px solid var(--bd); background: rgba(255,255,255,.012); }
	.rqCell:nth-child(2n) { border-right: 0; }
	.rqCell:nth-last-child(-n+2) { border-bottom: 0; }
	.rqCell.active { background: rgba(52, 211, 153, .055); box-shadow: inset 0 0 0 1px rgba(52, 211, 153, .28); }
	.rqCell span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dim); font-size: 9px; font-weight: 700; }
	.rqMarks { display: flex; flex-direction: column; gap: 2px; }
	.rqMarks i { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 14px; border: 1px solid rgba(251,146,60,.45); border-radius: 999px; color: var(--amber); background: rgba(251,146,60,.055); font-style: normal; font-size: 8px; font-family: var(--mono); font-weight: 800; }
	.rqLens { display: grid; gap: 2px; min-width: 0; }
	.rqLensRow { display: grid; grid-template-columns: 22px minmax(0, 1fr); gap: 5px; align-items: baseline; min-width: 0; }
	.rqLensRow b { color: var(--amber); font-family: var(--mono); font-size: 9px; }
	.rqLensRow span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--fg); font-size: 9.5px; }
	.rqLensRow em { grid-column: 2; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dim); font-style: normal; font-size: 8.5px; }
	.rqAssets { display: flex; flex-wrap: wrap; gap: 3px; min-width: 0; }
</style>
