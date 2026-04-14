<script lang="ts">
	import CompanyEgograph from '$lib/components/CompanyEgograph.svelte';
	import type { PageData } from './$types';
	import { base } from '$app/paths';

	let { data }: { data: PageData } = $props();
	let ego = $derived(data.data.ego);

	function formatRev(v: number): string {
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조원`;
		return `${v.toLocaleString()}억원`;
	}
</script>

<svelte:head>
	<title>{ego.corpName} 산업지도 | dartlab 전자공시</title>
	<meta
		name="description"
		content="{ego.corpName}({data.stockCode})의 산업지도 위치와 공급망 관계. {ego.industry} · {ego.stage || ''} · 매출 {formatRev(ego.revenue)}"
	/>
</svelte:head>

<div class="wrap">
	<nav class="breadcrumb">
		<a href="{base}/map">산업지도</a>
		<span>›</span>
		<span>{ego.industry}</span>
		<span>›</span>
		<span>{ego.corpName}</span>
	</nav>

	<header class="head">
		<h1>{ego.corpName}</h1>
		<div class="meta">
			<span class="badge industry">{ego.industry}</span>
			{#if ego.stage}
				<span class="badge stage">{ego.stage}</span>
			{/if}
			{#if ego.role}
				<span class="badge role">{ego.role}</span>
			{/if}
			<span class="code">{data.stockCode}</span>
		</div>
		<div class="stats">
			<div class="stat">
				<div class="label">매출</div>
				<div class="value">{formatRev(ego.revenue)}</div>
			</div>
			<div class="stat">
				<div class="label">이웃 기업</div>
				<div class="value">{data.data.neighbors.length}사</div>
			</div>
			<div class="stat">
				<div class="label">관계 엣지</div>
				<div class="value">{data.data.edges.length}건</div>
			</div>
			<div class="stat">
				<div class="label">분류 신뢰도</div>
				<div class="value">{(ego.confidence * 100).toFixed(0)}%</div>
			</div>
		</div>
	</header>

	<div class="graph-wrap">
		<CompanyEgograph data={data.data} width={900} height={600} />
	</div>

	<div class="help">
		이웃 노드에 마우스를 올리면 회사 정보, 엣지에 올리면 거래 품목/금액을 볼 수 있다.
		실선은 금액 공개, 점선은 텍스트 매칭. 두께는 거래 규모 비례.
	</div>
</div>

<style>
	.wrap {
		max-width: 1100px;
		margin: 0 auto;
		padding: 24px 16px;
	}

	.breadcrumb {
		font-size: 13px;
		color: #6b7280;
		margin-bottom: 16px;
	}
	.breadcrumb a {
		color: #0ea5e9;
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
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 500;
	}
	.badge.industry {
		background: #dbeafe;
		color: #1e40af;
	}
	.badge.stage {
		background: #dcfce7;
		color: #166534;
	}
	.badge.role {
		background: #fce7f3;
		color: #9d174d;
	}
	.code {
		font-family: monospace;
		color: #9ca3af;
		font-size: 13px;
	}

	.stats {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 12px;
		padding: 16px;
		background: #f9fafb;
		border-radius: 8px;
	}
	.stat .label {
		font-size: 12px;
		color: #6b7280;
		margin-bottom: 4px;
	}
	.stat .value {
		font-size: 20px;
		font-weight: 600;
	}

	.graph-wrap {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 8px;
		margin-bottom: 16px;
	}

	.help {
		font-size: 13px;
		color: #6b7280;
		padding: 12px 16px;
		background: #fffbeb;
		border-left: 3px solid #f59e0b;
		border-radius: 4px;
	}

	@media (max-width: 640px) {
		.stats {
			grid-template-columns: repeat(2, 1fr);
		}
		h1 {
			font-size: 22px;
		}
	}
</style>
