<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	// /lab/terminal → /terminal 본진 승격 (검증 완료).
	onMount(() => {
		goto(`${base}/terminal`, { replaceState: true });
	});
</script>

<svelte:head>
	<title>Terminal 로 이동 중… | dartlab</title>
	<meta name="robots" content="noindex" />
	<meta http-equiv="refresh" content="0; url={base}/terminal" />
</svelte:head>

<main class="redirect">
	<p>
		DartLab Terminal (<a href="{base}/terminal">/terminal</a>) 로 이동했습니다. 자동 이동되지
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
