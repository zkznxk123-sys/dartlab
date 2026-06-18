<script lang="ts">
	import type { Candle, FilingHit } from '@dartlab/ui-contracts';
	import { useDartLabRuntime } from '@dartlab/ui-runtime';
	import type { Engine, IndustryMacro } from '../lib/engine';
	import ScatterMap, { type ScatterPt } from './ScatterMap.svelte';
	import type { MacroLensTab } from '../lib/macroLens';
	import type { EcoNode, Lang } from '../lib/types';
	import Panel from '../ui/Panel.svelte';
	import ScreenerModal from './ScreenerModal.svelte';
	import FinTypeLegendDialog from './FinTypeLegendDialog.svelte'; // 유형 칩 범례 — TYPE 컬럼 ⓘ 에서 연다
	import Watchlist from './Watchlist.svelte'; // 공시 워치 — 큐레이션 종목 신선도 모니터 (recentMap 공유)
	import { watchlist } from '../lib/watchlist.svelte'; // 워치 카운트 — 하단 탭 라벨 배지
	import { readStore, writeStore } from '../lib/termStore'; // 하단 탭 선택 영속 (워치리스트와 동형 · 기기로컬)
	import { finTypeOf, displayPair } from '../lib/finType'; // 재무 유형 라벨 SSOT (기준=data/finType.ts 한 곳)
	import { txc, chgClass, sign, sparkPts } from '../ui/helpers';

	interface Props {
		eng: Engine;
		lang: Lang;
		active: string;
		onPick: (code: string) => void;
		onMacroLens?: (tab: MacroLensTab, focusId?: string) => void;
		onIndustry?: (id: string) => void; // 산업 sweep 행 클릭 → IndustryDialog
	}
	let { eng, lang, active, onPick, onMacroLens, onIndustry }: Props = $props();
	const rt = useDartLabRuntime();
	const base = rt.env.basePath;
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	// scan 와 동일 universe: finance+prices 보유 회사 (eng 불변 → 1 회 산출 후 캐시)
	const nodes = $derived(
		(eng.raw.eco?.nodes || []).filter((n) => eng.raw.finance.companies[n.id] && eng.priceOf(n.id))
	);
	// 소문자 회사명 사전 — 키 입력마다 nameOf().toLowerCase() 재계산 방지 (1 회 산출)
	const lowerNames = $derived(new Map(nodes.map((n) => [n.id, (eng.nameOf(n.id) || '').toLowerCase()])));

	// ── 통합 스크리너: 스파크라인(30거래일) + 1Y 수익률 + 유형 라벨 2칩 한 행 (제품급 조건검색기).
	// ROE·영업이익 수치 컬럼은 라벨(finType 체인)로 대체 — 수치 다조건은 상세검색 모달 소관. ──
	let screenerOpen = $state(false);
	let finLegendOpen = $state(false); // 유형 칩 범례 다이얼로그
	// 하단 통합 패널 탭 — 스크리너(기본) ⇄ 공시 워치. 선택을 localStorage 영속(워치리스트와 동형 · 기기로컬).
	// 기본 'screener' 는 키 미저장(쓰레기 키 방지 관례), 'watch' 선택 시에만 저장 → 새로고침해도 워치 유지.
	let bottomTab = $state<'screener' | 'watch'>(readStore<string>('dlTerm.bottomTab', 'screener') === 'watch' ? 'watch' : 'screener');
	$effect(() => { writeStore('dlTerm.bottomTab', bottomTab === 'watch' ? 'watch' : null); });
	// 30거래일 스파크 — recent.parquet 전종목 1파일 (티커 스트립과 어댑터 캐시 공유, 추가 다운로드 0)
	let recentMap = $state<Record<string, Candle[]> | null>(null);
	rt.price.govRecent().then((m) => (recentMap = m));

	// ── 공시 본문 전역검색(좌측 상단) — cmdBar 종목점프와 다른 intent: 462k 코퍼스 BM25.
	//    rt.search.queryFilings = HF sidecar byte-range fetch(무서버·exact). 결과 행 클릭 = 관련 회사로 점프.
	let fq = $state('');
	let fHits = $state<FilingHit[]>([]);
	let fBusy = $state(false);
	let fErr = $state(false);
	let fSeq = 0;
	$effect(() => {
		const q = fq.trim();
		if (!q) { fHits = []; fBusy = false; fErr = false; return; }
		const seq = ++fSeq;
		const t = setTimeout(async () => {
			fBusy = true;
			fErr = false;
			try {
				const hits = await rt.search.queryFilings({ text: q, limit: 12 });
				if (seq === fSeq) { fHits = hits; fBusy = false; }
			} catch {
				if (seq === fSeq) { fErr = true; fBusy = false; fHits = []; }
			}
		}, 200);
		return () => clearTimeout(t);
	});
	const openFiling = (h: FilingHit) => { if (h.stockCode) onPick(h.stockCode); };
	const viewerHref = (h: FilingHit) => (h.stockCode ? `${base}/viewer/company/${h.stockCode}${h.rceptNo ? `?rcept=${h.rceptNo}` : ''}` : '');

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
	// 정렬 = 1Y 수익률 단일 (prices). 수치 다조건 정렬·필터는 상세검색 모달이 담당.
	const r1yOf = (n: EcoNode): number | null => { const px = eng.priceOf(n.id); return px ? ((px.return1y as number | null) ?? null) : null; };
	interface Row { n: EcoNode; r1y: number | null; }
	const rows = $derived(
		nodes
			.filter(matchFilter)
			.map((n): Row => ({ n, r1y: r1yOf(n) }))
			.filter((r) => r.r1y != null)
			.sort((a, b) => (b.r1y as number) - (a.r1y as number))
			.slice(0, 80)
	);

	// ── 경제 (최상단 고정) ──
	const macro = $derived(eng.raw.macro);
	const assetChips: [string, string][] = [['주식', 'equity'], ['채권', 'bond'], ['원자재', 'commodity'], ['금', 'gold'], ['물가채', 'tips'], ['현금', 'cash']];
	const wcls = (w?: string) => (w === 'overweight' ? 'ow' : w === 'underweight' ? 'uw' : 'nu');
	const toggleSector = (id: string) => (sectorFilter = sectorFilter === id ? '' : id);

	// ── 산업 sweep — 거시 깔때기 산업층. 34산업을 선택 렌즈로 cross-section 비교(섹터 시세 히트맵 대체). ──
	// 전부 baked 합성(industryStats·ecosystem·gov 시총), 새 fetch 0. 측정근거=_attempts/macroIndustrySweep.
	const industryIds = $derived([...new Set((eng.raw.eco?.nodes || []).map((n) => n.industry))]);
	const sweepAll = $derived(industryIds.map((id) => eng.industryMacro(id)).filter((m): m is IndustryMacro => m != null));
	// 미니 지형도 — 산업 = (영업이익률 중앙값 × 마진 격차 IQR). 위치=구조 관측. 현재 종목 산업 강조·클릭=스크리너 필터+상세.
	const industryPts = $derived.by((): ScatterPt[] =>
		sweepAll
			.filter((s) => s.count >= 10 && s.dist.opMargin?.median != null && s.dist.revCagr?.median != null)
			.map((s) => ({ id: s.id, x: s.dist.opMargin!.median, y: s.dist.revCagr!.median, size: s.count, label: lang === 'en' ? s.en : s.kr, faint: s.count < 15 }))
	);
	const curIndustry = $derived(sectorFilter || (eng.raw.eco?.nodes || []).find((n) => n.id === active)?.industry || '');
	const activeSectorName = $derived(sectorFilter ? (sweepAll.find((s) => s.id === sectorFilter)?.kr || sectorFilter) : '');
	function pickIndustry(id: string) {
		toggleSector(id); // 스크리너 필터(기존 깔때기) — 한 번 더 누르면 해제
		onIndustry?.(id); // IndustryDialog 열기(신규)
	}
	// 매크로 국면 → 순풍/역풍 섹터(blended). 칩 클릭 = 아래 스크리너 섹터 필터.
	const tailwinds = $derived(eng.sectorTailwinds());
	const twTop = $derived(tailwinds.slice(0, 3));
	const twBot = $derived(tailwinds.length > 3 ? tailwinds.slice(-3).reverse() : []);
	const macroAsOf = $derived(macro?.asOf ?? '');
