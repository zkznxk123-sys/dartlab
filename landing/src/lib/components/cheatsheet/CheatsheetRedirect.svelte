<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';

	const landscapePdfUrl = `${base}/cheatsheets/dartlab-cheatsheet-landscape.pdf#page=1&zoom=page-width`;
	const portraitPdfUrl = `${base}/cheatsheets/dartlab-cheatsheet-portrait.pdf#page=1&zoom=page-width`;

	let pdfUrl = landscapePdfUrl;

	onMount(() => {
		const { innerWidth: width, innerHeight: height } = window;
		const usePortraitPdf = width <= 820 || height > width;

		pdfUrl = usePortraitPdf ? portraitPdfUrl : landscapePdfUrl;
		window.location.replace(pdfUrl);
	});
</script>

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
