<script lang="ts">
	import { base } from '$app/paths';
	import { LAST_SYM_KEY } from '@dartlab/ui-surfaces/terminal';
	import { getLocalRuntime } from '$lib/runtime/localRuntime';

	// 최근 본 종목 — surface 가 관리하는 LAST_SYM_KEY(localStorage) 재사용. 없으면 기본 005930.
	const recent =
		(typeof localStorage !== 'undefined' && localStorage.getItem(LAST_SYM_KEY)) || '005930';

	function openRecent() {
		void getLocalRuntime().navigation.toTerminal(recent);
	}
</script>

<section>
	<a class="back" href={base || '/'}>← local</a>
	<h1>ask</h1>
	<p>Ask — 최근 본 회사 터미널로 진입. 근거 기반 Q&A 코파일럿은 단계-7.</p>
	<button onclick={openRecent}>최근 회사 터미널 열기 · {recent} →</button>
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
		margin: 0 0 1.5rem;
	}
	button {
		padding: 0.6rem 1rem;
		border: 1px solid var(--dl-accent, #ff5a36);
		border-radius: 8px;
		background: transparent;
		color: var(--dl-accent, #ff5a36);
		cursor: pointer;
		font-family: var(--dl-font-mono, ui-monospace, monospace);
	}
	button:hover {
		background: var(--dl-accent, #ff5a36);
		color: #fff;
	}
</style>
