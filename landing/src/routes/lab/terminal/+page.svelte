<script lang="ts">
	import type { PageData } from './$types';
	import { createEngine } from '$lib/terminal/data/engine';
	import type { RawData } from '$lib/terminal/data/types';
	import Terminal from '$lib/terminal/Terminal.svelte';

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
