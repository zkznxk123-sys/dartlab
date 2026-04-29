<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';

	let stockCode = $derived(page.params.stockCode);
</script>

<svelte:head>
	<title>Company로 이동 · dartlab</title>
	<meta http-equiv="refresh" content="0;url={base}/company/{stockCode}" />
</svelte:head>

<main class="redirect">
	<p>Company 페이지로 이동 중입니다.</p>
	<a href="{base}/company/{stockCode}">바로 이동</a>
</main>

<style>
	.redirect {
		min-height: 70vh;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 10px;
		color: #94a3b8;
		background: #050811;
	}
	a {
		color: #fb923c;
	}
</style>
