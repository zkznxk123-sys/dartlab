<!--
	LoadingBar — top progress bar (shadcn 토큰). dlCall in-flight 카운터 활성 시.
-->
<script>
	import { getLoadingCounter } from "$lib/stores/loadingCounter.svelte.js";
	const counter = getLoadingCounter();
</script>

{#if counter.active}
	<div class="absolute top-0 left-0 right-0 h-0.5 overflow-hidden z-30" role="status" aria-label="loading">
		<div class="h-full w-1/3 bg-foreground/60 animate-pulse"></div>
	</div>
{/if}
