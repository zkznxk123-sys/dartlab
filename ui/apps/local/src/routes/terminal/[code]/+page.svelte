<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';

	const code = $derived(page.params.code);
</script>

<section>
	<a class="back" href={base || '/'}>← local</a>
	<h1>terminal / <code>{code}</code></h1>
	<p>터미널 모드 — TerminalSurface 풀스크린 마운트 = 단계-5-3 (createLocalRuntime 주입).</p>
</section>

<style>
	section {
		max-width: 720px;
		margin: 0 auto;
		padding: 3rem 1.5rem;
	}
	.back {
		color: var(--dl-ink-dim, #9aa0aa);
		text-decoration: none;
		font-size: 0.85rem;
	}
	h1 {
		font-size: 1.5rem;
		margin: 1rem 0 0.5rem;
	}
	h1 code {
		font-family: var(--dl-font-mono, ui-monospace, monospace);
		color: var(--dl-info, #6ab0ff);
	}
	p {
		color: var(--dl-ink-dim, #9aa0aa);
	}
</style>
