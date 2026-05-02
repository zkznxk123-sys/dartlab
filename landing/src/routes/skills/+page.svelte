<script lang="ts">
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';
	import SkillSearch from '$lib/components/skills/SkillSearch.svelte';
	import { buildAbsoluteUrl, buildBreadcrumbJsonLd, buildWebsiteJsonLd } from '$lib/seo';
	import { brand } from '$lib/brand';

	const pageTitle = 'DartLab Skills — 분석 절차 문서';
	const pageDesc =
		'DartLab 엔진과 분석 절차를 목적별로 검색하고 바로 실행 순서로 읽는 문서형 skill catalog.';
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
		<p class="kicker">Skills</p>
		<h1>DartLab 분석 절차 문서</h1>
		<p>
			무엇을 분석하려는지 먼저 고르고, 필요한 데이터·실행 순서·검산 기준을 한 화면에서 읽는다.
			개별 API 내부 참조가 아니라 사용자가 실제로 따라갈 수 있는 절차를 기준으로 정리했다.
		</p>
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

</style>
