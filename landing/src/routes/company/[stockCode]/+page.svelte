<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	onMount(() => {
		goto(`${base}/map?focus=${data.stockCode}`, { replaceState: true });
	});
</script>

<svelte:head>
	<title>{data.stockCode} | dartlab 산업지도</title>
	<meta name="description" content="dartlab 산업지도에서 회사 분석 보기" />
	<meta http-equiv="refresh" content="0;url={base}/map?focus={data.stockCode}" />
	<link rel="canonical" href="{base}/map?focus={data.stockCode}" />
</svelte:head>

<div class="redirect">
	<p>산업지도로 이동 중…</p>
	<a href="{base}/map?focus={data.stockCode}">바로 이동 →</a>
</div>

<style>
	.redirect {
		max-width: 600px;
		margin: 80px auto;
		text-align: center;
		color: #94a3b8;
		font-family: 'Pretendard Variable', sans-serif;
	}
	.redirect a {
		color: #60a5fa;
	}
</style>
