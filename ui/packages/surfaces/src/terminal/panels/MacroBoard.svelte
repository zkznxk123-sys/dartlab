<script lang="ts">
	import { MACRO_SERIES, MACRO_ATTRIBUTION, type MacroPoint, type MacroSeriesDef, type MacroPort } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';
	import {
		applyTransform, historyExtent, currentPosition, toZScore,
		momentumSign, zGap, quadOf, matchesCountry, type MacroTransform
	} from '../lib/macroBoard';
	import { MACRO_STATIONS, INVERT_SERIES, FLOW_OMITTED_NOTE, type MacroStation } from '../lib/macroStations';
	import MacroSeriesChart from './MacroSeriesChart.svelte';

	// 매크로 상황판 — 회사 무관 *가이드된 분석 흐름*(top-down 6 스테이션). 표 나열도 판정도 아님:
	// 각 스테이션 = 질문 → (방향집계·시계열·겹쳐보기·발산) → 인사이트 프롬프트 → 다음으로. 결론은 사용자.
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
	// 확대 — 단일 시리즈 또는 겹쳐보기 쌍.
	let expanded = $state<{ kind: 'series'; id: string } | { kind: 'overlay'; a: string; b: string } | null>(null);

	const WINDOWS: { y: number; label: string }[] = [
		{ y: 1, label: '1Y' }, { y: 5, label: '5Y' }, { y: 10, label: '10Y' }, { y: 0, label: 'Max' }
	];
	const TRANSFORMS: { k: MacroTransform; kr: string; en: string }[] = [
		{ k: 'level', kr: '수준', en: 'Level' }, { k: 'yoy', kr: '전년비', en: 'YoY' }, { k: 'z', kr: 'z-점수', en: 'z-score' }
	];
	const QUAD_LABEL: Record<string, { kr: string; en: string }> = {
		goldilocks: { kr: '골디락스 (성장↑물가↓)', en: 'Goldilocks (growth↑ infl↓)' },
		reflation: { kr: '리플레이션 (성장↑물가↑)', en: 'Reflation (growth↑ infl↑)' },
		stagflation: { kr: '스태그플레이션 (성장↓물가↑)', en: 'Stagflation (growth↓ infl↑)' },
		deflation: { kr: '디플레이션 (성장↓물가↓)', en: 'Deflation (growth↓ infl↓)' }
	};

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

	const defOf = (id: string): MacroSeriesDef | undefined => MACRO_SERIES.find((d) => d.id === id);
	const ptsOf = (id: string): MacroPoint[] => series.get(id) ?? [];
	const labelOf = (id: string) => { const d = defOf(id); return d ? T(d.kr, d.en) : id; };

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
	// 행 방향 화살표 — 값의 최근 방향(원시). 무판정(오르나/내리나 사실).
	const arrowOf = (id: string) => { const s = momentumSign(ptsOf(id)); return s === 'up' ? '▲' : s === 'down' ? '▼' : '–'; };

	// 스테이션의 가시 시리즈(국가 필터·존재).
	function visibleIds(st: MacroStation): string[] {
		return st.seriesIds.filter((id) => { const d = defOf(id); return d && matchesCountry(d, country) && ptsOf(id).length; });
	}
	// 방향집계(breadth) — 성장 방향 기준(INVERT_SERIES 부호 반전: 실업률↑=감속). 가속/감속/횡보 개수.
	function breadthOf(ids: string[]): { up: number; down: number; flat: number } {
		let up = 0, down = 0, flat = 0;
		for (const id of ids) {
			let s = momentumSign(ptsOf(id));
			if (INVERT_SERIES.has(id)) s = s === 'up' ? 'down' : s === 'down' ? 'up' : 'flat';
			if (s === 'up') up++; else if (s === 'down') down++; else flat++;
		}
		return { up, down, flat };
	}
	const hasInvert = (ids: string[]) => ids.some((id) => INVERT_SERIES.has(id));

	// ③ 국면 합성 — z 좌표(성장 세로·물가 가로)로 KR/US 사분면(평면 재현·자산가중치 금지).
	const zlast = (id: string): number | null => { const z = toZScore(ptsOf(id)); return z.length ? z[z.length - 1].v : null; };
	function regimePoint(growthId: string, inflId: string): { quad: string; g: number; i: number } | null {
		const g = zlast(growthId), i = zlast(inflId);
		if (g == null || i == null) return null;
		return { quad: quadOf(g, i), g, i };
	}
	const krRegime = $derived(series.size ? regimePoint('CLI', 'CPI') : null);
	const usRegime = $derived(series.size ? regimePoint('INDPRO', 'CPIAUCSL') : null);

	const expandedA = $derived(expanded ? defOf(expanded.kind === 'series' ? expanded.id : expanded.a) : null);
	const expandedB = $derived(expanded && expanded.kind === 'overlay' ? defOf(expanded.b) : null);
	const ymd = (d: string | null) => d ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}` : '—';
	const num1 = (v: number | null) => v == null ? '—' : v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
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
		<div class="mbIntro">{T('top-down 분석 흐름 — 성장 → 물가 → 국면 → 정책 → 금융여건 → 시장. 각 단계의 질문에 데이터로 스스로 답하고 다음으로.', 'Top-down flow — growth → inflation → regime → policy → conditions → markets. Answer each question from the data, then move on.')}</div>

		{#each MACRO_STATIONS as st (st.key)}
			{@const ids = visibleIds(st)}
			{@const b = breadthOf(ids)}
			<section class="mbStation" id={`macroStation-${st.key}`}>
				<div class="stHead">
					<span class="stNo">{st.order}</span>
					<div class="stTitleWrap">
						<b class="stTitle">{T(st.titleKr, st.titleEn)}</b>
						<span class="stQ">{T(st.questionKr, st.questionEn)}</span>
					</div>
					{#if !st.synthesis && ids.length}
						<span class="stBreadth" title={T('이 단계 지표들의 최근 방향(성장 기준)', 'recent direction of this station (growth-oriented)')}>
							<i class="bUp">▲{b.up}</i><i class="bDn">▼{b.down}</i>{#if b.flat}<i class="bFl">–{b.flat}</i>{/if}
						</span>
					{/if}
				</div>

				{#if st.synthesis}
					<!-- ③ 국면 합성 — quadOf 좌표(평면 재현·자산가중치 금지) -->
					<div class="stSynth">
						{#each [{ m: 'KR', r: krRegime }, { m: 'US', r: usRegime }] as row (row.m)}
							{#if row.r}
								<div class="synRow">
									<span class="synMkt">{row.m}</span>
									<b class="synQuad">{T(QUAD_LABEL[row.r.quad].kr, QUAD_LABEL[row.r.quad].en)}</b>
									<span class="synZ">{T('성장 z', 'growth z')} {num1(row.r.g)} · {T('물가 z', 'infl z')} {num1(row.r.i)}</span>
								</div>
							{/if}
						{/each}
						<div class="synNote">{T('성장·물가 모멘텀 z 좌표(역사 평균=0) · 추천·자산비중 아님 · 국면 평면 상세는 좌측 패널', 'growth/inflation momentum z (history mean = 0) · not advice/allocation · full plane in the left panel')}</div>
					</div>
				{:else if ids.length}
					<div class="mbRows">
						<div class="mbRowHead">
							<span>{T('지표', 'Indicator')}</span><span>{T('추이', 'Trend')}</span><span class="r">{T('현재', 'Last')}</span><span class="r">{T('이전', 'Prev')}</span><span>{T('역사 위치', 'History')}</span><span class="r">{T('기준일', 'Date')}</span>
						</div>
						{#each ids as id (id)}
							{@const def = defOf(id)}
							{#if def}
								{@const s = rowStat(def)}
								<button class="mbRow" onclick={() => (expanded = { kind: 'series', id })} aria-label={labelOf(id)}>
									<span class="mbName"><b>{arrowOf(id)} {T(def.kr, def.en)}</b><em>{def.id}</em></span>
									<span class="mbSpark"><MacroSeriesChart points={ptsOf(id)} {def} {transform} {windowYears} {lang} compact shading refLine={refLineFor(def)} {brushMs} onBrush={(m) => (brushMs = m)} /></span>
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
							{/if}
						{/each}
						{#if hasInvert(ids)}<div class="stInvertNote">{T('※ 실업률은 상승=둔화로 방향집계', '※ unemployment counted as slowing when it rises')}</div>{/if}
					</div>
				{:else}
					<div class="stEmpty">{T('이 국가 필터에 해당 지표 없음', 'no indicators for this country filter')}</div>
				{/if}

				<!-- 겹쳐보기 · 발산 (관계 검증) -->
				{#if st.overlays.length || st.divergences.length}
					<div class="stTools">
						{#each st.overlays as ov (ov.a + ov.b)}
							{#if defOf(ov.a) && defOf(ov.b)}
								<button class="stChip ov" onclick={() => (expanded = { kind: 'overlay', a: ov.a, b: ov.b })} title={ov.tests}>
									<span class="chipK">{T('겹쳐보기', 'overlay')}</span>{labelOf(ov.a)} ↔ {labelOf(ov.b)}
								</button>
							{/if}
						{/each}
						{#each st.divergences as dv (dv.a + dv.b)}
							{#if defOf(dv.a) && defOf(dv.b)}
								{@const g = zGap(ptsOf(dv.a), ptsOf(dv.b))}
								<button class="stChip dv" onclick={() => (expanded = { kind: 'overlay', a: dv.a, b: dv.b })} title={dv.why}>
									<span class="chipK">{T('발산', 'divergence')}</span>{labelOf(dv.a)} ↔ {labelOf(dv.b)}{#if g != null}<i class="chipGap">z-격차 {Math.abs(g).toFixed(1)}σ</i>{/if}
								</button>
							{/if}
						{/each}
					</div>
				{/if}

				<!-- 인사이트 프롬프트 + 다음으로 -->
				<details class="stInsight">
					<summary><span class="chipK">{T('이 단계에서 볼 것', 'what to look for')}</span><i class="stCaret" aria-hidden="true">▾</i></summary>
					<p class="stInsightBody">{T(st.insightKr, st.insightEn)}</p>
					<div class="stFeeds"><b>{T('다음 →', 'next →')}</b> {st.feedsNextKr}</div>
					<div class="stHonesty">{st.honestyKr}</div>
				</details>
			</section>
		{/each}
		<div class="mbOmit">{FLOW_OMITTED_NOTE}</div>
	{/if}

	<!-- 확대 — 단일/겹쳐보기 -->
	{#if expanded && expandedA}
		{@const aStat = rowStat(expandedA)}
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
		<div class="mbExpandScrim" role="presentation" onclick={() => (expanded = null)}>
			<div class="mbExpand" role="dialog" aria-modal="true" tabindex="-1" aria-label={labelOf(expandedA.id)} onclick={(e) => e.stopPropagation()}>
				<div class="mbExpandHead">
					<div>
						{#if expanded.kind === 'overlay'}<span class="chipK">{T('겹쳐보기 (z 정규화)', 'overlay (z-normalized)')}</span><b>{labelOf(expanded.a)} ↔ {expandedB ? labelOf(expanded.b) : ''}</b>
						{:else}<b>{T(expandedA.kr, expandedA.en)}</b><em class="mono">{expandedA.id}</em>{/if}
					</div>
					<button class="mbX" onclick={() => (expanded = null)} aria-label="close">✕</button>
				</div>
				<div class="mbExpandChart">
					<MacroSeriesChart points={ptsOf(expandedA.id)} def={expandedA} {transform} {windowYears} {lang} shading refLine={refLineFor(expandedA)} {brushMs} onBrush={(m) => (brushMs = m)}
						overlay={expanded.kind === 'overlay' && expandedB ? { points: ptsOf(expandedB.id), def: expandedB } : null} />
				</div>
				{#if expanded.kind === 'series'}
					<div class="mbExpandMeta">
						<div><span>{T('현재', 'Last')}</span><b>{fmt(aStat.cur, expandedA)}{displayUnit(expandedA)}</b></div>
						<div><span>{T('이전', 'Prev')}</span><b>{fmt(aStat.prev, expandedA)}{displayUnit(expandedA)}</b></div>
						<div><span>{T('역사 최저', 'Low')}</span><b>{fmt(aStat.ext?.min ?? null, expandedA)}</b></div>
						<div><span>{T('역사 최고', 'High')}</span><b>{fmt(aStat.ext?.max ?? null, expandedA)}</b></div>
						<div><span>{T('기준일', 'Date')}</span><b>{ymd(aStat.lastDate)}</b></div>
						<div><span>{T('출처', 'Source')}</span><b>{expandedA.src.toUpperCase()} · {expandedA.id}</b></div>
					</div>
				{:else}
					<div class="mbExpandNote">{T('두 시리즈를 각자 z-표준화해 겹침 — 절대 수치가 아닌 *방향·선후행·발산*을 본다. 인과는 사용자 판단(상관 ≠ 인과).', 'each series z-normalized to compare direction/lead-lag/divergence, not levels. Causation is your call (correlation ≠ causation).')}</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.mb { display: flex; flex-direction: column; gap: 12px; }
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
	.mbIntro { color: var(--dim); font-size: 10.5px; line-height: 1.5; padding: 2px 2px 0; }
	/* 스테이션 */
	.mbStation { border: 1px solid var(--bd); border-radius: 8px; background: rgba(255, 255, 255, 0.012); padding: 10px 12px 11px; }
	.stHead { display: flex; align-items: flex-start; gap: 10px; }
	.stNo { flex: 0 0 auto; width: 22px; height: 22px; border-radius: 50%; background: rgba(var(--amber-rgb), 0.16); color: var(--amber); font-family: var(--mono); font-weight: 800; font-size: 12px; display: inline-flex; align-items: center; justify-content: center; }
	.stTitleWrap { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
	.stTitle { font-size: 13px; font-weight: 800; color: var(--txt); }
	.stQ { font-size: 11px; color: var(--dim); line-height: 1.45; }
	.stBreadth { flex: 0 0 auto; display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--bd); border-radius: 999px; padding: 2px 9px; font-family: var(--mono); font-size: 11px; }
	.stBreadth i { font-style: normal; }
	.bUp { color: var(--up); } .bDn { color: var(--dn); } .bFl { color: var(--dimmer); }
	/* 행 */
	.mbRows { margin-top: 9px; }
	.mbRowHead, .mbRow { display: grid; grid-template-columns: minmax(120px, 1.5fr) minmax(90px, 1.4fr) 64px 54px minmax(120px, 1.2fr) 48px; gap: 8px; align-items: center; padding: 4px 7px; }
	.mbRowHead { font-size: 8.5px; font-weight: 800; color: var(--dimmer); letter-spacing: 0.04em; text-transform: uppercase; border-bottom: 1px solid var(--bd); }
	.mbRowHead .r, .mbRow .r { text-align: right; justify-self: end; }
	.mbRow { border: 0; background: transparent; color: var(--txt); text-align: left; cursor: pointer; border-top: 1px solid rgba(255, 255, 255, 0.04); border-radius: 5px; }
	.mbRow:hover { background: rgba(var(--amber-rgb), 0.05); }
	.mbName { display: flex; flex-direction: column; min-width: 0; gap: 1px; }
	.mbName b { font-size: 11px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mbName em { font-style: normal; color: var(--dimmer); font-size: 8px; font-family: var(--mono); }
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
	.stInvertNote, .stEmpty { color: var(--dimmer); font-size: 9px; margin-top: 6px; padding: 0 7px; }
	/* ③ 합성 */
	.stSynth { margin-top: 9px; display: flex; flex-direction: column; gap: 6px; }
	.synRow { display: flex; align-items: baseline; gap: 9px; border: 1px solid var(--bd); border-radius: 6px; padding: 7px 10px; background: rgba(255,255,255,0.014); }
	.synMkt { flex: 0 0 auto; color: var(--amber); font-family: var(--mono); font-weight: 800; font-size: 12px; }
	.synQuad { flex: 1 1 auto; font-size: 13px; font-weight: 700; color: var(--txt); }
	.synZ { flex: 0 0 auto; color: var(--dim); font-family: var(--mono); font-size: 10px; }
	.synNote { color: var(--dimmer); font-size: 9px; line-height: 1.4; }
	/* 도구칩 (겹쳐보기·발산) */
	.stTools { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
	.stChip { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--bd); border-radius: 999px; background: rgba(255,255,255,0.015); color: var(--dim); font-size: 10px; padding: 3px 9px; cursor: pointer; }
	.stChip:hover { color: var(--txt); border-color: var(--bdHi); }
	.stChip.ov:hover { border-color: rgba(96,165,250,0.5); }
	.stChip.dv:hover { border-color: rgba(167,139,250,0.5); }
	.chipK { font-family: var(--mono); font-size: 8px; font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase; color: var(--dimmer); }
	.chipGap { font-style: normal; font-family: var(--mono); font-size: 9px; color: var(--industry); margin-left: 2px; }
	/* 인사이트 fold */
	.stInsight { margin-top: 9px; border-top: 1px solid var(--bd); padding-top: 7px; }
	.stInsight > summary { cursor: pointer; list-style: none; display: flex; align-items: center; gap: 8px; }
	.stInsight > summary::-webkit-details-marker { display: none; }
	.stCaret { margin-left: auto; color: var(--amber); font-size: 10px; font-style: normal; }
	.stInsight[open] > summary .stCaret { transform: rotate(180deg); }
	.stInsightBody { margin: 7px 0 0; color: var(--txt); font-size: 11px; line-height: 1.6; }
	.stFeeds { margin-top: 7px; color: var(--dim); font-size: 10px; line-height: 1.5; }
	.stFeeds b { color: var(--amber); }
	.stHonesty { margin-top: 6px; color: var(--dimmer); font-size: 9px; line-height: 1.45; }
	.mbOmit { color: var(--dimmer); font-size: 9px; line-height: 1.45; padding: 2px; border-top: 1px dashed var(--bd); padding-top: 8px; }
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
	.mbExpandNote { color: var(--dim); font-size: 10px; line-height: 1.5; }
	@media (max-width: 720px) {
		.mbRowHead, .mbRow { grid-template-columns: minmax(90px, 1.3fr) 1fr 56px 64px; }
		.mbRowHead span:nth-child(4), .mbRow > .mbPrev, .mbRowHead span:nth-child(5), .mbRow > .mbHist { display: none; }
		.mbExpandMeta { grid-template-columns: repeat(3, 1fr); }
	}
</style>
