<script lang="ts">
	import { base } from '$app/paths';
	import type { Engine } from '../data/engine';
	import { gradeTone } from '../data/engine';
	import type { EcoNode, Lang } from '../data/types';
	import Panel from '../ui/Panel.svelte';
	import { txc, chgClass, sign, heat } from '../ui/helpers';

	interface Props {
		eng: Engine;
		lang: Lang;
		active: string;
		onPick: (code: string) => void;
	}
	let { eng, lang, active, onPick }: Props = $props();
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	let lens = $state<'econ' | 'price' | 'fin'>('price');

	// scan 와 동일 universe: finance+prices 보유 회사
	const nodes = $derived(
		(eng.raw.eco?.nodes || []).filter((n) => eng.raw.finance.companies[n.id] && eng.priceOf(n.id))
	);

	// ── 주가 렌즈 ──
	type PriceKey = 'return1m' | 'return3m' | 'return1y' | 'volatility1y';
	let priceKey = $state<PriceKey>('return1y');
	const priceMetrics: { k: PriceKey; kr: string; en: string }[] = [
		{ k: 'return1m', kr: '1M', en: '1M' },
		{ k: 'return3m', kr: '3M', en: '3M' },
		{ k: 'return1y', kr: '1Y', en: '1Y' },
		{ k: 'volatility1y', kr: 'σ', en: 'σ' }
	];
	const priceRows = $derived(
		nodes
			.map((n) => ({ n, v: (eng.priceOf(n.id) as Record<string, number | null>)[priceKey] }))
			.filter((r) => r.v != null)
			.sort((a, b) => (b.v as number) - (a.v as number))
			.slice(0, 26)
	);

	// ── 재무 렌즈 ──
	type FinKey = 'roe' | 'opMargin' | 'revCagr' | 'marketShare';
	let finKey = $state<FinKey>('roe');
	const finMetrics: { k: FinKey; kr: string; en: string; unit: string }[] = [
		{ k: 'roe', kr: 'ROE', en: 'ROE', unit: '%' },
		{ k: 'opMargin', kr: '영업이익률', en: 'OPM', unit: '%' },
		{ k: 'revCagr', kr: '매출성장', en: 'CAGR', unit: '%' },
		{ k: 'marketShare', kr: '점유율', en: 'Share', unit: '%' }
	];
	const finRows = $derived(
		nodes
			.map((n) => ({ n, v: (n as Record<string, number | null | undefined>)[finKey] }))
			.filter((r) => r.v != null)
			.sort((a, b) => (b.v as number) - (a.v as number))
			.slice(0, 26)
	);
	const finPill = (n: EcoNode): { v?: string; t: string } => ({ v: n.profGrade, t: gradeTone('prof', n.profGrade) });

	// ── 경제 렌즈 ──
	const macro = $derived(eng.raw.macro);
	const sectors = $derived(eng.sectorPerf().slice(0, 15));
	const sectorMax = $derived(Math.max(...sectors.map((x) => Math.abs(x.chg)), 1));
	const assetChips: [string, string][] = [['주식', 'equity'], ['채권', 'bond'], ['원자재', 'commodity'], ['금', 'gold'], ['물가채', 'tips'], ['현금', 'cash']];
	const wcls = (w?: string) => (w === 'overweight' ? 'ow' : w === 'underweight' ? 'uw' : 'nu');

	const lensTabs = [
		{ k: 'econ', kr: '경제', en: 'ECON' },
		{ k: 'price', kr: '주가', en: 'PRICE' },
		{ k: 'fin', kr: '재무', en: 'FIN' }
	] as const;
	const fmtMetric = (v: number | null | undefined, unit: string) => (v == null ? '—' : (v >= 0 && unit === '%' ? '' : '') + v.toFixed(1) + unit);
</script>

