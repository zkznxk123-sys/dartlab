<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import FreshnessBadge from '$lib/components/industry/FreshnessBadge.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	/**
	 * 쿼리 조건:
	 * - 산업(industry): 여러 개 선택 (OR)
	 * - 수치 필터: {metric, op, value} 배열 (AND)
	 *   op: '>=' | '<=' | '==' | '!='
	 * - 정렬: metric + 방향
	 */
	type Op = '>=' | '<=' | '==' | '!=';
	interface Cond {
		metric: string;
		op: Op;
		value: number;
	}

	const METRICS = [
		{ key: 'revenue', label: '매출(원)' },
		{ key: 'roe', label: 'ROE (%)' },
		{ key: 'opMargin', label: '영업이익률 (%)' },
		{ key: 'debtRatio', label: '부채비율 (%)' },
		{ key: 'revCagr', label: '매출 CAGR 3Y (%)' },
		{ key: 'revenueYoyPct', label: '매출 YoY (%)' },
		{ key: 'roeDelta', label: 'ROE YoY (%p)' },
		{ key: 'marketShare', label: '산업 점유율 (%)' },
		{ key: 'confidence', label: '분류 신뢰도' }
	] as const;

	const OPS: { v: Op; label: string }[] = [
		{ v: '>=', label: '이상' },
		{ v: '<=', label: '이하' },
		{ v: '==', label: '같음' },
		{ v: '!=', label: '다름' }
	];

	let selectedIndustries = $state<Set<string>>(new Set());
	let conds: Cond[] = $state([{ metric: 'roe', op: '>=', value: 10 }]);
	let sortBy = $state<string>('revenue');
	let sortDir: 'asc' | 'desc' = $state('desc');

	const nodes = $derived((data as any).ecosystem.nodes as any[]);
	const industries = $derived((data as any).ecosystem.industries as any[]);

	// URL 직렬화: ?q=base64(JSON)
	function encodeQuery() {
		const payload = {
			i: [...selectedIndustries],
			c: conds,
			s: sortBy,
			d: sortDir
		};
		return btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
	}

	function decodeQuery(q: string) {
		try {
			const json = decodeURIComponent(escape(atob(q)));
			const p = JSON.parse(json);
			if (Array.isArray(p.i)) selectedIndustries = new Set(p.i);
			if (Array.isArray(p.c)) conds = p.c;
			if (p.s) sortBy = p.s;
			if (p.d) sortDir = p.d;
		} catch {
			/* ignore bad query */
		}
	}

	function addCond() {
		conds = [...conds, { metric: 'opMargin', op: '>=', value: 10 }];
	}
	function removeCond(i: number) {
		conds = conds.filter((_, idx) => idx !== i);
	}
	function toggleIndustry(id: string) {
		const next = new Set(selectedIndustries);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedIndustries = next;
	}

	// 필터 적용
	const results = $derived.by(() => {
		let out = nodes;
		if (selectedIndustries.size > 0) {
			out = out.filter((n) => selectedIndustries.has(n.industry));
		}
		for (const c of conds) {
			out = out.filter((n) => {
				const v = n[c.metric];
				if (v === null || v === undefined || isNaN(v)) return false;
				if (c.op === '>=') return v >= c.value;
				if (c.op === '<=') return v <= c.value;
				if (c.op === '==') return Math.abs(v - c.value) < 0.01;
				if (c.op === '!=') return Math.abs(v - c.value) >= 0.01;
				return true;
			});
		}
		// 정렬
		const sorted = [...out].sort((a, b) => {
			const va = a[sortBy];
			const vb = b[sortBy];
			if (va === null || va === undefined) return 1;
			if (vb === null || vb === undefined) return -1;
			return sortDir === 'desc' ? vb - va : va - vb;
		});
		return sorted;
	});

	function copyCsv() {
		const cols = ['stockCode', 'label', 'industryName', 'revenue', 'roe', 'opMargin', 'debtRatio', 'revCagr', 'revenueYoyPct'];
		const header = cols.join(',');
		const rows = results.slice(0, 500).map((n) =>
			cols.map((c) => {
				const v = n[c];
				if (v === null || v === undefined) return '';
				if (typeof v === 'string') return `"${v.replace(/"/g, '""')}"`;
				return v;
			}).join(',')
		);
		const csv = header + '\n' + rows.join('\n');
		navigator.clipboard.writeText(csv);
	}

	function shareUrl() {
		const q = encodeQuery();
		const url = `${window.location.origin}${base}/map/screen?q=${q}`;
		navigator.clipboard.writeText(url);
	}

	onMount(() => {
		const q = page.url.searchParams.get('q');
		if (q) decodeQuery(q);
	});

	function fmt(v: any, metric: string): string {
		if (v === null || v === undefined || isNaN(v)) return '-';
		if (metric === 'revenue') {
			if (v >= 1e12) return `${(v / 1e12).toFixed(1)}조`;
			return `${Math.round(v / 1e8).toLocaleString()}억`;
		}
		if (metric === 'marketShare' || metric === 'confidence') return `${v.toFixed(2)}`;
		if (typeof v === 'number') return `${v > 0 && metric.includes('Delta') ? '+' : ''}${v.toFixed(1)}`;
		return String(v);
	}