</script>

<!-- 공시 본문 전역검색 — 좌측 최상단. cmdBar(종목 점프)와 다른 intent: 462k 코퍼스 본문 BM25.
     결과 행 클릭 = 관련 회사로 점프(onPick) · "공시 열기 ↗" = 뷰어 딥링크. 무서버 HF sidecar range fetch. -->
<section class="panel filingSrch">
	<div class="fsBar">
		<input
			class="fsInput mono"
			bind:value={fq}
			spellcheck={false}
			placeholder={lang === 'en' ? 'search filings — 증자·소송·배당…' : '공시 본문 검색 — 증자·소송·배당…'}
		/>
		{#if fq}<button class="fsX" onclick={() => (fq = '')} title={lang === 'en' ? 'clear' : '지우기'}>✕</button>{/if}
	</div>
	{#if fq.trim()}
		<div class="fsResults">
			{#if fBusy}
				<div class="fsMsg">{lang === 'en' ? 'searching…' : '검색 중…'}</div>
			{:else if fErr}
				<div class="fsMsg">{lang === 'en' ? 'search index unavailable' : '검색 인덱스 미배포'}</div>
			{:else if !fHits.length}
				<div class="fsMsg">{lang === 'en' ? 'no filings' : '결과 없음'}</div>
			{:else}
				{#each fHits as h (h.sourceRef)}
					<div class="fsRow" role="button" tabindex="0" onclick={() => openFiling(h)} onkeydown={(e) => e.key === 'Enter' && openFiling(h)}>
						<div class="fsRowTop"><b class="fsCorp">{h.corpName || h.stockCode || '—'}</b><span class="fsReport">{h.reportNm}</span><span class="fsDate mono">{h.rceptDt}</span></div>
						{#if h.snippet}<div class="fsSnip">{h.snippet}</div>{/if}
						{#if h.stockCode}<a class="fsOpen" href={viewerHref(h)} target="_blank" rel="noopener" onclick={(e) => e.stopPropagation()}>{lang === 'en' ? 'open ↗' : '공시 열기 ↗'}</a>{/if}
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</section>

<!-- 경제 — 최상단 고정 (탭 토글 폐지, 항상 노출) -->
{#if macro}
	<Panel {lang} className="eMacro" prov="real" title={{ kr: '마켓 펄스 · 매크로', en: 'MARKET PULSE' }} sub={{ kr: 'dartlab.macro' + (macroAsOf ? ' · ' + macroAsOf : ''), en: 'dartlab.macro' + (macroAsOf ? ' · ' + macroAsOf : '') }} flush>
		{#snippet right()}
			<button class="finFullBtn" onclick={() => onMacroLens?.('regime', 'KR')} title={lang === 'en' ? 'open macro lens' : '매크로 렌즈 열기'}>{lang === 'en' ? 'detail' : '상세보기'}</button>
			<span class="dim">{lang === 'en' ? 'daily batch' : '일배치'}</span>
		{/snippet}
		<div class="quadWrap">
			{#each [{ side: 'kr', label: 'KR' }, { side: 'us', label: 'US' }] as box (box.side)}
				{@const m = box.side === 'kr' ? macro.kr : macro.us}
				{@const q = m.quadrant}
				<div class="quadBox">
					<div class="quadMkt">{box.label} · {lang === 'en' ? m.phase.toUpperCase() : m.phaseLabel}{q?.inflation ? ' · ' + (lang === 'en' ? 'infl ' + q.inflation : '물가 ' + q.inflation) : ''}</div>
					{#if q}
						<div class={'quadPhase ' + (q.growth === 'rising' || q.growth === '상승' ? 'tUp' : 'tDn')}>{lang === 'en' ? q.quadrant : q.quadrantLabel}</div>
						<div class="quadDesc">{q.description}</div>
						<div class="quadAssets">
							{#each assetChips as [kr, key] (key)}<span class={'assetChip ' + wcls(q.assetImplication?.[key])}>{lang === 'en' ? key.slice(0, 4) : kr}</span>{/each}
						</div>
					{:else}
						<!-- quadrant 결측(빌더 입력 부족 등) — 국면 라벨만 정직 표시, 크래시 금지 -->
						<div class="quadDesc">{lang === 'en' ? 'quadrant data unavailable' : '국면 상세 데이터 없음'}</div>
					{/if}
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
{/if}

<!-- 산업 sweep — 거시 깔때기 산업층(매크로→★산업→종목). 패널 = 미니 지형도(읽기 아닌 *시각화*).
     전 산업을 (수익 수준×마진 격차) 점구름으로 — 현재 산업 강조·클릭=스크리너 필터+상세. 상세는 다이얼로그. -->
<Panel {lang} className="eIndustry" prov="real" title={{ kr: '산업 스윕', en: 'INDUSTRY SWEEP' }} sub={{ kr: '구조 · 클릭=상세', en: 'structure · click=detail' }}>
	{#snippet right()}
		<button class="scrOpenBtn" onclick={() => onIndustry?.('')} title={lang === 'en' ? 'detail · all industries' : '상세보기 · 전체 산업'}>{lang === 'en' ? 'Detail ↗' : '상세보기 ↗'}</button>
	{/snippet}
	<div class="swMap">
		<ScatterMap pts={industryPts} compact highlightId={curIndustry} onPick={pickIndustry} xLabel="" yLabel="" zeroX />
	</div>
	<button class="swMore" onclick={() => onIndustry?.('')}>{lang === 'en' ? `detail · ${industryPts.length} industries · companies →` : `상세보기 · ${industryPts.length}산업 · 회사 산포 →`}</button>
	<div class="swNote">ⓘ {lang === 'en' ? 'x = margin · y = growth · ring = current · equal-weight · not KRX' : '가로=수익 · 세로=성장 · ◯=현재 산업 · 상장 동일가중 · KRX 아님'}</div>
</Panel>

<!-- 하단 통합 — 스크리너 ⇄ 공시 워치 탭. 워치가 무한 증가해 스크리너를 가리던 문제 해소
     (한 자리를 탭으로 공유 · 각 탭이 잔여 높이 전부 차지 · 내부 스크롤). 탭 바가 패널 헤더 역할. -->
<section class="panel eQuant fillCol">
	<header class="panelHead leftTabHead">
		<button class={'leftTab' + (bottomTab === 'screener' ? ' on' : '')} onclick={() => (bottomTab = 'screener')}>{lang === 'en' ? 'SCREENER' : '스크리너'}</button>
		<button class={'leftTab' + (bottomTab === 'watch' ? ' on' : '')} onclick={() => (bottomTab = 'watch')}>{lang === 'en' ? 'WATCH' : '공시 워치'}{#if watchlist.count}<span class="leftTabN">{watchlist.count}</span>{/if}</button>
		<span class="panelRight">
			{#if bottomTab === 'screener'}<button class="scrOpenBtn" onclick={() => (screenerOpen = true)} title="상용급 다조건 검색">{lang === 'en' ? 'SCREEN' : '상세검색'}</button><a class="lensScan" href="{base}/scan" target="_blank" rel="noopener" title="전체 조건 조사 — scan 보드">{lang === 'en' ? 'scan ↗' : '조건조사 ↗'}</a>{/if}
		</span>
	</header>
	<div class="panelBody flush">
		{#if bottomTab === 'screener'}
			<div class="filtRow">
				<input class="filtInput" placeholder={lang === 'en' ? 'name/code' : '이름·코드'} bind:value={query} spellcheck={false} />
				<select class="filtSel" bind:value={market}><option value="">{lang === 'en' ? 'all market' : '전체 시장'}</option><option value="KOSPI">KOSPI</option><option value="KOSDAQ">KOSDAQ</option></select>
			</div>
			{#if sectorFilter}
				<div class="filtChipRow"><button class="filtChip" onclick={() => (sectorFilter = '')}>{lang === 'en' ? 'sector: ' : '섹터: '}{activeSectorName} ✕</button></div>
			{/if}
			<!-- 컬럼 헤더 — 정렬 1Y 고정 (수치 다조건은 상세검색) -->
			<div class="rkHead">
				<span class="rkHN">#</span>
				<span class="rkHName">{lang === 'en' ? 'Company' : '종목'}</span>
				<span class="rkHCol">{lang === 'en' ? '30D' : '추세'}</span>
				<span class="rkHCol on">1Y ▼</span>
				<button class="rkHCol rkHType" onclick={() => (finLegendOpen = true)} title={lang === 'en' ? 'What these type labels mean — criteria' : '유형 라벨 기준 보기'}>{lang === 'en' ? 'TYPE' : '유형'} <span class="rkHTypeI">ⓘ</span></button>
			</div>
			<div class="rankList">
				{#each rows as r, i (r.n.id)}
					{@const fts = displayPair(finTypeOf(r.n, eng.raw.finance.companies[r.n.id], eng.priceOf(r.n.id)))}
					{@const sp = recentMap?.[r.n.id]}
					<div class={'rankRow' + (active === r.n.id ? ' on' : '')} role="button" tabindex="0" onclick={() => onPick(r.n.id)} onkeydown={(e) => e.key === 'Enter' && onPick(r.n.id)}>
						<span class="rkN mono">{i + 1}</span>
						<span class="rkName"><b>{eng.nameOf(r.n.id)}</b><span class="rkInd">{r.n.industryName || ''}</span></span>
						<span class="rkSpark">{#if sp && sp.length > 1}<svg class={chgClass(r.r1y)} viewBox="0 0 34 11" preserveAspectRatio="none" aria-hidden="true"><polyline points={sparkPts(sp.map((k) => k.c))} fill="none" stroke="currentColor" stroke-width="1.1" /></svg>{/if}</span>
						<span class={'rkCol mono ' + chgClass(r.r1y)}>{r.r1y == null ? '—' : sign(r.r1y, 0) + '%'}</span>
						<span class="rkChips">
							{#each fts as ft (ft.name)}<span class={'rkChip ' + tcls(ft.tone)} title={ft.criteriaKr}>{ft.name}</span>{/each}
						</span>
					</div>
				{/each}
			</div>
		{:else}
			<Watchlist bare {eng} {lang} {active} {onPick} {recentMap} />
		{/if}
	</div>
</section>

<ScreenerModal {eng} {lang} open={screenerOpen} onClose={() => (screenerOpen = false)} onPick={(c) => { onPick(c); screenerOpen = false; }} />
{#if finLegendOpen}<FinTypeLegendDialog {lang} onClose={() => (finLegendOpen = false)} />{/if}

<style>
	/* 공시 본문 전역검색 — 좌측 상단. 터미널 토큰(--dl-*) 사용, 미정의 시 fallback. 운영자 눈검수 대상. */
	.filingSrch { padding: 5px 6px; border-bottom: 1px solid var(--dl-line, #1c2433); }
	.fsBar { display: flex; align-items: center; gap: 4px; }
	.fsInput {
		flex: 1; min-width: 0; background: var(--dl-bg-raised, #0b1018);
		border: 1px solid var(--dl-line-strong, #2a3650); color: var(--dl-text, #cdd6e4);
		border-radius: 4px; padding: 4px 7px; font-size: 11px;
	}
	.fsInput::placeholder { color: var(--dl-text-dim, #5b6678); }
	.fsX { background: none; border: none; color: var(--dl-text-dim, #5b6678); cursor: pointer; font-size: 11px; padding: 2px 4px; }
	.fsResults { margin-top: 4px; max-height: 320px; overflow-y: auto; display: flex; flex-direction: column; gap: 1px; }
	.fsMsg { font-size: 10.5px; color: var(--dl-text-dim, #5b6678); padding: 6px 2px; }
	.fsRow { padding: 5px 6px; border-radius: 4px; cursor: pointer; border: 1px solid transparent; }
	.fsRow:hover { background: var(--dl-bg-raised, #0b1018); border-color: var(--dl-line-strong, #2a3650); }
	.fsRowTop { display: flex; align-items: baseline; gap: 5px; }
	.fsCorp { font-size: 11px; color: var(--dl-text, #cdd6e4); white-space: nowrap; }
	.fsReport { font-size: 10px; color: var(--dl-text-dim, #8a94a6); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.fsDate { font-size: 9.5px; color: var(--dl-text-dim, #5b6678); }
	.fsSnip {
		font-size: 10px; color: var(--dl-text-dim, #8a94a6); margin-top: 2px; line-height: 1.35;
		display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
	}
	.fsOpen { font-size: 9.5px; color: var(--dl-accent, #5b9bd5); text-decoration: none; margin-top: 2px; display: inline-block; }
</style>
