<script lang="ts">
	import EcosystemMap from '$lib/components/industry/EcosystemMap.svelte';
	import type { PageData } from './$types';
	import { base } from '$app/paths';

	let { data }: { data: PageData } = $props();

	let allNodes = $derived(data.ecosystem.nodes);
	let allLinks = $derived(data.ecosystem.links);
	let industries = $derived(data.ecosystem.industries);

	// 필터 상태 — 초기에는 모든 산업 활성화
	let enabledIndustries = $state<Set<string>>(new Set());
	let initialized = $state(false);
	$effect(() => {
		if (!initialized && data?.ecosystem?.industries) {
			enabledIndustries = new Set(data.ecosystem.industries.map((i: any) => i.id));
			initialized = true;
		}
	});
	let showSupplier = $state(true);
	let showAffiliate = $state(false);
	let showInvestor = $state(false);
	let minConfidence = $state(0.6);
	let onlyWithAmount = $state(false);
	let searchQuery = $state('');

	// 선택된 노드 (상세 패널)
	let selectedNode: any = $state(null);
	let mapRef: any = $state(null);

	// 필터링된 데이터
	let filteredNodes = $derived(
		allNodes.filter((n: any) => enabledIndustries.has(n.industry))
	);

	let filteredLinks = $derived(
		allLinks.filter((l: any) => {
			if (l.type === 'supplier' && !showSupplier) return false;
			if (l.type === 'affiliate' && !showAffiliate) return false;
			if (l.type === 'investor' && !showInvestor) return false;
			if (l.type === 'customer' && !showSupplier) return false;
			if (l.confidence < minConfidence) return false;
			if (onlyWithAmount && !l.amount) return false;
			return true;
		})
	);

	// 선택된 회사의 관계
	let selectedRelations = $derived.by(() => {
		if (!selectedNode) return { suppliers: [], customers: [] };
		const id = selectedNode.id;
		const nodeById = new Map(allNodes.map((n: any) => [n.id, n]));
		const suppliers: any[] = [];
		const customers: any[] = [];
		for (const l of allLinks) {
			if (l.target === id && l.type === 'supplier') {
				const from = nodeById.get(l.source);
				if (from) suppliers.push({ ...l, partner: from });
			}
			if (l.source === id && (l.type === 'customer' || l.type === 'supplier')) {
				const to = nodeById.get(l.target);
				if (to) customers.push({ ...l, partner: to });
			}
		}
		return { suppliers, customers };
	});

	function toggleIndustry(id: string) {
		const next = new Set(enabledIndustries);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		enabledIndustries = next;
	}

	function toggleAllIndustries(on: boolean) {
		enabledIndustries = on ? new Set(industries.map((i: any) => i.id)) : new Set();
	}

	function handleNodeClick(node: any) {
		selectedNode = node;
	}

	function formatRev(rev: number): string {
		if (rev >= 1e12) return `${(rev / 1e12).toFixed(1)}조원`;
		return `${Math.round(rev / 1e8).toLocaleString()}억원`;
	}

	function handleSearch() {
		if (!searchQuery.trim()) return;
		const q = searchQuery.toLowerCase();
		const match = allNodes.find(
			(n: any) => n.label.includes(searchQuery) || n.id === searchQuery || n.label.toLowerCase().includes(q)
		);
		if (match && mapRef) {
			mapRef.zoomToNode(match.id);
			selectedNode = match;
		}
	}
</script>

<svelte:head>
	<title>산업지도 | dartlab 전자공시</title>
	<meta
		name="description"
		content="한국 상장사 2,664사 산업 생태계 지도. 공급망·매출·공정을 한눈에."
	/>
</svelte:head>