</script>

<svelte:head>
	<title>조건 검색 (스크리너) | dartlab 전자공시</title>
	<meta
		name="description"
		content="한국 상장사 2,664사를 ROE·영업이익률·부채·성장률·산업 조건으로 필터링. 결과 공유 URL · CSV export."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:title" content="조건 검색 스크리너 — dartlab" />
	<meta
		property="og:description"
		content="산업 × ROE × 영업이익률 × 부채 × 성장률 다중 조건. URL 공유 · CSV."
	/>
	<meta property="og:image" content="https://eddmpython.github.io/dartlab/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
</svelte:head>

<div class="page">
	<header class="head">
		<div class="head-left">
			<a class="back" href="{base}/map">← 산업지도</a>
			<h1>조건 검색 (스크리너)</h1>
			<p class="lead">
				한국 상장사 2,664사를 <strong>재무 조건 + 산업</strong>으로 필터. URL 복사로 공유 · CSV 로
				내보내기.
			</p>
		</div>
		{#if (data as any).meta?.dataAsOf}
			<FreshnessBadge dataAsOf={(data as any).meta.dataAsOf} variant="compact" />
		{/if}
	</header>

	<div class="builder">
		<!-- 산업 필터 -->
		<div class="block">
			<div class="block-title">산업 (다중 선택 · 비워두면 전체)</div>
			<div class="inds">
				{#each industries as ind (ind.id)}
					<label class="ind-pill" class:on={selectedIndustries.has(ind.id)}>
						<input type="checkbox" checked={selectedIndustries.has(ind.id)} onchange={() => toggleIndustry(ind.id)} />
						<span class="dot" style:background={ind.color}></span>
						<span class="ind-name">{ind.name}</span>
						<span class="ind-count">{ind.count}</span>
					</label>
				{/each}
			</div>
		</div>

		<!-- 조건 행 -->
		<div class="block">
			<div class="block-title">
				수치 조건 (AND)
				<button class="add-btn" onclick={addCond}>+ 조건 추가</button>
			</div>
			<div class="conds">
				{#each conds as c, i (i)}
					<div class="cond-row">
						<select bind:value={c.metric}>
							{#each METRICS as m (m.key)}
								<option value={m.key}>{m.label}</option>
							{/each}
						</select>
						<select bind:value={c.op}>
							{#each OPS as o (o.v)}
								<option value={o.v}>{o.label}</option>
							{/each}
						</select>
						<input type="number" bind:value={c.value} step="any" />
						<button class="cond-x" onclick={() => removeCond(i)} aria-label="제거">✕</button>
					</div>
				{/each}
			</div>
		</div>

		<!-- 정렬 -->
		<div class="block">
			<div class="block-title">정렬</div>
			<div class="sort-row">
				<select bind:value={sortBy}>
					{#each METRICS as m (m.key)}
						<option value={m.key}>{m.label}</option>
					{/each}
				</select>
				<select bind:value={sortDir}>
					<option value="desc">내림차순 (큰 값부터)</option>
					<option value="asc">오름차순 (작은 값부터)</option>
				</select>
			</div>
		</div>
	</div>

	<!-- 결과 요약 + 액션 -->
	<div class="result-bar">
		<div class="result-count">
			결과: <strong>{results.length.toLocaleString()}</strong>사
			<span class="result-note">
				{results.length > 500 ? '(상위 500사만 표시/CSV)' : ''}
			</span>
		</div>
		<div class="result-actions">
			<button onclick={shareUrl}>🔗 이 조건 URL 복사</button>
			<button onclick={copyCsv}>📋 CSV 복사</button>
		</div>
	</div>

	<!-- 결과 테이블 -->
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>회사</th>
					<th>산업</th>
					<th class="num">매출</th>
					<th class="num">ROE</th>
					<th class="num">영업이익률</th>
					<th class="num">부채비율</th>
					<th class="num">CAGR 3Y</th>
					<th class="num">매출 YoY</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				{#each results.slice(0, 500) as n (n.id)}
					<tr>
						<td>
							<div class="cell-main">
								<a href="{base}/map?focus={n.id}" class="name">{n.label}</a>
								<span class="code">{n.id}</span>
							</div>
						</td>
						<td>
							<a href="{base}/industry/{n.industry}" class="ind-link">{n.industryName}</a>
						</td>
						<td class="num">{fmt(n.revenue, 'revenue')}</td>
						<td class="num" style:color={n.roe > 10 ? '#34d399' : n.roe < 0 ? '#f87171' : '#cbd5e1'}>
							{fmt(n.roe, 'roe')}%
						</td>
						<td class="num" style:color={n.opMargin > 10 ? '#34d399' : n.opMargin < 0 ? '#f87171' : '#cbd5e1'}>
							{fmt(n.opMargin, 'opMargin')}%
						</td>
						<td class="num" style:color={n.debtRatio > 200 ? '#f87171' : n.debtRatio < 100 ? '#34d399' : '#cbd5e1'}>
							{fmt(n.debtRatio, 'debtRatio')}%
						</td>
						<td class="num" style:color={n.revCagr > 10 ? '#34d399' : n.revCagr < 0 ? '#f87171' : '#cbd5e1'}>
							{fmt(n.revCagr, 'revCagr')}%
						</td>
						<td class="num" style:color={n.revenueYoyPct > 20 ? '#34d399' : n.revenueYoyPct < -10 ? '#f87171' : '#cbd5e1'}>
							{fmt(n.revenueYoyPct, 'revenueYoyPct')}%
						</td>
						<td>
							<a href="{base}/map?focus={n.id}" class="open">→</a>
						</td>
					</tr>
				{/each}
				{#if results.length === 0}
					<tr><td colspan="9" class="empty">조건에 맞는 회사가 없습니다.</td></tr>
				{/if}
			</tbody>
		</table>
	</div>

	<div class="disclaimer">
		필터 결과는 scan 사전 계산값 기준. 일부 회사는 데이터 누락(null) 시 조건에서 자동 제외.
		투자 자문 아닙니다. 원본 공시 확인 필수.
	</div>
</div>

<style>
	.page {
		max-width: 1400px;
		margin: 0 auto;
		padding: 32px 24px 80px;
		color: #f1f5f9;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 24px;
		margin-bottom: 24px;
	}
	.back {
		color: #60a5fa;
		text-decoration: none;
		font-size: 12px;
	}
	.back:hover {
		text-decoration: underline;
	}
	.head h1 {
		margin: 6px 0 6px;
		font-size: 28px;
	}
	.lead {
		margin: 0;
		font-size: 14px;
		color: #cbd5e1;
	}
	.lead strong {
		color: #f1f5f9;
	}

	.builder {
		display: grid;
		gap: 16px;
		padding: 18px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		margin-bottom: 16px;
	}
	.block-title {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 11px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-weight: 600;
		margin-bottom: 10px;
	}
	.add-btn {
		padding: 4px 10px;
		background: #1e2433;
		border: 1px solid #334155;
		color: #60a5fa;
		font-size: 11px;
		border-radius: 4px;
		cursor: pointer;
	}
	.add-btn:hover {
		background: #2a3142;
	}

	.inds {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.ind-pill {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 4px 10px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 999px;
		cursor: pointer;
		font-size: 12px;
		color: #cbd5e1;
	}
	.ind-pill:hover {
		border-color: #334155;
	}
	.ind-pill.on {
		background: rgba(96, 165, 250, 0.1);
		border-color: rgba(96, 165, 250, 0.5);
		color: #f1f5f9;
	}
	.ind-pill input {
		display: none;
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	.ind-count {
		font-size: 10px;
		color: #64748b;
		font-family: monospace;
	}

	.conds {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.cond-row {
		display: grid;
		grid-template-columns: 1fr 100px 140px 28px;
		gap: 6px;
		align-items: center;
	}
	.cond-row select,
	.cond-row input {
		padding: 6px 10px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 4px;
		color: #f1f5f9;
		font-size: 13px;
		font-family: inherit;
	}
	.cond-row input {
		font-family: monospace;
	}
	.cond-x {
		background: none;
		border: 1px solid #1e2433;
		border-radius: 4px;
		color: #64748b;
		cursor: pointer;
	}
	.cond-x:hover {
		color: #f87171;
		border-color: rgba(239, 68, 68, 0.4);
	}

	.sort-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
	}
	.sort-row select {
		padding: 6px 10px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 4px;
		color: #f1f5f9;
		font-size: 13px;
	}

	.result-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 8px;
	}
	.result-count strong {
		color: #60a5fa;
		font-family: monospace;
	}
	.result-note {
		font-size: 11px;
		color: #64748b;
		margin-left: 8px;
	}
	.result-actions button {
		padding: 6px 12px;
		background: #1e2433;
		border: 1px solid #334155;
		border-radius: 6px;
		color: #cbd5e1;
		font-size: 12px;
		cursor: pointer;
		margin-left: 6px;
	}
	.result-actions button:hover {
		background: #2a3142;
		color: #f1f5f9;
	}

	.table-wrap {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 8px;
		overflow-x: auto;
		max-height: 70vh;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}
	thead th {
		padding: 10px 12px;
		text-align: left;
		color: #94a3b8;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		background: #050811;
		border-bottom: 1px solid #1e2433;
		position: sticky;
		top: 0;
	}
	thead th.num {
		text-align: right;
	}
	tbody td {
		padding: 8px 12px;
		border-bottom: 1px solid #1e2433;
	}
	tbody td.num {
		text-align: right;
		font-family: monospace;
	}
	.cell-main {
		display: flex;
		flex-direction: column;
	}
	.name {
		color: #f1f5f9;
		text-decoration: none;
		font-weight: 600;
	}
	.name:hover {
		color: #60a5fa;
	}
	.code {
		font-family: monospace;
		font-size: 10px;
		color: #64748b;
	}
	.ind-link {
		color: #a78bfa;
		text-decoration: none;
	}
	.ind-link:hover {
		text-decoration: underline;
	}
	.open {
		color: #60a5fa;
		text-decoration: none;
	}
	.empty {
		text-align: center;
		color: #64748b;
		padding: 40px;
	}

	.disclaimer {
		margin-top: 16px;
		padding: 10px 14px;
		background: rgba(251, 191, 36, 0.06);
		border: 1px solid rgba(251, 191, 36, 0.2);
		border-radius: 6px;
		font-size: 11px;
		color: #fbbf24;
		line-height: 1.6;
	}

	@media (max-width: 768px) {
		.cond-row {
			grid-template-columns: 1fr;
		}
		.sort-row {
			grid-template-columns: 1fr;
		}
	}
</style>
