<script lang="ts">
	import { MACRO_SERIES, MACRO_ATTRIBUTION, type MacroPoint, type MacroSeriesDef, type MacroPort } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';
	import {
		applyTransform, historyExtent, currentPosition,
		categoryOf, matchesCountry, BOARD_CATEGORIES, type MacroTransform
	} from '../lib/macroBoard';
	import MacroSeriesChart from './MacroSeriesChart.svelte';

	// 매크로 상황판 — 회사 무관 거시 보드. 조작(국가·기간·변환)→즉시 재렌더, hover 연결, 행 클릭 확대.
	// 무판정: 판정/추천 라벨 0. 데이터는 MacroPort.getSeries(다년 시계열) 소비.
	interface Props {
		macro: MacroPort;
		lang: Lang;
	}
	let { macro, lang }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);

	// ── 전역 조작 상태 ──
	let country = $state<'KR' | 'US' | 'both'>('both');
	let windowYears = $state(5); // 0 = Max
	let transform = $state<MacroTransform>('level');
	let showRef = $state(true);
	let brushMs = $state<number | null>(null);
	let expandedId = $state<string | null>(null);

	const WINDOWS: { y: number; label: string }[] = [
		{ y: 1, label: '1Y' }, { y: 5, label: '5Y' }, { y: 10, label: '10Y' }, { y: 0, label: 'Max' }
	];
	const TRANSFORMS: { k: MacroTransform; kr: string; en: string }[] = [
		{ k: 'level', kr: '수준', en: 'Level' }, { k: 'yoy', kr: '전년비', en: 'YoY' }, { k: 'z', kr: 'z-점수', en: 'z-score' }
	];

	// ── 시리즈 로드 (보드 mount 시 일괄 — parquet 1회 fetch·캐시) ──
	let series = $state<Map<string, MacroPoint[]>>(new Map());
	let loading = $state(true);
	$effect(() => {
		let alive = true;
		loading = true;
		Promise.all(MACRO_SERIES.map(async (d) => [d.id, (await macro.getSeries(d.id)) ?? []] as const))
			.then((entries) => {
				if (!alive) return;
				series = new Map(entries);
				loading = false;
			})
			.catch(() => { if (alive) loading = false; });
		return () => { alive = false; };
	});

	const defOf = (id: string) => MACRO_SERIES.find((d) => d.id === id);
	const ptsOf = (id: string): MacroPoint[] => series.get(id) ?? [];

	// 기준선 — z→0(평균선) · 핵심 인플레→2% 목표 · 곡선 스프레드→0(역전선) · 그 외 없음.
	function refLineFor(def: MacroSeriesDef): number | null {
		if (!showRef) return null;
		if (transform === 'z') return 0;
		if (['CPI', 'CPIAUCSL', 'CPILFESL', 'PCEPI'].includes(def.id)) return 2;
		if (['T10Y2Y', 'T10Y3M'].includes(def.id)) return 0;
		return null;
	}
	const displayUnit = (def: MacroSeriesDef) => transform === 'z' ? 'σ' : transform === 'yoy' && !def.yoy ? '%' : def.unit;
	const digitsOf = (def: MacroSeriesDef) => transform === 'z' ? 2 : def.digits ?? 1;
	const fmt = (v: number | null, def: MacroSeriesDef) =>
		v == null ? '—' : v.toLocaleString('en-US', { minimumFractionDigits: digitsOf(def), maximumFractionDigits: digitsOf(def) });

	// 행 통계 — 현재/이전/역사위치는 *전체* 시계열 기준(TradingEconomics Last/Prev/Hi-Lo).
	function rowStat(def: MacroSeriesDef) {
		const full = applyTransform(ptsOf(def.id), transform, def, 0);
		const raw = ptsOf(def.id);
		return {
			cur: full.length ? full[full.length - 1].v : null,
			prev: full.length > 1 ? full[full.length - 2].v : null,
			pos: currentPosition(full),
			ext: historyExtent(full),
			lastDate: raw.length ? raw[raw.length - 1].d : null
		};
	}

	// 카테고리별 가시 시리즈(국가 필터).
	const visibleByCategory = $derived(BOARD_CATEGORIES.map((c) => ({
		...c,
		series: MACRO_SERIES.filter((d) => categoryOf(d) === c.key && matchesCountry(d, country))
	})).filter((c) => c.series.length));

	// 국면 평면(성장×물가)은 좌측 패널 "마켓 펄스" 계기판 소관 — 다이얼로그는 *구체 데이터*만(중복 제거).
	const expandedDef = $derived(expandedId ? defOf(expandedId) : null);
	const ymd = (d: string | null) => d ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}` : '—';
</script>

<div class="mb">
	<!-- 전역 조작바 -->
	<div class="mbBar">
		<div class="mbSeg" role="group" aria-label={T('국가', 'country')}>
			{#each [{ k: 'KR', l: 'KR' }, { k: 'US', l: 'US' }, { k: 'both', l: T('둘다', 'Both') }] as o (o.k)}
				<button class:on={country === o.k} onclick={() => (country = o.k as typeof country)}>{o.l}</button>
			{/each}
		</div>
		<div class="mbSeg" role="group" aria-label={T('기간', 'window')}>
			{#each WINDOWS as w (w.label)}<button class:on={windowYears === w.y} onclick={() => (windowYears = w.y)}>{w.label}</button>{/each}
		</div>
		<div class="mbSeg" role="group" aria-label={T('변환', 'transform')}>
			{#each TRANSFORMS as t (t.k)}<button class:on={transform === t.k} onclick={() => (transform = t.k)}>{T(t.kr, t.en)}</button>{/each}
		</div>
		<button class="mbToggle" class:on={showRef} onclick={() => (showRef = !showRef)} title={T('기준선(목표·0·평균)', 'reference lines')}>{T('기준선', 'refs')}</button>
		<span class="mbAttr">{MACRO_ATTRIBUTION}</span>
	</div>

	{#if loading}
		<div class="mbLoading">{T('시계열 불러오는 중…', 'loading time series…')}</div>
	{:else}
		<!-- 카테고리 시계열 보드 (주역) — 국면 평면은 좌측 패널 계기판 -->
		{#each visibleByCategory as cat (cat.key)}
			<details class="mbCat" open>
				<summary><span class="mbCatK">{cat.key}</span><i>{cat.en} · {cat.series.length}</i></summary>
				<div class="mbRows">
					<div class="mbRowHead">
						<span>{T('지표', 'Indicator')}</span><span>{T('추이', 'Trend')}</span><span class="r">{T('현재', 'Last')}</span><span class="r">{T('이전', 'Prev')}</span><span>{T('역사 위치', 'History')}</span><span class="r">{T('기준일', 'Date')}</span>
					</div>
					{#each cat.series as def (def.id)}
						{@const s = rowStat(def)}
						<button class="mbRow" class:on={expandedId === def.id} onclick={() => (expandedId = expandedId === def.id ? null : def.id)} aria-label={T(def.kr, def.en)}>
							<span class="mbName"><b>{T(def.kr, def.en)}</b><em>{def.id}{def.group ? ` · ${def.group}` : ''}</em></span>
							<span class="mbSpark"><MacroSeriesChart points={ptsOf(def.id)} {def} {transform} {windowYears} {lang} compact shading refLine={refLineFor(def)} {brushMs} onBrush={(m) => (brushMs = m)} /></span>
							<span class="mbCur r mono">{fmt(s.cur, def)}<i>{displayUnit(def)}</i></span>
							<span class="mbPrev r mono">{fmt(s.prev, def)}</span>
							<span class="mbHist">
								{#if s.ext && s.pos != null}
									<i class="mbHistBar"><b style={`left:${(s.pos * 100).toFixed(0)}%`}></b></i>
									<em>{fmt(s.ext.min, def)} ↔ {fmt(s.ext.max, def)}</em>
								{:else}<em>—</em>{/if}
							</span>
							<span class="mbDate r mono">{s.lastDate ? `${s.lastDate.slice(2, 4)}-${s.lastDate.slice(4, 6)}` : '—'}</span>
						</button>
					{/each}
				</div>
			</details>
		{/each}
	{/if}

	<!-- 확대 오버레이 -->
	{#if expandedDef}
		{@const s = rowStat(expandedDef)}
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div class="mbExpandScrim" role="presentation" onclick={() => (expandedId = null)}>
			<div class="mbExpand" role="dialog" aria-modal="true" tabindex="-1" aria-label={T(expandedDef.kr, expandedDef.en)} onclick={(e) => e.stopPropagation()}>
				<div class="mbExpandHead">
					<div><span class="mbCatK">{categoryOf(expandedDef)}</span><b>{T(expandedDef.kr, expandedDef.en)}</b><em class="mono">{expandedDef.id}</em></div>
					<button class="mbX" onclick={() => (expandedId = null)} aria-label="close">✕</button>
				</div>
				<div class="mbExpandChart">
					<MacroSeriesChart points={ptsOf(expandedDef.id)} def={expandedDef} {transform} {windowYears} {lang} shading refLine={refLineFor(expandedDef)} {brushMs} onBrush={(m) => (brushMs = m)} />
				</div>
				<div class="mbExpandMeta">
					<div><span>{T('현재', 'Last')}</span><b>{fmt(s.cur, expandedDef)}{displayUnit(expandedDef)}</b></div>
					<div><span>{T('이전', 'Prev')}</span><b>{fmt(s.prev, expandedDef)}{displayUnit(expandedDef)}</b></div>
					<div><span>{T('역사 최저', 'Low')}</span><b>{fmt(s.ext?.min ?? null, expandedDef)}</b></div>
					<div><span>{T('역사 최고', 'High')}</span><b>{fmt(s.ext?.max ?? null, expandedDef)}</b></div>
					<div><span>{T('기준일', 'Date')}</span><b>{ymd(s.lastDate)}</b></div>
					<div><span>{T('출처', 'Source')}</span><b>{expandedDef.src.toUpperCase()} · {expandedDef.id}</b></div>
				</div>
				<div class="mbExpandNote">{T('변환·기간은 상단 조작바로 전환 · 구성 분해는 해당 지표에 구성 시계열이 있을 때만(현재 미제공)', 'transform/window via the top bar · component decomposition only where component series exist (not provided yet)')}</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.mb { display: flex; flex-direction: column; gap: 10px; }
	/* 조작바 — sticky 상단 */
	.mbBar { position: sticky; top: 0; z-index: 3; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 2px; background: var(--panel); border-bottom: 1px solid var(--bd); }
	.mbSeg { display: inline-flex; border: 1px solid var(--bd); border-radius: 6px; overflow: hidden; }
	.mbSeg button { border: 0; background: transparent; color: var(--dim); font-size: 10px; font-weight: 700; padding: 4px 9px; cursor: pointer; border-right: 1px solid var(--bd); }
	.mbSeg button:last-child { border-right: 0; }
	.mbSeg button:hover { color: var(--txt); }
	.mbSeg button.on { background: rgba(var(--amber-rgb), 0.14); color: var(--amber); }
	.mbToggle { border: 1px solid var(--bd); border-radius: 6px; background: transparent; color: var(--dim); font-size: 10px; font-weight: 700; padding: 4px 9px; cursor: pointer; }
	.mbToggle.on { color: var(--good); border-color: rgba(96, 165, 250, 0.4); }
	.mbAttr { margin-left: auto; color: var(--dimmer); font-size: 9px; }
	.mbLoading { padding: 40px; text-align: center; color: var(--dim); font-size: 11px; }
	/* 카테고리 */
	.mbCat { border: 1px solid var(--bd); border-radius: 8px; background: rgba(255, 255, 255, 0.012); overflow: hidden; }
	.mbCat > summary { cursor: pointer; list-style: none; display: flex; align-items: baseline; gap: 8px; padding: 8px 11px; }
	.mbCat > summary::-webkit-details-marker { display: none; }
	.mbCatK { font-size: 11px; font-weight: 800; color: var(--amber); letter-spacing: 0.04em; }
	.mbCat > summary i { font-style: normal; color: var(--dimmer); font-size: 9px; }
	.mbRows { padding: 0 4px 6px; }
	.mbRowHead, .mbRow { display: grid; grid-template-columns: minmax(120px, 1.5fr) minmax(90px, 1.4fr) 64px 56px minmax(120px, 1.2fr) 50px; gap: 8px; align-items: center; padding: 4px 7px; }
	.mbRowHead { font-size: 8.5px; font-weight: 800; color: var(--dimmer); letter-spacing: 0.04em; text-transform: uppercase; border-bottom: 1px solid var(--bd); }
	.mbRowHead .r, .mbRow .r { text-align: right; justify-self: end; }
	.mbRow { border: 0; background: transparent; color: var(--txt); text-align: left; cursor: pointer; border-top: 1px solid rgba(255, 255, 255, 0.04); border-radius: 5px; }
	.mbRow:hover, .mbRow.on { background: rgba(var(--amber-rgb), 0.05); }
	.mbName { display: flex; flex-direction: column; min-width: 0; gap: 1px; }
	.mbName b { font-size: 11px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mbName em { font-style: normal; color: var(--dimmer); font-size: 8px; font-family: var(--mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mbSpark { height: 34px; min-width: 0; }
	.mbCur { font-size: 12px; font-weight: 700; }
	.mbCur i { font-style: normal; font-size: 8px; color: var(--dimmer); margin-left: 1px; }
	.mbPrev { font-size: 10px; color: var(--dim); }
	.mbHist { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
	.mbHistBar { position: relative; display: block; height: 4px; border-radius: 999px; background: rgba(255, 255, 255, 0.08); }
	.mbHistBar b { position: absolute; top: 50%; width: 6px; height: 6px; border-radius: 50%; background: var(--good); transform: translate(-50%, -50%); }
	.mbHist em { font-style: normal; color: var(--dimmer); font-size: 8px; font-family: var(--mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mbDate { font-size: 9px; color: var(--dim); }
	.mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }
	/* 확대 오버레이 */
	.mbExpandScrim { position: fixed; inset: 0; z-index: 20; display: flex; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.55); padding: 24px; }
	.mbExpand { width: min(860px, 94vw); background: var(--panel); border: 1px solid var(--bdHi); border-radius: 10px; padding: 14px 16px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5); }
	.mbExpandHead { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
	.mbExpandHead div { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
	.mbExpandHead b { font-size: 14px; font-weight: 700; }
	.mbExpandHead em { color: var(--dimmer); font-size: 10px; }
	.mbX { border: 0; background: transparent; color: var(--dim); font-size: 14px; cursor: pointer; }
	.mbX:hover { color: var(--amber); }
	.mbExpandChart { height: 300px; margin: 10px 0; }
	.mbExpandMeta { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; }
	.mbExpandMeta div { border: 1px solid var(--bd); border-radius: 5px; padding: 5px 7px; min-width: 0; }
	.mbExpandMeta span { display: block; color: var(--dimmer); font-size: 8px; font-weight: 800; text-transform: uppercase; }
	.mbExpandMeta b { display: block; margin-top: 2px; font-family: var(--mono); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mbExpandNote { margin-top: 8px; color: var(--dimmer); font-size: 9px; line-height: 1.3; }
	@media (max-width: 720px) {
		.mbRowHead, .mbRow { grid-template-columns: minmax(90px, 1.3fr) 1fr 56px 64px; }
		.mbRowHead span:nth-child(4), .mbRow > .mbPrev, .mbRowHead span:nth-child(5), .mbRow > .mbHist { display: none; }
		.mbExpandMeta { grid-template-columns: repeat(3, 1fr); }
	}
</style>
