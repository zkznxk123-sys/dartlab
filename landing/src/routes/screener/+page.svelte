<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { page } from '$app/state';

	// /screener → /scan (Scan Studio) 으로 통합. base64 ?q= 페이로드 보존 (v2 디코더가 v1 호환).
	onMount(() => {
		const q = page.url.searchParams.get('q');
		const preset = page.url.searchParams.get('preset');
		const params = new URLSearchParams();
		if (q) params.set('q', q);
		if (preset) params.set('preset', preset);
		const next = params.toString() ? `${base}/scan?${params.toString()}` : `${base}/scan`;
		goto(next, { replaceState: true });
	});
</script>

<svelte:head>
	<title>Scan Studio 로 이동 중… | dartlab</title>
	<meta name="robots" content="noindex" />
	<meta http-equiv="refresh" content="0; url={base}/scan" />
</svelte:head>

<main class="redirect">
	<p>
		스크리너가 Scan Studio (<a href="{base}/scan">/scan</a>) 로 이동했습니다. 자동 이동되지
		않으면 클릭해 주세요.
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
