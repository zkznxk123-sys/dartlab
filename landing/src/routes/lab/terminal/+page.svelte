<script lang="ts">
	import type { PageData } from './$types';
	import { createEngine } from '$lib/terminal/data/engine';
	import type { RawData } from '$lib/terminal/data/types';
	import Terminal from '$lib/terminal/Terminal.svelte';
	import { loadDartDb } from '$lib/data/duckdb';

	// DuckDB-WASM 프리워밍 — JSON 데이터 로드와 병렬로 미리 인스턴스화 (주가 차트 체감속도↑)
	void loadDartDb();

	let { data }: { data: PageData } = $props();
	const eng = $derived(createEngine(data.raw as RawData));
	const ready = $derived(!!data.raw.finance.years.length && Object.keys(data.raw.prices.data).length > 0);
</script>

<svelte:head>
	<title>dartlab · /lab/terminal — DartLab Terminal (검증)</title>
	<meta name="robots" content="noindex" />
</svelte:head>

{#if ready}
	<Terminal {eng} initial="005930" />
{:else}
	<div class="loading">HuggingFace · dartlab-data 연결 중 …</div>
{/if}

<style>
	.loading {
		height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--dl-bg-base);
		color: var(--dl-ink-mute);
		font-family: var(--dl-font-mono);
		font-size: 12px;
	}
</style>
