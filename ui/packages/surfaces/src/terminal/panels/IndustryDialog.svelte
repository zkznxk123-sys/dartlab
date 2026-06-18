<script lang="ts">
	// 산업 분석 다이얼로그 — 산업이 *주체*(회사 주체 PercentileCrossDialog와 직교). 좌측 sweep 진입.
	//  · 랜드스케이프: 전체 산업을 선택 렌즈로 랭킹 + 분포(좌측 패널은 top7만, 전체는 여기).
	//  · 드릴: 단일 산업 4질문(수익성·방향·구성원), 각 지표 = 내부 분포 + 34산업 중 위치(rank).
	// 데이터 전부 baked 합성(industryStats·ecosystem·gov 시총), 새 fetch 0. 정직 = industry-analysis-lab 04 §3.
	// 경계: verdict·인과·예측 금지(분포/관측만). supply 0.7%·lifecycle·capex = 미포함(Phase 2).
	import type { Engine, IndustryMacro, IndustryDist } from '../lib/engine';
	import { INDUSTRY_LENSES, lensByKey, lensRank } from '../lib/industryLens';
	import type { Lang } from '../lib/types';
	import DistCurve from './DistCurve.svelte';

	interface Props {
		eng: Engine;
		industryId: string; // '' = 랜드스케이프 진입, 그 외 = 드릴
		lang: Lang;
		onClose: () => void;
		onPick: (code: string) => void;
	}
	let { eng, industryId, lang, onClose, onPick }: Props = $props();

	let view = $state(industryId); // '' = 랜드스케이프, 그 외 = 드릴 산업 id
	let landLens = $state('prof');
	const lens = $derived(lensByKey(landLens));

	const industryIds = $derived([...new Set((eng.raw.eco?.nodes || []).map((n) => n.industry))]);
	const all = $derived(industryIds.map((id) => eng.industryMacro(id)).filter((x): x is IndustryMacro => x != null && x.count >= 10));
	const m = $derived(view ? all.find((x) => x.id === view) ?? eng.industryMacro(view) : null);

	// 랜드스케이프 — 전체 산업을 선택 렌즈로 정렬(lower 반영)
	const landRows = $derived.by(() => {
		const rows = all.filter((x) => lens.valueOf(x) != null).map((x) => ({ x, v: lens.valueOf(x) as number }));
		rows.sort((a, b) => (lens.lower ? a.v - b.v : b.v - a.v));
		return rows;
	});
	const landVals = $derived(landRows.map((r) => r.v));

	// 드릴 지표 cross-industry rank — 이 산업 median 이 34산업 중 위치(거시 핵심).
	function rankOf(getter: (x: IndustryMacro) => number | null, lower: boolean): { pct: number; pos: number; tot: number } | null {
		const mine = m ? getter(m) : null;
		if (mine == null) return null;
		const vals = all.map(getter).filter((v): v is number => v != null);
		if (vals.length < 3) return null;
		const sorted = [...vals].sort((a, b) => (lower ? a - b : b - a));
		const pos = sorted.findIndex((v) => v === mine) + 1;
		const below = vals.filter((v) => (lower ? v > mine : v < mine)).length;
		return { pct: Math.round((below / vals.length) * 100), pos, tot: vals.length };
	}

	interface MetricDef { k: string; kr: string; en: string; unit: string; lower: boolean; band: (x: IndustryMacro) => IndustryDist | null; }
	const Q1: MetricDef[] = [
		{ k: 'opMargin', kr: '영업이익률', en: 'Op margin', unit: '%', lower: false, band: (x) => x.dist.opMargin },
		{ k: 'netMargin', kr: '순이익률', en: 'Net margin', unit: '%', lower: false, band: (x) => x.dist.netMargin },
		{ k: 'roe', kr: 'ROE', en: 'ROE', unit: '%', lower: false, band: (x) => x.dist.roe },
		{ k: 'debtRatio', kr: '부채비율', en: 'Debt', unit: '%', lower: true, band: (x) => x.dist.debtRatio },
		{ k: 'pbr', kr: 'PBR (gov 시총)', en: 'PBR (gov cap)', unit: '배', lower: true, band: (x) => x.pbr }
	];
	const Q3: MetricDef[] = [
		{ k: 'revCagr', kr: '매출 CAGR', en: 'Rev CAGR', unit: '%', lower: false, band: (x) => x.dist.revCagr },
		{ k: 'netIncomeCagr', kr: '순이익 CAGR', en: 'NI CAGR', unit: '%', lower: false, band: (x) => x.dist.netIncomeCagr }
	];

	const fmt = (v: number | null | undefined, unit: string): string =>
		v == null ? '—' : (unit === '배' ? v.toFixed(1) : (Math.abs(v) >= 10 ? Math.round(v).toString() : v.toFixed(1))) + (unit === '배' ? '배' : unit);
	const rankTone = (pct: number): string => (pct >= 66 ? 'tUp' : pct <= 33 ? 'tDn' : 'tNeu');
	const twLabel = (t: number | null): string => (t == null ? '' : t >= 0.55 ? '순풍' : t <= 0.35 ? '역풍' : '중립');
	const polarLabel = $derived(m?.marginIqr == null ? '' : m.marginIqr > 15 ? '넓음(양극)' : m.marginIqr < 8 ? '좁음(동질)' : '보통');

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
				<button class="indBack" onclick={() => (view = '')} title={lang === 'en' ? 'all industries' : '전체 산업'}>◄ {lang === 'en' ? 'all' : '전체'}</button>
				<span class="indWho">{lang === 'en' ? m.en : m.kr}<i>n={m.count}{#if m.tailwind != null} · {twLabel(m.tailwind)} {m.tailwind.toFixed(2)}{/if}{#if m.macroPhase} · {lang === 'en' ? 'macro' : '국면'} {m.macroPhase}{/if}</i></span>
			{:else}
				<span class="scrTitle">{lang === 'en' ? 'INDUSTRY ANALYSIS' : '산업 분석'}</span>
				<span class="indWho">{lang === 'en' ? `${landRows.length} industries` : `${landRows.length}개 산업`}<i>{lang === 'en' ? 'click → drill' : '클릭 → 산업 상세'}</i></span>
			{/if}
			<span class="indLens">{lang === 'en' ? 'cross-industry distribution facts (not a verdict)' : '34산업 cross-section 분포 사실 (판정 아님)'}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		<div class="indBody">
			{#if view && m}
				<!-- ── 드릴: 단일 산업 4질문 ── -->
				<section class="indSec">
					<h3 class="indH">{lang === 'en' ? '1 · Profitability structure' : '1 · 수익성 구조'}</h3>
					<div class="indMetrics">
						{#each Q1 as d (d.k)}
							{@const band = d.band(m)}
							{@const r = rankOf((x) => d.band(x)?.median ?? null, d.lower)}
							<div class="indMetric">
								<span class="indMName">{lang === 'en' ? d.en : d.kr}</span>
								<span class="indMCurve">{#if band}<DistCurve {band} value={band.median} p={r ? r.pct : 50} unit={d.unit} {lang} h={26} neutral={d.lower} />{:else}<span class="indDash">n&lt;10</span>{/if}</span>
								<span class="indMVal mono">{fmt(band?.median, d.unit)}</span>
								<span class={'indMRank ' + (r ? rankTone(r.pct) : 'tNeu')}>{#if r}{lang === 'en' ? r.pos + '/' + r.tot : '산업 ' + r.pos + '/' + r.tot + '위'}{:else}—{/if}</span>
							</div>
						{/each}
					</div>
					<div class="indFacts">
						<span>{lang === 'en' ? 'Margin spread (IQR)' : '마진 양극화(IQR)'} <b>{m.marginIqr ?? '—'}%p</b> {polarLabel}</span>
						<span>{lang === 'en' ? 'Loss/low-margin share' : '적자·저수익 비중'} <b>{m.bucket.profRisk}%</b></span>
						<span>{lang === 'en' ? 'Liquidity-risk share' : '유동성위험 비중'} <b>{m.bucket.liqRisk}%</b></span>
					</div>
				</section>

				<section class="indSec">
					<h3 class="indH">{lang === 'en' ? '2 · Direction & drivers' : '2 · 방향 · 동인'}</h3>
					<div class="indMetrics">
						{#each Q3 as d (d.k)}
							{@const band = d.band(m)}
							{@const r = rankOf((x) => d.band(x)?.median ?? null, d.lower)}
							<div class="indMetric">
								<span class="indMName">{lang === 'en' ? d.en : d.kr}</span>
								<span class="indMCurve">{#if band}<DistCurve {band} value={band.median} p={r ? r.pct : 50} unit={d.unit} {lang} h={26} />{:else}<span class="indDash">n&lt;10</span>{/if}</span>
								<span class="indMVal mono">{fmt(band?.median, d.unit)}</span>
								<span class={'indMRank ' + (r ? rankTone(r.pct) : 'tNeu')}>{#if r}{lang === 'en' ? r.pos + '/' + r.tot : '산업 ' + r.pos + '/' + r.tot + '위'}{:else}—{/if}</span>
							</div>
						{/each}
					</div>
					<div class="indFacts">
						{#if m.cfSignature}<span>{lang === 'en' ? 'Cashflow signature' : '현금흐름 시그니처'} <b>{m.cfSignature.pattern}</b> {m.cfSignature.share}%</span>{/if}
						<span>{lang === 'en' ? 'Cash-distress share' : '현금위기 비중'} <b>{m.bucket.cfDistress}%</b></span>
						{#if m.tailwind != null}<span>{lang === 'en' ? 'Macro tailwind' : '거시 순풍/역풍'} <b class={m.tailwind >= 0.55 ? 'tUp' : m.tailwind <= 0.35 ? 'tDn' : 'tNeu'}>{twLabel(m.tailwind)} {m.tailwind.toFixed(2)}</b></span>{/if}
					</div>
				</section>

				<section class="indSec">
					<h3 class="indH">{lang === 'en' ? '3 · Member topology' : '3 · 구성원 지형'} <i class="indHsub">{lang === 'en' ? 'click → company' : '클릭 → 종목'}</i></h3>
					<div class="indMembers">
						{#each [{ kr: 'ROE 상위', en: 'Top ROE', list: m.top.roe, unit: '%' }, { kr: '성장 상위', en: 'Top growth', list: m.top.growth, unit: '%' }, { kr: '부채 주의', en: 'High debt', list: m.top.risk, unit: '%' }] as col (col.en)}
							<div class="indMemCol">
								<div class="indMemHd">{lang === 'en' ? col.en : col.kr}</div>
								{#each col.list as mem (mem.code)}
									<button class="indMemRow" onclick={() => onPick(mem.code)}>
										<span class="indMemNm">{mem.name}</span>
										<span class="indMemV mono">{fmt(mem.value, col.unit)}</span>
									</button>
								{/each}
							</div>
						{/each}
					</div>
				</section>
			{:else}
				<!-- ── 랜드스케이프: 전체 산업 랭킹 + 분포 ── -->
				<div class="indLensRow">
					{#each INDUSTRY_LENSES as l (l.key)}
						<button class={'indLensBtn' + (landLens === l.key ? ' on' : '')} onclick={() => (landLens = l.key)} title={l.note}>{lang === 'en' ? l.en : l.kr}</button>
					{/each}
				</div>
				<div class="indLand">
					{#each landRows as r, i (r.x.id)}
						{@const band = lens.bandOf(r.x)}
						{@const rank = lensRank(lens, r.v, landVals)}
						<button class="indLandRow" onclick={() => (view = r.x.id)} title={`${r.x.kr} · n=${r.x.count} · ${lang === 'en' ? 'click → drill' : '클릭 → 상세'}`}>
							<span class="indLR mono">{i + 1}</span>
							<span class="indLName">{lang === 'en' ? r.x.en : r.x.kr}{#if r.x.tailwind != null}<i class={'swTw ' + (r.x.tailwind >= 0.55 ? 'tw-up' : r.x.tailwind <= 0.35 ? 'tw-dn' : 'tw-nu')}>{r.x.tailwind >= 0.55 ? '↑' : r.x.tailwind <= 0.35 ? '↓' : '·'}</i>{/if}</span>
							<span class="indLCurve">{#if band}<DistCurve {band} value={r.v} p={rank} unit={lens.unit} {lang} h={20} neutral={lens.lower} />{/if}</span>
							<span class={'indLVal mono ' + rankTone(rank)}>{fmt(r.v, lens.unit)}</span>
							<span class="indLN mono">{r.x.count}</span>
						</button>
					{/each}
				</div>
			{/if}

			<div class="indNotes">
				<div>※ {lang === 'en'
					? 'Distribution: industryStats · KSIC · equal-weight · listed primary (≠ KRX cap-weighted index). PBR uses gov market-cap, not KRX.'
					: '분포: industryStats · KSIC · 동일가중 · 상장 primary (≠ KRX 시총가중 업종지수). PBR은 gov 시총(KRX 아님).'}</div>
				<div>※ {lang === 'en'
					? 'Bucket % = scan-grade buckets (no ordinal-mean). Median ROE/ROA compressed in KR → spread is the signal. Snapshot, not a trend.'
					: '버킷 % = scan grade 버킷(ordinal 평균 아님). KR median ROE/ROA 압축 → 분산이 신호. 스냅샷(추세 아님).'}</div>
				<div>※ {lang === 'en'
					? 'Distribution facts only — no buy/sell, no causal/forecast (polarization is observed spread, not a verdict).'
					: '분포 사실만 — 매수/매도·인과/예측 금지(양극화는 관측된 격차이지 판정 아님).'}</div>
			</div>
		</div>
	</div>
</div>

<style>
	.indModal { width: min(760px, 95vw); }
	.indBack { background: none; border: 1px solid var(--dl-line, #2a3142); border-radius: 3px; color: #aeb6c2; font-size: 10px; padding: 1px 7px; cursor: pointer; }
	.indBack:hover { color: var(--dl-ink, #c8cfdb); border-color: var(--amber, #fb923c); }
	.indWho { font-size: 12px; font-weight: 700; color: var(--dl-ink, #c8cfdb); }
	.indWho i { font-style: normal; font-weight: 400; margin-left: 7px; font-size: 10px; color: #aeb6c2; }
	.indLens { font-size: 10px; color: #aeb6c2; font-style: italic; }
	.indBody { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 10px 14px 14px; }
	.indSec { margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--dl-line, #1b2130); }
	.indH { margin: 0 0 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.02em; color: var(--dl-ink, #c8cfdb); display: flex; align-items: baseline; gap: 8px; }
	.indHsub { font-style: normal; font-weight: 400; font-size: 9px; color: #aeb6c2; }
	.indMetrics { display: flex; flex-direction: column; gap: 4px; }
	.indMetric { display: grid; grid-template-columns: 92px 1fr 56px 78px; align-items: center; gap: 9px; }
	.indMName { font-size: 11px; color: var(--dl-ink, #c8cfdb); }
	.indMCurve { min-width: 0; line-height: 0; }
	.indMVal { font-size: 11px; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; color: var(--dl-ink, #c8cfdb); }
	.indMRank { font-size: 9.5px; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
	.indDash { font-size: 9.5px; color: #aeb6c2; font-style: italic; }
	.indFacts { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 8px; font-size: 10px; color: #aeb6c2; }
	.indFacts b { color: var(--dl-ink, #c8cfdb); font-variant-numeric: tabular-nums; }
	.indMembers { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
	.indMemCol { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
	.indMemHd { font-size: 9px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: #aeb6c2; margin-bottom: 2px; }
	.indMemRow { display: flex; justify-content: space-between; gap: 6px; align-items: baseline; background: none; border: 0; padding: 1.5px 2px; cursor: pointer; text-align: left; border-radius: 2px; }
	.indMemRow:hover { background: rgba(255, 255, 255, 0.05); }
	.indMemNm { font-size: 10px; color: var(--dl-ink, #c8cfdb); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.indMemV { font-size: 9.5px; color: #aeb6c2; flex-shrink: 0; font-variant-numeric: tabular-nums; }
	/* 랜드스케이프 — 전체 산업 랭킹 */
	.indLensRow { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 8px; }
	.indLensBtn { font-size: 10px; padding: 2px 9px; border-radius: 3px; border: 1px solid var(--dl-line, #2a3142); background: rgba(255, 255, 255, 0.02); color: #aeb6c2; cursor: pointer; }
	.indLensBtn:hover { color: var(--dl-ink, #c8cfdb); }
	.indLensBtn.on { color: var(--amber, #fb923c); border-color: color-mix(in srgb, var(--amber, #fb923c) 55%, transparent); background: color-mix(in srgb, var(--amber, #fb923c) 12%, transparent); }
	.indLand { display: flex; flex-direction: column; margin-bottom: 10px; }
	.indLandRow { display: grid; grid-template-columns: 18px 96px 1fr 56px 26px; align-items: center; gap: 9px; padding: 2px 4px; background: none; border: 0; border-bottom: 1px solid var(--dl-line, #1b2130); cursor: pointer; text-align: left; }
	.indLandRow:hover { background: var(--dl-bg-overlay, rgba(255, 255, 255, 0.04)); }
	.indLR { font-size: 9px; color: #aeb6c2; text-align: center; }
	.indLName { font-size: 11px; color: var(--dl-ink, #c8cfdb); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 3px; }
	.indLCurve { min-width: 0; line-height: 0; }
	.indLVal { font-size: 11px; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
	.indLN { font-size: 9px; color: #aeb6c2; text-align: right; font-variant-numeric: tabular-nums; }
	.swTw { font-style: normal; font-size: 9px; font-weight: 700; }
	.swTw.tw-up { color: var(--up, #3fb950); }
	.swTw.tw-dn { color: var(--dn, #f85149); }
	.swTw.tw-nu { color: #aeb6c2; }
	.indNotes { margin-top: 4px; display: flex; flex-direction: column; gap: 3px; }
	.indNotes div { font-size: 9px; line-height: 1.45; color: #aeb6c2; }
	.tUp { color: var(--up, #3fb950); }
	.tDn { color: var(--dn, #f85149); }
	.tNeu { color: #aeb6c2; }
</style>
