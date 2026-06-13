<script lang="ts">
	import '@dartlab/ui-design/styles/tokens.css';
	import '@dartlab/ui-design/styles/typography.css';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div class="lab-shell">
	{@render children()}
</div>

<style>
	.lab-shell {
		min-height: 100vh;
		background: var(--dl-bg-base);
		background-image: var(--dl-grad-bleed);
		color: var(--dl-ink);
		font-family: var(--dl-font-ui);
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
		text-rendering: optimizeLegibility;
	}
</style>
