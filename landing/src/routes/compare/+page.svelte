<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { page } from '$app/state';

	let target = $state(`${base}/map`);

	onMount(() => {
		const a = page.url.searchParams.get('a');
		const b = page.url.searchParams.get('b');
		if (a && b) target = `${base}/map?compare=${a},${b}`;
		else if (a) target = `${base}/map?focus=${a}`;
		goto(target, { replaceState: true });
	});
</script>

<svelte:head>
	<title>비교 | dartlab 산업지도</title>
	<meta name="description" content="dartlab 산업지도에서 회사 비교" />
</svelte:head>

<div class="redirect">
	<p>산업지도로 이동 중…</p>
	<a href={target}>바로 이동 →</a>
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
