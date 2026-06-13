<script lang="ts">
	import type { Candle, FinMode, ProductIndexItem, TerminalFinanceBundle } from '@dartlab/ui-contracts';
	import { useDartLabRuntime } from '@dartlab/ui-runtime';
	import type { Company, Lang, Tone, Num } from '../lib/types';
	import Panel from '../ui/Panel.svelte';
	import PriceChart from '../charts/PriceChart.svelte';
	import MiniFinChart from '../charts/MiniFinChart.svelte';
	import FinFullscreen from './FinFullscreen.svelte';
	import { tx, txc, chgClass, sign, fmtNum, sparkPts as kpiSpark } from '../ui/helpers';
	import { fmtKRW } from '../lib/engine';

	interface Props {
		co: Company;
		lang: Lang;
		kpis?: { l: string; v: string; t: string; s?: number[] }[];
		// 전체화면 심볼 점프 (PriceChart ⌘K·/) — 검색·전환은 터미널 엔진 관통
		suggest?: (q: string, n: number) => { code: string; name: string; industry: string }[];
		onPick?: (code: string) => void;
	}
	let { co, lang, kpis = [], suggest, onPick }: Props = $props();
	const rt = useDartLabRuntime();
	const localViewerHref = $derived(rt.viewer.urlForCompany(co.code));
	const localTerminalHref = $derived(`/analysis/${co.code}`);
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	// 주가 캔들 (hyparquet 온디맨드) — 부팅 비차단, 회사 전환 시 재로드. 재무는 아래 별도 섹션.
	// 주가차트 컨트롤(기간·지표·드로잉·실적·밸류·로그·전체화면)은 PriceChart 인-차트 툴바로 이전.
	// ★소프트 스왑 — 전환 중 candles 를 비우지 않아 PriceChart(klinecharts 인스턴스·전체화면 상태)가
	// 언마운트되지 않는다 (전체화면 심볼 점프의 전제 + 깜빡임 제거, viewer soft-swap 동일 패턴).
	// chartCode 는 candles 와 *원자적으로* 갱신 — 전환 중 "새 code + 옛 candles" 불일치가 PriceChart
	// 데이터 effect(드로잉 복원·lazy 백필 키)에 새는 것을 차단.
	let candles = $state<Candle[] | null>(null);
	let chartCode = $state('');
	let chartName = $state('');
	let candleState = $state<'loading' | 'ready' | 'unavail'>('loading');
	const priceYear = $derived(+co.price.asOf.slice(0, 4) || new Date().getFullYear());
	$effect(() => {
		const code = co.code;
		const nm = co.name.kr;
		const yr = priceYear;
		candleState = 'loading';
		let cancelled = false;
		rt.price.initial(code, yr).then((r) => {
			if (cancelled) return;
			candles = r && r.candles.length ? r.candles : null;
			chartCode = code;
			chartName = nm;
			candleState = r && r.candles.length ? 'ready' : 'unavail';
		});
		return () => {
			cancelled = true;
		};
	});

	// 재무 카드 — dart/finance/{code}.parquet (HF hyparquet) 연간/분기/TTM, 온디맨드·회사별
	let finBundle = $state<TerminalFinanceBundle | null>(null);
	let finMode = $state<FinMode>('ttm'); // 그래프 기본 = TTM (추세) — 표는 분기 원값 (우측 패널·다이얼로그)
	let finState = $state<'loading' | 'ready' | 'empty'>('loading');
	const finData = $derived(finBundle ? finBundle.views[finMode] ?? null : null);
	const finModeLabel: Record<FinMode, string> = { ttm: 'TTM', quarter: '분기', annual: '연간' };
	$effect(() => {
		const code = co.code;
		finState = 'loading';
		finBundle = null;
		let cancelled = false;
		rt.finance.bundle(code).then((b) => {
			if (cancelled) return;
			finBundle = b;
			finMode = b ? (b.views.ttm ? 'ttm' : b.defaultMode) : 'quarter'; // TTM 우선 — 분기 부족(신규상장 등)이면 defaultMode 폴백
			finState = b && b.modes.length ? 'ready' : 'empty';
		});
		return () => {
			cancelled = true;
		};
	});

	// 동종업계 — 주가차트 종목비교(VS) 후보 (map/companies relations, 회사별 캐시)
	let chartPeers = $state<{ code: string; name: string }[]>([]);
	$effect(() => {
		const code = co.code;
		let cancelled = false;
		chartPeers = [];
		rt.company.relations(code).then((r) => {
			if (cancelled) return;
			chartPeers = (r?.peers ?? []).filter((p) => p.stockCode && p.stockCode !== code).map((p) => ({ code: p.stockCode, name: p.corpName }));
		});
		return () => {
			cancelled = true;
		};
	});

	// 회사 주요제품 (corpList) — 헤더 빈 가운데 채움. 어댑터 캐시 공유(중복 다운로드 없음).
	let corpMeta = $state<Record<string, ProductIndexItem> | null>(null);
	rt.company.productIndex().then((m) => (corpMeta = m));
	const corpInfo = $derived(corpMeta?.[co.code] ?? null);
	const product = $derived(corpInfo?.product ?? '');
	// 재무제표 분석 전체화면 (FinFullscreen — 버틀러식 탭, ESC 닫기는 컴포넌트 내부)
	let finFull = $state(false);

	const p = $derived(co.price);
	const e = $derived(co.eco);
	// 헤더 가격 정합성 — prices 스냅샷(주배치, 지연 가능)보다 차트 캔들(gov EOD)이 최신이면 캔들 종가 SSOT.
	// 수익률·시총도 같은 기준으로 재계산(시총 = 스냅샷 주식수 × 최신 종가) — 헤더↔차트 불일치 제거.
	// 소프트 스왑 중(chartCode ≠ co.code)엔 옛 회사 캔들이므로 헤더 계산에서 제외 (스냅샷 폴백).
	const lastCandle = $derived(chartCode === co.code && candles && candles.length ? candles[candles.length - 1] : null);
	const dispLast = $derived(lastCandle ? lastCandle.c : p.last);
	const candleRet = (bars: number): number | null => {
		if (!candles || candles.length <= bars || !lastCandle) return null;
		const prev = candles[candles.length - 1 - bars].c;
		return prev ? (lastCandle.c / prev - 1) * 100 : null;
	};
	const dispRet1m = $derived(candleRet(22) ?? p.ret1m);
	const dispRet3m = $derived(candleRet(66) ?? p.ret3m);
	const dispRet1y = $derived(candleRet(252) ?? p.ret1y);
	const dispAsOf = $derived(lastCandle ? `${lastCandle.t.slice(0, 4)}-${lastCandle.t.slice(4, 6)}-${lastCandle.t.slice(6, 8)}` : p.asOf);
	const dispMktcap = $derived(lastCandle && p.last && p.mktcapRaw != null ? fmtKRW(p.mktcapRaw * (lastCandle.c / p.last)) : p.mktcap);
	const stats = $derived([
		{ l: '1M', v: dispRet1m == null ? '—' : sign(dispRet1m, 1) + '%', t: chgClass(dispRet1m) },
		{ l: '3M', v: dispRet3m == null ? '—' : sign(dispRet3m, 1) + '%', t: chgClass(dispRet3m) },
		{ l: '1Y', v: dispRet1y == null ? '—' : sign(dispRet1y, 0) + '%', t: chgClass(dispRet1y) },
		{ l: lang === 'en' ? 'MKT CAP' : '시가총액', v: dispMktcap, t: '' },
		{ l: lang === 'en' ? 'M.SHARE' : '점유율', v: e.marketShare != null ? e.marketShare.toFixed(1) + '%' : '—', t: '' },
		{ l: lang === 'en' ? 'RANK' : '산업순위', v: e.industryRank != null ? e.industryRank + '/' + (e.industryPeerCount || '—') : '—', t: '' }
	]);
	const meta = $derived([
		{ l: lang === 'en' ? 'M.SHARE' : '점유율', v: e.marketShare != null ? e.marketShare.toFixed(1) + '%' : '—' },
		{ l: lang === 'en' ? 'IND.RANK' : '산업순위', v: e.industryRank != null ? e.industryRank + '위/' + (e.industryPeerCount || '—') : '—' },
		{ l: lang === 'en' ? 'OWNER' : '대주주', v: e.holderPct != null ? e.holderPct.toFixed(1) + '%' : '—' },
		{ l: lang === 'en' ? 'EMP' : '임직원', v: e.empCount != null ? e.empCount.toLocaleString() + (lang === 'en' ? '' : '명') : '—' },
		{ l: 'ROE', v: e.roe != null ? e.roe.toFixed(1) + '%' : '—' },
		{ l: lang === 'en' ? 'OP MGN' : '영업이익률', v: e.opMargin != null ? e.opMargin.toFixed(1) + '%' : '—' }
	]);
	// ── 하단 분석: 종합 판정 + DuPont ROE 분해 (모두 동기 tier — finance.json 즉시) ──
	const fz = $derived(co.financials);
	const dp = $derived(fz.dupont); // {netMargin, assetTurn, equityMult, roe}
	const vd = $derived(co.verdict);
	const dpTone = $derived(dp.roe == null ? 'tNeu' : dp.roe >= 12 ? 'tUp' : dp.roe >= 6 ? 'tNeu' : 'tDn');
	const roeDriver = $derived.by<{ kr: string; en: string; tone: Tone } | null>(() => {
		const { netMargin, assetTurn, equityMult } = dp;
		if (netMargin == null || assetTurn == null || equityMult == null) return null;
		if (equityMult >= 2.5 && netMargin < 8) return { kr: '레버리지형', en: 'leverage-led', tone: 'warn' };
		if (netMargin >= 10) return { kr: '마진형', en: 'margin-led', tone: 'good' };
		if (assetTurn >= 1) return { kr: '회전형', en: 'turnover-led', tone: 'up' };
		return { kr: '균형형', en: 'balanced', tone: 'neutral' };
	});
	const dupontFactors = $derived([
		{ k: 'nm', label: lang === 'en' ? 'Net mgn' : '순이익률', disp: dp.netMargin != null ? dp.netMargin.toFixed(1) + '%' : '—', arr: fz.netMargin, col: '#34d399', op: '×' },
		{ k: 'at', label: lang === 'en' ? 'Asset turn' : '자산회전', disp: dp.assetTurn != null ? dp.assetTurn.toFixed(2) + '회' : '—', arr: fz.assetTurn, col: '#60a5fa', op: '×' },
		{ k: 'em', label: lang === 'en' ? 'Leverage' : '레버리지', disp: dp.equityMult != null ? dp.equityMult.toFixed(2) + '배' : '—', arr: fz.equityMult, col: (dp.equityMult ?? 0) >= 2.5 ? '#f0616f' : (dp.equityMult ?? 0) >= 2 ? '#fbbf24' : '#a78bfa', op: '=' },
		{ k: 'roe', label: 'ROE', disp: dp.roe != null ? dp.roe.toFixed(1) + '%' : '—', arr: fz.roe, col: '#34d399', op: '' }
	]);
	// 업종 백분위 중앙값 → 상위 N%
	const pctTop = $derived.by<number | null>(() => {
		const ms = co.percentile?.metrics ?? [];
		const ps = ms.map((m) => m.p).filter((x): x is number => x != null).sort((a, b) => a - b);
		if (!ps.length) return null;
		return 100 - ps[Math.floor(ps.length / 2)] + 1;
	});
	// 미니 스파크라인 path
	function spark(arr: Num[], w = 46, h = 13): string {
		const vals = arr.filter((x): x is number => x != null);
		if (vals.length < 2) return '';
		const lo = Math.min(...vals), hi = Math.max(...vals), rng = hi - lo || 1, n = arr.length;
		let d = '', pen = false;
		arr.forEach((val, i) => {
			if (val == null) { pen = false; return; }
			const x = n <= 1 ? w / 2 : (i / (n - 1)) * w;
			const y = h - ((val - lo) / rng) * h;
			d += `${pen ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)} `;
			pen = true;
		});
		return d.trim();
	}
	// 증자·감자 마커 — capitalChange 이벤트 (수정주가 자동 보정의 교차 검증 라벨).
	// 전환·행사(스톡옵션 등 수천 건)는 제외, 동일자 합산, |수량| 상위 40 상한 — 마커 폭주 방지.
	let capEvents = $state<{ date: string; label: string }[]>([]);
	$effect(() => {
		const code = co.code;
		let cancelled = false;
		capEvents = [];
		rt.report.capitalChanges(code).then((b) => {
			if (cancelled || !b) return;
			const byDate = new Map<string, { kind: string; qty: number }>();
			for (const ev of b.events) {
				if (ev.kind === 'conversion') continue;
				const d = ev.date.replace(/\D/g, '').slice(0, 8);
				if (d.length !== 8) continue;
				const key = `${d}|${ev.kind}`;
				const cur = byDate.get(key);
				if (cur) cur.qty += ev.qty;
				else byDate.set(key, { kind: ev.kind, qty: ev.qty });
			}
			const fmtQty = (q: number) => (Math.abs(q) >= 1e4 ? Math.round(Math.abs(q) / 1e4).toLocaleString() + '만주' : Math.abs(q).toLocaleString() + '주');
			capEvents = [...byDate.entries()]
				.sort((a, b2) => Math.abs(b2[1].qty) - Math.abs(a[1].qty))
				.slice(0, 40)
				.map(([key, v]) => ({ date: key.slice(0, 8), label: `${v.kind === 'paidIn' ? '유상증자' : '감자·소각'} ${fmtQty(v.qty)}` }));
		});
		return () => {
			cancelled = true;
		};
	});

	// 공시 이벤트 레일 (dartlab 고유 강점) — 정기보고서 url(접수일별) + 비정기 material 공시(날짜 그룹·클릭 시 DART).
	// 가격차트 마커가 곧 네비게이션 가능한 공시 타임라인. 같은 날 다수 공시는 1마커로 묶고 '외 N건' 표기(마커 폭주 방지).
	let regularUrlByDate = $state<Record<string, string>>({});
	let disclosureEvents = $state<{ date: string; label: string; url: string; kind: 'disclosure' }[]>([]);
	$effect(() => {
		const code = co.code;
		let cancelled = false;
		regularUrlByDate = {};
		disclosureEvents = [];
		void Promise.all([rt.filing.regular(code), rt.filing.nonRegular(code, 200)]).then(([reg, non]) => {
			if (cancelled) return;
			const rmap: Record<string, string> = {};
			for (const f of reg ?? []) if (f.rceptDate && f.url) rmap[f.rceptDate.replace(/\D/g, '').slice(0, 8)] = f.url;
			regularUrlByDate = rmap;
			const byDate = new Map<string, { labels: string[]; url: string }>();
			for (const f of non ?? []) {
				const d = (f.rceptDate ?? '').replace(/\D/g, '').slice(0, 8);
				if (d.length !== 8 || !f.url || !f.reportNm?.trim()) continue; // 빈 라벨 마커 방지(anti-clutter)
				const cur = byDate.get(d);
				if (cur) cur.labels.push(f.reportNm);
				else byDate.set(d, { labels: [f.reportNm], url: f.url });
			}
			// 최근 60개 날짜로 캡 — wide window 에서도 마커 폭주 방지(anti-clutter). 같은 날 다수는 이미 1마커로 묶임.
			disclosureEvents = [...byDate.entries()]
				.sort((a, b) => (a[0] < b[0] ? 1 : -1))
				.slice(0, 60)
				.map(([d, v]) => ({
					date: d,
					label: v.labels.length > 1 ? `${v.labels[0]} 외 ${v.labels.length - 1}건` : v.labels[0],
					url: v.url,
					kind: 'disclosure' as const
				}));
		});
		return () => {
			cancelled = true;
		};
	});

	// 주가차트 재무 오버레이: 실적 발표 마커(보고서 접수일·클릭 시 DART) + 증자·감자 + 비정기 공시 레일 + 적정주가 밴드
	const priceEvents = $derived.by(() => {
		const src = finBundle?.views.quarter ?? finBundle?.views.ttm ?? finBundle?.views.annual;
		const filed = finBundle?.filedDates ?? {};
		type Ev = { date: string; label: string; url?: string; kind?: 'report' | 'capital' | 'disclosure' };
		const out: Ev[] = [];
		if (src) {
			const QEND: Record<string, string> = { '1': '0331', '2': '0630', '3': '0930', '4': '1231' };
			const urlFor = (d: string) => regularUrlByDate[d.replace(/\D/g, '').slice(0, 8)];
			for (const p of src.periods) {
				const mq = p.match(/^(\d{2})Q(\d)$/);
				if (mq) {
					const d = filed[`20${mq[1]}-${mq[2]}`] ?? '20' + mq[1] + QEND[mq[2]];
					out.push({ date: d, label: p, url: urlFor(d), kind: 'report' });
					continue;
				}
				const fy = p.match(/^FY(\d{2})$/);
				if (fy) {
					const d = filed[`20${fy[1]}-4`] ?? '20' + fy[1] + '1231';
					out.push({ date: d, label: p, url: urlFor(d), kind: 'report' });
				}
			}
		}
		const caps: Ev[] = capEvents.map((e) => ({ ...e, kind: 'capital' as const }));
		return [...out, ...caps, ...disclosureEvents];
	});
	const v = $derived(co.valuation);
	const priceValBand = $derived(
		v && v.fairLow != null && v.fairHigh != null && v.fairMid != null
			? { lo: v.fairLow, mid: v.fairMid, hi: v.fairHigh }
			: null
	);
	const valBand = $derived(
		v && v.fairMid != null
			? (() => {
					const lo = Math.min(v.fairLow || v.last, v.last) * 0.9;
					const hi = Math.max(v.fairHigh || v.last, v.last) * 1.1;
					const pos = (x: number) => Math.max(0, Math.min(100, ((x - lo) / (hi - lo)) * 100));
					return { lo, hi, pos };
				})()
			: null
	);
