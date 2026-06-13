<script lang="ts">
	import { base } from '$app/paths';
</script>

<section>
	<a class="back" href={base || '/'}>← local</a>
	<h1>chat</h1>
	<p>챗 모드 (Ask 엔진 진입점). 배선·챗→터미널 전환 = 단계-5-3.</p>
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
