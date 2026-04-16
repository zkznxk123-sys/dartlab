<script lang="ts">
	import type { PageData } from './$types';
	import { base } from '$app/paths';
	import FreshnessBadge from '$lib/components/industry/FreshnessBadge.svelte';

	let { data }: { data: PageData } = $props();
	let ind = $derived(data.data);
	let stages = $derived(ind.stages || []);
	let edges = $derived(ind.edges || []);
	let stats = $derived((data as any).stats);
	let indMovers = $derived((data as any).movers || {});
	let meta = $derived((data as any).meta);

	// Movers 총 건수 (이 산업)
	let indMoversTotal = $derived(
		(Object.values(indMovers) as any[]).reduce((s, arr: any) => s + (arr?.length || 0), 0)
	);

	function formatRev(v: number): string {
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조원`;
		return `${v.toLocaleString()}억원`;
	}

	function formatAmount(v: number | null | undefined): string {
		if (!v) return '';
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조`;
		return `${v.toLocaleString()}억`;
	}

	// edge: stockCode → corpName 맵핑
	let nameMap = $derived.by(() => {
		const m: Record<string, string> = {};
		for (const stage of stages) {
			for (const node of stage.nodes || []) {
				m[node.stockCode] = node.corpName;
			}
		}
		return m;
	});

	// 정밀 엣지 (amount 있는) top 20
	let preciseEdges = $derived(
		[...edges]
			.filter((e: any) => e.amount)
			.sort((a: any, b: any) => (b.amount || 0) - (a.amount || 0))
			.slice(0, 20)
	);

</script>

<svelte:head>
	<title>{ind.name} 산업지도 · 공정별 · 공급망 | dartlab 전자공시</title>
	<meta
		name="description"
		content={`${ind.name} 산업 ${ind.nodeCount}사의 공정별 구조, 공급망 엣지 ${edges.length}건, 총 매출 ${formatRev(ind.totalRevenue)}`}
	/>
	<meta property="og:type" content="website" />
	<meta property="og:title" content={`${ind.name} 산업지도 — dartlab`} />
	<meta
		property="og:description"
		content={`${ind.nodeCount}사 · 총매출 ${formatRev(ind.totalRevenue)} · Top ROE/성장/위험 + 공급망`}
	/>
	<meta property="og:image" content="https://eddmpython.github.io/dartlab/og-image.png" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta name="twitter:card" content="summary_large_image" />
	<link
		rel="alternate"
		type="application/rss+xml"
		title={`${ind.name} 변화 감지 RSS`}
		href={`/dartlab/feed/industry/${data.id}.xml`}
	/>
</svelte:head>

