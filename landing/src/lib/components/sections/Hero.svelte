<script lang="ts">
	import { base } from '$app/paths';
	import { brand } from '$lib/brand';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Download } from 'lucide-svelte';
</script>

<section class="relative pt-32 pb-20 px-6 overflow-hidden">
	<div
		class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(234,70,71,0.06)_0%,_transparent_60%)]"
	></div>

	<div class="relative mx-auto max-w-4xl text-center">
		<div class="mb-6 flex justify-center">
			<picture>
				<source srcset="{base}/avatar.webp" type="image/webp" />
				<img
					src="{base}/avatar.png"
					alt="DartLab mascot"
					width="180"
					height="180"
					fetchpriority="high"
					class="drop-shadow-[0_0_32px_rgba(234,70,71,0.25)] animate-float"
				/>
			</picture>
		</div>

		<Badge variant="success" class="mb-8">
			<span class="w-1.5 h-1.5 rounded-full bg-dl-success animate-pulse"></span>
			v{brand.version} — Sections-First Company Map
		</Badge>

		<h1 class="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6">
			<span class="text-dl-text">1 stock code →</span><br />
			<span
				class="bg-gradient-to-r from-dl-primary via-dl-primary-light to-dl-primary bg-clip-text text-transparent"
				>full company story</span
			>
		</h1>

		<p class="text-lg md:text-xl text-dl-text-muted max-w-2xl mx-auto mb-6 leading-relaxed">
			Korean DART + US SEC EDGAR filings, structured.<br />
			2,700+ KR / 970+ US companies, one line of Python.
		</p>

		<div class="mb-10 inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-dl-bg-card/70 border border-dl-border/50 font-mono text-sm md:text-base text-dl-text">
			<span class="text-dl-text-dim">&gt;&gt;&gt;</span>
			<span class="text-dl-primary">dartlab</span><span class="text-dl-text-muted">.Company(</span><span class="text-dl-accent">"005930"</span><span class="text-dl-text-muted">)</span><span class="text-dl-text-muted">.review()</span>
		</div>

		<div class="flex flex-wrap items-center justify-center gap-3 mb-4">
			<Button href={brand.desktop}>
				<Download class="w-4 h-4 inline mr-1" /> Windows 런처 — 0 setup
			</Button>
			<Button variant="secondary" href="#install">pip install dartlab</Button>
			<Button variant="secondary" href="{base}/docs/">Docs</Button>
		</div>
		<div class="flex flex-wrap items-center justify-center gap-4 mb-16 text-xs text-dl-text-dim">
			<a href={brand.colab} class="hover:text-dl-text transition-colors">Colab</a>
			<span>·</span>
			<a href={brand.molab} class="hover:text-dl-text transition-colors">Molab</a>
		</div>

		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-3xl mx-auto">
			{#each [
				{ value: '2,700+', unit: '', label: 'Korean companies structured' },
				{ value: '970+', unit: '', label: 'US companies (SEC EDGAR)' },
				{ value: '329', unit: '', label: 'topics mapped per company' },
				{ value: '1 line', unit: '', label: "of Python. That's it." }
			] as stat}
				<div
					class="px-4 py-3 rounded-lg bg-dl-bg-card/50 border border-dl-border/50 hover:border-dl-primary/20 transition-colors"
				>
					<div
						class="text-2xl font-extrabold bg-gradient-to-r from-dl-primary to-dl-accent bg-clip-text text-transparent"
					>
						{stat.value}<span class="text-sm">{stat.unit}</span>
					</div>
					<div class="text-xs text-dl-text-dim mt-1">{stat.label}</div>
				</div>
			{/each}
		</div>
	</div>
</section>
