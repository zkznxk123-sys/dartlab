<script lang="ts">
	import { base } from '$app/paths';

	const pdfPath = `${base}/cheatsheet.pdf`;
	const pdfUrl = `${pdfPath}#page=1&view=Fit&toolbar=0&navpanes=0&scrollbar=0`;
</script>

<svelte:head>
	<title>DartLab Cheatsheet</title>
	<meta
		name="description"
		content="DartLab cheatsheet, one-page landscape PDF for quick sharing."
	/>
	<meta property="og:title" content="DartLab Cheatsheet" />
	<meta
		property="og:description"
		content="DartLab cheatsheet, one-page landscape PDF for quick sharing."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://eddmpython.github.io/dartlab/cheatsheet" />
</svelte:head>

<main class="sheet-page">
	<object class="sheet" data={pdfUrl} type="application/pdf" aria-label="DartLab cheatsheet PDF">
		<iframe class="sheet" src={pdfUrl} title="DartLab cheatsheet PDF"></iframe>
	</object>
	<a class="pdf-link" href={pdfPath} aria-label="Open PDF">PDF</a>
</main>

<style>
	:global(body) {
		margin: 0;
		background: #0b0f17;
	}

	.sheet-page {
		width: 100vw;
		height: 100svh;
		background: #0b0f17;
		overflow: hidden;
		position: relative;
	}

	.sheet {
		display: block;
		width: 100vw;
		height: 100svh;
		border: 0;
		background: #0b0f17;
	}

	.pdf-link {
		position: fixed;
		right: 12px;
		bottom: 12px;
		z-index: 2;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 44px;
		height: 32px;
		padding: 0 10px;
		border: 1px solid rgba(148, 163, 184, 0.5);
		border-radius: 6px;
		background: rgba(15, 23, 42, 0.72);
		color: #e2e8f0;
		font-size: 12px;
		font-weight: 700;
		text-decoration: none;
		backdrop-filter: blur(8px);
	}

	.pdf-link:hover {
		background: rgba(30, 41, 59, 0.9);
	}
</style>
