<script lang="ts">
	import { base } from '$app/paths';
	import Section from '$lib/components/ui/Section.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import Eyebrow from '$lib/components/ui/Eyebrow.svelte';
	import MonoNumber from '$lib/components/ui/MonoNumber.svelte';
	import Tag from '$lib/components/ui/Tag.svelte';
	import Sparkline from '$lib/components/ui/Sparkline.svelte';
	import Bar from '$lib/components/ui/Bar.svelte';
	import Tooltip from '$lib/components/ui/Tooltip.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Sankey from '$lib/components/ui/Sankey.svelte';
	import { fmtKrwFromEok, fmtPrice } from '$lib/format/krw';
	import { fmtPct, fmtMul } from '$lib/format/pct';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// ── ecosystem 노드 ── (revenue, roe, opMargin, debtRatio, revCagr 등 보유)
	const node = $derived(
		data.ecosystem?.nodes?.find((n: any) => n.id === data.stockCode) ?? null
	);

	// ── 회사 finance ──
	const fin = $derived((data.finance as any)?.companies?.[data.stockCode] ?? null);
	const years: string[] = $derived((data.finance as any)?.years ?? []);

	// ── grade 매핑 (ecosystem grade → 1~5 점수) ──
	const GRADE: Record<string, number> = {
		A: 5, B: 4, C: 3, D: 2, E: 1, F: 1,
		'우수': 5, '양호': 4, '보통': 3, '저수익': 2, '적자': 1,
		'고성장': 5, '성장': 4, '정체': 3, '급감': 2, '역성장': 1,
		'안전': 5, '관찰': 3, '주의': 2, '고위험': 1,
		'위험': 1, '안정': 5, '경고': 2, '취약': 1
	};
	const gradeScore = (g?: string | null) => (g ? (GRADE[g] ?? 3) : 3);

	const grades = $derived({
		profit: node?.profGrade,
		growth: node?.growthGrade,
		stable: node?.debtGrade,
		quality: node?.qualGrade,
		gov: node?.govGrade
	});
	const radarAvg = $derived.by(() => {
		const vals = Object.values(grades).map((g) => (g ? gradeScore(g) : null)).filter((v): v is number => v != null);
		if (vals.length === 0) return null;
		return vals.reduce((s, v) => s + v, 0) / vals.length;
	});

	// ── verdict (grade 평균 기반, AI 없이) ──
	const verdict = $derived.by(() => {
		if (radarAvg == null) return null;
		if (radarAvg >= 4) return { call: 'BUY', word: '매수 후보', tone: 'good' as const };
		if (radarAvg <= 2) return { call: 'SELL', word: '매도 검토', tone: 'bad' as const };
		return { call: 'HOLD', word: '보유', tone: 'warn' as const };
	});

	// ── KPI 4개 ──
	const kpis = $derived([
		{ key: 'roe', label: 'ROE', tip: '자기자본이익률 — 순이익 ÷ 자기자본', value: node?.roe, suffix: '%', tone: toneByPositive(node?.roe, 10) },
		{ key: 'opMargin', label: '영업이익률', tip: '매출 대비 영업이익 비중', value: node?.opMargin, suffix: '%', tone: toneByPositive(node?.opMargin, 8) },
		{ key: 'revCagr', label: '매출 CAGR', tip: '5년간 연복리 매출 성장률', value: node?.revCagr, suffix: '%', tone: toneByPositive(node?.revCagr, 5) },
		{ key: 'debtRatio', label: '부채비율', tip: '총부채 ÷ 자기자본', value: node?.debtRatio, suffix: '%', tone: toneByDebt(node?.debtRatio) }
	]);

	function toneByPositive(v: any, threshold: number): 'good' | 'warn' | 'bad' | 'flat' {
		if (typeof v !== 'number' || !Number.isFinite(v)) return 'flat';
		if (v >= threshold) return 'good';
		if (v >= 0) return 'warn';
		return 'bad';
	}
	function toneByDebt(v: any): 'good' | 'warn' | 'bad' | 'flat' {
		if (typeof v !== 'number' || !Number.isFinite(v)) return 'flat';
		if (v <= 100) return 'good';
		if (v <= 200) return 'warn';
		return 'bad';
	}

	// ── 5 년 시계열 ──
	const past = $derived({
		revenue: fin?.is?.sales ?? [],
		op: fin?.is?.op ?? [],
		roe: fin?.ratios?.roe ?? [],
		debt: fin?.ratios?.debtRatio ?? []
	});

	// ── 분기 시계열 (quarters.json) ──
	const qData = $derived((data.quarters as any)?.companies?.[data.stockCode] ?? null);
	const qPeriods = $derived(((data.quarters as any)?.periods ?? []) as string[]);

	// ── company meta (aiInsight 등) ──
	const cmeta = $derived(data.companyMeta ?? null);

	// ── industry ──
	const industry = $derived(data.industryMeta ?? null);

	// ── KPI 카드용 — 백분위 (industry 기반) ──
	function pctileInIndustry(metric: string): number | null {
		if (!industry?.stages) return null;
		const all: number[] = [];
		for (const stg of industry.stages) {
			for (const n of stg.nodes ?? []) {
				const v = n[metric];
				if (typeof v === 'number' && Number.isFinite(v)) all.push(v);
			}
		}
		if (!all.length || !node) return null;
		const me = node[metric];
		if (typeof me !== 'number') return null;
		const lower = all.filter((v) => v < me).length;
		return Math.round((lower / all.length) * 100);
	}
</script>

<svelte:head>
	<title>{node?.label ?? data.stockCode} · /lab dashboard</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<!-- ── Editorial nav ── -->
<header class="lab-nav">
	<div class="nav-inner">
		<a href="{base}/lab" class="brand">
			<span class="brand-mark">dartlab</span>
			<span class="brand-slash">/</span>
			<span class="brand-ctx">lab · dashboard</span>
		</a>
		<nav class="nav-actions">
			<Button variant="ghost" size="sm" href="{base}/lab">/lab 홈</Button>
			<Button variant="ghost" size="sm" href="{base}/lab/dashboard/005930">005930</Button>
			<Button variant="ghost" size="sm" href="{base}/lab/dashboard/035420">035420</Button>
			<Button variant="ghost" size="sm" href="{base}/lab/dashboard/000660">000660</Button>
		</nav>
	</div>
</header>

