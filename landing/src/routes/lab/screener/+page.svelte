<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	// /lab/screener → /scan 으로 통합 (Scan Studio).
	onMount(() => {
		goto(`${base}/scan`, { replaceState: true });
	});
</script>

<svelte:head>
	<title>스크리너로 이동 중… | dartlab</title>
	<meta name="robots" content="noindex" />
	<meta http-equiv="refresh" content="0; url={base}/scan" />
</svelte:head>

<main class="redirect">
	<p>
		Scan Studio (<a href="{base}/scan">/scan</a>) 로 이동했습니다. 자동 이동되지 않으면
		클릭해 주세요.
	</p>
</main>

<style>
	.redirect {
		max-width: 480px;
		margin: 80px auto;
		padding: 24px;
		text-align: center;
		font-size: 14px;
		color: #94a3b8;
	}
	.redirect a {
		color: #60a5fa;
		text-decoration: none;
	}
	.redirect a:hover {
		text-decoration: underline;
	}
</style>
