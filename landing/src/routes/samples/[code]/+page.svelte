<script lang="ts">
	import { base } from '$app/paths';
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';

	let { data } = $props();

	const Component = $derived(data.component);
	const meta = $derived(data.metadata ?? {});
	const pageTitle = $derived(`${meta.title ?? data.code} 분석 샘플 — DartLab`);
	const pageDesc = $derived(
		meta.description ?? `dartlab.Company("${data.code}") 로 만든 한국 종목 분석 샘플 보고서.`
	);
</script>

<svelte:head>
	<title>{pageTitle}</title>
	<meta name="description" content={pageDesc} />
	<link rel="canonical" href="https://eddmpython.github.io/dartlab/samples/{data.code}" />
</svelte:head>

<Header context="default" />

<main class="sample-page">
	<nav class="breadcrumb" aria-label="breadcrumb">
		<a href="{base}/">DartLab</a>
		<span>/</span>
		<a href="{base}/samples">Samples</a>
		<span>/</span>
		<code>{data.code}</code>
	</nav>

	<aside class="notice">
		<strong>참고</strong> — 이 페이지는 DartLab 분석 엔진으로 만든 종목 보고서 샘플이다. 실제 사용은
		<a href="{base}/skills/start.quickStart">Quick Start</a> 와
		<a href="{base}/skills/engines.company">engines.company</a> 를 본다.
	</aside>

	<article class="sample-body">
		<Component />
	</article>
</main>

<Footer />

<style>
	.sample-page {
		min-height: 100vh;
		max-width: 860px;
		margin: 0 auto;
		padding: 6.5rem 1.25rem 4rem;
		color: var(--dl-ink, #e2e8f0);
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		margin-bottom: 1.25rem;
		color: #64748b;
		font-size: 0.78rem;
		font-family: var(--dl-font-mono, 'JetBrains Mono', monospace);
	}

	.breadcrumb a {
		color: #94a3b8;
		text-decoration: none;
	}

	.breadcrumb a:hover {
		color: #fb923c;
	}

	.breadcrumb code {
		padding: 0.08rem 0.4rem;
		background: rgba(15, 18, 25, 0.7);
		border-radius: 4px;
		color: #cbd5e1;
	}

	.notice {
		margin: 0 0 2rem;
		padding: 0.85rem 1rem;
		border: 1px solid rgba(251, 146, 60, 0.3);
		border-radius: 8px;
		background: rgba(251, 146, 60, 0.06);
		color: #cbd5e1;
		font-size: 0.85rem;
		line-height: 1.6;
	}

	.notice strong {
		color: #fb923c;
	}

	.notice a {
		color: #fb923c;
		text-decoration: underline;
	}

	.sample-body {
		line-height: 1.75;
		color: #e2e8f0;
	}

	.sample-body :global(h1),
	.sample-body :global(h2),
	.sample-body :global(h3),
	.sample-body :global(h4) {
		color: #f8fafc;
		margin-top: 1.6rem;
		margin-bottom: 0.7rem;
	}

	.sample-body :global(h2) {
		font-size: 1.45rem;
		padding-bottom: 0.4rem;
		border-bottom: 1px solid rgba(30, 36, 51, 0.6);
	}

	.sample-body :global(h3) {
		font-size: 1.05rem;
		color: #fb923c;
	}

	.sample-body :global(h4) {
		font-size: 0.95rem;
		color: #fbbf24;
	}

	.sample-body :global(p) {
		margin: 0.7rem 0;
		color: #cbd5e1;
	}

	.sample-body :global(ul),
	.sample-body :global(ol) {
		padding-left: 1.4rem;
		color: #cbd5e1;
	}

	.sample-body :global(li) {
		margin: 0.25rem 0;
	}

	.sample-body :global(blockquote) {
		margin: 1rem 0;
		padding: 0.6rem 1rem;
		border-left: 3px solid #fb923c;
		background: rgba(251, 146, 60, 0.06);
		color: #cbd5e1;
	}

	.sample-body :global(code) {
		padding: 0.1rem 0.35rem;
		border-radius: 4px;
		background: rgba(15, 18, 25, 0.7);
		font-family: var(--dl-font-mono, 'JetBrains Mono', monospace);
		font-size: 0.86em;
		color: #fbbf24;
	}

	.sample-body :global(pre) {
		padding: 0.95rem 1.1rem;
		border-radius: 7px;
		background: rgba(3, 5, 9, 0.85);
		overflow-x: auto;
		font-size: 0.82rem;
		margin: 1rem 0;
	}

	.sample-body :global(pre code) {
		background: transparent;
		padding: 0;
		color: inherit;
	}

	.sample-body :global(table) {
		width: 100%;
		margin: 1rem 0;
		border-collapse: collapse;
		font-size: 0.86rem;
	}

	.sample-body :global(th),
	.sample-body :global(td) {
		padding: 0.45rem 0.7rem;
		border: 1px solid rgba(30, 36, 51, 0.7);
		text-align: left;
	}

	.sample-body :global(th) {
		background: rgba(15, 18, 25, 0.75);
		color: #f1f5f9;
	}

	.sample-body :global(a) {
		color: #fb923c;
		text-decoration: underline;
	}
</style>
