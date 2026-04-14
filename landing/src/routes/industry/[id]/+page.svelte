<script lang="ts">
	import type { PageData } from './$types';
	import { base } from '$app/paths';

	let { data }: { data: PageData } = $props();
	let ind = $derived(data.data);
	let stages = $derived(ind.stages || []);
	let edges = $derived(ind.edges || []);

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

	// 평균 매출
	let avgRev = $derived(
		ind.nodeCount > 0 ? Math.round(ind.totalRevenue / ind.nodeCount) : 0
	);
</script>

<svelte:head>
	<title>{ind.name} 산업지도 · 공정별 · 공급망 | dartlab 전자공시</title>
	<meta
		name="description"
		content={`${ind.name} 산업 ${ind.nodeCount}사의 공정별 구조, 공급망 엣지 ${edges.length}건, 총 매출 ${formatRev(ind.totalRevenue)}`}
	/>
</svelte:head>

<div class="wrap">
	<nav class="breadcrumb">
		<a href="{base}/map">산업지도</a>
		<span>›</span>
		<span>{ind.name}</span>
	</nav>

	<header class="head">
		<h1>{ind.name}</h1>
		<div class="stats">
			<div class="stat">
				<div class="label">기업 수</div>
				<div class="value">{ind.nodeCount}사</div>
			</div>
			<div class="stat">
				<div class="label">총 매출</div>
				<div class="value">{formatRev(ind.totalRevenue)}</div>
			</div>
			<div class="stat">
				<div class="label">평균 매출</div>
				<div class="value">{formatRev(avgRev)}</div>
			</div>
			<div class="stat">
				<div class="label">공급망 엣지</div>
				<div class="value">{edges.length}건</div>
			</div>
		</div>
	</header>

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
		margin-top: 28px;
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
