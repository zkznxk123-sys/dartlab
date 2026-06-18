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
	let landView = $state<'rank' | 'map'>('rank'); // 순위표 ↔ 지형도(구조 관측)
	let hoverId = $state(''); // 지형도 hover 산업
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

	// ── 지형도(map): 산업 = (수익 수준 × 마진 격차) 평면. 위치 = 구조 관측, 판정 아님.
	//   x = 영업이익률 median(수익 수준) · y = marginIqr(산업 내 회사 간 격차) · 크기 = n · 중앙 십자 = 중앙값 기준선.
	//   y(격차)는 정의상 좋고나쁨 아님(04 §3) → 2D 위치의 절반이 구조적으로 verdict-free.
	const _med = (arr: number[]): number => { const s = [...arr].sort((a, b) => a - b); const k = Math.floor(s.length / 2); return s.length % 2 ? s[k] : (s[k - 1] + s[k]) / 2; };
	const mapGeo = $derived.by(() => {
		const pts = all
			.map((x) => ({ x, mx: x.dist.opMargin?.median ?? null, my: x.marginIqr }))
			.filter((p): p is { x: IndustryMacro; mx: number; my: number } => p.mx != null && p.my != null);
		if (pts.length < 3) return null;
		const W = 700, H = 360, ml = 52, mr = 70, mt = 14, mb = 28;
		const x0 = ml, x1 = W - mr, y0 = mt, y1 = H - mb;
		const xs = pts.map((p) => p.mx), ys = pts.map((p) => p.my);
		let xmin = Math.min(...xs), xmax = Math.max(...xs);
		const xpad = (xmax - xmin || 1) * 0.08; xmin -= xpad; xmax += xpad;
		const ymax = Math.max(...ys, 1) * 1.08;
		const maxN = Math.max(...pts.map((p) => p.x.count));
		const sx = (v: number) => x0 + ((v - xmin) / (xmax - xmin)) * (x1 - x0);
		const sy = (v: number) => y1 - (v / ymax) * (y1 - y0);
		const rOf = (n: number) => 3.5 + ((Math.sqrt(n) - Math.sqrt(10)) / (Math.sqrt(maxN) - Math.sqrt(10) || 1)) * 10;
		const dots = pts.map((p) => ({ x: p.x, cx: sx(p.mx), cy: sy(p.my), r: rOf(p.x.count), mx: p.mx, my: p.my, faint: p.x.count < 15, showLbl: false }));
		// 라벨 충돌 제거(greedy): 큰 점 우선 배치, 겹치면 라벨만 숨김(점은 유지·hover 시 full). 위치 불변(정직).
		const placed: { x1: number; y1: number; x2: number; y2: number }[] = [];
		[...dots].sort((a, b) => b.r - a.r).forEach((d) => {
			if (d.faint) return;
			const nm = (d.x.kr || '').slice(0, 5);
			const lx = d.cx + d.r + 2, ly = d.cy - 6, lw = nm.length * 8 + 12, lh = 12;
			const box = { x1: lx, y1: ly, x2: lx + lw, y2: ly + lh };
			const hit = placed.some((p) => !(box.x2 < p.x1 || box.x1 > p.x2 || box.y2 < p.y1 || box.y1 > p.y2));
			if (!hit) { d.showLbl = true; placed.push(box); }
		});
		return { W, H, x0, x1, y0, y1, cx: sx(_med(xs)), cy: sy(_med(ys)), zx: xmin < 0 && xmax > 0 ? sx(0) : null, dots, xmin, xmax, ymax };
	});
	const hover = $derived(mapGeo ? (mapGeo.dots.find((d) => d.x.id === hoverId) ?? null) : null);

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
	// 최근 방향(YoY) 합의 — 마진·ROE·매출 델타 부호 다수결(단일 델타 노이즈 방어). 다년 CAGR과 직교.
	const dir = $derived(m?.direction ?? null);
	const dirSigns = $derived(dir ? [dir.opMarginDelta, dir.roeDelta, dir.revenueYoyPct].filter((x): x is number => x != null) : []);
	const dirLabel = $derived.by(() => {
		if (dirSigns.length < 2) return { txt: '', cls: 'tNeu' };
		const up = dirSigns.filter((x) => x > 0).length, dn = dirSigns.filter((x) => x < 0).length;
		return up > dn ? { txt: '개선', cls: 'tUp' } : dn > up ? { txt: '악화', cls: 'tDn' } : { txt: '혼조', cls: 'tNeu' };
	});
	const sgn = (v: number | null | undefined, u: string): string => (v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(1) + u);

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
				<button class="indBack" onclick={() => (view = '')} title={lang === 'en' ? 'back to list' : '목록으로'}>◄ {lang === 'en' ? 'list' : '목록'}</button>
				<span class="indWho">{lang === 'en' ? m.en : m.kr}<i>n={m.count}{#if m.tailwind != null} · {twLabel(m.tailwind)} {m.tailwind.toFixed(2)}{/if}{#if m.macroPhase} · {lang === 'en' ? 'macro' : '국면'} {m.macroPhase}{/if}</i></span>
			{:else}
				<span class="scrTitle">{lang === 'en' ? 'INDUSTRY DETAIL' : '산업 상세보기'}</span>
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
								<span class={'indMRank ' + (r ? rankTone(r.pct) : 'tNeu')} title={r ? (lang === 'en' ? `${r.pos} of ${r.tot} industries` : `${r.tot}개 산업 중 ${r.pos}위`) : ''}>{#if r}{lang === 'en' ? 'top ' + Math.max(1, Math.round((r.pos / r.tot) * 100)) + '%' : '상위 ' + Math.max(1, Math.round((r.pos / r.tot) * 100)) + '%'}{:else}—{/if}</span>
							</div>
						{/each}
					</div>
					<div class="indFacts">
						<span>{lang === 'en' ? 'Margin spread (IQR)' : '마진 분산(IQR)'} <b>{m.marginIqr ?? '—'}%p</b> {polarLabel}</span>
						<span>{lang === 'en' ? 'Loss share' : '적자 비중'} <b>{m.bucket.lossRisk}%</b></span>
						<span>{lang === 'en' ? 'Thin-margin share' : '저수익↓ 비중'} <b>{m.bucket.profRisk}%</b></span>
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
								<span class={'indMRank ' + (r ? rankTone(r.pct) : 'tNeu')} title={r ? (lang === 'en' ? `${r.pos} of ${r.tot} industries` : `${r.tot}개 산업 중 ${r.pos}위`) : ''}>{#if r}{lang === 'en' ? 'top ' + Math.max(1, Math.round((r.pos / r.tot) * 100)) + '%' : '상위 ' + Math.max(1, Math.round((r.pos / r.tot) * 100)) + '%'}{:else}—{/if}</span>
							</div>
						{/each}
					</div>
					<div class="indFacts">
						{#if dir && dirSigns.length >= 2}
							<span class="indDir">{lang === 'en' ? 'Recent direction (YoY)' : '최근 방향(YoY)'} <b>{lang === 'en' ? 'margin' : '마진'} {sgn(dir.opMarginDelta, '%p')} · ROE {sgn(dir.roeDelta, '%p')} · {lang === 'en' ? 'rev' : '매출'} {sgn(dir.revenueYoyPct, '%')}</b> <em class={dirLabel.cls}>{lang === 'en' ? (dirLabel.txt === '개선' ? 'improving' : dirLabel.txt === '악화' ? 'deteriorating' : 'mixed') : dirLabel.txt}</em></span>
						{/if}
						{#if m.cfSignature}<span>{lang === 'en' ? 'Cashflow signature' : '현금흐름 시그니처'} <b>{m.cfSignature.pattern}</b> {m.cfSignature.share}%</span>{/if}
						<span>{lang === 'en' ? 'Cash-distress share' : '현금위기 비중'} <b>{m.bucket.cfDistress}%</b></span>
						{#if m.tailwind != null}<span>{lang === 'en' ? 'Macro tailwind' : '거시 순풍/역풍'} <b class={m.tailwind >= 0.55 ? 'tUp' : m.tailwind <= 0.35 ? 'tDn' : 'tNeu'}>{twLabel(m.tailwind)} {m.tailwind.toFixed(2)}</b></span>{/if}
					</div>
					{#if dir && dirSigns.length >= 2 && (m.dist.netIncomeCagr || m.dist.revCagr)}
						<div class="indHint">※ {lang === 'en' ? 'CAGR = multi-year average; YoY direction = recent change. Divergence (e.g. +CAGR but −YoY) = possible cyclical peak (observation, not forecast).' : 'CAGR=다년 평균 · YoY 방향=최근 변화. 둘이 갈리면(예: CAGR+ 인데 YoY−) 순환 고점 가능성(관측이지 예측 아님).'}</div>
					{/if}
				</section>

				<section class="indSec">
					<h3 class="indH">{lang === 'en' ? '3 · Member topology' : '3 · 구성원 지형'} <i class="indHsub">{lang === 'en' ? 'click → company' : '클릭 → 종목'}</i></h3>
					<div class="indMembers">
						{#each [{ kr: 'ROE 상위', en: 'Top ROE', list: m.top.roe, unit: '%' }, { kr: '성장 상위', en: 'Top growth', list: m.top.growth, unit: '%' }, { kr: '부실 주의', en: 'Distressed', list: m.top.risk, unit: '%' }] as col (col.en)}
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
					<div class="indHint">※ {lang === 'en'
						? 'Distressed = flagged by debt-grade (주의/고위험) OR loss OR cash-distress pattern (value shown = debt ratio) — not raw high-debt. Click → company.'
						: '부실 주의 = 부채등급(주의·고위험) 또는 적자 또는 현금위기 패턴으로 플래그(표시값=부채비율) — 절대 고부채 아님. 클릭 → 종목.'}</div>
				</section>
			{:else}
				<!-- ── 랜드스케이프: 전체 산업 랭킹 + 분포 ── -->
				<div class="indLensRow">
					<div class="indViewTog">
						<button class={'indVBtn' + (landView === 'rank' ? ' on' : '')} onclick={() => (landView = 'rank')}>{lang === 'en' ? 'Rank' : '순위'}</button>
						<button class={'indVBtn' + (landView === 'map' ? ' on' : '')} onclick={() => (landView = 'map')} title={lang === 'en' ? 'margin level x spread terrain' : '수익 수준 x 마진 격차 지형'}>{lang === 'en' ? 'Map' : '지형도'}</button>
					</div>
					{#if landView === 'rank'}
						{#each INDUSTRY_LENSES as l (l.key)}
							<button class={'indLensBtn' + (landLens === l.key ? ' on' : '')} onclick={() => (landLens = l.key)} title={l.note}>{lang === 'en' ? l.en : l.kr}</button>
						{/each}
					{/if}
				</div>
				{#if landView === 'rank'}
				<div class="indLand">
					{#each landRows as r, i (r.x.id)}
						{@const band = lens.bandOf(r.x)}
						{@const rank = lensRank(lens, r.v, landVals)}
						<button class="indLandRow" onclick={() => (view = r.x.id)} title={`${r.x.kr} · n=${r.x.count} · ${lang === 'en' ? 'click → drill' : '클릭 → 상세'}`}>
							<span class="indLR mono">{i + 1}</span>
							<span class="indLName">{lang === 'en' ? r.x.en : r.x.kr}{#if r.x.tailwind != null}<i class={'swTw ' + (r.x.tailwind >= 0.55 ? 'tw-up' : r.x.tailwind <= 0.35 ? 'tw-dn' : 'tw-nu')}>{r.x.tailwind >= 0.55 ? '↑' : r.x.tailwind <= 0.35 ? '↓' : '·'}</i>{/if}</span>
							<span class="indLCurve">{#if band}<DistCurve {band} value={r.v} p={rank} unit={lens.unit} {lang} h={20} neutral={lens.lower} />{/if}</span>
							<span class={'indLVal mono ' + rankTone(rank)}>{fmt(r.v, lens.unit)}</span>
							<span class="indLN mono" class:warn={r.x.count < 15} title={r.x.count < 15 ? (lang === 'en' ? 'small sample — rank less stable' : '표본 작아 순위 불안정') : ''}>{r.x.count}{#if r.x.count < 15}⚠{/if}</span>
						</button>
					{/each}
				</div>
				{:else}
					{#if mapGeo}
						{@const g = mapGeo}
						<div class="indMapWrap">
							<svg viewBox={`0 0 ${g.W} ${g.H}`} class="indMap" role="img" aria-label={lang === 'en' ? 'Industry margin-level vs spread map' : '산업 수익수준 x 마진격차 지형도'}>
								<line x1={g.x0} y1={g.y1} x2={g.x1} y2={g.y1} class="mapAx" />
								<line x1={g.x0} y1={g.y0} x2={g.x0} y2={g.y1} class="mapAx" />
								{#if g.zx != null}<line x1={g.zx} y1={g.y0} x2={g.zx} y2={g.y1} class="mapZero" /><text x={g.zx} y={g.y1 + 10} class="mapTick" text-anchor="middle">0%</text>{/if}
								<line x1={g.cx} y1={g.y0} x2={g.cx} y2={g.y1} class="mapCross" />
								<line x1={g.x0} y1={g.cy} x2={g.x1} y2={g.cy} class="mapCross" />
								<text x={g.cx + 2} y={g.y0 + 8} class="mapCrossLbl">{lang === 'en' ? 'median' : '중앙값'}</text>
								{#each g.dots as d (d.x.id)}
									<g class={'mapDot' + (hoverId === d.x.id ? ' on' : '')} role="button" tabindex="0" aria-label={d.x.kr} onclick={() => (view = d.x.id)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); view = d.x.id; } }} onmouseenter={() => (hoverId = d.x.id)} onmouseleave={() => (hoverId = '')} onfocus={() => (hoverId = d.x.id)} onblur={() => (hoverId = '')}>
										<circle cx={d.cx} cy={d.cy} r={d.r} class="mapC" class:faint={d.faint} />
										{#if d.showLbl}<text x={d.cx + d.r + 2} y={d.cy + 3} class="mapLbl">{(lang === 'en' ? d.x.en : d.x.kr).slice(0, 5)}{#if d.x.tailwind != null && (d.x.tailwind >= 0.55 || d.x.tailwind <= 0.35)} <tspan class={d.x.tailwind >= 0.55 ? 'tUp' : 'tDn'}>{d.x.tailwind >= 0.55 ? '↑' : '↓'}</tspan>{/if}</text>{/if}
									</g>
								{/each}
								{#if hover}
									<circle cx={hover.cx} cy={hover.cy} r={hover.r} class="mapC mapCtop" pointer-events="none" />
									<text x={hover.cx + hover.r + 2} y={hover.cy + 3} class="mapLbl mapLtop" pointer-events="none">{lang === 'en' ? hover.x.en : hover.x.kr}</text>
								{/if}
								<text x={(g.x0 + g.x1) / 2} y={g.H - 2} class="mapAxLbl" text-anchor="middle">{lang === 'en' ? 'op-margin median →' : '영업이익률 중앙값(수익 수준) →'}</text>
								<text x={13} y={(g.y0 + g.y1) / 2} class="mapAxLbl" text-anchor="middle" transform={`rotate(-90 13 ${(g.y0 + g.y1) / 2})`}>{lang === 'en' ? 'margin spread IQR ↑' : '마진 격차(IQR) ↑'}</text>
								<text x={g.x0} y={g.y1 + 10} class="mapTick" text-anchor="start">{Math.round(g.xmin)}%</text>
								<text x={g.x1} y={g.y1 + 10} class="mapTick" text-anchor="end">{Math.round(g.xmax)}%</text>
								<text x={g.x0 - 5} y={g.y1} class="mapTick" text-anchor="end">0</text>
								<text x={g.x0 - 5} y={g.y0 + 8} class="mapTick" text-anchor="end">{Math.round(g.ymax)}</text>
							</svg>
							<div class="indMapInfo">
								{#if hover}
									<b>{lang === 'en' ? hover.x.en : hover.x.kr}</b> · n={hover.x.count}{#if hover.x.count < 15}⚠{/if} · {lang === 'en' ? 'margin' : '마진'} {hover.mx.toFixed(1)}% · {lang === 'en' ? 'spread' : '격차'} {hover.my.toFixed(1)}%p{#if hover.x.tailwind != null} · <span class={hover.x.tailwind >= 0.55 ? 'tUp' : hover.x.tailwind <= 0.35 ? 'tDn' : 'tNeu'}>{twLabel(hover.x.tailwind)}</span>{/if} · <em>{lang === 'en' ? 'click → detail' : '클릭 → 상세'}</em>
								{:else}
									{lang === 'en' ? '※ dot = industry · x = margin level (op-margin median) · y = within-industry spread (IQR) · position = structural observation, not a verdict · larger = more members · faint = n<15' : '※ 점=산업 · 가로=수익 수준(영업이익률 중앙값) · 세로=산업 내 격차(IQR) · 위치=구조 관측이지 판정 아님 · 클수록 멤버 많음 · 흐림=n<15'}
								{/if}
							</div>
						</div>
					{/if}
				{/if}
			{/if}

			<div class="indNotes">
				<div>※ {lang === 'en'
					? 'Distribution: industryStats · KSIC · equal-weight · listed primary (≠ KRX cap-weighted index). PBR uses gov market-cap, not KRX.'
					: '분포: industryStats · KSIC · 동일가중 · 상장 primary (≠ KRX 시총가중 업종지수). PBR은 gov 시총(KRX 아님).'}</div>
				<div>※ {lang === 'en'
					? 'Bucket % = scan-grade buckets (no ordinal-mean). Median ROE/ROA compressed in KR → spread is the signal. n<15 (⚠) ranks less stable.'
					: '버킷 % = scan grade 버킷(ordinal 평균 아님). KR median ROE/ROA 압축 → 분산이 신호. n<15(⚠) 순위 불안정.'}</div>
				<div>※ {lang === 'en'
					? 'Snapshot of current listed members (survivorship: delisted/unlisted excluded) — not a trend; rank may shift year to year.'
					: '현재 상장 멤버 스냅샷(생존편향: 상폐·비상장 제외) — 추세 아님, 순위는 연도별로 바뀔 수 있음.'}</div>
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
	.indDir em { font-style: normal; font-weight: 700; margin-left: 2px; }
	.indHint { font-size: 9px; color: #aeb6c2; line-height: 1.4; margin-top: 5px; font-style: italic; }
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
	.indLand { display: flex; flex-direction: column; margin-bottom: 10px; max-height: 56vh; overflow-y: auto; }
	.indLandRow { display: grid; grid-template-columns: 18px 96px 1fr 56px 26px; align-items: center; gap: 9px; padding: 2px 4px; background: none; border: 0; border-bottom: 1px solid var(--dl-line, #1b2130); cursor: pointer; text-align: left; }
	.indLandRow:hover { background: var(--dl-bg-overlay, rgba(255, 255, 255, 0.04)); }
	.indLR { font-size: 9px; color: #aeb6c2; text-align: center; }
	.indLName { font-size: 11px; color: var(--dl-ink, #c8cfdb); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 3px; }
	.indLCurve { min-width: 0; line-height: 0; }
	.indLVal { font-size: 11px; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
	.indLN { font-size: 9px; color: #aeb6c2; text-align: right; font-variant-numeric: tabular-nums; }
	.indLN.warn { color: var(--warn, #d29922); }
	.swTw { font-style: normal; font-size: 9px; font-weight: 700; }
	.swTw.tw-up { color: var(--up, #3fb950); }
	.swTw.tw-dn { color: var(--dn, #f85149); }
	.swTw.tw-nu { color: #aeb6c2; }
	/* 뷰 토글 + 지형도(구조 관측) */
	.indViewTog { display: inline-flex; border: 1px solid var(--dl-line, #2a3142); border-radius: 3px; overflow: hidden; margin-right: 4px; }
	.indVBtn { font-size: 10px; padding: 2px 9px; border: 0; background: rgba(255, 255, 255, 0.02); color: #aeb6c2; cursor: pointer; }
	.indVBtn:hover { color: var(--dl-ink, #c8cfdb); }
	.indVBtn.on { color: var(--amber, #fb923c); background: color-mix(in srgb, var(--amber, #fb923c) 14%, transparent); }
	.indMapWrap { margin-bottom: 10px; }
	.indMap { width: 100%; height: auto; display: block; }
	.mapAx { stroke: var(--dl-line, #2a3142); stroke-width: 1; }
	.mapZero { stroke: color-mix(in srgb, var(--dl-ink, #c8cfdb) 22%, transparent); stroke-width: 1; stroke-dasharray: 1 3; }
	.mapCross { stroke: color-mix(in srgb, var(--amber, #fb923c) 26%, transparent); stroke-width: 1; stroke-dasharray: 3 3; }
	.mapCrossLbl { fill: color-mix(in srgb, var(--amber, #fb923c) 70%, transparent); font-size: 8px; }
	.mapDot { cursor: pointer; outline: none; }
	.mapC { fill: color-mix(in srgb, #6aa3ff 42%, transparent); stroke: #6aa3ff; stroke-width: 1; transition: fill 0.12s; }
	.mapC.faint { fill: color-mix(in srgb, #6aa3ff 16%, transparent); stroke: color-mix(in srgb, #6aa3ff 45%, transparent); }
	.mapDot.on .mapC, .mapCtop { fill: color-mix(in srgb, var(--amber, #fb923c) 60%, transparent); stroke: var(--amber, #fb923c); }
	.mapDot:focus-visible .mapC { stroke: var(--amber, #fb923c); stroke-width: 2; }
	.mapLbl { fill: #8b93a0; font-size: 8.5px; pointer-events: none; }
	.mapDot.on .mapLbl, .mapLtop { fill: var(--dl-ink, #c8cfdb); font-weight: 700; }
	.mapLbl .tUp { fill: var(--up, #3fb950); }
	.mapLbl .tDn { fill: var(--dn, #f85149); }
	.mapAxLbl { fill: #aeb6c2; font-size: 9px; }
	.mapTick { fill: #6b7280; font-size: 8px; }
	.indMapInfo { font-size: 9.5px; color: #aeb6c2; line-height: 1.45; margin-top: 4px; padding: 0 2px; min-height: 26px; }
	.indMapInfo b { color: var(--dl-ink, #c8cfdb); }
	.indMapInfo em { font-style: normal; color: var(--amber, #fb923c); }
	.indNotes { margin-top: 4px; display: flex; flex-direction: column; gap: 3px; }
	.indNotes div { font-size: 9px; line-height: 1.45; color: #aeb6c2; }
	.tUp { color: var(--up, #3fb950); }
	.tDn { color: var(--dn, #f85149); }
	.tNeu { color: #aeb6c2; }
</style>
