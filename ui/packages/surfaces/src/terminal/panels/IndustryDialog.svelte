<script lang="ts">
	// 산업 분석 다이얼로그 — 산업이 *주체*. 시각화 우선(읽는 표 최소): 지형도 → 클릭 → 회사 산포도.
	//  · 지형도(기본): 29산업을 (수익 수준 × 마진 격차) 평면에 — 구조가 0.5초에 보임. 순위표는 보조 토글.
	//  · 드릴: 산업 내 회사들을 (수익성 × 성장) 산포 — 양극화·스타·부실이 *보임*. 크기=gov 시총·색=수익성 등급.
	// 전부 baked(industryStats·ecosystem·gov 시총), 새 fetch 0. 위치=관측(판정 아님, 04 §3).
	import type { Engine, IndustryMacro, IndustryMember } from '../lib/engine';
	import { gradeTone } from '../lib/engine';
	import { INDUSTRY_LENSES, lensByKey, lensRank } from '../lib/industryLens';
	import type { Lang } from '../lib/types';
	import DistCurve from './DistCurve.svelte';
	import ScatterMap, { type ScatterPt } from './ScatterMap.svelte';

	interface Props {
		eng: Engine;
		industryId: string; // '' = 지형도 진입, 그 외 = 드릴
		lang: Lang;
		onClose: () => void;
		onPick: (code: string) => void;
	}
	let { eng, industryId, lang, onClose, onPick }: Props = $props();

	let view = $state(industryId); // '' = 지형도/랜드스케이프, 그 외 = 드릴 산업 id
	let landView = $state<'map' | 'rank'>('map'); // 지형도(기본) ↔ 순위표(보조)
	let landLens = $state('prof');
	const lens = $derived(lensByKey(landLens));

	const industryIds = $derived([...new Set((eng.raw.eco?.nodes || []).map((n) => n.industry))]);
	const all = $derived(industryIds.map((id) => eng.industryMacro(id)).filter((x): x is IndustryMacro => x != null && x.count >= 10));
	const m = $derived(view ? all.find((x) => x.id === view) ?? eng.industryMacro(view) : null);

	const fmt1 = (v: number | null | undefined, u = ''): string => (v == null ? '—' : (Math.abs(v) >= 10 ? Math.round(v).toString() : v.toFixed(1)) + u);
	const twLabel = (t: number | null): string => (t == null ? '' : t >= 0.55 ? (lang === 'en' ? 'tailwind' : '순풍') : t <= 0.35 ? (lang === 'en' ? 'headwind' : '역풍') : (lang === 'en' ? 'neutral' : '중립'));

	// ── 지형도: 산업 = (영업이익률 중앙값 × 마진 격차 IQR). y(격차)는 좋고나쁨 아님 → 위치 절반 verdict-free.
	const industryPts = $derived.by((): ScatterPt[] =>
		all
			.filter((x) => x.dist.opMargin?.median != null && x.marginIqr != null)
			.map((x) => ({
				id: x.id,
				x: x.dist.opMargin!.median,
				y: x.marginIqr as number,
				size: x.count,
				label: lang === 'en' ? x.en : x.kr,
				faint: x.count < 15,
				meta: `n=${x.count} · ${lang === 'en' ? 'margin' : '마진'} ${fmt1(x.dist.opMargin!.median)}% · ${lang === 'en' ? 'spread' : '격차'} ${fmt1(x.marginIqr)}%p${x.tailwind != null ? ' · ' + twLabel(x.tailwind) : ''}`
			}))
	);

	// ── 드릴: 산업 내 회사 산포도(수익성 × 성장). 크기=gov 시총 · 색=수익성 등급. 위치=회사 실측(사실).
	const members = $derived.by((): IndustryMember[] => (view ? eng.industryMembers(view) : []));
	const memberPts = $derived.by((): ScatterPt[] =>
		members.map((c) => ({
			id: c.code,
			x: c.margin,
			y: c.growth,
			size: c.cap,
			tone: gradeTone('prof', c.grade),
			label: c.name,
			meta: `${lang === 'en' ? 'margin' : '마진'} ${fmt1(c.margin)}% · ${lang === 'en' ? 'growth' : '성장'} ${fmt1(c.growth)}%${c.grade ? ' · ' + c.grade : ''}`
		}))
	);
	const plotted = $derived(memberPts.length);

	// 랜드스케이프 순위표(보조) — 선택 렌즈 정렬(lower 반영)
	const landRows = $derived.by(() => {
		const rows = all.filter((x) => lens.valueOf(x) != null).map((x) => ({ x, v: lens.valueOf(x) as number }));
		rows.sort((a, b) => (lens.lower ? a.v - b.v : b.v - a.v));
		return rows;
	});
	const landVals = $derived(landRows.map((r) => r.v));
	const rankToneVal = (pct: number): string => (pct >= 66 ? 'tUp' : pct <= 33 ? 'tDn' : 'tNeu');
	const fmtUnit = (v: number | null | undefined, unit: string): string => (v == null ? '—' : (unit === '배' ? v.toFixed(1) : fmt1(v)) + (unit === '배' ? '배' : unit));

	// 드릴 보조 — 비공간 사실(방향 YoY·tailwind·distress). 표 아님, 얇은 칩 한 줄.
	const dir = $derived(m?.direction ?? null);
	const dirSigns = $derived(dir ? [dir.opMarginDelta, dir.roeDelta, dir.revenueYoyPct].filter((x): x is number => x != null) : []);
	const dirLabel = $derived.by(() => {
		if (dirSigns.length < 2) return { txt: '', cls: 'tNeu' };
		const up = dirSigns.filter((x) => x > 0).length, dn = dirSigns.filter((x) => x < 0).length;
		return up > dn ? { txt: lang === 'en' ? 'improving' : '개선', cls: 'tUp' } : dn > up ? { txt: lang === 'en' ? 'deteriorating' : '악화', cls: 'tDn' } : { txt: lang === 'en' ? 'mixed' : '혼조', cls: 'tNeu' };
	});
	const sgn = (v: number | null | undefined, u: string): string => (v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(1) + u);
	const polarLabel = $derived(m?.marginIqr == null ? '' : m.marginIqr > 15 ? (lang === 'en' ? 'wide' : '넓음') : m.marginIqr < 8 ? (lang === 'en' ? 'narrow' : '좁음') : (lang === 'en' ? 'mid' : '보통'));

	const GRADE_LEG: { t: string; k: string; e: string }[] = [
		{ t: 'up', k: '우수', e: 'top' }, { t: 'good', k: '양호', e: 'good' }, { t: 'neutral', k: '보통', e: 'mid' }, { t: 'warn', k: '저수익', e: 'thin' }, { t: 'down', k: '적자', e: 'loss' }
	];

	$effect(() => {
		const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { if (view) { view = ''; } else { onClose(); } } };
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal indModal" role="dialog" aria-modal="true" aria-label={lang === 'en' ? 'Industry analysis' : '산업 분석'} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			{#if view && m}
				<button class="indBack" onclick={() => (view = '')} title={lang === 'en' ? 'back to map' : '지형도로'}>◄ {lang === 'en' ? 'map' : '지형도'}</button>
				<span class="indWho">{lang === 'en' ? m.en : m.kr}<i>n={m.count}{#if m.tailwind != null} · {twLabel(m.tailwind)} {m.tailwind.toFixed(2)}{/if}{#if m.macroPhase} · {lang === 'en' ? 'macro' : '국면'} {m.macroPhase}{/if}</i></span>
			{:else}
				<span class="scrTitle">{lang === 'en' ? 'INDUSTRY MAP' : '산업 지형도'}</span>
				<span class="indWho">{lang === 'en' ? `${industryPts.length} industries` : `${industryPts.length}개 산업`}<i>{lang === 'en' ? 'click → companies' : '클릭 → 회사 산포'}</i></span>
			{/if}
			<span class="indLens">{lang === 'en' ? 'position = structure (not a verdict)' : '위치 = 구조 (판정 아님)'}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		<div class="indBody">
			{#if view && m}
				<!-- ── 드릴: 회사 산포도(수익성 × 성장) — 양극화·스타·부실이 보임 ── -->
				<div class="indScatterHd">
					<span class="indScatterT">{lang === 'en' ? 'Companies — profitability × growth' : '회사 지형 — 수익성 × 성장'}</span>
					<span class="indGradeLeg">
						{#each GRADE_LEG as g (g.t)}<span class={'indLegDot ' + g.t}></span><i>{lang === 'en' ? g.e : g.k}</i>{/each}
					</span>
				</div>
				<ScatterMap pts={memberPts} xLabel={lang === 'en' ? 'op-margin %' : '수익성(영업이익률 %)'} yLabel={lang === 'en' ? 'rev CAGR %' : '성장(매출 CAGR %)'} showLabels zeroX onPick={onPick}
					hint={lang === 'en' ? `※ dot = company · size = gov market-cap · color = profit grade · position = actual values (${plotted} plotted, extremes pinned to edge) · click → company` : `※ 점=회사 · 크기=gov 시총 · 색=수익성 등급 · 위치=실측값 (${plotted}사 · 극단값 가장자리·hover=실제) · 클릭 → 종목`} />
				<!-- 비공간 사실 — 얇은 칩 한 줄(표 아님) -->
				<div class="indFactStrip">
					<span>{lang === 'en' ? 'spread(IQR)' : '마진 격차'} <b>{fmt1(m.marginIqr)}%p</b> {polarLabel}</span>
					<span>{lang === 'en' ? 'loss' : '적자'} <b>{m.bucket.lossRisk}%</b></span>
					<span>{lang === 'en' ? 'thin' : '저수익'} <b>{m.bucket.profRisk}%</b></span>
					<span>{lang === 'en' ? 'distress' : '부실'} <b>{m.bucket.cfDistress}%</b></span>
					{#if dir && dirSigns.length >= 2}<span>{lang === 'en' ? 'YoY' : '방향'} {lang === 'en' ? 'm' : '마진'}{sgn(dir.opMarginDelta, '')} ROE{sgn(dir.roeDelta, '')} {lang === 'en' ? 'rev' : '매출'}{sgn(dir.revenueYoyPct, '')} <em class={dirLabel.cls}>{dirLabel.txt}</em></span>{/if}
					{#if m.cfSignature}<span>{lang === 'en' ? 'CF' : '현금'} <b>{m.cfSignature.pattern}</b></span>{/if}
					{#if m.tailwind != null}<span class={m.tailwind >= 0.55 ? 'tUp' : m.tailwind <= 0.35 ? 'tDn' : 'tNeu'}>{twLabel(m.tailwind)} {m.tailwind.toFixed(2)}</span>{/if}
				</div>
				<div class="indHint">※ {lang === 'en' ? 'CAGR (y) = multi-year average; the YoY chip = recent change. Divergence (high CAGR but −YoY) = possible cyclical peak (observation, not forecast).' : 'CAGR(세로)=다년 평균 · YoY 칩=최근 변화. 둘이 갈리면(높은 CAGR 인데 −YoY) 순환 고점 가능성(관측이지 예측 아님).'}</div>
			{:else}
				<!-- ── 지형도(기본) ↔ 순위표(보조) ── -->
				<div class="indLensRow">
					<div class="indViewTog">
						<button class={'indVBtn' + (landView === 'map' ? ' on' : '')} onclick={() => (landView = 'map')}>{lang === 'en' ? 'Map' : '지형도'}</button>
						<button class={'indVBtn' + (landView === 'rank' ? ' on' : '')} onclick={() => (landView = 'rank')}>{lang === 'en' ? 'Rank' : '순위'}</button>
					</div>
					{#if landView === 'rank'}
						{#each INDUSTRY_LENSES as l (l.key)}
							<button class={'indLensBtn' + (landLens === l.key ? ' on' : '')} onclick={() => (landLens = l.key)} title={l.note}>{lang === 'en' ? l.en : l.kr}</button>
						{/each}
					{/if}
				</div>
				{#if landView === 'map'}
					<ScatterMap pts={industryPts} xLabel={lang === 'en' ? 'op-margin median' : '영업이익률 중앙값(수익 수준)'} yLabel={lang === 'en' ? 'margin spread IQR' : '마진 격차(IQR)'} showLabels zeroX yFloor0 onPick={(id) => (view = id)}
						hint={lang === 'en' ? '※ dot = industry · x = margin level · y = within-industry spread · size = members · position = observation, not a verdict · click → companies' : '※ 점=산업 · 가로=수익 수준 · 세로=산업 내 격차 · 크기=멤버수 · 위치=관측이지 판정 아님 · 클릭 → 회사 산포'} />
				{:else}
					<div class="indLand">
						{#each landRows as r, i (r.x.id)}
							{@const band = lens.bandOf(r.x)}
							{@const rank = lensRank(lens, r.v, landVals)}
							<button class="indLandRow" onclick={() => (view = r.x.id)} title={`${r.x.kr} · n=${r.x.count} · ${lang === 'en' ? 'click → companies' : '클릭 → 회사 산포'}`}>
								<span class="indLR mono">{i + 1}</span>
								<span class="indLName">{lang === 'en' ? r.x.en : r.x.kr}{#if r.x.tailwind != null}<i class={'swTw ' + (r.x.tailwind >= 0.55 ? 'tw-up' : r.x.tailwind <= 0.35 ? 'tw-dn' : 'tw-nu')}>{r.x.tailwind >= 0.55 ? '↑' : r.x.tailwind <= 0.35 ? '↓' : '·'}</i>{/if}</span>
								<span class="indLCurve">{#if band}<DistCurve {band} value={r.v} p={rank} unit={lens.unit} {lang} h={20} neutral={lens.lower} />{/if}</span>
								<span class={'indLVal mono ' + rankToneVal(rank)}>{fmtUnit(r.v, lens.unit)}</span>
								<span class="indLN mono" class:warn={r.x.count < 15} title={r.x.count < 15 ? (lang === 'en' ? 'small sample — rank less stable' : '표본 작아 순위 불안정') : ''}>{r.x.count}{#if r.x.count < 15}⚠{/if}</span>
							</button>
						{/each}
					</div>
				{/if}
			{/if}

			<div class="indNotes">
				<div>※ {lang === 'en'
					? 'Distribution: industryStats · KSIC · equal-weight · listed primary (≠ KRX cap-weighted index). Market-cap/PBR use gov, not KRX.'
					: '분포: industryStats · KSIC · 동일가중 · 상장 primary (≠ KRX 시총가중 업종지수). 시총/PBR은 gov(KRX 아님).'}</div>
				<div>※ {lang === 'en'
					? 'Company dots = actual reported values; grade color = scan profit grade (an assessment, labeled). n<15 (⚠) ranks less stable.'
					: '회사 점 = 실측 보고값 · 색 = scan 수익성 등급(평가값, 라벨). n<15(⚠) 순위 불안정.'}</div>
				<div>※ {lang === 'en'
					? 'Snapshot of current listed members (survivorship: delisted/unlisted excluded) — not a trend; positions shift year to year.'
					: '현재 상장 멤버 스냅샷(생존편향: 상폐·비상장 제외) — 추세 아님, 위치는 연도별로 바뀜.'}</div>
				<div>※ {lang === 'en'
					? 'Position facts only — no buy/sell, no causal/forecast (spread is observed dispersion, not a verdict).'
					: '위치 사실만 — 매수/매도·인과/예측 금지(격차는 관측된 분산이지 판정 아님).'}</div>
			</div>
		</div>
	</div>
</div>

<style>
	.indModal { width: min(760px, 95vw); }
	.indBack { background: none; border: 1px solid var(--dl-line, #2a3142); border-radius: 3px; color: #c2cad6; font-size: 10px; padding: 1px 7px; cursor: pointer; }
	.indBack:hover { color: var(--dl-ink, #c8cfdb); border-color: var(--amber, #fb923c); }
	.indWho { font-size: 12px; font-weight: 700; color: var(--dl-ink, #c8cfdb); }
	.indWho i { font-style: normal; font-weight: 400; margin-left: 7px; font-size: 10px; color: #c2cad6; }
	.indLens { font-size: 10px; color: #c2cad6; font-style: italic; }
	.indBody { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 10px 14px 14px; }
	/* 드릴 — 회사 산포도 헤더 + 등급 범례 */
	.indScatterHd { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
	.indScatterT { font-size: 11px; font-weight: 700; color: var(--dl-ink, #c8cfdb); }
	.indGradeLeg { display: inline-flex; align-items: center; gap: 3px; font-size: 9px; color: #c2cad6; }
	.indGradeLeg i { font-style: normal; margin-right: 4px; }
	.indLegDot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
	.indLegDot.up { background: #3fb950; }
	.indLegDot.good { background: #6fbf73; }
	.indLegDot.neutral { background: #8b93a0; }
	.indLegDot.warn { background: #d29922; }
	.indLegDot.down { background: #f85149; }
	.indFactStrip { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 8px; font-size: 10px; color: #c2cad6; }
	.indFactStrip b { color: var(--dl-ink, #c8cfdb); font-variant-numeric: tabular-nums; }
	.indFactStrip em { font-style: normal; font-weight: 700; margin-left: 2px; }
	.indHint { font-size: 9.5px; color: #c2cad6; line-height: 1.45; margin-top: 6px; font-style: italic; }
	/* 뷰 토글 + 순위표(보조) */
	.indLensRow { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 8px; align-items: center; }
	.indViewTog { display: inline-flex; border: 1px solid var(--dl-line, #2a3142); border-radius: 3px; overflow: hidden; margin-right: 4px; }
	.indVBtn { font-size: 10px; padding: 2px 9px; border: 0; background: rgba(255, 255, 255, 0.02); color: #c2cad6; cursor: pointer; }
	.indVBtn:hover { color: var(--dl-ink, #c8cfdb); }
	.indVBtn.on { color: var(--amber, #fb923c); background: color-mix(in srgb, var(--amber, #fb923c) 14%, transparent); }
	.indLensBtn { font-size: 10px; padding: 2px 9px; border-radius: 3px; border: 1px solid var(--dl-line, #2a3142); background: rgba(255, 255, 255, 0.02); color: #c2cad6; cursor: pointer; }
	.indLensBtn:hover { color: var(--dl-ink, #c8cfdb); }
	.indLensBtn.on { color: var(--amber, #fb923c); border-color: color-mix(in srgb, var(--amber, #fb923c) 55%, transparent); background: color-mix(in srgb, var(--amber, #fb923c) 12%, transparent); }
	.indLand { display: flex; flex-direction: column; margin-bottom: 10px; max-height: 56vh; overflow-y: auto; }
	.indLandRow { display: grid; grid-template-columns: 18px 96px 1fr 56px 26px; align-items: center; gap: 9px; padding: 2px 4px; background: none; border: 0; border-bottom: 1px solid var(--dl-line, #1b2130); cursor: pointer; text-align: left; }
	.indLandRow:hover { background: var(--dl-bg-overlay, rgba(255, 255, 255, 0.04)); }
	.indLR { font-size: 9px; color: #c2cad6; text-align: center; }
	.indLName { font-size: 11px; color: var(--dl-ink, #c8cfdb); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 3px; }
	.indLCurve { min-width: 0; line-height: 0; }
	.indLVal { font-size: 11px; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
	.indLN { font-size: 9px; color: #c2cad6; text-align: right; font-variant-numeric: tabular-nums; }
	.indLN.warn { color: var(--warn, #d29922); }
	.swTw { font-style: normal; font-size: 9px; font-weight: 700; }
	.swTw.tw-up { color: var(--up, #3fb950); }
	.swTw.tw-dn { color: var(--dn, #f85149); }
	.swTw.tw-nu { color: #c2cad6; }
	.indNotes { margin-top: 10px; display: flex; flex-direction: column; gap: 3px; }
	.indNotes div { font-size: 9.5px; line-height: 1.5; color: #c2cad6; }
	.tUp { color: var(--up, #3fb950); }
	.tDn { color: var(--dn, #f85149); }
	.tNeu { color: #c2cad6; }
</style>
