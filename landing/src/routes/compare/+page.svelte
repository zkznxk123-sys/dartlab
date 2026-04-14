<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';

	let companyA: any = $state(null);
	let companyB: any = $state(null);
	let loadingA = $state(false);
	let loadingB = $state(false);
	let errorA = $state('');
	let errorB = $state('');
	let inputA = $state('');
	let inputB = $state('');

	// URL 쿼리에서 초기값
	$effect(() => {
		const q = page.url.searchParams;
		const a = q.get('a');
		const b = q.get('b');
		if (a && !inputA) {
			inputA = a;
			loadCompany(a, 'a');
		}
		if (b && !inputB) {
			inputB = b;
			loadCompany(b, 'b');
		}
	});

	async function loadCompany(code: string, slot: 'a' | 'b') {
		const trimmed = code.trim();
		if (!trimmed) return;
		const setLoading = slot === 'a' ? (v: boolean) => (loadingA = v) : (v: boolean) => (loadingB = v);
		const setError = slot === 'a' ? (v: string) => (errorA = v) : (v: string) => (errorB = v);
		const setCompany = slot === 'a' ? (v: any) => (companyA = v) : (v: any) => (companyB = v);
		setLoading(true);
		setError('');
		try {
			const res = await fetch(`${base}/map/companies/${trimmed}.json`);
			if (!res.ok) throw new Error('회사 데이터 없음 (top 200만 지원)');
			setCompany(await res.json());
		} catch (e: any) {
			setError(e.message || '로드 실패');
			setCompany(null);
		} finally {
			setLoading(false);
		}
	}

	function handleSubmit(slot: 'a' | 'b') {
		const code = slot === 'a' ? inputA : inputB;
		loadCompany(code, slot);
		const url = new URL(window.location.href);
		if (slot === 'a') url.searchParams.set('a', code);
		else url.searchParams.set('b', code);
		window.history.replaceState({}, '', url.toString());
	}

	function formatRev(v: number): string {
		if (!v) return '-';
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조원`;
		return `${v.toLocaleString()}억원`;
	}

	// 재무 5년 비교 (매출 기준)
	let financialsCompared = $derived.by(() => {
		if (!companyA || !companyB) return [];
		const byYearA: Record<string, any> = {};
		const byYearB: Record<string, any> = {};
		for (const f of companyA.financials5y || []) byYearA[f.year] = f;
		for (const f of companyB.financials5y || []) byYearB[f.year] = f;
		const years = Array.from(new Set([...Object.keys(byYearA), ...Object.keys(byYearB)])).sort();
		return years.map((y) => ({
			year: y,
			a: byYearA[y],
			b: byYearB[y],
		}));
	});

	// 공통 공급사 (정밀 엣지)
	let commonSuppliers = $derived.by(() => {
		if (!companyA || !companyB) return [];
		const codeA = new Set((companyA.suppliers || []).map((s: any) => s.stockCode));
		return (companyB.suppliers || []).filter((s: any) => codeA.has(s.stockCode));
	});
</script>

<svelte:head>
	<title>기업 비교 | dartlab 전자공시</title>
	<meta name="description" content="두 기업의 공급망·재무·지표를 나란히 비교" />
</svelte:head>

<div class="wrap">
	<nav class="breadcrumb">
		<a href="{base}/map">산업지도</a>
		<span>›</span>
		<span>기업 비교</span>
	</nav>

	<h1>기업 비교</h1>

	<!-- 입력 -->
	<div class="inputs">
		<div class="slot">
			<label>A. 종목코드</label>
			<form onsubmit={(e) => { e.preventDefault(); handleSubmit('a'); }}>
				<input type="text" bind:value={inputA} placeholder="예: 005930" />
				<button>불러오기</button>
			</form>
			{#if loadingA}<div class="status">로딩…</div>{/if}
			{#if errorA}<div class="err">{errorA}</div>{/if}
		</div>
		<div class="vs">vs</div>
		<div class="slot">
			<label>B. 종목코드</label>
			<form onsubmit={(e) => { e.preventDefault(); handleSubmit('b'); }}>
				<input type="text" bind:value={inputB} placeholder="예: 000660" />
				<button>불러오기</button>
			</form>
			{#if loadingB}<div class="status">로딩…</div>{/if}
			{#if errorB}<div class="err">{errorB}</div>{/if}
		</div>
	</div>

	{#if companyA && companyB}
		<!-- 기본 정보 -->
		<section class="sec">
			<h2>기본 정보</h2>
			<table class="cmp">
				<thead>
					<tr>
						<th class="metric">지표</th>
						<th>
							<a href="{base}/company/{companyA.ego.stockCode}">{companyA.ego.corpName}</a>
							<span class="code">({companyA.ego.stockCode})</span>
						</th>
						<th>
							<a href="{base}/company/{companyB.ego.stockCode}">{companyB.ego.corpName}</a>
							<span class="code">({companyB.ego.stockCode})</span>
						</th>
					</tr>
				</thead>
				<tbody>
					<tr><td class="metric">산업</td><td>{companyA.ego.industry}</td><td>{companyB.ego.industry}</td></tr>
					<tr><td class="metric">공정</td><td>{companyA.ego.stage || '-'}</td><td>{companyB.ego.stage || '-'}</td></tr>
					<tr><td class="metric">매출</td><td>{formatRev(companyA.ego.revenue)}</td><td>{formatRev(companyB.ego.revenue)}</td></tr>
					<tr><td class="metric">분류 신뢰도</td><td>{(companyA.ego.confidence * 100).toFixed(0)}%</td><td>{(companyB.ego.confidence * 100).toFixed(0)}%</td></tr>
				</tbody>
			</table>
		</section>

		<!-- 공급망 비교 -->
		<section class="sec">
			<h2>공급망</h2>
			<table class="cmp">
				<tbody>
					<tr><td class="metric">공급사 수</td><td>{companyA.supplyInsights?.supplierCount ?? 0}</td><td>{companyB.supplyInsights?.supplierCount ?? 0}</td></tr>
					<tr><td class="metric">정밀 엣지 수</td><td>{companyA.supplyInsights?.preciseEdgeCount ?? 0}</td><td>{companyB.supplyInsights?.preciseEdgeCount ?? 0}</td></tr>
					<tr><td class="metric">HHI</td><td>{(companyA.supplyInsights?.hhi ?? 0).toLocaleString()}</td><td>{(companyB.supplyInsights?.hhi ?? 0).toLocaleString()}</td></tr>
					<tr><td class="metric">집중도</td><td>{companyA.supplyInsights?.hhiRisk || '-'}</td><td>{companyB.supplyInsights?.hhiRisk || '-'}</td></tr>
					<tr><td class="metric">Top1 의존도</td><td>{companyA.supplyInsights?.top1Ratio ?? 0}%</td><td>{companyB.supplyInsights?.top1Ratio ?? 0}%</td></tr>
					<tr><td class="metric">Top3 의존도</td><td>{companyA.supplyInsights?.top3Ratio ?? 0}%</td><td>{companyB.supplyInsights?.top3Ratio ?? 0}%</td></tr>
					<tr><td class="metric">산업 다양성</td><td>{companyA.supplyInsights?.industryDiversity ?? 0}산업</td><td>{companyB.supplyInsights?.industryDiversity ?? 0}산업</td></tr>
				</tbody>
			</table>

			{#if commonSuppliers.length > 0}
				<div class="common">
					<h3>공통 공급사 ({commonSuppliers.length})</h3>
					<ul>
						{#each commonSuppliers as s}
							<li>
								<a href="{base}/company/{s.stockCode}">{s.corpName}</a>
								{#if s.product}<span class="product">· {s.product}</span>{/if}
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</section>

		<!-- 재무 5년 -->
		{#if financialsCompared.length > 0}
			<section class="sec">
				<h2>재무 5년</h2>
				<table class="cmp fin">
					<thead>
						<tr>
							<th class="metric">연도</th>
							<th colspan="2">{companyA.ego.corpName}</th>
							<th colspan="2">{companyB.ego.corpName}</th>
						</tr>
						<tr>
							<th></th>
							<th>매출</th>
							<th>영업익</th>
							<th>매출</th>
							<th>영업익</th>
						</tr>
					</thead>
					<tbody>
						{#each financialsCompared as row}
							<tr>
								<td class="metric">{row.year}</td>
								<td>{row.a?.sales ? (row.a.sales / 1e12).toFixed(1) + '조' : '-'}</td>
								<td>{row.a?.operating_profit ? (row.a.operating_profit / 1e12).toFixed(1) + '조' : '-'}</td>
								<td>{row.b?.sales ? (row.b.sales / 1e12).toFixed(1) + '조' : '-'}</td>
								<td>{row.b?.operating_profit ? (row.b.operating_profit / 1e12).toFixed(1) + '조' : '-'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</section>
		{/if}

		<!-- AI verdict -->
		{#if companyA.aiInsight || companyB.aiInsight}
			<section class="sec">
				<h2>AI 판단</h2>
				<div class="verdict-grid">
					<div class="verdict-col">
						<h3>{companyA.ego.corpName}</h3>
						{#if companyA.aiInsight?.narrative}
							<p>{companyA.aiInsight.narrative}</p>
						{:else}
							<p class="muted">분석 없음</p>
						{/if}
					</div>
					<div class="verdict-col">
						<h3>{companyB.ego.corpName}</h3>
						{#if companyB.aiInsight?.narrative}
							<p>{companyB.aiInsight.narrative}</p>
						{:else}
							<p class="muted">분석 없음</p>
						{/if}
					</div>
				</div>
			</section>
		{/if}
	{:else if !loadingA && !loadingB}
		<p class="hint">두 회사 종목코드를 입력하세요. (top 200 내: 005930, 000660, 035420 등)</p>
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
	.breadcrumb span {
		margin: 0 6px;
	}

	h1 {
		margin: 0 0 20px;
		font-size: 28px;
	}
	h2 {
		font-size: 13px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 12px;
		font-weight: 600;
	}
	h3 {
		font-size: 14px;
		margin: 0 0 8px;
	}

	.inputs {
		display: grid;
		grid-template-columns: 1fr 40px 1fr;
		gap: 12px;
		align-items: end;
		padding: 16px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		margin-bottom: 24px;
	}
	.slot label {
		display: block;
		font-size: 11px;
		color: #94a3b8;
		text-transform: uppercase;
		margin-bottom: 6px;
	}
	.slot form {
		display: flex;
		gap: 6px;
	}
	.slot input {
		flex: 1;
		padding: 8px 10px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		color: #f1f5f9;
		font-family: monospace;
	}
	.slot button {
		padding: 8px 12px;
		background: #60a5fa;
		color: #050811;
		border: none;
		border-radius: 6px;
		font-weight: 600;
		cursor: pointer;
	}
	.slot button:hover {
		background: #3b82f6;
	}
	.vs {
		text-align: center;
		color: #64748b;
		font-weight: 600;
		padding-bottom: 8px;
	}
	.status {
		margin-top: 6px;
		font-size: 11px;
		color: #64748b;
	}
	.err {
		margin-top: 6px;
		font-size: 11px;
		color: #f87171;
	}

	.sec {
		margin-bottom: 28px;
	}

	.cmp {
		width: 100%;
		border-collapse: collapse;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		overflow: hidden;
		font-size: 13px;
	}
	.cmp th {
		background: #050811;
		text-align: left;
		padding: 10px 12px;
		color: #94a3b8;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 600;
	}
	.cmp th a {
		color: #60a5fa;
		text-decoration: none;
	}
	.cmp th .code {
		font-family: monospace;
		color: #64748b;
		font-weight: 400;
		margin-left: 4px;
	}
	.cmp td {
		padding: 8px 12px;
		border-top: 1px solid #1e2433;
		color: #cbd5e1;
	}
	.cmp td.metric {
		color: #94a3b8;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: 600;
		width: 160px;
	}
	.cmp.fin td:not(.metric) {
		color: #f1f5f9;
		font-weight: 500;
	}

	.common {
		margin-top: 12px;
		padding: 12px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
	}
	.common ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 8px;
	}
	.common li {
		font-size: 12px;
	}
	.common a {
		color: #f1f5f9;
		text-decoration: none;
		font-weight: 500;
	}
	.common a:hover {
		color: #60a5fa;
	}
	.product {
		color: #94a3b8;
		font-size: 11px;
	}

	.verdict-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
	}
	.verdict-col {
		padding: 14px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
	}
	.verdict-col p {
		margin: 0;
		font-size: 13px;
		line-height: 1.6;
		color: #cbd5e1;
	}
	.muted {
		color: #64748b !important;
		font-style: italic;
	}

	.hint {
		padding: 20px;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		color: #94a3b8;
		font-size: 13px;
	}

	@media (max-width: 768px) {
		.inputs {
			grid-template-columns: 1fr;
		}
		.vs {
			text-align: left;
			padding: 0;
		}
		.verdict-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