{#if !node}
	<div class="empty">
		<Eyebrow text="NO DATA" />
		<h1 class="dl-h1-kr">대시보드 데이터 없음</h1>
		<p class="dl-body">종목코드 <span class="dl-mono">{data.stockCode}</span> 가 ecosystem.json 에 없거나 finance.json prebuild 가 누락됐습니다.</p>
		<Button href="{base}/lab" variant="primary">/lab 홈으로</Button>
	</div>
{:else}
	<!-- ── HERO · Verdict-first ── -->
	<section class="hero">
		<div class="hero-inner">
			<!-- editorial slug -->
			<div class="hero-slug">
				<span class="dl-mono">KOSPI</span>
				<span class="hero-sep"></span>
				<span class="dl-mono">{data.stockCode}</span>
				<span class="hero-sep"></span>
				<span>{node.industryName ?? node.industry ?? '—'}</span>
				<span class="hero-sep"></span>
				<span class="dl-eyebrow" style="text-transform: none; letter-spacing: 0.05em;">분석 시점 2026-04-23</span>
			</div>

			<h1 class="hero-name dl-h1-kr">{node.label}</h1>

			<div class="hero-tags">
				{#if node.stageName}<Tag>{node.stageName}</Tag>{/if}
				{#if node.role}<Tag tone="info">{node.role}</Tag>{/if}
				{#if node.revenue}<Tag tone="neutral">매출 {fmtKrwFromEok(node.revenue)}</Tag>{/if}
			</div>

			<div class="hero-grid">
				<!-- 좌: Verdict (사용자 v3 핵심) -->
				<Card eyebrow="VERDICT · 종합 판정" accent={verdict?.tone === 'good' ? 'good' : verdict?.tone === 'bad' ? 'bad' : 'warn'}>
					{#if verdict && radarAvg != null}
						<div class="verdict">
							<div class="v-call tone-{verdict.tone}">
								{verdict.word}
								<span class="v-call-en">· {verdict.call}</span>
							</div>
							<div class="v-meta">
								<span class="dl-label">5축 평균</span>
								<MonoNumber value={radarAvg.toFixed(1)} suffix="/ 5" size="lg" tone="ink" align="left" />
							</div>
							<p class="v-line">
								{#if verdict.call === 'BUY'}
									업종 평균 대비 5축 모두 양호. 다만 시장 사이클 확인 후 진입.
								{:else if verdict.call === 'SELL'}
									다축에서 약세 신호. 보유 중이면 비중 점검.
								{:else}
									강점·약점 혼재. 다음 분기 실적 발표 대기 구간.
								{/if}
							</p>
						</div>
					{:else}
						<p class="dl-body-sm" style="color: var(--dl-ink-mute)">등급 데이터 부족 — 판정 보류.</p>
					{/if}
				</Card>

				<!-- 우: 5축 grade 분해 -->
				<Card eyebrow="QUALITY · 5축 등급" padded>
					<div class="grades">
						{#each Object.entries(grades) as [key, g]}
							{@const score = g ? gradeScore(g) : 0}
							{@const labelKr = ({ profit: '수익성', growth: '성장', stable: '안정성', quality: '품질', gov: '지배구조' } as any)[key]}
							<div class="grade-row">
								<span class="grade-label">{labelKr}</span>
								<div class="grade-bar"><Bar value={score} max={5} tone={score >= 4 ? 'good' : score >= 3 ? 'warn' : 'bad'} /></div>
								<span class="grade-text dl-mono">{g ?? '—'}</span>
							</div>
						{/each}
					</div>
				</Card>
			</div>
		</div>
	</section>

	<!-- ── 01 KPI · Quality Check ── -->
	<Section number="01" eyebrow="KPI" title="핵심 지표 4축" subtitle="동종 업종 백분위 기준. 한국 컨벤션 (양호 빨강 · 위험 파랑) 은 등락 전용, KPI 는 신호색 (good/warn/bad).">
		<div class="kpi-grid">
			{#each kpis as k}
				{@const ile = pctileInIndustry(k.key)}
				<Card padded>
					<div class="kpi-head">
						<span class="dl-label">{k.label}<Tooltip label={k.tip} /></span>
					</div>
					<div class="kpi-val">
						<MonoNumber
							value={typeof k.value === 'number' ? k.value.toFixed(1) : '—'}
							suffix={k.suffix}
							size="xl"
							tone={k.tone === 'good' ? 'good' : k.tone === 'warn' ? 'warn' : k.tone === 'bad' ? 'bad' : 'flat'}
							align="left"
						/>
					</div>
					{#if ile != null}
						<div class="kpi-pctile">
							<Bar value={ile} max={100} tone={ile >= 70 ? 'good' : ile >= 30 ? 'warn' : 'bad'} />
							<span class="dl-eyebrow">업종 내 {ile}%ile</span>
						</div>
					{/if}
				</Card>
			{/each}
		</div>
	</Section>

	<!-- ── 02 LOOKING BACK · 5년 시계열 ── -->
	<Section number="02" eyebrow="LOOKING BACK" title="지난 5년" subtitle="매출 · 영업이익 · ROE · 부채비율. {years[0] ?? '—'} ~ {years[years.length - 1] ?? '—'}">
		<div class="past-grid">
			{#each [
				{ label: '매출', data: past.revenue, fmt: (v: number) => fmtKrwFromEok(v), tone: 'orange' },
				{ label: '영업이익', data: past.op, fmt: (v: number) => fmtKrwFromEok(v), tone: 'red' },
				{ label: 'ROE', data: past.roe, fmt: (v: number) => fmtPct(v), tone: 'good' },
				{ label: '부채비율', data: past.debt, fmt: (v: number) => fmtPct(v, { digits: 0 }), tone: 'info' }
			] as series}
				{@const last = series.data?.[series.data.length - 1]}
				{@const first = series.data?.[0]}
				{@const delta = (last != null && first != null && first !== 0) ? ((last - first) / Math.abs(first)) * 100 : null}
				<Card padded>
					<div class="past-head">
						<span class="dl-label">{series.label}</span>
						{#if delta != null}
							<Tag tone={delta > 0 ? 'good' : 'bad'} filled>
								{delta > 0 ? '+' : ''}{delta.toFixed(1)}%
							</Tag>
						{/if}
					</div>
					<div class="past-val">
						<MonoNumber value={typeof last === 'number' ? series.fmt(last) : '—'} size="lg" tone="ink" align="left" />
					</div>
					<div class="past-spark">
						<Sparkline
							data={series.data}
							width={280}
							height={48}
							stroke={({ orange: 'var(--dl-orange)', red: 'var(--dl-red)', good: 'var(--dl-good)', info: 'var(--dl-info)' } as any)[series.tone]}
						/>
					</div>
					<div class="past-axis dl-mono">
						<span>{years[0]}</span><span>{years[years.length - 1]}</span>
					</div>
				</Card>
			{/each}
		</div>
	</Section>

	<!-- ── 02.3 분기 시계열 (8분기) ── -->
	{#if qData?.is?.sales?.length}
		{@const N = qData.is.sales.length}
		{@const showN = Math.min(N, 8)}
		{@const start = Math.max(0, N - showN)}
		{@const recent = (arr: any[]) => arr.slice(start, start + showN)}
		{@const periods = recent(qPeriods.slice(start, start + showN))}
		{@const sales = recent(qData.is.sales)}
		{@const op = recent(qData.is.op)}
		{@const net = recent(qData.is.net)}
		{@const maxSales = Math.max(...sales.map((v: any) => Math.abs(Number(v) || 0)))}
		{@const maxOp = Math.max(...op.map((v: any) => Math.abs(Number(v) || 0)))}
		<Section eyebrow="QUARTERS · 최근 8분기" title="분기 시계열" subtitle="{periods[0]} ~ {periods[periods.length - 1]} · IS 핵심 3축 (매출 · 영업이익 · 순이익)">
			<Card padded>
				<table class="qtable">
					<thead>
						<tr>
							<th class="dl-label" style="text-align: left; width: 80px;">지표</th>
							{#each periods as p}
								<th class="dl-label dl-mono" style="text-align: right;">{p}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						<tr>
							<td class="qtable-rowlabel">매출</td>
							{#each sales as v, i}
								<td class="qtable-cell">
									<MonoNumber value={fmtKrwFromEok(v)} size="sm" tone="ink" align="right" />
									<div class="qtable-bar"><div class="qtable-fill" style="width: {Math.max(2, (Math.abs(Number(v) || 0) / maxSales) * 100)}%; background: var(--dl-orange);"></div></div>
								</td>
							{/each}
						</tr>
						<tr>
							<td class="qtable-rowlabel">영업이익</td>
							{#each op as v, i}
								<td class="qtable-cell">
									<MonoNumber value={fmtKrwFromEok(v)} size="sm" tone={(Number(v) || 0) >= 0 ? 'good' : 'bad'} align="right" />
									<div class="qtable-bar"><div class="qtable-fill" style="width: {Math.max(2, (Math.abs(Number(v) || 0) / maxOp) * 100)}%; background: {(Number(v) || 0) >= 0 ? 'var(--dl-good)' : 'var(--dl-bad)'};"></div></div>
								</td>
							{/each}
						</tr>
						<tr>
							<td class="qtable-rowlabel">순이익</td>
							{#each net as v, i}
								<td class="qtable-cell">
									<MonoNumber value={fmtKrwFromEok(v)} size="sm" tone={(Number(v) || 0) >= 0 ? 'good' : 'bad'} align="right" />
								</td>
							{/each}
						</tr>
					</tbody>
				</table>
			</Card>
		</Section>
	{/if}

	<!-- ── 02.5 IS · 손익 분해 + DuPont ── -->
	{#if fin?.is}
		{@const lastIdx = years.length - 1}
		{@const sales = fin.is.sales?.[lastIdx]}
		{@const op = fin.is.op?.[lastIdx]}
		{@const net = fin.is.net?.[lastIdx]}
		{@const opMargin = sales ? (op / sales) * 100 : null}
		{@const netMargin = sales ? (net / sales) * 100 : null}
		{@const ta = fin.bs?.totals?.totalAsset?.[lastIdx]}
		{@const eq = ta && fin.bs?.totals?.totalLiab?.[lastIdx] != null ? ta - fin.bs.totals.totalLiab[lastIdx] : null}
		{@const turnover = ta && sales ? sales / ta : null}
		{@const leverage = ta && eq ? ta / eq : null}
		{@const roeCalc = netMargin != null && turnover && leverage ? (netMargin / 100) * turnover * leverage * 100 : null}
		{@const cogs = sales && op != null ? sales - op - (sales * 0.15) : null}
		{@const sga = sales ? sales * 0.15 : null}
		{@const tax = op != null && net != null ? op - net : null}
		<Section eyebrow="IS · LOOKING DEEPER" title="손익 분해 + DuPont" subtitle="{years[lastIdx]}년 결산 — 매출 → 영업이익 → 순이익 흐름 + ROE 3-요소 분해">
			<!-- Sankey P&L 흐름 -->
			{#if sales && op != null && net != null && cogs != null && sga != null && tax != null && cogs > 0 && tax > 0}
				<Card eyebrow="P&L · 매출 → 순이익 흐름 (Sankey)" padded>
					<div style="overflow-x: auto; padding: var(--dl-s-2) 0;">
						<Sankey
							flows={[
								{ from: '매출', to: 'COGS', value: cogs, tone: 'neutral' },
								{ from: '매출', to: '영업이익', value: op, tone: 'good' },
								{ from: '매출', to: 'SG&A', value: sga, tone: 'neutral' },
								{ from: '영업이익', to: '세금', value: Math.max(0, tax), tone: 'warn' },
								{ from: '영업이익', to: '순이익', value: Math.max(0, net), tone: 'good' }
							]}
							width={760}
							height={220}
						/>
					</div>
					<p class="dl-body-sm" style="margin: var(--dl-s-3) 0 0; color: var(--dl-ink-faint); font-size: 11px;">
						SG&A 는 매출의 15% 가정 · COGS 는 잔여로 계산 — prebuild 세부 분해 미적용 시 추정치
					</p>
				</Card>
			{/if}

			<div class="is-grid" style="margin-top: var(--dl-s-3);">
				<!-- IS 분해 카드 -->
				<Card eyebrow="IS · 마진 분해" padded>
					<div class="is-flow">
						<div class="is-row">
							<span class="is-label">매출</span>
							<MonoNumber value={fmtKrwFromEok(sales)} size="lg" tone="ink" align="right" />
							<Bar value={100} max={100} tone="brand" height={8} />
						</div>
						<div class="is-row">
							<span class="is-label">영업이익</span>
							<MonoNumber value={fmtKrwFromEok(op)} size="md" tone="good" align="right" />
							<Bar value={Math.max(0, opMargin ?? 0)} max={100} tone="good" height={8} />
						</div>
						<div class="is-row sub">
							<span class="is-sublabel">영업이익률</span>
							<MonoNumber value={fmtPct(opMargin)} size="sm" tone="good" align="right" />
							<span></span>
						</div>
						<div class="is-row">
							<span class="is-label">순이익</span>
							<MonoNumber value={fmtKrwFromEok(net)} size="md" tone={net >= 0 ? 'good' : 'bad'} align="right" />
							<Bar value={Math.max(0, netMargin ?? 0)} max={100} tone={net >= 0 ? 'good' : 'bad'} height={8} />
						</div>
						<div class="is-row sub">
							<span class="is-sublabel">순이익률</span>
							<MonoNumber value={fmtPct(netMargin)} size="sm" tone={net >= 0 ? 'good' : 'bad'} align="right" />
							<span></span>
						</div>
					</div>
				</Card>

				<!-- DuPont 분해 -->
				<Card eyebrow="DUPONT · ROE 분해" padded>
					{#if roeCalc != null}
						<div class="dupont">
							<div class="dp-eq">
								<span class="dp-num">ROE</span>
								<span class="dp-eq-sign">=</span>
								<span class="dp-num accent">{fmtPct(roeCalc)}</span>
							</div>
							<div class="dp-eq parts">
								<div class="dp-part">
									<span class="dl-label">순이익률<Tooltip label="순이익 ÷ 매출 (수익성)" /></span>
									<MonoNumber value={fmtPct(netMargin)} size="md" tone="ink" align="left" />
								</div>
								<span class="dp-eq-sign x">×</span>
								<div class="dp-part">
									<span class="dl-label">자산회전율<Tooltip label="매출 ÷ 총자산 (효율성, 배수)" /></span>
									<MonoNumber value={fmtMul(turnover)} size="md" tone="ink" align="left" />
								</div>
								<span class="dp-eq-sign x">×</span>
								<div class="dp-part">
									<span class="dl-label">레버리지<Tooltip label="총자산 ÷ 자기자본 (재무 레버리지)" /></span>
									<MonoNumber value={fmtMul(leverage)} size="md" tone="ink" align="left" />
								</div>
							</div>
							<p class="dp-note dl-body-sm">
								{#if netMargin != null && netMargin > 10}수익성이 ROE 의 핵심 동력.{:else if leverage && leverage > 2.5}레버리지 비중 큼 — 안정성 점검 필요.{:else}3-요소 균형.{/if}
							</p>
						</div>
					{:else}
						<p class="dl-body-sm" style="color: var(--dl-ink-mute)">DuPont 계산 데이터 부족 (BS totals 누락).</p>
					{/if}
				</Card>
			</div>
		</Section>
	{/if}

	<!-- ── 02.6 BS 자산 + 자본구조 ── -->
	{#if fin?.bs?.totals && fin?.bs?.assets}
		{@const lastIdx = years.length - 1}
		{@const ta = fin.bs.totals.totalAsset?.[lastIdx] ?? 0}
		{@const tl = fin.bs.totals.totalLiab?.[lastIdx] ?? 0}
		{@const cash = fin.bs.assets.cash?.[lastIdx] ?? 0}
		{@const recv = fin.bs.assets.recv?.[lastIdx] ?? 0}
		{@const inv = fin.bs.assets.inv?.[lastIdx] ?? 0}
		{@const tang = fin.bs.assets.tang?.[lastIdx] ?? 0}
		{@const intan = fin.bs.assets.intan?.[lastIdx] ?? 0}
		{@const other = Math.max(0, ta - cash - recv - inv - tang - intan)}
		{@const eqVal = ta - tl}
		{@const debtRatio = ta > 0 ? (tl / ta) * 100 : 0}
		{@const eqRatio = ta > 0 ? (eqVal / ta) * 100 : 0}
		<Section eyebrow="BS · 자산 + 자본 구조" title="대차대조표 한 장" subtitle="{years[lastIdx]}년말 — 자산 분해 + 부채/자본 비중">
			<div class="bs-grid">
				<Card eyebrow="자산 분해" padded>
					<div class="bs-stack">
						{#each [
							{ label: '현금', value: cash, color: 'var(--dl-good)' },
							{ label: '매출채권', value: recv, color: 'var(--dl-info)' },
							{ label: '재고', value: inv, color: 'var(--dl-warn)' },
							{ label: '유형자산', value: tang, color: 'var(--dl-orange)' },
							{ label: '무형자산', value: intan, color: 'var(--dl-violet, #a855f7)' },
							{ label: '기타', value: other, color: 'var(--dl-ink-faint)' }
						].filter((s) => s.value > 0) as seg}
							{@const pct = ta > 0 ? (seg.value / ta) * 100 : 0}
							<div class="bs-row">
								<span class="bs-label">{seg.label}</span>
								<MonoNumber value={fmtKrwFromEok(seg.value)} size="sm" tone="ink" align="right" />
								<div class="bs-bar"><div class="bs-fill" style="width: {pct}%; background: {seg.color};"></div></div>
								<span class="dl-mono bs-pct">{pct.toFixed(1)}%</span>
							</div>
						{/each}
					</div>
					<div class="bs-total">
						<span class="dl-label">총자산</span>
						<MonoNumber value={fmtKrwFromEok(ta)} size="lg" tone="ink" align="right" />
					</div>
				</Card>

				<Card eyebrow="자본 구조" padded>
					<div class="cap-row">
						<span class="cap-label">부채</span>
						<MonoNumber value={fmtKrwFromEok(tl)} size="md" tone="bad" align="right" />
						<span class="dl-mono cap-pct">{debtRatio.toFixed(0)}%</span>
					</div>
					<div class="cap-bar">
						<div class="cap-debt" style="width: {debtRatio}%"></div>
						<div class="cap-eq" style="width: {eqRatio}%"></div>
					</div>
					<div class="cap-row">
						<span class="cap-label">자기자본</span>
						<MonoNumber value={fmtKrwFromEok(eqVal)} size="md" tone="good" align="right" />
						<span class="dl-mono cap-pct">{eqRatio.toFixed(0)}%</span>
					</div>
					<div class="cap-meta">
						<Tag tone={debtRatio <= 100 ? 'good' : debtRatio <= 200 ? 'warn' : 'bad'} filled>
							부채비율 {fmtPct((tl / Math.max(eqVal, 1)) * 100, { digits: 0 })}
						</Tag>
					</div>
				</Card>
			</div>
		</Section>
	{/if}

	<!-- ── 02.65 CF 흐름 ── -->
	{#if fin?.cf}
		{@const lastIdx = years.length - 1}
		{@const opening = fin.cf.opening?.[lastIdx] ?? null}
		{@const opCf = fin.cf.op?.[lastIdx] ?? null}
		{@const invCf = fin.cf.inv?.[lastIdx] ?? null}
		{@const finCf = fin.cf.fin?.[lastIdx] ?? null}
		{@const closing = fin.cf.closing?.[lastIdx] ?? null}
		{#if opCf != null || invCf != null || finCf != null}
			<Section eyebrow="CF · 현금 흐름" title="현금의 출처와 사용" subtitle="{years[lastIdx]}년 — 영업·투자·재무 활동 + 기말 잔액">
				<div class="cf-grid">
					<Card eyebrow="기초 현금" padded>
						<MonoNumber value={fmtKrwFromEok(opening)} size="lg" tone="ink" align="left" />
					</Card>
					<Card eyebrow="영업 CF" accent={(opCf ?? 0) >= 0 ? 'good' : 'bad'} padded>
						<MonoNumber value={fmtKrwFromEok(opCf)} size="lg" tone={(opCf ?? 0) >= 0 ? 'good' : 'bad'} align="left" />
						<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-ink-mute)">{(opCf ?? 0) >= 0 ? '본업으로 현금 생성' : '본업 적자'}</p>
					</Card>
					<Card eyebrow="투자 CF" accent={(invCf ?? 0) <= 0 ? 'warn' : 'info'} padded>
						<MonoNumber value={fmtKrwFromEok(invCf)} size="lg" tone={(invCf ?? 0) <= 0 ? 'warn' : 'info'} align="left" />
						<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-ink-mute)">{(invCf ?? 0) <= 0 ? 'CAPEX 등 투자 진행' : '자산 매각/회수'}</p>
					</Card>
					<Card eyebrow="재무 CF" accent={(finCf ?? 0) >= 0 ? 'info' : 'warn'} padded>
						<MonoNumber value={fmtKrwFromEok(finCf)} size="lg" tone={(finCf ?? 0) >= 0 ? 'info' : 'warn'} align="left" />
						<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-ink-mute)">{(finCf ?? 0) >= 0 ? '차입/증자' : '상환/배당'}</p>
					</Card>
					<Card eyebrow="기말 현금" padded>
						<MonoNumber value={fmtKrwFromEok(closing)} size="lg" tone="ink" align="left" />
					</Card>
				</div>
			</Section>
		{/if}
	{/if}

	<!-- ── 02.7 ROIC vs WACC ── -->
	{#if fin?.is && fin?.bs?.totals}
		{@const lastIdx = years.length - 1}
		{@const ic = (fin.bs.totals.totalAsset?.[lastIdx] ?? 0) - (fin.bs.totals.totalLiab?.[lastIdx] ?? 0)}
		{@const opAfterTax = (fin.is.op?.[lastIdx] ?? 0) * (1 - 0.21)}
		{@const roic = ic > 0 ? (opAfterTax / ic) * 100 : null}
		{@const wacc = 8.5}
		{@const eva = roic != null ? roic - wacc : null}
		<Section eyebrow="ROIC · 자본 효율" title="ROIC vs WACC" subtitle="투하자본이익률(세후) 대 가중평균자본비용. 자본 창출 vs 파괴.">
			<div class="roic-grid">
				<Card eyebrow="ROIC · 세후 영업이익 ÷ 투하자본" accent={eva != null && eva > 0 ? 'good' : 'bad'} padded>
					<MonoNumber value={roic != null ? fmtPct(roic) : '—'} size="xl" tone={eva != null && eva > 0 ? 'good' : 'bad'} align="left" />
					<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-ink-mute)">
						{years[lastIdx]}년 · 투하자본 {fmtKrwFromEok(ic)}
					</p>
				</Card>

				<Card eyebrow="WACC · 가정" padded>
					<MonoNumber value={fmtPct(wacc)} size="xl" tone="ink" align="left" />
					<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-ink-mute)">
						한국 평균 (CAPM 단순 가정)<Tooltip label="실제는 섹터 베타 + Risk-free + ERP 로 산출. 여기는 8.5% 고정." />
					</p>
				</Card>

				<Card eyebrow="EVA · 가치 창출/파괴" accent={eva != null && eva > 0 ? 'good' : 'bad'} padded>
					<MonoNumber value={eva != null ? `${eva > 0 ? '+' : ''}${eva.toFixed(1)}%p` : '—'} size="xl" tone={eva != null && eva > 0 ? 'good' : 'bad'} align="left" />
					<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: {eva != null && eva > 0 ? 'var(--dl-good)' : 'var(--dl-bad)'}">
						{#if eva != null && eva > 0}자본 창출 중. ROIC > WACC.{:else if eva != null && eva <= 0}자본 파괴 중. WACC 부담 초과.{:else}데이터 부족.{/if}
					</p>
				</Card>
			</div>
		</Section>
	{/if}

	<!-- ── 03 INDUSTRY · 업종 위치 ── -->
	{#if industry}
		<Section number="03" eyebrow="INDUSTRY" title="업종 안에서의 위치" subtitle="{industry.name ?? industry.id} · 회사 {industry.nodeCount ?? '?'} 사 · 총 매출 {fmtKrwFromEok(industry.totalRevenue)}">
			<div class="ind-grid">
				<Card eyebrow="STAGE" title="이 회사의 단계" padded>
					<div class="stage-info">
						<MonoNumber value={cmeta?.ego?.stage ?? node.stageName ?? '—'} size="lg" tone="ink" align="left" />
						<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-ink-mute)">
							{node.role ?? '업종 내 역할 정보 없음'}
						</p>
					</div>
				</Card>

				<Card eyebrow="STAGES" title="업종 단계 분포" padded>
					<div class="stages">
						{#each (industry.stages ?? []) as stg}
							{@const pct = (stg.nodes?.length ?? 0) / Math.max(industry.nodeCount ?? 1, 1) * 100}
							<div class="stage-row">
								<span class="stage-name">{stg.name}</span>
								<div class="stage-bar"><Bar value={pct} max={100} tone={stg.key === (cmeta?.ego?.stage ?? node.stage) ? 'brand' : 'neutral'} /></div>
								<span class="stage-count dl-mono">{stg.nodes?.length ?? 0}</span>
							</div>
						{/each}
					</div>
				</Card>
			</div>
		</Section>
	{/if}

	<!-- ── 03.5 MACRO · 거시 사이클 + 섹터 영향 ── -->
	{#if data.macro}
		{@const m = data.macro as any}
		<Section eyebrow="MACRO · 거시 맥락" title="현재 사이클 + 섹터 순풍/역풍" subtitle="{m.asOf ?? ''} 기준 · KR/US 시장">
			<div class="macro-grid">
				{#if m.kr}
					<Card eyebrow="KR · 한국" accent={m.kr.phase === 'expansion' ? 'good' : m.kr.phase === 'contraction' ? 'bad' : 'warn'} padded>
						<div class="phase-name">{m.kr.phaseLabel ?? m.kr.phase ?? '—'}</div>
						<div class="phase-conf"><span class="dl-label">신뢰도</span><MonoNumber value={m.kr.confidence ?? '—'} size="sm" tone="ink" align="left" /></div>
						{#if m.kr.signals?.length}
							<ul class="phase-sig">
								{#each m.kr.signals.slice(0, 3) as s}
									<li>{typeof s === 'string' ? s : (s?.text ?? s?.label ?? '')}</li>
								{/each}
							</ul>
						{/if}
					</Card>
				{/if}
				{#if m.us}
					<Card eyebrow="US · 미국" accent={m.us.phase === 'expansion' ? 'good' : m.us.phase === 'contraction' ? 'bad' : 'warn'} padded>
						<div class="phase-name">{m.us.phaseLabel ?? m.us.phase ?? '—'}</div>
						<div class="phase-conf"><span class="dl-label">신뢰도</span><MonoNumber value={m.us.confidence ?? '—'} size="sm" tone="ink" align="left" /></div>
						{#if m.us.signals?.length}
							<ul class="phase-sig">
								{#each m.us.signals.slice(0, 3) as s}
									<li>{typeof s === 'string' ? s : (s?.text ?? s?.label ?? '')}</li>
								{/each}
							</ul>
						{/if}
					</Card>
				{/if}
			</div>
		</Section>
	{/if}

	<!-- ── 03.7 FUTURE · 시나리오 ── -->
	{#if past.revenue?.length >= 3}
		{@const lastRev = past.revenue[past.revenue.length - 1]}
		{@const cagr = node?.revCagr ?? 0}
		{@const baseGrow = cagr / 100}
		{@const bullGrow = baseGrow + 0.05}
		{@const bearGrow = Math.max(-0.1, baseGrow - 0.05)}
		{@const proj3y = (g: number) => lastRev * Math.pow(1 + g, 3)}
		<Section eyebrow="FUTURE · 시나리오" title="3년 후 매출 예상" subtitle="과거 5년 CAGR 기준. Bull (+5%p) · Base (CAGR 그대로) · Bear (-5%p, 최저 -10%).">
			<div class="scn-grid">
				<Card eyebrow="BEAR · 비관" accent="bad" padded>
					<div class="scn-prob"><span class="dl-label">확률</span><MonoNumber value="22" suffix="%" size="sm" tone="ink" align="left" /></div>
					<MonoNumber value={fmtKrwFromEok(proj3y(bearGrow))} size="lg" tone="bad" align="left" />
					<div class="dl-eyebrow" style="margin-top: var(--dl-s-2)">3Y CAGR {fmtPct(bearGrow * 100)}</div>
				</Card>
				<Card eyebrow="BASE · 기본" accent="warn" padded>
					<div class="scn-prob"><span class="dl-label">확률</span><MonoNumber value="56" suffix="%" size="sm" tone="ink" align="left" /></div>
					<MonoNumber value={fmtKrwFromEok(proj3y(baseGrow))} size="lg" tone="warn" align="left" />
					<div class="dl-eyebrow" style="margin-top: var(--dl-s-2)">3Y CAGR {fmtPct(baseGrow * 100)}</div>
				</Card>
				<Card eyebrow="BULL · 낙관" accent="good" padded>
					<div class="scn-prob"><span class="dl-label">확률</span><MonoNumber value="22" suffix="%" size="sm" tone="ink" align="left" /></div>
					<MonoNumber value={fmtKrwFromEok(proj3y(bullGrow))} size="lg" tone="good" align="left" />
					<div class="dl-eyebrow" style="margin-top: var(--dl-s-2)">3Y CAGR {fmtPct(bullGrow * 100)}</div>
				</Card>
			</div>
			<p class="dl-body-sm" style="margin-top: var(--dl-s-3); color: var(--dl-ink-faint); text-align: center; font-size: 11px;">
				prebuild forecast 미적용 — 단순 CAGR 외삽. 실 quant 엔진 연동 예정
			</p>
		</Section>
	{/if}

	<!-- ── 04 INSIGHT · dartlab AI 해석 (prebuild) ── -->
	{#if cmeta?.aiInsight}
		<Section number="04" eyebrow="AI INSIGHT" title="dartlab 의 해석" subtitle="CI 에서 prebuild 된 분석. 실시간 호출 없음. {cmeta.aiInsight.createdAt ? new Date(cmeta.aiInsight.createdAt).toLocaleDateString('ko-KR') : ''} 기준.">
			<div class="insight-grid">
				<Card padded>
					<div class="dl-label" style="margin-bottom: var(--dl-s-3)">서사</div>
					<div class="ai-narrative dl-body">
						{cmeta.aiInsight.narrative ?? '해석 생성 전.'}
					</div>
				</Card>

				<div class="proscons">
					{#if cmeta.aiInsight.strengths?.length}
						<Card eyebrow="강점 · STRENGTHS" accent="good" padded>
							<ul class="pc-list">
								{#each cmeta.aiInsight.strengths as s}
									<li><span class="pc-mark up">▲</span><span class="pc-text">{s}</span></li>
								{/each}
							</ul>
						</Card>
					{/if}
					{#if cmeta.aiInsight.weaknesses?.length}
						<Card eyebrow="약점 · WEAKNESSES" accent="bad" padded>
							<ul class="pc-list">
								{#each cmeta.aiInsight.weaknesses as w}
									<li><span class="pc-mark down">▼</span><span class="pc-text">{w}</span></li>
								{/each}
							</ul>
						</Card>
					{/if}
				</div>
			</div>
		</Section>
	{/if}

	<!-- ── 05 PEERS · 동종 비교 ── -->
	{#if cmeta?.peers?.length}
		{@const maxRev = Math.max(...cmeta.peers.map((p: any) => p.revenue ?? 0), node.revenue ?? 0)}
		<Section number="05" eyebrow="PEERS" title="같은 단계 회사 비교" subtitle="매출 기준 상위 {cmeta.peers.length} 사. 같은 산업 · 같은 stage.">
			<Card padded>
				<table class="peer-table">
					<thead>
						<tr>
							<th class="dl-label">#</th>
							<th class="dl-label">회사</th>
							<th class="dl-label">단계</th>
							<th class="dl-label" style="text-align: right">매출</th>
							<th class="dl-label">상대</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						<tr class="self-row">
							<td><span class="dl-mono dim">★</span></td>
							<td><span class="peer-name self">{node.label} (현재)</span></td>
							<td><Tag tone="info">{node.stageName ?? '—'}</Tag></td>
							<td style="text-align: right"><MonoNumber value={fmtKrwFromEok(node.revenue)} size="sm" tone="ink" align="right" /></td>
							<td><Bar value={node.revenue ?? 0} max={maxRev} tone="brand" /></td>
							<td></td>
						</tr>
						{#each cmeta.peers as p, i}
							<tr>
								<td><span class="dl-mono dim">{(i + 1).toString().padStart(2, '0')}</span></td>
								<td><span class="peer-name">{p.corpName ?? p.stockCode}</span></td>
								<td><Tag>{p.stage ?? '—'}</Tag></td>
								<td style="text-align: right"><MonoNumber value={fmtKrwFromEok(p.revenue)} size="sm" tone="ink" align="right" /></td>
								<td><Bar value={p.revenue ?? 0} max={maxRev} tone="neutral" /></td>
								<td><a href="{base}/lab/dashboard/{p.stockCode}" class="peer-link" aria-label="대시보드 이동">→</a></td>
							</tr>
						{/each}
					</tbody>
				</table>
			</Card>
		</Section>
	{/if}

	<!-- ── 06 SUPPLY · 공급망 ── -->
	{#if cmeta?.supplyInsights}
		{@const si = cmeta.supplyInsights}
		<Section number="06" eyebrow="SUPPLY CHAIN" title="공급망" subtitle="DART 사업보고서 거래처·제품 명세 기반. confidence ≥ 0.7 만 노출.">
			<div class="supply-grid">
				<Card eyebrow="HHI · 집중도" accent={si.hhiRisk === 'high' ? 'bad' : si.hhiRisk === 'medium' ? 'warn' : 'good'} padded>
					<MonoNumber value={si.hhi?.toFixed(0) ?? '—'} size="xl" tone="ink" align="left" />
					<div style="margin-top: var(--dl-s-3)">
						<Tag tone={si.hhiRisk === 'high' ? 'bad' : si.hhiRisk === 'medium' ? 'warn' : 'good'} filled>
							{si.hhiRisk === 'high' ? '높은 집중' : si.hhiRisk === 'medium' ? '중간 집중' : '낮은 집중'}
						</Tag>
					</div>
					<p class="dl-body-sm" style="margin-top: var(--dl-s-3); color: var(--dl-ink-mute)">
						Top 1 비중 {si.top1Ratio?.toFixed(1) ?? '—'}% · Top 3 {si.top3Ratio?.toFixed(1) ?? '—'}%
					</p>
				</Card>

				<Card eyebrow="다양성" padded>
					<div class="div-grid">
						<div>
							<span class="dl-label">공급처 산업</span>
							<MonoNumber value={si.industryDiversity ?? '—'} size="lg" tone="ink" align="left" />
						</div>
						<div>
							<span class="dl-label">공급처 단계</span>
							<MonoNumber value={si.stageDiversity ?? '—'} size="lg" tone="ink" align="left" />
						</div>
					</div>
					<p class="dl-body-sm" style="margin-top: var(--dl-s-3); color: var(--dl-ink-mute)">
						공급사 {si.supplierCount ?? 0} · 고객 {si.customerCount ?? 0} · 거래 {si.preciseEdgeCount ?? 0} 건
					</p>
				</Card>

				{#if cmeta.suppliers?.length}
					<Card eyebrow="TOP 공급사" padded>
						<ul class="sc-list">
							{#each cmeta.suppliers.slice(0, 5) as s}
								<li class="sc-row">
									<span class="sc-name">{s.corpName ?? s.stockCode}</span>
									<span class="sc-prod">{s.product ?? '—'}</span>
									{#if s.ratio}<Tag>{s.ratio.toFixed(1)}%</Tag>{/if}
								</li>
							{/each}
						</ul>
					</Card>
				{/if}

				{#if cmeta.customers?.length}
					<Card eyebrow="TOP 고객사" padded>
						<ul class="sc-list">
							{#each cmeta.customers.slice(0, 5) as c}
								<li class="sc-row">
									<span class="sc-name">{c.corpName ?? c.stockCode}</span>
									<span class="sc-prod">{c.product || '—'}</span>
								</li>
							{/each}
						</ul>
					</Card>
				{/if}
			</div>
		</Section>
	{/if}

	<!-- ── 06.5 GOVERNANCE · 지배구조 ── -->
	{#if cmeta?.ego}
		{@const eg = cmeta.ego}
		<Section number="06" eyebrow="GOVERNANCE" title="지배구조 · 자본" subtitle="감사·지분·감사인 정보">
			<div class="gov-grid">
				{#if eg.holderPct != null}
					<Card eyebrow="최대주주 지분" padded>
						<MonoNumber value={fmtPct(eg.holderPct, { digits: 1 })} size="xl" tone="ink" align="left" />
						{#if eg.holderChange != null}
							<div style="margin-top: var(--dl-s-2)">
								<Tag tone={eg.holderChange >= 0 ? 'good' : 'bad'} filled>
									{eg.holderChange >= 0 ? '+' : ''}{eg.holderChange.toFixed(1)}%p YoY
								</Tag>
							</div>
						{/if}
					</Card>
				{/if}
				{#if eg.audit}
					<Card eyebrow="감사" padded>
						<div class="gov-val">{eg.audit}</div>
						<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-ink-mute)">감사인</p>
					</Card>
				{/if}
				{#if eg.govGrade}
					<Card eyebrow="지배구조 등급" accent={eg.govGrade === 'A' ? 'good' : eg.govGrade === 'C' || eg.govGrade === 'D' || eg.govGrade === 'E' ? 'bad' : 'warn'} padded>
						<MonoNumber value={eg.govGrade} size="xl" tone={eg.govGrade === 'A' ? 'good' : eg.govGrade === 'C' || eg.govGrade === 'D' || eg.govGrade === 'E' ? 'bad' : 'warn'} align="left" />
					</Card>
				{/if}
				{#if eg.empCount != null}
					<Card eyebrow="임직원 수" padded>
						<MonoNumber value={eg.empCount.toLocaleString()} suffix=" 명" size="xl" tone="ink" align="left" />
					</Card>
				{/if}
			</div>
		</Section>
	{/if}

	<!-- ── 07 BLOG · 관련 글 ── -->
	{#if cmeta?.blogPosts?.length}
		<Section number="07" eyebrow="READ · 심층 분석" title="블로그 관련 글" subtitle="이 회사를 다룬 dartlab 블로그 포스트.">
			<div class="blog-grid">
				{#each cmeta.blogPosts.slice(0, 4) as bp}
					<a href="{base}/blog/{bp.slug}" class="blog-card">
						<Card interactive padded>
							<div class="dl-eyebrow">{bp.date ?? ''}</div>
							<h4 class="blog-title">{bp.title}</h4>
							{#if bp.excerpt}
								<p class="blog-excerpt">{bp.excerpt}</p>
							{/if}
						</Card>
					</a>
				{/each}
			</div>
		</Section>
	{/if}

	<!-- ── footer · 다음 단계 안내 ── -->
	<footer class="lab-foot">
		<Eyebrow text="END · /lab/dashboard prototype — 다음: IS/BS/CF Sankey · Value 4모델 · Future 시나리오" />
	</footer>
{/if}

<style>
	/* ── nav ── */
	.lab-nav {
		position: sticky;
		top: 0;
		z-index: 30;
		border-bottom: 1px solid var(--dl-line);
		background: rgba(15, 15, 16, 0.85);
		backdrop-filter: blur(14px);
	}
	.nav-inner {
		max-width: var(--dl-w-max);
		margin-inline: auto;
		padding: var(--dl-s-3) var(--dl-s-6);
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--dl-s-4);
	}
	.brand { display: inline-flex; align-items: baseline; gap: var(--dl-s-2); text-decoration: none; color: var(--dl-ink); }
	.brand-mark { font-family: var(--dl-font-head); font-weight: 700; font-size: 18px; letter-spacing: -0.02em; }
	.brand-slash { color: var(--dl-ink-faint); font-weight: 300; }
	.brand-ctx { font-family: var(--dl-font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.16em; color: var(--dl-orange); }
	.nav-actions { display: flex; gap: var(--dl-s-1); }

	/* ── empty state ── */
	.empty {
		max-width: var(--dl-w-article);
		margin: var(--dl-s-9) auto;
		padding: var(--dl-s-6);
		text-align: center;
		display: flex;
		flex-direction: column;
		gap: var(--dl-s-4);
		align-items: center;
	}

	/* ── hero ── */
	.hero { padding: var(--dl-s-8) var(--dl-s-6) var(--dl-s-7); border-bottom: 1px solid var(--dl-line); }
	.hero-inner { max-width: var(--dl-w-max); margin-inline: auto; }
	.hero-slug { display: flex; align-items: center; gap: var(--dl-s-2); font-size: 12px; color: var(--dl-ink-mute); margin-bottom: var(--dl-s-3); flex-wrap: wrap; }
	.hero-sep { width: 3px; height: 3px; border-radius: 50%; background: var(--dl-ink-faint); }
	.hero-name { margin: var(--dl-s-2) 0 var(--dl-s-4); }
	.hero-tags { display: flex; gap: var(--dl-s-2); margin-bottom: var(--dl-s-6); flex-wrap: wrap; }
	.hero-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: var(--dl-s-5); align-items: stretch; }

	.verdict { display: flex; flex-direction: column; gap: var(--dl-s-3); }
	.v-call { font-family: var(--dl-font-ui); font-size: 32px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; }
	.v-call.tone-good { color: var(--dl-good); }
	.v-call.tone-bad { color: var(--dl-bad); }
	.v-call.tone-warn { color: var(--dl-warn); }
	.v-call-en { font-family: var(--dl-font-mono); font-size: 14px; font-weight: 500; opacity: 0.7; margin-left: 4px; }
	.v-meta { display: flex; align-items: baseline; gap: var(--dl-s-3); padding-top: var(--dl-s-3); border-top: 1px solid var(--dl-line); }
	.v-line { margin: 0; font-size: 14px; line-height: 1.6; color: var(--dl-ink); }

	/* ── grades ── */
	.grades { display: flex; flex-direction: column; gap: var(--dl-s-3); }
	.grade-row { display: grid; grid-template-columns: 80px 1fr 60px; gap: var(--dl-s-3); align-items: center; }
	.grade-label { font-size: 13px; color: var(--dl-ink); }
	.grade-bar { min-width: 0; }
	.grade-text { text-align: right; font-size: 11px; color: var(--dl-ink-mute); }

	/* ── KPI grid ── */
	.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--dl-s-3); }
	.kpi-head { margin-bottom: var(--dl-s-2); display: flex; align-items: center; }
	.kpi-val { margin-bottom: var(--dl-s-3); }
	.kpi-pctile { display: flex; flex-direction: column; gap: var(--dl-s-1); padding-top: var(--dl-s-2); border-top: 1px solid var(--dl-line); }

	/* ── Past 5Y grid ── */
	.past-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--dl-s-3); }
	.past-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--dl-s-2); }
	.past-val { margin-bottom: var(--dl-s-3); }
	.past-spark { color: var(--dl-orange); margin-bottom: var(--dl-s-2); }
	.past-axis { display: flex; justify-content: space-between; font-size: 10px; color: var(--dl-ink-faint); }

	/* ── Industry ── */
	.ind-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--dl-s-3); }
	.stage-info { padding: var(--dl-s-2) 0; }
	.stages { display: flex; flex-direction: column; gap: var(--dl-s-3); }
	.stage-row { display: grid; grid-template-columns: 100px 1fr 40px; gap: var(--dl-s-3); align-items: center; }
	.stage-name { font-size: 12px; color: var(--dl-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.stage-count { text-align: right; font-size: 11px; color: var(--dl-ink-mute); }

	/* ── AI narrative ── */
	.ai-narrative { white-space: pre-wrap; max-width: var(--dl-w-article); }

	/* ── IS / DuPont (02.5) ── */
	.is-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--dl-s-3); }
	.is-flow { display: flex; flex-direction: column; gap: var(--dl-s-3); padding: var(--dl-s-2) 0; }
	.is-row { display: grid; grid-template-columns: 80px 1fr 1.4fr; gap: var(--dl-s-3); align-items: center; }
	.is-row.sub { grid-template-columns: 80px 1fr; padding-left: var(--dl-s-3); border-left: 1px dashed var(--dl-line); margin-left: var(--dl-s-2); padding-top: 0; padding-bottom: 0; }
	.is-label { font-size: 13px; color: var(--dl-ink); font-weight: 500; }
	.is-sublabel { font-size: 11px; color: var(--dl-ink-dim); }

	.dupont { display: flex; flex-direction: column; gap: var(--dl-s-4); padding: var(--dl-s-2) 0; }
	.dp-eq { display: flex; align-items: baseline; gap: var(--dl-s-3); justify-content: center; }
	.dp-num { font-family: var(--dl-font-mono); font-size: 22px; font-weight: 700; color: var(--dl-ink-print); letter-spacing: -0.02em; }
	.dp-num.accent { color: var(--dl-orange); font-size: 28px; }
	.dp-eq-sign { font-family: var(--dl-font-mono); font-size: 18px; color: var(--dl-ink-faint); }
	.dp-eq-sign.x { font-size: 14px; }
	.dp-eq.parts { gap: var(--dl-s-2); flex-wrap: wrap; }
	.dp-part { display: flex; flex-direction: column; gap: var(--dl-s-1); align-items: flex-start; padding: var(--dl-s-2) var(--dl-s-3); background: var(--dl-bg-base); border-radius: var(--dl-r-sm); border: 1px solid var(--dl-line); }
	.dp-note { color: var(--dl-ink-mute); margin: var(--dl-s-2) 0 0; text-align: center; font-size: 12px; }

	/* ── Quarters table (02.3) ── */
	.qtable { width: 100%; border-collapse: collapse; font-size: 12px; }
	.qtable th { padding: var(--dl-s-2); border-bottom: 1px solid var(--dl-line); }
	.qtable td { padding: var(--dl-s-2); border-bottom: 1px solid var(--dl-line); vertical-align: middle; }
	.qtable tr:last-child td { border-bottom: none; }
	.qtable-rowlabel { font-size: 12px; color: var(--dl-ink); font-weight: 500; }
	.qtable-cell { text-align: right; min-width: 80px; }
	.qtable-bar { width: 100%; height: 3px; background: rgba(255, 255, 255, 0.04); border-radius: 1.5px; overflow: hidden; margin-top: 3px; }
	.qtable-fill { height: 100%; border-radius: 1.5px; }

	/* ── BS 자산 + 자본 (02.6) ── */
	.bs-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: var(--dl-s-3); }
	.bs-stack { display: flex; flex-direction: column; gap: var(--dl-s-2); padding: var(--dl-s-2) 0; }
	.bs-row { display: grid; grid-template-columns: 80px 90px 1fr 50px; gap: var(--dl-s-2); align-items: center; font-size: 12px; }
	.bs-label { color: var(--dl-ink); font-weight: 500; }
	.bs-bar { height: 8px; background: rgba(255, 255, 255, 0.04); border-radius: 4px; overflow: hidden; }
	.bs-fill { height: 100%; border-radius: 4px; }
	.bs-pct { color: var(--dl-ink-mute); font-size: 11px; text-align: right; }
	.bs-total { display: flex; justify-content: space-between; align-items: baseline; padding-top: var(--dl-s-3); margin-top: var(--dl-s-3); border-top: 1px solid var(--dl-line); }

	.cap-row { display: grid; grid-template-columns: 80px 1fr 50px; gap: var(--dl-s-2); align-items: baseline; padding: var(--dl-s-2) 0; }
	.cap-label { font-size: 13px; color: var(--dl-ink); font-weight: 500; }
	.cap-pct { color: var(--dl-ink-mute); font-size: 11px; text-align: right; }
	.cap-bar { display: flex; height: 14px; border-radius: var(--dl-r-sm); overflow: hidden; margin: var(--dl-s-2) 0; }
	.cap-debt { background: var(--dl-bad); opacity: 0.7; }
	.cap-eq { background: var(--dl-good); opacity: 0.7; }
	.cap-meta { padding-top: var(--dl-s-3); border-top: 1px solid var(--dl-line); margin-top: var(--dl-s-3); }

	/* ── CF (02.65) ── */
	.cf-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--dl-s-3); }

	/* ── ROIC vs WACC (02.7) ── */
	.roic-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--dl-s-3); }

	/* ── governance (06) ── */
	.gov-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--dl-s-3); }
	.gov-val { font-family: var(--dl-font-mono); font-size: 18px; font-weight: 700; color: var(--dl-ink-print); margin-top: var(--dl-s-2); }

	/* ── future scenario (03.7) ── */
	.scn-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--dl-s-3); }
	.scn-prob { display: flex; align-items: baseline; gap: var(--dl-s-2); margin-bottom: var(--dl-s-2); }

	/* ── macro (03.5) ── */
	.macro-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--dl-s-3); }
	.phase-name { font-family: var(--dl-font-ui); font-size: 28px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; color: var(--dl-ink-print); margin: var(--dl-s-2) 0; }
	.phase-conf { display: flex; align-items: baseline; gap: var(--dl-s-2); padding: var(--dl-s-2) 0; border-top: 1px solid var(--dl-line); }
	.phase-sig { list-style: none; padding: 0; margin: var(--dl-s-3) 0 0; display: flex; flex-direction: column; gap: var(--dl-s-1); font-size: 12px; color: var(--dl-ink-mute); }
	.phase-sig li { padding-left: var(--dl-s-3); position: relative; }
	.phase-sig li::before { content: '·'; position: absolute; left: var(--dl-s-1); color: var(--dl-ink-faint); }

	/* ── insight grid (04) ── */
	.insight-grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: var(--dl-s-3); align-items: start; }
	.proscons { display: flex; flex-direction: column; gap: var(--dl-s-3); }
	.pc-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--dl-s-2); }
	.pc-list li { display: flex; gap: var(--dl-s-2); align-items: flex-start; font-size: 13px; line-height: 1.55; color: var(--dl-ink); }
	.pc-mark { font-size: 10px; flex-shrink: 0; padding-top: 4px; }
	.pc-mark.up { color: var(--dl-good); }
	.pc-mark.down { color: var(--dl-bad); }
	.pc-text { flex: 1; }

	/* ── peer table (05) ── */
	.peer-table { width: 100%; border-collapse: collapse; font-size: 13px; }
	.peer-table th { text-align: left; padding: var(--dl-s-2) var(--dl-s-3); border-bottom: 1px solid var(--dl-line); font-size: 10px; }
	.peer-table td { padding: var(--dl-s-2) var(--dl-s-3); border-bottom: 1px solid var(--dl-line); color: var(--dl-ink); }
	.peer-table tr:last-child td { border-bottom: none; }
	.peer-table tr.self-row { background: rgba(234, 70, 71, 0.04); }
	.peer-name { font-weight: 500; }
	.peer-name.self { font-weight: 700; color: var(--dl-ink-print); }
	.peer-link { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: var(--dl-r-sm); color: var(--dl-orange); text-decoration: none; transition: background var(--dl-dur-hover) var(--dl-ease); }
	.peer-link:hover { background: var(--dl-bg-overlay); }
	.dim { color: var(--dl-ink-faint); }

	/* ── supply (06) ── */
	.supply-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--dl-s-3); }
	.div-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--dl-s-3); padding: var(--dl-s-2) 0; }
	.div-grid > div { display: flex; flex-direction: column; gap: var(--dl-s-1); }
	.sc-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--dl-s-2); }
	.sc-row { display: grid; grid-template-columns: 1fr 1fr auto; gap: var(--dl-s-2); align-items: center; font-size: 12px; padding: var(--dl-s-1) 0; border-bottom: 1px dashed var(--dl-line); }
	.sc-row:last-child { border-bottom: none; }
	.sc-name { color: var(--dl-ink); }
	.sc-prod { color: var(--dl-ink-mute); font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

	/* ── blog (07) ── */
	.blog-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--dl-s-3); }
	.blog-card { text-decoration: none; color: inherit; }
	.blog-title { font-size: 16px; font-weight: 700; letter-spacing: -0.01em; line-height: 1.35; margin: var(--dl-s-2) 0 var(--dl-s-2); color: var(--dl-ink-print); }
	.blog-excerpt { font-size: 13px; color: var(--dl-ink-mute); line-height: 1.55; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

	/* ── foot ── */
	.lab-foot { padding: var(--dl-s-7) var(--dl-s-6); text-align: center; border-top: 1px solid var(--dl-line); }

	/* ── responsive ── */
	@media (max-width: 900px) {
		.hero-grid { grid-template-columns: 1fr; }
		.kpi-grid { grid-template-columns: repeat(2, 1fr); }
		.past-grid { grid-template-columns: 1fr; }
		.ind-grid { grid-template-columns: 1fr; }
	}
	@media (max-width: 560px) {
		.kpi-grid { grid-template-columns: 1fr; }
		.hero { padding: var(--dl-s-6) var(--dl-s-4) var(--dl-s-5); }
	}
</style>
