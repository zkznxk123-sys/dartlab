<script lang="ts">
	import { base } from '$app/paths';
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';

	let { data } = $props();

	const pageTitle = 'Samples — DartLab 분석 보고서 샘플';
	const pageDesc =
		'DartLab 의 engines.company + engines.analysis 으로 만든 한국 종목 분석 샘플 11 종.';
</script>

<svelte:head>
	<title>{pageTitle}</title>
	<meta name="description" content={pageDesc} />
	<link rel="canonical" href="https://eddmpython.github.io/dartlab/samples" />
</svelte:head>

<Header context="default" />

<main class="samples-index">
	<header class="hero">
		<p class="kicker">Samples</p>
		<h1>분석 보고서 샘플</h1>
		<p class="lead">
			DartLab 분석 엔진으로 만든 한국 종목 보고서 11 종. 실제 사용은
			<a href="{base}/skills/start.quickStart">Quick Start</a> 와
			<a href="{base}/skills/engines.company">engines.company</a> 를 본다.
		</p>
	</header>

	<ul class="sample-list">
		{#each data.entries as entry (entry.code)}
			<li>
				<a href="{base}/samples/{entry.code}">
					<span class="code">{entry.code}</span>
					<span class="title">{entry.title}</span>
					{#if entry.excerpt}
						<span class="excerpt">{entry.excerpt}</span>
					{/if}
				</a>
			</li>
		{/each}
	</ul>
</main>

<Footer />

<style>
	.samples-index {
		min-height: 100vh;
		max-width: 860px;
		margin: 0 auto;
		padding: 6.5rem 1.25rem 4rem;
		color: var(--dl-ink, #e2e8f0);
	}

	.hero {
		margin-bottom: 2.5rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid rgba(30, 36, 51, 0.6);
	}

	.kicker {
		margin: 0 0 0.5rem;
		color: #fb923c;
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	h1 {
		margin: 0 0 0.85rem;
		font-size: clamp(2rem, 4vw, 3rem);
		line-height: 1.1;
		color: #f8fafc;
	}

	.lead {
		margin: 0;
		max-width: 38rem;
		color: #94a3b8;
		font-size: 1rem;
		line-height: 1.7;
	}

	.lead a {
		color: #fb923c;
		text-decoration: underline;
	}

	.sample-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 0.7rem;
	}

	.sample-list a {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.5rem 1rem;
		align-items: baseline;
		padding: 0.85rem 1.1rem;
		border: 1px solid rgba(30, 36, 51, 0.7);
		border-radius: 8px;
		background: rgba(15, 18, 25, 0.4);
		color: #cbd5e1;
		text-decoration: none;
		transition: border-color 0.15s, background 0.15s;
	}

	.sample-list a:hover {
		border-color: rgba(251, 146, 60, 0.4);
		background: rgba(251, 146, 60, 0.04);
	}

	.code {
		font-family: var(--dl-font-mono, 'JetBrains Mono', monospace);
		font-size: 0.85rem;
		color: #fb923c;
		font-weight: 600;
	}

	.title {
		font-size: 1rem;
		font-weight: 600;
		color: #f1f5f9;
	}

	.excerpt {
		grid-column: 2 / -1;
		margin-top: 0.25rem;
		font-size: 0.85rem;
		color: #94a3b8;
		line-height: 1.5;
	}
</style>
