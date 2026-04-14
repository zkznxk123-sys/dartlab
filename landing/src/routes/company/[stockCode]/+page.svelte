<script lang="ts">
	import CompanyEgograph from '$lib/components/CompanyEgograph.svelte';
	import AIInsightBox from '$lib/components/industry/AIInsightBox.svelte';
	import SupplyInsightCard from '$lib/components/industry/SupplyInsightCard.svelte';
	import FinancialsTrend from '$lib/components/industry/FinancialsTrend.svelte';
	import RelatedPostList from '$lib/components/industry/RelatedPostList.svelte';
	import type { PageData } from './$types';
	import { base } from '$app/paths';

	let { data }: { data: PageData } = $props();
	let ego = $derived(data.data.ego);
	let supplyInsights = $derived(data.data.supplyInsights);
	let aiInsight = $derived(data.data.aiInsight);
	let blogPosts = $derived(data.data.blogPosts || []);
	let financials5y = $derived(data.data.financials5y || []);
	let suppliers = $derived(data.data.suppliers || []);
	let customers = $derived(data.data.customers || []);
	let peers = $derived(data.data.peers || []);
	let topBlog = $derived(blogPosts[0] || null);

	function formatRev(v: number): string {
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조원`;
		return `${v.toLocaleString()}억원`;
	}

	function formatAmountRaw(v: number | null | undefined): string {
		if (!v) return '-';
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조`;
		return `${v.toLocaleString()}억`;
	}
</script>

<svelte:head>
	<title>{ego.corpName} ({data.stockCode}) · 산업지도 · 공급망 | dartlab 전자공시</title>
	<meta
		name="description"
		content={aiInsight?.narrative?.slice(0, 160) ||
			topBlog?.verdict ||
			`${ego.corpName}(${data.stockCode})의 산업 생태계 위치, 공급망 관계, 재무 추이. ${ego.industry} · ${ego.stage || ''} · 매출 ${formatRev(ego.revenue)}`}
	/>
</svelte:head>