<div class="lensBar">
	{#each lensTabs as t (t.k)}
		<button class={'lensTab' + (lens === t.k ? ' on' : '')} onclick={() => (lens = t.k as typeof lens)}>{lang === 'en' ? t.en : t.kr}</button>
	{/each}
	<a class="lensScan" href="{base}/scan" target="_blank" rel="noopener" title="전체 조건 조사 — scan 보드">조건조사 ↗</a>
</div>

{#if lens === 'econ'}
	{#if macro}
		<Panel {lang} className="eMacro" prov="live" title={{ kr: '마켓 펄스 · 매크로', en: 'MARKET PULSE' }} sub={{ kr: 'dartlab.macro', en: 'dartlab.macro' }} flush>
			{#snippet right()}<span class="liveDot">LIVE</span>{/snippet}
			<div class="quadWrap">
				{#each [{ side: 'kr', label: 'KR' }, { side: 'us', label: 'US' }] as box (box.side)}
					{@const m = box.side === 'kr' ? macro.kr : macro.us}
					{@const q = m.quadrant}
					<div class="quadBox">
						<div class="quadMkt">{box.label} · {lang === 'en' ? m.phase.toUpperCase() : m.phaseLabel}</div>
						<div class={'quadPhase ' + (q.growth === 'rising' || q.growth === '상승' ? 'tUp' : 'tDn')}>{lang === 'en' ? q.quadrant : q.quadrantLabel}</div>
						<div class="quadDesc">{q.description}</div>
						<div class="quadAssets">
							{#each assetChips as [kr, key] (key)}<span class={'assetChip ' + wcls(q.assetImplication?.[key])}>{lang === 'en' ? key.slice(0, 4) : kr}</span>{/each}
						</div>
					</div>
				{/each}
			</div>
		</Panel>
	{/if}
	<Panel {lang} className="eIndustry" prov="live" title={{ kr: '섹터 히트맵', en: 'SECTOR HEATMAP' }} sub={{ kr: '평균 1M', en: 'avg 1M' }}>
		<div class="sectorGrid">
			{#each sectors as x (x.id)}
				<div class="sectorCell" style={`background:${heat(x.chg, sectorMax)}`}>
					<span class="sName">{txc(x, lang)}</span>
					<span class={'sChg ' + chgClass(x.chg)}>{sign(x.chg, 1)}</span>
				</div>
			{/each}
		</div>
	</Panel>
{:else if lens === 'price'}
	<Panel {lang} className="eQuant" prov="live" title={{ kr: '주가 랭킹', en: 'PRICE RANK' }} sub={{ kr: nodes.length + '종목', en: 'n=' + nodes.length }} flush>
		{#snippet right()}<span class="segGroup mini">{#each priceMetrics as m (m.k)}<button class={priceKey === m.k ? 'seg on' : 'seg'} onclick={() => (priceKey = m.k)}>{lang === 'en' ? m.en : m.kr}</button>{/each}</span>{/snippet}
		<div class="rankList">
			{#each priceRows as r, i (r.n.id)}
				<div class={'rankRow' + (active === r.n.id ? ' on' : '')} role="button" tabindex="0" onclick={() => onPick(r.n.id)} onkeydown={(e) => e.key === 'Enter' && onPick(r.n.id)}>
					<span class="rkN mono">{i + 1}</span>
					<span class="rkName"><b>{eng.nameOf(r.n.id)}</b><span class="rkInd">{r.n.industryName || ''}</span></span>
					<span class={'rkVal mono ' + (priceKey === 'volatility1y' ? 'tNeu' : chgClass(r.v))}>{r.v == null ? '—' : (priceKey === 'volatility1y' ? r.v.toFixed(0) : sign(r.v, 1)) + '%'}</span>
				</div>
			{/each}
		</div>
	</Panel>
{:else}
	<Panel {lang} className="eAnalysis" prov="live" title={{ kr: '재무 랭킹', en: 'FINANCIAL RANK' }} sub={{ kr: nodes.length + '종목', en: 'n=' + nodes.length }} flush>
		{#snippet right()}<span class="segGroup mini">{#each finMetrics as m (m.k)}<button class={finKey === m.k ? 'seg on' : 'seg'} onclick={() => (finKey = m.k)}>{lang === 'en' ? m.en : m.kr}</button>{/each}</span>{/snippet}
		<div class="rankList">
			{#each finRows as r, i (r.n.id)}
				{@const pill = finPill(r.n)}
				<div class={'rankRow' + (active === r.n.id ? ' on' : '')} role="button" tabindex="0" onclick={() => onPick(r.n.id)} onkeydown={(e) => e.key === 'Enter' && onPick(r.n.id)}>
					<span class="rkN mono">{i + 1}</span>
					<span class="rkName"><b>{eng.nameOf(r.n.id)}</b><span class="rkInd">{r.n.industryName || ''}</span></span>
					{#if pill.v}<span class={'gPill ' + tcls(pill.t)}>{pill.v}</span>{/if}
					<span class="rkVal mono tNeu">{fmtMetric(r.v, finMetrics.find((m) => m.k === finKey)?.unit || '')}</span>
				</div>
			{/each}
		</div>
	</Panel>
{/if}
