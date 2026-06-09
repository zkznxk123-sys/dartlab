<script lang="ts">
	import { base } from '$app/paths';
	import type { Company, Lang } from '../data/types';
	import Panel from '../ui/Panel.svelte';
	import Radar from '../charts/Radar.svelte';
	import TrendChart from '../charts/TrendChart.svelte';
	import PriceChart from '../charts/PriceChart.svelte';
	import { loadDailyOHLCV, type Candle } from '../data/priceSeries';
	import { tx, txc, chgClass, sign, toneClass, fmtNum } from '../ui/helpers';

	interface Props {
		co: Company;
		lang: Lang;
	}
	let { co, lang }: Props = $props();
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	let freq = $state<'annual' | 'quarter'>('annual');
	const trend = $derived(freq === 'quarter' && co.trendQuarter ? co.trendQuarter : co.trendAnnual);
	$effect(() => {
		// 분기 데이터 없는 회사로 전환 시 annual 로 복귀
		if (freq === 'quarter' && !co.trendQuarter) freq = 'annual';
	});

	// 주가 캔들 (DuckDB 온디맨드) — 부팅 비차단, 회사 전환 시 재로드
	let chartMode = $state<'price' | 'fin'>('price');
	let pPeriod = $state<'3M' | '6M' | '1Y' | 'MAX'>('1Y');
	let pOverlay = $state<'MA' | 'BB' | 'NONE'>('MA');
	let pSub = $state<'VOL' | 'RSI' | 'MACD'>('VOL');
	let candles = $state<Candle[] | null>(null);
	let candleState = $state<'loading' | 'ready' | 'unavail'>('loading');
	const priceYear = $derived(+co.price.asOf.slice(0, 4) || new Date().getFullYear());
	$effect(() => {
		const code = co.code;
		const yr = priceYear;
		candleState = 'loading';
		candles = null;
		let cancelled = false;
		loadDailyOHLCV(code, yr).then((c) => {
			if (cancelled) return;
			candles = c;
			candleState = c && c.length ? 'ready' : 'unavail';
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
	const w52pos = $derived(
		p.hi52 && p.lo52 && p.hi52 > p.lo52 ? Math.max(0, Math.min(1, (p.last - p.lo52) / (p.hi52 - p.lo52))) : 0.5
	);
	const retCells = $derived([
		{ l: '1M', v: p.ret1m, neu: false }, { l: '3M', v: p.ret3m, neu: false },
		{ l: '1Y', v: p.ret1y, neu: false }, { l: 'σ 1Y', v: p.vol1y, neu: true }
	]);
	const f = $derived(co.fundamentals);
	const fundCells = $derived([
		{ l: 'PER', v: f.per != null ? f.per.toFixed(1) + 'x' : '—' },
		{ l: 'PBR', v: f.pbr != null ? f.pbr.toFixed(2) + 'x' : '—' },
		{ l: 'PSR', v: f.psr != null ? f.psr.toFixed(2) + 'x' : '—' },
		{ l: 'ROE', v: f.roe != null ? f.roe.toFixed(1) + '%' : '—' },
		{ l: lang === 'en' ? 'NET MGN' : '순이익률', v: f.npm != null ? f.npm.toFixed(1) + '%' : '—' },
		{ l: lang === 'en' ? 'DEBT R' : '부채비율', v: f.dr != null ? f.dr.toFixed(0) + '%' : '—' }
	]);
	const v = $derived(co.valuation);
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
	const ver = $derived(co.verdict);
	const tw = $derived(co.tailwind);
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

<!-- VERDICT -->
<Panel {lang} className="eAnalysis" prov="derived" title={{ kr: '투자 종합 판단', en: 'VERDICT' }} sub={{ kr: 'grades+value+momentum', en: 'composite' }} flush>
	{#snippet right()}
		{#if tw}<span class={'dim ' + (tw.tone === 'up' ? 'tUp' : tw.tone === 'down' ? 'tDn' : '')}>{tw.kr} {tw.label}</span>{/if}
	{/snippet}
	<div class="verdictWrap">
		<div class="verdictScore">
			<span class={'vsNum ' + tcls(ver.band.tone)}>{ver.composite}</span>
			<span class={'vsBand ' + tcls(ver.band.tone)}>{lang === 'en' ? ver.band.en : ver.band.kr}</span>
			<span class="vsLabel">{lang === 'en' ? 'dartlab score' : '종합점수'}</span>
		</div>
		<div class="verdictBody">
			<div class="vRow s"><span class="vk">{lang === 'en' ? 'STRENGTH' : '강점'}</span>
				<span class="vList">{#if ver.strengths.length}{#each ver.strengths as s, i (i)}<span>· {txc(s, lang)}</span>{/each}{:else}<span class="dim">—</span>{/if}</span></div>
			<div class="vRow c"><span class="vk">{lang === 'en' ? 'CONCERN' : '우려'}</span>
				<span class="vList">{#if ver.concerns.length}{#each ver.concerns as s, i (i)}<span>· {txc(s, lang)}</span>{/each}{:else}<span class="dim">{lang === 'en' ? 'none flagged' : '특이사항 없음'}</span>{/if}</span></div>
		</div>
	</div>
	<div class="vRiskline">
		<span>{lang === 'en' ? 'Red flags' : '위험 신호'} <b class="tDn">{ver.riskRed}</b></span>
		<span>{lang === 'en' ? 'Watch' : '주의'} <b class="tWarn">{ver.riskYellow}</b></span>
		{#if tw}<span>{lang === 'en' ? 'Sector' : '섹터'} <b class={tw.tone === 'up' ? 'tUp' : tw.tone === 'down' ? 'tDn' : 'tNeu'}>{tw.label}</b></span>{/if}
		<span class="dim" style="margin-left:auto;">{lang === 'en' ? 'diagnosis, not advice' : '진단 — 투자권유 아님'}</span>
	</div>
</Panel>

<!-- 주가 캔들(일별 실데이터·보조지표) ⇄ 재무 추세 -->
<Panel {lang} className="eQuant" prov="live" title={{ kr: '주가 · 재무', en: 'PRICE · FINANCIALS' }}
	sub={chartMode === 'price' ? { kr: 'krx 일별 · EOD', en: 'krx daily · EOD' } : { kr: 'finance · 실데이터', en: 'finance · real' }} flush>
	{#snippet right()}
		<span class="segGroup">
			<button class={chartMode === 'price' ? 'seg on' : 'seg'} onclick={() => (chartMode = 'price')}>{lang === 'en' ? 'PRICE' : '주가'}</button>
			<button class={chartMode === 'fin' ? 'seg on' : 'seg'} onclick={() => (chartMode = 'fin')}>{lang === 'en' ? 'FIN' : '재무'}</button>
		</span>
	{/snippet}
	{#if chartMode === 'price'}
		<div class="chartCtlRow">
			<span class="segGroup">{#each ['3M', '6M', '1Y', 'MAX'] as p (p)}<button class={pPeriod === p ? 'seg on' : 'seg'} onclick={() => (pPeriod = p as typeof pPeriod)}>{p}</button>{/each}</span>
			<span class="segGroup">{#each [['MA', 'MA'], ['BB', 'BB'], ['NONE', '없음']] as [v, l] (v)}<button class={pOverlay === v ? 'seg on' : 'seg'} onclick={() => (pOverlay = v as typeof pOverlay)}>{l}</button>{/each}</span>
			<span class="segGroup">{#each ['VOL', 'RSI', 'MACD'] as v (v)}<button class={pSub === v ? 'seg on' : 'seg'} onclick={() => (pSub = v as typeof pSub)}>{v}</button>{/each}</span>
			<span class="eodBadge" title="키 발급 전 — 전일 종가까지(EOD)">EOD · {co.price.asOf}</span>
		</div>
		{#if candleState === 'ready' && candles}
			<PriceChart {candles} {lang} period={pPeriod} overlay={pOverlay} sub={pSub} />
		{:else if candleState === 'loading'}
			<div class="chartLoad">{lang === 'en' ? 'loading daily prices …' : '일별 시세 불러오는 중 …'}</div>
		{:else}
			<div class="chartLoad">{lang === 'en' ? 'daily chart unavailable here — snapshot only.' : '이 기기에서 일별 차트 불가 — 스냅샷만.'} 52W {fmtNum(co.price.lo52)}~{fmtNum(co.price.hi52)}</div>
		{/if}
	{:else}
		<div class="chartCtlRow">
			<span class="segGroup">
				<button class={freq === 'annual' ? 'seg on' : 'seg'} onclick={() => (freq = 'annual')}>{lang === 'en' ? 'ANNUAL' : '연간'}</button>
				<button class={freq === 'quarter' ? 'seg on' : 'seg'} disabled={!co.trendQuarter} style={!co.trendQuarter ? 'opacity:.4;cursor:not-allowed' : ''} onclick={() => co.trendQuarter && (freq = 'quarter')}>{lang === 'en' ? 'QUARTER' : '분기'}</button>
			</span>
			<span class="dim" style="font-size:8.5px">{lang === 'en' ? 'revenue · op · margin' : '매출·영업이익·이익률'}</span>
		</div>
		<TrendChart {trend} {lang} />
	{/if}
</Panel>

<div class="rowSplit">
	<!-- RADAR -->
	<Panel {lang} className="eIndustry" prov="live" title={{ kr: '종합 스노우플레이크', en: 'SNOWFLAKE' }} sub={{ kr: '6축 등급', en: '6-axis' }} flush>
		<div class="radarWrap">
			<Radar data={co.radar} {lang} size={104} />
			<div class="radarLegend">
				{#each co.radar as d (d.en)}
					<div class="rl"><span>{txc(d, lang)}</span><b class={d.s == null ? 'tNeu' : d.s >= 0.66 ? 'tUp' : d.s >= 0.4 ? 'tNeu' : 'tDn'}>{d.s == null ? '—' : Math.round(d.s * 100)}</b></div>
				{/each}
			</div>
		</div>
	</Panel>
	<!-- RETURNS / RISK -->
	<Panel {lang} className="eQuant" prov="live" title={{ kr: '수익률 · 리스크', en: 'RETURNS · RISK' }} sub={{ kr: 'prices-snapshot', en: 'prices-snapshot' }} flush>
		<div class="retGrid">{#each retCells as c (c.l)}<div class="retCell"><span>{c.l}</span><b class={c.neu ? 'tNeu' : chgClass(c.v)}>{c.v == null ? '—' : sign(c.v, 1) + '%'}</b></div>{/each}</div>
		<div class="w52">
			<div class="w52Lbl"><span>{lang === 'en' ? '52W LOW' : '52주 최저'}</span><span>{lang === 'en' ? '52W HIGH' : '52주 최고'}</span></div>
			<div class="w52Track"><div class="w52Fill" style={`width:${w52pos * 100}%`}></div><div class="w52Dot" style={`left:${w52pos * 100}%`}></div></div>
			<div class="w52Lbl"><span class="mono">{fmtNum(p.lo52)}</span><span class="dim mono">{fmtNum(p.last)}</span><span class="mono">{fmtNum(p.hi52)}</span></div>
		</div>
		<div class="finNote">price as of {p.asOf} · KRX</div>
	</Panel>
</div>

<div class="rowSplit">
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
	<!-- FUNDAMENTALS -->
	<Panel {lang} className="eValuation" prov="derived" title={{ kr: '가치 · 펀더멘털', en: 'VALUATION' }} sub={{ kr: 'finance · derived', en: 'derived' }} flush>
		<div class="fundGrid">{#each fundCells as c (c.l)}<div class="fundCell"><span class="fundL">{c.l}</span><span class="fundV mono">{c.v}</span></div>{/each}</div>
	</Panel>
</div>

<!-- ANALYSIS -->
<Panel {lang} className="eAnalysis" prov="derived" title={{ kr: '재무 분석', en: 'FINANCIAL ANALYSIS' }} sub={{ kr: 'c.analysis', en: 'c.analysis' }} flush>
	<div class="anSummary">{tx(co.analysis.summary, lang)}</div>
	<div class="anTracks">
		{#each co.analysis.tracks as t (t.en)}
			<div class="anRow"><span class="anName">{txc(t, lang)}</span><span class={'anDelta mono ' + toneClass(t.tone)}>{t.delta}</span><span class="anVerdict">{tx(t.verdict, lang)}</span></div>
		{/each}
	</div>
</Panel>
