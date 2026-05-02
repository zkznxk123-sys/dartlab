<script lang="ts">
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';
	import SkillSearch from '$lib/components/skills/SkillSearch.svelte';
	import { buildAbsoluteUrl, buildBreadcrumbJsonLd, buildWebsiteJsonLd } from '$lib/seo';
	import { brand } from '$lib/brand';

	const pageTitle = 'DartLab Skill Catalog — 분석 절차 검색';
	const pageDesc =
		'Generated capability와 src/dartlab/skills SkillSpec에서 만든 DartLab 분석 절차 검색 화면.';
	const pageUrl = buildAbsoluteUrl('skills');
	const jsonLd = JSON.stringify([
		buildWebsiteJsonLd(),
		buildBreadcrumbJsonLd([
			{ name: 'DartLab', url: brand.url },
			{ name: 'Skill Catalog', url: pageUrl }
		])
	]);
</script>

<svelte:head>
	<title>{pageTitle}</title>
	<meta name="description" content={pageDesc} />
	<link rel="canonical" href={pageUrl} />
	<meta property="og:type" content="website" />
	<meta property="og:title" content={pageTitle} />
	<meta property="og:description" content={pageDesc} />
	<meta property="og:url" content={pageUrl} />
	{@html `<script type="application/ld+json">${jsonLd}</script>`}
</svelte:head>

<Header context="skills" />
<main class="skill-page">
	<section class="skill-hero">
		<p class="kicker">Skill Catalog</p>
		<h1>DartLab 분석 절차 검색</h1>
		<p>
			API 능력은 docstring/generated capability가 기준이고, 분석 절차는
			<code>src/dartlab/skills</code> SkillSpec이 기준이다. 이 화면은 generated JSON index를 읽어
			목적별 skill과 capability ref를 찾는다.
		</p>
		<div class="hero-links">
			<a href="https://github.com/eddmpython/dartlab/tree/master/src/dartlab/skills" target="_blank" rel="noopener">
				src/dartlab/skills
			</a>
			<a href="https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md" target="_blank" rel="noopener">
				CAPABILITIES.md
			</a>
		</div>
	</section>
	<SkillSearch />
</main>
<Footer />

<style>
	.skill-page {
		min-height: 100vh;
		padding: 6.5rem 1.25rem 4rem;
		background: #050811;
		color: #f1f5f9;
	}

	.skill-page :global(.skill-search) {
		max-width: 1120px;
		margin: 0 auto;
	}

	.skill-hero {
		max-width: 1120px;
		margin: 0 auto 1.5rem;
	}

	.kicker {
		margin: 0 0 0.5rem;
		color: #fb923c;
		font-size: 0.75rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	h1 {
		margin: 0 0 0.75rem;
		font-size: clamp(2rem, 4vw, 3.5rem);
		line-height: 1.05;
		letter-spacing: 0;
	}

	.skill-hero p {
		max-width: 760px;
		margin: 0;
		color: #94a3b8;
		line-height: 1.75;
	}

	code {
		padding: 0.1rem 0.25rem;
		border: 1px solid #1e2433;
		border-radius: 4px;
		background: #0f1219;
		color: #fdba74;
	}

	.hero-links {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 1.25rem;
	}

	.hero-links a {
		display: inline-flex;
		align-items: center;
		min-height: 2.25rem;
		padding: 0.45rem 0.75rem;
		border: 1px solid #1e2433;
		border-radius: 6px;
		color: #f1f5f9;
		text-decoration: none;
		background: #0f1219;
	}

	.hero-links a:hover {
		border-color: rgba(251, 146, 60, 0.55);
		color: #fdba74;
	}
</style>
