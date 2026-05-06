<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';

	let { data } = $props();

	const redirectMap: Record<string, string> = {
		'getting-started/installation': '/skills/start.installUv',
		'getting-started/quickstart': '/skills/start.quickStart',
		'getting-started/cli-maintenance': '/skills/operation.cliMaintenance',
		'getting-started/sections': '/skills/engines.company.sections',
		tutorials: '/skills/runtime.notebooks',
		about: '/about',
		stability: '/skills/operation.stability',
		methodology: '/skills/operation.methodology'
	};

	const target = $derived(redirectMap[data.slug] ?? '');
	const fullUrl = $derived(target ? `${base}${target}` : '');
	const Component = $derived(data.component);
	const meta = $derived(data.metadata ?? {});
	const pageTitle = $derived(
		target
			? `Redirecting to ${target} — DartLab`
			: `${meta.title ?? data.slug} — DartLab Docs`
	);

	onMount(() => {
		if (target) {
			goto(fullUrl, { replaceState: true });
		}
	});
</script>

<svelte:head>
	<title>{pageTitle}</title>
	{#if target}
		<meta name="robots" content="noindex" />
		<meta http-equiv="refresh" content="0;url={fullUrl}" />
		<link rel="canonical" href={fullUrl} />
	{:else if meta.description}
		<meta name="description" content={meta.description} />
	{/if}
</svelte:head>

{#if target}
	<main class="redirect-page">
		<p>이 페이지는 <a href={fullUrl}>{target}</a> 으로 이동했습니다.</p>
	</main>
{:else if Component}
	<Header context="default" />
	<main class="legacy-doc">
		<nav class="breadcrumb" aria-label="breadcrumb">
			<a href="{base}/skills">Skills</a>
			<span>/</span>
			<span>legacy docs</span>
			<span>/</span>
			<code>{data.slug}</code>
		</nav>

		<aside class="legacy-notice">
			<strong>참고</strong> — 이 페이지는 자동 발간 산출물 또는 분석 샘플로, 새 구조 (Skill OS / Blog) 로
			흡수되지 않은 콘텐츠다. 일차 진입은 <a href="{base}/skills">Skill Catalog</a>.
		</aside>

		<article class="doc-body">
			<Component />
		</article>
	</main>
	<Footer />
{:else}
	<main class="not-found">
		<h1>404</h1>
		<p>페이지를 찾을 수 없습니다.</p>
		<a href="{base}/skills">Skill Catalog 로 이동</a>
	</main>
{/if}

<style>
	.redirect-page {
		min-height: 60vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 4rem 1rem;
		color: #94a3b8;
		font-size: 0.95rem;
	}

	.redirect-page a {
		color: #fb923c;
		text-decoration: underline;
		margin: 0 0.25rem;
	}

	.legacy-doc {
		min-height: 100vh;
		max-width: 860px;
		margin: 0 auto;
		padding: 6.5rem 1.25rem 4rem;
		color: #e2e8f0;
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		margin-bottom: 1.25rem;
		color: #64748b;
		font-size: 0.78rem;
		font-family: 'JetBrains Mono', monospace;
	}

	.breadcrumb a { color: #94a3b8; text-decoration: none; }
	.breadcrumb a:hover { color: #fb923c; }
	.breadcrumb code {
		padding: 0.08rem 0.4rem;
		background: rgba(15, 18, 25, 0.7);
		border-radius: 4px;
		color: #cbd5e1;
	}

	.legacy-notice {
		margin: 0 0 2rem;
		padding: 0.85rem 1rem;
		border: 1px solid rgba(251, 191, 36, 0.3);
		border-radius: 8px;
		background: rgba(251, 191, 36, 0.06);
		color: #cbd5e1;
		font-size: 0.85rem;
		line-height: 1.6;
	}

	.legacy-notice strong { color: #fbbf24; }
	.legacy-notice a { color: #fb923c; text-decoration: underline; }

	.doc-body {
		line-height: 1.75;
		color: #e2e8f0;
	}

	.doc-body :global(h1),
	.doc-body :global(h2),
	.doc-body :global(h3),
	.doc-body :global(h4) {
		color: #f8fafc;
		margin-top: 1.6rem;
		margin-bottom: 0.7rem;
	}

	.doc-body :global(h1) { font-size: 1.9rem; }
	.doc-body :global(h2) {
		font-size: 1.35rem;
		padding-bottom: 0.4rem;
		border-bottom: 1px solid rgba(30, 36, 51, 0.6);
	}
	.doc-body :global(h3) { font-size: 1.05rem; color: #fb923c; }

	.doc-body :global(p) { margin: 0.7rem 0; color: #cbd5e1; }
	.doc-body :global(ul), .doc-body :global(ol) { padding-left: 1.4rem; color: #cbd5e1; }
	.doc-body :global(li) { margin: 0.25rem 0; }

	.doc-body :global(code) {
		padding: 0.1rem 0.35rem;
		border-radius: 4px;
		background: rgba(15, 18, 25, 0.7);
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.86em;
		color: #fbbf24;
	}

	.doc-body :global(pre) {
		padding: 0.95rem 1.1rem;
		border-radius: 7px;
		background: rgba(3, 5, 9, 0.85);
		overflow-x: auto;
		font-size: 0.82rem;
		margin: 1rem 0;
	}

	.doc-body :global(pre code) {
		background: transparent;
		padding: 0;
		color: inherit;
	}

	.doc-body :global(table) {
		width: 100%;
		margin: 1rem 0;
		border-collapse: collapse;
		font-size: 0.86rem;
	}
	.doc-body :global(th), .doc-body :global(td) {
		padding: 0.45rem 0.7rem;
		border: 1px solid rgba(30, 36, 51, 0.7);
		text-align: left;
	}
	.doc-body :global(th) {
		background: rgba(15, 18, 25, 0.75);
		color: #f1f5f9;
	}

	.doc-body :global(a) {
		color: #fb923c;
		text-decoration: underline;
	}

	.not-found {
		min-height: 60vh;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 4rem 1rem;
		color: #94a3b8;
	}

	.not-found h1 {
		font-size: 4rem;
		font-weight: 800;
		background: linear-gradient(135deg, #ea4647, #f87171);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		margin: 0;
	}

	.not-found a {
		color: #fb923c;
		text-decoration: underline;
	}
</style>