</script>

<!-- 경제·시장 KPI 티커 (종목/주가 라인 위, 좌우 흐름) -->
{#if kpis.length}
	<div class="kpiTicker"><div class="kpiTrack">
		{#each kpis.concat(kpis) as k, i (i)}
			<span class="kpiItem"><i>{k.l}</i>{#if k.s && k.s.length > 1}<svg class={'kpiSpark ' + k.t} viewBox="0 0 34 11" preserveAspectRatio="none" aria-hidden="true"><polyline points={kpiSpark(k.s)} fill="none" stroke="currentColor" stroke-width="1.1" /></svg>{/if}<b class={k.t}>{k.v}</b></span>
		{/each}
	</div></div>
{/if}

<!-- SYMBOL HEADER -->
<div class="symHead">
	<div>
		<div class="symTop">
			<span class="symCode">{co.code}</span>
			<span class="symBadge kr">{co.marketLabel}</span>
			<span class="symName">{co.name.kr}</span>
		</div>
		<div class="symMeta">{tx(co.sector, lang)}{co.stage ? ' · ' + co.stage : ''}{co.role ? ' · ' + co.role : ''} · DART</div>
		{#if localViewerHref}
			<!-- ui/web 임베드 한정 — 로컬 어댑터가 있을 때만 /analysis 터미널 링크 노출 -->
			<nav class="symLinks"><a href={localTerminalHref}>{lang === 'en' ? 'terminal' : '터미널'}</a></nav>
		{/if}
	</div>
	{#if product || corpInfo}
		<div class="symProd" title={product}>
			{#if corpInfo}
				<div class="symInfoRow">
					{#if corpInfo.ceo}<span class="sif"><i>{lang === 'en' ? 'CEO' : '대표'}</i><b>{corpInfo.ceo}</b></span>{/if}
					{#if corpInfo.fiscalMonth}<span class="sif"><i>{lang === 'en' ? 'FY END' : '결산'}</i><b>{corpInfo.fiscalMonth}</b></span>{/if}
					{#if corpInfo.listedDate}<span class="sif"><i>{lang === 'en' ? 'LISTED' : '상장'}</i><b class="mono">{corpInfo.listedDate}</b></span>{/if}
					{#if corpInfo.region}<span class="sif"><i>{lang === 'en' ? 'HQ' : '본사'}</i><b>{corpInfo.region}</b></span>{/if}
					{#if corpInfo.homepage}<a class="sifLink" href={corpInfo.homepage} target="_blank" rel="noopener">{lang === 'en' ? 'website ↗' : '홈페이지 ↗'}</a>{/if}
				</div>
			{/if}
			<span class="symProdLbl">{lang === 'en' ? 'PRODUCTS' : '주요제품'}</span>
			{#if product}<span class="symProdV">{product}</span>{/if}
		</div>
	{/if}
	<div class="symPrice">
		<span class="symLast mono">{fmtNum(dispLast)}</span>
		<span class={'symChg ' + chgClass(dispRet1m)}>{dispRet1m == null ? '' : sign(dispRet1m, 2) + '% · 1M'}</span>
	</div>
	<div class="symStats">
		{#each stats as s (s.l)}<div class="symStat"><span>{s.l}</span><b class={'mono ' + s.t}>{s.v}</b></div>{/each}
	</div>
</div>

<!-- GRADE STRIP -->
<Panel {lang} className="eAnalysis" prov="real" title={{ kr: '스캔 등급', en: 'SCAN GRADES' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }} flush>
	{#snippet right()}<span class="dim">{co.grades.length} {lang === 'en' ? 'axes' : '축'}</span>{/snippet}
	<div class="ecoMeta">{#each meta as m (m.l)}<div class="em"><span>{m.l}</span><b>{m.v}</b></div>{/each}</div>
	<div class="gradeStrip" style={`grid-template-columns:repeat(${co.grades.length || 1},1fr)`}>
		{#each co.grades as g (g.key)}
			<div class="gradeChip" style={`--gc:${g.color}`}>
				<span class="gcLabel">{txc(g, lang)}</span>
				<span class={'gcVal ' + tcls(g.tone)}>{g.v}</span>
			</div>
		{/each}
	</div>
</Panel>

<!-- 주가 캔들(일별 실데이터·멀티 보조지표) — 메인 히어로. 재무는 아래 전용 섹션. -->
<Panel {lang} className="eQuant" prov="real" title={{ kr: '주가 차트', en: 'PRICE CHART' }} sub={{ kr: '공공데이터 일별 · EOD', en: 'gov daily · EOD' }} flush>
	{#snippet right()}<span class="eodBadge" title={lang === 'en' ? 'end-of-day daily data' : '일별 종가 기준(EOD)'}>EOD · {dispAsOf}</span>{/snippet}
	{#if candles && chartCode}
		<!-- 소프트 스왑: 전환 중에도 직전 캔들로 마운트 유지 (code·name 은 candles 와 원자 갱신) -->
		<PriceChart {candles} code={chartCode} name={chartName} {lang} events={priceEvents} valBand={priceValBand} peers={chartPeers} {suggest} {onPick} />
	{:else if candleState === 'loading'}
		<div class="chartLoad">{lang === 'en' ? 'loading daily prices …' : '일별 시세 불러오는 중 …'}</div>
	{:else}
		<div class="chartLoad">{lang === 'en' ? 'daily chart unavailable here — snapshot only.' : '이 기기에서 일별 차트 불가 — 스냅샷만.'} 52W {fmtNum(co.price.lo52)}~{fmtNum(co.price.hi52)}</div>
	{/if}
</Panel>

<!-- 재무제표 분석 — dart/finance parquet 분기 TTM, 밀집 small-multiples.
     ui/web analysis.financial 의 핵심 카드 체계를 한 화면에 빽빽하게. -->
<Panel {lang} className="eAnalysis" prov="real" title={{ kr: '재무제표 분석', en: 'FINANCIALS' }}
	sub={finData ? { kr: finModeLabel[finMode] + ' · ' + finData.periods.length + '기 · 조 KRW', en: finMode + ' · ' + finData.periods.length + 'p' } : { kr: 'dart/finance', en: 'dart/finance' }} flush>
	{#snippet right()}
		{#if finBundle && finBundle.modes.length > 1}
			<span class="segGroup mini">{#each finBundle.modes as m (m)}<button class={finMode === m ? 'seg on' : 'seg'} onclick={() => (finMode = m)}>{lang === 'en' ? m.toUpperCase() : finModeLabel[m]}</button>{/each}</span>
		{/if}
		<button class="finFullBtn" onclick={() => (finFull = true)} title={lang === 'en' ? 'fullscreen analysis' : '전체화면 분석'} aria-label="fullscreen">⤢</button>
	{/snippet}
	{#if finState === 'ready' && finData}
		<div class="finGrid">
			{#each finData.cards as card (card.key)}
				<div class="finMini"><MiniFinChart {card} periods={finData.periods} /></div>
			{/each}
		</div>
	{:else if finState === 'loading'}
		<div class="chartLoad" style="height:110px">{lang === 'en' ? 'loading financials …' : '재무제표 불러오는 중 …'}</div>
	{:else}
		<div class="storyEmpty">{lang === 'en' ? 'No quarterly financials for this company.' : '분기 재무 데이터 없음.'}</div>
	{/if}
</Panel>
{#if finFull}
	<FinFullscreen {co} {lang} bundle={finBundle} mode={finMode} onMode={(m) => (finMode = m)} onClose={() => (finFull = false)} />
{/if}

<!-- VERDICT (종합 판정 — co.verdict 합성, 동기 tier 즉시 렌더) -->
<Panel {lang} className="eAnalysis" prov="derived" title={{ kr: '종합 판정', en: 'VERDICT' }} sub={{ kr: 'verdict · 합성', en: 'verdict · synth' }} flush>
	{#snippet right()}<span class="vdRisk">{lang === 'en' ? 'risk' : '위험'} <b class="tDn">{vd.riskRed}</b>·<b class="tWarn">{vd.riskYellow}</b></span>{/snippet}
	<div class="vdTop">
		<span class={'vdBand ' + tcls(vd.band.tone)}>{txc(vd.band, lang)}</span>
		<div class="vdChips">
			<span class="vdChip"><i>{lang === 'en' ? 'credit' : '신용'}</i><b class="tCredit">{co.credit.grade}</b></span>
			<span class="vdChip"><i>ROE</i><b class={dpTone}>{dp.roe != null ? dp.roe.toFixed(1) + '%' : '—'}</b>{#if roeDriver}<em class={tcls(roeDriver.tone)}>{txc(roeDriver, lang)}</em>{/if}</span>
			{#if pctTop != null}<span class="vdChip"><i>{lang === 'en' ? 'sector' : '업종'}</i><b class="tUp">{lang === 'en' ? 'top ' + pctTop + '%' : '상위 ' + pctTop + '%'}</b></span>{/if}
			{#if v && v.upside != null}<span class="vdChip"><i>{lang === 'en' ? 'value' : '밸류'}</i><b class={v.upside > 8 ? 'tUp' : v.upside < -8 ? 'tDn' : 'tNeu'}>{(v.upside >= 0 ? '+' : '') + v.upside.toFixed(0)}% {lang === 'en' ? 'up' : '여력'}</b></span>{/if}
		</div>
	</div>
	<div class="vdSummary">{tx(co.analysis.summary, lang)}</div>
	{#if vd.strengths.length || vd.concerns.length}
		<div class="vdSC">
			{#each vd.strengths.slice(0, 3) as sg (sg.en)}<span class="vdS">▲ {tx(sg, lang)}</span>{/each}
			{#each vd.concerns.slice(0, 3) as cn (cn.en)}<span class="vdC">▼ {tx(cn, lang)}</span>{/each}
		</div>
	{/if}
</Panel>

<div class="rowSplit">
	<!-- DUPONT ROE 분해 -->
	<Panel {lang} className="eValuation" prov="derived" title={{ kr: 'DuPont ROE 분해', en: 'DUPONT ROE' }} sub={{ kr: '순이익률 × 자산회전 × 레버리지', en: 'margin × turn × leverage' }} flush>
		{#snippet right()}<b class={'mono ' + dpTone}>{dp.roe != null ? dp.roe.toFixed(1) + '%' : '—'}</b>{/snippet}
		<div class="dupontRow">
			{#each dupontFactors as fct (fct.k)}
				<div class="dpCell">
					<span class="dpLbl">{fct.label}</span>
					<b class="dpVal mono" style={`color:${fct.col}`}>{fct.disp}</b>
					<svg class="dpSpark" viewBox="0 0 46 13" preserveAspectRatio="none" aria-hidden="true"><path d={spark(fct.arr)} fill="none" stroke={fct.col} stroke-width="1.2" /></svg>
				</div>
				{#if fct.op}<span class="dpOp">{fct.op}</span>{/if}
			{/each}
		</div>
		<div class="dpVerdict">
			{#if !roeDriver}{lang === 'en' ? 'Insufficient data for ROE decomposition.' : 'ROE 분해 데이터 부족.'}
			{:else if roeDriver.tone === 'warn'}{lang === 'en' ? `Leverage-led — equity multiplier ${dp.equityMult?.toFixed(1)}×, margin only ${dp.netMargin?.toFixed(1)}%. Returns lean on debt.` : `차입 의존 ROE — 자본승수 ${dp.equityMult?.toFixed(1)}배, 순이익률 ${dp.netMargin?.toFixed(1)}%. 레버리지가 수익률을 떠받침.`}
			{:else if roeDriver.tone === 'good'}{lang === 'en' ? `Margin-led — net margin ${dp.netMargin?.toFixed(1)}% drives returns. Durable quality.` : `마진형 ROE — 순이익률 ${dp.netMargin?.toFixed(1)}% 가 견인. 질 높은 수익률.`}
			{:else if roeDriver.tone === 'up'}{lang === 'en' ? `Turnover-led — asset turn ${dp.assetTurn?.toFixed(2)}× drives returns.` : `회전형 ROE — 자산회전 ${dp.assetTurn?.toFixed(2)}회 가 견인. 효율 중심.`}
			{:else}{lang === 'en' ? 'Balanced across margin, turnover and leverage.' : '마진·회전·레버리지가 고르게 기여하는 균형형 ROE.'}{/if}
		</div>
	</Panel>
	<!-- VALUATION -->
	{#if v}
		<Panel {lang} className="eValuation" prov="derived" title={{ kr: '밸류에이션 위치', en: 'VALUATION' }} sub={{ kr: '업종 중앙값 대비', en: 'vs peer median' }} flush>
			{#snippet right()}
				{@const cheap = v.upside != null && v.upside > 8}
				{@const rich = v.upside != null && v.upside < -8}
				<span class={cheap ? 'tUp' : rich ? 'tDn' : 'tNeu'}>{v.upside != null ? (v.upside >= 0 ? '+' : '') + v.upside.toFixed(0) + '%' : '—'}</span>
			{/snippet}
			<div class="valTop">
				<div class="valCell"><div class="vl">PER</div><div class={'vv ' + (v.per != null && v.perMed && v.per <= v.perMed ? 'tUp' : 'tDn')}>{v.per != null ? v.per.toFixed(1) + 'x' : '—'}</div><div class="vsub">{lang === 'en' ? 'peer med' : '업종중앙'} {v.perMed != null ? v.perMed.toFixed(1) + 'x' : '—'}</div></div>
				<div class="valCell"><div class="vl">PBR</div><div class={'vv ' + (v.pbr != null && v.pbrMed && v.pbr <= v.pbrMed ? 'tUp' : 'tDn')}>{v.pbr != null ? v.pbr.toFixed(2) + 'x' : '—'}</div><div class="vsub">{lang === 'en' ? 'peer med' : '업종중앙'} {v.pbrMed != null ? v.pbrMed.toFixed(2) + 'x' : '—'}</div></div>
			</div>
			{#if v.fairMid != null && valBand}
				<div class="fairBand">
					<div class="fairTrack">
						<div class="fairRange" style={`left:${valBand.pos(v.fairLow!)}%;width:${valBand.pos(v.fairHigh!) - valBand.pos(v.fairLow!)}%`}></div>
						<div class="fairNow" style={`left:${valBand.pos(v.last)}%`}></div>
					</div>
					<div class="fairLbl"><span>{fmtNum(Math.round(v.fairLow!))}</span><span class="tAmber">{lang === 'en' ? 'now ' : '현재 '}{fmtNum(v.last)}</span><span>{fmtNum(Math.round(v.fairHigh!))}</span></div>
				</div>
			{/if}
			<div class="valVerdict">
				{#if v.upside == null}{lang === 'en' ? 'Fair value n/a.' : '적정가 산출 불가.'}
				{:else if v.upside > 8}{lang === 'en' ? `Below peer multiples — ~+${v.upside.toFixed(0)}% to fair value.` : `업종 중앙값 대비 저평가 — 적정가까지 약 +${v.upside.toFixed(0)}% 여력.`}
				{:else if v.upside < -8}{lang === 'en' ? `Above peer median — ${Math.abs(v.upside).toFixed(0)}% rich.` : `업종 중앙값 대비 고평가 — 약 ${Math.abs(v.upside).toFixed(0)}% 비쌈.`}
				{:else}{lang === 'en' ? 'Roughly in line with peers.' : '업종 평균 수준의 밸류에이션.'}{/if}
			</div>
		</Panel>
	{:else}
		<Panel {lang} className="eValuation" prov="derived" title={{ kr: '밸류에이션', en: 'VALUATION' }} flush><div class="storyEmpty">{lang === 'en' ? 'Insufficient data.' : '데이터 부족.'}</div></Panel>
	{/if}
</div>
