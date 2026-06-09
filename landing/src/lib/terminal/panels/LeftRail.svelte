<script lang="ts">
	import { base } from '$app/paths';
	import type { Engine } from '../data/engine';
	import { gradeTone } from '../data/engine';
	import type { EcoNode, Lang } from '../data/types';
	import Panel from '../ui/Panel.svelte';
	import ScreenerModal from './ScreenerModal.svelte';
	import { txc, chgClass, sign, heat } from '../ui/helpers';

	interface Props {
		eng: Engine;
		lang: Lang;
		active: string;
		onPick: (code: string) => void;
	}
	let { eng, lang, active, onPick }: Props = $props();
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	// scan 와 동일 universe: finance+prices 보유 회사 (eng 불변 → 1 회 산출 후 캐시)
	const nodes = $derived(
		(eng.raw.eco?.nodes || []).filter((n) => eng.raw.finance.companies[n.id] && eng.priceOf(n.id))
	);
	// 소문자 회사명 사전 — 키 입력마다 nameOf().toLowerCase() 재계산 방지 (1 회 산출)
	const lowerNames = $derived(new Map(nodes.map((n) => [n.id, (eng.nameOf(n.id) || '').toLowerCase()])));

	// ── 통합 스크리너: 주가·재무를 한 행에 같이 표시, 컬럼 헤더 클릭 정렬 (제품급 조건검색기). ──
	type SortKey = 'return1y' | 'roe' | 'opMargin';
	interface ColDef { k: SortKey; kr: string; en: string; }
	const COLS: ColDef[] = [
		{ k: 'return1y', kr: '1Y', en: '1Y' },
		{ k: 'roe', kr: 'ROE', en: 'ROE' },
		{ k: 'opMargin', kr: '영업익', en: 'OPM' }
	];
	let sortKey = $state<SortKey>('return1y');
	let screenerOpen = $state(false);

	// 조건 검색 — query 즉시 반영(입력 반응성) + queryD 140ms 디바운스(무거운 rows 재계산 억제)
	let query = $state('');
	let queryD = $state('');
	$effect(() => {
		const q = query;
		const t = setTimeout(() => (queryD = q), 140);
		return () => clearTimeout(t);
	});
	let market = $state(''); // '' | 'KOSPI' | 'KOSDAQ'
	let sectorFilter = $state(''); // industry id (히트맵 셀 클릭)
	const MKT: Record<string, string> = { KOSPI: '유가증권', KOSDAQ: '코스닥' };
	const matchFilter = (n: EcoNode): boolean => {
		if (queryD) {
			const q = queryD.trim().toLowerCase();
			const name = lowerNames.get(n.id) || '';
			if (!name.includes(q) && !n.id.includes(queryD.trim())) return false;
		}
		if (market && n.market !== MKT[market]) return false;
		if (sectorFilter && n.industry !== sectorFilter) return false;
		return true;
	};
	// 주가(1Y) + 재무(ROE·영업이익률) 한 행에. ret1y=prices, roe/opMargin=eco node.
	const r1yOf = (n: EcoNode): number | null => { const px = eng.priceOf(n.id); return px ? ((px.return1y as number | null) ?? null) : null; };
	interface Row { n: EcoNode; r1y: number | null; roe: number | null; opm: number | null; }
	const rowOf = (n: EcoNode): Row => ({ n, r1y: r1yOf(n), roe: (n.roe ?? null) as number | null, opm: (n.opMargin ?? null) as number | null });
	const sortVal = (r: Row): number | null => (sortKey === 'return1y' ? r.r1y : sortKey === 'roe' ? r.roe : r.opm);
	const rows = $derived(
		nodes
			.filter(matchFilter)
			.map(rowOf)
			.filter((r) => sortVal(r) != null)
			.sort((a, b) => (sortVal(b) as number) - (sortVal(a) as number))
			.slice(0, 80)
	);
	const finPillOf = (n: EcoNode) => ({ v: n.profGrade, t: gradeTone('prof', n.profGrade) });
	const fmtPct = (v: number | null, d = 1): string => (v == null ? '—' : v.toFixed(d));

	// ── 경제 (최상단 고정) ──
	const macro = $derived(eng.raw.macro);
	const sectors = $derived(eng.sectorPerf().slice(0, 12));
	const sectorMax = $derived(Math.max(...sectors.map((x) => Math.abs(x.chg)), 1));
	const assetChips: [string, string][] = [['주식', 'equity'], ['채권', 'bond'], ['원자재', 'commodity'], ['금', 'gold'], ['물가채', 'tips'], ['현금', 'cash']];
	const wcls = (w?: string) => (w === 'overweight' ? 'ow' : w === 'underweight' ? 'uw' : 'nu');
	const toggleSector = (id: string) => (sectorFilter = sectorFilter === id ? '' : id);
	const activeSectorName = $derived(sectorFilter ? (sectors.find((s) => s.id === sectorFilter)?.kr || sectorFilter) : '');
	// 매크로 국면 → 순풍/역풍 섹터(blended). 칩 클릭 = 아래 스크리너 섹터 필터.
	const tailwinds = $derived(eng.sectorTailwinds());
	const twTop = $derived(tailwinds.slice(0, 3));
	const twBot = $derived(tailwinds.length > 3 ? tailwinds.slice(-3).reverse() : []);
	const macroAsOf = $derived(macro?.asOf ?? '');
