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

	// ── 통합 스크리너: 주가·재무를 한 리스트에서 정렬·조건검색 (3탭 렌즈 폐지) ──
	type MetricKey = 'return1m' | 'return3m' | 'return1y' | 'volatility1y' | 'roe' | 'opMargin' | 'revCagr' | 'marketShare';
	type PriceK = 'return1m' | 'return3m' | 'return1y' | 'volatility1y';
	type FinK = 'roe' | 'opMargin' | 'revCagr' | 'marketShare';
	interface MetricDef { k: MetricKey; kr: string; en: string; fam: 'price' | 'fin'; unit: string; }
	const METRICS: MetricDef[] = [
		{ k: 'return1m', kr: '1M', en: '1M', fam: 'price', unit: '%' },
		{ k: 'return3m', kr: '3M', en: '3M', fam: 'price', unit: '%' },
		{ k: 'return1y', kr: '1Y', en: '1Y', fam: 'price', unit: '%' },
		{ k: 'volatility1y', kr: 'σ', en: 'σ', fam: 'price', unit: '' },
		{ k: 'roe', kr: 'ROE', en: 'ROE', fam: 'fin', unit: '%' },
		{ k: 'opMargin', kr: '영업이익률', en: 'OPM', fam: 'fin', unit: '%' },
		{ k: 'revCagr', kr: '매출성장', en: 'CAGR', fam: 'fin', unit: '%' },
		{ k: 'marketShare', kr: '점유율', en: 'Share', fam: 'fin', unit: '%' }
	];
	let metricKey = $state<MetricKey>('return1y');
	const activeMetric = $derived(METRICS.find((m) => m.k === metricKey) as MetricDef);
	let screenerOpen = $state(false);

	// 조건 검색 — query 는 입력 즉시 반영(입력칸 반응성), queryD 는 140ms 디바운스(무거운 rows 재계산 억제)
	let query = $state('');
	let queryD = $state('');
	$effect(() => {
		const q = query;
		const t = setTimeout(() => (queryD = q), 140);
		return () => clearTimeout(t);
	});
	let minVal = $state<number | null>(null);
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
	const valOf = (n: EcoNode): number | null => {
		if (activeMetric.fam === 'price') {
			const px = eng.priceOf(n.id);
			return px ? ((px[activeMetric.k as PriceK] as number | null) ?? null) : null;
		}
		return (n[activeMetric.k as FinK] ?? null) as number | null;
	};
	const rows = $derived(
		nodes
			.filter(matchFilter)
			.map((n) => ({ n, v: valOf(n) }))
			.filter((r) => r.v != null && (minVal == null || (r.v as number) >= minVal))
			.sort((a, b) => (b.v as number) - (a.v as number))
			.slice(0, 80)
	);
	const rowsMax = $derived(Math.max(...rows.map((r) => Math.abs(r.v as number)), 1));
	const isReturn = $derived(activeMetric.fam === 'price' && activeMetric.k !== 'volatility1y');
	const fmtVal = (v: number | null): string => {
		if (v == null) return '—';
		if (isReturn) return sign(v, 1) + '%';
		if (activeMetric.k === 'volatility1y') return v.toFixed(0);
		return v.toFixed(1) + activeMetric.unit;
	};
	const finPillOf = (n: EcoNode) => ({ v: n.profGrade, t: gradeTone('prof', n.profGrade) });

	// ── 경제 (최상단 고정) ──
	const macro = $derived(eng.raw.macro);
	const sectors = $derived(eng.sectorPerf().slice(0, 12));
	const sectorMax = $derived(Math.max(...sectors.map((x) => Math.abs(x.chg)), 1));
	const assetChips: [string, string][] = [['주식', 'equity'], ['채권', 'bond'], ['원자재', 'commodity'], ['금', 'gold'], ['물가채', 'tips'], ['현금', 'cash']];
	const wcls = (w?: string) => (w === 'overweight' ? 'ow' : w === 'underweight' ? 'uw' : 'nu');
	const toggleSector = (id: string) => (sectorFilter = sectorFilter === id ? '' : id);
	const activeSectorName = $derived(sectorFilter ? (sectors.find((s) => s.id === sectorFilter)?.kr || sectorFilter) : '');
</script>

<!-- 경제 — 최상단 고정 (탭 토글 폐지, 항상 노출) -->
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

<!-- 통합 스크리너 — 주가 + 재무 한 리스트, 조건 검색 -->
<Panel {lang} className="eQuant fillCol" prov="live" title={{ kr: '주가·재무 스크리너', en: 'SCREENER' }} sub={{ kr: nodes.length + '종목', en: 'n=' + nodes.length }} flush>
	{#snippet right()}<button class="scrOpenBtn" onclick={() => (screenerOpen = true)} title="상용급 다조건 검색">{lang === 'en' ? 'SCREEN' : '상세검색'}</button><a class="lensScan" href="{base}/scan" target="_blank" rel="noopener" title="전체 조건 조사 — scan 보드">조건조사 ↗</a>{/snippet}
	<div class="metricBar">
		{#each METRICS as m, i (m.k)}
			{#if i === 4}<span class="metricDiv"></span>{/if}
			<button class={'seg' + (metricKey === m.k ? ' on' : '')} onclick={() => (metricKey = m.k)}>{lang === 'en' ? m.en : m.kr}</button>
		{/each}
	</div>
	<div class="filtRow">
		<input class="filtInput" placeholder={lang === 'en' ? 'name/code' : '이름·코드'} bind:value={query} spellcheck={false} />
		<span class="filtCond">{lang === 'en' ? activeMetric.en : activeMetric.kr} ≥<input class="filtNum mono" type="number" bind:value={minVal} placeholder="—" /></span>
		<select class="filtSel" bind:value={market}><option value="">{lang === 'en' ? 'all' : '전체'}</option><option value="KOSPI">KOSPI</option><option value="KOSDAQ">KOSDAQ</option></select>
	</div>
	{#if sectorFilter}
		<div class="filtChipRow"><button class="filtChip" onclick={() => (sectorFilter = '')}>{lang === 'en' ? 'sector: ' : '섹터: '}{activeSectorName} ✕</button></div>
	{/if}
	<div class="rankList">
		{#each rows as r, i (r.n.id)}
			{@const pill = finPillOf(r.n)}
			<div class={'rankRow' + (active === r.n.id ? ' on' : '')} role="button" tabindex="0" onclick={() => onPick(r.n.id)} onkeydown={(e) => e.key === 'Enter' && onPick(r.n.id)}>
				<span class="rkN mono">{i + 1}</span>
				<span class="rkName"><b>{eng.nameOf(r.n.id)}</b><span class="rkInd">{r.n.industryName || ''}</span></span>
				{#if activeMetric.fam === 'fin' && pill.v}<span class={'gPill ' + tcls(pill.t)}>{pill.v}</span>{/if}
				<span class="rkMag">
					<span class="rkBar"><span class="rkBarFill" style={`width:${Math.min(100, (Math.abs(r.v as number) / rowsMax) * 100)}%;background:${isReturn ? ((r.v as number) >= 0 ? 'var(--up)' : 'var(--dn)') : 'var(--industry)'}`}></span></span>
					<span class={'rkVal mono ' + (isReturn ? chgClass(r.v) : 'tNeu')}>{fmtVal(r.v)}</span>
				</span>
			</div>
		{/each}
	</div>
</Panel>
