<script lang="ts">
	import { base } from '$app/paths';
</script>

<section>
	<a class="back" href={base || '/'}>← local</a>
	<h1>settings / workspace</h1>
	<p>workspace 설정. 배선 = 단계-5-3.</p>
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
	p {
		color: var(--dl-ink-dim, #9aa0aa);
	}
</style>
