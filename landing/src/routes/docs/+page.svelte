<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';

	onMount(() => {
		goto(`${base}/docs/getting-started/quickstart`, { replaceState: true });
	});
</script>

<svelte:head>
	<title>DartLab Docs — 빠른 시작</title>
	<meta name="description" content="DartLab 설치와 빠른 시작 문서." />
	<meta http-equiv="refresh" content="0;url={base}/docs/getting-started/quickstart" />
</svelte:head>
