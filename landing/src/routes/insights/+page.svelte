<script lang="ts">
	import type { PageData } from './$types';
	import { base } from '$app/paths';

	let { data }: { data: PageData } = $props();
	let rankings = $derived(data.data.rankings);
	let total = $derived(data.data.totalCompanies);

	let order = [
		'concentrated',
		'diversified',
		'connected',
		'diverseIndustries',
		'dependent',
	];

	function formatRev(v: number): string {
		if (!v) return '-';
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조원`;
		return `${v.toLocaleString()}억원`;
	}

	function hhiColor(hhi: number): string {
		if (hhi >= 2500) return '#f87171';
		if (hhi >= 1500) return '#fb923c';
		if (hhi > 0) return '#34d399';
		return '#64748b';
	}
</script>

<svelte:head>
	<title>인사이트 랭킹 · 공급망 집중도 · 허브 기업 | dartlab 전자공시</title>
	<meta
		name="description"
		content={`한국 상장사 ${total}개 공급망 인사이트 랭킹. 집중도, 분산도, 허브 기업, 의존도 위험.`}
	/>
</svelte:head>

<div class="wrap">
	<nav class="breadcrumb">
		<a href="{base}/map">산업지도</a>
		<span>›</span>
		<span>인사이트 랭킹</span>
	</nav>

	<header class="head">
		<h1>공급망 인사이트 랭킹</h1>
		<p class="sub">상위 {total}사 공시 기반 자동 생성. 주 1회 갱신.</p>
	</header>

	{#each order as key}
		{#if rankings[key]}
			<section class="sec">
				<header class="sec-head">
					<h2>{rankings[key].title}</h2>
					<p class="desc">{rankings[key].description}</p>
				</header>
				<div class="rank-list">
					{#each rankings[key].entries as e, i}
						<a href="{base}/terminal?sym={e.stockCode}" class="rank-item">
							<div class="rank-num">{i + 1}</div>
							<div class="rank-body">
								<div class="rank-name">{e.corpName}</div>
								<div class="rank-meta">
									<span class="industry">{e.industry}</span>
									<span class="sep">·</span>
									<span>{formatRev(e.revenue)}</span>
								</div>
							</div>
							<div class="rank-metric">
								{#if key === 'concentrated' || key === 'diversified'}
									<div class="m-val" style="color: {hhiColor(e.hhi)}">
										HHI {e.hhi.toLocaleString()}
									</div>
									<div class="m-sub">Top3 {e.top3Ratio}%</div>
								{:else if key === 'connected'}
									<div class="m-val">{e.supplierCount + e.customerCount}관계</div>
									<div class="m-sub">공급 {e.supplierCount} · 고객 {e.customerCount}</div>
								{:else if key === 'diverseIndustries'}
									<div class="m-val">{e.industryDiversity}산업</div>
									<div class="m-sub">공급사 {e.supplierCount}사</div>
								{:else if key === 'dependent'}
									<div class="m-val" style="color: #f87171">{e.top1Ratio}%</div>
									<div class="m-sub">단일 공급사 비중</div>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}
	{/each}

	<footer class="foot">
		<a href="{base}/map" class="btn">전체 산업지도 →</a>
	</footer>
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
	.breadcrumb span {
		margin: 0 6px;
	}

	.head {
		margin-bottom: 32px;
	}
	h1 {
		margin: 0 0 6px;
		font-size: 32px;
	}
	.sub {
		margin: 0;
		font-size: 13px;
		color: #94a3b8;
	}

	.sec {
		margin-bottom: 32px;
	}
	.sec-head {
		margin-bottom: 12px;
	}
	h2 {
		margin: 0 0 4px;
		font-size: 16px;
		color: #f1f5f9;
	}
	.desc {
		margin: 0;
		font-size: 12px;
		color: #94a3b8;
	}

	.rank-list {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
		gap: 8px;
	}
	.rank-item {
		display: flex;
		gap: 12px;
		align-items: center;
		padding: 10px 14px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: border-color 0.15s;
	}
	.rank-item:hover {
		border-color: #60a5fa;
	}
	.rank-num {
		font-size: 18px;
		font-weight: 700;
		color: #475569;
		width: 24px;
		text-align: right;
	}
	.rank-body {
		flex: 1;
		min-width: 0;
	}
	.rank-name {
		font-size: 14px;
		font-weight: 600;
		color: #f1f5f9;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.rank-meta {
		font-size: 11px;
		color: #94a3b8;
		margin-top: 2px;
	}
	.industry {
		color: #60a5fa;
	}
	.sep {
		margin: 0 4px;
		color: #475569;
	}
	.rank-metric {
		text-align: right;
	}
	.m-val {
		font-size: 13px;
		font-weight: 700;
		color: #f1f5f9;
	}
	.m-sub {
		font-size: 10px;
		color: #64748b;
		margin-top: 2px;
	}

	.foot {
		margin-top: 24px;
		text-align: center;
	}
	.btn {
		display: inline-block;
		padding: 10px 20px;
		background: #60a5fa;
		color: #050811;
		border-radius: 6px;
		text-decoration: none;
		font-weight: 600;
		font-size: 13px;
	}
	.btn:hover {
		background: #3b82f6;
	}
</style>