<div class="wrap">
	<nav class="breadcrumb">
		<a href="{base}/map">산업지도</a>
		<span>›</span>
		<span>{ego.corpName}</span>
	</nav>

	<!-- 헤더 -->
	<header class="head">
		<h1>{ego.corpName}</h1>
		<div class="meta">
			<span class="badge industry">{ego.industry}</span>
			{#if ego.stage}<span class="badge stage">{ego.stage}</span>{/if}
			{#if ego.role}<span class="badge role">{ego.role}</span>{/if}
			<span class="code">{data.stockCode}</span>
		</div>
		<div class="stats">
			<div class="stat">
				<div class="label">매출</div>
				<div class="value">{formatRev(ego.revenue)}</div>
			</div>
			<div class="stat">
				<div class="label">공급 관계</div>
				<div class="value">{supplyInsights?.supplierCount || 0}사</div>
			</div>
			<div class="stat">
				<div class="label">이웃 기업</div>
				<div class="value">{data.data.neighbors.length}사</div>
			</div>
			<div class="stat">
				<div class="label">분류 신뢰도</div>
				<div class="value">{(ego.confidence * 100).toFixed(0)}%</div>
			</div>
		</div>
	</header>

	<!-- AI 인사이트 -->
	{#if aiInsight || topBlog}
		<section class="sec">
			<AIInsightBox insight={aiInsight} blogVerdict={topBlog} />
		</section>
	{/if}

	<!-- 공급망 인사이트 -->
	{#if supplyInsights && supplyInsights.supplierCount > 0}
		<section class="sec">
			<h2>공급망 인사이트</h2>
			<SupplyInsightCard data={supplyInsights} />
		</section>
	{/if}

	<!-- 공급망 그래프 -->
	<section class="sec">
		<h2>공급망 네트워크</h2>
		<div class="graph-wrap">
			<CompanyEgograph data={data.data} width={900} height={500} />
		</div>
	</section>

	<!-- 공급사/고객사 리스트 -->
	{#if suppliers.length || customers.length}
		<section class="sec relations">
			{#if suppliers.length}
				<div class="rel-box">
					<h3>주요 공급사 ({suppliers.length})</h3>
					<ul>
						{#each suppliers as s}
							<li>
								<a href="{base}/company/{s.stockCode}" class="rel-link">
									<span class="rel-name">{s.corpName}</span>
									{#if s.product}<span class="rel-product">· {s.product}</span>{/if}
									{#if s.amount}
										<span class="rel-amount">{formatAmountRaw(s.amount)}원</span>
										{#if s.ratio}<span class="rel-ratio">({s.ratio}%)</span>{/if}
									{/if}
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
			{#if customers.length}
				<div class="rel-box">
					<h3>관계사 · 고객사 ({customers.length})</h3>
					<ul>
						{#each customers as c}
							<li>
								<a href="{base}/company/{c.stockCode}" class="rel-link">
									<span class="rel-name">{c.corpName}</span>
									{#if c.product}<span class="rel-product">· {c.product}</span>{/if}
									{#if c.amount}
										<span class="rel-amount">{formatAmountRaw(c.amount)}원</span>
									{/if}
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</section>
	{/if}

	<!-- 재무 5년 -->
	{#if financials5y.length >= 2}
		<section class="sec">
			<FinancialsTrend data={financials5y} />
		</section>
	{/if}

	<!-- 동종사 비교 -->
	{#if peers.length}
		<section class="sec">
			<h2>같은 산업 {peers.length}사</h2>
			<div class="peer-grid">
				{#each peers as p}
					<a href="{base}/company/{p.stockCode}" class="peer-card">
						<div class="peer-name">{p.corpName}</div>
						{#if p.stage}<div class="peer-stage">{p.stage}</div>{/if}
						<div class="peer-rev">{p.revenue.toLocaleString()}억원</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}

	<!-- 관련 블로그 -->
	{#if blogPosts.length}
		<section class="sec">
			<RelatedPostList posts={blogPosts} />
		</section>
	{/if}
</div>

<style>
	.wrap {
		max-width: 1100px;
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

	.head {
		margin-bottom: 24px;
	}
	h1 {
		margin: 0 0 8px;
		font-size: 28px;
		color: #f1f5f9;
	}
	h2 {
		font-size: 15px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 12px;
		font-weight: 600;
	}
	.meta {
		display: flex;
		gap: 8px;
		align-items: center;
		margin-bottom: 16px;
		flex-wrap: wrap;
	}
	.badge {
		display: inline-block;
		padding: 3px 10px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 500;
	}
	.badge.industry {
		background: rgba(96, 165, 250, 0.15);
		color: #60a5fa;
	}
	.badge.stage {
		background: rgba(52, 211, 153, 0.15);
		color: #34d399;
	}
	.badge.role {
		background: rgba(236, 72, 153, 0.15);
		color: #f472b6;
	}
	.code {
		font-family: monospace;
		color: #64748b;
		font-size: 13px;
	}

	.stats {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
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
		font-size: 20px;
		font-weight: 600;
		color: #f1f5f9;
	}

	.sec {
		margin-bottom: 28px;
	}

	.graph-wrap {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		padding: 8px;
	}

	.relations {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
	}
	.rel-box {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		padding: 16px;
	}
	.rel-box h3 {
		font-size: 13px;
		color: #94a3b8;
		margin: 0 0 10px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.rel-box ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.rel-box li {
		padding: 6px 0;
		border-bottom: 1px solid #1e2433;
	}
	.rel-box li:last-child {
		border-bottom: none;
	}
	.rel-link {
		display: flex;
		gap: 6px;
		font-size: 13px;
		text-decoration: none;
		color: #cbd5e1;
		flex-wrap: wrap;
	}
	.rel-link:hover .rel-name {
		color: #60a5fa;
	}
	.rel-name {
		font-weight: 600;
		color: #f1f5f9;
	}
	.rel-product {
		color: #94a3b8;
		font-size: 11px;
	}
	.rel-amount {
		color: #fb923c;
		font-weight: 600;
		margin-left: auto;
	}
	.rel-ratio {
		color: #64748b;
		font-size: 11px;
	}

	.peer-grid {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: 10px;
	}
	.peer-card {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 8px;
		padding: 12px;
		text-decoration: none;
		transition: border-color 0.2s;
	}
	.peer-card:hover {
		border-color: #ea4647;
	}
	.peer-name {
		font-size: 13px;
		font-weight: 600;
		color: #f1f5f9;
		margin-bottom: 4px;
	}
	.peer-stage {
		font-size: 10px;
		color: #34d399;
		margin-bottom: 4px;
	}
	.peer-rev {
		font-size: 11px;
		color: #fb923c;
	}

	@media (max-width: 768px) {
		.stats {
			grid-template-columns: repeat(2, 1fr);
		}
		.relations {
			grid-template-columns: 1fr;
		}
		.peer-grid {
			grid-template-columns: repeat(2, 1fr);
		}
		h1 {
			font-size: 22px;
		}
	}
</style>
