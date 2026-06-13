<script lang="ts">
	import { base } from '$app/paths';
	import { getLocalRuntime } from '$lib/runtime/localRuntime';

	let code = $state('005930');

	function enterTerminal(e: Event) {
		e.preventDefault();
		const c = code.trim();
		if (/^\d{6}$/.test(c)) void getLocalRuntime().navigation.toTerminal(c);
	}
</script>

<section>
	<a class="back" href={base || '/'}>← local</a>
	<h1>chat</h1>
	<p>챗 모드 — 종목을 지정하면 별도 탭 없이 터미널 모드로 진입한다. Ask 엔진 대화·근거 코파일럿은 단계-7.</p>
	<form onsubmit={enterTerminal}>
		<input bind:value={code} placeholder="종목코드 6자리 (예: 005930)" inputmode="numeric" maxlength="6" />
		<button type="submit">터미널 열기 →</button>
	</form>
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
	form {
		display: flex;
		gap: 0.5rem;
	}
	input {
		flex: 1;
		padding: 0.6rem 0.8rem;
		border: 1px solid var(--dl-bd, #2a2c33);
		border-radius: 8px;
		background: var(--dl-bg-raised, #16171a);
		color: var(--dl-ink, #e7e7ea);
		font-family: var(--dl-font-mono, ui-monospace, monospace);
	}
	button {
		padding: 0.6rem 1rem;
		border: 1px solid var(--dl-accent, #ff5a36);
		border-radius: 8px;
		background: transparent;
		color: var(--dl-accent, #ff5a36);
		cursor: pointer;
	}
	button:hover {
		background: var(--dl-accent, #ff5a36);
		color: #fff;
	}
</style>
