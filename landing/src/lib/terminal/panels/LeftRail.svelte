<script lang="ts">
	import type { Engine } from '../data/engine';
	import { gradeTone } from '../data/engine';
	import type { Lang } from '../data/types';
	import Panel from '../ui/Panel.svelte';
	import { tx, txc, chgClass, sign, heat } from '../ui/helpers';

	interface Props {
		eng: Engine;
		lang: Lang;
		active: string;
		onPick: (code: string) => void;
	}
	let { eng, lang, active, onPick }: Props = $props();

	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';
	const macro = $derived(eng.raw.macro);
	const screenerCodes = $derived(eng.featured(18));
	const sectors = $derived(eng.sectorPerf().slice(0, 12));
	const sectorMax = $derived(Math.max(...sectors.map((x) => Math.abs(x.chg)), 1));
	const moverRows = $derived(
		eng
			.featured(60)
			.map((c) => ({ c, p: eng.priceOf(c), name: eng.nameOf(c) }))
			.filter((r) => r.p && r.p.return1m != null)
			.sort((a, b) => (b.p!.return1m as number) - (a.p!.return1m as number))
	);
	const gainers = $derived(moverRows.slice(0, 6));
	const losers = $derived(moverRows.slice(-6).reverse());

	const assetChips: [string, string][] = [['주식', 'equity'], ['채권', 'bond'], ['원자재', 'commodity'], ['금', 'gold'], ['물가채', 'tips'], ['현금', 'cash']];
	const wcls = (w: string) => (w === 'overweight' ? 'ow' : w === 'underweight' ? 'uw' : 'nu');
</script>

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
						{#each assetChips as [kr, key] (key)}
							<span class={'assetChip ' + wcls(q.assetImplication?.[key])}>{lang === 'en' ? key.slice(0, 4) : kr}</span>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</Panel>
{/if}

<Panel {lang} className="eQuant" prov="live" title={{ kr: '스캔 스크리너', en: 'SCAN SCREENER' }} sub={{ kr: 'ecosystem 등급', en: 'ecosystem grades' }} flush>
	{#snippet right()}<span class="dim">{screenerCodes.length}</span>{/snippet}
	<div style="overflow-y:auto;max-height:300px;">
		{#each screenerCodes as c (c)}
			{@const eco = eng.raw.eco?.nodes.find((n) => n.id === c)}
			{@const px = eng.priceOf(c)}
			{#if px}
				{@const pills = [{ v: eco?.profGrade, t: gradeTone('prof', eco?.profGrade) }, { v: eco?.growthGrade, t: gradeTone('growth', eco?.growthGrade) }].filter((p) => p.v)}
				<div class={'scrRow' + (active === c ? ' on' : '')} role="button" tabindex="0" onclick={() => onPick(c)} onkeydown={(e) => e.key === 'Enter' && onPick(c)}>
					<span class="scrName"><b>{eng.nameOf(c)}</b><span class="si">{c} · {eco?.industryName || ''}</span></span>
					<span class="scrGrades">{#each pills as p, i (i)}<span class={'gPill ' + tcls(p.t)}>{p.v}</span>{/each}</span>
					<span class={'scrRet ' + chgClass(px.return1m)}>{sign(px.return1m, 1)}</span>
				</div>
			{/if}
		{/each}
	</div>
</Panel>

<Panel {lang} className="eIndustry" prov="live" title={{ kr: '섹터 맵', en: 'SECTOR MAP' }} sub={{ kr: '평균 1M', en: 'avg 1M' }}>
	<div class="sectorGrid">
		{#each sectors as x (x.id)}
			<div class="sectorCell" style={`background:${heat(x.chg, sectorMax)}`}>
				<span class="sName">{txc(x, lang)}</span>
				<span class={'sChg ' + chgClass(x.chg)}>{sign(x.chg, 1)}</span>
			</div>
		{/each}
	</div>
</Panel>

<Panel {lang} className="eQuant" prov="live" title={{ kr: '톱 무버스', en: 'TOP MOVERS' }} sub={{ kr: '1M', en: '1M' }} flush>
	<div class="moversWrap">
		<div class="moverCol">
			<div class="moverHd tUp">▲ {lang === 'en' ? 'GAINERS' : '상승'}</div>
			{#each gainers as r (r.c)}
				<div class="moverRow" role="button" tabindex="0" onclick={() => onPick(r.c)} onkeydown={(e) => e.key === 'Enter' && onPick(r.c)}>
					<span class="mn">{r.name}</span><span class={'mv ' + chgClass(r.p!.return1m)}>{sign(r.p!.return1m, 1)}</span>
				</div>
			{/each}
		</div>
		<div class="moverCol">
			<div class="moverHd tDn">▼ {lang === 'en' ? 'LOSERS' : '하락'}</div>
			{#each losers as r (r.c)}
				<div class="moverRow" role="button" tabindex="0" onclick={() => onPick(r.c)} onkeydown={(e) => e.key === 'Enter' && onPick(r.c)}>
					<span class="mn">{r.name}</span><span class={'mv ' + chgClass(r.p!.return1m)}>{sign(r.p!.return1m, 1)}</span>
				</div>
			{/each}
		</div>
	</div>
</Panel>