</script>

<!-- 경제 — 최상단 고정 (탭 토글 폐지, 항상 노출) -->
{#if macro}
	<Panel {lang} className="eMacro" prov="live" title={{ kr: '마켓 펄스 · 매크로', en: 'MARKET PULSE' }} sub={{ kr: 'dartlab.macro' + (macroAsOf ? ' · ' + macroAsOf : ''), en: 'dartlab.macro' + (macroAsOf ? ' · ' + macroAsOf : '') }} flush>
		{#snippet right()}<span class="liveDot">LIVE</span>{/snippet}
		<div class="quadWrap">
			{#each [{ side: 'kr', label: 'KR' }, { side: 'us', label: 'US' }] as box (box.side)}
				{@const m = box.side === 'kr' ? macro.kr : macro.us}
				{@const q = m.quadrant}
				<div class="quadBox">
					<div class="quadMkt">{box.label} · {lang === 'en' ? m.phase.toUpperCase() : m.phaseLabel}{q.inflation ? ' · ' + (lang === 'en' ? 'infl ' + q.inflation : '물가 ' + q.inflation) : ''}</div>
					<div class={'quadPhase ' + (q.growth === 'rising' || q.growth === '상승' ? 'tUp' : 'tDn')}>{lang === 'en' ? q.quadrant : q.quadrantLabel}</div>
					<div class="quadDesc">{q.description}</div>
					<div class="quadAssets">
						{#each assetChips as [kr, key] (key)}<span class={'assetChip ' + wcls(q.assetImplication?.[key])}>{lang === 'en' ? key.slice(0, 4) : kr}</span>{/each}
					</div>
				</div>
			{/each}
		</div>
		{#if twTop.length}
			<div class="twRibbon">
				<span class="twHd tUp">{lang === 'en' ? 'TAILWIND' : '순풍'}</span>
				{#each twTop as t (t.id)}<button class={'twChip up' + (sectorFilter === t.id ? ' on' : '')} onclick={() => toggleSector(t.id)} title={'blended ' + t.blended.toFixed(2)}>{txc(t, lang)}</button>{/each}
				{#if twBot.length}<span class="twHd tDn">{lang === 'en' ? 'HEADWIND' : '역풍'}</span>{#each twBot as t (t.id)}<button class={'twChip dn' + (sectorFilter === t.id ? ' on' : '')} onclick={() => toggleSector(t.id)} title={'blended ' + t.blended.toFixed(2)}>{txc(t, lang)}</button>{/each}{/if}
			</div>
		{/if}
	</Panel>

<ScreenerModal {eng} {lang} open={screenerOpen} onClose={() => (screenerOpen = false)} onPick={(c) => { onPick(c); screenerOpen = false; }} />
{/if}
<Panel {lang} className="eIndustry" prov="live" title={{ kr: '섹터 히트맵', en: 'SECTOR HEATMAP' }} sub={{ kr: '평균 1M · 클릭=필터', en: 'avg 1M · click to filter' }}>
	<div class="sectorGrid">
		{#each sectors as x (x.id)}
			<div class={'sectorCell' + (sectorFilter === x.id ? ' on' : '')} role="button" tabindex="0"
				onclick={() => toggleSector(x.id)} onkeydown={(e) => e.key === 'Enter' && toggleSector(x.id)}
				style={`background:${heat(x.chg, sectorMax)}`}>
				<span class="sName">{txc(x, lang)}</span>
				<span class={'sChg ' + chgClass(x.chg)}>{sign(x.chg, 1)}</span>
			</div>
		{/each}
	</div>
</Panel>

<!-- 통합 스크리너 — 주가(1Y) + 재무(ROE·영업이익률) 한 행, 컬럼 클릭 정렬. 복합 조건은 상세검색 모달. -->
<Panel {lang} className="eQuant fillCol" prov="live" title={{ kr: '주가·재무 스크리너', en: 'SCREENER' }} sub={{ kr: nodes.length + '종목 · 정렬 ' + (COLS.find((c) => c.k === sortKey)?.kr ?? ''), en: 'n=' + nodes.length }} flush>
	{#snippet right()}<button class="scrOpenBtn" onclick={() => (screenerOpen = true)} title="상용급 다조건 검색">{lang === 'en' ? 'SCREEN' : '상세검색'}</button><a class="lensScan" href="{base}/scan" target="_blank" rel="noopener" title="전체 조건 조사 — scan 보드">조건조사 ↗</a>{/snippet}
	<div class="filtRow">
		<input class="filtInput" placeholder={lang === 'en' ? 'name/code' : '이름·코드'} bind:value={query} spellcheck={false} />
		<select class="filtSel" bind:value={market}><option value="">{lang === 'en' ? 'all market' : '전체 시장'}</option><option value="KOSPI">KOSPI</option><option value="KOSDAQ">KOSDAQ</option></select>
	</div>
	{#if sectorFilter}
		<div class="filtChipRow"><button class="filtChip" onclick={() => (sectorFilter = '')}>{lang === 'en' ? 'sector: ' : '섹터: '}{activeSectorName} ✕</button></div>
	{/if}
	<!-- 컬럼 헤더 (클릭=정렬) -->
	<div class="rkHead">
		<span class="rkHN">#</span>
		<span class="rkHName">{lang === 'en' ? 'Company' : '종목'}</span>
		{#each COLS as c (c.k)}
			<button class={'rkHCol' + (sortKey === c.k ? ' on' : '')} onclick={() => (sortKey = c.k)}>{lang === 'en' ? c.en : c.kr}{sortKey === c.k ? ' ▼' : ''}</button>
		{/each}
	</div>
	<div class="rankList">
		{#each rows as r, i (r.n.id)}
			{@const pill = finPillOf(r.n)}
			<div class={'rankRow' + (active === r.n.id ? ' on' : '')} role="button" tabindex="0" onclick={() => onPick(r.n.id)} onkeydown={(e) => e.key === 'Enter' && onPick(r.n.id)}>
				<span class="rkN mono">{i + 1}</span>
				<span class="rkName"><b>{eng.nameOf(r.n.id)}</b><span class="rkInd">{r.n.industryName || ''}{pill.v ? ' · ' + pill.v : ''}</span></span>
				<span class={'rkCol mono ' + chgClass(r.r1y)}>{r.r1y == null ? '—' : sign(r.r1y, 0) + '%'}</span>
				<span class={'rkCol mono ' + (sortKey === 'roe' ? tcls(pill.t) : 'tNeu')}>{fmtPct(r.roe)}</span>
				<span class="rkCol mono tNeu">{fmtPct(r.opm)}</span>
			</div>
		{/each}
	</div>
</Panel>
