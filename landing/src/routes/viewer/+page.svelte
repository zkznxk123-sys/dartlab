<script lang="ts">
	// 공시뷰어 진입 — 회사 검색 + 예시. scan 디자인(다크 #050811 · 오렌지).
	import { base } from '$app/paths';
	import Header from '$lib/components/sections/Header.svelte';
	import CompanySearch from '$lib/components/viewer/CompanySearch.svelte';

	const examples = [
		{ code: '005930', name: '삼성전자' },
		{ code: '000660', name: 'SK하이닉스' },
		{ code: '035420', name: 'NAVER' },
		{ code: 'AAPL', name: 'Apple' }
	];
</script>

<svelte:head><title>공시 뷰어 · dartlab</title></svelte:head>

<Header context="landing" />

<main class="viewer-home">
	<div class="hero">
		<div class="eyebrow">공시 뷰어</div>
		<h1>panel 하나로 보는 정기보고서 — 항목 × 기간 수평 격자</h1>
		<p>회사명이나 종목코드로 검색해 DART·EDGAR 공시 본문을 기간별로 펼쳐봅니다.</p>
		<div class="search-row"><CompanySearch /></div>
		<div class="examples">
			{#each examples as c (c.code)}
				<a class="ex" href={`${base}/viewer/company/${c.code}`}>
					<span class="ex-name">{c.name}</span>
					<span class="ex-code">{c.code}</span>
				</a>
			{/each}
		</div>
	</div>
</main>

<style>
	.viewer-home {
		min-height: 100vh;
		background: #050811;
		color: #f1f5f9;
		padding: 96px 20px 48px;
		display: flex;
		justify-content: center;
	}
	.hero {
		width: 100%;
		max-width: 720px;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 800;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.hero h1 {
		margin: 10px 0 12px;
		font-size: clamp(1.6rem, 3vw, 2.4rem);
		line-height: 1.2;
		letter-spacing: -0.02em;
	}
	.hero p {
		margin: 0 0 24px;
		color: #94a3b8;
		line-height: 1.6;
	}
	.search-row {
		margin-bottom: 28px;
	}
	.examples {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.ex {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 7px 12px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0a0e18;
		color: #cbd5e1;
		text-decoration: none;
		font-size: 13px;
	}
	.ex:hover {
		border-color: rgba(251, 146, 60, 0.6);
		color: #fb923c;
	}
	.ex-code {
		font-family: monospace;
		font-size: 11px;
		color: #64748b;
	}
	.ex:hover .ex-code {
		color: #fb923c;
	}
</style>
