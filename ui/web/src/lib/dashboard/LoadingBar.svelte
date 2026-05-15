<!--
	LoadingBar — Editorial 톤 top progress bar.
	dlCall in-flight 카운터 활성 시 표시.
-->
<script>
	import { getLoadingCounter } from "$lib/stores/loadingCounter.svelte.js";
	const counter = getLoadingCounter();
</script>

{#if counter.active}
	<div class="editorial-loading-bar" role="status" aria-label="loading"></div>
{/if}
