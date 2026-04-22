<script lang="ts">
	// @ts-nocheck
	import { base } from '$app/paths';
	import { brand } from '$lib/brand';
	import NavBar from './sections/NavBar.svelte';
	import Hero from './sections/Hero.svelte';
	import HealthStrip from './sections/HealthStrip.svelte';
	import PastPerformance from './sections/PastPerformance.svelte';
	import PastQuarters from './sections/PastQuarters.svelte';
	import FinancialsCard from './sections/FinancialsCard.svelte';
	import ValueCard from './sections/ValueCard.svelte';
	import FutureCard from './sections/FutureCard.svelte';
	import HealthCard from './sections/HealthCard.svelte';
	import EgoCard from './sections/EgoCard.svelte';
	import SupplyCard from './sections/SupplyCard.svelte';
	import MacroCard from './sections/MacroCard.svelte';
	import ThesisCTA from './sections/ThesisCTA.svelte';
	import EnginesCard from './sections/EnginesCard.svelte';
	import BottomCTA from './sections/BottomCTA.svelte';
	import { assembleCompany } from './assembleCompany';

	let { data } = $props();
	const c = $derived(assembleCompany(data));
	const mapLink = $derived(`${base}/map?focus=${data.stockCode}`);
</script>

<svelte:head>
	<title>{c?.name ?? data.stockCode} 전자공시 대시보드 · dartlab</title>
	<meta
		name="description"
		content="{c?.name ?? data.stockCode} 재무·가치평가·리스크·공급망·매크로·AI 논제. DART 기반, 무료·오픈소스."
	/>
</svelte:head>

{#if c}
	<NavBar data={{ version: data.version, mapLink, stockCode: data.stockCode }} />

	<div class="top-strip container">
		<span class="chip">FREE</span>
		<span class="chip">OPEN SOURCE</span>
		<span class="chip">DART 2,664사</span>
		<a class="chip chip-link" href={mapLink}>📍 산업지도</a>
		<a class="chip chip-link" href={brand.coffee} target="_blank" rel="noopener">☕ 후원</a>
	</div>

	<Hero data={c} />
	<HealthStrip data={c.health} />
	<PastPerformance data={c.past} />

	{#if c.quarters}
		<PastQuarters data={c.quarters} />
	{/if}

	<section class="container"><FinancialsCard data={{ is: c.is, bs: c.bs, cf: c.cf }} /></section>

	{#if c.value?.methods?.length}
		<section class="container"><ValueCard data={{ value: c.value, price: c.price }} /></section>
	{/if}

	<section class="container"><FutureCard data={{ future: c.future, currentPrice: c.price }} /></section>
	<section class="container"><HealthCard data={c.health_fin} /></section>

	{#if c.egoData}
		<EgoCard data={c.egoData} />
	{/if}

	<section class="container"><SupplyCard data={c.supply} /></section>

	{#if c.macro}
		<MacroCard data={c.macro} />
	{/if}

	<section class="container"><ThesisCTA data={{ thesis: c.thesis, blog: c.blog }} /></section>
	<section class="container"><EnginesCard data={c.engines} /></section>

	<BottomCTA
		data={{
			stockCode: data.stockCode,
			mapLink,
			donateUrl: brand.coffee,
			repoUrl: brand.repo
		}}
	/>
{:else}
	<div class="container empty-state">
		<h1>대시보드 준비 중</h1>
		<p>
			이 종목({data.stockCode})은 ecosystem 데이터에 아직 등록되지 않았습니다.
			<br />
			산업지도에서 다른 회사를 찾아보세요.
		</p>
		<p>
			<a href="{base}/map" class="btn-link">← 산업지도로 돌아가기</a>
		</p>
	</div>
{/if}

<style>
	.top-strip {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
		align-items: center;
		padding: 14px 32px 0;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 11px;
		border-radius: 999px;
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.06em;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--border);
		color: var(--text-mid);
	}
	.chip-link {
		cursor: pointer;
		transition: all 0.15s;
		text-decoration: none;
	}
	.chip-link:hover {
		background: var(--grad-heat-soft);
		border-color: var(--border-accent);
		color: var(--text);
	}
	.empty-state {
		min-height: 70vh;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		gap: 12px;
		color: var(--text-mid);
	}
	.empty-state h1 {
		font-size: 32px;
		color: var(--text);
	}
	.btn-link {
		color: var(--orange);
		text-decoration: underline;
	}

	@media (max-width: 768px) {
		.top-strip {
			padding: 10px 16px 0;
		}
	}
</style>
