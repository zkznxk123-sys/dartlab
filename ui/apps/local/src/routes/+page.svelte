<script lang="ts">
	import { base } from '$app/paths';

	// 5-1 scaffold 진입 셸 — 스켈레톤 라우트 네비게이션 맵. 기본 진입(→/chat)·실 배선은 5-3.
	const routes: { href: string; label: string; note: string }[] = [
		{ href: `${base}/chat`, label: 'chat', note: '챗 모드 (Ask 엔진 진입점)' },
		{ href: `${base}/terminal/005930`, label: 'terminal/[code]', note: '터미널 모드 (TerminalSurface 풀스크린)' },
		{ href: `${base}/ask`, label: 'ask', note: 'Ask → 최근 회사 터미널' },
		{ href: `${base}/analysis/005930`, label: 'analysis/[code]', note: '회사 분석' },
		{ href: `${base}/analysis/005930/viewer`, label: 'analysis/[code]/viewer', note: '공시 뷰어 (터미널 overlay 대상)' },
		{ href: `${base}/settings/providers`, label: 'settings/providers', note: 'AI provider 설정' },
		{ href: `${base}/settings/workspace`, label: 'settings/workspace', note: 'workspace 설정' }
	];
</script>

<main>
	<h1>DartLab <span>Local</span></h1>
	<p class="sub">로컬 SvelteKit 앱 — scaffold (단계-5-1). 라우트 스켈레톤·배선은 5-3.</p>
	<nav>
		{#each routes as r (r.href)}
			<a href={r.href}>
				<code>{r.label}</code>
				<span>{r.note}</span>
			</a>
		{/each}
	</nav>
</main>

<style>
	main {
		max-width: 720px;
		margin: 0 auto;
		padding: 4rem 1.5rem;
	}
	h1 {
		font-size: 2rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		margin: 0 0 0.25rem;
	}
	h1 span {
		color: var(--dl-accent, #ff5a36);
	}
	.sub {
		color: var(--dl-ink-dim, #9aa0aa);
		font-size: 0.9rem;
		margin: 0 0 2rem;
	}
	nav {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	a {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border: 1px solid var(--dl-bd, #2a2c33);
		border-radius: 8px;
		background: var(--dl-bg-raised, #16171a);
		text-decoration: none;
		color: inherit;
		transition: border-color 0.15s;
	}
	a:hover {
		border-color: var(--dl-accent, #ff5a36);
	}
	code {
		font-family: var(--dl-font-mono, ui-monospace, monospace);
		font-size: 0.85rem;
		color: var(--dl-info, #6ab0ff);
	}
	a span {
		color: var(--dl-ink-dim, #9aa0aa);
		font-size: 0.82rem;
	}
</style>
