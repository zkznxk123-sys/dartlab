<script lang="ts">
	import { base } from '$app/paths';
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';
	import { brand } from '$lib/brand';
	import { buildAbsoluteUrl, buildBreadcrumbJsonLd, buildWebsiteJsonLd } from '$lib/seo';
	import { findRelatedSkills, isCatalogSkillId } from '$lib/skills/catalog';
	import { ArrowLeft, ExternalLink } from 'lucide-svelte';

	let { data } = $props();

	const Component = $derived(data.component);
	const meta = $derived(data.meta);
	const id = $derived(data.id);
	const sourcePath = $derived(data.sourcePath);

	const related = $derived(findRelatedSkills(id, 6));

	const pageTitle = $derived(`${meta.title} — DartLab Skills`);
	const pageDesc = $derived(meta.purpose);
	const pageUrl = $derived(buildAbsoluteUrl(`skills/${id}`));

	const jsonLd = $derived(
		JSON.stringify([
			buildWebsiteJsonLd(),
			buildBreadcrumbJsonLd([
				{ name: 'DartLab', url: brand.url },
				{ name: 'Skill Catalog', url: buildAbsoluteUrl('skills') },
				{ name: meta.title, url: pageUrl }
			])
		])
	);

	const githubUrl = $derived.by(() => {
		if (!sourcePath) return '';
		const idx = sourcePath.indexOf('src/dartlab/skills/');
		const tail = idx >= 0 ? sourcePath.slice(idx) : sourcePath.replace(/\\/g, '/');
		return `https://github.com/eddmpython/dartlab/blob/master/${tail}`;
	});

	function refLink(value: string): { href: string | null; label: string } {
		if (isCatalogSkillId(value)) {
			return { href: `${base}/skills/${value}`, label: value };
		}
		return { href: null, label: value };
	}
</script>

<svelte:head>
	<title>{pageTitle}</title>
	<meta name="description" content={pageDesc} />
	<link rel="canonical" href={pageUrl} />
	<meta property="og:type" content="article" />
	<meta property="og:title" content={pageTitle} />
	<meta property="og:description" content={pageDesc} />
	<meta property="og:url" content={pageUrl} />
	{@html `<script type="application/ld+json">${jsonLd}</script>`}
</svelte:head>

<Header context="skills" />