<div class="wrap">
	<nav class="breadcrumb">
		<a href="{base}/map">산업지도</a>
		<span>›</span>
		<span>{ind.name}</span>
	</nav>

	<header class="head">
		<div class="head-top">
			<h1>{ind.name}</h1>
			{#if meta?.dataAsOf}
				<FreshnessBadge dataAsOf={meta.dataAsOf} variant="compact" />
			{/if}
		</div>
		<div class="stats">
			<div class="stat">
				<div class="label">기업 수</div>
				<div class="value">{ind.nodeCount}사</div>
			</div>
			<div class="stat">
				<div class="label">총 매출</div>
				<div class="value">{formatRev(ind.totalRevenue)}</div>
			</div>
			{#if stats?.avgRoe !== null && stats?.avgRoe !== undefined}
				<div class="stat">
					<div class="label">평균 ROE</div>
					<div class="value" class:pos={stats.avgRoe > 0} class:neg={stats.avgRoe < 0}>
						{stats.avgRoe}%
					</div>
				</div>
			{/if}
			{#if stats?.avgOpMargin !== null && stats?.avgOpMargin !== undefined}
				<div class="stat">
					<div class="label">평균 영업이익률</div>
					<div class="value" class:pos={stats.avgOpMargin > 0} class:neg={stats.avgOpMargin < 0}>
						{stats.avgOpMargin}%
					</div>
				</div>
			{/if}
			{#if stats?.avgCagr !== null && stats?.avgCagr !== undefined}
				<div class="stat">
					<div class="label">평균 CAGR 3Y</div>
					<div class="value" class:pos={stats.avgCagr > 0} class:neg={stats.avgCagr < 0}>
						{stats.avgCagr}%
					</div>
				</div>
			{/if}
			<div class="stat">
				<div class="label">공급망 엣지</div>
				<div class="value">{edges.length}건</div>
			</div>
		</div>
		{#if indMoversTotal > 0}
			<a class="movers-pill" href="{base}/changes">
				⚡ 이 산업 이번 회계연도 급변 <strong>{indMoversTotal}건</strong> · 상세 보기 →
			</a>
		{/if}
	</header>

	<!-- Top 3 / 최고 성장 / 위험 신호 -->
	{#if stats && (stats.topRoe?.length || stats.topGrowth?.length || stats.riskFlags?.length)}
		<section class="sec rankings">
			<h2>산업 내 Top 랭킹</h2>
			<div class="rank-grid">
				{#if stats.topRoe?.length}
					<div class="rank-card">
						<div class="rank-head">
							<span class="rank-icon">🏆</span>
							<span class="rank-title">최고 수익성 (ROE)</span>
						</div>
						<ul>
							{#each stats.topRoe.slice(0, 5) as r, i (r.stockCode)}
								<li>
									<span class="rank-n">{i + 1}</span>
									<a href="{base}/map?focus={r.stockCode}" class="rank-name">{r.corpName}</a>
									<span class="rank-val pos">{r.roe}%</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
				{#if stats.topGrowth?.length}
					<div class="rank-card">
						<div class="rank-head">
							<span class="rank-icon">📈</span>
							<span class="rank-title">최대 성장 (매출 CAGR)</span>
						</div>
						<ul>
							{#each stats.topGrowth.slice(0, 5) as r, i (r.stockCode)}
								<li>
									<span class="rank-n">{i + 1}</span>
									<a href="{base}/map?focus={r.stockCode}" class="rank-name">{r.corpName}</a>
									<span class="rank-val pos">+{r.revCagr}%</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
				{#if stats.riskFlags?.length}
					<div class="rank-card risk">
						<div class="rank-head">
							<span class="rank-icon">⚠</span>
							<span class="rank-title">위험 신호</span>
						</div>
						<ul>
							{#each stats.riskFlags.slice(0, 5) as r, i (r.stockCode)}
								<li>
									<span class="rank-n">{i + 1}</span>
									<a href="{base}/map?focus={r.stockCode}" class="rank-name">{r.corpName}</a>
									<span class="rank-val neg">
										{r.roe !== null ? `ROE ${r.roe}%` : ''}
										{#if r.debtGrade}· {r.debtGrade}{/if}
									</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		</section>
	{/if}

	<!-- 공급 흐름: 이 산업이 공급하는/받는 산업 Top 5 -->
	{#if stats && (stats.supplyTo?.length || stats.supplyFrom?.length)}
		<section class="sec flows-section">
			<h2>산업 간 공급 흐름</h2>
			<div class="flow-grid">
				{#if stats.supplyTo?.length}
					<div class="flow-col">
						<h3>이 산업이 공급하는 곳</h3>
						<ul>
							{#each stats.supplyTo as f (f.toIndustry)}
								<li>
									<a href="{base}/industry/{f.toIndustry}" class="flow-link">
										{f.toName} <span class="flow-arrow">↗</span>
									</a>
									<span class="flow-stat">{f.edgeCount}건 · {formatAmount(f.amount)}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
				{#if stats.supplyFrom?.length}
					<div class="flow-col">
						<h3>이 산업이 공급 받는 곳</h3>
						<ul>
							{#each stats.supplyFrom as f (f.fromIndustry)}
								<li>
									<a href="{base}/industry/{f.fromIndustry}" class="flow-link">
										↖ {f.fromName}
									</a>
									<span class="flow-stat">{f.edgeCount}건 · {formatAmount(f.amount)}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		</section>
	{/if}

	<!-- 공정 흐름 -->
	{#if stages.length > 0}
		<section class="sec">
			<h2>공정 흐름</h2>
			<div class="flow">
				{#each stages as stage, i}
					<div class="stage-col">
						<div class="stage-header">
							<div class="stage-name">{stage.name}</div>
							<div class="stage-meta">{stage.nodes?.length || 0}사</div>
						</div>
						<ul class="stage-list">
							{#each (stage.nodes || []).slice(0, 8) as n}
								<li>
									<a href="{base}/company/{n.stockCode}" class="stage-company">
										<span class="c-name">{n.corpName}</span>
										<span class="c-rev">{formatRev(n.revenue)}</span>
									</a>
								</li>
							{/each}
							{#if (stage.nodes?.length || 0) > 8}
								<li class="more">+{(stage.nodes?.length || 0) - 8}사 더</li>
							{/if}
						</ul>
					</div>
					{#if i < stages.length - 1}
						<div class="flow-arrow">→</div>
					{/if}
				{/each}
			</div>
		</section>
	{/if}

	<!-- 공정별 랭킹 카드 -->
	{#if stages.length > 0}
		<section class="sec">
			<h2>공정별 톱5</h2>
			<div class="rank-grid">
				{#each stages as stage}
					<div class="rank-card">
						<div class="rank-header">
							<span class="rank-name">{stage.name}</span>
							<span class="rank-count">{stage.nodes?.length || 0}사</span>
						</div>
						<ol class="rank-list">
							{#each (stage.nodes || []).slice(0, 5) as n, i}
								<li>
									<span class="rank-num">{i + 1}</span>
									<a href="{base}/company/{n.stockCode}" class="rank-link">
										<span>{n.corpName}</span>
										<span class="rank-rev">{formatRev(n.revenue)}</span>
									</a>
								</li>
							{/each}
						</ol>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- 정밀 공급망 엣지 top 20 -->
	{#if preciseEdges.length > 0}
		<section class="sec">
			<h2>주요 공급 관계 (거래금액 공개분 {preciseEdges.length}건)</h2>
			<div class="edge-table">
				<table>
					<thead>
						<tr>
							<th>공급사</th>
							<th></th>
							<th>고객사</th>
							<th>품목</th>
							<th class="num">거래금액</th>
						</tr>
					</thead>
					<tbody>
						{#each preciseEdges as e}
							<tr>
								<td>
									<a href="{base}/company/{e.from}" class="e-link">
										{nameMap[e.from] || e.from}
									</a>
								</td>
								<td class="arrow">→</td>
								<td>
									<a href="{base}/company/{e.to}" class="e-link">
										{nameMap[e.to] || e.to}
									</a>
								</td>
								<td class="product">{e.product || '-'}</td>
								<td class="num amount">{formatAmount(e.amount)}원</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
</div>

<style>
	.wrap {
		max-width: 1200px;
		margin: 0 auto;
		padding: 24px 16px;
		background: #050811;
		color: #f1f5f9;
		min-height: 100vh;
	}

	.breadcrumb {
		font-size: 13px;
		color: #94a3b8;
		margin-bottom: 16px;
	}
	.breadcrumb a {
		color: #60a5fa;
		text-decoration: none;
	}
	.breadcrumb a:hover {
		text-decoration: underline;
	}
	.breadcrumb span {
		margin: 0 6px;
	}

	h1 {
		margin: 0 0 16px;
		font-size: 32px;
		color: #f1f5f9;
	}
	h2 {
		font-size: 13px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 12px;
		font-weight: 600;
	}

	.head-top {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 16px;
		flex-wrap: wrap;
		margin-bottom: 16px;
	}

	.stats {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 12px;
		padding: 16px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
	}
	.stat .label {
		font-size: 11px;
		color: #94a3b8;
		margin-bottom: 4px;
	}
	.stat .value {
		font-size: 18px;
		font-weight: 600;
		color: #f1f5f9;
		font-family: monospace;
	}
	.stat .value.pos {
		color: #34d399;
	}
	.stat .value.neg {
		color: #f87171;
	}

	.movers-pill {
		display: inline-block;
		margin-top: 12px;
		padding: 8px 14px;
		background: rgba(251, 191, 36, 0.08);
		border: 1px solid rgba(251, 191, 36, 0.35);
		border-radius: 999px;
		color: #fbbf24;
		text-decoration: none;
		font-size: 12px;
	}
	.movers-pill:hover {
		background: rgba(251, 191, 36, 0.15);
	}
	.movers-pill strong {
		color: #f1f5f9;
	}

	.sec {
		margin-top: 28px;
	}

	/* Top 랭킹 */
	.rank-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 12px;
	}
	.rank-card {
		padding: 14px 16px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 8px;
	}
	.rank-card.risk {
		border-color: rgba(239, 68, 68, 0.3);
	}
	.rank-head {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 10px;
	}
	.rank-icon {
		font-size: 18px;
	}
	.rank-title {
		font-size: 13px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.rank-card ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.rank-card li {
		display: grid;
		grid-template-columns: 20px 1fr auto;
		gap: 8px;
		align-items: center;
		padding: 5px 0;
		border-bottom: 1px dashed #1e2433;
		font-size: 12px;
	}
	.rank-card li:last-child {
		border-bottom: none;
	}
	.rank-n {
		color: #64748b;
		font-family: monospace;
		font-size: 11px;
	}
	.rank-name {
		color: #cbd5e1;
		text-decoration: none;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.rank-name:hover {
		color: #60a5fa;
	}
	.rank-val {
		font-family: monospace;
		font-weight: 600;
	}
	.rank-val.pos {
		color: #34d399;
	}
	.rank-val.neg {
		color: #f87171;
	}

	/* 공급 흐름 */
	.flows-section .flow-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
	}
	.flow-col {
		padding: 14px 16px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 8px;
	}
	.flow-col h3 {
		margin: 0 0 10px;
		font-size: 12px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.flow-col ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.flow-col li {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 6px 0;
		border-bottom: 1px dashed #1e2433;
	}
	.flow-col li:last-child {
		border-bottom: none;
	}
	.flow-link {
		color: #60a5fa;
		text-decoration: none;
		font-size: 13px;
	}
	.flow-link:hover {
		text-decoration: underline;
	}
	.flow-arrow {
		color: #94a3b8;
		font-size: 11px;
	}
	.flow-stat {
		color: #94a3b8;
		font-size: 11px;
		font-family: monospace;
	}

	@media (max-width: 900px) {
		.rank-grid,
		.flows-section .flow-grid {
			grid-template-columns: 1fr;
		}
	}

	/* 공정 흐름 */
	.flow {
		display: flex;
		gap: 4px;
		align-items: stretch;
		overflow-x: auto;
		padding: 16px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
	}
	.stage-col {
		flex: 1;
		min-width: 140px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 8px;
		padding: 10px;
	}
	.stage-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding-bottom: 8px;
		border-bottom: 1px solid #1e2433;
		margin-bottom: 8px;
	}
	.stage-name {
		font-size: 14px;
		font-weight: 600;
		color: #60a5fa;
	}
	.stage-meta {
		font-size: 11px;
		color: #64748b;
	}
	.stage-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.stage-list li {
		padding: 4px 0;
	}
	.stage-company {
		display: flex;
		justify-content: space-between;
		gap: 6px;
		font-size: 12px;
		text-decoration: none;
		color: #cbd5e1;
	}
	.stage-company:hover .c-name {
		color: #60a5fa;
	}
	.c-name {
		color: #f1f5f9;
		font-weight: 500;
	}
	.c-rev {
		color: #fb923c;
		font-size: 10px;
	}
	.more {
		font-size: 11px;
		color: #64748b;
		font-style: italic;
		padding-top: 4px;
	}
	.flow-arrow {
		display: flex;
		align-items: center;
		color: #475569;
		font-size: 18px;
		padding: 0 2px;
	}

	/* 공정별 랭킹 */
	.rank-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 12px;
	}
	.rank-card {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		padding: 14px;
	}
	.rank-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 8px;
	}
	.rank-name {
		font-size: 13px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.rank-count {
		font-size: 11px;
		color: #64748b;
	}
	.rank-list {
		list-style: none;
		padding: 0;
		margin: 0;
		counter-reset: rank;
	}
	.rank-list li {
		display: flex;
		gap: 8px;
		padding: 4px 0;
		font-size: 12px;
		border-bottom: 1px solid #1e2433;
	}
	.rank-list li:last-child {
		border-bottom: none;
	}
	.rank-num {
		color: #475569;
		font-size: 11px;
		width: 16px;
		text-align: right;
	}
	.rank-link {
		display: flex;
		justify-content: space-between;
		flex: 1;
		text-decoration: none;
		color: #cbd5e1;
	}
	.rank-link:hover {
		color: #60a5fa;
	}
	.rank-rev {
		color: #fb923c;
		font-size: 11px;
	}

	/* 엣지 테이블 */
	.edge-table {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		overflow: hidden;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}
	th {
		background: #050811;
		text-align: left;
		padding: 10px 12px;
		color: #94a3b8;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 600;
	}
	th.num,
	td.num {
		text-align: right;
	}
	td {
		padding: 8px 12px;
		border-top: 1px solid #1e2433;
		color: #cbd5e1;
	}
	td.arrow {
		color: #475569;
		text-align: center;
	}
	td.product {
		color: #94a3b8;
		font-size: 12px;
	}
	td.amount {
		color: #fb923c;
		font-weight: 600;
	}
	.e-link {
		color: #f1f5f9;
		text-decoration: none;
	}
	.e-link:hover {
		color: #60a5fa;
	}

	@media (max-width: 768px) {
		.stats {
			grid-template-columns: repeat(2, 1fr);
		}
		h1 {
			font-size: 24px;
		}
		.flow {
			flex-direction: column;
		}
		.flow-arrow {
			transform: rotate(90deg);
			justify-content: center;
		}
	}
</style>
