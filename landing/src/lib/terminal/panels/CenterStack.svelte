<script lang="ts">
	import { base } from '$app/paths';
	import type { Company, Lang, Tone, Num } from '../data/types';
	import Panel from '../ui/Panel.svelte';
	import PriceChart from '../charts/PriceChart.svelte';
	import MiniFinChart from '../charts/MiniFinChart.svelte';
	import { loadTerminalFinance, type TerminalFinanceBundle, type FinMode } from '../data/terminalFinance';
	import { loadInitialOHLCV, type Candle } from '../data/priceSeries';
	import { tx, txc, chgClass, sign, fmtNum } from '../ui/helpers';

	interface Props {
		co: Company;
		lang: Lang;
	}
	let { co, lang }: Props = $props();
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	// 주가 캔들 (hyparquet 온디맨드) — 부팅 비차단, 회사 전환 시 재로드. 재무는 아래 별도 섹션.
	// 주가차트 컨트롤(기간·지표·드로잉·실적·밸류·로그·전체화면)은 PriceChart 인-차트 툴바로 이전.
	let candles = $state<Candle[] | null>(null);
	let candleState = $state<'loading' | 'ready' | 'unavail'>('loading');
	const priceYear = $derived(+co.price.asOf.slice(0, 4) || new Date().getFullYear());
	$effect(() => {
		const code = co.code;
		const yr = priceYear;
		candleState = 'loading';
		candles = null;
		let cancelled = false;
		loadInitialOHLCV(code, yr).then((r) => {
			if (cancelled) return;
			candles = r ? r.candles : null;
			candleState = r && r.candles.length ? 'ready' : 'unavail';
		});
		return () => {
			cancelled = true;
		};
	});

	// 재무 카드 — dart/finance/{code}.parquet (HF hyparquet) 연간/분기/TTM, 온디맨드·회사별
	let finBundle = $state<TerminalFinanceBundle | null>(null);
	let finMode = $state<FinMode>('ttm');
	let finState = $state<'loading' | 'ready' | 'empty'>('loading');
	const finData = $derived(finBundle ? finBundle.views[finMode] ?? null : null);
	const finModeLabel: Record<FinMode, string> = { ttm: '분기 TTM', quarter: '분기', annual: '연간' };
	$effect(() => {
		const code = co.code;
		finState = 'loading';
		finBundle = null;
		let cancelled = false;
		loadTerminalFinance(code).then((b) => {
			if (cancelled) return;
			finBundle = b;
			finMode = b ? b.defaultMode : 'ttm';
			finState = b && b.modes.length ? 'ready' : 'empty';
		});
		return () => {
			cancelled = true;
		};
	});

	const p = $derived(co.price);
	const e = $derived(co.eco);
	const stats = $derived([
		{ l: '1M', v: p.ret1m == null ? '—' : sign(p.ret1m, 1) + '%', t: chgClass(p.ret1m) },
		{ l: '3M', v: p.ret3m == null ? '—' : sign(p.ret3m, 1) + '%', t: chgClass(p.ret3m) },
		{ l: '1Y', v: p.ret1y == null ? '—' : sign(p.ret1y, 0) + '%', t: chgClass(p.ret1y) },
		{ l: lang === 'en' ? 'MKT CAP' : '시가총액', v: p.mktcap, t: '' },
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
	// 주가차트 재무 오버레이: 실적 시점(분기말) 마커 + 적정주가 밴드
	const priceEvents = $derived.by(() => {
		const src = finBundle?.views.quarter ?? finBundle?.views.ttm ?? finBundle?.views.annual;
		const out: { date: string; label: string }[] = [];
		if (!src) return out;
		const QEND: Record<string, string> = { '1': '0331', '2': '0630', '3': '0930', '4': '1231' };
		for (const p of src.periods) {
			const mq = p.match(/^(\d{2})Q(\d)$/);
			if (mq) { out.push({ date: '20' + mq[1] + QEND[mq[2]], label: p }); continue; }
			const fy = p.match(/^FY(\d{2})$/);
			if (fy) out.push({ date: '20' + fy[1] + '1231', label: p });
		}
		return out;
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

<!-- SYMBOL HEADER -->
<div class="symHead">
	<div>
		<div class="symTop">
			<span class="symCode">{co.code}</span>
			<span class="symBadge kr">{co.marketLabel}</span>
			<span class="symName">{co.name.kr}</span>
		</div>
		<div class="symMeta">{tx(co.sector, lang)}{co.stage ? ' · ' + co.stage : ''}{co.role ? ' · ' + co.role : ''} · DART</div>
		<nav class="symLinks">
			<a href="{base}/viewer/company/{co.code}" target="_blank" rel="noopener">{lang === 'en' ? 'viewer ↗' : '공시뷰어 ↗'}</a>
			<a href="{base}/lab/dashboard/{co.code}" target="_blank" rel="noopener">{lang === 'en' ? 'dashboard ↗' : '대시보드 ↗'}</a>
			<a href="{base}/company/{co.code}" target="_blank" rel="noopener">{lang === 'en' ? 'company ↗' : '회사 ↗'}</a>
		</nav>
	</div>
	<div class="symPrice">
		<span class="symLast mono">{fmtNum(p.last)}</span>
		<span class={'symChg ' + chgClass(p.ret1m)}>{p.ret1m == null ? '' : sign(p.ret1m, 2) + '% · 1M'}</span>
	</div>
	<div class="symStats">
		{#each stats as s (s.l)}<div class="symStat"><span>{s.l}</span><b class={'mono ' + s.t}>{s.v}</b></div>{/each}
	</div>
</div>

<!-- GRADE STRIP -->
<Panel {lang} className="eAnalysis" prov="live" title={{ kr: '스캔 등급', en: 'SCAN GRADES' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }} flush>
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
<Panel {lang} className="eQuant" prov="live" title={{ kr: '주가 차트', en: 'PRICE CHART' }} sub={{ kr: 'krx 일별 · EOD', en: 'krx daily · EOD' }} flush>
	{#snippet right()}<span class="eodBadge" title="키 발급 전 — 전일 종가까지(EOD)">EOD · {co.price.asOf}</span>{/snippet}
	{#if candleState === 'ready' && candles}
		<PriceChart {candles} code={co.code} {lang} events={priceEvents} valBand={priceValBand} />
	{:else if candleState === 'loading'}
		<div class="chartLoad">{lang === 'en' ? 'loading daily prices …' : '일별 시세 불러오는 중 …'}</div>
	{:else}
		<div class="chartLoad">{lang === 'en' ? 'daily chart unavailable here — snapshot only.' : '이 기기에서 일별 차트 불가 — 스냅샷만.'} 52W {fmtNum(co.price.lo52)}~{fmtNum(co.price.hi52)}</div>
	{/if}
</Panel>

<!-- 재무제표 분석 — dart/finance parquet 분기 TTM, 밀집 small-multiples.
     ui/web analysis.financial 의 핵심 카드 체계를 한 화면에 빽빽하게. -->
<Panel {lang} className="eAnalysis" prov="live" title={{ kr: '재무제표 분석', en: 'FINANCIALS' }}
	sub={finData ? { kr: finModeLabel[finMode] + ' · ' + finData.periods.length + '기 · 조 KRW', en: finMode + ' · ' + finData.periods.length + 'p' } : { kr: 'dart/finance', en: 'dart/finance' }} flush>
	{#snippet right()}
		{#if finBundle && finBundle.modes.length > 1}
			<span class="segGroup mini">{#each finBundle.modes as m (m)}<button class={finMode === m ? 'seg on' : 'seg'} onclick={() => (finMode = m)}>{lang === 'en' ? m.toUpperCase() : finModeLabel[m]}</button>{/each}</span>
		{/if}
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

