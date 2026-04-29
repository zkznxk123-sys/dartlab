<script lang="ts">
	import { base } from '$app/paths';

	const pdfUrl = `${base}/cheatsheet.pdf#page=1&zoom=page-width`;
</script>

<svelte:head>
	<title>DartLab Cheatsheet</title>
	<meta
		name="description"
		content="DartLab cheatsheet, a two-page landscape PDF for quick sharing."
	/>
	<meta http-equiv="refresh" content={`0; url=${pdfUrl}`} />
	<link rel="canonical" href="https://eddmpython.github.io/dartlab/cheatsheet" />

	<meta property="og:type" content="website" />
	<meta property="og:title" content="DartLab Cheatsheet" />
	<meta
		property="og:description"
		content="DartLab cheatsheet, a two-page landscape PDF for quick sharing."
	/>
	<meta property="og:url" content="https://eddmpython.github.io/dartlab/cheatsheet" />
	<meta property="og:site_name" content="DartLab" />
	<meta property="og:image" content="https://eddmpython.github.io/dartlab/cheatsheet-og.png" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta property="og:image:type" content="image/png" />
	<meta property="og:locale" content="ko_KR" />

	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="DartLab Cheatsheet" />
	<meta
		name="twitter:description"
		content="DartLab cheatsheet, a two-page landscape PDF for quick sharing."
	/>
	<meta name="twitter:image" content="https://eddmpython.github.io/dartlab/cheatsheet-og.png" />
</svelte:head>

<main class="share-redirect">
	<a href={pdfUrl}>Open DartLab Cheatsheet PDF</a>
</main>

<style>
	.share-redirect {
		min-height: 100svh;
		display: grid;
		place-items: center;
		background: #ffffff;
	}

	a {
		color: #0f172a;
		font: 600 16px/1.4 system-ui, sans-serif;
	}
</style>