<div class="map-page">
	<!-- 왼쪽 필터 -->
	<aside class="sidebar">
		<div class="header">
			<h1>산업 생태계</h1>
			<p class="sub">
				{filteredNodes.length.toLocaleString()}사 · {filteredLinks.length.toLocaleString()}관계
			</p>
		</div>

		<!-- 검색 -->
		<div class="section">
			<input
				type="text"
				bind:value={searchQuery}
				onkeydown={(e) => e.key === 'Enter' && handleSearch()}
				placeholder="회사명/종목코드 검색..."
				class="search"
			/>
		</div>

		<!-- 엣지 타입 -->
		<div class="section">
			<h3>관계 유형</h3>
			<label class="check"><input type="checkbox" bind:checked={showSupplier} /> <span class="dot supplier"></span>공급</label>
			<label class="check"><input type="checkbox" bind:checked={showAffiliate} /> <span class="dot affiliate"></span>계열</label>
			<label class="check"><input type="checkbox" bind:checked={showInvestor} /> <span class="dot investor"></span>투자</label>
		</div>

		<!-- 품질 -->
		<div class="section">
			<h3>품질 필터</h3>
			<label class="range">
				신뢰도 ≥ {minConfidence.toFixed(1)}
				<input type="range" bind:value={minConfidence} min="0" max="1" step="0.1" />
			</label>
			<label class="check">
				<input type="checkbox" bind:checked={onlyWithAmount} />
				금액 공개 엣지만
			</label>
		</div>

		<!-- 산업 토글 -->
		<div class="section industries">
			<h3>
				산업
				<span class="controls">
					<button onclick={() => toggleAllIndustries(true)}>전체</button>
					<button onclick={() => toggleAllIndustries(false)}>해제</button>
				</span>
			</h3>
			<ul>
				{#each industries as ind}
					<li>
						<label class="check industry-item">
							<input
								type="checkbox"
								checked={enabledIndustries.has(ind.id)}
								onchange={() => toggleIndustry(ind.id)}
							/>
							<span class="swatch" style="background:{ind.color}"></span>
							<span class="name">{ind.name}</span>
							<span class="count">{ind.count}</span>
						</label>
					</li>
				{/each}
			</ul>
		</div>
	</aside>

	<!-- 메인 지도 -->
	<main class="map-main">
		<EcosystemMap
			bind:this={mapRef}
			nodes={filteredNodes}
			links={filteredLinks}
			onNodeClick={handleNodeClick}
		/>
	</main>

	<!-- 오른쪽 상세 -->
	{#if selectedNode}
		<aside class="detail">
			<button class="close" onclick={() => (selectedNode = null)}>✕</button>
			<div class="detail-head">
				<h2>{selectedNode.label}</h2>
				<p class="code">{selectedNode.id}</p>
				<div class="badges">
					<span class="badge" style="background:{selectedNode.color}20; color:{selectedNode.color}">
						{selectedNode.industryName}
					</span>
					{#if selectedNode.stage}
						<span class="badge stage-badge">{selectedNode.stage}</span>
					{/if}
				</div>
				{#if selectedNode.revenue > 0}
					<div class="big-stat">
						<span class="label">매출</span>
						<span class="value">{formatRev(selectedNode.revenue)}</span>
					</div>
				{/if}
			</div>

			{#if selectedRelations.suppliers.length > 0}
				<div class="section">
					<h3>공급사 ({selectedRelations.suppliers.length})</h3>
					<ul class="rel-list">
						{#each selectedRelations.suppliers.slice(0, 10) as rel}
							<li>
								<div class="rel-partner">
									<strong>{rel.partner.label}</strong>
									{#if rel.product}
										<span class="product">· {rel.product}</span>
									{/if}
								</div>
								{#if rel.amount}
									<div class="rel-amount">
										{rel.amount.toLocaleString()}억원
										{#if rel.ratio}<span class="ratio">({rel.ratio}%)</span>{/if}
									</div>
								{/if}
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if selectedRelations.customers.length > 0}
				<div class="section">
					<h3>고객/관련사 ({selectedRelations.customers.length})</h3>
					<ul class="rel-list">
						{#each selectedRelations.customers.slice(0, 10) as rel}
							<li>
								<div class="rel-partner">
									<strong>{rel.partner.label}</strong>
									{#if rel.product}<span class="product">· {rel.product}</span>{/if}
								</div>
								{#if rel.amount}
									<div class="rel-amount">{rel.amount.toLocaleString()}억원</div>
								{/if}
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<div class="section">
				<a href="{base}/company/{selectedNode.id}" class="full-link">
					전체 페이지 보기 →
				</a>
			</div>
		</aside>
	{/if}
</div>

<style>
	.map-page {
		display: grid;
		grid-template-columns: 280px 1fr;
		height: calc(100vh - 64px);
		background: #050811;
		color: #f1f5f9;
	}

	.sidebar {
		overflow-y: auto;
		background: #0f1219;
		border-right: 1px solid #1e2433;
		padding: 16px;
		color: #f1f5f9;
	}
	.header h1 {
		margin: 0 0 4px;
		font-size: 18px;
		color: #f1f5f9;
	}
	.header .sub {
		margin: 0;
		font-size: 12px;
		color: #94a3b8;
	}

	.section {
		margin-top: 16px;
		padding-top: 16px;
		border-top: 1px solid #1e2433;
	}
	.section:first-of-type {
		border-top: none;
	}
	.section h3 {
		font-size: 11px;
		font-weight: 600;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 8px;
		display: flex;
		justify-content: space-between;
	}
	.controls button {
		font-size: 10px;
		padding: 2px 6px;
		background: #1e2433;
		color: #94a3b8;
		border: none;
		border-radius: 3px;
		cursor: pointer;
		margin-left: 4px;
	}
	.controls button:hover {
		background: #2a3142;
		color: #f1f5f9;
	}

	.search {
		width: 100%;
		padding: 8px 12px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		font-size: 13px;
		color: #f1f5f9;
	}
	.search::placeholder {
		color: #64748b;
	}

	.check {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		padding: 4px 0;
		cursor: pointer;
		color: #cbd5e1;
	}
	.check input {
		margin: 0;
	}
	.dot {
		width: 12px;
		height: 3px;
		border-radius: 2px;
	}
	.dot.supplier {
		background: #f97316;
	}
	.dot.affiliate {
		background: #d1d5db;
	}
	.dot.investor {
		background: #8b5cf6;
	}

	.range {
		display: block;
		font-size: 12px;
		color: #cbd5e1;
		margin-bottom: 8px;
	}
	.range input {
		width: 100%;
		margin-top: 4px;
	}

	.industries ul {
		list-style: none;
		padding: 0;
		margin: 0;
		max-height: 400px;
		overflow-y: auto;
	}
	.industry-item {
		padding: 3px 0;
	}
	.swatch {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.industry-item .name {
		flex: 1;
	}
	.industry-item .count {
		font-size: 11px;
		color: #64748b;
	}

	.map-main {
		position: relative;
		overflow: hidden;
	}

	.detail {
		position: fixed;
		top: 64px;
		right: 0;
		width: 360px;
		height: calc(100vh - 64px);
		background: #0f1219;
		border-left: 1px solid #1e2433;
		padding: 16px;
		overflow-y: auto;
		box-shadow: -4px 0 12px rgba(0, 0, 0, 0.5);
		color: #f1f5f9;
	}
	.close {
		position: absolute;
		top: 12px;
		right: 12px;
		background: none;
		border: none;
		font-size: 18px;
		cursor: pointer;
		color: #64748b;
	}
	.close:hover {
		color: #f1f5f9;
	}
	.detail-head h2 {
		margin: 0;
		font-size: 20px;
		color: #f1f5f9;
	}
	.code {
		margin: 2px 0 8px;
		font-family: monospace;
		color: #64748b;
		font-size: 12px;
	}
	.badges {
		display: flex;
		gap: 6px;
		margin-bottom: 12px;
	}
	.badge {
		font-size: 11px;
		padding: 2px 8px;
		border-radius: 4px;
		font-weight: 500;
	}
	.stage-badge {
		background: rgba(52, 211, 153, 0.15);
		color: #34d399;
	}
	.big-stat {
		background: #050811;
		padding: 12px;
		border-radius: 8px;
		margin-bottom: 12px;
		border: 1px solid #1e2433;
	}
	.big-stat .label {
		font-size: 11px;
		color: #94a3b8;
		display: block;
		margin-bottom: 4px;
	}
	.big-stat .value {
		font-size: 20px;
		font-weight: 600;
		color: #f1f5f9;
	}

	.rel-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.rel-list li {
		padding: 8px 0;
		border-bottom: 1px solid #1e2433;
	}
	.rel-list li:last-child {
		border-bottom: none;
	}
	.rel-partner {
		font-size: 13px;
		color: #cbd5e1;
	}
	.rel-partner strong {
		color: #f1f5f9;
	}
	.rel-partner .product {
		color: #94a3b8;
		font-size: 11px;
	}
	.rel-amount {
		font-size: 12px;
		color: #fb923c;
		margin-top: 2px;
	}
	.rel-amount .ratio {
		color: #64748b;
		font-size: 10px;
	}
	.full-link {
		display: inline-block;
		margin-top: 8px;
		color: #60a5fa;
		text-decoration: none;
		font-size: 13px;
	}
	.full-link:hover {
		text-decoration: underline;
	}

	@media (max-width: 768px) {
		.map-page {
			grid-template-columns: 1fr;
		}
		.sidebar {
			display: none;
		}
		.detail {
			width: 100%;
			top: auto;
			bottom: 0;
			height: 50vh;
			border-left: none;
			border-top: 1px solid #e5e7eb;
		}
	}
</style>