<main class="skill-detail-page">
	<nav class="breadcrumb" aria-label="breadcrumb">
		<a href="{base}/skills"><ArrowLeft size={14} /> Skill Catalog</a>
		<span>/</span>
		<span>{meta.categoryTitle ?? meta.category}</span>
	</nav>

	<header class="skill-head">
		<div class="kicker-row">
			<span class="kicker">{meta.categoryTitle ?? meta.category}</span>
			<span class="status">{meta.status}</span>
		</div>
		<h1>{meta.title}</h1>
		<p class="purpose">{meta.purpose}</p>
		<div class="id-row">
			<code>{id}</code>
			{#if githubUrl}
				<a class="source-link" href={githubUrl} target="_blank" rel="noopener noreferrer">
					GitHub 원본 <ExternalLink size={12} />
				</a>
			{/if}
		</div>
	</header>

	<div class="layout">
		<aside class="meta-card" aria-label="Skill metadata">
			{#if meta.whenToUse?.length}
				<section>
					<h3>언제 쓰나</h3>
					<ul>
						{#each meta.whenToUse.slice(0, 8) as item}<li>{item}</li>{/each}
					</ul>
				</section>
			{/if}

			{#if meta.requiredEvidence?.length}
				<section>
					<h3>필요한 근거</h3>
					<div class="chip-row">
						{#each meta.requiredEvidence as item}<span>{item}</span>{/each}
					</div>
				</section>
			{/if}

			{#if (meta.apiRefs?.length ?? 0) + (meta.toolRefs?.length ?? 0) > 0}
				<section>
					<h3>API · Tool</h3>
					<div class="chip-row">
						{#each [...(meta.apiRefs ?? []), ...(meta.toolRefs ?? [])] as item}
							{@const link = refLink(item)}
							{#if link.href}
								<a href={link.href} class="ref-chip">{link.label}</a>
							{:else}
								<span>{link.label}</span>
							{/if}
						{/each}
					</div>
				</section>
			{/if}

			{#if meta.knowledgeRefs?.length}
				<section>
					<h3>관련 skill</h3>
					<div class="chip-row">
						{#each meta.knowledgeRefs as item}
							{@const link = refLink(item)}
							{#if link.href}
								<a href={link.href} class="ref-chip">{link.label}</a>
							{:else}
								<span>{link.label}</span>
							{/if}
						{/each}
					</div>
				</section>
			{/if}

			{#if meta.sourceRefs?.length}
				<section>
					<h3>원본 출처</h3>
					<div class="chip-row">
						{#each meta.sourceRefs as item}<span>{item}</span>{/each}
					</div>
				</section>
			{/if}

			{#if related.length}
				<section>
					<h3>같은 카테고리</h3>
					<ul class="related-list">
						{#each related as r}
							<li><a href="{base}/skills/{r.id}">{r.title}</a></li>
						{/each}
					</ul>
				</section>
			{/if}
		</aside>

		<article class="body" aria-label="Skill body">
			{#if Component}
				<Component />
			{/if}
		</article>
	</div>
</main>

<Footer />

<style>
	.skill-detail-page {
		min-height: 100vh;
		max-width: 1240px;
		margin: 0 auto;
		padding: 6.5rem 1.25rem 4rem;
		background: #050811;
		color: #f1f5f9;
	}

	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		margin-bottom: 1.25rem;
		color: #64748b;
		font-size: 0.8rem;
		font-family: 'JetBrains Mono', monospace;
	}

	.breadcrumb a {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		color: #94a3b8;
		text-decoration: none;
	}

	.breadcrumb a:hover {
		color: #fb923c;
	}

	.skill-head {
		margin-bottom: 1.75rem;
		padding-bottom: 1.25rem;
		border-bottom: 1px solid rgba(30, 36, 51, 0.72);
	}

	.kicker-row {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		margin-bottom: 0.5rem;
	}

	.kicker {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #fb923c;
	}

	.status {
		padding: 0.1rem 0.45rem;
		border-radius: 4px;
		background: rgba(251, 146, 60, 0.12);
		color: #fb923c;
		font-size: 0.68rem;
		font-family: 'JetBrains Mono', monospace;
	}

	.skill-head h1 {
		margin: 0 0 0.6rem;
		font-size: clamp(1.75rem, 3.4vw, 2.6rem);
		line-height: 1.15;
		color: #f8fafc;
	}

	.purpose {
		margin: 0 0 0.7rem;
		max-width: 60rem;
		color: #cbd5e1;
		font-size: 1rem;
		line-height: 1.7;
	}

	.id-row {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		flex-wrap: wrap;
	}

	.id-row code {
		padding: 0.18rem 0.5rem;
		border-radius: 4px;
		background: rgba(15, 18, 25, 0.85);
		color: #94a3b8;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.78rem;
	}

	.source-link {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		color: #fb923c;
		font-size: 0.78rem;
		text-decoration: none;
	}

	.source-link:hover {
		text-decoration: underline;
	}

	.layout {
		display: grid;
		grid-template-columns: minmax(260px, 0.85fr) minmax(0, 2fr);
		gap: 1.5rem;
		align-items: start;
	}

	.meta-card {
		position: sticky;
		top: 4.5rem;
		padding: 1.1rem;
		border: 1px solid rgba(30, 36, 51, 0.82);
		border-radius: 8px;
		background: rgba(3, 5, 9, 0.76);
	}

	.meta-card section + section {
		margin-top: 1.1rem;
		padding-top: 1.1rem;
		border-top: 1px solid rgba(30, 36, 51, 0.72);
	}

	.meta-card h3 {
		margin: 0 0 0.55rem;
		color: #f1f5f9;
		font-size: 0.85rem;
	}

	.meta-card ul {
		margin: 0;
		padding-left: 1.05rem;
		color: #94a3b8;
		font-size: 0.82rem;
		line-height: 1.6;
	}

	.meta-card li + li {
		margin-top: 0.28rem;
	}

	.related-list {
		list-style: none;
		padding-left: 0;
	}

	.related-list a {
		color: #cbd5e1;
		text-decoration: none;
	}

	.related-list a:hover {
		color: #fb923c;
	}

	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}

	.chip-row span,
	.chip-row .ref-chip {
		display: inline-flex;
		align-items: center;
		min-height: 1.55rem;
		padding: 0.18rem 0.5rem;
		border: 1px solid rgba(30, 36, 51, 0.9);
		border-radius: 6px;
		background: rgba(15, 18, 25, 0.68);
		color: #cbd5e1;
		font-size: 0.74rem;
		text-decoration: none;
	}

	.chip-row .ref-chip:hover {
		border-color: rgba(251, 146, 60, 0.5);
		color: #fb923c;
	}

	.body {
		padding: 1.4rem 1.6rem;
		border: 1px solid rgba(30, 36, 51, 0.82);
		border-radius: 8px;
		background: rgba(10, 14, 23, 0.82);
		color: #e2e8f0;
		line-height: 1.75;
	}

	.body :global(h1),
	.body :global(h2),
	.body :global(h3),
	.body :global(h4) {
		color: #f8fafc;
		margin-top: 1.6rem;
		margin-bottom: 0.7rem;
	}

	.body :global(h1) { font-size: 1.6rem; }
	.body :global(h2) { font-size: 1.25rem; }
	.body :global(h3) { font-size: 1.05rem; }
	.body :global(h4) { font-size: 0.95rem; color: #fb923c; }

	.body :global(p) { margin: 0.7rem 0; color: #cbd5e1; }
	.body :global(ul), .body :global(ol) { padding-left: 1.4rem; color: #cbd5e1; }
	.body :global(li) { margin: 0.25rem 0; }
	.body :global(code) {
		padding: 0.1rem 0.35rem;
		border-radius: 4px;
		background: rgba(3, 5, 9, 0.65);
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.86em;
		color: #fbbf24;
	}
	.body :global(pre) {
		padding: 0.95rem 1.1rem;
		border-radius: 7px;
		background: rgba(3, 5, 9, 0.85);
		overflow-x: auto;
		font-size: 0.82rem;
	}
	.body :global(pre code) {
		background: transparent;
		padding: 0;
		color: inherit;
	}
	.body :global(table) {
		width: 100%;
		margin: 0.85rem 0;
		border-collapse: collapse;
		font-size: 0.86rem;
	}
	.body :global(th), .body :global(td) {
		padding: 0.45rem 0.7rem;
		border: 1px solid rgba(30, 36, 51, 0.8);
		text-align: left;
	}
	.body :global(th) {
		background: rgba(15, 18, 25, 0.75);
		color: #f1f5f9;
	}
	.body :global(blockquote) {
		margin: 0.85rem 0;
		padding: 0.55rem 0.95rem;
		border-left: 3px solid rgba(251, 146, 60, 0.55);
		background: rgba(251, 146, 60, 0.06);
		color: #cbd5e1;
	}
	.body :global(a) {
		color: #fb923c;
		text-decoration: underline;
		text-decoration-thickness: 1px;
		text-underline-offset: 3px;
	}

	@media (max-width: 920px) {
		.layout { grid-template-columns: 1fr; }
		.meta-card { position: static; }
	}
</style>
