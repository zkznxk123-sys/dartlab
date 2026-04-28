<script lang="ts">
	import { base } from '$app/paths';
	import { Download, ExternalLink, FileText, Image as ImageIcon } from 'lucide-svelte';
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';
	import { brand } from '$lib/brand';

	const siteUrl = `${brand.url.replace(/\/$/, '')}`;
	const landscapePdf = `${base}/cheatsheets/dartlab-cheatsheet-landscape.pdf`;
	const landscapeImage = `${base}/cheatsheets/dartlab-cheatsheet-landscape.webp`;
	const absoluteLandscapePdf = `${siteUrl}/cheatsheets/dartlab-cheatsheet-landscape.pdf`;
</script>

<svelte:head>
	<title>DartLab Cheatsheet — PDF 다운로드</title>
	<meta name="description" content="DartLab 사용법을 가로형 합본 cheatsheet 한 장으로 정리했다." />
	<link rel="canonical" href="{siteUrl}/cheatsheet" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="DartLab Cheatsheet" />
	<meta property="og:description" content="DartLab 사용법을 가로형 합본 PDF cheatsheet로 바로 열고 내려받을 수 있다." />
	<meta property="og:url" content="{siteUrl}/cheatsheet" />
	<meta property="og:image" content="{siteUrl}/cheatsheets/dartlab-cheatsheet-landscape.webp" />
</svelte:head>

<Header />

<main class="cheatsheet-page">
	<section class="hero">
		<div class="hero-copy">
			<p class="eyebrow">DartLab Cheatsheet</p>
			<h1>한 장으로 보는 DartLab</h1>
			<p class="lead">DartLab 3·4를 좌우로 합친 가로형 cheatsheet를 메인으로 제공한다.</p>
			<div class="actions">
				<a class="primary-action" href={landscapePdf} target="_blank" rel="noopener">
					<FileText size={17} />
					<span>합본 PDF 열기</span>
				</a>
			</div>
		</div>
		<div class="url-panel" aria-label="public urls">
			<div>
				<span>메인 가로형</span>
				<a href={absoluteLandscapePdf} target="_blank" rel="noopener">{absoluteLandscapePdf}</a>
			</div>
		</div>
	</section>

	<section class="asset-grid" aria-label="cheatsheet assets">
		<article class="asset-block landscape-block">
			<div class="asset-head">
				<div>
					<p class="asset-kicker">Main Landscape</p>
					<h2>DartLab 3·4 합본 가로형</h2>
				</div>
				<div class="asset-actions">
					<a href={landscapePdf} target="_blank" rel="noopener" title="PDF 열기">
						<ExternalLink size={16} />
					</a>
					<a href={landscapePdf} download title="PDF 다운로드">
						<Download size={16} />
					</a>
					<a href={landscapeImage} target="_blank" rel="noopener" title="이미지 열기">
						<ImageIcon size={16} />
					</a>
				</div>
			</div>
			<a class="preview landscape-preview" href={landscapePdf} target="_blank" rel="noopener">
				<img src={landscapeImage} alt="DartLab 3 and 4 combined landscape cheatsheet" loading="eager" width="3384" height="941" />
			</a>
		</article>
	</section>
</main>

<Footer />

<style>
	:global(body) {
		margin: 0;
		background: #050811;
		color: #f1f5f9;
	}

	.cheatsheet-page {
		min-height: 100vh;
		padding: 6rem 1rem 5rem;
		background:
			linear-gradient(180deg, rgba(234, 70, 71, 0.08), rgba(5, 8, 17, 0) 28rem),
			#050811;
	}

	.hero {
		max-width: 1180px;
		margin: 0 auto 2rem;
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(280px, 420px);
		gap: 2rem;
		align-items: end;
	}

	.eyebrow,
	.asset-kicker {
		margin: 0 0 0.5rem;
		color: #fb923c;
		font-size: 0.75rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	h1 {
		margin: 0;
		font-size: clamp(2.4rem, 6vw, 5rem);
		line-height: 0.95;
		letter-spacing: 0;
	}

	.lead {
		max-width: 640px;
		margin: 1.25rem 0 0;
		color: #cbd5e1;
		font-size: 1.05rem;
		line-height: 1.7;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 1.5rem;
	}

	.primary-action,
	.asset-actions a {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		text-decoration: none;
		border-radius: 8px;
		transition: transform 0.15s, border-color 0.15s, background 0.15s;
	}

	.primary-action {
		gap: 0.5rem;
		min-height: 42px;
		padding: 0 1rem;
		font-weight: 700;
	}

	.primary-action {
		background: #ea4647;
		color: #fff;
	}

	.primary-action:hover,
	.asset-actions a:hover {
		transform: translateY(-1px);
	}

	.url-panel {
		display: grid;
		gap: 0.75rem;
		border: 1px solid rgba(148, 163, 184, 0.18);
		background: rgba(15, 18, 25, 0.72);
		border-radius: 8px;
		padding: 1rem;
	}

	.url-panel div {
		min-width: 0;
	}

	.url-panel span {
		display: block;
		margin-bottom: 0.25rem;
		color: #64748b;
		font-size: 0.75rem;
		font-weight: 700;
	}

	.url-panel a {
		display: block;
		color: #cbd5e1;
		font-size: 0.82rem;
		line-height: 1.45;
		overflow-wrap: anywhere;
		text-decoration: none;
	}

	.asset-grid {
		max-width: 1180px;
		margin: 0 auto;
		display: grid;
		gap: 1.25rem;
		justify-items: center;
	}

	.asset-block {
		border: 1px solid rgba(148, 163, 184, 0.18);
		border-radius: 8px;
		background: rgba(9, 13, 25, 0.72);
		overflow: hidden;
	}

	.asset-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1rem;
		border-bottom: 1px solid rgba(148, 163, 184, 0.14);
	}

	.asset-head h2 {
		margin: 0;
		font-size: 1.05rem;
		line-height: 1.25;
	}

	.asset-actions {
		display: flex;
		gap: 0.4rem;
		flex-shrink: 0;
	}

	.asset-actions a {
		width: 34px;
		height: 34px;
		border: 1px solid rgba(148, 163, 184, 0.2);
		color: #cbd5e1;
		background: rgba(15, 18, 25, 0.82);
	}

	.preview {
		display: block;
		padding: 1rem;
		background: #030509;
	}

	.preview img {
		display: block;
		width: 100%;
		height: auto;
		border-radius: 6px;
		border: 1px solid rgba(148, 163, 184, 0.16);
	}

	.landscape-block {
		width: 100%;
	}

	@media (max-width: 820px) {
		.hero {
			grid-template-columns: 1fr;
			gap: 1.25rem;
		}

		.cheatsheet-page {
			padding-top: 5rem;
		}
	}
</style>
